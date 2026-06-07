# Spider Manager User Guide

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Features](#features)
- [Browser Extension Setup](#browser-extension-setup)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Installation

### Windows Installer
1. Download the latest Spider Manager installer from the releases page
2. Run the installer and follow the setup wizard
3. Launch Spider Manager from the Start menu or desktop shortcut

### From Source
```bash
# Clone the repository
git clone https://github.com/zikani/spider-manager.git
cd spider_manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Quick Start

1. **Add a Download**
   - Click the "Add" button in the toolbar
   - Paste a URL into the dialog
   - Choose save location and click "Download"

2. **Monitor Progress**
   - View download progress in the main table
   - Check the speed graph for real-time performance
   - Monitor status bar for overall statistics

3. **Manage Downloads**
   - Pause/Resume downloads using toolbar buttons
   - Cancel downloads you no longer need
   - Delete completed downloads from the list

## Features

### Multi-Segment Downloading
- Automatically splits files into multiple segments for faster downloads
- Configurable segment count (1-32 segments)
- Intelligent segment sizing based on file size

### Speed Limiting
- Set global speed limits to manage bandwidth
- Real-time speed monitoring with graph
- Per-download speed control

### Scheduling
- Schedule downloads for specific time windows
- Set start and end times for automatic downloading
- Useful for off-peak hours or metered connections

### Browser Integration
- Chrome and Firefox extension support
- Automatic URL capture from browser
- One-click download from browser context menu

### Video/Audio Support
- yt-dlp integration for video sites (YouTube, Vimeo, etc.)
- HLS/DASH streaming support
- Automatic format selection

### File Categorization
- Automatic categorization by file type
- Category panel for easy filtering
- Custom save paths per category

### Sound Notifications
- Audio alerts for download completion
- Customizable sound events
- Volume control

### System Tray
- Minimize to system tray
- Speed badge in tray icon
- Quick access menu

## Browser Extension Setup

### Chrome
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the extension directory
4. The extension will be loaded and ready to use

### Firefox
1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select the extension's manifest file
4. The extension will be loaded for the session

### Using the Extension
- Right-click on any link and select "Download with Spider Manager"
- The URL will be automatically added to your download queue
- Configure download options in the dialog that appears

## Configuration

### General Settings
- **Download Directory**: Default location for downloaded files
- **Segment Count**: Number of parallel segments per download (1-32)
- **Max Concurrent**: Maximum simultaneous downloads (1-10)

### Connection Settings
- **Speed Limit**: Global download speed limit (KB/s)
- **Timeout**: Connection timeout in seconds
- **Retry Count**: Number of retry attempts on failure

### Scheduler Settings
- **Enable Scheduler**: Turn on time-based scheduling
- **Start Time**: When to begin downloads (HH:MM format)
- **End Time**: When to stop downloads (HH:MM format)

### Appearance
- **Theme**: Choose between Dark and Light themes
- **Font Size**: Adjust UI font size
- **Window State**: Remember window position and size

### Sounds
- **Enable Notifications**: Turn on sound alerts
- **Master Volume**: Overall volume control
- **Event Sounds**: Customize sounds for specific events

## Troubleshooting

### Downloads Not Starting
- Check your internet connection
- Verify the URL is valid and accessible
- Check if scheduler is preventing downloads outside time window
- Ensure speed limit isn't set too low

### Slow Download Speeds
- Reduce segment count (too many segments can slow things down)
- Check if speed limit is enabled
- Verify server supports multi-segment downloads
- Try pausing other active downloads

### Browser Extension Not Working
- Ensure Spider Manager is running
- Check extension is enabled in browser
- Verify native messaging host is properly configured
- Check browser console for errors

### High Memory Usage
- Reduce max concurrent downloads
- Reduce segment count
- Clear completed downloads from the list
- Restart the application periodically

### File Size Mismatch
- This error occurs when downloaded file size doesn't match expected
- Usually indicates server changed the file or network issue
- Try downloading the file again
- Check if URL redirects to a different file

## FAQ

**Q: Can I download files larger than 4GB?**
A: Yes, Spider Manager supports files of any size.

**Q: Does it support resuming interrupted downloads?**
A: Yes, partial downloads are automatically resumed when you restart the application.

**Q: Can I download from password-protected sites?**
A: Yes, you can add authentication credentials in the download dialog.

**Q: What video sites are supported?**
A: Spider Manager supports YouTube, Vimeo, Twitch, and many others via yt-dlp integration.

**Q: How do I update the application?**
A: Check for updates in the Help menu, or download the latest version from the releases page.

**Q: Can I run multiple instances?**
A: No, only one instance of Spider Manager can run at a time to prevent conflicts.

**Q: Where are settings stored?**
A: Settings are stored in `~/.spider_manager/` on Linux/Mac and `%APPDATA%\SpiderManager\` on Windows.

**Q: How do I completely uninstall?**
A: Use the uninstaller, then manually delete the settings directory if desired.

**Q: Is my data sent to any servers?**
A: No, Spider Manager is completely offline and does not send any data to external servers.

**Q: Can I use it with a proxy?**
A: Yes, configure proxy settings in the Connection preferences tab.




Fix Magnet and Torrent Downloads

Root cause

The libtorrent implementation exists and is wired in the engine, but the UI never reaches it.

flowchart LR
    subgraph broken [Current broken path]
        A[Extension or Add URL] --> B["_handle_plugin_download()"]
        B --> C["task._plugin_name = torrent"]
        C --> D["_run_plugin_task()"]
        D --> E["plugin.process() metadata only"]
        E --> F["result.success AttributeError"]
    end

    subgraph working [Working path never used]
        G["task.download_mode = torrent"] --> H["engine.start()"]
        H --> I["_run_torrent()"]
        I --> J["plugin.download_torrent() libtorrent"]
    end

Three separate bugs block downloads:







Bug



Location



Effect





Wrong queue path



[ui/main_window.py](ui/main_window.py) _handle_plugin_download



Sets _plugin_name so queue uses _run_plugin_task instead of engine.start()





result.success missing



[core/queue_manager.py](core/queue_manager.py) line 389



PluginResult has no success field → AttributeError even if metadata fetch succeeds





download_mode never set



[ui/main_window.py](ui/main_window.py)



Engine only runs torrents when task.download_mode == "torrent" (see [core/download_engine.py](core/download_engine.py) line 743)

Secondary gaps (also in scope per your choices):





HTTP .torrent URLs are routed to [_handle_direct_download](ui/main_window.py) → downloads the .torrent file, not content



Manual Add URL / clipboard uses HTTP-only [normalize_url()](core/protocol_handler.py) and [engine.probe()](core/download_engine.py) → magnet/torrent rejected



[download_torrent()](plugins/torrent_plugin.py) line 425 calls lt.torrent_info(url) with a URL string (expects a local file path) for non-magnet torrents

The working reference to copy is [_handle_streaming_download_with_queue](ui/main_window.py): create task → set download_mode → add to queue → engine.start().



Implementation plan

1. Add a dedicated torrent queue handler (mirror yt-dlp pattern)

In [ui/main_window.py](ui/main_window.py), add _handle_torrent_download_with_queue() modeled on _handle_streaming_download_with_queue():





create_task() with filename, save_path, category from dialog ("Torrents", not hardcoded "documents")



Set task.download_mode = "torrent"



Do not set task._plugin_name (so queue goes to engine.start())



Wire progress/state callbacks and show DownloadProgressDialog



Pass protocol_options from dialog into task.headers['torrent_options'] if present

Update call sites:





Extension path: magnet / torrent: links (lines 907–912)



Extension path: HTTP .torrent links (lines 915–918) — route here instead of _handle_direct_download



Manual path: new branch in _handle_new_download (before engine.probe())

2. Fix queue routing for plugin tasks

In [core/queue_manager.py](core/queue_manager.py) _run_plugin_task():





Remove the broken result.success / result.error check



Apply PluginResult fields to the task (filename, total_size, download_mode)



If result.download_mode == DownloadMode.TORRENT, call await self.engine.start(task) instead of marking complete



Keep FTP on the plugin path for now (FTP is a separate gap: no _run_ftp in engine), but at least surface real exceptions instead of AttributeError

Also update _run_task() to prefer task.download_mode in ("torrent", "ytdlp", ...) over _plugin_name when both are set, as a safety net.

3. Support HTTP .torrent URLs in the plugin

In [plugins/torrent_plugin.py](plugins/torrent_plugin.py) download_torrent():





When URL is HTTP/HTTPS and path ends with .torrent:





Fetch the .torrent bytes via aiohttp (reuse engine session pattern or a small internal fetch)



Parse with lt.torrent_info(bdecode(data)) or save to a temp file and load



Add to libtorrent session with lt.add_torrent({'ti': torrent_info, 'save_path': ...})



Improve URL detection: use urlparse(url).path.lower().endswith('.torrent') so query strings like file.torrent?token=abc work

Apply the same fetch logic in _process_torrent_file() so metadata (filename, size) can be resolved before download starts.

4. Enable manual Add URL / clipboard for magnet and torrent

In [ui/main_window.py](ui/main_window.py) _handle_new_download():





Import TorrentPlugin and detect magnet / torrent: / HTTP .torrent (same logic as extension handler)



Show DownloadFileInfoDialog and call _handle_torrent_download_with_queue()



Return early before engine.probe()

In [core/protocol_handler.py](core/protocol_handler.py) normalize_url():





Allow magnet: and torrent: schemes (return as-is after strip/validate)



For HTTP URLs whose path ends in .torrent, allow normalization (already works for http/https)

Update [ui/dialogs/add_download.py](ui/dialogs/add_download.py) validation message so magnet/torrent are accepted.

Optional: update [utils/clipboard_monitor.py](utils/clipboard_monitor.py) to pass magnet links through (currently silently dropped by normalize_url).

5. Wire protocol options through the dialog

In [ui/dialogs/download_file_info.py](ui/dialogs/download_file_info.py):





Initialize self.protocol_options = {}



Include protocol_options in get_info()



In torrent handler, map options dict keys to what _extract_torrent_options() expects (torrent_max_connections, etc.) or store as a flat dict in task.headers['torrent_options'] matching [_run_torrent](core/download_engine.py) line 1462

6. Minor correctness fixes





[plugins/torrent_plugin.py](plugins/torrent_plugin.py): set DownloadMode.TORRENT on multi-file playlist_items (currently DIRECT)



[ui/main_window.py](ui/main_window.py): use info["category"] from dialog instead of hardcoded "documents" in _handle_plugin_download (FTP path)

7. Verify libtorrent dependency

[requirements.txt](requirements.txt) lists libtorrent>=2.0.0. On Windows this often requires a prebuilt wheel (pip install libtorrent or python-libtorrent). If import fails, the app already raises PluginDependencyMissing with an install hint — confirm this error is shown clearly in the progress dialog after the routing fix.



Files to change







File



Changes





[ui/main_window.py](ui/main_window.py)



New _handle_torrent_download_with_queue, reroute extension + manual paths





[core/queue_manager.py](core/queue_manager.py)



Fix _run_plugin_task, safer _run_task routing





[plugins/torrent_plugin.py](plugins/torrent_plugin.py)



HTTP .torrent fetch + parse in download_torrent / _process_torrent_file





[ui/dialogs/download_file_info.py](ui/dialogs/download_file_info.py)



Expose protocol_options in get_info()





[core/protocol_handler.py](core/protocol_handler.py)



Allow magnet/torrent in normalize_url()





[ui/dialogs/add_download.py](ui/dialogs/add_download.py)



Accept magnet/torrent URLs



Test plan





Dependency check: python -c "import libtorrent" — if missing, install and retry



Magnet via extension: intercept a magnet:?xt=... link → dialog → queue → verify task uses download_mode=torrent, reaches downloading state, peers connect



Magnet via Add URL: paste magnet link in Add URL → same behavior



HTTP .torrent via extension: https://.../file.torrent → starts BitTorrent download (not a 2 KB .torrent file saved via HTTP)



HTTP .torrent via Add URL: same as above



Regression: normal https://.../file.zip still uses direct HTTP download



Unit tests: extend [tests/test_torrent_plugin.py](tests/test_torrent_plugin.py) for HTTP .torrent URL path detection; add queue routing test mocking engine.start



Expected outcome

After these changes, both browser extension and manual entry will enqueue torrent tasks on the same path as yt-dlp: queue.add() → engine.start() → _run_torrent() → download_torrent(). Magnet links and HTTP .torrent links will start real BitTorrent transfers instead of failing on result.success or downlo