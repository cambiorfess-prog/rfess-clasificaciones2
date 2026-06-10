@echo off
cd /d "%~dp0"
echo Instalando/actualizando requisitos de RFESS App...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Error instalando requisitos. Comprueba que Python esta instalado.
  pause
  exit /b 1
)
echo.
echo Abriendo RFESS App en el navegador...
python -m streamlit run app.py
pause
