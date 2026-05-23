# Spider Manager

A professional internet download manager built with Python 3.11+ and PyQt6. Inspired by IDM (Internet Download Manager), it provides multi-segment parallel downloading, browser integration, scheduling, and a polished dark/light UI.

## Features

- **Multi-Segment Downloading**: Automatically splits files into multiple segments for faster downloads
- **Speed Limiting**: Global bandwidth control with real-time monitoring
- **Browser Integration**: Chrome and Firefox extension support
- **Video/Audio Support**: yt-dlp integration for YouTube, Vimeo, and other streaming sites
- **Scheduling**: Time-based download windows for off-peak downloading
- **File Categorization**: Automatic organization by file type
- **Sound Notifications**: Audio alerts for download events
- **System Tray**: Minimize to tray with speed badge
- **Themes**: Dark and light theme support
- **Resume Support**: Automatic resume of interrupted downloads

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/spider-manager.git
cd spider_manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Requirements

- Python 3.11 or higher
- PyQt6 >= 6.6.0
- qasync >= 0.27.0
- aiohttp >= 3.9.0
- yt-dlp >= 2024.1.0
- ffmpeg (for video/audio processing)

## Development Setup

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_engine.py

# Run with coverage
pytest --cov=core --cov=ui --cov-report=html

# Run performance benchmarks
pytest tests/performance/ -m benchmark
```

### Code Style

```bash
# Format code with Black
black .

# Type checking with mypy
mypy core/ ui/ utils/

# Linting
pylint core/ ui/ utils/
```

### Project Structure

```
spider_manager/
├── main.py                      # Entry point
├── config/                      # Configuration
│   ├── constants.py             # App constants
│   └── settings.py              # User preferences
├── core/                        # Core download engine
│   ├── download_engine.py       # Multi-segment downloader
│   ├── queue_manager.py         # Queue management
│   ├── scheduler.py             # Time-based scheduling
│   ├── speed_limiter.py         # Bandwidth throttling
│   ├── resume_handler.py        # Resume support
│   └── protocol_handler.py      # Protocol handling
├── ui/                          # PyQt6 UI
│   ├── main_window.py           # Main window
│   ├── dialogs/                 # Dialog windows
│   ├── widgets/                 # Custom widgets
│   └── themes/                  # Theme management
├── plugins/                     # Plugin system
│   ├── plugin_base.py           # Plugin base class
│   ├── browser_extension.py     # Browser integration
│   └── yt_dlp_plugin.py         # Video extraction
├── utils/                       # Utilities
│   ├── file_utils.py            # File operations
│   ├── network_utils.py         # Network helpers
│   ├── url_parser.py            # URL parsing
│   └── logger.py                # Logging
├── tests/                       # Test suite
│   ├── test_engine.py
│   ├── test_queue.py
│   ├── test_utils.py
│   └── performance/             # Performance benchmarks
└── docs/                        # Documentation
```

## Architecture

### Download Engine

The download engine (`core/download_engine.py`) is the heart of the application. It supports multiple download modes:

- **DIRECT**: Standard HTTP/HTTPS download with multi-segment support
- **STREAM_HLS**: HLS streaming with ffmpeg integration
- **STREAM_DASH**: DASH streaming with ffmpeg integration
- **YTDLP**: yt-dlp subprocess wrapper for video sites
- **BLOB**: Blob URL fallback handling

Key features:
- Adaptive segment count based on file size
- Speed limiting integration
- Checksum verification (SHA-256, MD5)
- Resume support via .part files
- Connection retry logic

### Queue Manager

The queue manager (`core/queue_manager.py`) handles:

- Priority-based queuing (high/normal/low)
- Concurrency control
- Category-based filtering
- Scheduler integration
- Persistent queue storage
- Signal emission for UI updates

### Plugin System

The plugin system (`plugins/plugin_base.py`) provides:

- Capability flags (URL handling, stream extraction, metadata)
- Standardized plugin interface
- yt-dlp integration for video sites
- Browser extension IPC handler

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style Guidelines

- Follow PEP 8 style guide
- Use Black for formatting (line length: 100)
- Add type hints for all functions
- Write docstrings for all public functions
- Add tests for new features
- Keep functions focused and small

### Testing Guidelines

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use pytest for testing
- Mock external dependencies (network, filesystem)
- Add performance benchmarks for critical paths

## Building for Distribution

### Windows Installer

```bash
# Build with PyInstaller
pyinstaller spider_manager.spec

# Create NSIS installer
makensis installer.nsi
```

See `docs/BUILD.md` for detailed build instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Internet Download Manager (IDM)
- Built with PyQt6 and qasync
- Uses yt-dlp for video extraction
- Uses aiohttp for async HTTP operations
- Uses ffmpeg for media processing

## Support

- **Documentation**: See `docs/USER_GUIDE.md` for user documentation
- **API Docs**: See `docs/API.md` for API documentation
- **Build Docs**: See `docs/BUILD.md` for build instructions
- **Issues**: Report bugs on GitHub Issues
