#!/usr/bin/env python3
"""
Comprehensive test runner for MindVueBot that handles dependency installation
and provides detailed error reporting.
"""

import subprocess
import sys
import os
import importlib.util
from pathlib import Path

def check_package_installed(package_name):
    """Check if a Python package is installed."""
    try:
        if package_name == "telegram":
            import telegram
        elif package_name == "pandas":
            import pandas
        elif package_name == "pytest":
            import pytest
        elif package_name == "freezegun":
            import freezegun
        elif package_name == "cryptography":
            import cryptography
        else:
            importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_spec):
    """Install a package using pip."""
    try:
        print(f"Installing {package_spec}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_spec
        ], capture_output=True, text=True, check=True)
        print(f"✓ Successfully installed {package_spec}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package_spec}")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ pip is not available")
        return False

def setup_environment():
    """Set up the test environment by installing missing dependencies."""
    print("🔧 Setting up test environment...")
    
    # Check required packages
    required_packages = [
        ("pandas", "pandas>=1.3.0"),
        ("telegram", "python-telegram-bot[job-queue]>=20.0"),
        ("pytest", "pytest==7.3.1"),
        ("freezegun", "freezegun==1.2.2"),
        ("cryptography", "cryptography>=36.0.0"),
    ]
    
    missing_packages = []
    
    for package_name, package_spec in required_packages:
        if not check_package_installed(package_name):
            print(f"📦 {package_name} is missing")
            missing_packages.append(package_spec)
        else:
            print(f"✓ {package_name} is available")
    
    if missing_packages:
        print(f"\n📥 Installing {len(missing_packages)} missing packages...")
        for package_spec in missing_packages:
            if not install_package(package_spec):
                return False
        print("✓ All packages installed successfully!")
    else:
        print("✓ All required packages are already installed!")
    
    return True

def check_imports():
    """Test basic imports to verify the setup."""
    print("\n🧪 Testing basic imports...")
    
    # Add src to path
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    import_tests = [
        ("src.config", "Config module"),
        ("src.utils.date_helpers", "Date helpers"),
        ("src.utils.formatters", "Formatters"),
        ("src.utils.conversation_manager", "Conversation manager"),
        ("src.data.encryption", "Encryption module"),
        ("pandas", "Pandas"),
        ("pytest", "Pytest"),
    ]
    
    failed_imports = []
    
    for module_name, description in import_tests:
        try:
            importlib.import_module(module_name)
            print(f"✓ {description}")
        except ImportError as e:
            print(f"✗ {description}: {e}")
            failed_imports.append((module_name, str(e)))
    
    if failed_imports:
        print(f"\n❌ {len(failed_imports)} import(s) failed:")
        for module_name, error in failed_imports:
            print(f"  - {module_name}: {error}")
        return False
    
    print("✓ All imports successful!")
    return True

def run_tests_with_pytest():
    """Run tests using pytest."""
    print("\n🚀 Running tests with pytest...")
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--no-header"
        ], cwd=Path(__file__).parent)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("✗ pytest command not found")
        return False

def run_tests_with_unittest():
    """Run tests using unittest as fallback."""
    print("\n🚀 Running tests with unittest...")
    
    try:
        # Add src to Python path for imports
        env = os.environ.copy()
        current_path = env.get('PYTHONPATH', '')
        src_path = str(Path(__file__).parent / "src")
        env['PYTHONPATH'] = f"{src_path}:{current_path}" if current_path else src_path
        
        result = subprocess.run([
            sys.executable, 
            "tests/run_tests.py"
        ], cwd=Path(__file__).parent, env=env)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("✗ Python test runner not found")
        return False

def analyze_test_failures():
    """Analyze and report test failures."""
    print("\n📊 Analyzing test results...")
    
    # Check for common issues
    issues_found = []
    
    # Check if config file exists and is readable
    config_path = Path(__file__).parent / "src" / "config.py"
    if not config_path.exists():
        issues_found.append("Config file is missing")
    
    # Check if test fixtures are available
    conftest_path = Path(__file__).parent / "tests" / "conftest.py"
    if not conftest_path.exists():
        issues_found.append("Test fixtures (conftest.py) are missing")
    
    # Check for .env file (might be needed for config)
    env_path = Path(__file__).parent / ".env"
    env_bak_path = Path(__file__).parent / ".env.bak"
    if not env_path.exists() and env_bak_path.exists():
        issues_found.append("Environment file (.env) might be missing - found .env.bak")
    
    if issues_found:
        print("⚠️  Potential issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("✓ No obvious configuration issues found")

def main():
    """Main test runner function."""
    print("🧪 MindVueBot Test Runner")
    print("=" * 40)
    
    # Step 1: Set up environment
    if not setup_environment():
        print("\n❌ Environment setup failed!")
        return 1
    
    # Step 2: Check imports
    if not check_imports():
        print("\n❌ Import checks failed!")
        analyze_test_failures()
        return 1
    
    # Step 3: Run tests
    print("\n" + "=" * 40)
    
    # Try pytest first
    if check_package_installed("pytest"):
        success = run_tests_with_pytest()
    else:
        print("pytest not available, falling back to unittest...")
        success = run_tests_with_unittest()
    
    # Step 4: Report results
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed!")
        analyze_test_failures()
        return 1

if __name__ == "__main__":
    sys.exit(main())
