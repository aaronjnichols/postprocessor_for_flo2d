"""
Enhanced message system for FLO-2D Postprocessor GUI.
Provides rich formatting, color coding, and user-friendly messaging.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk

class MessageFormatter:
    """Handles message formatting with colors, icons, and user-friendly text."""
    
    MESSAGE_STYLES = {
        'info': {'color': '#17a2b8', 'icon': 'ℹ️', 'bg': '#e7f3ff'},
        'success': {'color': '#28a745', 'icon': '✅', 'bg': '#e8f5e8'}, 
        'processing': {'color': '#007bff', 'icon': '⚙️', 'bg': '#e7f1ff'},
        'warning': {'color': '#ffc107', 'icon': '⚠️', 'bg': '#fff8e1'},
        'error': {'color': '#dc3545', 'icon': '❌', 'bg': '#ffe6e6'},
        'file': {'color': '#6f42c1', 'icon': '📁', 'bg': '#f3e8ff'},
        'step': {'color': '#fd7e14', 'icon': '📍', 'bg': '#fff4e6'}
    }
    
    # User-friendly message translations
    FRIENDLY_MESSAGES = {
        # File operations
        "Extracting model data from FLO-2D files": "📊 Reading your flood model data...",
        "Model data extraction completed": "📊 Flood model data loaded successfully",
        "Creating necessary output directories": "📁 Setting up output folders...",
        "Output directories successfully created": "📁 Output folders ready",
        
        # Data processing
        "Converting model data to GeoDataFrame for spatial processing": "🗺️ Preparing data for mapping...",
        "Conversion to GeoDataFrame completed": "🗺️ Geographic data ready for analysis",
        "Extracting Area Reduction Factors (ARF)": "📊 Reading area reduction data...",
        "ARF data successfully merged with model data": "📊 Area reduction data integrated",
        
        # Spatial operations
        "Initiating creation of FLO-2D Points Output": "📍 Creating flood analysis points...",
        "Creating raster from gdf": "🖼️ Generating flood depth images...",
        "Raster creation completed": "🖼️ Flood depth maps created",
        
        # File processing
        "Processing Inflow Data": "💧 Analyzing water inflow sources...",
        "Processing Outflow Data": "🌊 Analyzing water outflow points...",
        "Extracting outflow data": "🌊 Reading outflow boundary data...",
        "Extracting inflow data": "💧 Reading inflow boundary data...",
        
        # Structures
        "Processing Hydraulic Structures": "🏗️ Analyzing bridges and culverts...",
        "Processing Floodplain Cross Sections": "📏 Analyzing channel cross-sections...",
        
        # Reports and outputs
        "Applying style files to shapefiles and rasters": "🎨 Adding visual styling to maps...",
        "Style application process completed": "🎨 Map styling applied successfully",
        
        # Completion
        "=== FLO-2D Postprocessor Completed Successfully ===": "🎉 Analysis completed successfully!",
        "FLO-2D Postprocessing completed successfully.": "✅ All flood analysis outputs ready"
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


class ProgressTracker:
    """Tracks progress across multiple levels (overall and current step)."""
    
    def __init__(self):
        self.total_steps = 10  # Main processing steps
        self.current_step = 0
        self.current_step_progress = 0
        self.step_names = [
            "Setup",
            "Data Loading", 
            "Spatial Prep",
            "Point Creation",
            "Raster Generation",
            "Inflow Analysis",
            "Outflow Analysis", 
            "Structure Analysis",
            "Report Generation",
            "Finalization"
        ]
        
    def set_total_steps(self, total: int):
        """Set the total number of steps."""
        self.total_steps = total
        
    def advance_step(self, step_name: Optional[str] = None):
        """Advance to the next major step."""
        self.current_step = min(self.current_step + 1, self.total_steps)
        self.current_step_progress = 0
        
    def set_step_progress(self, progress: float):
        """Set progress within current step (0.0 to 1.0)."""
        self.current_step_progress = max(0.0, min(1.0, progress))
        
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
        
    def get_progress_text(self) -> str:
        """Get formatted progress text."""
        overall_pct = int(self.get_overall_progress() * 100)
        step_pct = int(self.current_step_progress * 100)
        step_name = self.get_current_step_name()
        
        return f"Overall: {overall_pct}% (Step {self.current_step}/{self.total_steps}) | Current: {step_pct}% - {step_name}"


class RichMessageFrame(ttk.Frame):
    """Enhanced message display frame with rich formatting and scrolling."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.setup_widgets()
        self.formatter = MessageFormatter()
        
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
        
    def add_message(self, message: str, msg_type: str = 'info'):
        """Add a formatted message to the display."""
        formatted = self.formatter.format_message(message, msg_type)
        
        self.text_widget.configure(state='normal')
        
        # Insert the message with appropriate styling
        self.text_widget.insert(tk.END, formatted['text'] + '\n', msg_type)
        
        # Auto-scroll to bottom
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
        
    def clear_messages(self):
        """Clear all messages from display."""
        self.text_widget.configure(state='normal')
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.configure(state='disabled')


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