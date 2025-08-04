"""
Enhanced logging system that integrates with the GUI message system.
Provides progress tracking and user-friendly message formatting.
"""

import logging
import time
from typing import Optional, Callable
from .message_system import MessageFormatter, ProgressTracker


class EnhancedTimingLogger:
    """Enhanced timing logger with GUI integration and progress tracking."""
    
    def __init__(self, logger, message_callback: Optional[Callable] = None, progress_callback: Optional[Callable] = None):
        self.logger = logger
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.message_callback = message_callback  # Function to call for GUI message updates
        self.progress_callback = progress_callback  # Function to call for progress updates
        self.progress_tracker = ProgressTracker()
        self.step_counter = 0
        
        # Map processing steps to step indices for progress tracking
        self.step_mapping = {
            "Creating necessary output directories": 0,
            "Extracting model data from FLO-2D files": 1,
            "Converting model data to GeoDataFrame for spatial processing": 2,
            "Generating computational domain polygon": 2.5,  # Added domain vectorization step
            "Initiating creation of FLO-2D Points Output": 3,
            "Initiating raster creation for available data columns": 4,
            "Extracting inflow data": 5,
            "Processing Inflow Data": 5,  # Alternative message
            "Extracting outflow data": 6,
            "Processing Outflow Data": 6,  # Alternative message
            "Processing Hydraulic Structures": 7,
            "Processing Floodplain Cross Sections": 7,  # Same as structures
            "Processing Channel Data": 7,  # Also structures/channel processing
            "Applying style files to shapefiles and rasters": 8,
            "=== FLO-2D Postprocessor Completed Successfully ===": 9
        }
        
    def log(self, message: str, msg_type: str = 'processing'):
        """
        Log a message with timing and optional GUI updates.
        
        Args:
            message: The message to log
            msg_type: Type of message for styling (processing, success, error, etc.)
        """
        current_time = time.time()
        elapsed = current_time - self.last_log_time
        total_elapsed = current_time - self.start_time
        
        # Clean message for step extraction
        clean_message = MessageFormatter.extract_step_from_message(message)
        
        # Update progress tracking if this is a known step
        if clean_message in self.step_mapping:
            step_index = self.step_mapping[clean_message]
            # Only advance if we're moving to a new step
            if step_index > self.progress_tracker.current_step - 1:
                self.progress_tracker.current_step = step_index + 1
                self.progress_tracker.current_step_progress = 0.0
            
            # Update progress callback if available
            if self.progress_callback:
                self.progress_callback(self.progress_tracker)
        else:
            # For non-step messages, gradually increment progress within current step
            if self.progress_tracker.current_step > 0:
                # Increment progress by small amounts (max 0.9 to save 0.1 for step completion)
                current_progress = self.progress_tracker.current_step_progress
                if current_progress < 0.9:
                    # Gradually increase progress with diminishing increments
                    increment = max(0.05, (0.9 - current_progress) * 0.2)
                    self.progress_tracker.current_step_progress = min(0.9, current_progress + increment)
                    
                    if self.progress_callback:
                        self.progress_callback(self.progress_tracker)
        
        # Determine message type based on content if not explicitly set
        if msg_type == 'processing':  # Only auto-detect if using default
            if "error" in message.lower() or "failed" in message.lower():
                msg_type = 'error'
            elif "warning" in message.lower():
                msg_type = 'warning'
            elif "completed" in message.lower() or "created" in message.lower() or "successfully" in message.lower():
                msg_type = 'success'
            elif "processing" in message.lower() or "extracting" in message.lower() or "creating" in message.lower() or "initiating" in message.lower():
                msg_type = 'processing'
            else:
                msg_type = 'info'
            
        # Create the technical log message with timing
        log_message = f"{clean_message} (Step time: {elapsed:.2f}s, Total time: {total_elapsed:.2f}s)"
        
        # Log to the standard logger
        self.logger.info(log_message)
        
        # Send to GUI if callback is available
        if self.message_callback:
            self.message_callback(clean_message, msg_type)
            
        self.last_log_time = current_time
        
    def log_error(self, message: str):
        """Log an error message."""
        self.log(message, 'error')
        
    def log_warning(self, message: str):
        """Log a warning message."""
        self.log(message, 'warning')
        
    def log_success(self, message: str):
        """Log a success message."""
        self.log(message, 'success')
        
    def log_file_operation(self, message: str):
        """Log a file-related operation."""
        self.log(message, 'file')
        
    def set_step_progress(self, progress: float):
        """Update progress within the current step."""
        self.progress_tracker.set_step_progress(progress)
        if self.progress_callback:
            self.progress_callback(self.progress_tracker)
            
    def complete_step(self, message: str = ""):
        """Mark current step as complete and advance to next."""
        if message:
            self.log(message, 'success')
        self.progress_tracker.current_step_progress = 1.0
        if self.progress_callback:
            self.progress_callback(self.progress_tracker)


class GUIMessageHandler(logging.Handler):
    """Custom logging handler that sends messages to the GUI."""
    
    def __init__(self, message_callback: Callable):
        super().__init__()
        self.message_callback = message_callback
        
    def emit(self, record):
        """Handle a log record by sending it to the GUI."""
        try:
            message = self.format(record)
            
            # Determine message type based on log level
            if record.levelno >= logging.ERROR:
                msg_type = 'error'
            elif record.levelno >= logging.WARNING:
                msg_type = 'warning'
            elif record.levelno >= logging.INFO:
                msg_type = 'info'
            else:
                msg_type = 'info'
                
            # Extract clean message (remove logger formatting)
            clean_message = record.getMessage()
            clean_message = MessageFormatter.extract_step_from_message(clean_message)
            
            self.message_callback(clean_message, msg_type)
            
        except Exception:
            # Fail silently to avoid recursive logging issues
            pass