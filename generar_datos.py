# -*- coding: utf-8 -*-
"""
Genera el dataset de la pagina de quinielas.

Baja los resultados publicos de football-data.co.uk (sin llave, sin cuenta),
los limpia y los deja en quiniela/datos.json con esta forma:

{
  "generado": "2026-10-29T12:00:00",
  "ligas": [{"id","nombre","pais","equipos":[...],"partidos":[[fecha,iLocal,iVisita,gl,gv],...]}],
  "proximos": [{"liga","fecha","hora","local","visita","cuotas":[L,E,V]}]
}

Para refrescar antes de llenar la quiniela:
    python generar_datos.py
"""

import csv
import difflib
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime

BASE = "https://www.football-data.co.uk"

# De aqui sale la jornada de Progol ya programada (los 14 + 7 de revancha).
# El sitio oficial (pronosticos.gob.mx) arma su tabla con JavaScript, asi que
# no se puede leer desde un script; esta pagina la publica en HTML plano y
# ademas trae los momios de cada partido.
JORNADA_PROGOL = "https://gainblers.com/mx/quinielas/progol/"
JORNADA_REVANCHA = "https://gainblers.com/mx/quinielas/progol-revancha/"

# Ligas "principales": un archivo CSV por temporada.
# id -> (nombre, pais)
LIGAS_MAIN = {
    "E0": ("Premier League", "Inglaterra"),
    "E1": ("Championship", "Inglaterra"),
    "E2": ("League One", "Inglaterra"),
    "E3": ("League Two", "Inglaterra"),
    "SC0": ("Premiership", "Escocia"),
    "SP1": ("LaLiga", "Espana"),
    "SP2": ("LaLiga 2", "Espana"),
    "I1": ("Serie A", "Italia"),
    "I2": ("Serie B", "Italia"),
    "D1": ("Bundesliga", "Alemania"),
    "D2": ("Bundesliga 2", "Alemania"),
    "F1": ("Ligue 1", "Francia"),
    "F2": ("Ligue 2", "Francia"),
    "N1": ("Eredivisie", "Holanda"),
    "B1": ("Pro League", "Belgica"),
    "P1": ("Primeira Liga", "Portugal"),
    "T1": ("Super Lig", "Turquia"),
    "G1": ("Super League", "Grecia"),
}

# Temporadas a usar: la actual pesa completo, la anterior sirve de respaldo.
TEMPORADAS = ["2627", "2526"]

# Ligas "extra": un solo CSV con todas las temporadas.
# archivo -> (id, nombre, pais, temporadas validas)
LIGAS_EXTRA = {
    "MEX": ("MEX", "Liga MX", "Mexico", ["2026/2027", "2025/2026"]),
    "USA": ("USA", "MLS", "Estados Unidos", ["2026", "2025"]),
    "ARG": ("ARG", "Liga Profesional", "Argentina", ["2026", "2025"]),
    "BRA": ("BRA", "Serie A", "Brasil", ["2026", "2025"]),
    "JPN": ("JPN", "J1 League", "Japon", ["2026", "2025"]),
}


def bajar(ruta):
    """Descarga un CSV y lo devuelve como lista de diccionarios."""
    url = BASE + ruta
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido, timeout=60) as resp:
            crudo = resp.read()
    except Exception as exc:  # pragma: no cover - red
        print("  ! no se pudo bajar %s (%s)" % (ruta, exc))
        return []
    texto = crudo.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(texto)))


def fecha_iso(valor):
    """dd/mm/yyyy o dd/mm/yy -> yyyy-mm-dd."""
    valor = (valor or "").strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def numero(valor):
    try:
        return float(str(valor).strip())
    except (TypeError, ValueError):
        return None


def entero(valor):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def cuotas(fila, claves):
    """Primer trio de cuotas disponible (local, empate, visita)."""
    for cl, ce, cv in claves:
        l, e, v = numero(fila.get(cl)), numero(fila.get(ce)), numero(fila.get(cv))
        if l and e and v:
            return [l, e, v]
    return None


