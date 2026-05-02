# Spider Manager — Project Planning

## Overview
Spider Manager is a professional internet download manager built with Python 3.11+ and PyQt6.
Inspired by IDM (Internet Download Manager), it provides multi-segment parallel downloading,
browser integration, scheduling, and a polished dark UI.

**🎯 Current Status: ~85% Complete - Production Ready Core Features**

---

## Architecture

```
spider_manager/
├── main.py                      # Entry point, QApplication setup
├── config/
│   ├── constants.py             # App-wide constants, colors, limits
│   └── settings.py              # User preferences (JSON-backed QSettings)
├── core/
│   ├── download_engine.py       # Async multi-segment downloader (aiohttp)
│   ├── queue_manager.py         # Concurrency control, priority queue
│   ├── scheduler.py             # Time-based scheduling (start/stop windows)
│   ├── speed_limiter.py         # Global/per-task bandwidth throttling
│   ├── resume_handler.py        # .part file detection and resumption
│   ├── segment_downloader.py    # Byte-range request handler
│   └── protocol_handler.py      # HTTP/HTTPS/FTP/magnet dispatch
├── ui/
│   ├── main_window.py           # QMainWindow shell, layout orchestration
│   ├── tray_icon.py             # System tray with speed badge
│   ├── widgets/
│   │   ├── download_table.py    # QTableView with custom model
│   │   ├── progress_delegate.py # Custom progress bar cell renderer
│   │   ├── speed_graph.py       # Real-time QPainter speed chart
│   │   ├── category_panel.py    # Left sidebar category tree
│   │   ├── toolbar.py           # Main action toolbar
│   │   └── status_bar.py        # Speed, active count, disk space
│   ├── dialogs/
│   │   ├── add_download.py      # URL input + options dialog
│   │   ├── batch_download.py    # Multi-URL / text list importer
│   │   ├── preferences.py       # Settings dialog (tabbed)
│   │   ├── scheduler_dialog.py  # Time window scheduler UI
│   │   └── about.py             # About dialog
│   └── themes/
│       ├── dark_theme.py        # GitHub-dark QSS stylesheet
│       ├── light_theme.py       # Light QSS stylesheet
│       └── theme_manager.py     # Runtime theme switching
├── utils/
│   ├── file_utils.py            # Path sanitization, disk space checks
│   ├── network_utils.py         # IP resolution, proxy helpers
│   ├── url_parser.py            # URL normalization, filename extraction
│   ├── mime_detector.py         # Content-Type → category mapping
│   ├── clipboard_monitor.py     # Watches clipboard for URLs
│   └── logger.py                # Structured logging with rotation
├── plugins/
│   ├── plugin_base.py           # Plugin ABC
│   ├── browser_extension.py     # Native messaging host (Chrome/Firefox)
│   └── yt_dlp_plugin.py         # Video/audio extraction via yt-dlp
├── resources/
│   ├── icons/                   # SVG icons (categories, actions)
│   └── sounds/                  # Completion chime (optional)
└── tests/
    ├── test_engine.py
    ├── test_queue.py
    └── test_utils.py
```

---

## Development Phases

### Phase 1 — Foundation (Week 1–2) ✅ COMPLETE
- [x] Project structure scaffold
- [x] Constants and config system
- [x] Core download engine (async, multi-segment)
- [x] Queue manager with concurrency control
- [x] Protocol handler (HTTP/HTTPS)
- [x] Resume handler (.part file detection)
- [x] Speed limiter implementation
- [x] Basic unit tests

### Phase 2 — UI Shell (Week 2–3) ✅ COMPLETE
- [x] MainWindow with toolbar, sidebar, table
- [x] Dark theme QSS (complete)
- [x] Light theme QSS (complete)
- [x] Add Download dialog
- [x] Download table with custom model
- [x] Progress bar delegate
- [x] Status bar
- [x] System tray icon
- [x] Batch download dialog
- [x] Enhanced title bar with window controls
- [x] Comprehensive menu bar with all features

### Phase 3 — Core Features (Week 3–4) ✅ COMPLETE
- [x] Speed graph widget (QPainter real-time)
- [x] Category filtering (sidebar)
- [x] Clipboard monitor (auto-detect URLs)
- [x] Preferences dialog (IDM-style with all tabs)
- [x] System tray icon
- [x] Batch download dialog
- [x] Context menus (download table, categories, speed graph)
- [x] Menu state management (enable/disable based on selection)
- [x] Recent files tracking
- [x] Window state management

### Phase 4 — Advanced Features (Week 5–6) 🔄 IN PROGRESS
- [x] Speed limiter (global + per-task)
- [x] Scheduler (time windows)
- [ ] yt-dlp plugin (video download) - TODO
- [ ] Browser extension (native messaging) - TODO
- [x] Light theme + theme switcher
- [ ] Sound notifications - TODO
- [x] Queue management (move, sort, shuffle)
- [x] Advanced download controls (restart failed, clear operations)

