@echo off
echo ========================================
echo  ClipSeq - Build para Executavel (.exe)
echo ========================================
echo.

echo [1/4] Criando pasta data se nao existir...
if not exist "data" mkdir data
if not exist "data\config.json" echo {} > data\config.json

echo.
echo [2/4] Instalando dependencias no usuario (sem admin)...
pip install --user pynput pyperclip pyinstaller
echo.

echo [3/4] Gerando ClipSeq.exe...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name ClipSeq ^
    --add-data "data;data" ^
    --hidden-import pynput.keyboard._win32 ^
    --hidden-import pynput.mouse._win32 ^
    --hidden-import pyperclip ^
    main.py

echo.
echo [4/4] Concluido!
if exist "dist\ClipSeq.exe" (
    echo [OK] Executavel gerado em: dist\ClipSeq.exe
) else (
    echo [ERRO] Nao foi possivel gerar o executavel.
)
echo.