CUOTAS_RESULTADO = [
    ("AvgCH", "AvgCD", "AvgCA"),
    ("AvgH", "AvgD", "AvgA"),
    ("B365CH", "B365CD", "B365CA"),
    ("B365H", "B365D", "B365A"),
    ("PSCH", "PSCD", "PSCA"),
    ("MaxCH", "MaxCD", "MaxCA"),
]


class Liga(object):
    """Una liga con sus equipos y partidos.

    Cada partido se guarda como [fecha, iLocal, iVisita, golesL, golesV,
    iTemporada, cuotas] y las cuotas pueden venir como null.
    """

    def __init__(self, id_, nombre, pais):
        self.id = id_
        self.nombre = nombre
        self.pais = pais
        self.equipos = []
        self.indices = {}
        self.temporadas = []
        self.partidos = []

    def indice(self, equipo):
        if equipo not in self.indices:
            self.indices[equipo] = len(self.equipos)
            self.equipos.append(equipo)
        return self.indices[equipo]

    def i_temporada(self, temporada):
        if temporada not in self.temporadas:
            self.temporadas.append(temporada)
        return self.temporadas.index(temporada)

    def agregar(self, fecha, local, visita, gl, gv, odds, temporada):
        self.partidos.append([
            fecha, self.indice(local), self.indice(visita), gl, gv,
            self.i_temporada(temporada),
            [round(o, 2) for o in odds] if odds else None,
        ])

    def a_dict(self):
        # Las temporadas quedan ordenadas de la mas vieja a la mas nueva y los
        # indices de cada partido se reacomodan para que coincidan.
        orden = sorted(range(len(self.temporadas)), key=lambda k: self.temporadas[k])
        nuevo = {viejo: i for i, viejo in enumerate(orden)}
        for p in self.partidos:
            p[5] = nuevo[p[5]]
        self.temporadas = [self.temporadas[k] for k in orden]
        self.partidos.sort(key=lambda p: p[0])
        return {
            "id": self.id,
            "nombre": self.nombre,
            "pais": self.pais,
            "equipos": self.equipos,
            "temporadas": self.temporadas,
            "partidos": self.partidos,
        }


