"""Version information for FLO-2D Postprocessor"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Build information
BUILD_DATE = "2025-01-15"
BUILD_TYPE = "release"

# Application metadata
APP_NAME = "FLO-2D Postprocessor"
APP_DESCRIPTION = "Automated processing and visualization of FLO-2D hydraulic modeling data"
APP_AUTHOR = "FLO-2D Community"
APP_URL = "https://github.com/yourusername/postprocessor_for_flo2d"

def get_version():
    """Get the current version string"""
    return __version__

def get_version_info():
    """Get version information as a dictionary"""
    return {
        'version': __version__,
        'version_info': __version_info__,
        'build_date': BUILD_DATE,
        'build_type': BUILD_TYPE,
        'app_name': APP_NAME,
        'description': APP_DESCRIPTION,
        'author': APP_AUTHOR,
        'url': APP_URL
    }

def print_version():
    """Print version information to console"""
    print(f"{APP_NAME} v{__version__}")
    print(f"Build: {BUILD_DATE} ({BUILD_TYPE})")
    print(f"Description: {APP_DESCRIPTION}")