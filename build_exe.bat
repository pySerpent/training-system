@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

if exist "requirements.txt" (
    python -m pip install -r requirements.txt
)

python -m pip install pyinstaller
if errorlevel 1 goto :error

echo Сборка приложения (это может занять несколько минут)...
python -m PyInstaller --noconfirm --onefile --windowed --name IBTraining --collect-all customtkinter main.py
if errorlevel 1 goto :error

echo Копирование базы данных...
if not exist "dist\data" mkdir "dist\data"
if exist "data\ib_training.db" (
    copy /Y "data\ib_training.db" "dist\data\ib_training.db" >nul
)

echo.
echo ГОТОВО! Файл IBTraining.exe находится в папке dist.
pause
exit /b 0

:error
echo.
echo Сборка остановлена из-за ошибки выше.
pause
exit /b 1
