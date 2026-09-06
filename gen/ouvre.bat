@echo off
rem Attend que le serveur ecoute, puis ouvre le navigateur avec la commande
rem native "start" de Windows -- la seule qui ouvre reellement le navigateur
rem par defaut. os.startfile et webbrowser echouent silencieusement ici.
setlocal
set N=0
:attente
set /a N+=1
if %N% gtr 60 goto fin
%PY_EXE% -c "import socket,sys; s=socket.socket(); s.settimeout(0.3); sys.exit(0 if s.connect_ex(('127.0.0.1',8420))==0 else 1)" >nul 2>&1
if errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto attente
)
start "" "http://127.0.0.1:8420"
:fin
endlocal
