import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import io
import os
import time
# Add parent directory to path to import main
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from main import batch_process_flo2d, process_flo2d
import shutil
import threading
import json
from ttkthemes import ThemedStyle
from .message_system import RichMessageFrame, StepIndicator, ProgressTracker
from .enhanced_logger import EnhancedTimingLogger, GUIMessageHandler

CONFIG_FILE = os.path.join(parent_dir, "config.json")

class RedirectText(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

class ToolTip:
    """Tooltip for widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        # Determine tooltip position based on widget type
        if isinstance(self.widget, (tk.Entry, tk.Text)):
            try:
                x, y, cx, cy = self.widget.bbox("insert")
                x += self.widget.winfo_rootx() + 25
                y += self.widget.winfo_rooty() + 20
            except tk.TclError:
                # Fallback if "insert" is not available
                x = self.widget.winfo_rootx() + 25
                y = self.widget.winfo_rooty() + 20
        else:
            # For other widgets, position tooltip near the widget
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#3E3E3E", foreground="#FFFFFF",
                         relief='solid', borderwidth=1, wraplength=200)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

class FLO2DPostProcessorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("FLO2D Post-Processor Lite")
        self.master.geometry("900x900")  # Increased height to accommodate new widgets
        self.master.configure(bg="#2E2E2E")

        # Initialize ThemedStyle and set to 'equilux'
        self.style = ThemedStyle(self.master)
        self.style.set_theme("equilux")  # Set 'equilux' as the exclusive theme

        # Initialize progress tracking
        self.progress_tracker = ProgressTracker()
        self.enhanced_logger = None

        self.create_widgets()
        self.load_settings()

        # Bind the close event to save settings
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Bind keyboard shortcuts
        self.master.bind('<Control-r>', lambda e: self.run_process_thread())
        self.master.bind('<Control-l>', lambda e: self.clear_output())
        self.master.bind('<F5>', lambda e: self.run_process_thread())
        self.master.focus_set()  # Allow window to receive key events

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        # FLO-2D Folders Section
        folders_label = ttk.Label(main_frame, text="FLO-2D Folders:")
        folders_label.grid(column=0, row=0, sticky=tk.W)
        ToolTip(folders_label, "Select one or more FLO-2D project folders to process.")

        # Folder management frame
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(column=0, row=1, columnspan=2, sticky=(tk.W, tk.E), pady=(5,0))
        folder_frame.columnconfigure(0, weight=1)

        # Customize Listbox with black background and white text
        self.folder_listbox = tk.Listbox(folder_frame, width=50, height=5, bg="#000000", fg="#FFFFFF", selectmode=tk.MULTIPLE)
        self.folder_listbox.grid(column=0, row=0, sticky=(tk.W, tk.E))
        ToolTip(self.folder_listbox, "List of FLO-2D project folders to be processed.")

        folder_buttons_frame = ttk.Frame(folder_frame)
        folder_buttons_frame.grid(column=1, row=0, sticky=tk.NW, padx=(10,0))
        add_btn = ttk.Button(folder_buttons_frame, text="Add", command=self.add_folder)
        add_btn.grid(column=0, row=0, sticky=tk.W, pady=(0, 5))
        ToolTip(add_btn, "Add a FLO-2D project folder to the list.")
        remove_btn = ttk.Button(folder_buttons_frame, text="Remove", command=self.remove_folder)
        remove_btn.grid(column=0, row=1, sticky=tk.W)
        ToolTip(remove_btn, "Remove the selected folder(s) from the list.")

        # EPSG Number Section
        epsg_label = ttk.Label(main_frame, text="EPSG Number:")
        epsg_label.grid(column=0, row=2, sticky=tk.W, pady=(15, 0))
        ToolTip(epsg_label, "Enter the EPSG code for spatial reference.")

        self.epsg_number = ttk.Entry(main_frame, width=20)
        self.epsg_number.grid(column=0, row=3, sticky=tk.W)
        ToolTip(self.epsg_number, "Enter a valid integer EPSG code (e.g., 4326).")

        # Shapefile Option
        self.create_shapefile = tk.BooleanVar()
        shapefile_cb = ttk.Checkbutton(
            main_frame,
            text="Create FLO-2D Data Points Shapefile",
            variable=self.create_shapefile,
            style='TCheckbutton'
        )
        shapefile_cb.grid(column=0, row=4, sticky=tk.W, pady=(10, 0))
        ToolTip(shapefile_cb, "Check to generate a shapefile of FLO-2D data points.")

        # --- New Section: Output Format Selection ---
        output_format_label = ttk.Label(main_frame, text="Output Format:")
        output_format_label.grid(column=0, row=5, sticky=tk.W, pady=(15, 0))
        ToolTip(output_format_label, "Select the format for saving the output data.")

        self.output_format = tk.StringVar(value="Shapefile")  # Default selection

        # Radio Buttons for Output Format
        shapefile_rb = ttk.Radiobutton(
            main_frame,
            text="Shapefile",
            variable=self.output_format,
            value="Shapefile"
        )
        shapefile_rb.grid(column=0, row=6, sticky=tk.W)
        ToolTip(shapefile_rb, "Save output data as Shapefile.")

        geopackage_rb = ttk.Radiobutton(
            main_frame,
            text="GeoPackage",
            variable=self.output_format,
            value="GeoPackage"
        )
        geopackage_rb.grid(column=0, row=7, sticky=tk.W)
        ToolTip(geopackage_rb, "Save output data as GeoPackage.")

        # Style Files Folder Section
        style_label = ttk.Label(main_frame, text="Style Files Folder:")
        style_label.grid(column=0, row=8, sticky=tk.W, pady=(15, 0))
        ToolTip(style_label, "Select the folder containing style files for processing.")

        style_frame = ttk.Frame(main_frame)
        style_frame.grid(column=0, row=9, sticky=(tk.W, tk.E))
        self.style_folder = ttk.Entry(style_frame, width=40, state='readonly')  # Set to readonly to prevent manual editing
        self.style_folder.grid(column=0, row=0, sticky=(tk.W, tk.E))
        ToolTip(self.style_folder, "Path to the folder containing style files.")
        browse_style_btn = ttk.Button(style_frame, text="Browse", command=self.browse_style_folder)
        browse_style_btn.grid(column=1, row=0, sticky=tk.W, padx=(5,0))
        ToolTip(browse_style_btn, "Browse to select the style files folder.")

        style_frame.columnconfigure(0, weight=1)

        # Step Indicator Section
        step_frame = ttk.LabelFrame(main_frame, text="Processing Steps", padding="5")
        step_frame.grid(column=0, row=10, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 5))
        step_frame.columnconfigure(0, weight=1)
        
        self.step_indicator = StepIndicator(step_frame)
        self.step_indicator.pack(fill=tk.X, expand=True)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(column=0, row=11, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 5))
        progress_frame.columnconfigure(0, weight=1)
        
        # Overall progress bar
        overall_label = ttk.Label(progress_frame, text="Overall Progress:")
        overall_label.grid(column=0, row=0, sticky=tk.W)
        
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.overall_progress.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=(2, 5))
        
        # Current step progress bar
        step_label = ttk.Label(progress_frame, text="Current Step:")
        step_label.grid(column=0, row=2, sticky=tk.W)
        
        self.step_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.step_progress.grid(column=0, row=3, sticky=(tk.W, tk.E), pady=(2, 5))
        
        # Progress Status Label
        self.progress_label = ttk.Label(progress_frame, text="Ready to process")
        self.progress_label.grid(column=0, row=4, sticky=tk.W, pady=(5, 0))
        
        # Processing Statistics
        self.stats_label = ttk.Label(progress_frame, text="")
        self.stats_label.grid(column=0, row=5, sticky=tk.W)

        # Enhanced Message Output Section
        output_label = ttk.Label(main_frame, text="Processing Messages:")
        output_label.grid(column=0, row=12, sticky=tk.W, pady=(10, 0))
        ToolTip(output_label, "Real-time processing messages with enhanced formatting.")
        
        # Rich message frame
        self.rich_message_frame = RichMessageFrame(main_frame)
        self.rich_message_frame.grid(column=0, row=13, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # Keep the old output_text reference for compatibility
        self.output_text = self.rich_message_frame.text_widget

        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(column=0, row=14, columnspan=2, sticky=(tk.W, tk.E), pady=(10,0))
        control_frame.columnconfigure(1, weight=1)
        
        # Clear output button
        clear_btn = ttk.Button(control_frame, text="Clear Output", command=self.clear_output)
        clear_btn.grid(column=0, row=0, sticky=tk.W)
        ToolTip(clear_btn, "Clear the output log display.\nKeyboard: Ctrl+L")
        
        # Run Button (larger and more prominent)
        self.run_btn = ttk.Button(control_frame, text="🚀 Start Processing", command=self.run_process_thread)
        self.run_btn.grid(column=1, row=0, sticky=tk.E)
        ToolTip(self.run_btn, "Start processing the selected FLO-2D folders.\nKeyboard: Ctrl+R or F5")

        # Configure grid weights for responsiveness
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(13, weight=1)  # Updated for rich message frame

    def on_message_received(self, message: str, msg_type: str = 'info'):
        """Callback for receiving messages from the processing system."""
        self.master.after(0, lambda: self.rich_message_frame.add_message(message, msg_type))
        
    def on_progress_update(self, progress_tracker):
        """Callback for receiving progress updates."""
        def update_ui():
            # Update progress bars
            overall_progress = progress_tracker.get_overall_progress() * 100
            step_progress = progress_tracker.current_step_progress * 100
            
            self.overall_progress['value'] = overall_progress
            self.step_progress['value'] = step_progress
            
            # Update step indicator
            # Map progress tracker steps to simple step indicator
            if progress_tracker.current_step <= 2:
                step_index = 0  # Setup
            elif progress_tracker.current_step <= 4:
                step_index = 1  # Analysis
            elif progress_tracker.current_step <= 6:
                step_index = 2  # Mapping
            elif progress_tracker.current_step <= 8:
                step_index = 3  # Reports
            else:
                step_index = 4  # Complete
                
            self.step_indicator.set_current_step(step_index)
            
            # Update progress text
            progress_text = progress_tracker.get_progress_text()
            self.progress_label.config(text=progress_text)
            
        self.master.after(0, update_ui)

    def add_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            if folder_selected not in self.folder_listbox.get(0, tk.END):
                # Check if it's a valid FLO-2D folder and show warning if not
                if not self.is_flo2d_folder(folder_selected):
                    result = messagebox.askyesno(
                        "Folder Validation", 
                        f"The selected folder does not appear to contain typical FLO-2D files.\n\n"
                        f"Folder: {folder_selected}\n\n"
                        f"Add anyway?",
                        icon='warning'
                    )
                    if not result:
                        return
                
                self.folder_listbox.insert(tk.END, folder_selected)
                self.save_settings()
            else:
                messagebox.showinfo("Duplicate Folder", "The selected folder is already in the list.")

    def remove_folder(self):
        selected_indices = self.folder_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one folder to remove.")
            return
        for index in reversed(selected_indices):
            self.folder_listbox.delete(index)
        self.save_settings()

    def browse_style_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.style_folder.configure(state='normal')
            self.style_folder.delete(0, tk.END)
            self.style_folder.insert(0, folder_selected)
            self.style_folder.configure(state='readonly')
            self.save_settings()

    def run_process_thread(self):
        # Validate inputs before starting
        validation_errors = self.validate_inputs()
        if validation_errors:
            messagebox.showerror("Input Validation Failed", "\n".join(validation_errors))
            return

        # Update UI for processing state
        self.set_widgets_state(main_frame=self.master, state='disabled')
        self.run_btn.config(text="⏳ Processing...", state='disabled')
        
        # Reset progress indicators
        self.overall_progress['value'] = 0
        self.step_progress['value'] = 0
        self.step_indicator.set_current_step(0)
        self.progress_label.config(text="Initializing processing...")
        self.stats_label.config(text="")
        
        # Clear previous messages
        self.rich_message_frame.clear_messages()
        
        # Add initial message
        self.rich_message_frame.add_message("🚀 Starting FLO-2D post-processing...", 'processing')

        # Run processing in a separate thread to keep GUI responsive
        threading.Thread(target=self.run_process, daemon=True).start()
    
    def validate_inputs(self):
        """Validate all user inputs and return list of errors"""
        errors = []
        
        if not self.folder_listbox.size():
            errors.append("• Please add at least one FLO-2D folder to process.")
        
        epsg = self.epsg_number.get().strip()
        if not epsg:
            errors.append("• EPSG number is required.")
        elif not epsg.isdigit():
            errors.append("• EPSG number must be a valid integer.")
        elif not (1000 <= int(epsg) <= 32767):
            errors.append("• EPSG number should be between 1000 and 32767.")
        
        style_folder = self.style_folder.get().strip()
        if style_folder and not os.path.isdir(style_folder):
            errors.append("• The specified style files folder does not exist.")
            
        # Validate that selected folders exist and contain FLO-2D files
        folders_to_check = list(self.folder_listbox.get(0, tk.END))
        invalid_folders = []
        for folder in folders_to_check:
            if not os.path.isdir(folder):
                invalid_folders.append(f"  - {folder} (does not exist)")
            elif not self.is_flo2d_folder(folder):
                invalid_folders.append(f"  - {folder} (no FLO-2D files found)")
        
        if invalid_folders:
            errors.append("• Invalid FLO-2D folders detected:")
            errors.extend(invalid_folders)
            
        return errors
    
    def is_flo2d_folder(self, folder_path):
        """Check if folder contains typical FLO-2D files"""
        flo2d_files = [
            # Core input files
            'CADPTS.DAT', 'TOPO.DAT', 'FPLAIN.DAT', 'MANNINGS_N.DAT',
            # Optional input files
            'ARF.DAT', 'INFLOW.DAT', 'FPXSEC.DAT', 'HYSTRUC.DAT', 
            'RAIN.DAT', 'SWMM.inp', 'SWMMFLORT.DAT', 'XSEC.DAT', 
            'CHAN.DAT', 'INFIL.DAT'
        ]
        existing_files = os.listdir(folder_path) if os.path.isdir(folder_path) else []
        return any(file in existing_files for file in flo2d_files)

    def format_time(self, seconds):
        """Format elapsed time in seconds to a human-readable string."""
        if seconds < 1:
            return f"{seconds:.2f} seconds"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours} hours, {minutes} minutes, {secs} seconds"
        elif minutes > 0:
            return f"{minutes} minutes, {secs} seconds"
        else:
            return f"{secs} seconds"

    def run_process(self):
        # Record start time
        start_time = time.time()
        file_paths = list(self.folder_listbox.get(0, tk.END))
        total_folders = len(file_paths)
        
        # Setup enhanced logging with GUI callbacks
        import logging
        
        # Create a logger for this processing session
        logger = logging.getLogger('FLO2D_GUI_Processing')
        logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # Add our GUI handler
        gui_handler = GUIMessageHandler(self.on_message_received)
        gui_handler.setLevel(logging.INFO)
        logger.addHandler(gui_handler)

        try:
            for i, file_path in enumerate(file_paths, 1):
                # Reset progress tracker for each folder
                self.progress_tracker = ProgressTracker()
                
                # Update folder progress information
                folder_name = os.path.basename(file_path)
                folder_message = f"📁 Processing folder {i}/{total_folders}: {folder_name}"
                self.on_message_received(folder_message, 'step')
                
                # Update stats
                elapsed = time.time() - start_time
                self.master.after(0, lambda: self.stats_label.config(
                    text=f"Folder {i}/{total_folders} | Elapsed: {self.format_time(elapsed)}"
                ))
                
                # Create enhanced timing logger for this folder
                self.enhanced_logger = EnhancedTimingLogger(
                    logger, 
                    message_callback=self.on_message_received,
                    progress_callback=self.on_progress_update
                )
                
                # Process the folder with enhanced logging
                result = self.process_flo2d_with_enhanced_logging(
                    file_path,
                    int(self.epsg_number.get()),
                    self.create_shapefile.get(),
                    verbose=True,
                    style_folder=self.style_folder.get(),
                    output_format=self.output_format.get()
                )
                
                # Mark folder completion
                self.on_message_received(f"✅ Completed folder: {folder_name}", 'success')
            
            # Calculate elapsed time
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Final completion
            self.step_indicator.set_current_step(4)  # Complete
            self.overall_progress['value'] = 100
            self.step_progress['value'] = 100
            
            # Update final status
            self.master.after(0, lambda: self.progress_label.config(text="All processing completed successfully! 🎉"))
            self.master.after(0, lambda: self.stats_label.config(
                text=f"Processed {total_folders} folder(s) in {self.format_time(elapsed_time)}"
            ))
            
            # Final completion message
            completion_message = f"🎉 All {total_folders} FLO-2D folders processed successfully!"
            self.on_message_received(completion_message, 'success')
            self.on_message_received(f"⏱️ Total processing time: {self.format_time(elapsed_time)}", 'info')
            
        except Exception as e:
            # Calculate elapsed time even for errors
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            self.master.after(0, lambda: self.progress_label.config(text="Processing failed"))
            self.master.after(0, lambda: self.stats_label.config(
                text=f"Failed after {self.format_time(elapsed_time)}"
            ))
            
            error_message = f"An error occurred: {str(e)}"
            self.on_message_received(error_message, 'error')
            self.on_message_received(f"Processing stopped after: {self.format_time(elapsed_time)}", 'error')
            messagebox.showerror("Processing Error", f"An error occurred during processing:\n{str(e)}")
        finally:
            self.set_widgets_state(main_frame=self.master, state='normal')
            self.run_btn.config(text="🚀 Start Processing", state='normal')
    
    def process_flo2d_with_enhanced_logging(self, file_path, coord_system, create_flo2d_points, verbose, style_folder, output_format):
        """Process FLO-2D with enhanced logging that integrates with our GUI system."""
        # Import here to avoid circular imports
        import logging
        from main import process_flo2d
        
        # Temporarily redirect the main processing logger to our enhanced system
        original_logger = logging.getLogger('FLO2D_Postprocessor')
        
        # Clear existing handlers and add our GUI handler
        for handler in original_logger.handlers[:]:
            original_logger.removeHandler(handler)
            
        gui_handler = GUIMessageHandler(self.on_message_received)
        gui_handler.setLevel(logging.INFO)
        original_logger.addHandler(gui_handler)
        
        try:
            # Process with the enhanced logging system
            result = process_flo2d(
                file_path,
                coord_system,
                create_flo2d_points,
                verbose,
                style_folder=style_folder,
                output_format=output_format
            )
            return result
        finally:
            # Restore original logging setup if needed
            pass

    def set_widgets_state(self, main_frame, state):
        """Recursively set the state of widgets that support the 'state' option."""
        for child in main_frame.winfo_children():
            # Skip frames
            if isinstance(child, ttk.Frame):
                self.set_widgets_state(child, state)
                continue
            # Check if widget has 'state' option
            try:
                child.configure(state=state)
            except tk.TclError:
                # Widget does not support 'state' option
                pass

    def load_settings(self):
        """Load settings from the configuration file."""
        if not os.path.exists(CONFIG_FILE):
            return  # No settings to load

        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Load FLO-2D Folders
            folders = config.get("flo2d_folders", [])
            for folder in folders:
                if os.path.isdir(folder):
                    self.folder_listbox.insert(tk.END, folder)
            
            # Load EPSG Number
            epsg = config.get("epsg_number", "")
            self.epsg_number.insert(0, epsg)
            
            # Load Shapefile Option
            shapefile = config.get("create_flo2d_points", False)
            self.create_shapefile.set(shapefile)
            
            # Load Style Files Folder
            style_folder = config.get("style_folder", "")
            self.style_folder.configure(state='normal')
            self.style_folder.insert(0, style_folder)
            self.style_folder.configure(state='readonly')
            
            # Load Output Format
            output_format = config.get("output_format", "Shapefile")
            self.output_format.set(output_format)
            
        except Exception as e:
            messagebox.showwarning("Load Settings", f"Failed to load settings:\n{str(e)}")

    def save_settings(self):
        """Save current settings to the configuration file."""
        config = {
            "flo2d_folders": list(self.folder_listbox.get(0, tk.END)),
            "epsg_number": self.epsg_number.get(),
            "create_flo2d_points": self.create_shapefile.get(),
            "style_folder": self.style_folder.get(),
            "output_format": self.output_format.get()  # Save output format
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            messagebox.showwarning("Save Settings", f"Failed to save settings:\n{str(e)}")

    def on_close(self):
        """Handle the window close event."""
        self.save_settings()
        self.master.destroy()
    
    def clear_output(self):
        """Clear the output text display"""
        self.rich_message_frame.clear_messages()
        
        # Reset progress indicators
        self.overall_progress['value'] = 0
        self.step_progress['value'] = 0
        self.step_indicator.set_current_step(0)
        
        # Reset labels
        self.progress_label.config(text="Output cleared - Ready to process")
        self.stats_label.config(text="")

def main():
    root = tk.Tk()
    app = FLO2DPostProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
