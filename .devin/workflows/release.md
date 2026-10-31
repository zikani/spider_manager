---
description: Create a new release of Spider Manager
---

# Release Workflow

This workflow guides you through creating a new release of Spider Manager.

## Prerequisites

- Ensure all tests pass
- Ensure changelog is updated
- Ensure version is bumped in all relevant files
- Commit all changes

## Steps

1. **Run full test suite**
   ```bash
   pytest tests/ -v --cov=.
   ```
   Ensure all tests pass and coverage is acceptable (>80%).

2. **Update version in config/constants.py**
   - Open `config/constants.py`
   - Update `APP_VERSION` to the new version number
   - Save the file

3. **Update version in pyproject.toml**
   - Open `pyproject.toml`
   - Update `version` field to match APP_VERSION
   - Save the file

4. **Update changelog in ui/dialogs/changelog_dialog.py**
   - Open `ui/dialogs/changelog_dialog.py`
   - Add new version to `_populate_versions()` list
   - Add changelog data in `_get_changelog_data()` method
   - Update `_show_current_version()` to point to new version
   - Save the file

5. **Update mock update version in ui/dialogs/check_updates_dialog.py**
   - Open `ui/dialogs/check_updates_dialog.py`
   - Update the mock version in `UpdateChecker.run()` to next version
   - Save the file

6. **Commit version changes**
   ```bash
   git add config/constants.py pyproject.toml ui/dialogs/changelog_dialog.py ui/dialogs/check_updates_dialog.py
   git commit -m "Bump version to X.Y.Z"
   ```

7. **Create git tag**
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0: Protocol Expansion"
   git push origin v1.1.0
   ```

8. **Build the application**
   - Run the build workflow: `/build`
   - This will create the executable and installer

9. **Test the build**
   - Run the built executable
   - Verify basic functionality
   - Test new features added in this release

10. **Create GitHub Release**
    - Go to GitHub Releases page
    - Click "Draft a new release"
    - Choose the tag you just pushed
    - Copy changelog from `ui/dialogs/changelog_dialog.py`
    - Attach built installer files
    - Publish the release

11. **Update documentation (if needed)**
    - Update README.md if there are breaking changes
    - Update docs/USER_GUIDE.md for new features
    - Update docs/API.md for API changes

12. **Announce release**
    - Post announcement in relevant channels
    - Update project status if needed
