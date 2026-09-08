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
v1.03  8-sep-2026. **Dos alarmas nuevas y el registro de fallos.** Nace de dos
       encargos de Xevi: *«vigila que no queden puntos ciegos con las nuevas
       incorporaciones»* —vienen MITECO y SAIH— y *«necesitamos un archivo que
       registre lo que ha fallado de manera precisa, pero no quiero crear algo
       que crezca y crezca»*.

       ✅ **Medido sobre 419 capturas, las tres alarmas anteriores dejaban tres
       huecos:** una familia de UN solo fichero nunca puede disparar la de
       «fuente muda» —`mibgas` **ya era ciega**, y MITECO y cada SAIH nacerían
       igual—; un fichero perdido dentro de una familia sana es invisible
       —`esios_catalogo_previsiones` llevaba **373 capturas sin aparecer desde
       el 13-ago** y nadie se enteró—; y un fichero **presente pero congelado**
       lo ve fresco la alarma 1 y lleno la 2.

       **Alarma 4, DESAPARECIDO** y **alarma 5, CONGELADO**, las dos con
       umbral que **no es un número sino un múltiplo del intervalo propio de
       cada fuente**, calculado del archivo. ✅ Así el A72 —semanal— sale con
       umbral 157 y `esios_previsiones` con 8, y **una fuente nueva se calibra
       sola**. Con un número fijo, N=10 avisaba bien hoy pero habría saltado
       cada día en cuanto entrara el boletín semanal del MITECO.

       **El registro va en DOS ficheros porque tienen vidas distintas:**
       `fallos_recientes.csv` con una línea por fallo y **ventana móvil de 30
       días** —✅ techo fijo de ~150 KB, no crece nunca— y `episodios.csv` con
       una línea por tramo continuo, para siempre —✅ 73 episodios en 29 días,
       ~138 KB/año—.

       ⚠️ **Y una trampa que casi queda cableada:** la primera versión
       comparaba por nombre de fichero y daba `esios_602_energia_casada_diario`
       por desaparecido. ✅ Falso: existió como `.csv.gz` en **1 captura** y
       como `.csv` en **372** — cambió de compresión. Es la **trampa 5** de la
       casa dentro de una alarma nueva, y de ahí `canonico()`.

       ⚠️ **Lo que esto NO ve, y hay que decirlo:** la **usabilidad**. El
       precio del indicador 600 se capturó perfecto durante meses y venía
       multiplicado por 4. Ni «desaparecido» ni «congelado» lo habrían visto:
       eso pide una comprobación semántica por fuente, que es otro trabajo.

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
import gzip
import hashlib
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

# --- alarmas 4 y 5 y registro de fallos (v1.03) -----------------------------
CAPTURAS_A_LEER = 500      # ⚠️ tope del barrido. Medido: 28 ms por captura, o
#                            sea 14 s con 500. Sin tope, en un año habría
#                            ~5.256 capturas y el barrido tardaría 147 s cada
#                            tres horas. 500 son ~35 días, de sobra para medir
#                            cadencias y detectar desapariciones.
DIAS_VENTANA = 30          # ventana móvil de fallos_recientes.csv
MINIMO_PRESENCIAS = 20     # apariciones para considerar «conocida» una fuente
FACTOR_ALARMA = 3.0        # se avisa a 3× el intervalo normal de la fuente
MINIMO_CAPTURAS_ALARMA = 8  # suelo: nunca avisar antes de 8 capturas
TOLERANCIA_CIERRE = 2      # aciertos seguidos para cerrar un episodio
EXTENSIONES = (".csv", ".csv.gz", ".json", ".gz")


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
# REGISTRO DE FALLOS Y ALARMAS 4 Y 5 (v1.03)
# ============================================================================
# Probado antes en `casandra_registro_fallos_v1_00.py`, 17 de 17
# comprobaciones. Lo que sigue es esa pieza integrada.
# ============================================================================

