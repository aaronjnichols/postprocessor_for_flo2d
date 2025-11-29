"""Auto-update module for FLO-2D Postprocessor.

This module checks for new releases on GitHub and downloads updates automatically.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Callable, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Application version - update this with each release
__version__ = "1.0.0"

# GitHub repository information
GITHUB_OWNER = "aaronjnichols"
GITHUB_REPO = "postprocessor_for_flo2d"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Update check settings
UPDATE_CHECK_TIMEOUT = 10  # seconds
DOWNLOAD_CHUNK_SIZE = 8192  # bytes


def get_current_version() -> str:
    """Get the current application version.

    Returns:
        str: Current version string (e.g., "1.0.0").
    """
    return __version__


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string into a comparable tuple.

    Args:
        version_str: Version string (e.g., "1.2.3" or "v1.2.3").

    Returns:
        Tuple of integers representing the version.
    """
    # Remove 'v' prefix if present
    if version_str.startswith('v'):
        version_str = version_str[1:]

    # Remove any pre-release suffixes for comparison
    version_str = version_str.split('-')[0].split('+')[0]

    try:
        return tuple(int(x) for x in version_str.split('.'))
    except ValueError:
        return (0, 0, 0)


def is_newer_version(latest: str, current: str) -> bool:
    """Check if the latest version is newer than the current version.

    Args:
        latest: Latest version string.
        current: Current version string.

    Returns:
        True if latest is newer than current.
    """
    return parse_version(latest) > parse_version(current)


def check_for_updates(timeout: int = UPDATE_CHECK_TIMEOUT) -> Optional[dict]:
    """Check GitHub for the latest release.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        Dictionary with update info if available, None otherwise.
        Keys: 'version', 'download_url', 'release_notes', 'html_url'
    """
    logger = logging.getLogger('FLO2D_Postprocessor')

    try:
        request = Request(
            GITHUB_API_URL,
            headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'FLO2D-Postprocessor'}
        )

        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))

        latest_version = data.get('tag_name', '')
        current_version = get_current_version()

        if not is_newer_version(latest_version, current_version):
            logger.debug(f"No update available. Current: {current_version}, Latest: {latest_version}")
            return None

        # Find the appropriate asset for the current platform
        download_url = None
        system = platform.system().lower()

        for asset in data.get('assets', []):
            asset_name = asset.get('name', '').lower()
            # Look for Windows executable
            if system == 'windows' and asset_name.endswith('.exe'):
                download_url = asset.get('browser_download_url')
                break
            # Look for zip/tar.gz for other platforms
            elif system != 'windows' and (asset_name.endswith('.zip') or asset_name.endswith('.tar.gz')):
                download_url = asset.get('browser_download_url')
                break

        update_info = {
            'version': latest_version,
            'download_url': download_url,
            'release_notes': data.get('body', ''),
            'html_url': data.get('html_url', ''),
            'published_at': data.get('published_at', ''),
        }

        logger.info(f"Update available: {current_version} -> {latest_version}")
        return update_info

    except HTTPError as e:
        logger.warning(f"HTTP error checking for updates: {e.code} {e.reason}")
        return None
    except URLError as e:
        logger.warning(f"Network error checking for updates: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Error parsing update response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error checking for updates: {e}")
        return None


