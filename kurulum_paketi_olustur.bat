@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv ( echo Once kurulum.bat calistirilmali. & pause & exit /b 1 )
call .venv\Scripts\activate.bat
echo [1/2] Program derleniyor (PyInstaller)...
pyinstaller --noconfirm --clean --windowed --name "VesikalikPro" --icon ui\assets\app_icon.ico ^
  --add-data "ui;ui" --collect-all onnxruntime --hidden-import tkinter --collect-all webview --collect-all pillow_heif --collect-all rawpy --collect-binaries nvidia ^
  --hidden-import win32print --hidden-import win32ui --hidden-import win32gui app.py
if errorlevel 1 ( echo [HATA] Derleme basarisiz. & pause & exit /b 1 )
xcopy /E /I /Y models dist\VesikalikPro\models >nul
echo [2/2] Kurulum dosyasi olusturuluyor (Inno Setup)...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 bulunamadi. https://jrsoftware.org/isdl.php adresinden ucretsiz kurun ve tekrar calistirin.
  echo Program yine de dist\VesikalikPro klasorunde hazir: VesikalikPro.exe
  pause & exit /b 0
)
%ISCC% kurulum\vesikalik_pro.iss
echo.
echo Tamam: kurulum\cikti\HayalMedya_VesikalikPro_1.4_Kurulum.exe
pause