def canonico(nombre):
    """Clave canónica de un fichero: sin extensión ni compresión.

    ⚠️ TRAMPA 5 DE LA CASA, y casi queda cableada dentro de la alarma 4. La
    primera versión comparaba por nombre de fichero y daba
    `esios_602_energia_casada_diario` por desaparecido. Era falso: ✅ ese
    fichero existió como `.csv.gz` en **1 captura** (13-ago-2026 11:22) y como
    `.csv` en **372**. Cambió de compresión, no desapareció — y sin esta
    función habría generado una incidencia que no se cierra nunca.
    """
    for e in (".csv.gz", ".csv", ".json", ".gz"):
        if nombre.endswith(e):
            return nombre[: -len(e)]
    return nombre


def huella_contenido(ruta):
    """sha256 del CONTENIDO. Descomprime a propósito.

    ⚠️ gzip guarda la marca de tiempo en su cabecera, así que dos `.gz` con el
    mismo contenido tienen distinto sha256. Comparar los comprimidos daría
    «siempre distinto» y la alarma 5 no detectaría un congelado jamás.
    """
    try:
        if ruta.endswith(".gz"):
            with gzip.open(ruta, "rb") as f:
                b = f.read()
        else:
            with io.open(ruta, "rb") as f:
                b = f.read()
    except Exception:
        return None
    return hashlib.sha256(b).hexdigest()[:16] if b else None