def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[str]:
    """Download the update file.

    Args:
        download_url: URL to download the update from.
        progress_callback: Optional callback(downloaded_bytes, total_bytes).

    Returns:
        Path to the downloaded file, or None if download failed.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')

    if not download_url:
        logger.error("No download URL provided")
        return None

    try:
        request = Request(download_url, headers={'User-Agent': 'FLO2D-Postprocessor'})

        with urlopen(request) as response:
            total_size = int(response.headers.get('content-length', 0))

            # Create temporary file
            suffix = '.exe' if download_url.endswith('.exe') else '.zip'
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix='flo2d_update_')

            try:
                downloaded = 0
                with os.fdopen(fd, 'wb') as f:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded, total_size)

                logger.info(f"Update downloaded to: {temp_path}")
                return temp_path

            except Exception:
                # Clean up on error
                os.unlink(temp_path)
                raise

    except Exception as e:
        logger.error(f"Error downloading update: {e}")
        return None


def apply_update(update_path: str, restart: bool = True) -> bool:
    """Apply the downloaded update.

    This function handles the update process:
    1. For frozen (PyInstaller) apps: Replace the current executable
    2. Optionally restart the application

    Args:
        update_path: Path to the downloaded update file.
        restart: Whether to restart the application after update.

    Returns:
        True if update was applied successfully, False otherwise.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')

    if not os.path.exists(update_path):
        logger.error(f"Update file not found: {update_path}")
        return False

    # Check if running as frozen executable
    is_frozen = getattr(sys, 'frozen', False)

    if is_frozen and platform.system() == 'Windows':
        # Running as PyInstaller executable on Windows
        current_exe = sys.executable
        backup_path = current_exe + '.backup'

        try:
            # Create a batch script to perform the update
            batch_script = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.bat',
                delete=False,
                prefix='flo2d_update_'
            )

            # Write batch commands
            batch_content = f'''@echo off
timeout /t 2 /nobreak >nul
move /y "{current_exe}" "{backup_path}"
move /y "{update_path}" "{current_exe}"
'''
            if restart:
                batch_content += f'start "" "{current_exe}"\n'
            batch_content += f'del "{backup_path}"\ndel "%~f0"\n'

            batch_script.write(batch_content)
            batch_script.close()

            # Execute the batch script and exit
            logger.info("Starting update process...")
            subprocess.Popen(
                ['cmd', '/c', batch_script.name],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            return True

        except Exception as e:
            logger.error(f"Error applying update: {e}")
            return False
    else:
        # Not running as frozen app or not on Windows
        logger.info(f"Update downloaded to: {update_path}")
        logger.info("Please manually replace the application with the new version.")
        return True


def check_for_updates_async(
    callback: Callable[[Optional[dict]], None],
    timeout: int = UPDATE_CHECK_TIMEOUT
) -> threading.Thread:
    """Check for updates asynchronously.

    Args:
        callback: Function to call with the update info (or None).
        timeout: Request timeout in seconds.

    Returns:
        The started thread.
    """
    def _check():
        result = check_for_updates(timeout)
        callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


class UpdateChecker:
    """Class to manage update checking with GUI integration."""

    def __init__(self):
        self.update_info: Optional[dict] = None
        self.is_checking = False
        self.download_progress = 0
        self.download_total = 0

    def check(self, callback: Optional[Callable[[Optional[dict]], None]] = None) -> None:
        """Check for updates asynchronously.

        Args:
            callback: Optional callback with update info.
        """
        if self.is_checking:
            return

        self.is_checking = True

        def _on_result(result):
            self.update_info = result
            self.is_checking = False
            if callback:
                callback(result)

        check_for_updates_async(_on_result)

    def download(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        complete_callback: Optional[Callable[[Optional[str]], None]] = None
    ) -> None:
        """Download the update asynchronously.

        Args:
            progress_callback: Optional callback(downloaded, total).
            complete_callback: Optional callback with download path.
        """
        if not self.update_info or not self.update_info.get('download_url'):
            if complete_callback:
                complete_callback(None)
            return

        def _progress(downloaded, total):
            self.download_progress = downloaded
            self.download_total = total
            if progress_callback:
                progress_callback(downloaded, total)

        def _download():
            result = download_update(self.update_info['download_url'], _progress)
            if complete_callback:
                complete_callback(result)

        thread = threading.Thread(target=_download, daemon=True)
        thread.start()


# Convenience function for GUI integration
def get_update_checker() -> UpdateChecker:
    """Get a singleton UpdateChecker instance."""
    if not hasattr(get_update_checker, '_instance'):
        get_update_checker._instance = UpdateChecker()
    return get_update_checker._instance
