#!/usr/bin/env python3
"""
PureWebScan - Cross-platform Startup Script
Supports: Windows (PowerShell/CMD), Linux, macOS
"""

import sys
import os
import subprocess
import socket
import platform
from pathlib import Path

# Try to import yaml, if not available, we'll install dependencies first
def load_config():
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARN] Failed to load config.yaml: {e}")
    return {}


def check_python():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"[ERROR] Python 3.10+ required, but found {version.major}.{version.minor}")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def check_port(host, port):
    """Check if port is available (not in use)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.bind((host, port))
        sock.close()
        return True  # Port is available
    except (socket.error, OSError):
        return False  # Port is in use


def ensure_venv():
    """Ensure virtual environment exists and is set up."""
    venv_path = Path("venv")
    is_windows = platform.system() == "Windows"
    python_exec = venv_path / "Scripts" / "python.exe" if is_windows else venv_path / "bin" / "python3"

    # Create venv if not exists
    if not venv_path.exists():
        print("[INFO] Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("[OK] Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to create virtual environment: {e}")
            return None

    # Check if dependencies are installed
    site_packages = None
    if is_windows:
        site_packages = venv_path / "Lib" / "site-packages"
    else:
        # Find site-packages for Linux/macOS
        result = subprocess.run(
            [str(python_exec), "-c", "import site; print(site.getsitepackages()[0])"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            site_packages = Path(result.stdout.strip())

    deps_ok = False
    if site_packages and site_packages.exists():
        deps_ok = (site_packages / "fastapi").exists() and (site_packages / "uvicorn").exists()

    if not deps_ok:
        print("[INFO] Installing dependencies (first run)...")
        pip_exec = venv_path / "Scripts" / "pip.exe" if is_windows else venv_path / "bin" / "pip3"

        try:
            # Upgrade pip first
            subprocess.run([str(pip_exec), "install", "--upgrade", "pip"], check=True, timeout=120)
            # Install requirements
            subprocess.run([str(pip_exec), "install", "-r", "requirements.txt"], check=True, timeout=300)
            print("[OK] Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install dependencies: {e}")
            return None
    else:
        print("[OK] Dependencies already installed")

    return str(python_exec)


def ensure_directories():
    """Ensure required directories exist."""
    for dir_name in ["data", "rules"]:
        path = Path(dir_name)
        if not path.exists():
            path.mkdir(parents=True)
            print(f"[INFO] Created directory: {dir_name}")
        else:
            print(f"[OK] Directory exists: {dir_name}")


def main():
    """Main entry point."""
    # Banner
    print()
    print("=" * 50)
    print("  PureWebScan - Web Fingerprint Scanner")
    print("=" * 50)
    print()

    # Get project root (where this script is located)
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Load configuration
    config = load_config()
    server_config = config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 9933)

    # Check Python
    if not check_python():
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Ensure directories
    ensure_directories()

    # Set up virtual environment
    python_exec = ensure_venv()
    if not python_exec:
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Check port availability from config
    if not check_port(host, port):
        print(f"[WARN] Port {port} ({host}) is already in use!")
        print("Please stop the existing service or change port in config.yaml")
        print(f"Current config: host={host}, port={port}")
        print()

    # Start the application
    print()
    print(f"[INFO] Starting PureWebScan on http://{host}:{port}...")
    print(f"[INFO] Access http://localhost:{port} for UI")
    print(f"[INFO] API docs: http://localhost:{port}/api/docs")
    print(f"[INFO] Press Ctrl+C to stop")
    print()
    print("=" * 50)
    print()

    try:
        # Run the FastAPI application
        subprocess.run([python_exec, "-m", "backend.app.main"])
    except KeyboardInterrupt:
        print()
        print("[INFO] Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
