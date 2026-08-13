#!/usr/bin/env python3
"""
archivador_diario.py — Fase 0 del proyecto BESS.

Guarda cada día una FOTO de lo que estaba publicado y disponible en el momento
de ejecutarse. No modela nada, no predice nada: solo deja constancia.

POR QUÉ EXISTE
--------------
Es la única pieza del proyecto cuyo coste crece cada día que se retrasa,
porque el tiempo va en una sola dirección. Hoy el modelo de precio se entrena
con:

  · Temperatura REAL histórica en lugar de la predicción que había ese día,
    porque AEMET no archiva predicciones pasadas. Sesgo optimista conocido.
  · Previsiones descargadas HOY para fechas pasadas, con el riesgo de revisión
    retroactiva ya detectado en los indicadores 460, 2563 y 10249 de e·sios.

Ninguna de las dos cosas se puede arreglar mirando atrás. Sí se pueden
arreglar hacia delante.

QUÉ CAMBIA EN LA v3.9
---------------------
Seguimiento de la CADENA DE PROGRAMACIÓN (PBF → PVP → P48 → PHF), a petición
del análisis de vertidos fotovoltaicos.

El problema: esos indicadores viven en el grupo «programa», con tope 0 en modo
ligero, y solo la primera captura del día va en completo. La cadena se
fotografiaba **una vez al día**, hacia las 00:50. Del P48 teníamos su estado
recién nacido y nunca cómo se modifica durante el día de operación.

  1. **28 indicadores fijos** (fotovoltaica, eólica terrestre y solar térmica)
     entran en TODAS las capturas, al margen de los topes.
  2. **`archivo/seguimiento_programas.csv`**, acumulativo y en ruta fija: una
     fila por captura y por indicador, con `values_updated_at`, `fecha_max`,
     `n_periodos`, `suma_valores` y `hash_valores`.

Las dos últimas columnas son la clave: detectan una republicación **aunque
`values_updated_at` no cambie**, y distinguen el refresco sin cambio de datos
del cambio real. Con eso, «¿a qué hora se emite la primera versión del P48 de
un día?» se contesta buscando la primera fila del indicador 84 cuyo
`fecha_max` alcanza ese día.

Se registran también las filas VACÍAS, a propósito: «a esta hora todavía no
estaba publicado» es la mitad de la respuesta.

QUÉ CAMBIA EN LA v3.8
---------------------
AEMET pasa de ser la fuente más pobre del archivo a una de las más ricas.

  1. **Ocho municipios en vez de seis.** Entra **A Coruña**, que cubre el
     noroeste —la zona con más eólica y con un régimen atlántico distinto del
     resto, que no estaba representada—, y **Mataró** como referencia local.
  2. **Se guarda mucho más que la temperatura.** Hasta ahora se pedía la
     predicción entera y se tiraba todo menos tmax y tmin. Ahora se conservan
     viento (velocidad y dirección), racha máxima, estado del cielo, humedad,
     sensación térmica, probabilidad de precipitación e índice UV.
  3. **Producto HORARIO nuevo** (`municipio/horaria`): 48 horas hora a hora.
     Es el que de verdad sirve para D+1, porque su resolución es la del
     mercado; el diario da máximos y mínimos, que no se pueden repartir por
     horas sin inventar.

Sobre la RADIACIÓN SOLAR: **AEMET no publica previsión de radiación.** Su
producto de radiación es de observación, no de predicción. Lo más cercano en
la predicción es `uvMax` (índice UV diario, y además para cielo despejado, o
sea que ignora justo la nubosidad). El sustituto utilizable es el **estado del
cielo horario**, que es lo que modula la fotovoltaica, y ese sí se archiva
ahora.

QUÉ CAMBIA EN LA v3.7
---------------------
Dos retoques al servicio del visor de móvil:

  1. **El índice se rellena hacia atrás.** Las capturas anteriores a la v3.4
     existen en disco pero nunca dejaron línea en `indice.csv`. Sin esto, el
     visor no vería los primeros días de archivo — justo los que sirvieron para
     caracterizar la publicación de las series D+1.
  2. **El 602 se guarda en CSV plano**, como el 600. Se me había quedado
     comprimido pese a anunciarlo en plano.

QUÉ CAMBIA EN LA v3.6
---------------------
Todo esto sale de leer los datos ya archivados y encontrar lo que faltaba.

  1. **Las descripciones ya no se truncan.** Estaban cortadas a 300 caracteres
     y 606 de los 1.506 indicadores quedaban a media frase. La del 460 se
     cortaba justo en «Important...», que era donde REE ponía la advertencia.
  2. **El catálogo se muda a `archivo/catalogo.csv`**, en ruta fija, acumulativo
     y reescrito solo cuando cambia. Es material de referencia, no una serie
     temporal: guardarlo ocho veces al día era lo que obligaba a truncarlo.
  3. **Grupo de búsqueda nuevo, «capacidad».** No había ni una serie de potencia
     de eólica o fotovoltaica: la potencia *disponible* solo existe para
     generación convencional, pero la *instalada* renovable debería estar y no
     entraba por ninguno de los cinco términos anteriores.
  4. **El indicador 602 (energía casada en el diario) pasa a principal.** Es la
     pareja natural del precio 600 y estaba solo en el barrido completo.

QUÉ CAMBIA EN LA v3.5
---------------------
Una corrección, y no menor. Hasta la v3.4 AEMET se pedía cuando la hora era
múltiplo de 3 (`hora % 3 == 0`). Con capturas cada hora eso daba ocho al día,
correcto. Pero al pasar a capturas cada tres horas incluyendo la de las 11:50
—la última antes del cierre de ofertas, y por tanto la que no se puede
sacrificar—, todas las horas pasan a ser 2, 5, 8, 11, 14, 17, 20 y 23: ninguna
múltiplo de 3, y AEMET no se habría pedido NUNCA. Sin error y sin aviso, solo
`OMITIDA` en todos los manifiestos.

Y AEMET es la fuente cuya pérdida es definitiva: su API solo devuelve la
predicción vigente. Ahora el espaciado no se calcula con el reloj sino con el
disco —horas transcurridas desde la última captura buena—, así que es correcto
con cualquier horario y además reintenta a la siguiente cuando una falla.

QUÉ CAMBIA EN LA v3.4
---------------------
Dos ficheros nuevos en una RUTA FIJA, que no cambia nunca:

  · `archivo/ultimo.json` — copia del manifiesto de la última captura.
  · `archivo/indice.csv`  — una línea por captura, desde la primera.

El motivo es concreto. La carpeta de cada captura lleva el minuto REAL de
arranque del script, que no es predecible: el disparo externo pide a y 50,
pero la ejecución empieza cuando GitHub asigna máquina. Comprobar cómo había
ido el archivador exigía por tanto adivinar el nombre de la carpeta —0850,
1452, 2303...— o mirarla a mano. Con una ruta fija, deja de ser un problema.

El índice guarda además `disparo` (de dónde vino la ejecución: `schedule`,
`workflow_dispatch`, `push`), que es lo que permitirá medir con datos la
fiabilidad del cron de GitHub frente al disparador externo, en vez de contar
carpetas a mano como hasta ahora.

QUÉ CAMBIA EN LA v3
-------------------
Tres cambios, todos motivados por una aportación del usuario: las previsiones
de renovables cubren unos 10 días y se REGENERAN varias veces al día.

  1. Se piden 10 días hacia delante en vez de uno. La evolución de la
     previsión de un día concreto según se acerca es irrecuperable si no se
     captura, y es la serie más interesante que puede dar esta fuente.
  2. Una subcarpeta por CAPTURA (`.../AAAA-MM-DD/HHMM/`) en vez de por día:
     con varias ejecuciones diarias, la segunda machacaba a la primera.
  3. Compresión por defecto, salvo los ficheros pequeños que conviene poder
     mirar desde la web. Sin esto, 10 días × 8 capturas diarias multiplicaban
     por cinco el tamaño del repositorio.

QUÉ CAMBIÓ EN LA v2
-------------------
La v1 archivaba solo los cuatro indicadores que el modelo usa hoy. La v2
archiva **todas las previsiones que publica e·sios**, descubriéndolas del
catálogo en cada ejecución.

El motivo no es «por si acaso». Los indicadores 460, 2563 y 10249 están hoy
DESCARTADOS como variable de entrenamiento porque se revisan después de
publicarse: el valor que se descarga hoy para una fecha pasada no es
necesariamente el que existía entonces. Archivarlos a diario **resuelve
exactamente ese problema**: a partir de la primera ejecución tendremos su
valor tal como se publicó, que es el único que un modelo honesto puede usar.
Es decir, el archivador no los guarda por completismo — los rehabilita.

Y lo mismo vale para los indicadores cuyo significado todavía no conocemos:
guardarlos cuesta unos KB al día; no haberlos guardado cuesta el histórico
entero el día que resulten útiles.

QUÉ GUARDA
----------
Una carpeta por día bajo `archivo/AAAA/MM/AAAA-MM-DD/`:

  · Los indicadores del modelo actual, en CSV plano y legible.
  · TODAS las previsiones descubiertas, en un único CSV comprimido.
  · Un CSV de metadatos con el `values_updated_at` de cada indicador, que es
    lo que permitirá detectar revisiones posteriores.
  · La predicción de temperatura de AEMET, irrecuperable después.
  · Las vistas de ENTSO-E y el precio del gas.
  · Un `manifiesto.json` con hora de ejecución y estado de cada fuente.

Las ventanas son DELIBERADAMENTE CORTAS: se trata de registrar lo nuevo y
poder detectar revisiones, no de duplicar el histórico cada mañana.

NOTA SOBRE EL NOMBRE DEL FICHERO
--------------------------------
Rompe a propósito la convención del proyecto de incluir la versión en el
nombre (`_vN`): este fichero lo ejecuta un workflow que lo referencia por
nombre, así que tiene que ser estable. La versión va en esta cabecera y en el
manifiesto de cada ejecución.

REQUISITOS
----------
Python 3.9+, `requests`, `pandas`. Tokens en variables de entorno:
ESIOS_TOKEN, ENTSOE_TOKEN, AEMET_TOKEN.

Versión: v3.9 — 2026-08-13.
"""

