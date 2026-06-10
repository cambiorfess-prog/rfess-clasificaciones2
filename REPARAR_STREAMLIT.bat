@echo off
cd /d "%~dp0"
echo Reparando Streamlit...
python -m pip uninstall streamlit -y
python -m pip install --force-reinstall streamlit==1.41.1
python -m streamlit run app.py
pause
