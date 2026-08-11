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

Versión: v3.1 — 2026-08-11.
"""

import os
import sys
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
GRUPOS_BUSQUEDA = {
    "prevision": ["previsión", "prevista", "previsto"],
    "programa": ["D+1", "H+3"],
}

# Red de seguridad: si el descubrimiento falla, se bajan al menos estos, que
# son los ya catalogados en Aprendizaje_API_REE §4.6.
PREVISIONES_CONOCIDAS = [
    460, 541, 542, 543, 603, 1775, 1776, 1777, 1778,
    2563, 10034, 10249, 10358, 10359,
]

# Tope POR GRUPO, no global: así una familia no puede desplazar a la otra, que
# es exactamente lo que pasó con el tope único. A ~1 petición/segundo, 500
# indicadores son unos 8 minutos, holgados dentro del tiempo del workflow.
MAX_POR_GRUPO = {"prevision": 350, "programa": 150}

# AEMET no se pide en todas las capturas. Su predicción se elabora unas pocas
# veces al día (medido: 08:55 y 10:35), así que pedirla cada hora devuelve lo
# mismo y además nos gana un HTTP 429 — ya pasó en dos de las tres primeras
# capturas horarias. Se pide cuando la hora es múltiplo de este número.
CADA_CUANTAS_HORAS_AEMET = 3

MUNICIPIOS_AEMET = {
    "28079": "madrid", "08019": "barcelona", "46250": "valencia",
    "41091": "sevilla", "48020": "bilbao", "50297": "zaragoza",
}

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
    marca = {"OK": "✓", "VACIO": "·", "FALLO": "✗", "OMITIDA": "–"}.get(estado, "?")
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

def descubrir_previsiones():
    """
    Busca en el catálogo de e·sios todos los indicadores que parezcan una
    previsión. Se hace en cada ejecución a propósito: si REE publica un
    indicador nuevo, entra solo, sin que nadie tenga que enterarse.
    """
    titulo("e·sios — descubrimiento del catálogo, por grupos")
    encontrados, por_grupo = {}, {}

    for grupo, terminos in GRUPOS_BUSQUEDA.items():
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
                    "descripcion": (ind.get("description") or "")[:300].strip(),
                    "termino": termino,
                }
                nuevos += 1
            print(f"  [{grupo}] '{termino}': {len(lista)} resultados, "
                  f"{nuevos} nuevos")
            time.sleep(1)

        tope = MAX_POR_GRUPO.get(grupo, 200)
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

    ids = sorted(encontrados)
    detalle = " · ".join(f"{g}: {v['archivados']}/{v['encontrados']}"
                         for g, v in por_grupo.items())
    registrar("esios_catalogo", "OK" if ids else "FALLO",
              f"{len(ids)} a archivar ({detalle})",
              extra={"por_grupo": por_grupo, "total_archivados": len(ids)})
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
            # El precio spot en plano: es el que más se consulta a ojo.
            guardar(df, carpeta, etiqueta, comprimir=(indicador != 600))
            registrar(etiqueta, "OK",
                      f"{df['datetime_utc'].min()[:10]} a {df['datetime_utc'].max()[:10]}",
                      filas=len(df),
                      extra={"values_updated_at": ind.get("values_updated_at"),
                             "hash": hash_texto(df.to_csv(index=False))})
        time.sleep(1)
    return True


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

    trozos, meta = [], []
    ok = vacios = fallos = 0
    for i, entrada in enumerate(catalogo, 1):
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
        else:
            df = df.copy()
            df.insert(0, "indicador", idx)
            trozos.append(df)
            ok += 1
            meta.append({"id": idx, "nombre": entrada["nombre"],
                         "estado": "ok", "detalle": "",
                         "values_updated_at": ind.get("values_updated_at"),
                         "filas": len(df)})
        if i % 20 == 0:
            print(f"    {i}/{len(catalogo)} indicadores procesados...")
        time.sleep(1)

    df_meta = pd.DataFrame(meta)
    # El catálogo con nombres y descripciones se guarda aparte: es lo que
    # permitirá saber, dentro de un año, qué era el indicador 10358.
    guardar(pd.DataFrame(catalogo), carpeta, "esios_catalogo_previsiones",
            comprimir=False)
    guardar(df_meta, carpeta, "esios_previsiones_meta", comprimir=False)

    if not trozos:
        registrar("esios_previsiones", "FALLO", "ningún indicador devolvió datos")
        return

    completo = pd.concat(trozos, ignore_index=True)
    ruta = guardar(completo, carpeta, "esios_previsiones")
    tam_kb = os.path.getsize(ruta) / 1024
    registrar("esios_previsiones", "OK",
              f"{ok} con datos, {vacios} vacíos, {fallos} fallidos "
              f"({tam_kb:.0f} KB comprimidos)",
              filas=len(completo),
              extra={"indicadores_ok": ok, "indicadores_vacios": vacios,
                     "indicadores_fallidos": fallos,
                     "kb_comprimido": round(tam_kb, 1)})


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

def capturar_aemet(carpeta, hora_actual):
    titulo("AEMET — PREDICCIÓN de temperatura (irrecuperable después)")
    print("  La API solo devuelve la predicción vigente: si no se guarda hoy,")
    print("  no hay forma de saber mañana qué decía. Es el motivo principal")
    print("  por el que existe este programa.")
    if not AEMET_TOKEN:
        registrar("aemet", "FALLO", "falta AEMET_TOKEN")
        return
    # No en todas las capturas: ver CADA_CUANTAS_HORAS_AEMET.
    if hora_actual % CADA_CUANTAS_HORAS_AEMET != 0:
        registrar("aemet_prediccion_diaria", "OMITIDA",
                  f"solo se pide cada {CADA_CUANTAS_HORAS_AEMET} h "
                  f"(su predicción se elabora pocas veces al día)")
        return

    filas = []
    for codigo, ciudad in MUNICIPIOS_AEMET.items():
        ruta = f"/api/prediccion/especifica/municipio/diaria/{codigo}"
        datos, error = None, None
        for intento in range(1, 4):
            try:
                r = requests.get(f"{AEMET_BASE}{ruta}",
                                 params={"api_key": AEMET_TOKEN}, timeout=90)
            except Exception as e:
                error = f"error de red: {e}"
                time.sleep(10 * intento)
                continue
            # AEMET devuelve 429 esporádicos incluso sin exceso de ritmo
            # evidente (Aprendizaje_API_AEMET_y_Otros §4.6).
            if r.status_code == 429:
                error = "HTTP 429"
                time.sleep(20 * intento)
                continue
            if r.status_code != 200:
                error = f"HTTP {r.status_code}"
                break
            j = r.json()
            if j.get("estado") != 200 or not j.get("datos"):
                error = f"estado={j.get('estado')}"
                break
            r2 = requests.get(j["datos"], timeout=90)
            # AEMET a veces declara mal la codificación: UTF-8 y si no, Latin-1.
            texto = r2.content.decode("utf-8", errors="replace")
            if "�" in texto:
                texto = r2.content.decode("latin-1")
            datos = json.loads(texto)
            error = None
            break

        if not datos:
            registrar(f"aemet_{ciudad}", "FALLO", error or "sin datos")
            time.sleep(3)
            continue

        bloque = datos[0]
        elaborado = bloque.get("elaborado")
        for dia in bloque.get("prediccion", {}).get("dia", []):
            temp = dia.get("temperatura", {})
            filas.append({
                "ciudad": ciudad, "municipio": codigo,
                "fecha_prevista": (dia.get("fecha") or "")[:10],
                "elaborado": elaborado,   # cuándo se generó esta predicción
                "tmax": temp.get("maxima"), "tmin": temp.get("minima"),
            })
        time.sleep(3)

    if not filas:
        registrar("aemet_prediccion", "FALLO", "ninguna ciudad devolvió datos")
        return
    df = pd.DataFrame(filas)
    guardar(df, carpeta, "aemet_prediccion_diaria", comprimir=False)
    registrar("aemet_prediccion_diaria", "OK",
              f"{df['ciudad'].nunique()} ciudades, hasta {df['fecha_prevista'].max()}",
              filas=len(df),
              extra={"elaborado": sorted(set(df["elaborado"].dropna()))})


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
def ejecutar():
    ahora_utc = dt.datetime.now(dt.timezone.utc)
    ahora_madrid = ahora_utc.astimezone(TZ_MADRID)
    hoy = ahora_madrid.date()

    print("ARCHIVADOR DIARIO — FASE 0 DEL PROYECTO BESS (v3.1)")
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
        "version": "v3.1",
        "ejecucion_madrid": ahora_madrid.isoformat(timespec="seconds"),
        "ejecucion_utc": ahora_utc.isoformat(timespec="seconds"),
        "fecha": hoy.isoformat(),
        "dia_objetivo": (hoy + dt.timedelta(days=1)).isoformat(),
    })

    catalogo = []
    try:
        if capturar_esios_principales(carpeta, hoy):
            catalogo = descubrir_previsiones()
            capturar_esios_previsiones(carpeta, hoy, catalogo)
    except Exception as e:
        registrar("e·sios", "FALLO", f"excepción: {type(e).__name__}: {e}")

    for nombre, funcion, args in (
        ("ENTSO-E", capturar_entsoe, (carpeta, hoy)),
        ("AEMET", capturar_aemet, (carpeta, ahora_madrid.hour)),
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
        "kb_total": round(tam, 1),
    }

    with open(os.path.join(carpeta, "manifiesto.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFIESTO, f, ensure_ascii=False, indent=2)

    titulo("RESUMEN")
    for nombre, info in MANIFIESTO["fuentes"].items():
        print(f"  {info['estado']:6s} {nombre:34s} {info['detalle']}")
    r = MANIFIESTO["resumen"]
    print(f"\n  {r['ok']} OK · {r['vacio']} vacías · {r['fallo']} fallidas")
    print(f"  Tamaño de la foto de hoy: {r['kb_total']:.0f} KB")
    print(f"  Manifiesto en {carpeta}/manifiesto.json")

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
