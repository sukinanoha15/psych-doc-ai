@echo off
cd /d %~dp0

tasklist /fi "imagename eq ollama.exe" | find "ollama.exe" > nul
if errorlevel 1 (
    start /min "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 8 /nobreak > nul
)

start pythonw -m streamlit run app.py