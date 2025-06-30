# Setup script for CI/CD development environment
# Run with: python setup_dev.py
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    else:
        print(f"✅ Success: {description}")
        return True


def main():
    """Setup development environment."""
    print("Setting up CI/CD Development Environment...")
    print("=" * 60)

    # Check if we're in the right directory
    if not Path('plugins/stdev_calculator.py').exists():
        print("Error: Run this script from the project root directory")
        sys.exit(1)

    commands = [
        ("pip install -r requirements.txt", "Install project dependencies"),
        ("pip install -r requirements-dev.txt", "Install development dependencies"),
        ("pre-commit install", "Install pre-commit hooks"),
        ("python -m pytest --version", "Verify pytest installation"),
        ("black --version", "Verify black installation"),
        ("flake8 --version", "Verify flake8 installation"),
    ]

    success_count = 0
    total_count = len(commands)

    for cmd, description in commands:
        if run_command(cmd, description):
            success_count += 1
        print()  # Add spacing

    print("=" * 60)
    print(f"Setup complete: {success_count}/{total_count} steps successful")

    if success_count == total_count:
        print("\n🎉 Development environment setup complete!")
        print("\nNext steps:")
        print("1. Run 'python run_tests.py' to test your setup")
        print("2. Make changes to your code")
        print("3. Pre-commit hooks will run automatically on commit")
        print("4. Push to trigger the full CI/CD pipeline")
    else:
        print("\n⚠️ Some setup steps failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
