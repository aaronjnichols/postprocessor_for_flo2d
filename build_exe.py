#!/usr/bin/env python3
"""
PyInstaller build script for FLO-2D Postprocessor executable.
Creates a standalone Windows executable with all dependencies bundled.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def clean_build_dirs():
    """Remove existing build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}...")
            shutil.rmtree(dir_name)

def create_version_info():
    """Create version info file for Windows executable"""
    version_info = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
filevers=(1, 0, 0, 0),
prodvers=(1, 0, 0, 0),
mask=0x3f,
flags=0x0,
OS=0x40004,
fileType=0x1,
subtype=0x0,
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'FLO-2D Postprocessor'),
    StringStruct(u'FileDescription', u'FLO-2D Postprocessor GUI'),
    StringStruct(u'FileVersion', u'1.0.0.0'),
    StringStruct(u'InternalName', u'FLO2D-Postprocessor'),
    StringStruct(u'LegalCopyright', u'MIT License'),
    StringStruct(u'OriginalFilename', u'FLO2D-Postprocessor.exe'),
    StringStruct(u'ProductName', u'FLO-2D Postprocessor'),
    StringStruct(u'ProductVersion', u'1.0.0.0')])
  ]), 
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("Created version_info.txt")

def build_executable():
    """Build the executable using PyInstaller"""
    
    # Create the PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',                    # Single executable file
        '--windowed',                   # No console window
        '--name=FLO2D-Postprocessor',   # Executable name
        '--icon=assets/icon.ico',       # Icon (if exists)
        '--version-file=version_info.txt',  # Version info
        '--add-data=config.json;.',     # Include config file
        '--add-data=requirements.txt;.', # Include requirements
        '--add-data=docs;docs',         # Include documentation
        '--hidden-import=tkinter',      # Ensure tkinter is included
        '--hidden-import=ttkthemes',    # Ensure themes are included
        '--hidden-import=PIL',          # For any image processing
        '--hidden-import=matplotlib',   # For plotting
        '--hidden-import=openpyxl',     # For Excel files
        '--hidden-import=xlsxwriter',   # For Excel writing
        'gui/launch_gui.py'             # Entry point
    ]
    
    # Remove icon if it doesn't exist
    if not os.path.exists('assets/icon.ico'):
        cmd = [c for c in cmd if not c.startswith('--icon')]
        print("Note: No icon file found, building without icon")
    
    print("Building executable...")
    print("Command:", ' '.join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("Error: PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    return True

def create_installer_files():
    """Create files needed for the installer"""
    
    # Create assets directory if it doesn't exist
    os.makedirs('assets', exist_ok=True)
    
    # Create a simple icon file placeholder (you should replace with actual icon)
    print("Note: Add a proper icon.ico file to the assets/ directory for better branding")
    
    # Create installer script template
    installer_script = """
; FLO-2D Postprocessor Installer Script for Inno Setup
; This script creates a Windows installer for the application

[Setup]
AppName=FLO-2D Postprocessor
AppVersion=1.0.0
DefaultDirName={autopf}\\FLO2D Postprocessor
DefaultGroupName=FLO-2D Postprocessor
OutputDir=installer_output
OutputBaseFilename=FLO2D-Postprocessor-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\\FLO2D-Postprocessor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\\*"; DestDir: "{app}\\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\FLO-2D Postprocessor"; Filename: "{app}\\FLO2D-Postprocessor.exe"
Name: "{group}\\{cm:UninstallProgram,FLO-2D Postprocessor}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\FLO-2D Postprocessor"; Filename: "{app}\\FLO2D-Postprocessor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\\FLO2D-Postprocessor.exe"; Description: "{cm:LaunchProgram,FLO-2D Postprocessor}"; Flags: nowait postinstall skipifsilent
"""
    
    with open('installer.iss', 'w') as f:
        f.write(installer_script)
    
    print("Created installer.iss (Inno Setup script)")
    print("To build installer: Download Inno Setup and compile installer.iss")

def main():
    """Main build process"""
    print("=" * 60)
    print("FLO-2D Postprocessor - Executable Builder")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Clean previous builds
    clean_build_dirs()
    
    # Create version info
    create_version_info()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Create installer files
    create_installer_files()
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"Executable: dist/FLO2D-Postprocessor.exe")
    print(f"Size: {os.path.getsize('dist/FLO2D-Postprocessor.exe') / (1024*1024):.1f} MB")
    print("\nNext steps:")
    print("1. Test the executable on a clean Windows system")
    print("2. Install Inno Setup and compile installer.iss to create setup.exe")
    print("3. Upload to GitHub releases or distribution platform")
    
    # Clean up temporary files
    if os.path.exists('version_info.txt'):
        os.remove('version_info.txt')
    
    print("\nBuild process completed successfully!")

if __name__ == '__main__':
    main()