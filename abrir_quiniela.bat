@echo off
REM Abre la pagina de la quiniela en el navegador, servida desde esta carpeta.
REM Se queda una ventana negra minimizada: esa es el servidor.
REM Para cerrar la pagina, cierra esa ventana.

cd /d "%~dp0"

if not exist "datos.json" (
    echo No se encontro datos.json en esta carpeta.
    echo Corre primero:  python generar_datos.py
    pause
    exit /b 1
)

start "Servidor quiniela" /min python -m http.server 8777
timeout /t 2 /nobreak >nul
start "" http://localhost:8777/index.html
exit /b 0
