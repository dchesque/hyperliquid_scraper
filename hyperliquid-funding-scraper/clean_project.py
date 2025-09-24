"""Script to clean unnecessary files from the project."""

import os
import shutil
from pathlib import Path


def clean_project():
    """Remove unnecessary files and keep only essentials."""

    project_root = Path(".")

    print("============================================================")
    print("Limpando arquivos desnecessários do projeto")
    print("============================================================")

    # Files to remove
    files_to_remove = [
        "fix_dependencies.bat",
        "fix_chromedriver.bat",
        "fix_chromedriver_v140.bat",
        "install_full.bat",
        "install_py313.bat",
        "setup.bat",
        "download_chromedriver.py",
        "requirements-minimal.txt",
        "requirements_py313.txt",
        "chromedriver.zip",
        "cleanup.bat",  # Remove the bat version too
    ]

    # Directories to remove
    dirs_to_remove = [
        "chromedriver-win64",
        "chromedriver-win32",
    ]

    # Remove files
    print("\nRemoving temporary installation files...")
    for file_name in files_to_remove:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  [OK] Removed {file_name}")
            except Exception as e:
                print(f"  [ERROR] Failed to remove {file_name}: {e}")

    # Remove directories
    print("\nRemoving temporary directories...")
    for dir_name in dirs_to_remove:
        dir_path = project_root / dir_name
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"  [OK] Removed {dir_name}/")
            except Exception as e:
                print(f"  [ERROR] Failed to remove {dir_name}/: {e}")

    # Clean Python cache
    print("\nCleaning Python cache files...")
    cache_patterns = [
        "__pycache__",
        "src/__pycache__",
        "src/**/__pycache__",
        "tests/__pycache__",
        "*.pyc",
        "*.pyo",
    ]

    def remove_pycache(directory):
        """Recursively remove __pycache__ directories."""
        for root, dirs, files in os.walk(directory):
            if '__pycache__' in dirs:
                cache_dir = os.path.join(root, '__pycache__')
                try:
                    shutil.rmtree(cache_dir)
                    print(f"  [OK] Removed {cache_dir}")
                except Exception as e:
                    print(f"  [ERROR] Failed to remove {cache_dir}: {e}")

    remove_pycache(".")

    # Clean screenshots (keep directory but remove files)
    screenshots_dir = project_root / "screenshots"
    if screenshots_dir.exists():
        print("\nCleaning test screenshots...")
        for file in screenshots_dir.glob("*.png"):
            try:
                file.unlink()
                print(f"  [OK] Removed {file.name}")
            except Exception as e:
                print(f"  [ERROR] Failed to remove {file.name}: {e}")

    # Remove alternative data processor (keep only the compat version)
    old_processor = project_root / "src" / "utils" / "data_processor.py"
    if old_processor.exists():
        print("\nRemoving old data processor...")
        try:
            old_processor.unlink()
            print("  [OK] Removed old data_processor.py")

            # Rename the compat version to be the main one
            compat_processor = project_root / "src" / "utils" / "data_processor_compat.py"
            if compat_processor.exists():
                compat_processor.rename(old_processor)
                print("  [OK] Renamed data_processor_compat.py to data_processor.py")

                # Update the import in __init__.py
                init_file = project_root / "src" / "utils" / "__init__.py"
                if init_file.exists():
                    content = init_file.read_text()
                    new_content = content.replace(
                        "# Try to import the compatible version first (works with Python 3.13)\ntry:\n    from .data_processor_compat import DataProcessor\nexcept ImportError:\n    # Fallback to original if compat version has issues\n    from .data_processor import DataProcessor",
                        "from .data_processor import DataProcessor"
                    )
                    init_file.write_text(new_content)
                    print("  [OK] Updated utils/__init__.py")
        except Exception as e:
            print(f"  [ERROR] Failed to clean data processor: {e}")

    # Remove alternative supabase client
    old_supabase = project_root / "src" / "database" / "supabase_client.py"
    compat_supabase = project_root / "src" / "database" / "supabase_client_compat.py"
    if compat_supabase.exists():
        print("\nCleaning up database clients...")
        try:
            if old_supabase.exists():
                old_supabase.unlink()
                print("  [OK] Removed old supabase_client.py")

            compat_supabase.rename(old_supabase)
            print("  [OK] Renamed supabase_client_compat.py to supabase_client.py")

            # Update the import in __init__.py
            init_file = project_root / "src" / "database" / "__init__.py"
            if init_file.exists():
                content = init_file.read_text()
                new_content = content.replace(
                    "# Try to import the compatible version first\ntry:\n    from .supabase_client_compat import SupabaseClient\nexcept ImportError:\n    # Fallback to original if compat version fails\n    from .supabase_client import SupabaseClient",
                    "from .supabase_client import SupabaseClient"
                )
                init_file.write_text(new_content)
                print("  [OK] Updated database/__init__.py")
        except Exception as e:
            print(f"  [ERROR] Failed to clean database clients: {e}")

    print("\n============================================================")
    print("ARQUIVOS ESSENCIAIS MANTIDOS:")
    print("============================================================")

    essential_files = [
        "src/ (código principal)",
        "migrations/ (banco de dados)",
        "tests/ (testes)",
        "requirements.txt (dependências)",
        ".env.example (template de configuração)",
        ".gitignore",
        "README.md",
        "run.bat (executor principal)",
        "chromedriver.exe (necessário para scraping)",
        "logs/ (diretório de logs)",
        "exports/ (diretório de exports)",
        "screenshots/ (diretório de screenshots)"
    ]

    for item in essential_files:
        print(f"  [OK] {item}")

    print("\n============================================================")
    print("Limpeza concluída com sucesso!")
    print("============================================================")

    # Show final project structure
    print("\nEstrutura final do projeto:")
    print("hyperliquid-funding-scraper/")
    for root, dirs, files in os.walk("."):
        # Skip hidden and cache directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        level = root.replace(".", "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = "  " * (level + 1)
        for file in files:
            if not file.startswith('.') and not file.endswith('.pyc'):
                print(f"{subindent}{file}")


if __name__ == "__main__":
    clean_project()