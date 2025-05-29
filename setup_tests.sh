#!/bin/bash

# Test Setup and Dependency Installation Script for MindVueBot

echo "Setting up test environment for MindVueBot..."

# Function to check if a Python package is installed
check_package() {
    python -c "import $1" 2>/dev/null
    return $?
}

# Function to install packages with error handling
install_package() {
    echo "Installing $1..."
    if python -m pip install "$1"; then
        echo "✓ Successfully installed $1"
    else
        echo "✗ Failed to install $1"
        return 1
    fi
}

# Check if pip is available
if ! python -m pip --version &>/dev/null; then
    echo "Error: pip is not available. Please install pip first."
    exit 1
fi

# Install main project dependencies
echo "Installing main project dependencies..."
if [ -f "requirements.txt" ]; then
    install_package "-r requirements.txt"
else
    echo "Installing individual packages..."
    install_package "python-telegram-bot[job-queue]>=20.0"
    install_package "pandas>=1.3.0"
    install_package "cryptography>=36.0.0"
    install_package "python-dotenv>=0.19.0"
    install_package "matplotlib>=3.4.0"
    install_package "seaborn>=0.11.0"
    install_package "psutil"
fi

# Install test dependencies
echo "Installing test dependencies..."
install_package "pytest==7.3.1"
install_package "pytest-asyncio==0.21.0"
install_package "pytest-cov==4.1.0"
install_package "freezegun==1.2.2"
install_package "coverage==7.2.7"

# Verify installations
echo "Verifying package installations..."
packages=("pandas" "telegram" "cryptography" "pytest" "freezegun")
failed_packages=()

for package in "${packages[@]}"; do
    if check_package "$package"; then
        echo "✓ $package is available"
    else
        echo "✗ $package is not available"
        failed_packages+=("$package")
    fi
done

if [ ${#failed_packages[@]} -eq 0 ]; then
    echo "✓ All packages installed successfully!"
    
    # Test basic imports
    echo "Testing basic imports..."
    python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

try:
    from src import config
    print('✓ Config module imports successfully')
except Exception as e:
    print(f'✗ Config import failed: {e}')

try:
    from src.utils import date_helpers
    print('✓ Date helpers import successfully')
except Exception as e:
    print(f'✗ Date helpers import failed: {e}')

try:
    from src.data import encryption
    print('✓ Encryption module imports successfully')
except Exception as e:
    print(f'✗ Encryption import failed: {e}')
"
    
    echo "Setup complete! You can now run tests with:"
    echo "  pytest tests/ -v"
    echo "  python tests/run_tests.py"
    
else
    echo "Some packages failed to install: ${failed_packages[*]}"
    echo "Please check your Python environment and try again."
    exit 1
fi