import os
import csv
import sys
import glob
import json
import time
import gzip
import hashlib
import datetime as dt
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import requests
import pandas as pd

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

TZ_MADRID = ZoneInfo("Europe/Madrid")
CARPETA_RAIZ = "archivo"

# Ventanas de captura, en días.
DIAS_PRECIO_ATRAS = 8        # precios publicados: contexto + detectar revisiones
DIAS_PREVISION_ATRAS = 1     # las previsiones no necesitan histórico
# Hasta dónde se piden las previsiones hacia delante. Se piden 10 días aunque
# el modelo solo use D+1: la previsión de un día concreto se REGENERA varias
# veces a medida que ese día se acerca, y esa evolución —cómo cambia la
# previsión del día 20 vista desde el 10, el 15 y el 19— es irrecuperable si
# no se captura. Si un indicador no llega tan lejos, simplemente devuelve
# menos: se pide y se registra hasta dónde llegó, en vez de suponerlo.
DIAS_ADELANTE = 11

ESIOS_BASE = "https://api.esios.ree.es"
ENTSOE_API = "https://web-api.tp.entsoe.eu/api"
AEMET_BASE = "https://opendata.aemet.es/opendata"

EIC_ES = "10YES-REE------0"
EIC_FR = "10YFR-RTE------C"
UA = {"User-Agent": "Mozilla/5.0 (proyecto BESS, datos publicos)"}

# Los que usa el modelo hoy. Se guardan en CSV plano para poder mirarlos
# desde la web de GitHub sin descargar nada.
INDICADORES_PRINCIPALES = {
    600: "precio_spot",
    # La energía casada en el diario, que es la pareja natural del precio 600.
    # Estaba ya en el barrido completo (grupo «programa»), pero solo una vez al
    # día. Aquí entra en las ocho capturas y en CSV plano. OJO: se publica tras
    # la casación, así que a las 11:50 llega hasta el final de HOY, nunca a
    # D+1. Sirve como variable retardada y para la Fase 3, no para predecir.
    602: "energia_casada_diario",
    541: "prev_eolica",
    542: "prev_solar_fv",
    543: "prev_solar_termica",
}

# Términos de búsqueda, SEPARADOS EN GRUPOS con tope propio cada uno.
#
# Por qué en grupos: la v3 buscaba los cinco términos juntos, ordenaba por id y
# se quedaba con los 300 primeros. Resultado medido el 11-ago-2026: los 300
# archivados eran TODOS «Generación programada PBF/PVP/P48/PHF…» —ids del 1 al
# 350—, y ni una sola previsión de verdad. Las de eólica, solar y demanda
# tienen ids de cuatro y cinco cifras, así que entraban únicamente por la lista
# fija de abajo. El tope, combinado con el orden por id, estaba dejando fuera
# justo lo que buscábamos.
#
# Y son dos familias distintas, no un matiz:
#
#   · PREVISIÓN — lo que se espera que pase. Se publica ANTES del cierre de
#     ofertas, así que es utilizable para predecir el precio del día siguiente.
#   · PROGRAMA — lo que el mercado ya ha casado (PBF, P48, PHF de las sesiones
#     intradiarias). Se publica DESPUÉS de la casación del mercado diario, o
#     sea después de las 13:00. Usarlo para predecir el precio de D+1 sería
#     fuga de información pura. Se archiva igualmente porque es valioso para la
#     Fase 3 (backtest de estrategia de oferta) y para entender el mercado,
#     pero NO puede entrar como variable del modelo de precio.
#   · CAPACIDAD — potencia instalada y disponible. Grupo nuevo en la v3.6, a
#     raíz de una pregunta concreta: en el catálogo no aparecía ni una sola
#     serie de potencia disponible de eólica o fotovoltaica. La explicación es
#     que ese concepto solo existe para generación CONVENCIONAL —se calcula
#     como potencia instalada menos indisponibilidad declarada por los sujetos
#     del mercado, y nadie declara la indisponibilidad del viento—. Pero la
#     potencia INSTALADA renovable sí debería existir, y no entraba porque
#     ninguno de los cinco términos anteriores casaba con su nombre. Se busca
#     explícitamente: si existe, entrará sola en el próximo barrido completo.
GRUPOS_BUSQUEDA = {
    "prevision": ["previsión", "prevista", "previsto"],
    "capacidad": ["potencia instalada", "potencia disponible",
                  "capacidad instalada"],
    "programa": ["D+1", "H+3"],
}

# Red de seguridad: si el descubrimiento falla, se bajan al menos estos, que
# son los ya catalogados en Aprendizaje_API_REE §4.6.
# Cadena de programación bajo SEGUIMIENTO. Entran en TODAS las capturas, al
# margen de los topes, igual que PREVISIONES_CONOCIDAS.
#
# Por qué (petición del 13-ago-2026 desde el análisis de vertidos): estos
# indicadores viven en el grupo «programa», cuyo tope en modo ligero es 0. Como
# solo la primera captura del día va en completo, la cadena se fotografiaba UNA
# vez al día, hacia las 00:50. Del P48 solo teníamos su estado recién nacido y
# nunca veíamos cómo se modifica durante el día de operación — que es
# justamente lo que hay que ver, y lo que no se puede recuperar después.
#
# Los 28 ids están verificados uno a uno contra el catálogo real archivado el
# 13-ago-2026. Aviso para quien los revise: PHF2 y PHF4 NO existen para estas
# tecnologías (4 indicadores en el catálogo frente a 57 de cada uno de los
# demás PHF), así que su ausencia en esta lista es correcta.
PROGRAMAS_SEGUIDOS = [
    # Solar fotovoltaica — la prioritaria. 84 es el P48, el que urge.
    14, 49, 84, 119, 189, 259, 294, 329, 1413, 434,
    # Eólica terrestre
    12, 47, 82, 117, 187, 257, 292, 327, 1411,
    # Solar térmica
    15, 50, 85, 120, 190, 260, 295, 330, 1414,
]

PREVISIONES_CONOCIDAS = [
    460, 541, 542, 543, 603, 1775, 1776, 1777, 1778,
    2563, 10034, 10249, 10358, 10359,
]

# Tope POR GRUPO y POR MODO. Medido el 11-ago-2026: de los 1.506 indicadores
# que devuelve la búsqueda, solo **110 son previsiones**; los otros 1.396 son
# programas de generación. Así que las previsiones caben enteras en cualquier
# captura, y lo único que hay que racionar son los programas.
#
# De ahí los dos modos:
#   · LIGERO   — solo previsiones (110). Unos 2 minutos. Es lo que se regenera
#                cada hora, así que es lo único que tiene sentido capturar a
#                ritmo horario.
#   · COMPLETO — previsiones + todos los programas. Una vez al día basta: son
#                el resultado de una casación ya cerrada, no cambian cada hora.
#
# El modo ligero además acorta muchísimo la ejecución, y eso importa: GitHub
# descarta las ejecuciones programadas cuando hay carga —el 11-ago-2026 solo
# corrieron 2 de las ~8 previstas— y las tareas largas son las primeras en caer.
MAX_POR_GRUPO = {
    "ligero":   {"prevision": 400, "capacidad": 0,   "programa": 0},
    "completo": {"prevision": 400, "capacidad": 200, "programa": 1600},
}

# Ritmo de peticiones. El documento de conocimiento del proyecto fija ~1/s
# como norma prudente, y se mantiene para los indicadores principales. Para el
# barrido masivo se baja: 1.506 indicadores a 1/s son más de 25 minutos, y la
# primera ejecución completa (11-ago-2026) se quedó sin tiempo y NO GUARDÓ
# NADA. Los 429 se reintentan igual, así que el riesgo de acelerar es bajo y
# el de no hacerlo ya se materializó.
PAUSA_BARRIDO = 0.4

# Presupuesto de tiempo del barrido, en minutos. Al agotarse se para y se
# guarda lo capturado hasta ese momento, anotando cuántos quedaron fuera.
# Sin esto, un barrido que no termina se lleva por delante la captura entera:
# los ficheros se escriben al final, así que el trabajo de media hora se
# perdía sin dejar rastro. Mejor una foto incompleta y anotada que ninguna.
MINUTOS_MAX_BARRIDO = 22

# AEMET no se pide en todas las capturas. Su predicción se elabora unas pocas
# veces al día (medido: 08:55 y 10:35), así que pedirla cada hora devuelve lo
# mismo y además nos gana un HTTP 429 — ya pasó en dos de las tres primeras
# capturas horarias.
#
# CUIDADO CON CÓMO SE ESPACIA (corregido en la v3.5). Hasta la v3.4 la
# condición era `hora % 3 == 0`, es decir, AEMET solo se pedía a las 0, 3, 6,
# 9... Eso funcionaba con capturas cada hora, pero se rompe en silencio en
# cuanto el horario deja de pasar por esas horas: con capturas a y 50 cada tres
# horas empezando a las 02:50 —el horario que incluye la captura clave de las
# 11:50— TODAS las horas son 2, 5, 8, 11, 14... y AEMET no se habría pedido
# NUNCA. Ni un error, ni un aviso: solo `OMITIDA` en todos los manifiestos.
#
# Y AEMET es precisamente la fuente que no se puede recuperar: su API solo
# devuelve la predicción vigente. Perder un mes de predicciones es perderlo.
#
# Por eso ahora no se mira el reloj sino el disco: se pide si hace más de estas
# horas que no se consigue una. Así el espaciado es correcto con CUALQUIER
# horario, y además reintenta en la siguiente captura cuando una falla, en vez
# de esperar al siguiente múltiplo.
HORAS_MINIMAS_ENTRE_AEMET = 2.5

