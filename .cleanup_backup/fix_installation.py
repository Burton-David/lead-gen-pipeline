#!/usr/bin/env python3
# fix_installation.py - Automated fixes for common installation issues

import sys
import os
import subprocess
import platform
from pathlib import Path

def print_header(title: str):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)

def run_command(cmd: str, description: str = ""):
    """Run command and report status."""
    print(f"Running: {cmd}")
    if description:
        print(f"Purpose: {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print("✅ Success")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()[:200]}...")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error: {e.stderr.strip()[:200]}...")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def detect_system_info():
    """Detect system information for targeted fixes."""
    print_header("System Information")
    
    system = platform.system()
    machine = platform.machine()
    python_version = sys.version
    
    print(f"OS: {system}")
    print(f"Architecture: {machine}")
    print(f"Python: {python_version}")
    
    # Detect Apple Silicon
    is_apple_silicon = system == "Darwin" and machine == "arm64"
    print(f"Apple Silicon: {'Yes' if is_apple_silicon else 'No'}")
    
    return {
        'system': system,
        'machine': machine,
        'is_apple_silicon': is_apple_silicon,
        'is_macos': system == "Darwin",
        'is_linux': system == "Linux"
    }

def fix_virtual_environment():
    """Ensure virtual environment is properly set up."""
    print_header("Virtual Environment Fix")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print("✅ Already in virtual environment")
        return True
    
    # Check if venv directory exists
    if not os.path.exists('venv'):
        print("Creating new virtual environment...")
        if not run_command("python3 -m venv venv", "Create virtual environment"):
            return False
    
    print("\n⚠️  IMPORTANT: You need to activate the virtual environment manually:")
    print("Run this command:")
    print("source venv/bin/activate")
    print("\nThen re-run this script or the main commands.")
    
    return False

def fix_llama_cpp_installation(system_info):
    """Fix llama-cpp-python installation with appropriate flags."""
    print_header("llama-cpp-python Installation Fix")
    
    # First, uninstall existing installation
    print("Removing existing llama-cpp-python installation...")
    run_command("pip uninstall -y llama-cpp-python", "Remove existing installation")
    
    # Clear pip cache
    run_command("pip cache purge", "Clear pip cache")
    
    # Determine appropriate CMAKE flags based on system
    cmake_args = []
    
    if system_info['is_apple_silicon']:
        print("Detected Apple Silicon - using Metal acceleration")
        cmake_args.append('-DLLAMA_METAL=on')
    elif system_info['is_macos']:
        print("Detected Intel Mac - using OpenBLAS")
        cmake_args.append('-DLLAMA_BLAS=ON')
        cmake_args.append('-DLLAMA_BLAS_VENDOR=OpenBLAS')
    elif system_info['is_linux']:
        print("Detected Linux - using OpenBLAS")
        cmake_args.append('-DLLAMA_BLAS=ON')
        cmake_args.append('-DLLAMA_BLAS_VENDOR=OpenBLAS')
    else:
        print("Using default configuration")
        cmake_args.append('-DLLAMA_BLAS=ON')
    
    # Build installation command
    cmake_str = ' '.join(cmake_args)
    install_cmd = f'CMAKE_ARGS="{cmake_str}" pip install llama-cpp-python --no-cache-dir --verbose'
    
    print(f"Installing llama-cpp-python with: {cmake_str}")
    
    success = run_command(install_cmd, "Install llama-cpp-python with optimizations")
    
    if not success:
        print("\n⚠️  Installation with optimizations failed. Trying fallback...")
        fallback_cmd = "pip install llama-cpp-python --no-cache-dir"
        success = run_command(fallback_cmd, "Fallback installation")
    
    return success

def install_system_dependencies(system_info):
    """Install required system dependencies."""
    print_header("System Dependencies Installation")
    
    if system_info['is_macos']:
        # Check if Homebrew is available
        if run_command("which brew", "Check for Homebrew"):
            print("Installing dependencies with Homebrew...")
            deps = ['cmake', 'pkg-config']
            for dep in deps:
                run_command(f"brew install {dep}", f"Install {dep}")
        else:
            print("⚠️  Homebrew not found. Please install it first:")
            print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            
    elif system_info['is_linux']:
        # Try different package managers
        if run_command("which apt-get", "Check for apt-get"):
            print("Installing dependencies with apt-get...")
            run_command("sudo apt-get update", "Update package list")
            run_command("sudo apt-get install -y cmake build-essential pkg-config", "Install build tools")
        elif run_command("which yum", "Check for yum"):
            print("Installing dependencies with yum...")
            run_command("sudo yum install -y cmake gcc-c++ make", "Install build tools")
        elif run_command("which dnf", "Check for dnf"):
            print("Installing dependencies with dnf...")
            run_command("sudo dnf install -y cmake gcc-c++ make", "Install build tools")
        else:
            print("⚠️  Could not detect package manager. Please install cmake and build tools manually.")

def test_installation():
    """Test if the installation is working."""
    print_header("Installation Test")
    
    try:
        print("Testing llama-cpp-python import...")
        from llama_cpp import Llama
        from llama_cpp.llama_grammar import LlamaGrammar
        print("✅ llama-cpp-python imports successfully")
        
        print("Testing project imports...")
        sys.path.insert(0, os.getcwd())
        from lead_gen_pipeline.llm_processor import LLMProcessor, LLAMA_CPP_AVAILABLE
        
        if LLAMA_CPP_AVAILABLE:
            print("✅ LLM processor reports llama-cpp-python is available")
            
            # Test creating processor instance
            processor = LLMProcessor()
            print("✅ LLM processor instance created successfully")
            
            return True
        else:
            print("❌ LLM processor reports llama-cpp-python is NOT available")
            return False
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main fix routine."""
    print("🔧 B2B Intelligence Platform - Installation Fix")
    print("="*60)
    print("This script will attempt to fix common installation issues.")
    print()
    
    # Detect system
    system_info = detect_system_info()
    
    # Check virtual environment
    if not fix_virtual_environment():
        print("\n❌ Please activate virtual environment and re-run this script.")
        return False
    
    # Install system dependencies
    install_system_dependencies(system_info)
    
    # Fix llama-cpp-python installation
    if not fix_llama_cpp_installation(system_info):
        print("\n❌ Failed to install llama-cpp-python")
        return False
    
    # Test installation
    if test_installation():
        print_header("Fix Complete")
        print("✅ Installation appears to be working!")
        print("\nYou can now run:")
        print("python cli.py chambers --url https://www.paloaltochamber.com")
        return True
    else:
        print_header("Fix Incomplete")
        print("❌ Some issues remain. Please:")
        print("1. Run diagnostic_tests.py for detailed analysis")
        print("2. Check the error messages above")
        print("3. Consider manual installation steps")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
