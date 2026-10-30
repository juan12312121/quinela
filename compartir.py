# -*- coding: utf-8 -*-
"""
Sirve la pagina de la quiniela a toda la red local.

A diferencia de abrir_quiniela.bat (que solo la deja ver en esta PC), este
escucha en todas las interfaces, asi que cualquiera en la misma red entra con
http://<ip-de-esta-pc>:8777/

    python quiniela/compartir.py

Deja la ventana abierta: es el servidor. Al cerrarla se cae la pagina.
"""

import http.server
import os
import socket
import socketserver
import sys
import webbrowser

PUERTO = 8777


def ip_local():
    """IP de esta PC en la red. No manda nada, solo ve que ruta usaria."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, formato, *args):
        # Una linea por visita, para ver quien se conecta.
        if args and str(args[0]).startswith("GET / "):
            print("  -> entro %s" % self.client_address[0])

    def end_headers(self):
        # Que no se quede con el datos.json viejo en cache.
        self.send_header("Cache-Control", "no-store")
        http.server.SimpleHTTPRequestHandler.end_headers(self)


def main():
    carpeta = os.path.dirname(os.path.abspath(__file__))
    os.chdir(carpeta)

    if not os.path.exists("datos.json"):
        print("No se encontro datos.json en %s" % carpeta)
        print("Corre primero:  python generar_datos.py")
        return 1

    ip = ip_local()
    direccion = "http://%s:%d/" % (ip or "localhost", PUERTO)

    socketserver.TCPServer.allow_reuse_address = True
    try:
        servidor = socketserver.TCPServer(("0.0.0.0", PUERTO), Handler)
    except OSError as exc:
        print("No se pudo abrir el puerto %d: %s" % (PUERTO, exc))
        print("Seguramente ya hay otro servidor corriendo en ese puerto.")
        return 1

    print("")
    print("  ===============================================")
    print("   QUINIELA PROGOL  -  compartida en la red")
    print("  ===============================================")
    print("")
    print("   Pasales esta direccion a tus compas:")
    print("")
    print("        %s" % direccion)
    print("")
    print("   Tienen que estar en la misma red (el mismo")
    print("   wifi o el mismo cable) que esta PC.")
    print("")
    print("   Esta ventana es el servidor: si la cierras,")
    print("   la pagina deja de funcionar para todos.")
    print("   Para apagarlo: Ctrl+C")
    print("  ===============================================")
    print("")

    try:
        webbrowser.open("http://localhost:%d/" % PUERTO)
    except Exception:
        pass

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor apagado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
