#!/usr/bin/env python3
"""
Validate that the GUI components work correctly
"""
import sys
import os

def validate_gui():
    """Validate GUI functionality without showing the window"""
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        print("Testing GUI components...")
        
        # Test imports
        from flo2d_postprocessor_gui import FLO2DPostProcessorGUI
        import tkinter as tk
        from ttkthemes import ThemedStyle
        print("✅ All required modules import successfully")
        
        # Test creating GUI object (hidden)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        app = FLO2DPostProcessorGUI(root)
        print("✅ GUI object created successfully")
        
        # Test validation method
        errors = app.validate_inputs()
        print("✅ Input validation method works")
        
        # Test folder validation method
        is_flo2d = app.is_flo2d_folder(".")
        print("✅ Folder validation method works")
        
        # Clean up
        root.destroy()
        print("✅ All GUI components validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_gui()
    if success:
        print("\n🎉 GUI is ready to use!")
        print("\nTo launch the GUI, run one of these:")
        print("  • python flo2d_postprocessor_gui.py")
        print("  • python launch_gui.py")
        print("  • Double-click run_gui.bat")
    else:
        print("\n❌ GUI validation failed")