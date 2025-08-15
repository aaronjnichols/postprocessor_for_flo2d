# Build Tools

This directory contains tools for building and distributing the FLO-2D Postprocessor executable.

## Files

### `build_exe.py`
Python script that creates a standalone Windows executable using PyInstaller.

**Usage:**
```bash
# From project root or tools directory
python tools/build_exe.py
```

**Features:**
- Creates single-file executable with all dependencies
- Includes comprehensive hidden imports for geospatial libraries
- Windowed mode (no console) for GUI application
- Automatic version info embedding

### `build_installer.bat`
Windows batch script that builds both the executable and installer.

**Usage:**
```bash
# From project root
tools\build_installer.bat
```

**Features:**
- Installs PyInstaller if needed
- Builds executable using build_exe.py
- Creates Windows installer with Inno Setup (if installed)
- Comprehensive error handling

### `version.py`
Centralized version management for the application.

**Features:**
- Single source of truth for version numbers
- Build metadata and application information
- Used by build scripts and the application

## Building the Executable

### Prerequisites
- Python 3.8 or higher
- PyInstaller (`pip install pyinstaller`)
- For installer: Inno Setup 6 (optional)

### Quick Build
```bash
# Simple executable build
python tools/build_exe.py

# Complete build with installer
tools\build_installer.bat
```

### Output
- `dist/FLO2D-Postprocessor.exe` - Standalone executable (~189MB)
- `installer_output/FLO2D-Postprocessor-Setup.exe` - Windows installer (if Inno Setup available)

## Distribution

For public distribution:
1. **Test the executable** on clean Windows systems
2. **Upload to GitHub Releases** rather than committing large binaries
3. **Include documentation** (README, USER_MANUAL) with releases
4. **Provide both** standalone executable and installer options

## Notes

- Build artifacts (`build/`, `dist/`, `*.spec`) are git-ignored
- The executable includes all Python dependencies (no installation required)
- Performance is ~5-15% slower than native Python but provides standalone functionality
- File size is large (~189MB) due to bundled scientific libraries (numpy, scipy, geopandas, etc.)