# Nombres como los escribe la quiniela -> nombre exacto del dataset.
# Solo van los que el parecido automatico no acierta (apodos y nombres en
# espanol de equipos europeos).
ALIAS = {
    # Liga MX
    "pumas": "UNAM Pumas", "unam": "UNAM Pumas", "america": "Club America",
    "aguilas": "Club America", "guadalajara": "Guadalajara Chivas",
    "chivas": "Guadalajara Chivas", "tijuana": "Club Tijuana",
    "xolos": "Club Tijuana", "leon": "Club Leon", "tigres": "Tigres UANL",
    "santos": "Santos Laguna", "rayados": "Monterrey", "mazatlan": "Mazatlan FC",
    "san luis": "Atl. San Luis", "atletico san luis": "Atl. San Luis",
    # Espana
    "athletic": "Ath Bilbao", "athletic bilbao": "Ath Bilbao",
    "atletico madrid": "Ath Madrid", "atletico de madrid": "Ath Madrid",
    "real sociedad": "Sociedad", "rayo vallecano": "Vallecano",
    "la coruna": "La Coruna", "real betis": "Betis",
    # Inglaterra
    "manchester united": "Man United", "manchester city": "Man City",
    "nottingham forest": "Nott'm Forest", "wolverhampton": "Wolves",
    "tottenham hotspur": "Tottenham", "newcastle united": "Newcastle",
    "west ham united": "West Ham", "leeds united": "Leeds",
    # Italia
    "napoles": "Napoli", "internazionale": "Inter", "ac milan": "Milan",
    "bolonia": "Bologna", "genova": "Genoa", "juve": "Juventus",
    # Alemania
    "friburgo": "Freiburg", "augsburgo": "Augsburg", "colonia": "FC Koln",
    "colonia fc": "FC Koln", "borussia dortmund": "Dortmund",
    "bayer leverkusen": "Leverkusen", "leipzig": "RB Leipzig",
    "monchengladbach": "M'gladbach", "borussia monchengladbach": "M'gladbach",
    "maguncia": "Mainz", "wolfsburgo": "Wolfsburg", "hamburgo": "Hamburg",
    "bremen": "Werder Bremen", "union berlin": "Union Berlin",
    # Francia
    "psg": "Paris SG", "paris saint germain": "Paris SG",
    "paris saint-germain": "Paris SG", "marsella": "Marseille",
    "niza": "Nice", "estrasburgo": "Strasbourg", "monaco": "Monaco",
    # Holanda y Portugal
    "az": "AZ Alkmaar", "alkmaar": "AZ Alkmaar", "psv": "PSV Eindhoven",
    "sporting": "Sp Lisbon", "sporting lisboa": "Sp Lisbon", "braga": "Sp Braga",
    # Brasil
    "atletico mineiro": "Atletico-MG", "mineiro": "Atletico-MG",
    "athletico paranaense": "Athletico-PR", "paranaense": "Athletico-PR",
    "flamengo": "Flamengo RJ", "botafogo": "Botafogo RJ",
    "red bull bragantino": "Bragantino", "sport recife": "Sport Recife",
    # Argentina
    "velez": "Velez Sarsfield", "newells": "Newells Old Boys",
    "argentinos": "Argentinos Jrs", "riestra": "Deportivo Riestra",
    "central cordoba": "Central Cordoba", "racing": "Racing Club",
}

RUIDO = ("club", "fc", "cf", "cd", "ac", "sc", "deportivo", "de", "del", "the")


def normalizar(nombre):
    """Quita acentos, puntuacion y palabras de relleno."""
    txt = unicodedata.normalize("NFKD", nombre or "")
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.lower().replace("&", " ").replace(".", " ").replace("-", " ")
    txt = re.sub(r"[^a-z0-9' ]", " ", txt)
    piezas = [p for p in txt.split() if p not in RUIDO]
    return " ".join(piezas) if piezas else txt.strip()


def mejor_equipo(liga, nombre):
    """Devuelve (equipo del dataset, parecido 0-1) o (None, 0)."""
    objetivo = ALIAS.get(normalizar(nombre))
    if objetivo and objetivo in liga.equipos:
        return objetivo, 1.0
    norm = {normalizar(e): e for e in liga.equipos}
    clave = normalizar(nombre)
    if clave in norm:
        return norm[clave], 1.0
    cerca = difflib.get_close_matches(clave, list(norm.keys()), n=1, cutoff=0.6)
    if not cerca:
        return None, 0.0
    return norm[cerca[0]], difflib.SequenceMatcher(None, clave, cerca[0]).ratio()


def empatar(ligas, local, visita):
    """Busca en que liga del dataset viven los dos equipos del partido."""
    mejor = None
    for liga in ligas.values():
        a, sa = mejor_equipo(liga, local)
        b, sb = mejor_equipo(liga, visita)
        if not a or not b or a == b:
            continue
        punto = min(sa, sb)
        if mejor is None or punto > mejor[0]:
            mejor = (punto, liga.id, a, b)
    if mejor and mejor[0] >= 0.78:
        return mejor[1], mejor[2], mejor[3]
    return None, None, None


def limpiar_html(txt):
    txt = re.sub(r"&nbsp;?", " ", txt or "")
    txt = re.sub(r"<[^>]+>", "", txt)
    try:
        import html as _html
        txt = _html.unescape(txt)
    except Exception:
        pass
    return re.sub(r"\s+", " ", txt).strip()


