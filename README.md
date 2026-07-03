<h4 align="right">
  English
</h4>

> [!NOTE]
> Spider Manager is currently in active development for v2.0.0 with enhanced protocol support and UI improvements.

<!-- PROJECT LOGO -->
<div align="center">

### Professional internet download manager built with Python and PyQt6

##### [Documentation](docs/USER_GUIDE.md) · [Report Bug](issues) · [Request Feature](issues)

</div>

<!-- ABOUT THE PROJECT -->
## About The Project

* A professional download manager built with modern Python technologies
* Inspired by IDM (Internet Download Manager) with multi-segment parallel downloading
* Built with extensibility in mind through a comprehensive plugin system
* Focused on performance, reliability, and user experience

|    Platform    | Required Version |  Architectures   | Compatible |
|:--------------:|:----------------:|:----------------:|:----------:|
| 🪟 **Windows** |     `10+`        | `x86_64`         |     ✅      |
|  🐧 **Linux**  |     (Planned)    | `x86_64`/`arm64` |     🚧      |
|  🍎 **macOS**  |     (Planned)    | `x86_64`/`arm64` |     🚧      |

> [!WARNING]
> Qt `6.6+` no longer supports CPUs without the `AVX` instruction set.

> [!TIP]
> **Cross-platform support** is planned for v2.0.0. Currently Windows is the primary supported platform.

<!-- FEATURES -->
## Features

* **Multi-Segment Downloading**: Automatically splits files into multiple segments for faster downloads ⚡
* **Speed Limiting**: Global bandwidth control with real-time monitoring 📊
* **Browser Integration**: Chrome and Firefox extension support 🦊
* **Video/Audio Support**: yt-dlp integration for YouTube, Vimeo, and other streaming sites 🎬
* **FTP/FTPS Support**: Full FTP and FTPS protocol support with authentication and resume 📁
* **BitTorrent Support**: Magnet link and .torrent file support with peer management 🔗
* **Scheduling**: Time-based download windows for off-peak downloading ⏰
* **File Categorization**: Automatic organization by file type 📂
* **Sound Notifications**: Audio alerts for download events 🔔
* **System Tray**: Minimize to tray with speed badge 🖥️
* **Themes**: Dark and light theme support 🎨
* **Resume Support**: Automatic resume of interrupted downloads 🔄

<!-- ROADMAP -->
## Roadmap

- ❌ Download history system with search and export
- ❌ Advanced tagging and labeling system
- ❌ Cloud storage integration (Google Drive, Dropbox, OneDrive)
- ❌ Performance optimization (connection pooling, memory management)
- ❌ Cross-platform support (Linux, macOS)
- ❌ Enhanced statistics dashboard
- ❌ AI-powered download acceleration

Visit [Open issues](issues) to see all requested features (and known issues).

<!-- CONTRIBUTING -->
## Contributing

Contributions make the open source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion, fork the repo and create a pull request. You can also simply open an issue with the "Enhancement" tag. Don't forget to give the project a star⭐! Thanks again!

1. Fork the Project
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
3. Commit your Changes (git commit -m 'Add some AmazingFeature')
4. Push to the Branch (git push origin feature/AmazingFeature)
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

<!-- LICENSE -->
## License

Distributed under the MIT License. Open `LICENSE` for more details.

Copyright © 2024-2026 Spider Manager Team.

<!-- CONTACT -->
## Contact

* **Documentation**: See `docs/USER_GUIDE.md` for user documentation
* **API Docs**: See `docs/API.md` for API documentation
* **Build Docs**: See `docs/BUILD.md` for build instructions
* **Issues**: Report bugs on GitHub Issues

<!-- REFERENCES -->
## References

* [aiohttp](https://github.com/aio-libs/aiohttp) Async HTTP client/server for asyncio
* [aioftp](https://github.com/aio-libs/aioftp) Ftp client/server for asyncio
* [libtorrent](https://github.com/arvidn/libtorrent) An efficient feature complete C++ bittorrent implementation
* [PyQt6](https://github.com/PyQt6/PyQt6) Python bindings for the Qt application framework
* [qasync](https://github.com/CabbageDevelopment/qasync) Implementation of the PEP 3156 event loop
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) A youtube-dl fork with additional features and fixes
* [FFmpeg](https://ffmpeg.org/) A complete, cross-platform solution to record, convert and stream audio and video
* [pytest](https://github.com/pytest-dev/pytest) The pytest framework makes it easy to write simple tests
* [Black](https://github.com/psf/black) The uncompromising Python code formatter
* [mypy](https://github.com/python/mypy) Optional static typing for Python
