"""
Tests for start_server.sh script.

This test validates the startup script functionality without actually starting the server.
"""
import subprocess
import sys
from pathlib import Path


def test_start_server_help():
    """Test that start_server.sh --help works correctly."""
    script_path = Path(__file__).parent.parent / "start_server.sh"
    assert script_path.exists(), "start_server.sh not found"

    result = subprocess.run(
        [str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert result.returncode == 0
    assert "PyFluff Server Startup Script" in result.stdout
    assert "--host HOST" in result.stdout
    assert "--port PORT" in result.stdout
    assert "--reload" in result.stdout
    assert "Examples:" in result.stdout


def test_start_server_exists_and_executable():
    """Test that start_server.sh exists and is executable."""
    script_path = Path(__file__).parent.parent / "start_server.sh"
    assert script_path.exists(), "start_server.sh not found"
    assert script_path.stat().st_mode & 0o111, "start_server.sh is not executable"


def test_systemd_service_file_exists():
    """Test that pyfluff.service file exists."""
    service_path = Path(__file__).parent.parent / "pyfluff.service"
    assert service_path.exists(), "pyfluff.service not found"

    # Validate basic service file structure
    content = service_path.read_text()
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content
    assert "Description=PyFluff" in content
    assert "ExecStart=" in content


def test_readme_documents_start_script():
    """Test that README.md documents the start script."""
    readme_path = Path(__file__).parent.parent / "README.md"
    assert readme_path.exists(), "README.md not found"

    content = readme_path.read_text()
    assert "start_server.sh" in content
    assert "./start_server.sh" in content
    assert "systemd" in content.lower() or "service" in content.lower()


if __name__ == "__main__":
    # Run tests manually if executed directly
    print("Running start_server.sh tests...")

    try:
        test_start_server_exists_and_executable()
        print("✓ Script exists and is executable")
    except AssertionError as e:
        print(f"✗ Script executable test failed: {e}")
        sys.exit(1)

    try:
        test_start_server_help()
        print("✓ Help message works")
    except Exception as e:
        print(f"✗ Help test failed: {e}")
        sys.exit(1)

    try:
        test_systemd_service_file_exists()
        print("✓ Systemd service file exists and is valid")
    except AssertionError as e:
        print(f"✗ Service file test failed: {e}")
        sys.exit(1)

    try:
        test_readme_documents_start_script()
        print("✓ README.md documents the script")
    except AssertionError as e:
        print(f"✗ README documentation test failed: {e}")
        sys.exit(1)

    print("\nAll tests passed!")