# Ocho municipios. Los seis primeros son las grandes áreas de consumo; los dos
# últimos se añadieron en la v3.8:
#   · A Coruña (15030) cubre el NOROESTE, que no estaba representado y es la
#     zona con más eólica y con un régimen atlántico distinto del resto.
#   · Mataró (08121) es un punto de referencia local del propio proyecto.
MUNICIPIOS_AEMET = {
    "28079": "madrid", "08019": "barcelona", "46250": "valencia",
    "41091": "sevilla", "48020": "bilbao", "50297": "zaragoza",
    "15030": "a_coruna", "08121": "mataro",
}

# Segundos entre peticiones a AEMET. Su API devuelve 429 esporádicos incluso sin
# exceso evidente, y en la v3.8 se pasa de 6 a 16 llamadas por captura (ocho
# municipios × dos productos), así que el ritmo importa más que antes.
PAUSA_AEMET = 3

ESIOS_TOKEN = os.environ.get("ESIOS_TOKEN", "").strip()
ENTSOE_TOKEN = os.environ.get("ENTSOE_TOKEN", "").strip()
AEMET_TOKEN = os.environ.get("AEMET_TOKEN", "").strip()

MANIFIESTO = {"fuentes": {}}


def registrar(nombre, estado, detalle, filas=None, extra=None):
    """
    Deja constancia de cómo fue cada fuente. Un fallo NO aborta el programa:
    una foto parcial vale mucho más que ninguna foto, y el manifiesto deja
    claro qué falta. Lo que no puede pasar es que falte algo en silencio.
    """
    MANIFIESTO["fuentes"][nombre] = {
        "estado": estado, "detalle": detalle, "filas": filas, **(extra or {})
    }
    marca = {"OK": "✓", "VACIO": "·", "FALLO": "✗", "OMITIDA": "–",
             "PARCIAL": "◐"}.get(estado, "?")
    print(f"  [{marca}] {nombre}: {detalle}" + (f" ({filas} filas)" if filas else ""))


def guardar(df, carpeta, nombre, comprimir=True):
    """
    Comprime por defecto. Con 10 días de previsión y varias capturas al día,
    el CSV plano multiplicaría por cinco el tamaño del repositorio sin aportar
    nada: pandas lee un .csv.gz exactamente igual que un .csv.

    Se dejan en plano solo los ficheros que interesa poder mirar de un vistazo
    desde la web de GitHub sin descargar nada — el precio, la predicción de
    AEMET y los dos índices del catálogo—, que además son los pequeños.
    """
    if df is None or df.empty:
        return None
    if comprimir:
        ruta = os.path.join(carpeta, f"{nombre}.csv.gz")
        df.to_csv(ruta, index=False, compression="gzip")
    else:
        ruta = os.path.join(carpeta, f"{nombre}.csv")
        df.to_csv(ruta, index=False)
    return ruta


def hash_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def titulo(t):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


def cabeceras_esios():
    return {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": ESIOS_TOKEN,
    }


def pedir_esios(ruta, params, intentos=3):
    """
    Petición a e·sios con reintentos. Los HTTP 404 de e·sios son TRANSITORIOS
    (Aprendizaje_API_REE §3.4 punto 8): tres ejecuciones seguidas de la misma
    descarga fallaron en un tramo distinto cada vez. Aquí se reintentan igual
    que los 5xx; un 404 NO significa "no existe".
    """
    error = None
    for intento in range(1, intentos + 1):
        try:
            r = requests.get(f"{ESIOS_BASE}{ruta}", params=params,
                             headers=cabeceras_esios(), timeout=90)
        except Exception as e:
            error = f"error de red: {e}"
            time.sleep(4 * intento)
            continue
        if r.status_code == 200:
            try:
                return r.json(), None
            except Exception as e:
                return None, f"respuesta no es JSON: {e}"
        error = f"HTTP {r.status_code}"
        if r.status_code in (404, 429, 502, 503, 504):
            time.sleep(4 * intento)
            continue
        break
    return None, error


# ============================================================================
# Descubrimiento del catálogo de previsiones
# ============================================================================

def ya_hay_captura_completa_hoy(hoy):
    """
    ¿Se ha hecho ya hoy la captura completa? Se mira el disco en vez de la hora
    del reloj porque el cron de GitHub es impredecible: si se decidiera por
    hora fija y esa ejecución se descartara, el día se quedaría sin barrido
    completo y nadie se enteraría. Así lo hace la primera que consiga correr.
    """
    base = os.path.join(CARPETA_RAIZ, f"{hoy:%Y}", f"{hoy:%m}", f"{hoy:%Y-%m-%d}")
    if not os.path.isdir(base):
        return False
    for sub in sorted(os.listdir(base)):
        ruta = os.path.join(base, sub, "manifiesto.json")
        if not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, encoding="utf-8") as f:
                if json.load(f).get("modo") == "completo":
                    return True
        except Exception:
            continue
    return False


def horas_desde_ultima_aemet(ahora_madrid):
    """
    Horas transcurridas desde la última captura de AEMET que salió OK, o None
    si no hay ninguna. Se mira el disco, no el reloj, por el motivo explicado
    en HORAS_MINIMAS_ENTRE_AEMET.

    Se recorren hoy y ayer: una captura de madrugada tiene su última AEMET
    buena en la carpeta del día anterior, y sin mirar ayer se pediría dos veces
    seguidas en el cambio de día.
    """
    ultima = None
    for dia in (ahora_madrid.date(), ahora_madrid.date() - dt.timedelta(days=1)):
        base = os.path.join(CARPETA_RAIZ, f"{dia:%Y}", f"{dia:%m}", f"{dia:%Y-%m-%d}")
        if not os.path.isdir(base):
            continue
        for sub in os.listdir(base):
            ruta = os.path.join(base, sub, "manifiesto.json")
            if not os.path.isfile(ruta):
                continue
            try:
                with open(ruta, encoding="utf-8") as f:
                    m = json.load(f)
                fuente = m.get("fuentes", {}).get("aemet_prediccion_diaria", {})
                if fuente.get("estado") != "OK":
                    continue
                cuando = dt.datetime.fromisoformat(m["ejecucion_madrid"])
                if ultima is None or cuando > ultima:
                    ultima = cuando
            except Exception:
                continue
    if ultima is None:
        return None
    return (ahora_madrid - ultima).total_seconds() / 3600


def descubrir_previsiones(modo):
    """
    Busca en el catálogo de e·sios los indicadores que parezcan una previsión.
    Se hace en cada ejecución a propósito: si REE publica un indicador nuevo,
    entra solo, sin que nadie tenga que enterarse.
    """
    titulo(f"e·sios — descubrimiento del catálogo, por grupos (modo {modo})")
    encontrados, por_grupo = {}, {}

    topes = MAX_POR_GRUPO[modo]
    for grupo, terminos in GRUPOS_BUSQUEDA.items():
        if topes.get(grupo, 0) <= 0:
            print(f"  [{grupo}] omitido en modo {modo}")
            por_grupo[grupo] = {"encontrados": None, "archivados": 0,
                                "omitido": True}
            continue
        del_grupo = {}
        for termino in terminos:
            datos, error = pedir_esios("/indicators", {"text": termino})
            if error:
                print(f"  ⚠ búsqueda '{termino}': {error}")
                continue
            lista = datos.get("indicators", []) if isinstance(datos, dict) else []
            nuevos = 0
            for ind in lista:
                idx = ind.get("id")
                # Un indicador ya visto en otro grupo no se reasigna: el primer
                # grupo que lo encuentra se lo queda, y 'prevision' va primero.
                if idx is None or idx in encontrados or idx in del_grupo:
                    continue
                del_grupo[idx] = {
                    "id": idx, "grupo": grupo,
                    "nombre": (ind.get("name") or "").strip(),
                    # SIN TRUNCAR (v3.6). Hasta la v3.5 esto era [:300], y de
                    # los 1.506 indicadores del barrido completo, 606 quedaban
                    # cortados a media frase. La descripción es la ÚNICA
                    # documentación de qué significa cada serie: la del 460 se
                    # cortaba literalmente en «Important...», justo donde REE
                    # ponía la advertencia. Ahora cabe entera porque el catálogo
                    # ya no se reescribe en cada captura (ver guardar_catalogo).
                    "descripcion": (ind.get("description") or "").strip(),
                    "termino": termino,
                }
                nuevos += 1
            print(f"  [{grupo}] '{termino}': {len(lista)} resultados, "
                  f"{nuevos} nuevos")
            time.sleep(1)

        tope = topes.get(grupo, 200)
        ids_grupo = sorted(del_grupo)
        por_grupo[grupo] = {"encontrados": len(ids_grupo),
                            "archivados": min(len(ids_grupo), tope)}
        if len(ids_grupo) > tope:
            print(f"  ⚠ [{grupo}] {len(ids_grupo)} encontrados, tope {tope}: "
                  f"se archivan los {tope} de id más bajo.")
            ids_grupo = ids_grupo[:tope]
        for idx in ids_grupo:
            encontrados[idx] = del_grupo[idx]

    # Los conocidos entran siempre, aunque la búsqueda no los haya devuelto y
    # aunque los topes se hayan agotado. Son los que el modelo usa de verdad.
    for idx in PREVISIONES_CONOCIDAS:
        encontrados.setdefault(idx, {"id": idx, "grupo": "fijo",
                                     "nombre": "(de la lista fija)",
                                     "descripcion": "", "termino": "fijo"})
    # Y la cadena de programación bajo seguimiento, por el mismo mecanismo. Sus
    # ids son bajos (12 a 434), así que al ordenar quedan de los primeros y se
    # capturan antes de que pueda actuar el corte por presupuesto de tiempo.
    for idx in PROGRAMAS_SEGUIDOS:
        encontrados.setdefault(idx, {"id": idx, "grupo": "programa_seguido",
                                     "nombre": "(cadena de programación)",
                                     "descripcion": "", "termino": "seguimiento"})

    ids = sorted(encontrados)
    detalle = " · ".join(
        f"{g}: omitido" if v.get("omitido")
        else f"{g}: {v['archivados']}/{v['encontrados']}"
        for g, v in por_grupo.items())
    registrar("esios_catalogo", "OK" if ids else "FALLO",
              f"[{modo}] {len(ids)} a archivar ({detalle})",
              extra={"modo": modo, "por_grupo": por_grupo,
                     "total_archivados": len(ids)})
    return [encontrados[i] for i in ids]


