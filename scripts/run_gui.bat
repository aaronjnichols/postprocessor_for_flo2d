@echo off
echo Starting FLO-2D Post-Processor GUI...
echo.
cd /d "%~dp0.."
python gui\launch_gui.py
echo.
echo GUI closed.
pause