#!/usr/bin/env python3
"""
Simple test runner to identify failing scraper tests
"""
import sys
import subprocess
import os
from pathlib import Path

# Set up the environment
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_scraper_tests():
    """Run the scraper tests and capture output"""
    try:
        # Change to project directory
        os.chdir(project_root)
        
        # Run pytest on scraper tests specifically
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/unit/test_scraper.py", 
            "-v", "--tb=short", "--no-header"
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Tests timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_scraper_tests()
    sys.exit(0 if success else 1)
