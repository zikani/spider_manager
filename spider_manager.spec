# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Spider Manager.
Run with: pyinstaller spider_manager.spec
"""
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('config', 'config'),
        ('ui', 'ui'),
        ('core', 'core'),
        ('utils', 'utils'),
        ('plugins', 'plugins'),
        ('extension', 'extension'),
    ] + collect_data_files('config') + collect_data_files('ui') + collect_data_files('core') + collect_data_files('utils') + collect_data_files('plugins'),
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'qasync',
        'aiohttp',
        'aiofiles',
        'yt_dlp',
        'pyperclip',
        'psutil',
        'humanize',
        'mutagen',
        'Pillow',
        'cryptography',
        'rich',
        'logging',
        'logging.handlers',
    ] + collect_submodules('utils') + collect_submodules('config') + collect_submodules('core') + collect_submodules('ui') + collect_submodules('plugins'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'PyQt5',
        'PySide2',
        'PySide6',
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/brand/spider_logo.ico' if Path('resources/icons/brand/spider_logo.ico').exists() else None,
)
