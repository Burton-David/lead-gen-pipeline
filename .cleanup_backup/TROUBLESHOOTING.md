# Troubleshooting Guide

This guide helps diagnose and fix common issues with the B2B Intelligence Platform.

## 🚨 Quick Problem Identification

### Issue: "llama-cpp-python not available"

**Symptoms:**
```
ERROR | llama-cpp-python not available. Install with: pip install llama-cpp-python
```

**Cause:** The llama-cpp-python package failed to install or import properly.

**Solution:**
```bash
# 1. Run diagnostics to identify the specific issue
python diagnostic_tests.py

# 2. Run automated fix
python fix_installation.py

# 3. Test without LLM to verify other components
python test_without_llm.py
```

### Issue: Virtual Environment Not Activated

**Symptoms:**
- Packages appear installed but imports fail
- "Module not found" errors for installed packages

**Solution:**
```bash
# Always activate virtual environment first
source venv/bin/activate

# Then run commands
python cli.py chambers --url https://example.com
```

### Issue: Model File Not Found

**Symptoms:**
```
Model file not found: ./models/qwen2-7b-instruct-q4_k_m.gguf
```

**Solution:**
```bash
# Download model automatically
python cli.py setup-llm

# Or download manually from:
# https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/blob/main/qwen2-7b-instruct-q4_k_m.gguf
```

## 🔧 Systematic Troubleshooting

### Step 1: Run Diagnostics

```bash
python diagnostic_tests.py
```

This comprehensive diagnostic will check:
- Python environment and virtual environment status
- System dependencies (cmake, build tools)
- Package installations and imports
- Project structure and file permissions
- LLM processor initialization

### Step 2: Test Components Individually

```bash
# Test non-LLM components
python test_without_llm.py
```

This isolates the problem by testing:
- Web crawler functionality
- HTML scraper operations
- Database operations
- CLI commands (non-chamber)

### Step 3: Apply Automated Fixes

```bash
python fix_installation.py
```

This script will:
- Detect your system type (Apple Silicon, Intel Mac, Linux)
- Apply appropriate CMAKE flags for llama-cpp-python
- Reinstall packages with correct configurations
- Test the installation

## 🍎 macOS-Specific Issues

### Apple Silicon (M1/M2/M3) Macs

**Issue:** llama-cpp-python compilation fails or runs slowly

**Solution:**
```bash
# Uninstall existing version
pip uninstall llama-cpp-python

# Install with Metal acceleration
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --no-cache-dir
```

### Intel Macs

**Issue:** Performance issues or compilation problems

**Solution:**
```bash
# Install Homebrew dependencies
brew install cmake pkg-config

# Install with OpenBLAS
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python --no-cache-dir
```

### Missing Build Tools

**Issue:** "cmake not found" or compilation errors

**Solution:**
```bash
# Install Xcode command line tools
xcode-select --install

# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install build dependencies
brew install cmake pkg-config
```

## 🐧 Linux-Specific Issues

### Ubuntu/Debian

**Issue:** Missing build dependencies

**Solution:**
```bash
# Update package list
sudo apt-get update

# Install build tools
sudo apt-get install -y cmake build-essential pkg-config python3-dev

# Reinstall llama-cpp-python
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python --no-cache-dir
```

### CentOS/RHEL/Fedora

**Issue:** Missing build dependencies

**Solution:**
```bash
# For CentOS/RHEL
sudo yum install -y cmake gcc-c++ make python3-devel

# For Fedora
sudo dnf install -y cmake gcc-c++ make python3-devel

# Reinstall llama-cpp-python
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_BLAS=ON" pip install llama-cpp-python --no-cache-dir
```

## 🐳 Docker Issues

### Issue: Container fails to build

**Solution:**
```bash
# Clean build
docker-compose down
docker system prune -f
docker-compose up --build --no-cache
```

### Issue: Model not found in container

**Solution:**
```bash
# Ensure model directory is mounted
# Check docker-compose.yml volumes section:
volumes:
  - ./models:/app/models
  - ./data:/app/data
```

## 🗂️ Database Issues

### Issue: Database locked or permission errors

**Solution:**
```bash
# Stop all processes using the database
pkill -f "python.*cli"

# Reset database permissions
chmod 664 data/*.db

# Reinitialize if needed
python cli.py init
```

### Issue: SQLite performance issues with large datasets

**Solution:**
```bash
# Switch to PostgreSQL for better performance
# Update .env file:
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname"
```

## 🌐 Network Issues

### Issue: Chamber website access blocked

**Symptoms:**
- "403 Forbidden" errors
- "robots.txt disallows" messages
- Slow or failing page loads

**Solution:**
```bash
# Check robots.txt compliance
# Edit .env file:
CRAWLER_RESPECT_ROBOTS_TXT=false  # Only if necessary

# Adjust delays to be more respectful
CRAWLER_MIN_DELAY_PER_DOMAIN_SECONDS=5.0
CRAWLER_MAX_DELAY_PER_DOMAIN_SECONDS=10.0
```

### Issue: Playwright browser download fails

**Solution:**
```bash
# Manual browser installation
playwright install chromium

# Or install system-wide
sudo playwright install-deps chromium
```

## 🧠 Memory Issues

### Issue: Out of memory errors with LLM

**Symptoms:**
- Process killed during model loading
- "Cannot allocate memory" errors

**Solution:**
```bash
# Reduce concurrency in .env
MAX_PIPELINE_CONCURRENCY=1
CRAWLER_DEFAULT_TIMEOUT_SECONDS=60

# Monitor memory usage
htop  # Linux/macOS
# Or Activity Monitor on macOS
```

### Issue: Swap thrashing

**Solution:**
```bash
# Close other applications
# Consider processing smaller batches
python cli.py chambers --url https://single-chamber.com

# Rather than:
python cli.py chambers --input data/many_chambers.csv
```

## 🔍 Advanced Debugging

### Enable Debug Logging

```bash
# Edit .env file
LOGGING_LOG_LEVEL=DEBUG

# Run with verbose output
python cli.py chambers --url https://example.com --verbose
```

### Check Log Files

```bash
# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/error.log
```

### Manual Testing

```bash
# Test individual components
python -c "from lead_gen_pipeline.crawler import AsyncWebCrawler; print('Crawler OK')"
python -c "from lead_gen_pipeline.scraper import HTMLScraper; print('Scraper OK')"
python -c "from llama_cpp import Llama; print('LLM OK')"
```

## 📞 Getting Help

### Before Asking for Help

1. **Run diagnostics:** `python diagnostic_tests.py`
2. **Check logs:** Look in `logs/app.log` and `logs/error.log`
3. **Test components:** Run `python test_without_llm.py`
4. **Try automated fix:** Run `python fix_installation.py`

### What to Include in Bug Reports

1. **System information:**
   ```bash
   uname -a
   python --version
   pip list | grep llama
   ```

2. **Complete error output** from diagnostic_tests.py

3. **Steps to reproduce** the issue

4. **Environment details** (.env configuration, excluding secrets)

### Common Solutions Summary

| Problem | Quick Fix |
|---------|-----------|
| llama-cpp-python import fails | `python fix_installation.py` |
| Virtual env not active | `source venv/bin/activate` |
| Model not found | `python cli.py setup-llm` |
| Database locked | `pkill -f python.*cli` |
| Memory issues | Reduce concurrency in .env |
| Network issues | Increase delays in .env |
| Permission errors | `chmod 664 data/*.db` |

Most issues can be resolved by running the diagnostic and fix scripts. The platform is designed to be robust and self-healing where possible.