def leer_quiniela(url, cuantos):
    """Saca de la pagina el numero de concurso, la fecha y sus partidos."""
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido, timeout=45) as resp:
            pagina = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        print("  ! no se pudo leer %s (%s)" % (url, exc))
        return None, None, []

    concurso = re.search(r'lblJornada"[^>]*>\s*Concurso\s*(\d+)', pagina)
    fecha = re.search(r'lblFecha"[^>]*>\s*([\d/]+)', pagina)

    partidos = []
    for bloque in re.findall(r'<li class="tr quiniela-tr">(.*?)</li>', pagina, re.S):
        evento = re.search(
            r'<p class="event">\s*<span>(.*?)</span>\s*<span class="vs">\s*vs\s*</span>\s*<span>(.*?)</span>',
            bloque, re.S)
        if not evento:
            continue
        momios = []
        for m in re.findall(r'class="cuotita[^"]*"[^>]*>\s*([\d.,]+)\s*</span>', bloque):
            try:
                momios.append(float(m.replace(",", ".")))
            except ValueError:
                pass
        partidos.append({
            "local": limpiar_html(evento.group(1)),
            "visita": limpiar_html(evento.group(2)),
            "cuotas": momios[:3] if len(momios) >= 3 else None,
        })
        if len(partidos) >= cuantos:
            break

    return (concurso.group(1) if concurso else None,
            fecha.group(1) if fecha else None,
            partidos)


def bajar_jornada(ligas):
    """Arma la jornada de Progol ya empatada con los equipos del dataset."""
    numero, fecha, principales = leer_quiniela(JORNADA_PROGOL, 14)
    _, _, revanchas = leer_quiniela(JORNADA_REVANCHA, 7)
    if not principales:
        return None

    salida, sin_datos = [], 0
    for i, p in enumerate(principales + revanchas):
        liga, local, visita = empatar(ligas, p["local"], p["visita"])
        if not liga:
            sin_datos += 1
        salida.append({
            "n": i + 1,
            "revancha": i >= len(principales),
            "txtLocal": p["local"],
            "txtVisita": p["visita"],
            "liga": liga,
            "local": local,
            "visita": visita,
            "cuotas": p["cuotas"],
        })

    print("  concurso %s (%s): %d partidos, %d sin datos en el dataset"
          % (numero, fecha, len(salida), sin_datos))
    for p in salida:
        if not p["liga"]:
            print("    sin empatar: %s vs %s" % (p["txtLocal"], p["txtVisita"]))

    return {
        "numero": numero,
        "fecha": fecha,
        "fuente": "gainblers.com",
        "partidos": salida,
    }


