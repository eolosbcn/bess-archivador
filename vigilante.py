#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""VIGILANTE DEL ARCHIVADOR BESS — comprueba que el archivo sigue vivo.

⚠️ ESTE FICHERO NO ES DE CASANDRA. Vive en el repositorio del archivador,
`eolosbcn/bess-archivador`, junto a `archivador_diario.py`, y por eso NO lleva
el prefijo `casandra_` ni entra en la disciplina de versiones de esta carpeta
(plan estratégico -D, fase F−1). Esta copia local existe para poder probarlo
sin red y para que quede bajo git; la que manda es la desplegada.

QUÉ HACE, Y QUÉ NO HACE
=======================
Lee dos ficheros que el archivador ya escribe —`archivo/indice.csv` y
`archivo/ultimo.json`— y, si algo va mal, abre una incidencia en GitHub.

⚠️ NO descarga nada, NO escribe en `archivo\`, NO hace commit y NO toca
`archivador_diario.py`. Su workflow se declara con `contents: read`, así que
aunque tuviera un fallo no podría modificar el archivo. Es de solo mirar.

LAS TRES COMPROBACIONES
=======================
1. ANTIGÜEDAD. La última captura no puede tener más de UMBRAL_HORAS.
2. FUENTE MUDA. Una familia entera de fuentes callada a la vez.
3. CADUCIDAD. El token de AEMET es un JWT y lleva su fecha dentro.

POR QUÉ ESTAS TRES, Y NO «avisar de cualquier fallo»
====================================================
Avisar de cualquier fallo sería la trampa 7 de la casa —un aviso que salta
siempre deja de ser un aviso—. ✅ Medido sobre 410 capturas del archivo el
7-sep-2026: **32 de ellas tienen algún fallo suelto**, 103 fallos en total. Un
vigilante que avisara de eso habría abierto 32 incidencias en tres semanas y
nadie volvería a mirarlas.

HISTORIAL
=========
v1.02  7-sep-2026. **Una avería REAL dejaba de salir etiquetada como
       simulacro.** La v1.01 ponía el prefijo `[SIMULACRO]` a *todas* las
       incidencias de una pasada de prueba, no solo a la que la prueba
       forzaba. Pasó a la primera: al hacer la prueba de disparo de
       `antiguedad`, ENTSO-E estaba caído de verdad y su alarma —cierta— se
       abrió como `[SIMULACRO] La fuente entsoe está muda`.
       ⚠️ Eso es **peor que no avisar**: una alarma real disfrazada de prueba
       es la que alguien descarta de un vistazo pensando «ah, es el simulacro
       de ayer». El chivato suena y además enseña a ignorarlo.
       Ahora cada alarma lleva la marca **solo si es la que se ha forzado**, y
       hay una prueba del escenario exacto: simulacro de antigüedad con una
       fuente caída de verdad.

v1.01  7-sep-2026. **Las incidencias se ASIGNAN**, y con eso el vigilante deja
       de estar a medias. La v1.00 abría la issue y daba el trabajo por hecho;
       media hora después de desplegarse cazó una caída real de ENTSO-E —cinco
       HTTP 503 a la vez— y Xevi preguntó lo único que faltaba por comprobar:
       «¿dónde he recibido yo esta alarma?». En ninguna parte fiable: que una
       issue de un bot llegue a una persona depende de su *watching* y de su
       configuración de correo. Asignarla notifica siempre y llega al móvil.
       ⚠️ Y va con su comprobación, porque la API **ignora en silencio** un
       asignado que no puede asignar y devuelve 201 igualmente: sin mirar el
       `assignees` de la respuesta, el fallo se disfrazaría de éxito y
       volveríamos al mismo sitio, pero convencidos de lo contrario.

v1.00  7-sep-2026. Primera versión. Nace de la fase F−1 del plan estratégico
       de Casandra, y de dos hechos del 7-sep-2026: (a) la acción X6 demostró
       que de las cuatro credenciales del proyecto **solo AEMET declara fecha
       de caducidad**, así que la defensa contra el fallo mudo no puede ser una
       alarma de calendario y recae entera en la detección; (b) Xevi preguntó
       qué pasa «si el token ha caducado y no recibimos error»: todo saldría
       vacío y nadie se enteraría. De ahí la comprobación 2.
"""

import argparse
import base64
import collections
import csv
import datetime as dt
import io
import json
import os
import sys

# ============================================================================
# LOS UMBRALES, Y LA MEDICIÓN QUE LOS SOSTIENE
# ============================================================================
# ⚠️ La casa manda escribir una puerta con la cifra que el instrumento da HOY,
# copiada de su salida (trampa 8). Aquí están, con su muestra.

# ✅ Medido sobre 87 huecos entre capturas, desde el 28-ago-2026 —cuando el
# disparo pasó a cron-job.org— hasta el 7-sep-2026:
#     mediana 3,00 h · p90 3,00 h · p99 3,02 h · MÁXIMO 3,02 h
#     huecos de más de 5 h: 0
# O sea que 6 h son el doble del peor hueco jamás observado, y equivalen a dos
# capturas seguidas perdidas. Por debajo de 5 h estaríamos rozando el ruido
# normal; por encima de 8 h tardaríamos casi un día en enterarnos.
UMBRAL_HORAS = 6.0

# Días de antelación con que se avisa de una credencial a punto de caducar.
UMBRAL_CADUCIDAD_DIAS = 15

# ⚠️ Una familia de UNA SOLA fuente no dispara la alarma de fuente muda: que
# falle una fuente aislada es ruido normal (ver la medición de arriba). Hoy la
# única familia de tamaño 1 es `mibgas`, que además no usa credencial, así que
# no es la que esta alarma viene a proteger.
MINIMO_FUENTES_POR_FAMILIA = 2

# ⚠️ A QUIÉN SE LE ASIGNA LA INCIDENCIA, y por qué esto no es un adorno.
# ---------------------------------------------------------------------------
# La v1.00 abría la incidencia y ahí acababa su trabajo. El 7-sep-2026, media
# hora después de desplegarla, cazó una caída real de ENTSO-E... y Xevi
# preguntó lo único que importaba: «¿dónde he recibido yo esta alarma?».
#
# En ninguna parte fiable. Que una issue abierta por un bot llegue a una
# persona depende de que esa persona esté *watching* del repositorio y de
# cómo tenga la configuración de correo. **Una alarma que nadie recibe no es
# una alarma**, que es la trampa 7 de la casa por su lado peor: el chivato
# sonaba, y sonaba en una habitación vacía.
#
# Asignar la incidencia notifica al asignado SIEMPRE, sin depender del
# *watching*, y llega como aviso a la app de GitHub del móvil.
ASIGNAR_A = os.environ.get("VIGILANTE_ASIGNAR_A", "eolosbcn")


# ============================================================================
# LECTURA — funciones puras, sin red, para poder probarlas
# ============================================================================

def leer_ultima_captura(ruta_indice):
    """Devuelve el instante UTC de la última fila de `indice.csv`.

    ⚠️ Lee por NOMBRE de columna, nunca por posición (trampa 4 de la casa):
    el archivador ha añadido columnas al índice a lo largo del tiempo —las
    filas viejas traen `omitida` y `parcial` en blanco— y un lector por
    posición se rompería en silencio el día que se añada otra.
    """
    with io.open(ruta_indice, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise ValueError("el índice está vacío: no hay ni una captura")
    ultima = filas[-1]
    if "ejecucion_utc" not in ultima:
        raise ValueError("el índice no tiene la columna `ejecucion_utc`")
    return dt.datetime.fromisoformat(ultima["ejecucion_utc"]), ultima


def familia_de(nombre_fuente):
    """`entsoe_A44_precio_es` -> `entsoe`.

    ⚠️ En minúsculas a propósito: en los manifiestos antiguos conviven
    `aemet_*` y `AEMET_*`, y sin normalizar serían dos familias distintas —una
    de tres fuentes y otra de una—, que es la trampa 5 de la casa (comparar por
    la etiqueta del fichero en vez de por clave canónica).
    """
    return nombre_fuente.split("_")[0].lower()


def familias_mudas(fuentes, minimo=MINIMO_FUENTES_POR_FAMILIA):
    """Familias en las que NINGUNA fuente ha salido OK.

    ✅ Probada sobre los 409 manifiestos del archivo el 7-sep-2026: dispara en
    **23 capturas (5,6 %)**, y las 23 son `entsoe` entre el 30-ago y el 2-sep
    —el corte real de ENTSO-E, confirmado por ellos mismos por correo—. Cero
    disparos en las otras 386. La regla estaba probada antes de desplegarse.
    """
    por_familia = collections.defaultdict(list)
    for nombre, datos in fuentes.items():
        por_familia[familia_de(nombre)].append((datos or {}).get("estado"))

    mudas = []
    for familia, estados in sorted(por_familia.items()):
        if len(estados) >= minimo and all(e != "OK" for e in estados):
            mudas.append((familia, len(estados)))
    return mudas


def caducidad_del_jwt(token):
    """Fecha de caducidad de un JWT, leyendo su `exp` SIN validar la firma.

    ⚠️ No verifica nada criptográficamente y no debe usarse para autenticar:
    solo lee una fecha que el propio token lleva escrita. Devuelve `None` si el
    token no es un JWT o no trae `exp`.

    ⚠️ NUNCA devuelve ni imprime el token. Solo la fecha.
    """
    if not token or token.count(".") != 2:
        return None
    carga = token.split(".")[1]
    carga += "=" * (-len(carga) % 4)          # el JWT va sin relleno base64
    try:
        datos = json.loads(base64.urlsafe_b64decode(carga).decode("utf-8"))
    except Exception:
        return None
    exp = datos.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    return dt.datetime.fromtimestamp(exp, dt.timezone.utc)


# ============================================================================
# LAS COMPROBACIONES
# ============================================================================

class Incidencia(object):
    """Algo que hay que mirar. `clave` sirve para no duplicar la issue."""

    def __init__(self, clave, titulo, cuerpo):
        self.clave = clave
        self.titulo = titulo
        self.cuerpo = cuerpo

    def __repr__(self):
        return "Incidencia(%r)" % self.clave


def comprobar(raiz, ahora=None, token_aemet=None, simulacro=None):
    """Devuelve la lista de incidencias. Función PURA: no habla con la red.

    `simulacro` fuerza una de las condiciones sin tocar un solo fichero, que es
    la prueba de disparo de F−1: el archivo sigue sano y lo que cambia es la
    regla, no el dato.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    incidencias = []

    def marca(cual):
        """El prefijo `[SIMULACRO]` SOLO lo lleva la alarma que se ha forzado.

        ⚠️ CORREGIDO EN LA v1.02, y es el fallo más peligroso que ha tenido
        este programa. La v1.01 ponía el prefijo a **todas** las incidencias de
        una pasada de simulacro, así que una avería REAL detectada durante la
        prueba salía etiquetada como simulacro.

        Pasó de verdad el 7-sep-2026: al hacer la prueba de disparo de
        `antiguedad`, ENTSO-E estaba caído y su alarma —cierta— se abrió como
        `[SIMULACRO] La fuente entsoe está muda`.

        Una alarma real disfrazada de prueba es **peor que no avisar**: es la
        que alguien descarta de un vistazo pensando «ah, es el simulacro de
        ayer». El chivato suena y además enseña a ignorarlo.
        """
        return "[SIMULACRO] " if simulacro == cual else ""

    prefijo = marca("antiguedad")

    # ---- 1. antigüedad ----------------------------------------------------
    # En el simulacro el umbral se pone en 0 h: el archivo está perfectamente
    # al día, pero la regla es imposible de cumplir y la alarma salta.
    umbral = 0.0 if simulacro == "antiguedad" else UMBRAL_HORAS
    instante, fila = leer_ultima_captura(os.path.join(raiz, "indice.csv"))
    horas = (ahora - instante).total_seconds() / 3600.0
    if horas > umbral:
        incidencias.append(Incidencia(
            "antiguedad",
            "%s⚠️ El archivo lleva %.1f h sin actualizarse" % (prefijo, horas),
            "La última captura del índice es de **%s UTC**, hace **%.1f h**, y "
            "el umbral son **%.1f h**.\n\n"
            "- Ruta de esa captura: `%s`\n"
            "- Ejecución que la escribió: `%s`\n\n"
            "El umbral está medido, no supuesto: ✅ sobre 87 huecos entre "
            "capturas desde el 28-ago-2026, la mediana es de 3,00 h y el "
            "máximo observado 3,02 h; ninguno pasó de 5 h.\n\n"
            "**Qué mirar, por orden:** que cron-job.org siga disparando; que "
            "las Actions no estén paradas por minutos agotados; y que el "
            "último `run` no haya fallado."
            % (instante.isoformat(), horas, umbral,
               fila.get("ruta", "?"), fila.get("run_id", "?"))))

    # ---- 2. fuente muda ---------------------------------------------------
    ruta_ultimo = os.path.join(raiz, "ultimo.json")
    with io.open(ruta_ultimo, encoding="utf-8") as f:
        ultimo = json.load(f)
    fuentes = ultimo.get("fuentes") or {}
    if not fuentes:
        incidencias.append(Incidencia(
            "sin_fuentes",
            "⚠️ `ultimo.json` no trae ninguna fuente",
            "El manifiesto de la última captura existe pero su bloque "
            "`fuentes` está vacío. Eso no es una fuente muda: es el archivador "
            "escribiendo algo que no debería."))
    else:
        estados = {k: (v or {}).get("estado") for k, v in fuentes.items()}

        if simulacro == "fuente_muda":
            # ⚠️ El simulacro finge que calla UNA sola familia, no todas: así
            # deja UNA incidencia que cerrar y no cuatro. Se elige `entsoe` por
            # ser la que de verdad enmudeció —30-ago a 2-sep-2026— y, si no
            # estuviera, la familia más numerosa.
            cuantas_por_familia = collections.Counter(
                familia_de(k) for k in fuentes)
            elegida = ("entsoe" if "entsoe" in cuantas_por_familia
                       else cuantas_por_familia.most_common(1)[0][0])
            fingidas = {k: ({"estado": "SIMULACRO"}
                            if familia_de(k) == elegida else v)
                        for k, v in fuentes.items()}
            estados = {k: (v or {}).get("estado") for k, v in fingidas.items()}
            # ⚠️ `fingidas` es un diccionario NUEVO en memoria. El fichero
            # `ultimo.json` no se ha abierto para escribir en ningún momento.
            mudas = familias_mudas(fingidas, 1)
        else:
            mudas = familias_mudas(fuentes, MINIMO_FUENTES_POR_FAMILIA)

        for familia, cuantas in mudas:
            caidas = sorted(k for k in fuentes if familia_de(k) == familia)
            incidencias.append(Incidencia(
                "muda:" + familia,
                "%s⚠️ La fuente `%s` está muda: sus %d ficheros vacíos"
                % (marca("fuente_muda"), familia, cuantas),
                "**Ninguna** de las %d fuentes de la familia `%s` ha salido OK "
                "en la última captura (`%s`).\n\n"
                "Fuentes afectadas:\n%s\n\n"
                "⚠️ Esta alarma **no intenta adivinar la causa**, a propósito: "
                "el silencio total de una fuente es grave venga de donde venga "
                "—credencial muerta, bloqueo temporal por exceso de "
                "peticiones, o caída del proveedor—.\n\n"
                "**Antes de regenerar ningún token, lee** "
                "`aprendizajes_api_entsoe` §2.quater: lo que parece una "
                "caducidad suele ser un **bloqueo temporal** que se levanta "
                "solo en unos 10 minutos, y regenerar el token es la respuesta "
                "equivocada.\n\n"
                "Para calibrar: ✅ esta regla, pasada sobre los 409 "
                "manifiestos del archivo, dispara 23 veces, y las 23 son el "
                "corte real de ENTSO-E del 30-ago al 2-sep-2026."
                % (cuantas, familia, ultimo.get("ruta", "?"),
                   "\n".join("- `%s` → `%s`" % (k, estados.get(k)) for k in caidas))))

    # ---- 3. caducidad de credenciales -------------------------------------
    # Solo AEMET puede comprobarse así: es el único de los cuatro tokens del
    # proyecto que declara caducidad, y además la lleva dentro (es un JWT).
    # ✅ Comprobado sobre 1 caso el 7-sep-2026 (acción X6 del plan).
    if token_aemet:
        caduca = caducidad_del_jwt(token_aemet)
        if caduca is None:
            incidencias.append(Incidencia(
                "aemet_ilegible",
                "⚠️ El token de AEMET ya no parece un JWT",
                "No se ha podido leer la fecha de caducidad del token de "
                "AEMET. O ha cambiado de formato, o el secreto contiene otra "
                "cosa. **No se ha impreso el token en ningún sitio.**"))
        else:
            dias = (caduca - ahora).total_seconds() / 86400.0
            aviso = 10**6 if simulacro == "caducidad" else UMBRAL_CADUCIDAD_DIAS
            if dias < aviso:
                incidencias.append(Incidencia(
                    "caducidad:aemet",
                    "%s⚠️ El token de AEMET caduca en %d días (%s)"
                    % (marca("caducidad"), int(dias), caduca.date().isoformat()),
                    "El token de AEMET declara `exp` = **%s UTC**, dentro de "
                    "**%d días**.\n\nSe renueva desde el portal de AEMET "
                    "OpenData con el mismo correo. ⚠️ El token nuevo se guarda "
                    "como secreto del repositorio **y** en la variable de "
                    "entorno de la máquina local: son dos sitios, y olvidar el "
                    "segundo deja los programas locales sin AEMET sin que "
                    "nada avise."
                    % (caduca.isoformat(), int(dias))))

    return incidencias


# ============================================================================
# PUBLICACIÓN — la única parte que habla con la red
# ============================================================================

def peticion_de_issue(inc, etiqueta, asignar_a=None):
    """Construye el cuerpo de la petición. PURA, para poder probarla.

    Está fuera de `publicar()` a propósito: lo que se puede probar sin red se
    prueba sin red. Dentro de la función que llama a la API no lo probaría
    nadie, que es la trampa 3 de la casa —«nada que calcule vive dentro de la
    ventana»— trasladada a un cliente HTTP.
    """
    # La clave va en un comentario HTML: invisible al leer, y estable aunque
    # alguien edite el título.
    cuerpo = ("<!-- clave: %s -->\n\n%s\n\n---\n*Abierta por el vigilante del "
              "archivador.*" % (inc.clave, inc.cuerpo))
    peticion = {"title": inc.titulo, "body": cuerpo, "labels": [etiqueta]}
    if asignar_a:
        peticion["assignees"] = [asignar_a]
    return peticion


def publicar(incidencias, repo, token, etiqueta="vigilante", asignar_a=None):
    """Abre una issue por incidencia, si no hay ya una abierta con su clave.

    ⚠️ El antiduplicado no es un lujo: sin él, una avería de un día abriría 8
    incidencias idénticas —una por captura— y al tercer día nadie las miraría.
    Es la trampa 7 otra vez, ahora por el lado del volumen.
    """
    import urllib.error
    import urllib.request

    def api(camino, datos=None):
        pet = urllib.request.Request(
            "https://api.github.com" + camino,
            data=json.dumps(datos).encode("utf-8") if datos else None,
            headers={"Authorization": "Bearer " + token,
                     "Accept": "application/vnd.github+json",
                     "User-Agent": "vigilante-bess"},
            method="POST" if datos else "GET")
        with urllib.request.urlopen(pet, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    abiertas = api("/repos/%s/issues?state=open&labels=%s&per_page=100"
                   % (repo, etiqueta))
    ya = set()
    for issue in abiertas:
        cuerpo = issue.get("body") or ""
        for linea in cuerpo.splitlines():
            if linea.startswith("<!-- clave:"):
                ya.add(linea.split(":", 1)[1].strip().rstrip("->").strip())

    creadas, omitidas = [], []
    for inc in incidencias:
        if inc.clave in ya:
            omitidas.append(inc.clave)
            continue
        # La clave va en un comentario HTML: invisible al leer, y estable
        # aunque alguien edite el título.
        creada = api("/repos/%s/issues" % repo,
                     peticion_de_issue(inc, etiqueta, asignar_a))
        creadas.append(inc.clave)

        # ⚠️ Y AQUÍ SE COMPRUEBA QUE LA ASIGNACIÓN HA PEGADO, que no es
        # paranoia: la API de GitHub **ignora en silencio** un asignado que no
        # puede asignar —usuario mal escrito, sin permiso sobre el
        # repositorio— y devuelve la issue creada igual, con `assignees`
        # vacío y código 201. O sea que el fallo devuelve ÉXITO.
        #
        # Sin esta comprobación volveríamos exactamente al problema que este
        # cambio viene a resolver: una incidencia que existe y no avisa a
        # nadie, y encima con la tranquilidad de creer que sí.
        if asignar_a:
            asignados = [u.get("login") for u in (creada.get("assignees") or [])]
            if asignar_a not in asignados:
                print("  ⚠️ AVISO: la incidencia #%s se ha creado pero NO se ha "
                      "podido asignar a `%s`." % (creada.get("number"), asignar_a))
                print("     GitHub no da error al ignorar un asignado, así que "
                      "esto solo se ve mirándolo.")
                print("     Consecuencia: puede que nadie reciba el aviso. "
                      "Comprueba el nombre de usuario y sus permisos.")
    return creadas, omitidas


# ============================================================================
# PRUEBAS INTERNAS
# ============================================================================

def autotest():
    """Prueba las funciones puras. No toca la red ni el repositorio."""
    import tempfile
    fallos = []
    pasadas = []

    def comprobar_que(condicion, nombre):
        print("   %s  %s" % ("OK  " if condicion else "FALLA", nombre))
        (pasadas if condicion else fallos).append(nombre)

    print("\n-- familia_de -----------------------------------------------")
    comprobar_que(familia_de("entsoe_A44_precio_es") == "entsoe",
                  "el prefijo sale bien")
    comprobar_que(familia_de("AEMET_prediccion") == "aemet",
                  "las mayúsculas se normalizan (trampa 5)")

    print("\n-- familias_mudas -------------------------------------------")
    todo_ok = {"esios_a": {"estado": "OK"}, "esios_b": {"estado": "OK"}}
    comprobar_que(familias_mudas(todo_ok) == [],
                  "con todo OK no salta nada")

    una_caida = {"esios_a": {"estado": "OK"}, "esios_b": {"estado": "FALLO"}}
    comprobar_que(familias_mudas(una_caida) == [],
                  "un fallo suelto NO salta (trampa 7: 32 de 410 capturas "
                  "tienen alguno)")

    familia_muda = {"entsoe_a": {"estado": "FALLO"},
                    "entsoe_b": {"estado": "VACIO"},
                    "esios_a": {"estado": "OK"}}
    comprobar_que(familias_mudas(familia_muda) == [("entsoe", 2)],
                  "la familia entera callada SÍ salta")

    solitaria = {"mibgas_gdaes": {"estado": "FALLO"}}
    comprobar_que(familias_mudas(solitaria) == [],
                  "una familia de una sola fuente no salta")

    print("\n-- caducidad_del_jwt ----------------------------------------")
    futuro = int((dt.datetime.now(dt.timezone.utc)
                  + dt.timedelta(days=40)).timestamp())
    carga = base64.urlsafe_b64encode(
        json.dumps({"exp": futuro}).encode()).decode().rstrip("=")
    jwt = "cabecera." + carga + ".firma"
    leida = caducidad_del_jwt(jwt)
    comprobar_que(leida is not None and abs(
        (leida - dt.datetime.fromtimestamp(futuro, dt.timezone.utc))
        .total_seconds()) < 2, "lee el `exp` de un JWT bien formado")
    comprobar_que(caducidad_del_jwt("esto-no-es-un-jwt") is None,
                  "una cadena cualquiera devuelve None, no revienta")
    comprobar_que(caducidad_del_jwt("") is None, "y la cadena vacía también")

    print("\n-- peticion_de_issue (v1.01: el asignado) -------------------")
    inc = Incidencia("muda:entsoe", "titulo de prueba", "cuerpo de prueba")
    p = peticion_de_issue(inc, "vigilante", "eolosbcn")
    comprobar_que(p.get("assignees") == ["eolosbcn"],
                  "la incidencia se asigna: sin esto el aviso no llega a nadie")
    comprobar_que(p["labels"] == ["vigilante"], "lleva su etiqueta")
    comprobar_que("<!-- clave: muda:entsoe -->" in p["body"],
                  "la clave viaja en el cuerpo, para el antiduplicado")
    comprobar_que("assignees" not in peticion_de_issue(inc, "vigilante", None),
                  "sin asignado, no se manda el campo vacío")

    print("\n-- comprobar, sobre un archivo de mentira -------------------")
    with tempfile.TemporaryDirectory() as tmp:
        ahora = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.timezone.utc)
        reciente = (ahora - dt.timedelta(hours=2)).isoformat()

        def escribir(instante, fuentes):
            with io.open(os.path.join(tmp, "indice.csv"), "w",
                         encoding="utf-8", newline="") as f:
                f.write("fecha,ejecucion_utc,ruta,run_id\n")
                f.write("2026-09-07,%s,archivo/x,123\n" % instante)
            with io.open(os.path.join(tmp, "ultimo.json"), "w",
                         encoding="utf-8") as f:
                json.dump({"ruta": "archivo/x", "fuentes": fuentes}, f)

        sanas = {"esios_a": {"estado": "OK"}, "esios_b": {"estado": "OK"},
                 "entsoe_a": {"estado": "OK"}, "entsoe_b": {"estado": "OK"}}

        escribir(reciente, sanas)
        comprobar_que(comprobar(tmp, ahora) == [],
                      "archivo sano y reciente: NINGUNA incidencia")

        viejo = (ahora - dt.timedelta(hours=9)).isoformat()
        escribir(viejo, sanas)
        r = comprobar(tmp, ahora)
        comprobar_que([i.clave for i in r] == ["antiguedad"],
                      "archivo de hace 9 h: salta antigüedad, y solo esa")

        escribir(reciente, dict(sanas, entsoe_a={"estado": "FALLO"},
                                entsoe_b={"estado": "VACIO"}))
        r = comprobar(tmp, ahora)
        comprobar_que([i.clave for i in r] == ["muda:entsoe"],
                      "entsoe entera muda: salta fuente muda, y solo esa")

        print("\n-- el SIMULACRO, con el archivo sano ------------------------")
        escribir(reciente, sanas)
        comprobar_que(comprobar(tmp, ahora) == [],
                      "punto de partida: sin simulacro no salta nada")

        r = comprobar(tmp, ahora, simulacro="antiguedad")
        comprobar_que([i.clave for i in r] == ["antiguedad"]
                      and r[0].titulo.startswith("[SIMULACRO]"),
                      "simulacro de antigüedad: salta y se marca [SIMULACRO]")

        r = comprobar(tmp, ahora, simulacro="fuente_muda")
        comprobar_que(len(r) >= 1 and all(
            i.titulo.startswith("[SIMULACRO]") for i in r),
            "simulacro de fuente muda: salta y se marca")

        # ⚠️ LA PRUEBA QUE FALTABA EN LA v1.01, y que habría cazado el fallo.
        # Escenario real del 7-sep-2026: se hace el simulacro de ANTIGÜEDAD
        # mientras una fuente está caída DE VERDAD. La alarma cierta NO puede
        # salir etiquetada como simulacro.
        escribir(reciente, dict(sanas, entsoe_a={"estado": "FALLO"},
                                entsoe_b={"estado": "VACIO"}))
        r = comprobar(tmp, ahora, simulacro="antiguedad")
        por_clave = {i.clave: i for i in r}
        comprobar_que(
            por_clave["antiguedad"].titulo.startswith("[SIMULACRO]"),
            "durante un simulacro, la alarma FORZADA sí lleva la marca")
        comprobar_que(
            not por_clave["muda:entsoe"].titulo.startswith("[SIMULACRO]"),
            "⚠️ y la alarma REAL de la misma pasada NO la lleva")

        # ⚠️ Se devuelve el fichero de mentira a su estado sano: la
        # comprobación de más abajo mira que los simulacros no lo hayan
        # tocado, y este bloque sí lo ha reescrito a propósito. Sin esto, esa
        # comprobación falla y acusa al programa de algo que hizo la prueba.
        escribir(reciente, sanas)

        # ⚠️ Y lo que de verdad importa del simulacro: que NO haya tocado nada.
        with io.open(os.path.join(tmp, "ultimo.json"), encoding="utf-8") as f:
            despues = json.load(f)
        comprobar_que(despues["fuentes"] == sanas,
                      "⚠️ tras los simulacros, `ultimo.json` está INTACTO")

        r = comprobar(tmp, ahora, token_aemet=jwt, simulacro="caducidad")
        comprobar_que(any(i.clave == "caducidad:aemet" for i in r),
                      "simulacro de caducidad: salta con un token que no caduca")
        comprobar_que(not any(jwt in (i.titulo + i.cuerpo) for i in r),
                      "⚠️ el token NO aparece en ninguna incidencia")

    print("\n" + "=" * 64)
    if fallos:
        print("  %d PRUEBAS FALLIDAS: %s" % (len(fallos), ", ".join(fallos)))
        return 1
    # ⚠️ Contadas, no escritas a mano: un número puesto a ojo aquí convierte
    # el banco de pruebas en decoración el día que alguien añada una y no
    # actualice la cifra.
    print("  Las %d pruebas pasan." % len(pasadas))
    return 0


# ============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raiz", default="archivo",
                   help="carpeta con indice.csv y ultimo.json")
    p.add_argument("--simulacro",
                   choices=["antiguedad", "fuente_muda", "caducidad"],
                   help="fuerza una condición SIN tocar ningún fichero, para "
                        "comprobar que la alarma suena (prueba de disparo)")
    p.add_argument("--publicar", action="store_true",
                   help="abre las incidencias en GitHub. Sin esto solo imprime")
    p.add_argument("--autotest", action="store_true")
    a = p.parse_args()

    if a.autotest:
        return autotest()

    incidencias = comprobar(a.raiz,
                            token_aemet=os.environ.get("AEMET_TOKEN"),
                            simulacro=a.simulacro)

    if a.simulacro:
        print("⚠️  SIMULACRO «%s»: la regla se fuerza, los ficheros NO se "
              "tocan.\n" % a.simulacro)

    if not incidencias:
        print("✅ Sin incidencias. El archivo está al día y ninguna fuente "
              "está muda.")
        return 0

    print("Se han encontrado %d incidencia(s):\n" % len(incidencias))
    for i in incidencias:
        print("  [%s] %s" % (i.clave, i.titulo))

    if a.publicar:
        repo = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repo or not token:
            print("\n⚠️ Falta GITHUB_REPOSITORY o GITHUB_TOKEN: no se publica.")
            return 1
        creadas, omitidas = publicar(incidencias, repo, token,
                                     asignar_a=ASIGNAR_A)
        if creadas and ASIGNAR_A:
            print("\n  asignadas a `%s`, que es lo que hace que el aviso "
                  "llegue al móvil." % ASIGNAR_A)
        print("\n  abiertas: %s" % (", ".join(creadas) or "ninguna"))
        print("  ya estaban abiertas (no se duplican): %s"
              % (", ".join(omitidas) or "ninguna"))

    # ⚠️ Devuelve 0 aunque haya incidencias: el aviso es la issue, no un
    # workflow en rojo. Un vigilante que se pone rojo cada vez que detecta algo
    # llena de correos de «workflow failed» y acaba silenciado.
    return 0


if __name__ == "__main__":
    sys.exit(main())
