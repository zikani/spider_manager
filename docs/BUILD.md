# Spider Manager Build Documentation

## Building from Source

### Prerequisites

- Python 3.11 or higher
- pip
- git
- PyInstaller (for Windows builds)
- NSIS (for Windows installer)
- ffmpeg (for video/audio processing)

### Development Build

```bash
# Clone repository
git clone https://github.com/zikani/spider-manager.git
cd spider_manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Windows Installer Build

### Step 1: Install Build Tools

```bash
# Install PyInstaller
pip install pyinstaller

# Install NSIS from https://nsis.sourceforge.io/
# Add NSIS to your PATH
```

### Step 2: Create PyInstaller Spec File

Create `spider_manager.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('config', 'config'),
        ('ui/themes', 'ui/themes'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'qasync',
        'aiohttp',
        'aiofiles',
        'yt_dlp',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'numpy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SpiderManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/spider_logo.ico',
)
```

### Step 3: Build with PyInstaller

```bash
# Build executable
pyinstaller spider_manager.spec

# Output will be in dist/SpiderManager.exe
```

### Step 4: Create NSIS Installer Script

Create `installer.nsi`:

```nsis
!define APP_NAME "Spider Manager"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Spider Manager Team"
!define APP_EXE "SpiderManager.exe"

Name "${APP_NAME}"
OutFile "SpiderManager-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\Spider Manager"
InstallDirRegKey HKLM "Software\SpiderManager" "InstallLocation"
RequestExecutionLevel admin

; Interface settings
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "resources\icons\spider_logo.ico"
!define MUI_UNICON "resources\icons\spider_logo.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

Section "Main Files" SEC01
  SetOutPath "$INSTDIR"
  File /r "dist\SpiderManager\*"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\Spider Manager"
  CreateShortCut "$SMPROGRAMS\Spider Manager\Spider Manager.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortCut "$SMPROGRAMS\Spider Manager\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortCut "$DESKTOP\Spider Manager.lnk" "$INSTDIR\${APP_EXE}"
  
  ; Register file associations
  WriteRegStr HKCR ".spider" "" "SpiderManager.Download"
  WriteRegStr HKCR "SpiderManager.Download" "" "Spider Manager Download"
  WriteRegStr HKCR "SpiderManager.Download\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
  
  ; Write registry keys
  WriteRegStr HKLM "Software\SpiderManager" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\SpiderManager" "Version" "${APP_VERSION}"
SectionEnd

Section "Uninstall"
  ; Remove files and directories
  RMDir /r "$INSTDIR"
  RMDir /r "$SMPROGRAMS\Spider Manager"
  Delete "$DESKTOP\Spider Manager.lnk"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\SpiderManager"
  DeleteRegKey HKCR ".spider"
  DeleteRegKey HKCR "SpiderManager.Download"
SectionEnd
```

### Step 5: Build NSIS Installer

```bash
# Build installer
makensis installer.nsi

# Output: SpiderManager-1.0.0-Setup.exe
```

## Dependency Management

### Updating Requirements

```bash
# Update requirements.txt
pip freeze > requirements.txt

# Or manually update specific packages
pip install --upgrade PyQt6
pip install --upgrade yt-dlp
```

### Vendoring Dependencies

For offline builds, vendor dependencies:

```bash
# Download all packages to vendor directory
pip download -r requirements.txt -d vendor/

# Install from vendor directory
pip install --no-index --find-links=vendor/ -r requirements.txt
```

## Code Signing (Optional)

### Windows Code Signing

```bash
# Sign the executable
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist/SpiderManager.exe

# Sign the installer
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com SpiderManager-1.0.0-Setup.exe
```

## Automated Build Script

Create `scripts/build_windows.py`:

```python
"""
Automated Windows build script.
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
    return result

def build_windows():
    """Build Windows installer."""
    root = Path(__file__).parent.parent
    
    # Clean previous builds
    if (root / "build").exists():
        shutil.rmtree(root / "build")
    if (root / "dist").exists():
        shutil.rmtree(root / "dist")
    
    # Run PyInstaller
    print("Building with PyInstaller...")
    run_command("pyinstaller spider_manager.spec", cwd=root)
    
    # Run NSIS
    print("Building NSIS installer...")
    run_command("makensis installer.nsi", cwd=root)
    
    print("Build complete!")

if __name__ == "__main__":
    build_windows()
```

Run the build script:

```bash
python scripts/build_windows.py
```

## Testing the Build

### Test Executable

```bash
# Run the built executable
dist/SpiderManager/SpiderManager.exe
```

### Test Installer

```bash
# Run installer
SpiderManager-1.0.0-Setup.exe

# Verify installation
# Check Start Menu shortcuts
# Check Desktop shortcut
# Test file associations
```

## Troubleshooting

### PyInstaller Issues

**Missing imports:**
```python
# Add to hiddenimports in spec file
hiddenimports=['module.name']
```

**Missing data files:**
```python
# Add to datas in spec file
datas=[('source_dir', 'target_dir')]
```

**Large executable size:**
```python
# Use UPX compression
upx=True

# Exclude unnecessary modules
excludes=['tkinter', 'matplotlib']
```

### NSIS Issues

**Path issues:**
- Use forward slashes in paths
- Use `$INSTDIR` for install directory
- Use `$PROGRAMFILES` for Program Files

**Registry permissions:**
- Use `RequestExecutionLevel admin` for registry access
- Test on clean Windows installation

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `config/constants.py`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Build Windows installer
- [ ] Test installer on clean Windows
- [ ] Code sign executable and installer
- [ ] Create GitHub release
- [ ] Upload installer to release
- [ ] Update documentation
- [ ] Tag release in git

## Cross-Platform Builds (Future)

### Linux (AppImage)

```bash
# Install dependencies
sudo apt install python3-pip python3-venv

# Build with PyInstaller
pyinstaller spider_manager_linux.spec

# Create AppImage
wget https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage dist/SpiderManager SpiderManager.AppImage
```

### macOS (.app)

```bash
# Build with PyInstaller
pyinstaller spider_manager_mac.spec

# Create .app bundle
# Use platypus or manual bundle creation
```
