@echo off
rem Centro di controllo grafico della traduzione italiana di Aniimo.
rem Usa pythonw (nessuna finestra console); fallback su python se manca.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tools\aniimo_it_gui.py"
) else (
    start "" python "%~dp0tools\aniimo_it_gui.py"
)
