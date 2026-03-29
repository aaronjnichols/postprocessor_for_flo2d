@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "QGIS_PLUGINS_DIR=%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins"
set "PLUGIN_DIR=%QGIS_PLUGINS_DIR%\flo2d_postprocessor"

echo [1/4] Preparing plugin directory...
if not exist "%QGIS_PLUGINS_DIR%" mkdir "%QGIS_PLUGINS_DIR%"
if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

if not exist "%REPO_ROOT%\qgis_plugin\metadata.txt" (
    echo Could not find qgis_plugin files under: "%REPO_ROOT%\qgis_plugin"
    exit /b 1
)

echo [2/4] Copying qgis_plugin files...
xcopy "%REPO_ROOT%\qgis_plugin\*" "%PLUGIN_DIR%\" /E /I /Y >nul
if errorlevel 1 (
    echo Failed to copy plugin files.
    exit /b 1
)

echo [3/4] Writing project root hint...
> "%PLUGIN_DIR%\project_root.txt" echo %REPO_ROOT%
if errorlevel 1 (
    echo Failed to write project_root.txt hint file.
    exit /b 1
)

echo [4/4] Ensuring PYTHONPATH contains repository root...
powershell -NoProfile -Command "$repo=(Resolve-Path '%REPO_ROOT%').Path; $existing=[Environment]::GetEnvironmentVariable('PYTHONPATH','User'); if([string]::IsNullOrWhiteSpace($existing)){$new=$repo} elseif(($existing -split ';') -contains $repo){$new=$existing}else{$new=\"$repo;$existing\"}; [Environment]::SetEnvironmentVariable('PYTHONPATH',$new,'User'); Write-Output ('PYTHONPATH_USER=' + $new)"
if errorlevel 1 (
    echo Failed to update PYTHONPATH.
    exit /b 1
)

echo.
echo Install complete.
echo Plugin folder: "%PLUGIN_DIR%"
echo Restart QGIS, then enable "FLO-2D Postprocessor" in Plugins.

endlocal
