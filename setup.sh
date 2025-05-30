#!/bin/bash
# setup.sh - Enhanced setup script for B2B Intelligence Platform

set -e

echo "🚀 B2B Intelligence Platform - Setup"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    print_warning "Running inside Docker container - skipping some setup steps"
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# Check Python version
print_status "Checking system requirements..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
    
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
        print_success "Python version is compatible"
    else
        print_error "Python 3.8+ required. Current version: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check memory availability
if ! $IN_DOCKER; then
    if command -v free &> /dev/null; then
        MEMORY_GB=$(free -g | awk 'NR==2{printf "%.1f", $2}')
        print_status "Available memory: ${MEMORY_GB}GB"
        
        if (( $(echo "$MEMORY_GB < 8" | bc -l 2>/dev/null || echo "0") )); then
            print_warning "Less than 8GB RAM detected. LLM performance may be limited."
            print_warning "Consider running on a machine with 16GB+ RAM for optimal performance."
        fi
    fi
fi

# Detect system type for llama-cpp-python optimization
SYSTEM=$(uname -s)
MACHINE=$(uname -m)
print_status "Detected system: $SYSTEM on $MACHINE"

# Check for Apple Silicon
if [ "$SYSTEM" = "Darwin" ] && [ "$MACHINE" = "arm64" ]; then
    print_status "Apple Silicon detected - will use Metal acceleration for LLM"
    IS_APPLE_SILICON=true
else
    IS_APPLE_SILICON=false
fi

# Create directory structure
print_status "Creating directory structure..."

mkdir -p data logs models reports
mkdir -p data/exports logs/archive

print_success "Directory structure created"

# Set up Python environment
if ! $IN_DOCKER; then
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    print_status "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install basic requirements first (excluding llama-cpp-python)
    print_status "Installing basic Python dependencies..."
    pip install python-dotenv pydantic pydantic-settings loguru
    pip install httpx beautifulsoup4 playwright sqlalchemy aiosqlite
    pip install "typer[all]" rich pytest pytest-mock pytest-cov pytest-html pytest-asyncio
    pip install tldextract respx phonenumbers email-validator
    pip install markdownify huggingface-hub html2text lxml uvloop orjson
    
    print_success "Basic Python dependencies installed"
    
    # Install Playwright browsers
    print_status "Installing Playwright browsers..."
    playwright install chromium
    print_success "Playwright browsers installed"
    
    # Install llama-cpp-python with appropriate optimizations
    print_status "Installing llama-cpp-python with optimizations..."
    
    # Uninstall any existing version first
    pip uninstall -y llama-cpp-python 2>/dev/null || true
    
    # Set CMAKE args based on system
    if [ "$IS_APPLE_SILICON" = true ]; then
        print_status "Using Metal acceleration for Apple Silicon..."
        CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --no-cache-dir --verbose
    elif [ "$SYSTEM" = "Darwin" ]; then
        print_status "Using OpenBLAS for Intel Mac..."
        CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python --no-cache-dir --verbose
    elif [ "$SYSTEM" = "Linux" ]; then
        print_status "Using OpenBLAS for Linux..."
        CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python --no-cache-dir --verbose
    else
        print_status "Using default configuration..."
        CMAKE_ARGS="-DLLAMA_BLAS=ON" pip install llama-cpp-python --no-cache-dir --verbose
    fi
    
    # Test llama-cpp-python installation
    if python3 -c "from llama_cpp import Llama; print('llama-cpp-python works!')" 2>/dev/null; then
        print_success "llama-cpp-python installed and working"
    else
        print_warning "llama-cpp-python installation may have issues"
        print_warning "You can run 'python diagnostic_tests.py' to diagnose"
        print_warning "Or run 'python fix_installation.py' to attempt automatic fixes"
    fi
fi

# Configure environment
print_status "Setting up environment configuration..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success "Environment configuration created from template"
    print_warning "Please review and customize .env file as needed"
else
    print_success "Environment configuration already exists"
fi

# Check for LLM model
print_status "Checking for LLM model..."

MODEL_FILE="./models/qwen2-7b-instruct-q4_k_m.gguf"

