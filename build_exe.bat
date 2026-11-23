@echo off
rem Build IBTraining.exe with PyInstaller.
rem Run from the project root inside the activated virtual environment.
pip install pyinstaller
pyinstaller --noconfirm --windowed --name IBTraining --collect-data customtkinter main.py
if errorlevel 1 exit /b 1
xcopy /E /I /Y data dist\IBTraining\data >nul
echo Done: dist\IBTraining\IBTraining.exe
