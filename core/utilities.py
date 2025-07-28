"""Core utility functions for the FLO-2D postprocessor.

This module provides common utility functions including timing decorators
and folder creation utilities used throughout the application.
"""

import logging
import os
import time
from functools import wraps


def time_function(func):
    """
    Decorator to time function execution and log the duration.
    
    Args:
        func: The function to be timed.
        
    Returns:
        The wrapped function with timing functionality.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('FLO2D_Postprocessor')
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"Finished {func.__name__!r} in {end_time - start_time:.3f} seconds")
        return result
    return wrapper


def create_required_folders(folders):
    """
    Create required output directories for FLO-2D processing.
    
    Args:
        folders (list): List of folder paths to create.
        
    Raises:
        OSError: If folder creation fails due to permissions or other system issues.
    """
    logger = logging.getLogger('FLO2D_Postprocessor')
    
    for folder in folders:
        try:
            os.makedirs(folder, exist_ok=True)
            logger.debug(f"Created/verified directory: {folder}")
        except OSError as e:
            logger.error(f"Failed to create directory {folder}: {e}")
            raise
