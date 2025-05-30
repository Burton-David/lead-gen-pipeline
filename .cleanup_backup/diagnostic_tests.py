#!/usr/bin/env python3
# diagnostic_tests.py - Comprehensive system diagnostics for B2B Intelligence Platform

import sys
import os
import subprocess
import importlib
from pathlib import Path

def print_header(title: str):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def print_status(check: str, status: str, details: str = ""):
    """Print formatted status line."""
    status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_icon} {check:<30} {status}")
    if details:
        print(f"   → {details}")

def run_command(cmd: str, capture_output: bool = True):
    """Run shell command and return result."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True, timeout=30)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_python_environment():
    """Check Python environment and paths."""
    print_header("Python Environment Analysis")
    
    # Python version
    print_status("Python Version", "INFO", f"{sys.version}")
    
    # Python executable path
    print_status("Python Executable", "INFO", sys.executable)
    
    # Virtual environment detection
    venv_active = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print_status("Virtual Environment", "PASS" if venv_active else "WARN", 
                f"{'Active' if venv_active else 'Not detected'}")
    
    # Python path
    print_status("Python Path", "INFO", f"{len(sys.path)} entries")
    for i, path in enumerate(sys.path[:5]):  # Show first 5 entries
        print(f"   [{i}] {path}")
    if len(sys.path) > 5:
        print(f"   ... and {len(sys.path) - 5} more entries")

def check_critical_imports():
    """Test critical package imports."""
    print_header("Critical Package Import Tests")
    
    # Test core packages
    core_packages = [
        'asyncio', 'pathlib', 'typing', 'dataclasses',
        'httpx', 'beautifulsoup4', 'playwright', 'sqlalchemy', 
        'pydantic', 'typer', 'rich', 'loguru'
    ]
    
    for package in core_packages:
        try:
            importlib.import_module(package)
            print_status(f"Import {package}", "PASS")
        except ImportError as e:
            print_status(f"Import {package}", "FAIL", str(e))

def check_llama_cpp_detailed():
    """Detailed llama-cpp-python diagnostics."""
    print_header("llama-cpp-python Detailed Diagnostics")
    
    # Check if package is installed
    success, stdout, stderr = run_command("pip show llama-cpp-python")
    if success:
        print_status("Package Installation", "PASS", "Found in pip list")
        # Extract version info
        for line in stdout.split('\n'):
            if line.startswith('Version:') or line.startswith('Location:'):
                print(f"   → {line}")
    else:
        print_status("Package Installation", "FAIL", "Not found in pip list")
        return
    
    # Try importing main module
    try:
        import llama_cpp
        print_status("Import llama_cpp", "PASS", f"Version: {getattr(llama_cpp, '__version__', 'unknown')}")
    except ImportError as e:
        print_status("Import llama_cpp", "FAIL", str(e))
        return
    except Exception as e:
        print_status("Import llama_cpp", "FAIL", f"Unexpected error: {e}")
        return
    
    # Try importing Llama class
    try:
        from llama_cpp import Llama
        print_status("Import Llama class", "PASS")
    except ImportError as e:
        print_status("Import Llama class", "FAIL", str(e))
        return
    except Exception as e:
        print_status("Import Llama class", "FAIL", f"Unexpected error: {e}")
        return
    
    # Try importing LlamaGrammar
    try:
        from llama_cpp.llama_grammar import LlamaGrammar
        print_status("Import LlamaGrammar", "PASS")
    except ImportError as e:
        print_status("Import LlamaGrammar", "FAIL", str(e))
    except Exception as e:
        print_status("Import LlamaGrammar", "FAIL", f"Unexpected error: {e}")
    
    # Check for model file
    model_paths = [
        "./models/qwen2-7b-instruct-q4_k_m.gguf",
        "/models/qwen2-7b-instruct-q4_k_m.gguf",
        os.path.expanduser("~/models/qwen2-7b-instruct-q4_k_m.gguf")
    ]
    
    model_found = False
    for model_path in model_paths:
        if os.path.exists(model_path):
            print_status("Model File", "PASS", f"Found at {model_path}")
            model_found = True
            break
    
    if not model_found:
        print_status("Model File", "WARN", "Model not found in common locations")

def check_system_dependencies():
    """Check system-level dependencies."""
    print_header("System Dependencies")
    
    # Check for common build tools
    build_tools = [
        ('cmake', 'cmake --version'),
        ('gcc', 'gcc --version'),
        ('make', 'make --version'),
        ('python3-dev', 'python3-config --includes')
    ]
    
    for tool, cmd in build_tools:
        success, stdout, stderr = run_command(cmd)
        if success:
            version = stdout.split('\n')[0] if stdout else "Available"
            print_status(f"{tool}", "PASS", version)
        else:
            print_status(f"{tool}", "WARN", "Not available or not working")

def check_project_structure():
    """Check project file structure."""
    print_header("Project Structure Validation")
    
    required_files = [
        'cli.py',
        'requirements.txt',
        'setup.sh',
        '.env.example',
        'lead_gen_pipeline/__init__.py',
        'lead_gen_pipeline/llm_processor.py',
        'lead_gen_pipeline/chamber_parser.py',
        'lead_gen_pipeline/crawler.py',
        'lead_gen_pipeline/scraper.py',
        'lead_gen_pipeline/database.py',
        'lead_gen_pipeline/models.py',
        'data/chamber_urls.csv'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print_status(f"File: {file_path}", "PASS")
        else:
            print_status(f"File: {file_path}", "FAIL", "Missing")

def test_import_project_modules():
    """Test importing our project modules."""
    print_header("Project Module Import Tests")
    
    # Add current directory to path
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    project_modules = [
        'lead_gen_pipeline.config',
        'lead_gen_pipeline.utils',
        'lead_gen_pipeline.models',
        'lead_gen_pipeline.database',
        'lead_gen_pipeline.crawler',
        'lead_gen_pipeline.scraper',
        'lead_gen_pipeline.llm_processor',
        'lead_gen_pipeline.chamber_parser',
        'lead_gen_pipeline.chamber_pipeline'
    ]
    
    for module in project_modules:
        try:
            importlib.import_module(module)
            print_status(f"Import {module}", "PASS")
        except ImportError as e:
            print_status(f"Import {module}", "FAIL", str(e))
        except Exception as e:
            print_status(f"Import {module}", "FAIL", f"Unexpected error: {e}")

def test_llm_processor_initialization():
    """Test LLM processor initialization."""
    print_header("LLM Processor Initialization Test")
    
    try:
        # Import the module
        from lead_gen_pipeline.llm_processor import LLMProcessor
        print_status("Import LLMProcessor", "PASS")
        
        # Create instance
        processor = LLMProcessor()
        print_status("Create LLMProcessor instance", "PASS")
        
        # Check if llama-cpp is available according to our code
        from lead_gen_pipeline.llm_processor import LLAMA_CPP_AVAILABLE
        print_status("LLAMA_CPP_AVAILABLE flag", "PASS" if LLAMA_CPP_AVAILABLE else "FAIL", 
                    f"Value: {LLAMA_CPP_AVAILABLE}")
        
    except Exception as e:
        print_status("LLMProcessor test", "FAIL", str(e))

def generate_fix_recommendations():
    """Generate recommended fixes based on diagnostics."""
    print_header("Recommended Fixes")
    
    print("Based on the diagnostics above, here are potential solutions:")
    print()
    print("🔧 If llama-cpp-python import fails:")
    print("   1. Reinstall with specific flags:")
    print("      pip uninstall llama-cpp-python")
    print("      CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' pip install llama-cpp-python --no-cache-dir")
    print()
    print("   2. For Apple Silicon Macs:")
    print("      CMAKE_ARGS='-DLLAMA_METAL=on' pip install llama-cpp-python --no-cache-dir")
    print()
    print("   3. For systems without GPU:")
    print("      CMAKE_ARGS='-DLLAMA_BLAS=ON' pip install llama-cpp-python --no-cache-dir")
    print()
    print("🔧 If virtual environment issues:")
    print("   1. Activate virtual environment explicitly:")
    print("      source venv/bin/activate")
    print("      python cli.py chambers --url https://www.paloaltochamber.com")
    print()
    print("🔧 If missing system dependencies:")
    print("   - On macOS: brew install cmake")
    print("   - On Ubuntu/Debian: sudo apt-get install cmake build-essential")
    print("   - On CentOS/RHEL: sudo yum install cmake gcc-c++")

def main():
    """Run all diagnostic tests."""
    print("🚀 B2B Intelligence Platform - System Diagnostics")
    print("="*60)
    print("This script will diagnose potential issues with your installation.")
    print()
    
    # Run all diagnostic tests
    check_python_environment()
    check_system_dependencies()
    check_project_structure()
    check_critical_imports()
    check_llama_cpp_detailed()
    test_import_project_modules()
    test_llm_processor_initialization()
    
    # Generate recommendations
    generate_fix_recommendations()
    
    print_header("Diagnostic Complete")
    print("Review the results above to identify and fix any issues.")
    print("If you need help interpreting the results, share this output.")

if __name__ == "__main__":
    main()
