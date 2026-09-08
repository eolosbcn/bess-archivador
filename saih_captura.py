#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""CAPTURA DIARIA DEL SAIH — hidrología en tiempo real.

⚠️ ESTE FICHERO NO ES DE CASANDRA. Va en `eolosbcn/bess-archivador`. Esta copia
en `Casandra\` existe para que quede bajo git y para poder leerla sin abrir
GitHub. La que manda es la desplegada.

PARA QUÉ EXISTE, Y POR QUÉ ES URGENTE
=====================================
Los Sistemas Automáticos de Información Hidrológica de las Confederaciones
miden **el agua antes de que llegue al mercado**: nivel y volumen de cada
embalse, caudal de los ríos, precipitación y nieve. El 8-sep-2026 se midió que
la hidráulica gestionable deja de poner precio por encima del 85 % de llenado
(ver `conocimiento_mercado_*` §1), y que el instrumento que usábamos —la
reserva semanal de e·sios— llega con **10 a 16 días de retraso**.

⚠️⚠️ **Y ES URGENTE POR UNA RAZÓN QUE NO APLICA AL RESTO DEL PROYECTO: el SAIH
del Ebro sirve 365 días por API y lo anterior solo por correo.** Criterio de
Xevi, 8-sep-2026: *«a partir de ahora podemos recopilar las muestras cada día,
así que el aprendizaje crecerá»*. De todo lo que se descubrió ese día, **la
captura es lo único que se degrada si se espera**: el conocimiento aguanta, la
historia no se recupera.

ⓘ El MITECO, en cambio, **no es urgente**: su base de datos trae el histórico
completo desde 1988 y se puede descargar cuando sea.

⚠️ LA TRAMPA DEL CERTIFICADO, RESUELTA SIN BAJAR LA GUARDIA
===========================================================
`saihebro.com` sirve un certificado emitido por la **FNMT** y **no envía el
certificado intermedio**. Los navegadores lo resuelven solos por AIA; `requests`
no, y falla con `SSLError`.

⚠️ **La salida NO es `verify=False`**, que apaga la comprobación entera. Se
descarga el intermedio —cuya URL está dentro del propio certificado del
servidor— y se monta un paquete de CA con él. ✅ Comprobado el 8-sep-2026: con
`certifi` + `ACCOMP.crt` la petición devuelve HTTP 200 y la cadena se verifica
completa.

ⓘ Y no tiene nada que ver con el certificado de FIRMA de la FNMT: aquél
identifica a una persona ante la Administración, éste identifica al servidor.
Los datos son públicos y no piden identificarse.

QUÉ CAPTURA, Y POR QUÉ SOLO EL EBRO
====================================
Hoy solo el **Ebro**, porque es el único cuya API está mapeada (ver
`Aprendizajes_otras_fuentes_*` §5.bis). ⚠️ **No es un ensayo menor: el Ebro es
el 22,8 % de la hidráulica gestionable de España**, tercero de once y casi
empatado con el Miño-Sil. Las otras ocho confederaciones tienen sistemas
distintos y entran una a una.

CADENCIA: una vez al día. Los volúmenes de embalse son diarios; los aforos son
quinceminutales, pero para una previsión de precio de D+1 la foto diaria basta,
y multiplicar por 96 el volumen de datos sin usarlos sería pagar por nada.

⚠️ EL ÍNDICE ES DEL MISMO FORMATO QUE EL DEL ARCHIVADOR, y es deliberado: así
`vigilante.py` puede vigilar este archivo **sin una línea de código nuevo**,
apuntándolo con `--raiz`. Sin eso, las fuentes nuevas nacerían siendo un punto
ciego, que es justo lo que Xevi pidió evitar.

HISTORIAL
=========
v1.00  8-sep-2026. Primera versión. Solo el Ebro.
"""
import argparse
import csv
import datetime as dt
import gzip
import io
import json
import os
import ssl
import sys
import tempfile
import time

# ============================================================================
# CONSTANTES
# ============================================================================
CARPETA = "archivo_saih"

# El intermedio de la FNMT. ⚠️ La URL sale del PROPIO certificado del servidor
# (extensión AIA), no de una búsqueda: si la FNMT lo rota, el certificado nuevo
# apuntará al nuevo y esto lo seguirá.
URL_INTERMEDIO = "http://www.cert.fnmt.es/certs/ACCOMP.crt"

# ⚠️ Ritmo. La base de conocimiento documenta un cortafuegos anti-robots en
# e·sios (295 peticiones en 30 s = 403 durante 20 minutos). No se sabe si el
# SAIH tiene uno; con 2 peticiones al día el margen es absurdo, pero la
# costumbre importa para cuando entren nueve confederaciones.
ESPERA_S = 3.0

# Una entrada por confederación. Hoy solo el Ebro está mapeado.
# ⚠️ `peso` es el % de la hidráulica GESTIONABLE de España, ✅ medido sobre 151
# meses (ver `conocimiento_mercado_*` §1.8). Sirve para saber qué se pierde
# mientras las demás no estén.
CONFEDERACIONES = {
    "ebro": {
        "peso": 22.76,
        "base": "https://www.saihebro.com",
        "endpoints": {
            "volumenes_embalsados": "/api/principal/getVolumenesEmbalsados",
            "aforos_cuenca": ("/api/mapa/getDatosMapa"
                              "?slug=mapa-aforos-HG-toda-la-cuenca"),
        },
    },
    # PENDIENTES, por peso: duero 30,35 % · mino_sil 24,60 % · tajo 10,23 % ·
    # cantabrico 6,63 % · jucar 2,30 % · guadalquivir 1,24 % · c_cataluna
    # 0,89 % · guadiana 0,40 % · sur 0,37 % · segura 0,23 %.
    # ⚠️ Cada una tiene su propio sistema: no se pueden añadir copiando la
    # entrada del Ebro y cambiando el host.
}


# ============================================================================
# EL CERTIFICADO
# ============================================================================
def paquete_de_ca(destino=None):
    """certifi + el intermedio de la FNMT, en un fichero temporal.

    ⚠️ Devuelve la ruta del paquete, o None si no se pudo montar. Quien reciba
    None **no debe seguir con `verify=False`**: debe fallar y decirlo. Apagar
    la verificación convierte un problema de configuración en un agujero de
    seguridad permanente.
    """
    import requests
    try:
        import certifi
    except ImportError:
        print("  ⚠️ no hay certifi: no se puede montar el paquete de CA")
        return None
    try:
        r = requests.get(URL_INTERMEDIO, timeout=60)
        r.raise_for_status()
    except Exception as e:
        print("  ⚠️ no se pudo bajar el intermedio de la FNMT: %s"
              % type(e).__name__)
        return None
    bruto = r.content
    # ⚠️ Llega en DER (binario), no en PEM. Comprobado el 8-sep-2026: 1.754
    # bytes empezando por 0x30, que es la firma de una secuencia DER.
    if bruto[:1] == b"0":
        pem = ssl.DER_cert_to_PEM_cert(bruto)
    else:
        pem = bruto.decode("ascii", errors="replace")
    if "BEGIN CERTIFICATE" not in pem:
        print("  ⚠️ lo que ha llegado no parece un certificado")
        return None
    destino = destino or os.path.join(tempfile.mkdtemp(), "ca_saih.pem")
    with io.open(destino, "w", encoding="ascii") as f:
        with io.open(certifi.where(), encoding="ascii") as g:
            f.write(g.read())
        f.write("\n")
        f.write(pem)
    return destino


# ============================================================================
# LA CAPTURA
# ============================================================================
def capturar(confederacion, ca, carpeta):
    """Baja los endpoints de una confederación. Devuelve la ficha de cada uno.

    ⚠️ NADA de `continue` mudo: cada endpoint deja su estado en la ficha, y el
    manifiesto los lleva todos. Un fallo que no aparece en el manifiesto es un
    fallo que nadie verá.
    """
    import requests
    cfg = CONFEDERACIONES[confederacion]
    fichas = {}
    for nombre, ruta in sorted(cfg["endpoints"].items()):
        clave = "saih_%s_%s" % (confederacion, nombre)
        url = cfg["base"] + ruta
        t0 = time.time()
        try:
            # ⚠️ 15 s, no 120. Un servidor que contesta en 0,5 s no
            # necesita dos minutos, y con 120 una pasada fallida tardaba
            # **279 s** en decir que había fallado. 15 s sigue siendo treinta
            # veces el tiempo de respuesta medido el 8-sep-2026.
            r = requests.get(url, timeout=15, verify=ca,
                             headers={"Accept": "application/json"})
        except Exception as e:
            fichas[clave] = {"estado": "FALLO", "detalle": type(e).__name__}
            print("    %-40s ❌ %s" % (clave, type(e).__name__))
            time.sleep(ESPERA_S)
            continue
        dur = time.time() - t0
        if r.status_code != 200:
            fichas[clave] = {"estado": "FALLO",
                             "detalle": "HTTP %d" % r.status_code}
            print("    %-40s ❌ HTTP %d" % (clave, r.status_code))
            time.sleep(ESPERA_S)
            continue
        cuerpo = r.content
        if not cuerpo:
            fichas[clave] = {"estado": "VACIO", "detalle": "0 bytes"}
            print("    %-40s ⚠️ vacío" % clave)
            time.sleep(ESPERA_S)
            continue
        # ⚠️ Se comprueba que es JSON antes de guardarlo. Un HTML de error con
        # código 200 —una página de mantenimiento, un desafío de cortafuegos—
        # se guardaría tan campante y parecería un dato bueno.
        try:
            datos = json.loads(cuerpo.decode("utf-8"))
        except Exception:
            fichas[clave] = {"estado": "FALLO",
                             "detalle": "la respuesta no es JSON"}
            print("    %-40s ❌ no es JSON (%d bytes)" % (clave, len(cuerpo)))
            time.sleep(ESPERA_S)
            continue
        ruta_f = os.path.join(carpeta, clave + ".json.gz")
        with gzip.open(ruta_f, "wb") as f:
            f.write(cuerpo)
        fichas[clave] = {
            "estado": "OK",
            "bytes": len(cuerpo),
            "comprimido": os.path.getsize(ruta_f),
            "elementos": len(datos) if isinstance(datos, (list, dict)) else None,
            "segundos": round(dur, 2),
        }
        print("    %-40s ✅ %6.1f KB → %5.1f KB comprimido · %.1f s"
              % (clave, len(cuerpo) / 1024,
                 os.path.getsize(ruta_f) / 1024, dur))
        time.sleep(ESPERA_S)
    return fichas


def anotar_indice(raiz, ruta_rel, fichas, instante):
    """Índice con el MISMO formato que el del archivador.

    ⚠️ Y eso no es estética: `vigilante.py` lee `indice.csv` y las carpetas de
    captura, así que con este formato puede vigilar este archivo **sin una
    línea de código nueva**, apuntándolo con `--raiz`. Sin esto, el SAIH
    nacería siendo un punto ciego.
    """
    idx = os.path.join(raiz, "indice.csv")
    nuevo = not os.path.isfile(idx)
    ok = sum(1 for v in fichas.values() if v["estado"] == "OK")
    vacio = sum(1 for v in fichas.values() if v["estado"] == "VACIO")
    fallo = sum(1 for v in fichas.values() if v["estado"] == "FALLO")
    kb = sum(v.get("comprimido", 0) for v in fichas.values()) / 1024.0
    with io.open(idx, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "hora", "ejecucion_utc", "ok", "vacio",
                        "fallo", "kb_total", "ruta"])
        w.writerow([instante.strftime("%Y-%m-%d"), instante.strftime("%H%M"),
                    instante.isoformat(), ok, vacio, fallo,
                    round(kb, 1), ruta_rel])
    return ok, vacio, fallo


# ============================================================================
# PRUEBAS
# ============================================================================
def autotest():
    fallos, hechas = [], [0]

    def comprobar(cond, texto):
        hechas[0] += 1
        print("   %s  %s" % ("OK  " if cond else "FALLA", texto))
        if not cond:
            fallos.append(texto)

    comprobar("ebro" in CONFEDERACIONES, "el Ebro está configurado")
    comprobar(CONFEDERACIONES["ebro"]["base"].startswith("https://"),
              "⚠️ la base es HTTPS, no HTTP")
    comprobar(all("peso" in c for c in CONFEDERACIONES.values()),
              "cada confederación declara su peso: dice qué se pierde "
              "mientras falten las demás")

    # el índice, con el formato del archivador
    with tempfile.TemporaryDirectory() as tmp:
        ahora = dt.datetime(2026, 9, 8, 21, 0, tzinfo=dt.timezone.utc)
        f = {"saih_ebro_a": {"estado": "OK", "comprimido": 2048},
             "saih_ebro_b": {"estado": "FALLO", "detalle": "HTTP 500"}}
        ok, vacio, fallo = anotar_indice(tmp, "2026/09/2026-09-08", f, ahora)
        comprobar((ok, vacio, fallo) == (1, 0, 1), "cuenta ok/vacío/fallo")
        with io.open(os.path.join(tmp, "indice.csv"), encoding="utf-8") as g:
            filas = list(csv.DictReader(g))
        comprobar(len(filas) == 1, "escribe una fila")
        comprobar(set(["fecha", "hora", "ruta", "ok", "vacio", "fallo"])
                  <= set(filas[0]),
                  "⚠️ el índice tiene las columnas del archivador: el "
                  "vigilante puede leerlo sin cambios")
        # y que ACUMULA, no reescribe
        anotar_indice(tmp, "2026/09/2026-09-09", f, ahora)
        with io.open(os.path.join(tmp, "indice.csv"), encoding="utf-8") as g:
            filas = list(csv.DictReader(g))
        comprobar(len(filas) == 2, "⚠️ acumula, no reescribe: la segunda "
                                   "captura no borra la primera")

    # --- la prueba que de verdad importa: ¿lo lee el vigilante? -----------
    # ⚠️ Se COMPRUEBA, no se afirma. La primera versión de esta verificación
    # imprimía «✅ el vigilante lee el archivo» justo debajo de «capturas
    # leídas: 0», porque el mensaje estaba escrito a mano.
    with tempfile.TemporaryDirectory() as tmp:
        raiz = os.path.join(tmp, "archivo_saih")
        dia = os.path.join(raiz, "2026", "09", "2026-09-08")
        os.makedirs(dia)
        with gzip.open(os.path.join(dia, "saih_ebro_x.json.gz"), "wb") as f:
            f.write(b'{"a":1}')
        ahora = dt.datetime(2026, 9, 8, 21, 0, tzinfo=dt.timezone.utc)
        anotar_indice(raiz, "archivo_saih/2026/09/2026-09-08",
                      {"saih_ebro_x": {"estado": "OK", "comprimido": 30}},
                      ahora)
        # se replica EXACTAMENTE la resolución de rutas del vigilante
        idx = os.path.join(raiz, "indice.csv")
        base = os.path.dirname(os.path.dirname(idx))
        with io.open(idx, encoding="utf-8", newline="") as g:
            fila = list(csv.DictReader(g))[0]
        carpeta = os.path.join(base, fila["ruta"])
        comprobar(os.path.isdir(carpeta),
                  "⚠️ el vigilante ENCUENTRA la carpeta de captura: sin el "
                  "prefijo de la raíz en `ruta` leía 0 capturas")
        comprobar(any(n.endswith(".json.gz") for n in os.listdir(carpeta)),
                  "y dentro están los ficheros capturados")

    print("")
    print("  %d de %d comprobaciones pasan" % (hechas[0] - len(fallos),
                                               hechas[0]))
    return not fallos


# ============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raiz", default=CARPETA)
    p.add_argument("--confederacion", default="ebro",
                   choices=sorted(CONFEDERACIONES))
    p.add_argument("--autotest", action="store_true")
    a = p.parse_args()

    if a.autotest:
        return 0 if autotest() else 1

    ahora = dt.datetime.now(dt.timezone.utc)
    print("  SAIH · %s · %s" % (a.confederacion, ahora.isoformat()))

    ca = paquete_de_ca()
    if ca is None:
        # ⚠️ Se FALLA. No se sigue con `verify=False`: apagar la verificación
        # convertiría un problema de configuración en un agujero permanente, y
        # además nadie volvería a mirarlo porque «funciona».
        print("  ❌ sin paquete de CA no se captura. NO se desactiva la "
              "verificación: eso no es una solución, es esconder el problema.")
        return 1
    print("  ✅ paquete de CA montado (certifi + intermedio de la FNMT)")

    # ⚠️ La ruta del índice INCLUYE el nombre de la carpeta raíz, igual que
    # en el archivador (`archivo/2026/09/...`). No es cosmético: el vigilante
    # resuelve `base = dirname(dirname(indice.csv))` y le suma esta ruta, así
    # que sin el prefijo lee CERO capturas — comprobado el 8-sep-2026.
    nombre_raiz = os.path.basename(os.path.normpath(a.raiz))
    rel = "/".join([nombre_raiz, ahora.strftime("%Y"), ahora.strftime("%m"),
                    ahora.strftime("%Y-%m-%d")])
    carpeta = os.path.join(a.raiz, ahora.strftime("%Y"),
                           ahora.strftime("%m"), ahora.strftime("%Y-%m-%d"))
    os.makedirs(carpeta, exist_ok=True)

    fichas = capturar(a.confederacion, ca, carpeta)

    with io.open(os.path.join(carpeta, "manifiesto.json"), "w",
                 encoding="utf-8") as f:
        json.dump({"ejecucion_utc": ahora.isoformat(),
                   "confederacion": a.confederacion,
                   "version": "v1.00",
                   "fuentes": fichas}, f, ensure_ascii=False, indent=1)

    ok, vacio, fallo = anotar_indice(a.raiz, rel, fichas, ahora)
    print("")
    print("  %d OK · %d vacías · %d fallos" % (ok, vacio, fallo))
    # ⚠️ Devuelve 0 aunque haya fallos: quien avisa es el vigilante leyendo el
    # índice, no un workflow en rojo. Un workflow que se pone rojo cada vez que
    # una fuente falla llena de correos y acaba silenciado.
    return 0


if __name__ == "__main__":
    sys.exit(main())
