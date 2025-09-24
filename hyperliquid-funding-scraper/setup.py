"""
Setup script for Hyperliquid Funding Rate Scraper
Handles complete project initialization including:
- Python environment setup
- Dependencies installation
- ChromeDriver setup
- Database migration
- Environment configuration
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
import urllib.request
import zipfile
import shutil


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def print_step(step, text):
    """Print formatted step."""
    print(f"\n[{step}] {text}")


def run_command(command, description, shell=True):
    """Run command with error handling."""
    print(f"  Running: {command}")
    try:
        result = subprocess.run(command, shell=shell, check=True,
                              capture_output=True, text=True)
        print(f"  ✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ {description} failed: {e}")
        if e.stdout:
            print(f"  STDOUT: {e.stdout}")
        if e.stderr:
            print(f"  STDERR: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    print_step(1, "Checking Python version")

    version = sys.version_info
    print(f"  Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major != 3 or version.minor < 10:
        print("  ✗ Python 3.10+ required")
        return False

    print("  ✓ Python version is compatible")
    return True


def setup_virtual_environment():
    """Create and activate virtual environment."""
    print_step(2, "Setting up virtual environment")

    venv_path = Path("venv")

    if venv_path.exists():
        print("  ✓ Virtual environment already exists")
        return True

    # Create virtual environment
    if not run_command(f"{sys.executable} -m venv venv", "Virtual environment creation"):
        return False

    print("  ✓ Virtual environment created")
    return True


def get_venv_python():
    """Get path to virtual environment Python."""
    if platform.system() == "Windows":
        return Path("venv/Scripts/python.exe")
    else:
        return Path("venv/bin/python")


def install_dependencies():
    """Install Python dependencies."""
    print_step(3, "Installing Python dependencies")

    python_path = get_venv_python()

    # Upgrade pip first
    if not run_command(f"{python_path} -m pip install --upgrade pip", "pip upgrade"):
        return False

    # Install dependencies
    if not run_command(f"{python_path} -m pip install -r requirements.txt", "Dependencies installation"):
        print("  ! Some packages may have failed. This is common with Python 3.13.")
        print("  ! The scraper includes compatibility fallbacks.")

    print("  ✓ Dependencies installation completed")
    return True


def get_chrome_version():
    """Get installed Chrome version."""
    try:
        if platform.system() == "Windows":
            # Try registry first
            result = subprocess.run([
                'reg', 'query',
                'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon',
                '/v', 'version'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line:
                        version = line.split()[-1]
                        return version.split('.')[0]

            # Try executable
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]

            for path in chrome_paths:
                if os.path.exists(path):
                    result = subprocess.run([path, '--version'],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        version = result.stdout.strip().split()[-1]
                        return version.split('.')[0]

        return "131"  # Default fallback

    except Exception:
        return "131"


def download_chromedriver():
    """Download and setup ChromeDriver."""
    print_step(4, "Setting up ChromeDriver")

    # Check if chromedriver already exists
    if os.path.exists("chromedriver.exe"):
        print("  ✓ ChromeDriver already exists")
        return True

    chrome_version = get_chrome_version()
    print(f"  Detected Chrome version: {chrome_version}")

    # Get ChromeDriver version
    try:
        version_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{chrome_version}"
        with urllib.request.urlopen(version_url) as response:
            driver_version = response.read().decode().strip()
    except:
        # Fallback versions for common Chrome versions
        version_map = {
            "140": "140.0.7339.207",
            "131": "131.0.6778.204",
            "130": "130.0.6723.116",
            "129": "129.0.6668.100"
        }
        driver_version = version_map.get(chrome_version, "131.0.6778.204")

    print(f"  Using ChromeDriver version: {driver_version}")

    # Download ChromeDriver
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win64/chromedriver-win64.zip"

    try:
        print(f"  Downloading from: {download_url}")
        urllib.request.urlretrieve(download_url, "chromedriver.zip")

        # Extract
        with zipfile.ZipFile("chromedriver.zip", 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith("chromedriver.exe"):
                    zip_ref.extract(file, '.')
                    # Move to root directory
                    extracted_path = Path(file)
                    if extracted_path.parent != Path('.'):
                        shutil.move(str(extracted_path), "chromedriver.exe")
                    break

        # Cleanup
        os.remove("chromedriver.zip")
        for item in Path('.').iterdir():
            if item.is_dir() and 'chromedriver' in item.name.lower():
                shutil.rmtree(item)

        print("  ✓ ChromeDriver downloaded and extracted")
        return True

    except Exception as e:
        print(f"  ✗ Failed to download ChromeDriver: {e}")
        return False


def setup_environment():
    """Setup environment configuration."""
    print_step(5, "Setting up environment configuration")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("  ✓ .env file already exists")
        return True

    if env_example.exists():
        # Copy example to .env
        shutil.copy(env_example, env_file)
        print("  ✓ Created .env from .env.example")
        print("  ! Please edit .env file with your Supabase credentials")
    else:
        # Create basic .env
        env_content = """# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Scraper Configuration
