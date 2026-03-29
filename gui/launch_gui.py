#!/usr/bin/env python3
"""
Simple launcher for the FLO-2D Post-Processor GUI
"""
import sys
import os

from core.logger import setup_logger

def main():
    """Launch the FLO-2D GUI"""
    # Check if we're running in windowed mode (no console)
    is_windowed = not sys.stdin or not sys.stdin.isatty()
    logger = setup_logger("FLO2D_GUI_Launcher")
    
    if not is_windowed:
        logger.info("=" * 60)
        logger.info("          FLO-2D Post-Processor GUI Launcher")
        logger.info("=" * 60)
    
    try:
        # Add parent directory to path (where main.py is located)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        if not is_windowed:
            logger.info("Loading GUI components...")
        
        from gui.flo2d_postprocessor_gui import main as gui_main
        
        if not is_windowed:
            logger.info("Starting GUI...")
            logger.info("The FLO-2D Post-Processor GUI should now be visible.")
            logger.info("Close this console window or press Ctrl+C to exit.")
        
        # Launch the GUI
        gui_main()
        
    except KeyboardInterrupt:
        if not is_windowed:
            logger.info("GUI closed by user.")
    except ImportError as e:
        # For windowed mode, create a simple error dialog
        if is_windowed:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()  # Hide the main window
                messagebox.showerror("Import Error", 
                    f"Missing dependencies: {e}\n\n"
                    "Please ensure all required packages are installed.")
                root.destroy()
            except:
                pass  # Fail silently if we can't show the dialog
        else:
            logger.error("Import Error: %s", e)
            logger.info("Please ensure all required packages are installed:")
            logger.info("pip install -r requirements.txt")
    except Exception as e:
        # For windowed mode, create a simple error dialog
        if is_windowed:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()  # Hide the main window
                messagebox.showerror("Error", 
                    f"An error occurred: {e}\n\n"
                    "Please check the installation and try again.")
                root.destroy()
            except:
                pass  # Fail silently if we can't show the dialog
        else:
            logger.error("Error: %s", e)
            logger.info("If the error persists, please check the console output above.")
    
    # Only prompt for input if we have a console
    if not is_windowed:
        logger.info("GUI session ended.")
        try:
            input("Press Enter to close this window...")
        except:
            pass  # Fail silently if input is not available

if __name__ == "__main__":
    main()
