@echo off
REM Sirve la quiniela a toda la red local: tus compas entran desde su PC o su
REM celular con la direccion que aparece en pantalla.
REM La primera vez Windows pregunta si permites el acceso: di que SI en "redes privadas".

cd /d "%~dp0"
python compartir.py
pause
