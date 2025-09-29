@echo off
echo ========================================
echo   Fix Import Errors - GaSPipe
echo ========================================
echo.

REM Backup test files
echo Creating backups...
if exist tests\test_validate.py copy tests\test_validate.py tests\test_validate.py.backup
if exist tests\test_subprocess_wrapper.py copy tests\test_subprocess_wrapper.py tests\test_subprocess_wrapper.py.backup
if exist tests\test_pipeline_integration.py copy tests\test_pipeline_integration.py tests\test_pipeline_integration.py.backup

REM Fix imports using PowerShell
echo Fixing import statements...
powershell -Command "(Get-Content tests\test_validate.py) -replace 'from src\.gaspipe', 'from gaspipe' | Set-Content tests\test_validate.py"
powershell -Command "(Get-Content tests\test_subprocess_wrapper.py) -replace 'from src\.gaspipe', 'from gaspipe' | Set-Content tests\test_subprocess_wrapper.py"
powershell -Command "(Get-Content tests\test_pipeline_integration.py) -replace 'from src\.gaspipe', 'from gaspipe' | Set-Content tests\test_pipeline_integration.py"

echo.
echo ✓ Import statements fixed!
echo.
echo Now run: pytest tests/ -v
echo.
pause