# ============================================================================
# e·sios
# ============================================================================

def _serie_esios(indicador, ini_iso, fin_iso, filtrar_espana=False):
    params = {"start_date": ini_iso, "end_date": fin_iso,
              "time_trunc": "fifteen_minutes",
              "time_agg": "average"}   # crítico: con 'sum' los precios salen x4
    if filtrar_espana:
        params["geo_ids[]"] = 3
    datos, error = pedir_esios(f"/indicators/{indicador}", params)
    if error:
        return None, None, error
    ind = datos.get("indicator", {})
    valores = ind.get("values", [])
    if not valores:
        return None, ind, "sin valores (aún no publicado)"
    df = pd.DataFrame(valores)
    columnas = [c for c in ("datetime", "datetime_utc", "value", "geo_id")
                if c in df.columns]
    return df[columnas].sort_values("datetime_utc"), ind, None


def capturar_esios_principales(carpeta, hoy):
    titulo("e·sios — indicadores del modelo (CSV legible)")
    if not ESIOS_TOKEN:
        registrar("esios", "FALLO", "falta ESIOS_TOKEN")
        return False

    ini = dt.datetime.combine(hoy - dt.timedelta(days=DIAS_PRECIO_ATRAS),
                              dt.time(0, 0), tzinfo=TZ_MADRID).isoformat()
    fin = (dt.datetime.combine(hoy + dt.timedelta(days=DIAS_ADELANTE),
                               dt.time(0, 0), tzinfo=TZ_MADRID)
           - dt.timedelta(seconds=1)).isoformat()

    for indicador, nombre in INDICADORES_PRINCIPALES.items():
        df, ind, error = _serie_esios(indicador, ini, fin,
                                      filtrar_espana=(indicador == 600))
        etiqueta = f"esios_{indicador}_{nombre}"
        if df is None:
            registrar(etiqueta, "VACIO" if ind else "FALLO", error)
        else:
            # Precio (600) y energía casada (602) en plano: son los dos que
            # más se consultan a ojo y los más pequeños.
            guardar(df, carpeta, etiqueta, comprimir=(indicador not in (600, 602)))
            registrar(etiqueta, "OK",
                      f"{df['datetime_utc'].min()[:10]} a {df['datetime_utc'].max()[:10]}",
                      filas=len(df),
                      extra={"values_updated_at": ind.get("values_updated_at"),
                             "hash": hash_texto(df.to_csv(index=False))})
        time.sleep(1)
    return True


def guardar_catalogo(catalogo):
    """
    Escribe el catálogo en RUTA FIJA y ACUMULATIVA: `archivo/catalogo.csv`.

    Hasta la v3.5 el catálogo se reescribía dentro de cada captura. Eso tenía
    dos consecuencias malas a la vez:

      · Obligaba a truncar las descripciones a 300 caracteres para que el
        repositorio no se disparara —558 KB por captura completa—, y con ello
        se perdía la única documentación que existe de qué es cada indicador.
      · Guardaba ocho copias diarias de algo que cambia una vez cada varios
        meses.

    El catálogo no es una serie temporal, es material de referencia, y hay que
    tratarlo como tal: un solo fichero, con las descripciones ENTERAS, que solo
    se reescribe el día que REE cambia algo. Git guarda un blob nuevo
    únicamente entonces.

    Es ACUMULATIVO por una razón concreta: la captura ligera solo descubre 110
    indicadores y la completa 1.506. Si cada una sobrescribiera el fichero, las
    siete ligeras del día borrarían el trabajo de la completa. Así que se
    fusiona por id, actualizando lo que cambie y sin borrar nunca nada — un
    indicador retirado del catálogo de e·sios se queda aquí, que es justo lo
    que interesa para poder leer el archivo antiguo dentro de dos años.
    """
    ruta = os.path.join(CARPETA_RAIZ, "catalogo.csv")
    hoy = dt.date.today().isoformat()
    nuevo = {}
    for e in catalogo:
        if e.get("grupo") == "fijo" and not e.get("descripcion"):
            # Entrada de relleno de la lista fija: no debe pisar la buena.
            nuevo[e["id"]] = {**e, "visto": hoy, "_relleno": True}
        else:
            nuevo[e["id"]] = {**e, "visto": hoy, "_relleno": False}

    previo = {}
    if os.path.isfile(ruta):
        try:
            with open(ruta, newline="", encoding="utf-8") as f:
                for fila in csv.DictReader(f):
                    try:
                        previo[int(fila["id"])] = fila
                    except (KeyError, TypeError, ValueError):
                        continue
        except Exception:
            previo = {}

    fusionado = dict(previo)
    altas = cambios = 0
    for idx, e in nuevo.items():
        anterior = previo.get(idx)
        fila = {"id": idx, "grupo": e["grupo"], "nombre": e["nombre"],
                "descripcion": e["descripcion"], "termino": e["termino"],
                "visto": hoy}
        if anterior is None:
            fusionado[idx] = fila
            altas += 1
            continue
        # Una entrada de relleno nunca degrada una buena ya guardada.
        if e["_relleno"] and (anterior.get("nombre") or "") not in ("", "(de la lista fija)"):
            anterior["visto"] = hoy
            continue
        if any((anterior.get(c) or "") != (fila[c] or "")
               for c in ("grupo", "nombre", "descripcion", "termino")):
            cambios += 1
        fusionado[idx] = fila

    cols = ["id", "grupo", "nombre", "descripcion", "termino", "visto"]
    filas = [fusionado[i] for i in sorted(fusionado)]
    # Solo se reescribe si el contenido cambia de verdad. Comparar el texto
    # generado, y no los campos, evita reescrituras por diferencias de formato.
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore",
                       lineterminator="\n")
    w.writeheader()
    for fila in filas:
        w.writerow({c: fila.get(c, "") for c in cols})
    contenido = buf.getvalue()

    anterior_txt = ""
    if os.path.isfile(ruta):
        try:
            anterior_txt = open(ruta, encoding="utf-8").read()
        except Exception:
            anterior_txt = ""

    # El campo `visto` cambia todos los días y por sí solo no justifica un
    # commit: se compara ignorando esa columna.
    def sin_visto(t):
        return "\n".join(l.rsplit(",", 1)[0] for l in t.splitlines())

    escrito = False
    if sin_visto(contenido) != sin_visto(anterior_txt):
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        escrito = True

    registrar("esios_catalogo_fichero", "OK",
              f"{len(filas)} indicadores en {ruta}"
              + (f" · {altas} altas, {cambios} modificados, REESCRITO" if escrito
                 else " · sin cambios, no se reescribe"),
              extra={"total": len(filas), "altas": altas, "cambios": cambios,
                     "reescrito": escrito})
    return ruta


COLUMNAS_SEGUIMIENTO = [
    "captura_madrid", "indicador", "nombre", "estado", "values_updated_at",
    "fecha_min", "fecha_max", "dias_cubiertos", "n_periodos",
    "suma_valores", "hash_valores",
]


def _fila_seguimiento(idx, nombre, estado, ind, df):
    """
    Una foto compacta de un indicador de la cadena de programación, tal como
    estaba en ESTA captura.

    `suma_valores` y `hash_valores` son lo que permite detectar una
    republicación AUNQUE `values_updated_at` no cambie: si el hash cambia, el
    contenido cambió. Y al revés — si cambia `values_updated_at` pero no el
    hash, hubo refresco sin cambio de datos. Las dos cosas interesan y las dos
    se pierden si no se graban en su momento.
    """
    fila = {
        "captura_madrid": MANIFIESTO.get("ejecucion_madrid", ""),
        "indicador": idx, "nombre": nombre, "estado": estado,
        "values_updated_at": (ind or {}).get("values_updated_at", ""),
        "fecha_min": "", "fecha_max": "", "dias_cubiertos": 0,
        "n_periodos": 0, "suma_valores": "", "hash_valores": "",
    }
    if df is None or df.empty:
        # Una fila vacía NO es ruido: es la que dice «a esta hora todavía no
        # estaba publicado», y es la mitad de la respuesta a cuándo aparece
        # por primera vez el programa del día siguiente.
        return fila
    col = "datetime" if "datetime" in df.columns else "datetime_utc"
    fechas = df[col].astype(str)
    valores = pd.to_numeric(df["value"], errors="coerce")
    fila.update({
        "fecha_min": fechas.min(), "fecha_max": fechas.max(),
        "dias_cubiertos": fechas.str[:10].nunique(),
        "n_periodos": len(df),
        "suma_valores": round(float(valores.fillna(0).sum()), 1),
        "hash_valores": hash_texto(",".join(
            "" if pd.isna(v) else f"{v:.4f}" for v in valores)),
    })
    return fila


def actualizar_seguimiento(filas):
    """
    Añade al fichero acumulativo `archivo/seguimiento_programas.csv`. Mismo
    criterio que el índice: se AÑADE, y solo se reescribe entero si cambia la
    cabecera o si esta captura ya estaba registrada.

    No se poda nada. Durante los primeros meses, que es cuando se está
    caracterizando el comportamiento, cualquier poda destruye justamente lo
    que se quiere medir. Con 28 indicadores y 8 capturas diarias son ~224
    filas al día: unas 80.000 al año, que en CSV son pocos MB.
    """
    if not filas:
        return 0
    ruta = os.path.join(CARPETA_RAIZ, "seguimiento_programas.csv")
    previas, cabecera = [], None
    if os.path.isfile(ruta):
        try:
            with open(ruta, newline="", encoding="utf-8") as f:
                lector = csv.DictReader(f)
                cabecera = lector.fieldnames
                previas = list(lector)
        except Exception:
            previas, cabecera = [], None

    capturas = {f["captura_madrid"] for f in filas}
    repetida = any(p.get("captura_madrid") in capturas for p in previas)
    if cabecera != COLUMNAS_SEGUIMIENTO or repetida:
        previas = [p for p in previas
                   if p.get("captura_madrid") and
                   p.get("captura_madrid") not in capturas]
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS_SEGUIMIENTO,
                               extrasaction="ignore")
            w.writeheader()
            for p in previas:
                w.writerow({c: p.get(c, "") for c in COLUMNAS_SEGUIMIENTO})
            for fila in filas:
                w.writerow(fila)
    else:
        with open(ruta, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS_SEGUIMIENTO,
                               extrasaction="ignore")
            for fila in filas:
                w.writerow(fila)
    return len(previas) + len(filas)