if [ ! -f "$MODEL_FILE" ]; then
    print_warning "LLM model not found. Attempting to download..."
    
    if python3 -c "import huggingface_hub" 2>/dev/null; then
        print_status "Downloading Qwen2 Instruct 7B model (this may take several minutes)..."
        
        python3 -c "
from huggingface_hub import hf_hub_download
import os

print('Downloading model...')
try:
    downloaded_path = hf_hub_download(
        repo_id='Qwen/Qwen2-7B-Instruct-GGUF',
        filename='qwen2-7b-instruct-q4_k_m.gguf',
        local_dir='./models',
        local_dir_use_symlinks=False
    )
    print(f'Model downloaded successfully: {downloaded_path}')
except Exception as e:
    print(f'Download failed: {e}')
    exit(1)
"
        
        if [ $? -eq 0 ]; then
            print_success "LLM model downloaded successfully"
        else
            print_error "Failed to download LLM model automatically"
            print_warning "Manual download required:"
            print_warning "1. Go to: https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF"
            print_warning "2. Download: qwen2-7b-instruct-q4_k_m.gguf"
            print_warning "3. Save to: $MODEL_FILE"
        fi
    else
        print_warning "huggingface-hub not available for automatic download"
        print_warning "Manual download required:"
        print_warning "1. Go to: https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF"
        print_warning "2. Download: qwen2-7b-instruct-q4_k_m.gguf" 
        print_warning "3. Save to: $MODEL_FILE"
    fi
else
    print_success "LLM model already exists"
fi

# Initialize database
print_status "Initializing database..."

if ! $IN_DOCKER && [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 cli.py init

if [ $? -eq 0 ]; then
    print_success "Database initialized successfully"
else
    print_error "Database initialization failed"
    exit 1
fi

# Test configuration
print_status "Testing configuration..."

python3 cli.py config > /dev/null

if [ $? -eq 0 ]; then
    print_success "Configuration test passed"
else
    print_error "Configuration test failed"
    exit 1
fi

# Run component tests (without LLM)
print_status "Running component tests..."
if python3 test_without_llm.py > /dev/null 2>&1; then
    print_success "Component tests passed"
else
    print_warning "Some component tests failed - check with: python test_without_llm.py"
fi

# Security settings
print_status "Applying security settings..."

chmod 600 .env 2>/dev/null || true
chmod 700 data logs models 2>/dev/null || true

print_success "Security settings applied"

# Final summary
echo ""
echo "=============================================="
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}Quick Start Commands:${NC}"
echo ""
echo "# Test components without LLM:"
echo "python test_without_llm.py"
echo ""
echo "# Diagnose any issues:"
echo "python diagnostic_tests.py"
echo ""
echo "# Fix LLM issues if needed:"
echo "python fix_installation.py"
echo ""
echo "# Test single chamber (requires LLM):"
echo "python cli.py chambers --url https://www.paloaltochamber.com"
echo ""
echo "# Process chamber batch:"
echo "python cli.py chambers --input data/chamber_urls.csv"
echo ""
echo "# View database statistics:"
echo "python cli.py stats"
echo ""
echo "# Export business data:"
echo "python cli.py export --output business_data.csv"
echo ""

if [ ! -f "$MODEL_FILE" ]; then
    echo -e "${YELLOW}⚠️  IMPORTANT: LLM model not found${NC}"
    echo "Chamber directory processing requires the LLM model."
    echo "Run: python cli.py setup-llm"
    echo ""
fi

# Check llama-cpp-python installation
if ! python3 -c "from llama_cpp import Llama" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  IMPORTANT: llama-cpp-python may have installation issues${NC}"
    echo "Chamber directory processing requires working llama-cpp-python."
    echo "Troubleshooting steps:"
    echo "1. Run: python diagnostic_tests.py"
    echo "2. Run: python fix_installation.py"
    echo "3. Check system dependencies (cmake, build tools)"
    echo ""
fi

echo -e "${BLUE}For Docker deployment:${NC}"
echo "docker-compose up --build"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "See README.md for detailed usage instructions"
echo ""

print_success "B2B Intelligence Platform setup complete!"
