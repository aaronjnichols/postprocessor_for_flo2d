import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import io
import os
import time
from main import batch_process_flo2d, process_flo2d
import shutil
import threading
import json
from ttkthemes import ThemedStyle

CONFIG_FILE = "config.json"

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
        self.master.geometry("800x800")  # Increased height to accommodate new widgets
        self.master.configure(bg="#2E2E2E")

        # Initialize ThemedStyle and set to 'equilux'
        self.style = ThemedStyle(self.master)
        self.style.set_theme("equilux")  # Set 'equilux' as the exclusive theme

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
        self.folder_listbox.bind('<Double-Button-1>', self.show_folder_contents)
        ToolTip(self.folder_listbox, "List of FLO-2D project folders to be processed. Double-click to preview folder contents.")

        folder_buttons_frame = ttk.Frame(folder_frame)
        folder_buttons_frame.grid(column=1, row=0, sticky=tk.NW, padx=(10,0))
        add_btn = ttk.Button(folder_buttons_frame, text="Add", command=self.add_folder)
        add_btn.grid(column=0, row=0, sticky=tk.W, pady=(0, 5))
        ToolTip(add_btn, "Add a FLO-2D project folder to the list.")
        remove_btn = ttk.Button(folder_buttons_frame, text="Remove", command=self.remove_folder)
        remove_btn.grid(column=0, row=1, sticky=tk.W, pady=(0, 5))
        ToolTip(remove_btn, "Remove the selected folder(s) from the list.")
        preview_btn = ttk.Button(folder_buttons_frame, text="Preview", command=self.preview_selected_folder)
        preview_btn.grid(column=0, row=2, sticky=tk.W)
        ToolTip(preview_btn, "Preview FLO-2D files in the selected folder.")

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

        # Output Section
        output_label = ttk.Label(main_frame, text="Output:")
        output_label.grid(column=0, row=10, sticky=tk.W, pady=(15, 0))
        ToolTip(output_label, "Displays the processing logs and results.")

        # Customize Text widget with black background and white text
        self.output_text = tk.Text(main_frame, wrap=tk.WORD, width=80, height=15, bg="#000000", fg="#FFFFFF", state='disabled')
        self.output_text.grid(column=0, row=11, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        ToolTip(self.output_text, "Log output of the processing steps.")

        # Progress Section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(column=0, row=12, columnspan=2, sticky=(tk.W, tk.E), pady=(10,0))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress Bar
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.grid(column=0, row=0, sticky=(tk.W, tk.E), pady=(0,5))
        
        # Progress Status Label
        self.progress_label = ttk.Label(progress_frame, text="Ready to process")
        self.progress_label.grid(column=0, row=1, sticky=tk.W)
        
        # Processing Statistics
        self.stats_label = ttk.Label(progress_frame, text="")
        self.stats_label.grid(column=0, row=2, sticky=tk.W)

        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(column=0, row=13, columnspan=2, sticky=(tk.W, tk.E), pady=(10,0))
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
        main_frame.rowconfigure(11, weight=1)

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
        self.progress.start()
        self.progress_label.config(text="Initializing processing...")
        self.stats_label.config(text="")

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
        flo2d_files = ['CADPTS.DAT', 'TOPO.DAT', 'FPLAIN.DAT', 'MANNINGS.DAT']
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
        self.output_text.configure(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.configure(state='disabled')

        # Record start time
        start_time = time.time()
        file_paths = list(self.folder_listbox.get(0, tk.END))
        total_folders = len(file_paths)
        
        old_stdout = sys.stdout
        sys.stdout = RedirectText(self.output_text)

        try:
            for i, file_path in enumerate(file_paths, 1):
                # Update progress information
                self.master.after(0, lambda: self.progress_label.config(
                    text=f"Processing folder {i}/{total_folders}: {os.path.basename(file_path)}"
                ))
                self.master.after(0, lambda: self.stats_label.config(
                    text=f"Elapsed: {self.format_time(time.time() - start_time)}"
                ))
                
                print(f"Processing folder {i}/{total_folders}: {file_path}")
                print("-" * 50)
                result = process_flo2d(
                    file_path,
                    int(self.epsg_number.get()),
                    self.create_shapefile.get(),
                    verbose=True,
                    style_folder=self.style_folder.get(),
                    output_format=self.output_format.get()
                )
                print(result)
                print("\n")
            
            # Calculate elapsed time
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Update final status
            self.master.after(0, lambda: self.progress_label.config(text="Processing completed successfully"))
            self.master.after(0, lambda: self.stats_label.config(
                text=f"Processed {total_folders} folder(s) in {self.format_time(elapsed_time)}"
            ))
            
            # Final completion message with timing
            completion_message = "\n" + "=" * 50 + "\n"
            completion_message += "All FLO-2D folders processed successfully\n"
            completion_message += f"Total processing time: {self.format_time(elapsed_time)}\n"
            completion_message += "=" * 50 + "\n"
            print(completion_message)
            
        except Exception as e:
            # Calculate elapsed time even for errors
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            self.master.after(0, lambda: self.progress_label.config(text="Processing failed"))
            self.master.after(0, lambda: self.stats_label.config(
                text=f"Failed after {self.format_time(elapsed_time)}"
            ))
            
            error_message = f"\nAn error occurred: {str(e)}\n"
            error_message += f"Processing stopped after: {self.format_time(elapsed_time)}\n"
            print(error_message)
            messagebox.showerror("Processing Error", f"An error occurred during processing:\n{str(e)}")
        finally:
            sys.stdout = old_stdout
            self.progress.stop()
            self.set_widgets_state(main_frame=self.master, state='normal')
            self.run_btn.config(text="🚀 Start Processing", state='normal')

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
        self.output_text.configure(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.configure(state='disabled')
        self.progress_label.config(text="Output cleared - Ready to process")
        self.stats_label.config(text="")
    
    def show_folder_contents(self, event=None):
        """Show contents of double-clicked folder"""
        selection = self.folder_listbox.curselection()
        if selection:
            folder_path = self.folder_listbox.get(selection[0])
            self.preview_folder_contents(folder_path)
    
    def preview_selected_folder(self):
        """Preview contents of selected folder"""
        selection = self.folder_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder to preview.")
            return
        folder_path = self.folder_listbox.get(selection[0])
        self.preview_folder_contents(folder_path)
    
    def preview_folder_contents(self, folder_path):
        """Show folder contents in a popup window"""
        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", f"Folder does not exist: {folder_path}")
            return
            
        # Create preview window
        preview_window = tk.Toplevel(self.master)
        preview_window.title(f"Folder Preview: {os.path.basename(folder_path)}")
        preview_window.geometry("600x500")
        preview_window.configure(bg="#2E2E2E")
        
        # Apply theme to preview window
        preview_style = ThemedStyle(preview_window)
        preview_style.set_theme("equilux")
        
        main_preview_frame = ttk.Frame(preview_window, padding="10")
        main_preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Folder path label
        path_label = ttk.Label(main_preview_frame, text=f"Path: {folder_path}", font=('TkDefaultFont', 9))
        path_label.pack(anchor=tk.W, pady=(0,10))
        
        # Files list
        files_label = ttk.Label(main_preview_frame, text="Files in folder:")
        files_label.pack(anchor=tk.W)
        
        # Create listbox with scrollbar
        list_frame = ttk.Frame(main_preview_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        files_listbox = tk.Listbox(list_frame, bg="#000000", fg="#FFFFFF", font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=files_listbox.yview)
        files_listbox.configure(yscrollcommand=scrollbar.set)
        
        files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate files list
        try:
            files = sorted(os.listdir(folder_path))
            flo2d_files = ['CADPTS.DAT', 'TOPO.DAT', 'FPLAIN.DAT', 'MANNINGS.DAT', 'HYSTRUC.DAT', 
                          'FPXSEC.DAT', 'CHAN.DAT', 'XSEC.DAT', 'RAIN.DAT', 'SWMM.inp', 'INFLOW.DAT']
            
            for file in files:
                if os.path.isfile(os.path.join(folder_path, file)):
                    if file in flo2d_files:
                        files_listbox.insert(tk.END, f"✓ {file} (FLO-2D file)")
                        files_listbox.itemconfig(tk.END, {'fg': '#90EE90'})  # Light green
                    elif file.endswith(('.OUT', '.out')):
                        files_listbox.insert(tk.END, f"→ {file} (Output file)")
                        files_listbox.itemconfig(tk.END, {'fg': '#87CEEB'})  # Sky blue
                    else:
                        files_listbox.insert(tk.END, f"  {file}")
                        
            if not files:
                files_listbox.insert(tk.END, "No files found in folder")
                
        except PermissionError:
            files_listbox.insert(tk.END, "Permission denied - cannot read folder contents")
        except Exception as e:
            files_listbox.insert(tk.END, f"Error reading folder: {str(e)}")
        
        # Status frame
        status_frame = ttk.Frame(main_preview_frame)
        status_frame.pack(fill=tk.X, pady=(10,0))
        
        is_valid = self.is_flo2d_folder(folder_path)
        status_color = "#90EE90" if is_valid else "#FFB6C1"
        status_text = "✓ Valid FLO-2D folder" if is_valid else "⚠ No typical FLO-2D files detected"
        
        status_label = tk.Label(status_frame, text=status_text, fg=status_color, bg="#2E2E2E")
        status_label.pack(anchor=tk.W)
        
        # Close button
        close_btn = ttk.Button(main_preview_frame, text="Close", command=preview_window.destroy)
        close_btn.pack(pady=(10,0))

def main():
    root = tk.Tk()
    app = FLO2DPostProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
