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
