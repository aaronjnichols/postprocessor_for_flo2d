"""
Enhanced logging system that integrates with the GUI message system.
Provides progress tracking and technical message formatting for FLO-2D professionals.
"""

import logging
import time
from typing import Optional, Callable
from .message_system import MessageFormatter, ProgressTracker
from .message_templates import FLO2DMessageTemplates, FileProcessingResult
from .smart_message_tracker import SmartMessageTracker


class EnhancedTimingLogger:
    """Enhanced timing logger with GUI integration and progress tracking."""
    
    def __init__(self, logger, message_callback: Optional[Callable] = None, progress_callback: Optional[Callable] = None):
        # Ensure logger does not propagate to avoid duplicate GUI messages
        self.logger = logger
        self.logger.propagate = False
        # Remove any existing handlers to prevent duplicates
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
        # Attach a single GUI handler if a callback is provided
        if message_callback:
            gui_handler = GUIMessageHandler(message_callback)
            gui_handler.setLevel(logging.INFO)
            self.logger.addHandler(gui_handler)
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.message_callback = message_callback  # Function to call for GUI message updates
        self.progress_callback = progress_callback  # Function to call for progress updates
        self.progress_tracker = ProgressTracker()
        self.message_tracker = SmartMessageTracker(message_callback) if message_callback else None
        self.step_counter = 0
        
        # Enhanced step mapping for technical FLO-2D operations
        self.step_mapping = {
            "Creating necessary output directories": 0,
            "Extracting model data from FLO-2D files": 1,
            "Model data extraction completed": 1,
            "Converting model data to GeoDataFrame for spatial processing": 2,
            "Conversion to GeoDataFrame completed": 2,
            "Generating computational domain polygon": 2,
            "Initiating creation of FLO-2D Points Output": 3,
            "Initiating raster creation for available data columns": 4,
            "Processing Inflow Data": 5,
            "Extracting inflow data": 5,
            "Processing Outflow Data": 5,
            "Extracting outflow data": 5,
            "Processing Hydraulic Structures": 6,
            "Processing Floodplain Cross Sections": 6,
            "Processing Channel Data": 6,
            "Applying style files to shapefiles and rasters": 7,
            "Style application process completed": 7,
            "=== FLO-2D Postprocessor Completed Successfully ===": 8
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
        
        # Check if this is a technical message that should use smart tracking
        if False:  # Disable enhanced messaging to prevent duplicates
            # Use smart tracker for file operations to prevent duplication
            self.message_tracker.send_standalone_message(clean_message, msg_type)
        else:
            # Send through regular callback for non-file operations
            if self.message_callback:
                self.message_callback(clean_message, msg_type)
        
        # Update progress tracking if this is a known step
        if clean_message in self.step_mapping:
            step_index = self.step_mapping[clean_message]
            # Only advance if we're moving to a new step
            if step_index > self.progress_tracker.current_step - 1:
                self.progress_tracker.current_step = step_index + 1
                self.progress_tracker.current_step_progress = 0.0
                self.progress_tracker.set_current_operation(clean_message)
            
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
        
        # Log to the standard logger, passing msg_type in `extra`
        self.logger.info(log_message, extra={'msg_type': msg_type})
            
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
        
    def log_file_extraction(self, file_type: str, stage: str, result: Optional[FileProcessingResult] = None, **kwargs):
        """Log file extraction with technical details."""
        msg_data = FLO2DMessageTemplates.get_file_message(file_type, stage, result, **kwargs)
        self.log(msg_data['text'], msg_data['category'])
    
    def log_processing_operation(self, operation: str, stage: str, **kwargs):
        """Log processing operation with technical details."""
        msg_data = FLO2DMessageTemplates.get_processing_message(operation, stage, **kwargs)
        self.log(msg_data['text'], msg_data['category'])
    
    def set_step_progress(self, progress: float):
        """Update progress within the current step."""
        self.progress_tracker.set_step_progress(progress)
        if self.progress_callback:
            self.progress_callback(self.progress_tracker)
    
    def set_current_file(self, filename: str):
        """Set the current file being processed for progress display."""
        self.progress_tracker.set_current_file(filename)
        if self.progress_callback:
            self.progress_callback(self.progress_tracker)
            
    def complete_step(self, message: str = ""):
        """Mark current step as complete and advance to next."""
        if message:
            self.log(message, 'success')
        self.progress_tracker.current_step_progress = 1.0
        if self.progress_callback:
            self.progress_callback(self.progress_tracker)
    
    def _is_file_operation(self, message: str) -> bool:
        """Check if message is related to file operations."""
        file_keywords = [
            'Reading', 'Extracting', 'Processing', 'Loaded', 'Found',
            '.DAT', '.OUT', 'TOPO', 'DEPTH', 'INFLOW', 'OUTFLOW',
            'HYSTRUC', 'SWMM', 'ARF', 'INFIL', 'RAIN', 'CHAN'
        ]
        return any(keyword in message for keyword in file_keywords)


class GUIMessageHandler(logging.Handler):
    """Custom logging handler that sends messages to the GUI."""
    
    def __init__(self, message_callback: Callable):
        super().__init__()
        self.message_callback = message_callback
        
    def emit(self, record):
        """Handle a log record by sending it to the GUI."""
        try:
            message = self.format(record)
            
            # Determine message type based on log level or `extra` field
            msg_type = getattr(record, 'msg_type', None)
            if msg_type is None:
                if record.levelno >= logging.ERROR:
                    msg_type = 'error'
                elif record.levelno >= logging.WARNING:
                    msg_type = 'warning'
                else:
                    msg_type = 'info'
            
            # Extract clean message (remove logger formatting)
            clean_message = record.getMessage()
            clean_message = MessageFormatter.extract_step_from_message(clean_message)
            
            self.message_callback(clean_message, msg_type)
            
        except Exception:
            # Fail silently to avoid recursive logging issues
            pass