def capturar_esios_previsiones(carpeta, hoy, catalogo):
    """
    Todas las previsiones descubiertas, en un ÚNICO fichero comprimido en
    formato largo. Un CSV por indicador serían decenas de ficheros diminutos
    por día y un repositorio incómodo de mirar; comprimido y junto ocupa una
    fracción y se lee con una línea de pandas.
    """
    titulo(f"e·sios — archivo de {len(catalogo)} previsiones (comprimido)")
    if not ESIOS_TOKEN or not catalogo:
        return

    ini = dt.datetime.combine(hoy - dt.timedelta(days=DIAS_PREVISION_ATRAS),
                              dt.time(0, 0), tzinfo=TZ_MADRID).isoformat()
    fin = (dt.datetime.combine(hoy + dt.timedelta(days=DIAS_ADELANTE),
                               dt.time(0, 0), tzinfo=TZ_MADRID)
           - dt.timedelta(seconds=1)).isoformat()

    trozos, meta, seguimiento = [], [], []
    ok = vacios = fallos = 0
    t0 = time.time()
    limite = MINUTOS_MAX_BARRIDO * 60
    cortado_en = None
    for i, entrada in enumerate(catalogo, 1):
        if time.time() - t0 > limite:
            cortado_en = i
            print(f"  ⏱ Presupuesto de {MINUTOS_MAX_BARRIDO} min agotado en el "
                  f"indicador {i} de {len(catalogo)}.")
            print("    Se guarda lo capturado y se anota el corte: una foto")
            print("    incompleta y declarada vale mucho más que ninguna foto.")
            break
        idx = entrada["id"]
        df, ind, error = _serie_esios(idx, ini, fin)
        if df is None:
            if ind is not None:
                vacios += 1
                estado = "vacio"
            else:
                fallos += 1
                estado = "fallo"
            meta.append({"id": idx, "nombre": entrada["nombre"],
                         "estado": estado, "detalle": error,
                         "values_updated_at": (ind or {}).get("values_updated_at"),
                         "filas": 0})
            if idx in PROGRAMAS_SEGUIDOS:
                seguimiento.append(_fila_seguimiento(
                    idx, (ind or {}).get("name") or entrada["nombre"],
                    estado, ind, None))
        else:
            df = df.copy()
            df.insert(0, "indicador", idx)
            trozos.append(df)
            ok += 1
            meta.append({"id": idx, "nombre": entrada["nombre"],
                         "estado": "ok", "detalle": "",
                         "values_updated_at": ind.get("values_updated_at"),
                         "filas": len(df)})
            if idx in PROGRAMAS_SEGUIDOS:
                seguimiento.append(_fila_seguimiento(
                    idx, ind.get("name") or entrada["nombre"], "ok", ind, df))
        if i % 50 == 0:
            print(f"    {i}/{len(catalogo)} procesados "
                  f"({time.time() - t0:.0f}s)...")
        time.sleep(PAUSA_BARRIDO)

    df_meta = pd.DataFrame(meta)
    # El catálogo ya NO se guarda dentro de la captura: vive en ruta fija y
    # acumulativa (ver guardar_catalogo). Lo que sí es propio de cada captura
    # es el meta —estado, filas y values_updated_at cambian cada vez—.
    try:
        guardar_catalogo(catalogo)
    except Exception as e:
        registrar("esios_catalogo_fichero", "FALLO",
                  f"{type(e).__name__}: {e}")
    guardar(df_meta, carpeta, "esios_previsiones_meta", comprimir=False)

    # El seguimiento va en su propio try: llegados aquí las series ya están
    # capturadas y esto es contabilidad. Que un fallo aquí tumbe una captura
    # buena sería absurdo.
    try:
        total = actualizar_seguimiento(seguimiento)
        con_datos = sum(1 for f in seguimiento if f["estado"] == "ok")
        p48 = next((f for f in seguimiento if f["indicador"] == 84), None)
        detalle = (f"{len(seguimiento)} indicadores ({con_datos} con datos), "
                   f"{total} filas acumuladas")
        if p48:
            detalle += (f" · P48 FV hasta {p48['fecha_max'][:16] or '—'}"
                        f" (publicado {str(p48['values_updated_at'])[:19] or '—'})")
        registrar("esios_seguimiento_programas",
                  "OK" if seguimiento else "VACIO", detalle,
                  filas=len(seguimiento))
    except Exception as e:
        registrar("esios_seguimiento_programas", "FALLO",
                  f"{type(e).__name__}: {e}")

    if not trozos:
        registrar("esios_previsiones", "FALLO", "ningún indicador devolvió datos")
        return

    completo = pd.concat(trozos, ignore_index=True)
    ruta = guardar(completo, carpeta, "esios_previsiones")
    tam_kb = os.path.getsize(ruta) / 1024
    segundos = round(time.time() - t0)
    aviso = "" if cortado_en is None else \
        f", CORTADO en {cortado_en}/{len(catalogo)}"
    registrar("esios_previsiones", "OK" if cortado_en is None else "PARCIAL",
              f"{ok} con datos, {vacios} vacíos, {fallos} fallidos "
              f"({tam_kb:.0f} KB, {segundos}s{aviso})",
              filas=len(completo),
              extra={"indicadores_ok": ok, "indicadores_vacios": vacios,
                     "indicadores_fallidos": fallos,
                     "kb_comprimido": round(tam_kb, 1),
                     "segundos": segundos, "cortado_en": cortado_en,
                     "pedidos": len(catalogo)})


# ============================================================================
# ENTSO-E
# ============================================================================

def _sin_ns(tag):
    return tag.split("}")[-1]


def _minutos_iso(txt):
    """
    P7D, PT15M, PT60M, P1D... -> minutos. None si no se entiende.

    Se interpreta como duración ISO 8601 genérica y NO contra una lista
    cerrada de valores: una tabla cerrada descartó en silencio toda la serie
    semanal `P7D` de la reserva hidráulica y costó dos versiones de programa
    (Aprendizaje_API_ENTSOe §5).
    """
    if not txt or not txt.startswith("P"):
        return None
    dias = horas = mins = 0
    num, en_tiempo = "", False
    for c in txt[1:]:
        if c == "T":
            en_tiempo, num = True, ""
        elif c.isdigit():
            num += c
        else:
            if not num:
                return None
            v = int(num)
            if c == "D":
                dias = v
            elif c == "W":
                dias = v * 7
            elif c == "H":
                horas = v
            elif c == "M" and en_tiempo:
                mins = v
            elif c == "M":
                dias = v * 30
            num = ""
    return (dias * 1440 + horas * 60 + mins) or None


def _parsear_entsoe(xml_texto, campo_valor):
    """Las posiciones omitidas repiten el último valor conocido (§5)."""
    filas = []
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError:
        return filas
    for ts in raiz.iter():
        if _sin_ns(ts.tag) != "TimeSeries":
            continue
        psr = None
        for hijo in ts.iter():
            if _sin_ns(hijo.tag) == "psrType":
                psr = hijo.text
                break
        for period in ts.iter():
            if _sin_ns(period.tag) != "Period":
                continue
            inicio = resolucion = None
            for hijo in period.iter():
                et = _sin_ns(hijo.tag)
                if et == "start" and inicio is None:
                    inicio = hijo.text
                elif et == "resolution" and resolucion is None:
                    resolucion = hijo.text
            paso_min = _minutos_iso(resolucion)
            if not inicio or not paso_min:
                continue
            t0 = dt.datetime.fromisoformat(inicio.replace("Z", "+00:00"))
            paso = dt.timedelta(minutes=paso_min)
            puntos = {}
            for punto in period.iter():
                if _sin_ns(punto.tag) != "Point":
                    continue
                pos = val = None
                for hijo in punto:
                    et = _sin_ns(hijo.tag)
                    if et == "position":
                        pos = int(hijo.text)
                    elif et == campo_valor:
                        val = float(hijo.text)
                if pos is not None and val is not None:
                    puntos[pos] = val
            if not puntos:
                continue
            ultimo = None
            for pos in range(1, max(puntos) + 1):
                if pos in puntos:
                    ultimo = puntos[pos]
                if ultimo is not None:
                    filas.append((t0 + (pos - 1) * paso, ultimo, psr))
    return filas


def _entsoe(nombre, params_extra, campo, ini, fin):
    params = {"securityToken": ENTSOE_TOKEN,
              "periodStart": ini.strftime("%Y%m%d") + "0000",
              "periodEnd": fin.strftime("%Y%m%d") + "0000"}
    params.update(params_extra)
    try:
        r = requests.get(ENTSOE_API, params=params, timeout=120)
    except Exception as e:
        return None, f"error de red: {e}"
    if r.status_code != 200:
        # HTTP 400 con "No matching data found" NO es un error: es que aún no
        # hay datos publicados (Aprendizaje_API_ENTSOe §2).
        if r.status_code == 400 and "No matching data" in r.text:
            return None, "sin datos publicados todavía"
        return None, f"HTTP {r.status_code}"
    filas = _parsear_entsoe(r.text, campo)
    if not filas:
        return None, "respuesta sin puntos"
    df = pd.DataFrame(filas, columns=["datetime_utc", nombre, "psr_type"])
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    if df["psr_type"].isna().all():
        df = df.drop(columns=["psr_type"])
        df = df.drop_duplicates("datetime_utc")
    else:
        df = df.drop_duplicates(["datetime_utc", "psr_type"])
    return df.sort_values("datetime_utc"), None


