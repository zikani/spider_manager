---
description: Run tests for Spider Manager
---

# Test Workflow

This workflow guides you through running tests for Spider Manager.

## Prerequisites

- Python 3.11+ installed
- Virtual environment activated
- Test dependencies installed: `pip install pytest pytest-cov pytest-asyncio pytest-mock`

## Steps

1. **Install test dependencies**
   ```bash
   pip install pytest pytest-cov pytest-asyncio pytest-mock
   ```

2. **Run all tests**
   ```bash
   pytest tests/ -v
   ```

3. **Run tests with coverage report**
   ```bash
   pytest tests/ --cov=. --cov-report=html --cov-report=term
   ```
   This generates an HTML coverage report in `htmlcov/` directory.

4. **Run specific test file**
   ```bash
   pytest tests/test_download_engine.py -v
   ```

5. **Run specific test function**
   ```bash
   pytest tests/test_download_engine.py::test_download_segment -v
   ```

6. **Run tests by marker**
   ```bash
   pytest tests/ -m benchmark
   ```

7. **Run async tests**
   ```bash
   pytest tests/ -v --asyncio-mode=auto
   ```

8. **Run tests in parallel (requires pytest-xdist)**
   ```bash
   pip install pytest-xdist
   pytest tests/ -n auto
   ```

## Test Categories

**Unit Tests:**
- `tests/test_download_engine.py` - Core download engine functionality
- `tests/test_queue_manager.py` - Queue management logic
- `tests/test_history_manager.py` - Download history tracking
- `tests/test_tag_manager.py` - Tag and labeling system
- `tests/test_file_categorizer.py` - File categorization logic

**Integration Tests:**
- `tests/test_browser_extension.py` - Browser extension integration
- `tests/test_plugins.py` - Plugin system integration
- `tests/test_ftp_plugin.py` - FTP plugin functionality
- `tests/test_torrent_plugin.py` - Torrent plugin functionality

**Performance Tests:**
- `tests/performance/test_download_engine_benchmarks.py` - Performance benchmarks

**UI Tests:**
- `tests/test_ui.py` - UI component tests

## Coverage Goals

- Target: >80% code coverage
- Critical paths: >90% coverage
- Core modules (download_engine, queue_manager): >95% coverage

## Troubleshooting

**Tests fail with import errors:**
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH includes project root

**Async tests fail:**
- Ensure pytest-asyncio is installed
- Use `--asyncio-mode=auto` flag
- Check async fixtures are properly defined

**Coverage report incomplete:**
- Ensure pytest-cov is installed
- Check that .coveragerc exists if using custom config
- Verify source paths are correct

**Performance tests timeout:**
- Increase timeout in pytest.ini
- Run performance tests separately
- Check system resources