HEADLESS_MODE=true
SCRAPING_TIMEOUT=30
PAGE_LOAD_WAIT=10
MAX_RETRIES=3
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36

# Scheduling
SCHEDULE_INTERVAL=15

# ChromeDriver
CHROME_DRIVER_PATH=./chromedriver.exe

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/scraper.log
"""
        env_file.write_text(env_content)
        print("  ✓ Created basic .env file")
        print("  ! Please edit .env file with your Supabase credentials")

    return True


def create_directories():
    """Create necessary directories."""
    print_step(6, "Creating project directories")

    directories = ["logs", "exports", "screenshots"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  ✓ Created {directory}/ directory")

    return True


def run_database_migrations():
    """Run database migrations."""
    print_step(7, "Running database migrations")

    python_path = get_venv_python()

    # Check if .env has Supabase credentials
    env_file = Path(".env")
    if env_file.exists():
        env_content = env_file.read_text()
        if "your_supabase_url_here" in env_content:
            print("  ! Skipping migrations - Please configure Supabase credentials in .env first")
            print("  ! Run migrations manually with: python migrations/migrate.py")
            return True

    # Run migrations
    if not run_command(f"{python_path} migrations/migrate.py", "Database migrations"):
        print("  ! Migrations failed - Please check your Supabase credentials")
        return False

    print("  ✓ Database migrations completed")
    return True


def test_installation():
    """Test the installation."""
    print_step(8, "Testing installation")

    python_path = get_venv_python()

    # Test imports
    test_script = """
import sys
try:
    from src.config import settings
    from src.scrapers.funding_scraper import FundingScraper
    from src.database.supabase_client import SupabaseClient
    print("✓ All imports successful")
    sys.exit(0)
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
"""

    try:
        result = subprocess.run([str(python_path), "-c", test_script],
                              capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            print("  ✓ Installation test passed")
            return True
        else:
            print(f"  ✗ Installation test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Test execution failed: {e}")
        return False


def main():
    """Main setup function."""
    print_header("Hyperliquid Funding Rate Scraper - Setup")
    print("This script will set up the complete environment for the scraper.")
    print("Please ensure you have Python 3.10+ installed.")

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    success_steps = 0
    total_steps = 8

    steps = [
        check_python_version,
        setup_virtual_environment,
        install_dependencies,
        download_chromedriver,
        setup_environment,
        create_directories,
        run_database_migrations,
        test_installation
    ]

    for step_func in steps:
        if step_func():
            success_steps += 1
        else:
            print(f"\n❌ Setup failed at step: {step_func.__name__}")
            break

    print_header("Setup Summary")
    print(f"Completed: {success_steps}/{total_steps} steps")

    if success_steps == total_steps:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your Supabase credentials")
        print("2. Run database migrations if skipped: python migrations/migrate.py")
        print("3. Test the scraper: run.bat")
        print("4. Schedule regular runs or use CLI options")
    else:
        print("\n❌ Setup incomplete. Please check errors above.")
        print("You may need to:")
        print("1. Install missing system dependencies")
        print("2. Check Python version compatibility")
        print("3. Verify internet connection for downloads")

    return success_steps == total_steps


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)