def capturar_entsoe(carpeta, hoy):
    titulo("ENTSO-E — previsiones, precios y reserva hidráulica")
    if not ENTSOE_TOKEN:
        registrar("entsoe", "FALLO", "falta ENTSOE_TOKEN")
        return

    ini = hoy - dt.timedelta(days=DIAS_PRECIO_ATRAS)
    fin = hoy + dt.timedelta(days=DIAS_ADELANTE)

    vistas = [
        ("entsoe_A65_prev_demanda_es", "prev_demanda",
         {"documentType": "A65", "processType": "A01",
          "outBiddingZone_Domain": EIC_ES}, "quantity"),
        # A69: previsión de generación renovable, desglosada por psrType
        # (B16 solar, B19 eólica). Es la vista equivalente a las de e·sios,
        # y tenerla duplicada permite contrastar las dos fuentes.
        ("entsoe_A69_prev_renovable_es", "prev_renovable",
         {"documentType": "A69", "processType": "A01", "in_Domain": EIC_ES},
         "quantity"),
        ("entsoe_A44_precio_francia", "precio_francia",
         {"documentType": "A44", "in_Domain": EIC_FR, "out_Domain": EIC_FR},
         "price.amount"),
        ("entsoe_A44_precio_es", "precio_es",
         {"documentType": "A44", "in_Domain": EIC_ES, "out_Domain": EIC_ES},
         "price.amount"),
    ]
    for fichero, columna, extra, campo in vistas:
        df, error = _entsoe(columna, extra, campo, ini, fin)
        if df is None:
            registrar(fichero, "VACIO" if "sin datos" in (error or "") else "FALLO",
                      error)
        else:
            guardar(df, carpeta, fichero)
            registrar(fichero, "OK",
                      f"hasta {df['datetime_utc'].max()}", filas=len(df),
                      extra={"hash": hash_texto(df.to_csv(index=False))})
        time.sleep(2)

    # Reserva hidráulica: semanal (P7D) y con ~9 días de desfase de
    # publicación, así que necesita una ventana más ancha o no cae ninguna
    # lectura dentro.
    df, error = _entsoe("reserva_hidraulica",
                        {"documentType": "A72", "processType": "A16",
                         "in_Domain": EIC_ES}, "quantity",
                        hoy - dt.timedelta(days=35), fin)
    if df is None:
        registrar("entsoe_A72_reserva_hidraulica", "VACIO", error)
    else:
        guardar(df, carpeta, "entsoe_A72_reserva_hidraulica")
        registrar("entsoe_A72_reserva_hidraulica", "OK",
                  f"última lectura {df['datetime_utc'].max()}", filas=len(df))


# ============================================================================
# AEMET — la predicción, que es lo irrecuperable
# ============================================================================

def _aemet_json(ruta):
    """
    Una lectura de AEMET son SIEMPRE dos peticiones: la primera devuelve un
    JSON con la URL del dato real, y la segunda trae el dato. Devuelve
    (datos, error).
    """
    for intento in range(1, 4):
        try:
            r = requests.get(f"{AEMET_BASE}{ruta}",
                             params={"api_key": AEMET_TOKEN}, timeout=90)
        except Exception as e:
            error = f"error de red: {e}"
            time.sleep(10 * intento)
            continue
        # AEMET devuelve 429 esporádicos incluso sin exceso de ritmo evidente
        # (Aprendizaje_API_AEMET_y_Otros §4.6).
        if r.status_code == 429:
            error = "HTTP 429"
            time.sleep(20 * intento)
            continue
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        j = r.json()
        if j.get("estado") != 200 or not j.get("datos"):
            return None, f"estado={j.get('estado')}"
        r2 = requests.get(j["datos"], timeout=90)
        # AEMET a veces declara mal la codificación: UTF-8 y si no, Latin-1.
        texto = r2.content.decode("utf-8", errors="replace")
        if "\ufffd" in texto:
            texto = r2.content.decode("latin-1")
        return json.loads(texto), None
    return None, error


def _val(x):
    """Los valores vienen unas veces sueltos y otras dentro de una lista."""
    if isinstance(x, list):
        return x[0] if x else None
    return x


def _periodo_dia(lista, periodo="00-24"):
    """
    De una lista de tramos, la entrada del periodo pedido. AEMET no siempre
    publica el tramo 00-24: los días parcialmente pasados solo traen los
    tramos que quedan. En ese caso se coge el primero disponible en vez de
    devolver vacío, y así el resumen diario nunca sale en blanco por un
    detalle de formato.
    """
    if not lista:
        return {}
    for e in lista:
        if e.get("periodo") == periodo:
            return e
    for e in lista:
        if not e.get("periodo"):
            return e
    return lista[0]


def capturar_aemet(carpeta, ahora_madrid):
    titulo("AEMET — PREDICCIÓN de temperatura, viento y cielo (irrecuperable)")
    print("  La API solo devuelve la predicción vigente: si no se guarda hoy,")
    print("  no hay forma de saber mañana qué decía. Es el motivo principal")
    print("  por el que existe este programa.")
    if not AEMET_TOKEN:
        registrar("aemet", "FALLO", "falta AEMET_TOKEN")
        return
    # No en todas las capturas: ver HORAS_MINIMAS_ENTRE_AEMET.
    desde = horas_desde_ultima_aemet(ahora_madrid)
    if desde is not None and desde < HORAS_MINIMAS_ENTRE_AEMET:
        registrar("aemet_prediccion_diaria", "OMITIDA",
                  f"la última buena fue hace {desde:.1f} h "
                  f"(mínimo {HORAS_MINIMAS_ENTRE_AEMET} h)")
        return
    print("  Última captura buena: "
          + ("ninguna todavía" if desde is None else f"hace {desde:.1f} h"))

    diarias, periodos, horarias = [], [], []
    fallos_d, fallos_h = [], []

    for codigo, ciudad in MUNICIPIOS_AEMET.items():
        # ---- Producto DIARIO: 7 días, resumen por día y por tramos ----------
        datos, error = _aemet_json(
            f"/api/prediccion/especifica/municipio/diaria/{codigo}")
        if not datos:
            fallos_d.append(f"{ciudad}: {error}")
        else:
            bloque = datos[0]
            elaborado = bloque.get("elaborado")
            for dia in bloque.get("prediccion", {}).get("dia", []):
                fecha = (dia.get("fecha") or "")[:10]
                temp = dia.get("temperatura", {}) or {}
                hr = dia.get("humedadRelativa", {}) or {}
                st = dia.get("sensTermica", {}) or {}
                viento = _periodo_dia(dia.get("viento"))
                racha = _periodo_dia(dia.get("rachaMax"))
                cielo = _periodo_dia(dia.get("estadoCielo"))
                lluvia = _periodo_dia(dia.get("probPrecipitacion"))
                diarias.append({
                    "ciudad": ciudad, "municipio": codigo,
                    "fecha_prevista": fecha,
                    "elaborado": elaborado,   # cuándo se generó esta predicción
                    "tmax": temp.get("maxima"), "tmin": temp.get("minima"),
                    "hr_max": hr.get("maxima"), "hr_min": hr.get("minima"),
                    "sens_max": st.get("maxima"), "sens_min": st.get("minima"),
                    "uv_max": _val(dia.get("uvMax")),
                    "viento_velocidad": _val(viento.get("velocidad")),
                    "viento_direccion": _val(viento.get("direccion")),
                    "racha_max": racha.get("value"),
                    "estado_cielo": cielo.get("value"),
                    "estado_cielo_desc": cielo.get("descripcion"),
                    "prob_precipitacion": lluvia.get("value"),
                })
                # Y además TODOS los tramos, sin resumir: el tramo 12-18 de la
                # eólica no se recupera de una media diaria.
                for var in ("viento", "rachaMax", "estadoCielo",
                            "probPrecipitacion", "cotaNieveProv"):
                    for e in (dia.get(var) or []):
                        periodos.append({
                            "producto": "diaria", "ciudad": ciudad,
                            "fecha_prevista": fecha, "elaborado": elaborado,
                            "variable": var, "periodo": e.get("periodo"),
                            "value": e.get("value"),
                            "descripcion": e.get("descripcion"),
                            "velocidad": _val(e.get("velocidad")),
                            "direccion": _val(e.get("direccion")),
                        })
        time.sleep(PAUSA_AEMET)

        # ---- Producto HORARIO: 48 h hora a hora -----------------------------
        # Es el que de verdad sirve para D+1: viento y estado del cielo con
        # resolución horaria, que es la del mercado. El producto diario da
        # máximos y mínimos, que no sirven para repartir por horas.
        datos, error = _aemet_json(
            f"/api/prediccion/especifica/municipio/horaria/{codigo}")
        if not datos:
            fallos_h.append(f"{ciudad}: {error}")
        else:
            bloque = datos[0]
            elaborado = bloque.get("elaborado")
            for dia in bloque.get("prediccion", {}).get("dia", []):
                fecha = (dia.get("fecha") or "")[:10]
                rejilla = {}
                def poner(var, e, campo="value"):
                    h = e.get("periodo")
                    if not h or len(h) != 2 or not h.isdigit():
                        return False           # tramo, no hora concreta
                    rejilla.setdefault(h, {})[var] = e.get(campo)
                    return True
                for e in (dia.get("temperatura") or []):
                    poner("temperatura", e)
                for e in (dia.get("sensTermica") or []):
                    poner("sens_termica", e)
                for e in (dia.get("humedadRelativa") or []):
                    poner("humedad", e)
                for e in (dia.get("precipitacion") or []):
                    poner("precipitacion", e)
                for e in (dia.get("nieve") or []):
                    poner("nieve", e)
                for e in (dia.get("estadoCielo") or []):
                    if poner("estado_cielo", e):
                        rejilla[e["periodo"]]["estado_cielo_desc"] = \
                            e.get("descripcion")
                # vientoAndRachaMax mezcla DOS cosas en la misma lista: las
                # entradas con direccion/velocidad son el viento medio, y las
                # que traen `value` son la racha máxima. Se separan aquí.
                for e in (dia.get("vientoAndRachaMax") or []):
                    h = e.get("periodo")
                    if not h or len(h) != 2 or not h.isdigit():
                        continue
                    d = rejilla.setdefault(h, {})
                    if e.get("value") is not None:
                        d["racha_max"] = e.get("value")
                    if e.get("velocidad") is not None:
                        d["viento_velocidad"] = _val(e.get("velocidad"))
                        d["viento_direccion"] = _val(e.get("direccion"))
                for h in sorted(rejilla):
                    horarias.append({
                        "ciudad": ciudad, "municipio": codigo,
                        "fecha_prevista": fecha, "hora": h,
                        "datetime_local": f"{fecha}T{h}:00:00",
                        "elaborado": elaborado,
                        "orto": dia.get("orto"), "ocaso": dia.get("ocaso"),
                        **rejilla[h],
                    })
                # Las probabilidades vienen por tramos (0107, 0713...), no por
                # hora. Se guardan tal cual en vez de repartirlas a mano.
                for var in ("probPrecipitacion", "probTormenta", "probNieve"):
                    for e in (dia.get(var) or []):
                        periodos.append({
                            "producto": "horaria", "ciudad": ciudad,
                            "fecha_prevista": fecha, "elaborado": elaborado,
                            "variable": var, "periodo": e.get("periodo"),
                            "value": e.get("value"), "descripcion": None,
                            "velocidad": None, "direccion": None,
                        })
        time.sleep(PAUSA_AEMET)

    # --- Registro, fuente por fuente -----------------------------------------
    if diarias:
        df = pd.DataFrame(diarias)
        guardar(df, carpeta, "aemet_prediccion_diaria", comprimir=False)
        registrar("aemet_prediccion_diaria", "OK" if not fallos_d else "PARCIAL",
                  f"{df['ciudad'].nunique()} de {len(MUNICIPIOS_AEMET)} ciudades, "
                  f"hasta {df['fecha_prevista'].max()}"
                  + (f" · fallan {'; '.join(fallos_d)}" if fallos_d else ""),
                  filas=len(df),
                  extra={"elaborado": sorted(set(df["elaborado"].dropna())),
                         "ciudades": sorted(df["ciudad"].unique())})
    else:
        registrar("aemet_prediccion_diaria", "FALLO",
                  "ninguna ciudad devolvió datos: " + "; ".join(fallos_d))

    if horarias:
        dh = pd.DataFrame(horarias)
        guardar(dh, carpeta, "aemet_prediccion_horaria")
        registrar("aemet_prediccion_horaria", "OK" if not fallos_h else "PARCIAL",
                  f"{dh['ciudad'].nunique()} ciudades, {len(dh)} horas, "
                  f"hasta {dh['fecha_prevista'].max()}"
                  + (f" · fallan {'; '.join(fallos_h)}" if fallos_h else ""),
                  filas=len(dh),
                  extra={"elaborado": sorted(set(dh["elaborado"].dropna()))})
    else:
        registrar("aemet_prediccion_horaria", "FALLO",
                  "ninguna ciudad devolvió datos: " + "; ".join(fallos_h))

    if periodos:
        dp = pd.DataFrame(periodos)
        guardar(dp, carpeta, "aemet_prediccion_periodos")
        registrar("aemet_prediccion_periodos", "OK",
                  f"{dp['variable'].nunique()} variables por tramos",
                  filas=len(dp))


