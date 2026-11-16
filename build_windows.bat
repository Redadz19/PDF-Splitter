@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto failed
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto failed
pyinstaller --noconfirm --clean --windowed --name "PDF Splitter" --collect-all fitz --collect-all PySide6 main.py
if errorlevel 1 goto failed
echo.
echo Application built successfully: dist\PDF Splitter\PDF Splitter.exe
echo Next: install Inno Setup 6, open installer.iss and click Compile.
pause
exit /b 0
:failed
echo.
echo Build failed. Check the error messages above.
pause
exit /b 1
