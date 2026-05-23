"""
Automated Windows build script for Spider Manager.
Run with: python scripts/build_windows.py
"""
import subprocess
import shutil
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run command and check result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    print(result.stdout)
    return result


def build_windows():
    """Build Windows installer."""
    root = Path(__file__).parent.parent
    
    print("Cleaning previous builds...")
    if (root / "build").exists():
        shutil.rmtree(root / "build")
    if (root / "dist").exists():
        try:
            shutil.rmtree(root / "dist")
        except PermissionError:
            print("Warning: Could not remove dist folder (file may be in use)")
            print("Please close SpiderManager.exe if it's running and try again")
            return
    
    print("Building with PyInstaller...")
    run_command("pyinstaller spider_manager.spec", cwd=root)
    
    if not (root / "dist" / "SpiderManager.exe").exists():
        raise RuntimeError("PyInstaller build failed - executable not found")
    
    print("PyInstaller build successful!")
    
    try:
        print("Building NSIS installer...")
        run_command("makensis installer.nsi", cwd=root)
        
        installer_path = root / "SpiderManager-1.0.0-Setup.exe"
        if installer_path.exists():
            print(f"NSIS installer created: {installer_path}")
        else:
            print("Warning: NSIS installer not found (may need to check output)")
    except Exception as e:
        print(f"NSIS build skipped or failed: {e}")
        print("You can build the installer manually with: makensis installer.nsi")
    
    print("\nBuild complete!")
    print(f"Executable: {root / 'dist' / 'SpiderManager.exe'}")
    print(f"Installer: {root / 'SpiderManager-1.0.0-Setup.exe'}")


if __name__ == "__main__":
    build_windows()
