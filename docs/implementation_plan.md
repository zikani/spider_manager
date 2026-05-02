# Implementation Plan: Spider Manager

## 🎯 Project Overview
Spider Manager is a high-performance, IDM-inspired download manager built with Python and PyQt6. It features multi-segment downloading, global speed limiting, a professional dark/light UI, and a comprehensive management system.

---

## 🏗️ Phase 1: Foundation (Completed)
- [x] **Project Structure**: Organized directory layout (Core, UI, Utils, Plugins).
- [x] **Constants & Config**: Centralized constants and `QSettings` (JSON) integration.
- [x] **Download Engine**: Multi-segment async downloader using `aiohttp` and `aiofiles`.
- [x] **Queue Manager**: Concurrency control, priority-aware scheduling, and async task dispatching.
- [x] **Speed Limiter**: Shared global bandwidth throttling using token-bucket-like sleep logic.
- [x] **Resume Handler**: Hydration of partial tasks from `.part` segment files.
- [x] **Protocol Handler**: URL normalization/validation for HTTP/HTTPS.

## 🎨 Phase 2: UI Shell (Completed)
- [x] **Main Window**: Custom frameless window with draggable title bar and window controls (min, max, close).
- [x] **Menu Bar**: Full IDM-style menu system (File, Edit, View, Downloads, Queue, Tools, Help).
- [x] **Toolbar**: Functional action buttons for Add, Resume, Pause, Cancel, Delete, Settings, and Folder.
- [x] **Category Panel**: Sidebar with real-time download counts per category.
- [x] **Download Table**: Custom `QAbstractTableModel` with `ProgressDelegate` and state icons.
- [x] **Themes**: Production-ready Dark (GitHub) and Light themes with runtime switching.
- [x] **Status Bar**: Live stats for active/paused/completed counts, total speed, disk space, and clock.

## 🚀 Phase 3: Advanced Features (Completed)
- [x] **Speed Graph**: Real-time `QPainter` chart showing the last 60 seconds of performance.
- [x] **Clipboard Monitor**: Background monitoring of system clipboard for automatic URL detection.
- [x] **Preferences Dialog**: Tabbed configuration (General, File Types, Save To, Downloads, Connection, Proxy, Logins, Sounds, Appearance).
- [x] **System Tray**: Tray icon with dynamic speed badge and context menu.
- [x] **Context Menus**: Right-click menus for the download table, category panel, and speed graph.
- [x] **Menu State Management**: Dynamic enabling/disabling of menu actions based on selection.

## 🛠️ Phase 4: Implementation Progress (In-Progress)
- [x] **Task Persistence**: Serializing `DownloadTask` objects to disk (JSON) for persistence across app restarts.
- [x] **Scheduler UI**: Full implementation of the time-window based scheduler dialog.
- [x] **Speed Limiter Dialog**: UI for real-time adjustment of global speed limits.
- [x] **yt-dlp Integration**: Implementation of the video extraction plugin (framework and initial plugin).
- [ ] **Browser Extensions**: Finalizing native messaging host for Chrome/Firefox integration.
- [ ] **Sound System**: Real-time event notifications (complete, failed) using `QSoundEffect`.
- [x] **Batch Download Enhancements**: Multi-URL import validation and categorizing.

## 🧪 Phase 5: Testing & Distribution (Upcoming)
- [ ] **Comprehensive Test Suite**: Expanding `tests/` to cover all core engine edge cases.
- [ ] **Performance Profiling**: Optimizing segment merging and UI refresh rates.
- [ ] **Windows Installer**: Bundling with PyInstaller and NSIS.
- [ ] **Cross-Platform Bundles**: AppImage (Linux) and .app (macOS).
- [ ] **Documentation**: Complete user guide and developer README.
