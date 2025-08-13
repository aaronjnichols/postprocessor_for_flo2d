"""
Enhanced message system for FLO-2D Postprocessor GUI.
Provides rich formatting, color coding, and technical messaging for FLO-2D professionals.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk

# Simplified: templates and smart tracker removed in favor of centralized Messenger
from typing import Optional as _Optional  # alias to preserve type hints below
try:
    # Backward-compatible alias for removed type
    from typing import Any as FileProcessingResult  # type: ignore
except Exception:  # pragma: no cover
    FileProcessingResult = object  # fallback

class MessageFormatter:
    """Handles message formatting with colors, icons, and user-friendly text."""
    
    MESSAGE_STYLES = {
        # Enhanced technical categories
        'discovery': {'color': '#6c757d', 'icon': '🔍', 'bg': '#f8f9fa'},
        'extraction': {'color': '#17a2b8', 'icon': '📄', 'bg': '#e7f3ff'},
        'processing': {'color': '#007bff', 'icon': '⚙️', 'bg': '#e7f1ff'},
        'spatial': {'color': '#28a745', 'icon': '🗺️', 'bg': '#e8f5e8'},
        'validation': {'color': '#ffc107', 'icon': '✅', 'bg': '#fff8e1'},
        'output': {'color': '#6f42c1', 'icon': '📊', 'bg': '#f3e8ff'},
        'warning': {'color': '#fd7e14', 'icon': '⚠️', 'bg': '#fff4e6'},
        'error': {'color': '#dc3545', 'icon': '❌', 'bg': '#ffe6e6'},
        'success': {'color': '#198754', 'icon': '🎉', 'bg': '#d4edda'},
        
        # Legacy categories for backward compatibility
        'info': {'color': '#6c757d', 'icon': 'ℹ️', 'bg': '#f8f9fa'},
        'file': {'color': '#17a2b8', 'icon': '📁', 'bg': '#e7f3ff'},
        'step': {'color': '#fd7e14', 'icon': '📍', 'bg': '#fff4e6'}
    }
    
    # User-friendly message translations
    FRIENDLY_MESSAGES = {
        # File operations
        "Extracting model data from FLO-2D files": "Extracting model data from FLO-2D files...",
        "Model data extraction completed": "Model data extraction completed",
        "Creating necessary output directories": "Setting up output folders...",
        "Output directories successfully created": "Output folders ready",
        
        # Data processing
        "Converting model data to GeoDataFrame for spatial processing": "Converting model data to GeoDataFrame...",
        "Conversion to GeoDataFrame completed": "Converting model data to GeoDataFrame completed",
        "Extracting Area Reduction Factors (ARF)": "Extracting area reduction factors...",
        "ARF data successfully merged with model data": "Area reduction factor extraction completed",
        
        # Spatial operations
        "Initiating creation of flow direction arrows": "Creating flow direction arrows...",
        "Creating raster from gdf": "Generating model data rasters...",
        "Raster creation completed": "Raster creation completed",
        
        # File processing
        "Processing Inflow Data": "Processing inflow data...",
        "Processing Outflow Data": "Processing outflow data...",
        
        # Structures
        "Processing Hydraulic Structures": "Processing hydraulic structures...",
        "Processing Floodplain Cross Sections": "Processing floodplain cross-sections...",
        
        # Reports and outputs
        "Applying style files to shapefiles and rasters": "Adding GIS styles to geospatial data...",
        "Style application process completed": "GIS styling completed",
        
        # Completion
        "=== FLO-2D Postprocessor Completed Successfully ===": "FLO-2D model postprocessing completed successfully!",
        "FLO-2D Postprocessing completed successfully.": "Contact Aaron Nichols for custom postprocessing services."
    }
    
    @classmethod
    def format_message(cls, message: str, msg_type: str = 'info', include_timestamp: bool = True) -> Dict[str, Any]:
        """
        Format a message with styling and user-friendly text.
        
        Args:
            message: Original message text
            msg_type: Type of message (info, success, processing, warning, error, file, step)
            include_timestamp: Whether to include timestamp
            
        Returns:
            Dictionary with formatted message components
        """
        # Translate technical messages to user-friendly versions
        friendly_text = cls.FRIENDLY_MESSAGES.get(message, message)
        
        # Get style for message type
        style = cls.MESSAGE_STYLES.get(msg_type, cls.MESSAGE_STYLES['info'])
        
        # Create timestamp
        timestamp = datetime.now().strftime("%H:%M:%S") if include_timestamp else ""
        
        # Format the display text
        if include_timestamp:
            display_text = f"{timestamp} {style['icon']} {friendly_text}"
        else:
            display_text = f"{style['icon']} {friendly_text}"
        
        return {
            'text': display_text,
            'original': message,
            'type': msg_type,
            'color': style['color'],
            'bg_color': style['bg'],
            'icon': style['icon'],
            'timestamp': timestamp,
            'friendly_text': friendly_text
        }
    
    @classmethod
    def extract_step_from_message(cls, message: str) -> Optional[str]:
        """Extract step information from timing logger messages."""
        if "Step time:" in message:
            # Extract the main message before timing info
            return message.split(" (Step time:")[0]
        return message
    
    # Note: file/processing-specific template formatting removed for simplicity.


class ProgressTracker:
    """Tracks progress across multiple levels with technical file-specific details."""
    
    def __init__(self):
        self.total_steps = 8  # Streamlined technical steps
        self.current_step = 0
        self.current_step_progress = 0
        self.current_file = ""
        self.current_operation = ""
        self.files_processed = 0
        self.total_files = 0
        
        # Technical step names for FLO-2D professionals
        self.step_names = [
            "File Discovery",
            "Model Data Extraction", 
            "Spatial Processing",
            "Vector Generation",
            "Raster Creation",
            "Analysis & Validation",
            "Output Generation",
            "Completion"
        ]
        
        # Detailed step descriptions
        self.step_descriptions = {
            0: "Scanning for FLO-2D model files",
            1: "Extracting data from .DAT and .OUT files",
            2: "Converting to geographic coordinate system",
            3: "Creating shapefiles and vector layers",
            4: "Generating flood depth and velocity rasters",
            5: "Validating data integrity and model consistency",
            6: "Creating technical reports and visualizations",
            7: "Finalizing outputs and cleanup"
        }
        
    def set_total_steps(self, total: int):
        """Set the total number of steps."""
        self.total_steps = total
        
    def advance_step(self, step_name: Optional[str] = None):
        """Advance to the next major step."""
        self.current_step = min(self.current_step + 1, self.total_steps)
        self.current_step_progress = 0
        self.current_file = ""
        self.current_operation = ""
        
    def set_step_progress(self, progress: float):
        """Set progress within current step (0.0 to 1.0)."""
        self.current_step_progress = max(0.0, min(1.0, progress))
    
    def set_current_file(self, filename: str):
        """Set the current file being processed."""
        self.current_file = filename
    
    def set_current_operation(self, operation: str):
        """Set the current operation being performed."""
        self.current_operation = operation
    
    def set_file_counts(self, processed: int, total: int):
        """Set file processing counts."""
        self.files_processed = processed
        self.total_files = total
        
    def get_overall_progress(self) -> float:
        """Get overall progress as percentage (0.0 to 1.0)."""
        if self.total_steps == 0:
            return 0.0
        step_progress = (self.current_step - 1) / self.total_steps
        current_step_contribution = self.current_step_progress / self.total_steps
        return min(1.0, step_progress + current_step_contribution)
        
    def get_current_step_name(self) -> str:
        """Get the name of the current step."""
        if self.current_step <= len(self.step_names):
            return self.step_names[self.current_step - 1]
        return f"Step {self.current_step}"
    
    def get_current_step_description(self) -> str:
        """Get detailed description of current step."""
        if self.current_step <= len(self.step_descriptions):
            return self.step_descriptions.get(self.current_step - 1, "Processing...")
        return "Processing..."
        
    def get_progress_text(self) -> str:
        """Get formatted technical progress text."""
        overall_pct = int(self.get_overall_progress() * 100)
        step_pct = int(self.current_step_progress * 100)
        step_name = self.get_current_step_name()
        
        # Create detailed progress text for technical users
        base_text = f"Overall: {overall_pct}% ({self.current_step}/{self.total_steps}) | {step_name}: {step_pct}%"
        
        # Add file-specific details if available
        if self.current_file:
            base_text += f" - {self.current_file}"
        elif self.current_operation:
            base_text += f" - {self.current_operation}"
        
        # Add file counts if relevant
        if self.total_files > 0:
            base_text += f" ({self.files_processed}/{self.total_files} files)"
        
        return base_text


class RichMessageFrame(ttk.Frame):
    """Enhanced message display frame with rich formatting and scrolling."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.setup_widgets()
        self.formatter = MessageFormatter()
        self.message_map = {}  # message_id -> (start_line, end_line) mapping
        
    def setup_widgets(self):
        """Setup the rich message display widgets."""
        # Create scrollable text area
        self.text_frame = ttk.Frame(self)
        self.text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text widget with scrollbar
        self.text_widget = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            height=15,
            font=('Segoe UI', 10),
            bg='#2E2E2E',
            fg='#FFFFFF',
            insertbackground='#FFFFFF',
            selectbackground='#404040',
            state='disabled'
        )
        
        scrollbar = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for different message types
        self.setup_text_tags()
        
    def setup_text_tags(self):
        """Setup text tags for different message styles."""
        for msg_type, style in MessageFormatter.MESSAGE_STYLES.items():
            self.text_widget.tag_configure(
                msg_type,
                foreground=style['color'],
                font=('Segoe UI', 10, 'normal')
            )
            
        # Special tags
        self.text_widget.tag_configure('timestamp', foreground='#888888', font=('Segoe UI', 9))
        self.text_widget.tag_configure('success_bold', foreground='#28a745', font=('Segoe UI', 10, 'bold'))
        
    def add_message(self, message: str, msg_type: str = 'info', message_id: str = None):
        """Add a formatted message to the display."""
        formatted = self.formatter.format_message(message, msg_type)
        
        self.text_widget.configure(state='normal')
        
        # Get current position for message tracking
        start_line = self.text_widget.index(tk.END)
        
        # Insert the message with appropriate styling
        self.text_widget.insert(tk.END, formatted['text'] + '\n', msg_type)
        
        # Track message position if ID provided
        if message_id:
            end_line = self.text_widget.index(tk.END)
            self.message_map[message_id] = (start_line, end_line)
        
        # Auto-scroll to bottom
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
    
    # Removed specialized add_* methods; use add_message for all categories.
    
    def update_message(self, message_id: str, new_message: str, msg_type: str = 'processing'):
        """Update an existing message in place."""
        if message_id not in self.message_map:
            # Fallback to adding new message
            self.add_message(new_message, msg_type, message_id)
            return
        
        start_line, end_line = self.message_map[message_id]
        formatted = self.formatter.format_message(new_message, msg_type)
        
        self.text_widget.configure(state='normal')
        self.text_widget.delete(start_line, end_line)
        self.text_widget.insert(start_line, formatted['text'] + '\n', msg_type)
        
        # Update tracking
        new_end_line = self.text_widget.index(f"{start_line} + 1 line")
        self.message_map[message_id] = (start_line, new_end_line)
        
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
    
    def replace_message(self, message_id: str, new_message: str, msg_type: str = 'validation'):
        """Replace an existing message with new content."""
        self.update_message(message_id, new_message, msg_type)
        return message_id
    
    def clear_messages(self):
        """Clear all messages from display."""
        self.text_widget.configure(state='normal')
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.configure(state='disabled')
        self.message_map.clear()
        
    # Smart tracker removed; messages are pushed by the centralized Messenger.


