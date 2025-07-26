#!/usr/bin/env python3
"""
Test script to verify the FLO-2D GUI launches successfully
"""
import tkinter as tk
import threading
import time
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def auto_close_gui(root, delay=3):
    """Automatically close the GUI after a delay"""
    time.sleep(delay)
    try:
        root.quit()
        root.destroy()
    except:
        pass

def test_gui():
    """Test the FLO-2D GUI"""
    try:
        # Import the GUI module
        from flo2d_postprocessor_gui import FLO2DPostProcessorGUI
        
        print("Creating GUI window...")
        root = tk.Tk()
        
        # Start auto-close thread
        close_thread = threading.Thread(target=auto_close_gui, args=(root, 5), daemon=True)
        close_thread.start()
        
        print("Initializing FLO-2D GUI...")
        app = FLO2DPostProcessorGUI(root)
        
        print("GUI created successfully! Window will close automatically in 5 seconds.")
        print("If you see the window appear, the GUI is working correctly.")
        
        # Run the GUI
        root.mainloop()
        
        print("GUI test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error creating GUI: {e}")
        return False

if __name__ == "__main__":
    success = test_gui()
    if success:
        print("\n✅ GUI test PASSED - The FLO-2D post-processor GUI is working correctly!")
    else:
        print("\n❌ GUI test FAILED - There was an issue with the GUI")
    
    input("Press Enter to continue...")