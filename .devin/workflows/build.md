---
description: Build Spider Manager for Windows
---

# Build Workflow

This workflow guides you through building Spider Manager for Windows.

## Prerequisites

- Python 3.11+ installed
- PyInstaller installed: `pip install pyinstaller`
- NSIS (Nullsoft Scriptable Install System) installed for installer creation
- All dependencies installed: `pip install -r requirements.txt`

## Steps

1. **Clean previous builds**
   ```bash
   // turbo
   rmdir /s /q build dist 2>nul || true
   ```

2. **Install/update dependencies**
   ```bash
   pip install -r requirements.txt --upgrade
   pip install pyinstaller
   ```

3. **Generate resources**
   ```bash
   python scripts/convert_svg_to_ico.py
   python -c "from PyQt6.QtCore import QResource; from PyQt6.QtGui import QResourceFile; import os; os.system('pyrcc5 resources/icons/icons.qrc -o resources/icons/icons_rc.py')"
   ```

4. **Build executable with PyInstaller**
   ```bash
   pyinstaller spider_manager.spec --clean
   ```
   This creates the executable in the `dist/` directory.

5. **Verify the build**
   - Check that `dist/Spider Manager/` directory exists
   - Verify `Spider Manager.exe` is present
   - Run the executable to test basic functionality

6. **Create installer with NSIS**
   ```bash
   "C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
   ```
   This creates the installer in the project root.

7. **Test the installer**
   - Run the generated installer
   - Install to a test location
   - Verify the application launches correctly
   - Test key features (downloads, settings, etc.)

8. **Package for distribution**
   - The final installer is ready in the project root
   - Name format: `SpiderManager-Setup-X.Y.Z.exe`

## Troubleshooting

**Build fails with missing module errors:**
- Add missing modules to `hiddenimports` in `spider_manager.spec`
- Re-run PyInstaller

**UI resources not loading:**
- Ensure icons were generated with pyrcc5
- Check that resources are included in the spec file

**Installer fails to build:**
- Verify NSIS is installed and in PATH
- Check installer.nsi for correct paths
- Ensure all files referenced in installer.nsi exist

**Executable crashes on launch:**
- Check console output for errors
- Verify all dependencies are bundled
- Test with `--debug` flag in PyInstaller spec