class StepIndicator(ttk.Frame):
    """Simple visual step indicator showing main processing phases."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_step = 0
        self.steps = ["Setup", "Analysis", "Mapping", "Reports", "Complete"]
        self.setup_widgets()
        
    def setup_widgets(self):
        """Setup the step indicator widgets."""
        self.step_labels = []
        
        for i, step_name in enumerate(self.steps):
            # Create frame for each step
            step_frame = ttk.Frame(self)
            step_frame.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Step label
            label = ttk.Label(
                step_frame,
                text=f"⏳ {step_name}",
                font=('Segoe UI', 9),
                foreground='#888888'
            )
            label.pack()
            
            self.step_labels.append(label)
            
            # Add separator (except for last step)
            if i < len(self.steps) - 1:
                sep_label = ttk.Label(self, text="→", foreground='#666666')
                sep_label.pack(side=tk.LEFT, padx=2)
                
    def set_current_step(self, step_index: int):
        """Update the visual indicator for current step."""
        self.current_step = step_index
        
        for i, label in enumerate(self.step_labels):
            if i < step_index:
                # Completed steps
                label.configure(text=f"✅ {self.steps[i]}", foreground='#28a745')
            elif i == step_index:
                # Current step
                label.configure(text=f"⚙️ {self.steps[i]}", foreground='#007bff')
            else:
                # Pending steps
                label.configure(text=f"⏳ {self.steps[i]}", foreground='#888888')