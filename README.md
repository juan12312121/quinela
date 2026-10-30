# Quiniela Progol

Página web que calcula la probabilidad de **local, empate y visita** de cada partido
usando los resultados reales de 23 ligas.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `generar_datos.py` | Baja los resultados de football-data.co.uk **y la jornada de Progol ya programada**, y arma `datos.json`. Sin llave ni cuenta. |
| `datos.json` | El dataset: ~11,700 partidos de las dos últimas temporadas + los próximos partidos con sus cuotas. |
| `index.html` | La página. Lee `datos.json` y hace todo el cálculo en el navegador. |

Cada partido del dataset se guarda como
`[fecha, iLocal, iVisita, golesL, golesV, iTemporada, cuotas]`,
donde los índices apuntan a las listas `equipos` y `temporadas` de su liga y las
cuotas pueden ser `null`.

## La jornada automática

El script lee el concurso vigente (los 14 partidos y las 7 revanchas, con momios) y
lo deja en `datos.json` bajo `jornada`. La página abre con esa jornada ya puesta,
sin capturar nada a mano.

- **De dónde sale**: `https://gainblers.com/mx/quinielas/progol/` y `.../progol-revancha/`.
  El sitio oficial (`pronosticos.gob.mx/Progol/Progol`) arma su tabla con JavaScript,
  así que un script no la puede leer. Conviene comparar el boleto contra el oficial
  antes de pagar.
- **Los nombres** de la quiniela ("Pumas", "Nápoles", "Friburgo") se empatan solos con
  los del dataset por parecido, apoyados en el diccionario `ALIAS` de
  `generar_datos.py`. Si algún equipo no empata, el script lo imprime en consola como
  `sin empatar:` — ahí se le agrega su alias.
- **Ligas que no están en el dataset** (por ejemplo la chilena): la fila se queda con
  los nombres de la quiniela y sus porcentajes salen solo de los momios, sin modelo.

## Las tres vistas

- **Boleto**: las 14 filas (más revanchas) con L/E/V, la marca y, al tocar una fila,
  el estudio del partido: goles esperados, índices de ataque y defensa, posición en
  la tabla, rendimiento de local y de visitante, marcadores probables, modelo contra
  mercado, últimos partidos con rachas e historial entre los dos equipos.
- **Análisis**: toda la jornada en una tabla comparativa y el reparto automático de
  dobles y triples según cuántas quinielas quieras pagar.
- **Ligas**: tabla de posiciones de cualquiera de las 23 ligas con los índices del modelo.

## Refrescar los datos antes de la jornada

```
python generar_datos.py
```

Tarda alrededor de un minuto. Después hay que volver a publicar la página para que
el artifact tome el `datos.json` nuevo.

## Ligas incluidas

Liga MX, MLS, Argentina, Brasil, Japón, Premier League, Championship, League One,
League Two, Escocia, LaLiga, LaLiga 2, Serie A, Serie B, Bundesliga, Bundesliga 2,
Ligue 1, Ligue 2, Eredivisie, Bélgica, Portugal, Turquía y Grecia.

Para agregar otra liga se edita `LIGAS_MAIN` o `LIGAS_EXTRA` en `generar_datos.py`
(los códigos están en https://www.football-data.co.uk/notes.txt).

## El modelo

1. Índice de **ataque** y **defensa** por equipo contra el promedio de su liga,
   con los partidos viejos pesando menos (vida media de 200 días).
2. Goles esperados: `promedio de la liga × ataque de uno × defensa del otro`.
3. Probabilidad de cada marcador con Poisson + corrección Dixon-Coles
   (`RHO = -0.05`) para que los empates no queden subestimados.
4. Si el partido trae cuotas, se les quita la comisión y se mezclan con el modelo
   (55% modelo / 45% mercado). El interruptor de la página apaga la mezcla.

Las constantes están hasta arriba del `<script>` en `index.html`:
`VIDA_MEDIA`, `RHO`, `PESO_MERCADO`, `ENCOGE`.

## Publicar en Vercel

`python preparar_vercel.py` arma `web/` (index.html con su
`<!doctype>` + datos.json + vercel.json). En Vercel: importar el repo, poner
**Root Directory = `web`**, framework *Other*, sin build command.
Cada semana: `generar_datos.py`, `preparar_vercel.py`, commit y push.