# ============================================================================
# MIBGAS
# ============================================================================

def capturar_mibgas(carpeta, hoy):
    """
    En la primera ejecución real desde GitHub Actions (11-ago-2026) esta fuente
    devolvió `HTTP 200, 549 bytes`: un 200 con un cuerpo minúsculo, o sea que
    no era el XLSX. Es el mismo patrón de trampa que e·sios con los ficheros
    I3/I90 — un código de éxito que no trae lo que dice traer.

    Dos sospechas, y el código las cubre las dos sin poder distinguirlas de
    antemano: que MIBGAS rechace peticiones sin cabeceras de navegador
    completas (venían muy escuetas), o que sirva una página intermedia cuando
    no hay una visita previa al sitio. Por eso ahora se mantiene una sesión,
    se visita primero la página de acceso a ficheros y se envían cabeceras
    realistas.

    Y si aun así falla, **se guarda el principio de la respuesta en el
    manifiesto**: 549 bytes de HTML dicen exactamente qué pasa, mientras que
    "no funcionó" no dice nada. Diagnosticar a ciegas ya nos costó caro en
    este proyecto.
    """
    titulo("MIBGAS — precio del gas (PVB)")
    anio = hoy.year
    cabeceras = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/128.0 Safari/537.36"),
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "application/vnd.openxmlformats-officedocument."
                   "spreadsheetml.sheet,*/*;q=0.8"),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.mibgas.es/es/file-access",
    }
    urls = [
        (f"https://www.mibgas.es/es/file-access/MIBGAS_Data_{anio}.xlsx"
         f"?path=AGNO_{anio}/XLS"),
        (f"https://www.mibgas.es/en/file-access/MIBGAS_Data_{anio}.xlsx"
         f"?path=AGNO_{anio}/XLS"),
    ]

    sesion = requests.Session()
    sesion.headers.update(cabeceras)
    try:
        # Visita previa: algunos sitios sirven el fichero solo si hay cookie
        # de sesión. Si falla, no importa; se sigue igual.
        sesion.get("https://www.mibgas.es/es/file-access", timeout=60)
    except Exception:
        pass

    r = None
    for url in urls:
        try:
            r = sesion.get(url, timeout=120)
        except Exception as e:
            registrar("mibgas", "FALLO", f"error de red: {e}")
            return
        if r.status_code == 200 and len(r.content) >= 10000:
            break

    if r is None or r.status_code != 200 or len(r.content) < 10000:
        muestra = ""
        if r is not None:
            try:
                muestra = r.content[:400].decode("utf-8", errors="replace")
            except Exception:
                muestra = repr(r.content[:200])
        registrar("mibgas", "FALLO",
                  f"HTTP {getattr(r, 'status_code', '?')}, "
                  f"{len(r.content) if r is not None else 0} bytes "
                  f"(no parece un XLSX)",
                  extra={"tipo_contenido": (r.headers.get("Content-Type")
                                            if r is not None else None),
                         "muestra_respuesta": muestra})
        return

    ruta_tmp = os.path.join(carpeta, "_mibgas_tmp.xlsx")
    with open(ruta_tmp, "wb") as f:
        f.write(r.content)
    try:
        # Solo la hoja útil y solo los últimos días: el XLSX anual pesa ~3 MB
        # y guardarlo entero cada día llenaría el repositorio sin aportar nada.
        df = pd.read_excel(ruta_tmp, sheet_name="Trading Data PVB&VTP")
        df.columns = [str(c).strip() for c in df.columns]
        col_dia = next((c for c in df.columns
                        if c.lower().startswith("trading day")), None)
        if col_dia is None:
            registrar("mibgas", "FALLO",
                      f"no se encuentra 'Trading day' en {list(df.columns)[:6]}")
            return
        df[col_dia] = pd.to_datetime(df[col_dia], errors="coerce")
        corte = pd.Timestamp(hoy - dt.timedelta(days=DIAS_PRECIO_ATRAS + 7))
        recorte = df[df[col_dia] >= corte]
        if "Product" in recorte.columns:
            recorte = recorte[recorte["Product"].astype(str).str.startswith("GDAES")]
        guardar(recorte, carpeta, "mibgas_gdaes")
        registrar("mibgas_gdaes", "OK",
                  f"hasta {recorte[col_dia].max().date()}", filas=len(recorte))
    except Exception as e:
        registrar("mibgas", "FALLO", f"{type(e).__name__}: {e}")
    finally:
        if os.path.exists(ruta_tmp):
            os.remove(ruta_tmp)


# ============================================================================
# Índice en ruta fija
# ============================================================================
#
# Por qué existe esto (v3.4): hasta ahora, para saber cómo había ido el
# archivador había que ADIVINAR el nombre de la carpeta, porque lleva el minuto
# real de arranque del script y ese minuto no es predecible —el disparo externo
# pide a y 50, pero la ejecución empieza cuando GitHub asigna máquina—. En la
# práctica eso significaba encadenar 404s probando 0850, 1452, 2303, 2305...
# hasta acertar, o pedirle al usuario que mirara la carpeta a mano.
#
# La solución no es adivinar mejor: es que haya SIEMPRE dos ficheros en una
# ruta que no cambia nunca.
#
#   archivo/ultimo.json  → copia del manifiesto de la última captura.
#   archivo/indice.csv   → una línea por captura, desde la primera.
#
# El índice además responde una pregunta que hasta ahora se contestaba contando
# carpetas a mano: cuántas capturas hay de verdad al día, y cuántas vienen del
# disparador externo frente al cron de GitHub. Por eso se guarda `disparo`.

COLUMNAS_INDICE = [
    "fecha", "hora", "ejecucion_madrid", "ejecucion_utc", "version", "modo",
    "disparo", "ok", "vacio", "fallo", "omitida", "parcial", "kb_total",
    "ruta", "run_id",
]