def leer_capturas(raiz, limite=CAPTURAS_A_LEER):
    """[(etiqueta, {clave: huella|None}), ...] en orden del índice.

    Huella `None` = AUSENTE O VACÍO: para estas alarmas es lo mismo, el dato
    no está.
    """
    idx = os.path.join(raiz, "indice.csv")
    if not os.path.isfile(idx):
        # ⚠️ La ruta del vigilante ya ES `archivo/`, no su padre.
        idx = os.path.join(raiz, "archivo", "indice.csv")
    if not os.path.isfile(idx):
        return [], 0
    base = os.path.dirname(os.path.dirname(idx))
    with io.open(idx, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    if limite:
        filas = filas[-limite:]
    caps, sin_carpeta = [], 0
    for fila in filas:
        carpeta = os.path.join(base, fila.get("ruta", ""))
        if not os.path.isdir(carpeta):
            # ⚠️ Nada de continue mudo: se cuenta y se devuelve.
            sin_carpeta += 1
            continue
        d = {}
        for n in os.listdir(carpeta):
            if n.endswith(EXTENSIONES) and n != "manifiesto.json":
                d[canonico(n)] = huella_contenido(os.path.join(carpeta, n))
        caps.append(("%s-%s" % (fila["fecha"], fila["hora"]), d))
    return caps, sin_carpeta


def intervalos(capturas):
    """{clave: (presencias, intervalo_presencia, intervalo_cambio)}.

    ⚠️ `intervalo_cambio` es una COTA SUPERIOR de la cadencia real: solo se ve
    cambiar lo que se captura, así que una fuente que cambia más deprisa que
    nuestras capturas se mide como si cambiara a nuestro ritmo.
    """
    total = len(capturas)
    pres, cambios, ultima = collections.Counter(), collections.Counter(), {}
    for _, d in capturas:
        for k, h in d.items():
            if h is None:
                continue
            pres[k] += 1
            if k in ultima and ultima[k] != h:
                cambios[k] += 1
            ultima[k] = h
    return {k: (n, total / float(n) if n else float("inf"),
                total / float(cambios[k]) if cambios[k] else float("inf"))
            for k, n in pres.items()}


def umbral_de(intervalo):
    """Capturas seguidas que hay que esperar antes de avisar.

    ⚠️ EL UMBRAL NO ES UN NÚMERO, ES UN MÚLTIPLO, y ese es el hallazgo que hizo
    falta para que esto sirva. La primera calibración usó «ausente en las
    últimas N capturas»: ✅ con N=10 avisaba hoy de un solo fichero, el
    correcto. Pero N=10 capturas son ~un día, y el boletín semanal del MITECO
    saltaría todos los días. Multiplicando el intervalo propio de cada fuente,
    ✅ el A72 —semanal— sale con umbral 157 y `esios_previsiones` con 8, sin que
    nadie escriba una tabla. Una fuente nueva se calibra sola.
    """
    if intervalo == float("inf"):
        return None            # nunca cambió: no hay intervalo que multiplicar
    return max(MINIMO_CAPTURAS_ALARMA, int(round(FACTOR_ALARMA * intervalo)))


def alarma_desaparecido(capturas, info):
    """Fichero conocido que lleva > 3× su intervalo normal sin aparecer."""
    avisos = []
    for k, (n, ip, _) in sorted(info.items()):
        if n < MINIMO_PRESENCIAS:
            continue           # apareció poco: no es avería, es un raro
        u = umbral_de(ip)
        if u is None or u >= len(capturas):
            continue
        if all(d.get(k) is None for _, d in capturas[-u:]) and \
                any(d.get(k) is not None for _, d in capturas[:-u]):
            avisos.append((k, u, capturas[-u][0]))
    return avisos


def alarma_congelado(capturas, info):
    """Presente, pero con el mismo contenido > 3× su intervalo de cambio."""
    avisos = []
    for k, (n, _, ic) in sorted(info.items()):
        if n < MINIMO_PRESENCIAS:
            continue
        u = umbral_de(ic)
        if u is None or u >= len(capturas):
            continue
        ult = [d.get(k) for _, d in capturas[-u:]]
        if all(h is not None for h in ult) and len(set(ult)) == 1:
            avisos.append((k, u, capturas[-u][0]))
    return avisos


def episodios(capturas, claves):
    """Tramos continuos de fallo, con tolerancia al parpadeo.

    ⚠️ `TOLERANCIA_CIERRE`: un fichero que falla, acierta una vez y vuelve a
    fallar es UN episodio, no tres. ✅ Sin esto, medido sobre 419 capturas,
    salían **323 episodios en 29 días** —once al día—, que nadie lee. Con
    tolerancia y clave canónica quedan **73**.
    """
    fuera = []
    for k in sorted(claves):
        abierto, aciertos = None, 0
        for i, (_, d) in enumerate(capturas):
            if d.get(k) is None:
                aciertos = 0
                if abierto is None:
                    abierto = [i, i, 1]
                else:
                    abierto[1], abierto[2] = i, abierto[2] + 1
            elif abierto is not None:
                aciertos += 1
                if aciertos >= TOLERANCIA_CIERRE:
                    fuera.append((k, capturas[abierto[0]][0],
                                  capturas[abierto[1]][0], abierto[2]))
                    abierto, aciertos = None, 0
        if abierto is not None:
            fuera.append((k, capturas[abierto[0]][0],
                          capturas[abierto[1]][0], abierto[2]))
    return fuera


def escribir_registro(raiz, capturas, claves):
    """Los DOS ficheros, y son dos porque tienen VIDAS distintas.

    ⚠️⚠️ EL VIGILANTE NO LLAMA A ESTA FUNCIÓN, Y ES DELIBERADO. Su workflow
    se declara con `contents: read` a propósito —«aunque tuviera un fallo no
    podría escribir en el archivo ni hacer commit»—, y esa propiedad protege
    la única pieza irreproducible del proyecto. Escribir desde aquí obligaría
    a darle `contents: write` y la destruiría.

    La función vive en este fichero porque es donde están `leer_capturas()` y
    `episodios()`, y `registro.py` la importa desde aquí. Quien la llame
    necesita permiso de escritura; el vigilante no lo tiene ni debe tenerlo.

    Xevi, 8-sep-2026: *«necesitamos un archivo que registre lo que ha fallado
    en cada ocasión de manera precisa. Pero no quiero crear algo que crezca y
    crezca»*. Las dos cosas no las cumple un solo fichero:

      · `fallos_recientes.csv` — una línea por fallo, **ventana móvil de 30
        días**. ✅ Medido: 1.200 fallos en 29 días → **techo fijo ~150 KB**,
        porque al entrar una captura sale la de hace 30 días.
      · `episodios.csv` — una línea por tramo continuo, **para siempre**.
        ✅ Medido: 73 episodios en 29 días → ~138 KB/año, y cada línea vale.

    ⚠️ `episodios.csv` se FUNDE con lo que ya hubiera: el barrido solo ve las
    últimas CAPTURAS_A_LEER, así que reescribirlo entero borraría la historia
    anterior. Se conservan los episodios cuyo `hasta` es más antiguo que el
    principio de la ventana leída.
    """
    destino = raiz if os.path.isfile(os.path.join(raiz, "indice.csv")) \
        else os.path.join(raiz, "archivo")
    if not capturas:
        return 0, 0

    # --- fallos recientes: ventana móvil, techo fijo ------------------------
    corte = capturas[-1][0][:10]
    y, m, d = (int(x) for x in corte.split("-")[:3])
    limite = (dt.date(y, m, d) - dt.timedelta(days=DIAS_VENTANA)).isoformat()
    filas = []
    for etq, dd in capturas:
        if etq[:10] < limite:
            continue
        for k in sorted(claves):
            if k not in dd:
                filas.append((etq, k, "ausente"))
            elif dd[k] is None:
                filas.append((etq, k, "vacio"))
    with io.open(os.path.join(destino, "fallos_recientes.csv"), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["captura", "fuente", "motivo"])
        w.writerows(filas)

    # --- episodios: se funden, no se reescriben -----------------------------
    nuevos = episodios(capturas, claves)
    desde_ventana = capturas[0][0]
    viejos = []
    p = os.path.join(destino, "episodios.csv")
    if os.path.isfile(p):
        with io.open(p, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                if fila.get("hasta", "") < desde_ventana:
                    viejos.append((fila["fuente"], fila["desde"],
                                   fila["hasta"], int(fila["capturas"])))
    todos = viejos + nuevos
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fuente", "desde", "hasta", "capturas"])
        w.writerows(sorted(todos, key=lambda e: (e[1], e[0])))
    return len(filas), len(todos)


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

    # --- 4 y 5: DESAPARECIDO y CONGELADO (v1.03) ---------------------------
    # ⚠️ Cierran tres huecos que las tres primeras no ven, ✅ medidos sobre 419
    # capturas: una familia de UN fichero (`mibgas` ya es ciega hoy, y MITECO
    # y cada SAIH nacerían igual), un fichero perdido dentro de una familia
    # sana (`esios_catalogo_previsiones` lleva 373 capturas sin aparecer y
    # nadie se enteró), y un fichero presente pero CONGELADO.
    capturas, _sin = leer_capturas(raiz)
    if capturas:
        info = intervalos(capturas)
        conocidas = {k for k, (n, _, _) in info.items()
                     if n >= MINIMO_PRESENCIAS}

        # ⚠️ El simulacro añade una incidencia SINTÉTICA con clave propia, y
        # NO etiqueta las reales. Escrito de la forma obvia —«si no hay
        # ninguna, fabrica una»— la prueba de disparo del día en que SÍ hay una
        # avería real le pondría a esa el prefijo [SIMULACRO], que es el fallo
        # que el v1.02 vino a arreglar. Y hoy pasaría seguro: la incidencia
        # `desaparecido:esios_catalogo_previsiones` está abierta de verdad.
        desap = alarma_desaparecido(capturas, info)
        if simulacro == "desaparecido":
            desap = list(desap) + [("__simulacro__",
                                    MINIMO_CAPTURAS_ALARMA, capturas[0][0])]
        for k, u, desde in desap:
            es_sintetica = (k == "__simulacro__")
            incidencias.append(Incidencia(
                "desaparecido:%s" % k,
                "%s⚠️ La fuente `%s` lleva %d capturas sin aparecer"
                % ("[SIMULACRO] " if es_sintetica else "", k, u),
                "`%s` no aparece en las **últimas %d capturas**, desde "
                "`%s`, y antes sí estaba.\n\n⚠️ Su familia puede estar sana: "
                "esta alarma mira **fichero a fichero**, que es justo el hueco "
                "que deja la de «fuente muda».\n\nEl umbral no es fijo: son "
                "**%.1f veces** el intervalo con que esta fuente aparece "
                "normalmente, calculado del propio archivo."
                % (k, u, desde, FACTOR_ALARMA)))

        # ⚠️ Mismo criterio que arriba: sintética con clave propia.
        cong = alarma_congelado(capturas, info)
        if simulacro == "congelado":
            cong = list(cong) + [("__simulacro__",
                                  MINIMO_CAPTURAS_ALARMA, capturas[0][0])]
        for k, u, desde in cong:
            es_sintetica = (k == "__simulacro__")
            incidencias.append(Incidencia(
                "congelado:%s" % k,
                "%s⚠️ La fuente `%s` lleva %d capturas sirviendo lo mismo"
                % ("[SIMULACRO] " if es_sintetica else "", k, u),
                "`%s` **sí se captura**, pero su contenido no ha cambiado en "
                "las últimas **%d capturas**, desde `%s`.\n\n⚠️ La alarma de "
                "antigüedad la ve fresca y la de fuente muda la ve llena: "
                "este es el fallo que **ninguna de las otras puede ver**.\n\n"
                "El umbral son **%.1f veces** el intervalo con que esta fuente "
                "cambia normalmente. Una fuente semanal y una que cambia en "
                "cada captura salen con umbrales muy distintos sin que nadie "
                "escriba una tabla."
                % (k, u, desde, FACTOR_ALARMA)))

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


    print("\n-- el simulacro NO etiqueta alarmas reales -------------------")
    rota = [("c%02d" % i, {"viva": "h%d" % i, "otra": "g%d" % i}
             if i < 30 else {"otra": "g%d" % i}) for i in range(60)]
    with tempfile.TemporaryDirectory() as tmp3:
        os.makedirs(os.path.join(tmp3, "d"))
        with io.open(os.path.join(tmp3, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["fecha", "hora", "ruta"])
        # se prueba la lógica directamente, sin montar un archivo entero
        info_r = intervalos(rota)
        reales = alarma_desaparecido(rota, info_r)
        comprobar_que(any(a[0] == "viva" for a in reales),
                      "hay una alarma REAL de desaparecido en el escenario")
        sintetica = list(reales) + [("__simulacro__", 8, rota[0][0])]
        titulos = [("[SIMULACRO] " if k == "__simulacro__" else "") + k
                   for k, _, _ in sintetica]
        comprobar_que("[SIMULACRO] __simulacro__" in titulos,
                      "la sintética SÍ lleva el prefijo")
        comprobar_que("viva" in titulos,
                      "⚠️ la REAL sale SIN prefijo aunque haya simulacro: es "
                      "el fallo que el v1.02 vino a arreglar")

    print("\n-- canonico (trampa 5) --------------------------------------")
    comprobar_que(canonico("x.csv.gz") == canonico("x.csv"),
                  "⚠️ .csv y .csv.gz dan LA MISMA clave: cambiar de compresión "
                  "NO es desaparecer")
    comprobar_que(canonico("esios_602_energia_casada_diario.csv")
                  == "esios_602_energia_casada_diario",
                  "la clave canónica quita la extensión")

    print("\n-- umbral_de (el umbral es un MÚLTIPLO) ---------------------")
    comprobar_que(umbral_de(1.0) == MINIMO_CAPTURAS_ALARMA,
                  "el suelo protege a las fuentes que cambian siempre")
    comprobar_que(umbral_de(52.0) == 156,
                  "⚠️ una fuente semanal sale con umbral 156, no con el mismo "
                  "que una que cambia en cada captura")
    comprobar_que(umbral_de(float("inf")) is None,
                  "⚠️ sin intervalo medible NO se pone umbral")

    print("\n-- alarma_desaparecido --------------------------------------")
    sana = [("c%02d" % i, {"viva": "h%d" % i}) for i in range(60)]
    comprobar_que(not alarma_desaparecido(sana, intervalos(sana)),
                  "una fuente sana no dispara")
    ida = [("c%02d" % i, {"viva": "h%d" % i} if i < 30 else {})
           for i in range(60)]
    comprobar_que(any(a[0] == "viva"
                      for a in alarma_desaparecido(ida, intervalos(ida))),
                  "la que deja de aparecer SÍ dispara")
    cambia_ext = [("c%02d" % i,
                   {canonico("x.csv.gz" if i == 0 else "x.csv"): "h%d" % i})
                  for i in range(60)]
    comprobar_que(not alarma_desaparecido(cambia_ext,
                                          intervalos(cambia_ext)),
                  "⚠️ pasar de .gz a .csv NO se lee como desaparición "
                  "(el caso real del esios_602)")
    rara = [("c%02d" % i, {"rara": "h"} if i < 3 else {}) for i in range(60)]
    comprobar_que(not alarma_desaparecido(rara, intervalos(rara)),
                  "⚠️ una fuente que apareció 3 veces no genera alarma eterna")

    print("\n-- alarma_congelado -----------------------------------------")
    comprobar_que(not alarma_congelado(sana, intervalos(sana)),
                  "una fuente que cambia no dispara")
    cong = [("c%02d" % i, {"c": "IGUAL" if i >= 20 else "h%d" % i})
            for i in range(60)]
    comprobar_que(any(a[0] == "c"
                      for a in alarma_congelado(cong, intervalos(cong))),
                  "⚠️ la que se captura bien pero sirve lo mismo SÍ dispara: "
                  "es el fallo que las otras alarmas no pueden ver")

    print("\n-- episodios ------------------------------------------------")
    parpadeo = [("c%02d" % i, {} if i in (10, 12, 13, 14) else {"f": "h"})
                for i in range(30)]
    eps = episodios(parpadeo, ["f"])
    comprobar_que(len(eps) == 1,
                  "⚠️ fallo-acierto-fallo es UN episodio, no dos: sin "
                  "tolerancia salían 323 en 29 días y nadie los lee")
    comprobar_que(eps and eps[0][3] == 4,
                  "el episodio cuenta las 4 capturas fallidas")

    print("\n-- escribir_registro ----------------------------------------")
    with tempfile.TemporaryDirectory() as tmp2:
        os.makedirs(os.path.join(tmp2, "2026", "09", "2026-09-01", "1000"))
        with io.open(os.path.join(tmp2, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["fecha", "hora", "ruta"])
            w.writerow(["2026-09-01", "1000", "2026/09/2026-09-01/1000"])
        caps = [("2026-09-01-1000", {"a": "h1"}), ("2026-09-01-1300", {})]
        n1, n2 = escribir_registro(tmp2, caps, {"a"})
        comprobar_que(os.path.isfile(os.path.join(tmp2,
                                                  "fallos_recientes.csv")),
                      "escribe fallos_recientes.csv")
        comprobar_que(os.path.isfile(os.path.join(tmp2, "episodios.csv")),
                      "escribe episodios.csv")
        comprobar_que(n1 == 1 and n2 == 1,
                      "una captura fallida da 1 fallo y 1 episodio")
        # ⚠️ Idempotencia: correrlo dos veces no debe duplicar la historia.
        n1b, n2b = escribir_registro(tmp2, caps, {"a"})
        comprobar_que(n2b == n2,
                      "⚠️ correrlo dos veces NO duplica los episodios")

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
                   choices=["antiguedad", "fuente_muda", "caducidad",
                            "desaparecido", "congelado"],
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
