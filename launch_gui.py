#!/usr/bin/env python3
"""
Simple launcher for the FLO-2D Post-Processor GUI
"""
import sys
import os

def main():
    """Launch the FLO-2D GUI"""
    print("=" * 60)
    print("          FLO-2D Post-Processor GUI Launcher")
    print("=" * 60)
    print()
    
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        print("Loading GUI components...")
        from flo2d_postprocessor_gui import main as gui_main
        
        print("Starting GUI...")
        print()
        print("The FLO-2D Post-Processor GUI should now be visible.")
        print("Close this console window or press Ctrl+C to exit.")
        print()
        
        # Launch the GUI
        gui_main()
        
    except KeyboardInterrupt:
        print("\nGUI closed by user.")
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nPlease ensure all required packages are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nIf the error persists, please check the console output above.")
    
    print("\nGUI session ended.")
    input("Press Enter to close this window...")

if __name__ == "__main__":
    main()