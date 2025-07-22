@echo off
REM Setup script for FLO-2D Postprocessor
python -m venv venv
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
call venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
echo Setup complete.