def _fila_indice(manifiesto, carpeta):
    r = manifiesto.get("resumen", {})
    return {
        "fecha": manifiesto.get("fecha", ""),
        "hora": os.path.basename(carpeta.rstrip("/")),
        "ejecucion_madrid": manifiesto.get("ejecucion_madrid", ""),
        "ejecucion_utc": manifiesto.get("ejecucion_utc", ""),
        "version": manifiesto.get("version", ""),
        "modo": manifiesto.get("modo", ""),
        "disparo": manifiesto.get("disparo", ""),
        "ok": r.get("ok", ""), "vacio": r.get("vacio", ""),
        "fallo": r.get("fallo", ""), "omitida": r.get("omitida", ""),
        "parcial": r.get("parcial", ""), "kb_total": r.get("kb_total", ""),
        "ruta": carpeta.replace(os.sep, "/"),
        "run_id": manifiesto.get("run_id", ""),
    }


def _rellenar_indice(previas):
    """
    Añade al índice las capturas anteriores a la v3.4, que existen en disco pero
    nunca dejaron línea porque el índice no existía cuando corrieron.

    Sin esto, el visor del móvil solo vería el archivo a partir del momento en
    que se estrenó el índice, y los primeros días —que incluyen justo las
    capturas con las que se caracterizó la publicación de las series D+1— serían
    invisibles. Es una reparación de una sola vez: cuando no falta nada, el
    coste es listar unos cientos de rutas y salir.
    """
    rutas = glob.glob(os.path.join(CARPETA_RAIZ, "*", "*", "*", "*",
                                   "manifiesto.json"))
    ya = {p.get("ruta") for p in previas}
    faltan = [r for r in rutas
              if os.path.dirname(r).replace(os.sep, "/") not in ya]
    if not faltan:
        return previas, 0
    añadidas = []
    for r in sorted(faltan):
        try:
            with open(r, encoding="utf-8") as f:
                m = json.load(f)
            añadidas.append(_fila_indice(m, os.path.dirname(r)))
        except Exception:
            continue
    if not añadidas:
        return previas, 0
    print(f"  ↺ Índice: {len(añadidas)} capturas antiguas incorporadas.")
    todas = list(previas) + añadidas
    todas.sort(key=lambda f: (f.get("ejecucion_madrid") or "", f.get("ruta") or ""))
    return todas, len(añadidas)


def actualizar_indice(manifiesto, carpeta):
    """
    Escribe `archivo/ultimo.json` y añade una línea a `archivo/indice.csv`.

    Se hace al final y dentro de su propio try: si esto fallara, la captura ya
    está guardada y el índice es solo comodidad. Nunca debe tumbar una foto
    buena por un problema de contabilidad.

    Se AÑADE una línea en vez de reescribir el fichero entero. No es
    microoptimización: cada reescritura es un blob nuevo en Git, y a ocho
    capturas diarias durante un año eso engorda el repositorio sin motivo. Solo
    se reescribe entero en dos casos —que la cabecera haya cambiado al subir de
    versión, o que ya exista una línea con esta misma ruta (reejecución del
    mismo minuto)—, que son excepcionales.
    """
    fila = _fila_indice(manifiesto, carpeta)

    ruta_ultimo = os.path.join(CARPETA_RAIZ, "ultimo.json")
    with open(ruta_ultimo, "w", encoding="utf-8") as f:
        json.dump({"ruta": fila["ruta"], **manifiesto}, f,
                  ensure_ascii=False, indent=2)

    ruta_indice = os.path.join(CARPETA_RAIZ, "indice.csv")
    previas, cabecera_vieja = [], None
    if os.path.isfile(ruta_indice):
        try:
            with open(ruta_indice, newline="", encoding="utf-8") as f:
                lector = csv.DictReader(f)
                cabecera_vieja = lector.fieldnames
                previas = list(lector)
        except Exception:
            previas, cabecera_vieja = [], None

    previas, rellenadas = _rellenar_indice(previas)

    duplicada = any(p.get("ruta") == fila["ruta"] for p in previas)
    reescribir = (cabecera_vieja != COLUMNAS_INDICE) or duplicada or rellenadas

    if reescribir:
        # Al reescribir se descartan las líneas sin ruta. Sin este filtro, un
        # `indice.csv` corrupto —o truncado a medio push— se «migraba» a la
        # cabecera nueva convertido en filas vacías, y el índice pasaba a
        # mentir sobre cuántas capturas hay. Lo detectó la prueba 8: mejor
        # perder una línea ilegible que arrastrar un recuento falso.
        previas = [p for p in previas
                   if p.get("ruta") and p.get("ruta") != fila["ruta"]]
        with open(ruta_indice, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUMNAS_INDICE,
                                      extrasaction="ignore")
            escritor.writeheader()
            for p in previas:
                escritor.writerow({c: p.get(c, "") for c in COLUMNAS_INDICE})
            escritor.writerow(fila)
    else:
        with open(ruta_indice, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNAS_INDICE,
                           extrasaction="ignore").writerow(fila)

    return ruta_ultimo, ruta_indice, len(previas) + 1


# ============================================================================
def ejecutar():
    ahora_utc = dt.datetime.now(dt.timezone.utc)
    ahora_madrid = ahora_utc.astimezone(TZ_MADRID)
    hoy = ahora_madrid.date()

    print("ARCHIVADOR DIARIO — FASE 0 DEL PROYECTO BESS (v3.9)")
    print(f"Ejecución: {ahora_madrid.isoformat(timespec='seconds')} (Madrid)")
    print(f"           {ahora_utc.isoformat(timespec='seconds')} (UTC)")

    # Una subcarpeta por CAPTURA, no por día: con varias ejecuciones diarias,
    # escribir todas en la misma carpeta hacía que la segunda machacara a la
    # primera. Sobrevivían en el historial de Git, pero comparar dos versiones
    # del mismo día —que es justo lo que queremos estudiar— era incómodo.
    # La hora es la REAL de ejecución, no la programada: así el retraso del
    # cron queda registrado en vez de disimulado.
    carpeta = os.path.join(CARPETA_RAIZ, f"{hoy:%Y}", f"{hoy:%m}",
                           f"{hoy:%Y-%m-%d}", f"{ahora_madrid:%H%M}")
    os.makedirs(carpeta, exist_ok=True)
    print(f"Destino:   {carpeta}/")

    MANIFIESTO.update({
        "version": "v3.9",
        "ejecucion_madrid": ahora_madrid.isoformat(timespec="seconds"),
        "ejecucion_utc": ahora_utc.isoformat(timespec="seconds"),
        "fecha": hoy.isoformat(),
        "dia_objetivo": (hoy + dt.timedelta(days=1)).isoformat(),
        # Quién disparó esta ejecución. GitHub lo pone en el entorno:
        # "schedule" = cron de GitHub, "repository_dispatch"/"workflow_dispatch"
        # = disparo externo o botón manual, "push" = al tocar el código.
        # Con esto, dentro de dos semanas la fiabilidad de cada disparador se
        # mide contando líneas del índice en vez de discutiéndola.
        "disparo": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    })

    modo = "ligero" if ya_hay_captura_completa_hoy(hoy) else "completo"
    MANIFIESTO["modo"] = modo
    print(f"Modo:      {modo}"
          + ("" if modo == "completo" else "  (hoy ya se hizo el barrido completo)"))

    catalogo = []
    try:
        if capturar_esios_principales(carpeta, hoy):
            catalogo = descubrir_previsiones(modo)
            capturar_esios_previsiones(carpeta, hoy, catalogo)
    except Exception as e:
        registrar("e·sios", "FALLO", f"excepción: {type(e).__name__}: {e}")

    for nombre, funcion, args in (
        ("ENTSO-E", capturar_entsoe, (carpeta, hoy)),
        ("AEMET", capturar_aemet, (carpeta, ahora_madrid)),
        ("MIBGAS", capturar_mibgas, (carpeta, hoy)),
    ):
        try:
            funcion(*args)
        except Exception as e:
            registrar(nombre, "FALLO", f"excepción: {type(e).__name__}: {e}")

    estados = [v["estado"] for v in MANIFIESTO["fuentes"].values()]
    tam = sum(os.path.getsize(os.path.join(carpeta, f))
              for f in os.listdir(carpeta)) / 1024
    MANIFIESTO["resumen"] = {
        "ok": estados.count("OK"), "vacio": estados.count("VACIO"),
        "fallo": estados.count("FALLO"), "omitida": estados.count("OMITIDA"),
        "parcial": estados.count("PARCIAL"),
        "kb_total": round(tam, 1),
    }

    with open(os.path.join(carpeta, "manifiesto.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFIESTO, f, ensure_ascii=False, indent=2)

    # El índice va después del manifiesto y en su propio try: llegados aquí la
    # foto ya está en disco, y el índice es comodidad. Que un fallo de
    # contabilidad tumbe una captura buena sería absurdo.
    total_capturas = None
    try:
        _, _, total_capturas = actualizar_indice(MANIFIESTO, carpeta)
    except Exception as e:
        print(f"\n  ⚠ No se pudo actualizar el índice: {type(e).__name__}: {e}")

    titulo("RESUMEN")
    for nombre, info in MANIFIESTO["fuentes"].items():
        print(f"  {info['estado']:6s} {nombre:34s} {info['detalle']}")
    r = MANIFIESTO["resumen"]
    print(f"\n  {r['ok']} OK · {r['vacio']} vacías · {r['fallo']} fallidas")
    print(f"  Tamaño de la foto de hoy: {r['kb_total']:.0f} KB")
    print(f"  Manifiesto en {carpeta}/manifiesto.json")
    if total_capturas is not None:
        print(f"  Índice actualizado: {CARPETA_RAIZ}/ultimo.json y "
              f"{CARPETA_RAIZ}/indice.csv ({total_capturas} capturas)")

    if r["ok"] == 0:
        print("\n  ✗ Ninguna fuente respondió. Esto sí es un fallo real.")
        return 1
    if r["fallo"]:
        # Una foto parcial se guarda igual: el dato de hoy no se recupera
        # mañana, así que perderlo entero por un fallo parcial sería el peor
        # resultado posible.
        print("\n  ⚠ Foto parcial: hay fuentes fallidas, pero se guarda igual.")
        return 0
    print("\n  ✓ Foto completa.")
    return 0


if __name__ == "__main__":
    sys.exit(ejecutar())
