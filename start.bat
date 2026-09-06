@echo off
chcp 65001 >nul
title Generateur de carrousels
cd /d "%~dp0"

echo.
echo   Generateur de carrousels
echo   ------------------------
echo.

rem --- trouver Python ---
set PY=
where python >nul 2>&1 && set PY=python
if not defined PY where py >nul 2>&1 && set PY=py -3
if not defined PY (
  echo   [ERREUR] Python est introuvable.
  echo   Installe-le depuis https://www.python.org/downloads/
  echo   en cochant "Add Python to PATH", puis relance ce fichier.
  echo.
  pause
  exit /b 1
)

rem --- verifier Pillow, l'installer si besoin ---
%PY% -c "import PIL" >nul 2>&1
if errorlevel 1 (
  echo   Installation de Pillow ^(une seule fois^)...
  %PY% -m pip install --quiet pillow
  if errorlevel 1 (
    echo   [ERREUR] Installation de Pillow impossible.
    pause
    exit /b 1
  )
)

rem --- l'ouvreur attend le serveur dans sa propre fenetre, puis ouvre le navigateur ---
set PY_EXE=%PY%
start "" /min cmd /c ""%~dp0gen\ouvre.bat""

echo   Adresse : http://127.0.0.1:8420
echo   Le navigateur s'ouvre des que le serveur repond.
echo.
%PY% gen\serveur.py

echo.
echo   Serveur arrete.
pause
