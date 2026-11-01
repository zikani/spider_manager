---
description: Set up development environment for Spider Manager
---

# Development Workflow

This workflow guides you through setting up the development environment for Spider Manager.

## Prerequisites

- Python 3.11 or higher
- Git
- Windows 10/11 (primary development platform)
- Visual Studio Code or preferred IDE

## Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/spider-manager.git
   cd spider-manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-asyncio pytest-mock black mypy
   ```

4. **Install development tools**
   ```bash
   pip install pyinstaller  # For building executables
   ```

5. **Generate UI resources**
   ```bash
   python scripts/convert_svg_to_ico.py
   pyrcc6 resources/icons/icons.qrc -o resources/icons/icons_rc.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Set up pre-commit hooks (optional)**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use Black for formatting (line length: 100)
- Add type hints for all functions
- Write docstrings for all public functions
- Keep functions focused and small (<50 lines)

### Running Tests

- Run tests before committing: `/test`
- Ensure all tests pass
- Aim for >80% code coverage
- Add tests for new features

### Code Organization

- Core logic in `core/` directory
- UI components in `ui/` directory
- Plugins in `plugins/` directory
- Utilities in `utils/` directory
- Configuration in `config/` directory

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement the feature
3. Add tests for the feature
4. Update documentation if needed
5. Run tests: `/test`
6. Format code: `black .`
7. Type check: `mypy .`
8. Commit changes
9. Push and create pull request

### Debugging

- Use Python debugger: `python -m pdb main.py`
- Check logs in application directory
- Enable debug logging in `config/settings.py`
- Use VS Code debugger with launch configuration

## Project Structure

```
spider_manager/
├── config/           # Configuration files
├── core/             # Core application logic
├── docs/             # Documentation
├── extension/        # Browser extension
├── plugins/          # Download plugins
├── resources/        # UI resources (icons, themes)
├── scripts/          # Utility scripts
├── tests/            # Test files
├── ui/               # UI components
├── utils/            # Utility functions
├── main.py           # Application entry point
└── requirements.txt  # Python dependencies
```

## Common Development Tasks

**Add a new plugin:**
1. Create file in `plugins/` directory
2. Inherit from `PluginBase` class
3. Implement required methods
4. Register plugin in plugin manager
5. Add tests for plugin

**Add a new UI dialog:**
1. Create file in `ui/dialogs/` directory
2. Inherit from `QDialog`
3. Implement UI layout
4. Connect to main window
5. Add menu item or button

**Add a new core feature:**
1. Implement in appropriate `core/` module
2. Add tests in `tests/` directory
3. Update UI if needed
4. Update documentation

## Troubleshooting

**Import errors:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH includes project root

**UI not displaying correctly:**
- Regenerate resources: `pyrcc6 resources/icons/icons.qrc -o resources/icons/icons_rc.py`
- Check PyQt6 installation: `pip install --upgrade PyQt6`

**Tests failing:**
- Check test dependencies are installed
- Run tests individually to identify issue
- Check for async test issues with `--asyncio-mode=auto`

**Build issues:**
- Ensure PyInstaller is installed
- Check spec file paths are correct
- Verify all resources are included
