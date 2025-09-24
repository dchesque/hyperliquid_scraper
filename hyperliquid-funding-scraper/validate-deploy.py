#!/usr/bin/env python3
"""
Validation script to ensure everything is ready for EasyPanel deployment
Run this before deploying to catch issues early
"""

import os
import sys
from pathlib import Path

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "END": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['END']}")

def validate_files():
    """Validate required files exist"""
    print_status("Validating required files...")

    required_files = [
        "Dockerfile",
        "requirements.txt",
        ".env.production",
        "src/main.py",
        "src/database/supabase_client.py",
        "src/scrapers/funding_scraper.py",
        "migrations/migrate.py"
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print_status(f"Missing files: {', '.join(missing_files)}", "ERROR")
        return False

    print_status("All required files present", "SUCCESS")
    return True

def validate_env_file():
    """Validate .env.production file"""
    print_status("Validating environment configuration...")

    env_file = Path(".env.production")
    if not env_file.exists():
        print_status(".env.production file not found", "ERROR")
        return False

    content = env_file.read_text()
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "HEADLESS_MODE",
        "RUN_INTERVAL_MINUTES",
        "ENABLE_SCHEDULER"
    ]

    missing_vars = []
    placeholder_vars = []

    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
        elif f"{var}=your_" in content or f"{var}=https://your-" in content:
            placeholder_vars.append(var)

    if missing_vars:
        print_status(f"Missing environment variables: {', '.join(missing_vars)}", "ERROR")
        return False

    if placeholder_vars:
        print_status(f"Environment variables need configuration: {', '.join(placeholder_vars)}", "WARNING")
        print_status("Update these with your actual Supabase credentials", "WARNING")

    print_status("Environment configuration valid", "SUCCESS")
    return True

def validate_dockerfile():
    """Validate Dockerfile"""
    print_status("Validating Dockerfile...")

    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print_status("Dockerfile not found", "ERROR")
        return False

    content = dockerfile.read_text()

    # Check for known problematic packages
    problematic_packages = ["libgconf-2-4", "libgdk-pixbuf2.0-0"]
    for package in problematic_packages:
        if package in content:
            print_status(f"Found problematic package: {package}", "ERROR")
            return False

    # Check for required components
    required_components = [
        "FROM python:3.11-slim",
        "google-chrome-stable",
        "chromedriver",
        "WORKDIR /app"
    ]

    for component in required_components:
        if component not in content:
            print_status(f"Missing component in Dockerfile: {component}", "ERROR")
            return False

    print_status("Dockerfile validation passed", "SUCCESS")
    return True

def validate_requirements():
    """Validate requirements.txt"""
    print_status("Validating Python requirements...")

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print_status("requirements.txt not found", "ERROR")
        return False

    content = requirements_file.read_text()

    essential_packages = [
        "selenium",
        "supabase",
        "pandas",
        "python-dotenv"
    ]

    missing_packages = []
    for package in essential_packages:
        if package not in content:
            missing_packages.append(package)

    if missing_packages:
        print_status(f"Missing essential packages: {', '.join(missing_packages)}", "ERROR")
        return False

    print_status("Requirements validation passed", "SUCCESS")
    return True

def validate_src_structure():
    """Validate src directory structure"""
    print_status("Validating source code structure...")

    required_dirs = [
        "src/config",
        "src/database",
        "src/scrapers",
        "src/utils"
    ]

    required_files = [
        "src/__init__.py",
        "src/main.py",
        "src/config/settings.py",
        "src/database/__init__.py",
        "src/database/supabase_client.py",
        "src/scrapers/__init__.py",
        "src/scrapers/funding_scraper.py"
    ]

    missing_items = []

    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_items.append(f"Directory: {dir_path}")

    for file_path in required_files:
        if not Path(file_path).exists():
            missing_items.append(f"File: {file_path}")

    if missing_items:
        print_status(f"Missing source items: {', '.join(missing_items)}", "ERROR")
        return False

    print_status("Source structure validation passed", "SUCCESS")
    return True

def test_imports():
    """Test critical imports"""
    print_status("Testing Python imports...")

    try:
        # Add src to path
        sys.path.insert(0, str(Path("src").resolve()))

        # Test imports
        from src.config import settings
        from src.database.supabase_client import SupabaseClient
        from src.scrapers.funding_scraper import FundingRateScraper

        print_status("All imports successful", "SUCCESS")
        return True

    except ImportError as e:
        print_status(f"Import error: {e}", "ERROR")
        return False
    except Exception as e:
        print_status(f"Import test failed: {e}", "ERROR")
        return False

def main():
    print("="*60)
    print("EasyPanel Deployment Validation")
    print("="*60)

    validations = [
        ("Files", validate_files),
        ("Environment", validate_env_file),
        ("Dockerfile", validate_dockerfile),
        ("Requirements", validate_requirements),
        ("Source Structure", validate_src_structure),
        ("Python Imports", test_imports)
    ]

    results = []
    for name, validator in validations:
        print(f"\n--- {name} Validation ---")
        try:
            result = validator()
            results.append(result)
        except Exception as e:
            print_status(f"Validation failed with exception: {e}", "ERROR")
            results.append(False)

    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    passed = sum(results)
    total = len(results)

    for i, (name, _) in enumerate(validations):
        status = "PASSED" if results[i] else "FAILED"
        print(f"{name:<20} {status}")

    print(f"\nOverall: {passed}/{total} validations passed")

    if passed == total:
        print_status("\nALL VALIDATIONS PASSED!", "SUCCESS")
        print_status("Your project is ready for EasyPanel deployment!", "SUCCESS")
        print("\nNext steps:")
        print("1. Upload files to EasyPanel")
        print("2. Configure environment variables")
        print("3. Deploy!")
        return True
    else:
        print_status(f"\n{total-passed} validation(s) failed", "ERROR")
        print_status("Fix the issues above before deploying", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)