### Phase 5 — Polish & Distribution (Week 7–8) 📋 PENDING
- [ ] Complete test suite
- [ ] Windows installer (PyInstaller + NSIS)
- [ ] Linux AppImage / .deb
- [ ] macOS .app bundle
- [ ] README + user documentation
- [ ] Performance profiling

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Async runtime | asyncio + aiohttp | Non-blocking I/O, PyQt6 QThread bridge |
| Segment merging | Sequential file concat | Simple, reliable, cross-platform |
| Settings storage | QSettings (JSON) | Qt-native, no extra deps |
| Theme system | QSS stylesheets | Qt-native, runtime switchable |
| Packaging | PyInstaller | Single binary, no Python needed |
| Testing | pytest + pytest-qt | Industry standard, async support |

---

## UI Layout (Main Window) ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────┐
│ 🕷️ Spider Manager           [🟡] [🟢] [🔴]             │
├─────────────────────────────────────────────────────────┤
│ Menu: File Edit View Downloads Queue Tools Help          │
├─────────────────────────────────────────────────────────┤
│  [+ Add] [▶ Resume] [⏸ Pause] [✕ Cancel] [🗑 Delete]  │
├────────────┬────────────────────────────────────────────┤
│ CATEGORIES │ # │ Filename │ Size │ Progress │ Speed │ETA│
│            ├────────────────────────────────────────────┤
│ ▾ All (12) │ ▶ │ ubuntu.. │3.2GB │ ████░░ 64%│4.2M/s│2m│
│   Video(4) │ ⏸ │ movie.. │1.8GB │ ██░░░░ 30%│  — │  — │
│   Audio(2) │ ✓ │ song.mp3 │18MB  │ ██████100%│  ✓ │done│
│   Docs (3) │ ! │ file.zip │500MB │ ████░░ 40%│Error│    │
│   Archive  │   │          │      │            │    │    │
│   Programs │   │          │      │            │    │    │
│   Other    │   │          │      │            │    │    │
├────────────┴────────────────────────────────────────────┤
│  ▁▂▃▅▄▆▇▆▅▄  Speed Graph (last 60s)                   │
├─────────────────────────────────────────────────────────┤
│  ↓ 4.2 MB/s  |  3 active  |  Disk: 142 GB free        │
└─────────────────────────────────────────────────────────┘
```

**Enhanced Features Implemented:**
- **Title Bar**: Custom frameless window with spider icon, window state indicator, and functional controls
- **Menu Bar**: Complete IDM-style menus with keyboard shortcuts, context menus, and state management
- **Context Menus**: Right-click menus for download table, categories, and speed graph
- **Dynamic UI**: Menu items enable/disable based on selection, window state updates
- **Theme System**: Dark/Light themes with runtime switching
- **Professional Polish**: Hover effects, proper spacing, and consistent styling

---

## Current Implementation Status

### ✅ **Core Architecture Complete**
- **Async Download Engine**: Multi-segment downloads with aiohttp
- **Queue Manager**: Concurrency control, priority queue, advanced operations
- **Speed Limiter**: Global bandwidth throttling
- **Protocol Handler**: HTTP/HTTPS support
- **Resume Handler**: .part file detection and resumption
- **Scheduler**: Time-based download windows

### ✅ **UI Framework Complete**
- **Frameless Main Window**: Custom title bar with window controls
- **Professional Menu Bar**: Complete IDM-style menus with all features
- **Context Menus**: Right-click menus for all UI areas
- **Dynamic State Management**: Menu items enable/disable based on selection
- **Theme System**: Dark/Light themes with runtime switching
- **Advanced Widgets**: Download table, speed graph, category panel, status bar

### ✅ **Dialog System Complete**
- **Add Download Dialog**: URL input with advanced options
- **Batch Download Dialog**: Multi-URL import functionality
- **Preferences Dialog**: IDM-style tabbed interface with all settings
- **About Dialog**: Application information
- **System Tray Integration**: Minimize to tray with speed badge

### ✅ **Advanced Features**
- **Clipboard Monitor**: Automatic URL detection
- **Queue Management**: Move, sort, shuffle operations
- **Download Controls**: Start/pause/cancel/remove with keyboard shortcuts
- **Recent Files**: Track recently downloaded files
- **Window State Management**: Dynamic title updates and state indicators

### 🔄 **In Progress**
- **yt-dlp Plugin**: Video/audio extraction (framework exists)
- **Browser Extension**: Native messaging host (framework exists)
- **Sound Notifications**: Event sound system (framework exists)

### 📋 **Remaining Tasks**
- **Complete Test Suite**: Comprehensive testing coverage
- **Packaging**: Windows installer, Linux AppImage, macOS bundle
- **Documentation**: User guides and API documentation
- **Performance Optimization**: Profiling and optimization

---

## Data Flow

```
User clicks "Add Download"
        ↓
AddDownloadDialog (url, path, options)
        ↓
DownloadEngine.probe(url) → file metadata
        ↓
QueueManager.add(task)
        ↓
asyncio event loop dispatches up to N concurrent
        ↓
DownloadEngine.start(task)
  ├── _plan_segments() → N DownloadSegment objects
  ├── asyncio.gather(*[_download_segment(seg) for seg])
  │     └── aiohttp byte-range GET → write .partN files
  └── _merge_segments() → final file
        ↓
QueueManager notified → UI updated via Qt signals
```
