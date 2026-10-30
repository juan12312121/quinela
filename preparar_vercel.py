# -*- coding: utf-8 -*-
"""
Arma quiniela/web/, la carpeta que se publica en Vercel.

index.html esta escrito para el formato de artifact, que le pone por su cuenta
el <!doctype html> y la cabecera. Servido tal cual desde Vercel el navegador lo
abriria en modo quirks, asi que aqui se le pone ese envoltorio y se copia
datos.json al lado.

    python quiniela/preparar_vercel.py

Flujo de cada semana:
    python quiniela/generar_datos.py      (baja datos y la jornada nueva)
    python quiniela/preparar_vercel.py    (arma web/)
    git add quiniela/web && git commit && git push   (Vercel se redespliega solo)
"""

import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(AQUI, "index.html")
DATOS = os.path.join(AQUI, "datos.json")
DIST = os.path.join(AQUI, "web")

# Lo que el visor de artifacts agrega solo y que fuera de el hay que poner a mano.
RESET = (
    ":root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}"
    "body{margin:0;font:14px system-ui,sans-serif}"
    "img{max-width:100%}"
    "[hidden]{display:none!important}"
)


def main():
    for ruta in (ORIGEN, DATOS):
        if not os.path.exists(ruta):
            print("Falta %s" % ruta)
            print("Corre primero:  python quiniela/generar_datos.py")
            return 1

    with open(ORIGEN, "r", encoding="utf-8") as f:
        fuente = f.read()

    # La cabecera es todo hasta el ultimo </style>; el resto es el cuerpo.
    corte = fuente.rfind("</style>")
    if corte < 0:
        print("index.html no tiene </style>; no se pudo separar cabecera y cuerpo.")
        return 1
    corte += len("</style>")
    cabecera, cuerpo = fuente[:corte], fuente[corte:]

    html = (
        "<!doctype html>\n"
        '<html lang="es">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<style>" + RESET + "</style>\n"
        + cabecera + "\n</head>\n<body>\n" + cuerpo + "\n</body>\n</html>\n"
    )

    os.makedirs(DIST, exist_ok=True)
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    shutil.copyfile(DATOS, os.path.join(DIST, "datos.json"))

    print("Listo: %s" % DIST)
    for nombre in sorted(os.listdir(DIST)):
        kb = os.path.getsize(os.path.join(DIST, nombre)) / 1024.0
        print("  %-14s %7.0f KB" % (nombre, kb))
    return 0


if __name__ == "__main__":
    sys.exit(main())