def main():
    ligas = {}
    total = 0

    print("Bajando ligas principales...")
    for codigo, (nombre, pais) in LIGAS_MAIN.items():
        liga = Liga(codigo, nombre, pais)
        for temporada in TEMPORADAS:
            etiqueta = "20%s/20%s" % (temporada[:2], temporada[2:])
            filas = bajar("/mmz4281/%s/%s.csv" % (temporada, codigo))
            usados = 0
            for fila in filas:
                fecha = fecha_iso(fila.get("Date"))
                local = (fila.get("HomeTeam") or "").strip()
                visita = (fila.get("AwayTeam") or "").strip()
                gl, gv = entero(fila.get("FTHG")), entero(fila.get("FTAG"))
                if not (fecha and local and visita) or gl is None or gv is None:
                    continue
                liga.agregar(fecha, local, visita, gl, gv,
                             cuotas(fila, CUOTAS_RESULTADO), etiqueta)
                usados += 1
            print("  %s %s: %d partidos" % (codigo, temporada, usados))
            total += usados
        if liga.partidos:
            ligas[codigo] = liga

    print("Bajando ligas extra...")
    for archivo, (codigo, nombre, pais, temps) in LIGAS_EXTRA.items():
        liga = Liga(codigo, nombre, pais)
        filas = bajar("/new/%s.csv" % archivo)
        usados = 0
        for fila in filas:
            etiqueta = (fila.get("Season") or "").strip()
            if etiqueta not in temps:
                continue
            fecha = fecha_iso(fila.get("Date"))
            local = (fila.get("Home") or "").strip()
            visita = (fila.get("Away") or "").strip()
            gl, gv = entero(fila.get("HG")), entero(fila.get("AG"))
            if not (fecha and local and visita) or gl is None or gv is None:
                continue
            liga.agregar(fecha, local, visita, gl, gv,
                         cuotas(fila, CUOTAS_RESULTADO), etiqueta)
            usados += 1
        print("  %s: %d partidos" % (codigo, usados))
        total += usados
        if liga.partidos:
            ligas[codigo] = liga

    print("Bajando proximos partidos...")
    proximos = []

    for fila in bajar("/fixtures.csv"):
        codigo = (fila.get("Div") or "").strip()
        if codigo not in LIGAS_MAIN:
            continue
        fecha = fecha_iso(fila.get("Date"))
        local = (fila.get("HomeTeam") or "").strip()
        visita = (fila.get("AwayTeam") or "").strip()
        if not (fecha and local and visita):
            continue
        proximos.append({
            "liga": codigo,
            "fecha": fecha,
            "hora": (fila.get("Time") or "").strip(),
            "local": local,
            "visita": visita,
            "cuotas": cuotas(fila, CUOTAS_RESULTADO),
        })

    nombre_a_codigo = {}
    for archivo, (codigo, nombre, pais, temps) in LIGAS_EXTRA.items():
        nombre_a_codigo[(pais, nombre)] = codigo

    for fila in bajar("/new_league_fixtures.csv"):
        clave = ((fila.get("Country") or "").strip(), (fila.get("League") or "").strip())
        codigo = None
        for (pais, nombre), cod in nombre_a_codigo.items():
            if clave[1] == nombre and clave[0].lower().startswith(pais.lower()[:3]):
                codigo = cod
                break
        if codigo is None:
            codigo = {"Liga MX": "MEX", "MLS": "USA", "Liga Profesional": "ARG",
                      "J1 League": "JPN"}.get(clave[1])
        if codigo is None or codigo not in ligas:
            continue
        fecha = fecha_iso(fila.get("Date"))
        local = (fila.get("Home") or "").strip()
        visita = (fila.get("Away") or "").strip()
        if not (fecha and local and visita):
            continue
        proximos.append({
            "liga": codigo,
            "fecha": fecha,
            "hora": (fila.get("Time") or "").strip(),
            "local": local,
            "visita": visita,
            "cuotas": cuotas(fila, CUOTAS_RESULTADO),
        })

    # El archivo de proximos arrastra partidos de dias anteriores: los quitamos.
    hoy = datetime.now().strftime("%Y-%m-%d")
    jugados = set()
    for liga in ligas.values():
        for p in liga.partidos:
            jugados.add((liga.id, p[0], liga.equipos[p[1]], liga.equipos[p[2]]))
    proximos = [p for p in proximos
                if p["fecha"] >= hoy
                and (p["liga"], p["fecha"], p["local"], p["visita"]) not in jugados]

    proximos.sort(key=lambda p: (p["fecha"], p["hora"]))
    print("  %d partidos por jugarse" % len(proximos))

    print("Bajando la jornada de Progol...")
    jornada = bajar_jornada(ligas)

    datos = {
        "generado": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "fuente": "football-data.co.uk",
        "temporadas": TEMPORADAS,
        "total_partidos": total,
        "jornada": jornada,
        "ligas": [ligas[c].a_dict() for c in ligas],
        "proximos": proximos,
    }

    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))

    peso = os.path.getsize(destino) / 1024.0
    print("")
    print("Listo: %s" % destino)
    print("  %d ligas, %d partidos historicos, %d proximos, %.0f KB"
          % (len(datos["ligas"]), total, len(proximos), peso))
    return 0


if __name__ == "__main__":
    sys.exit(main())
