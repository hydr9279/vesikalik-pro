@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Hayal Medya Vesikalik Pro - Kurulum
echo ==========================================================
echo   Hayal Medya Vesikalik Pro 1.1 - Kurulum
echo ==========================================================
py -3.12 --version >nul 2>nul
if errorlevel 1 (
  echo [HATA] Python 3.12 bulunamadi.
  echo https://www.python.org/downloads/ adresinden Python 3.12 kurun,
  echo kurulumda "Add python.exe to PATH" kutusunu isaretleyin ve bu dosyayi tekrar calistirin.
  pause & exit /b 1
)
set REQ=requirements_directml.txt
powershell -NoProfile -Command "if ((Get-CimInstance Win32_VideoController).Name -match 'NVIDIA') { exit 0 } else { exit 1 }"
if not errorlevel 1 (
  set REQ=requirements_nvidia.txt
  echo NVIDIA ekran karti bulundu: CUDA hizlandirma kurulacak.
) else (
  echo NVIDIA bulunamadi: DirectML hizlandirma kurulacak.
)
if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r %REQ%
if errorlevel 1 ( echo [HATA] Paketler kurulamadi. & pause & exit /b 1 )
echo.
echo Yapay zeka modelleri indiriliyor (~1,6 GB, bir kez)...
powershell -NoProfile -ExecutionPolicy Bypass -File modelleri_indir.ps1
if errorlevel 1 ( echo [HATA] Modeller indirilemedi. Internet baglantisini kontrol edin. & pause & exit /b 1 )
echo.
echo Kurulum tamam. Programi "baslat.bat" ile acabilirsiniz.
echo Tek dosyalik kurulum paketi icin "kurulum_paketi_olustur.bat" calistirin.
pause
