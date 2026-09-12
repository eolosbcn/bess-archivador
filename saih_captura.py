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

UN ARTEFACTO CONOCIDO DE NUESTRO DESPLIEGUE (M29, auditoría del 9-sep-2026)
---------------------------------------------------------------------------
⚠️ El registro permanente de fallos del SAIH —`episodios.csv` y
`fallos_recientes.csv` del archivo— es **100 % artefacto nuestro**: sus
entradas no son caídas del servidor del SAIH, sino de nuestro propio
despliegue (las pasadas de antes de que existiera el clon, los empujes
fallidos, las pruebas). Todo se reconstruye del archivo en cada pasada salvo
`episodios.csv`, que se funde y por eso acumula.

Queda escrito aquí, y no se «limpia», por el mismo motivo por el que no se
reescribe la historia: esas líneas son ciertas —ocurrieron— y borrarlas haría
que el archivo dejara de coincidir con lo que pasó. Lo que hay que saber es
que **no miden la fiabilidad de la fuente**, sino la de nuestro montaje.

CADENCIA: una vez al día. Los volúmenes de embalse son diarios; los aforos son
quinceminutales, pero para una previsión de precio de D+1 la foto diaria basta,
y multiplicar por 96 el volumen de datos sin usarlos sería pagar por nada.

⚠️ EL ÍNDICE ES DEL MISMO FORMATO QUE EL DEL ARCHIVADOR, y es deliberado: así
`vigilante.py` puede vigilar este archivo **sin una línea de código nuevo**,
apuntándolo con `--raiz`. Sin eso, las fuentes nuevas nacerían siendo un punto
ciego, que es justo lo que Xevi pidió evitar.

HISTORIAL
=========
v1.03  12-sep-2026. **Entra el TURBINADO POR CENTRAL del Ebro y la hidrología
    de las otras dos cuencas** (decisión **D39** de Xevi, bloque B4), el
    manifiesto pasa a FUNDIRSE en vez de sobrescribirse (**M30**) y se
    documenta el artefacto de M29.

    ⚠️ LOS AFOROS DEL EBRO YA SE CAPTURABAN desde la v1.00 (`aforos_cuenca`).
    D39 pedía «QCENT y aforos»: de los dos, lo único nuevo aquí es `QCENT`.

    `QCENT` NO ES UN ENDPOINT, ES UN PROCEDIMIENTO DE TRES LLAMADAS, y por eso
    no cabe en `CONFEDERACIONES`: hay que preguntar qué estaciones lo tienen,
    pedir sus señales y descargar un ZIP por rango de fechas. Se captura con
    `capturar_qcent()`, que deja su ficha en el manifiesto como una fuente más.

    ⚠️ Y SE PIDE UN RANGO DE 15 DÍAS, NO EL DÍA DE HOY. Es la única fuente de
    este programa que RECUPERA HUECOS: si la máquina pasa días apagada, la
    pasada siguiente recoge lo que faltaba. Cuesta ~7 KB. Las demás fuentes
    solo sirven la foto de hoy y lo no capturado se pierde para siempre.

    ✅ Medido el 12-sep-2026 sobre 1 pasada de 7 días: 6 señales en el
    catálogo, ZIP de 3.723 bytes, un CSV por señal. Con tres avisos que salen
    del propio dato y que quien lo lea debe conocer:
      · el día EN CURSO viene incompleto (media sí, mínimo y máximo vacíos);
      · **una de las 6 está muerta** (Cortijo, `CH06T65QTOTA`: 0 filas en 7
        días; su serie acabó en 2022), así que vivas son **5**;
      · ⚠️ **una ni siquiera es QCENT**: `CH49Y68QCAUT` es `QCAUT`, da 0
        constante y **sirve las fechas DESORDENADAS** (10/09, 07/09, 11/09).
        El código de tipo NO va dentro del tag, así que nadie puede deducir de
        un tag lo que mide, ni dar por hecho el orden de las filas.

    LAS OTRAS DOS CUENCAS: ✅ se comprobó —no se supuso— qué ofrecen, y el
    resultado corrigió lo que este fichero daba por sabido.
      · **Duero**: `datos-tiempo-real/risr` trae **toda la cuenca en UNA
        petición**: 176 KB con 290 estaciones dentro del JavaScript —no en el
        HTML—, en `datosEA` (aforos, con caudal en m3/s), `datosEM` (embalses)
        y `datosPL` (pluviómetros, con precipitación observada en l/m2).
        ⚠️ La página tiene 9 tablas y **solo 32 celdas**: contar `<tr>` aquí no
        mide nada, y por eso el `spec` admite `contar`.
      · **Miño-Sil**: `/datos/resumen`, 1 tabla de 76 filas con umbrales de
        aviso. ⚠️ Lo que trae es **NIVEL en metros**, no caudal: se captura
        porque es hidrología observada, pero no es lo mismo y no se le llama
        aforo.

    ⚠️ LAS DOS SE ARCHIVAN CRUDAS Y NO SE PARSEAN (decisión de Xevi): es la
    filosofía del archivador —lo que no se captura hoy no se recupera, y lo
    que se parsea mal se vuelve a parsear— y hace que el cambio sea ADITIVO
    PURO: ninguna fuente existente cambia de significado.

    **M30 · EL MANIFIESTO SE FUNDE, NO SE SOBRESCRIBE.** Hasta la v1.02, una
    pasada fallida degradaba el veredicto del día aunque el dato estuviera
    guardado: si la de las 09:30 traía todo y la de las 14:00 fallaba, el
    manifiesto del día decía FALLO **sobre un fichero que estaba en disco**.
    El disco ya se comportaba como «lo mejor del día» —una pasada que falla
    hace `continue` ANTES de escribir, así que no pisa el `.gz` bueno—: era el
    manifiesto el que mentía. Ahora una fuente solo consta como FALLO si
    NINGUNA pasada del día la trajo, cada ficha dice de qué pasada viene, y el
    manifiesto lleva el rastro de todas en `pasadas`. ⚠️ Una pasada que falla
    sobre una fuente ya buena NO se esconde: queda en `ultima_pasada`.

    ⚠️⚠️ **Y EL DÍA QUE SE ESTRENA UNA VERSIÓN, EL MANIFIESTO ANTERIOR NO
    TIENE `pasadas` — Y ESO NO ES UN DÍA SIN PASADAS.** Lo descubrió la
    ejecución REAL del 12-sep-2026 a las 20:00, no el autotest ni la prueba en
    vivo: el manifiesto de ese día quedó diciendo **«1 pasada» cuando hubo
    TRES**, porque las de 09:30 y 14:00 las había escrito la v1.02. Sin
    marcarlo, ese día parecería de una sola pasada para siempre, y lo mismo le
    pasaría a cualquier día en que se estrene una versión futura.

    No se inventa un número: se dice que **hubo pasadas y no se sabe cuántas**,
    con lo único que sí se sabe —cuántas fuentes había ya—, en
    `pasadas_previas_sin_registrar` y en la línea de resumen.

    ℹ︎ **Cómo se coló una versión sin desplegar, que es la lección de fondo.**
    La casa tiene escrito que «lo que la rutina carga POR PATRÓN está en
    producción al escribirse». Este programa es un caso **más fuerte**: el
    `.bat` lo carga **por RUTA FIJA** desde el clon de despliegue, que es
    también el de trabajo, así que **basta guardar el fichero** — ni hace falta
    subir la versión ni ser el número más alto. Esta v1.03 llevaba capturando
    en producción desde las 20:00 del 12-sep, horas antes de que nadie la
    desplegara, y **funcionó**: 7 fuentes, 0 fallos, y el vigilante v1.06 leyó
    su manifiesto nuevo sin una queja. Salió bien; pero salió bien por suerte,
    y quien edite este fichero tiene que saber que está tocando producción.

    **M29 · documentado**: ver «UN ARTEFACTO CONOCIDO DE NUESTRO DESPLIEGUE».

    **Y NACE `VERSION`**, con la misma prueba que el archivador estrenó en su
    v3.14: la versión vivía escrita a mano dentro del manifiesto (`"version":
    "v1.02"`) y también en este historial, o sea en dos sitios. Hoy, 12-sep, el
    archivador estuvo TRES DÍAS con esas dos cosas descuadradas —`VERSION` en
    v3.16 y la cabecera en v3.14— y su autotest en rojo sin que nadie lo
    ejecutara. Aquí el dato vive en un solo sitio y `--autotest` lo comprueba.


v1.02  9-sep-2026. **Entran el DUERO y el MIÑO-SIL**, y con ellos la cobertura
       pasa del **22,76 % al 77,71 %** del volumen embalsado peninsular. El
       Ebro solo, que era todo lo que había, pesa menos que cualquiera de las
       dos por separado.

       ⚠️ Y no se pudieron añadir copiando la entrada del Ebro, que es lo que
       la v1.00 ya advertía: **ninguna de las dos tiene API**. Sirven la tabla
       montada en HTML, así que:
       · cada endpoint declara su `formato`, y el HTML se archiva crudo —lo que
         no se captura hoy no se recupera; lo que se parsea mal se reparsea—;
       · y con `marca`, porque la validación de JSON dejaba de proteger: **una
         página de error TAMBIÉN es HTML válido**. La marca es una cadena que
         tiene que estar. Identidad, no firma (trampa 10).
       · el Miño-Sil además exige la cookie `lang=es`: sin ella el servidor
         entra en un bucle de 50 redirecciones que parece una caída y no lo es.

       ⚠️ Y el defecto de `--confederacion` pasa de `ebro` a TODAS. La tarea
       programada llama sin ese argumento, así que dejarlo en `ebro` habría
       capturado el 22 % de España creyendo que se capturaba todo.

       ❌ El TAJO (10,23 %) queda fuera porque **su servidor está roto**: su
       `/get-embalses` devuelve `Division by zero` con traza de PHP. ✅
       Comprobado por dos vías, con `curl` y con un navegador real.

v1.01  9-sep-2026. **Escribe `ultimo.json` en la raíz**, con el mismo contenido
       que el `manifiesto.json` del día. Es lo que el vigilante lee para saber
       qué fuentes trajo la última captura, y sin él este archivo no se podía
       vigilar. ⚠️ El 8-sep se comprobó que el `indice.csv` tenía el formato
       bueno y se dio por hecho que con eso bastaba: no bastaba. El vigilante
       usa DOS ficheros, y del segundo nadie se acordó — hasta el punto de que
       apuntarle a este archivo lo habría hecho reventar entero, sin evaluar
       ninguna alarma. Es la trampa 8 de la casa: la comprobación cruzada que
       está escrita y no se hace. La otra mitad del arreglo va en
       `vigilante.py` v1.04, que ya no revienta si falta.

v1.00  8-sep-2026. Primera versión. Solo el Ebro.
"""
import argparse
import csv
import datetime as dt
import gzip
import zipfile
import io
import json
import os
import re
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
# ⚠️ CADA ENDPOINT DECLARA SU FORMATO Y SU MARCA, y eso no es burocracia.
#
# La v1.00 solo sabía de JSON, y validaba el contenido intentando parsearlo:
# así un HTML de error servido con código 200 —una página de mantenimiento, un
# desafío de cortafuegos— no podía colarse como dato bueno. Al entrar el Duero
# y el Miño-Sil, que **no tienen API y sirven la tabla en HTML**, esa red
# desaparecería: cualquier página de error es HTML válido.
#
# La sustituye la `marca`: una cadena que TIENE que estar en la respuesta. No
# es una firma con umbrales, es una identidad —está o no está—, que es lo que
# la trampa 10 de la casa manda preferir. Si el Duero deja de decir «Volumen
# embalsado», no queremos guardar lo que sea que haya devuelto.
# ⚠️ LA VERSIÓN VIVE AQUÍ Y EN NINGÚN OTRO SITIO, y `--autotest` comprueba que
# concuerde con el primer bloque del historial de la cabecera. Hasta la v1.02
# estaba escrita a mano dentro del manifiesto, o sea en dos sitios que podían
# descuadrarse — y el mismo 12-sep-2026 se comprobó que al archivador le había
# pasado exactamente eso durante tres días.
VERSION = "v1.03"

# ⚠️ `QCENT` va aparte de este diccionario A PROPÓSITO: no es una URL, son tres
# llamadas encadenadas con parámetros de fecha (ver `capturar_qcent`). Meterlo
# aquí obligaría a que `capturar()` supiera de casos especiales, y entonces el
# esquema dejaría de describir lo que hace.
DIAS_QCENT = 15          # ver el historial: es la única fuente que recupera huecos

CONFEDERACIONES = {
    "ebro": {
        "peso": 22.76,
        "base": "https://www.saihebro.com",
        "endpoints": {
            "volumenes_embalsados": {
                "ruta": "/api/principal/getVolumenesEmbalsados",
                "formato": "json"},
            "aforos_cuenca": {
                "ruta": ("/api/mapa/getDatosMapa"
                         "?slug=mapa-aforos-HG-toda-la-cuenca"),
                "formato": "json"},
        },
    },
    # ⚠️ El Duero sirve la tabla ya montada en HTML, sin API. Se archiva cruda
    # y se parsea después, que es la filosofía del archivador: lo que no se
    # captura hoy no se recupera, y lo que se parsea mal se vuelve a parsear.
    # ✅ La página se auto-fecha —«9 de septiembre de 2026»— así que nunca hay
    # que adivinar a qué día corresponde.
    "duero": {
        "peso": 30.35,
        "base": "https://www.saihduero.es",
        "endpoints": {
            "situacion_embalses": {
                "ruta": "/situacion-embalses",
                "formato": "html",
                "marca": "Volumen embalsado"},
            # ✅ D39, 12-sep-2026: TODA la cuenca en una petición. El dato no
            # está en el HTML sino dentro del JavaScript —`datosEA` aforos con
            # caudal en m3/s, `datosEM` embalses, `datosPL` pluviómetros con
            # precipitación observada—, 290 estaciones medidas ese día.
            #
            # ⚠️ La marca es la DEFINICIÓN de la variable, no la palabra
            # «caudal»: «Caudal:» aparece en las etiquetas del panel lateral
            # aunque no venga ni un dato, así que validaría una página vacía.
            # Y `contar` existe porque aquí `<tr>` no mide nada: la página
            # tiene 9 tablas y 32 celdas.
            "tiempo_real_risr": {
                "ruta": "/datos-tiempo-real/risr",
                "formato": "html",
                "marca": "var datosEA = new Array(",
                "contar": "station: '"},
        },
    },
    # ⚠️ El Miño-Sil corre «WEBSAIH ws 2022», un producto de terceros, y da
    # volumen por embalse en TIEMPO REAL —lecturas cada 15 min— en vez del D-1
    # del Ebro. ✅ Medido el 9-sep-2026: 34 filas con capacidad, volumen en hm³
    # y en %, caudal de salida y fecha por embalse.
    #
    # ⚠️ NECESITA LA COOKIE `lang=es`. Sin ella el servidor entra en un bucle
    # de redirecciones —medido: 50 saltos y curl se rinde— que parece una caída
    # y no lo es. Se descubrió comparando con un navegador, que sí la pone.
    "mino_sil": {
        "peso": 24.60,
        "base": "https://saih.chminosil.es",
        "cookies": {"lang": "es"},
        "endpoints": {
            "situacion_embalses": {
                "ruta": "/index.php?url=/datos/situacionEmbalses",
                "formato": "html",
                "marca": "Capacidad Total"},
            # ✅ D39, 12-sep-2026: 1 tabla de 76 filas, 294 celdas con número.
            # ⚠️ NO son aforos: es NIVEL en metros con umbrales de aviso
            # (rojo/naranja/amarillo). Se captura por ser hidrología observada,
            # y el nombre lo dice para que nadie lo confunda con caudal.
            "resumen_niveles": {
                "ruta": "/index.php?url=/datos/resumen",
                "formato": "html",
                "marca": "Valor actual (m)"},
        },
    },
    # ❌ TAJO (10,23 %): SU SERVIDOR ESTÁ ROTO, y no es cosa nuestra. Su portal
    # es una aplicación JS que pide `/get-embalses`, y ese endpoint devuelve
    # `Exception (0) Division by zero` con una traza de PHP. ✅ Comprobado el
    # 9-sep-2026 por dos vías: con `curl` y dentro de un navegador real, con
    # sesión y cabeceras propias. No se añade porque no hay nada que capturar;
    # se reintenta cuando lo arreglen.
    #
    # PENDIENTES, por peso: tajo 10,23 % · cantabrico 6,63 % · jucar 2,30 % ·
    # guadalquivir 1,24 % · c_cataluna 0,89 % · guadiana 0,40 % · sur 0,37 % ·
    # segura 0,23 %. Suman 22,29 %.
    # ⚠️ Cada una tiene su propio sistema: ✅ comprobado el 9-sep-2026 sobre 8
    # dominios que la ruta del Miño-Sil NO la comparte ninguna otra, así que no
    # se pueden añadir copiando una entrada y cambiando el host.
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
    for nombre, spec in sorted(cfg["endpoints"].items()):
        clave = "saih_%s_%s" % (confederacion, nombre)
        url = cfg["base"] + spec["ruta"]
        formato = spec["formato"]
        t0 = time.time()
        try:
            # ⚠️ 15 s, no 120. Un servidor que contesta en 0,5 s no
            # necesita dos minutos, y con 120 una pasada fallida tardaba
            # **279 s** en decir que había fallado. 15 s sigue siendo treinta
            # veces el tiempo de respuesta medido el 8-sep-2026.
            r = requests.get(
                url, timeout=15, verify=ca,
                cookies=cfg.get("cookies"),
                headers={"Accept": ("application/json" if formato == "json"
                                    else "text/html"),
                         # ⚠️ Un User-Agent explícito y honesto: dice qué somos.
                         # Sin ninguno, `requests` manda `python-requests/x.y`,
                         # que varios portales públicos filtran.
                         "User-Agent": "Revenergetica-Casandra/1.0 "
                                       "(archivador hidrologico)"})
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
        # ⚠️ SE VALIDA EL CONTENIDO ANTES DE GUARDARLO, y de la forma que
        # corresponda a cada formato. Un error servido con código 200 —una
        # página de mantenimiento, un desafío de cortafuegos— se guardaría tan
        # campante y parecería un dato bueno.
        #
        # Para JSON, la validación es parsearlo. Para HTML no sirve —una página
        # de error TAMBIÉN es HTML válido—, así que se exige la `marca`: una
        # cadena que tiene que estar. Está o no está, sin umbrales que calibrar.
        elementos = None
        if formato == "json":
            try:
                datos = json.loads(cuerpo.decode("utf-8"))
            except Exception:
                fichas[clave] = {"estado": "FALLO",
                                 "detalle": "la respuesta no es JSON"}
                print("    %-40s ❌ no es JSON (%d bytes)"
                      % (clave, len(cuerpo)))
                time.sleep(ESPERA_S)
                continue
            elementos = len(datos) if isinstance(datos, (list, dict)) else None
        else:
            marca = spec["marca"]
            if marca.encode("utf-8") not in cuerpo:
                fichas[clave] = {"estado": "FALLO",
                                 "detalle": "falta la marca %r" % marca}
                print("    %-40s ❌ falta la marca %r (%d bytes)"
                      % (clave, marca, len(cuerpo)))
                time.sleep(ESPERA_S)
                continue
            # Cuenta de elementos: no valida nada por sí sola, pero deja en el
            # manifiesto una cifra que cambia si la tabla se vacía.
            #
            # ⚠️ `<tr>` solo sirve cuando el dato viaja en una tabla. En el
            # visor del Duero el dato está dentro del JavaScript y la página
            # tiene 9 tablas con 32 celdas: contar `<tr>` daría siempre lo
            # mismo, hubiera 290 estaciones o ninguna. Por eso un `spec` puede
            # declarar qué contar.
            aguja = spec.get("contar")
            if aguja:
                elementos = cuerpo.count(aguja.encode("utf-8"))
            else:
                elementos = cuerpo.count(b"<tr")

        ruta_f = os.path.join(carpeta, "%s.%s.gz" % (clave, formato))
        with gzip.open(ruta_f, "wb") as f:
            f.write(cuerpo)
        fichas[clave] = {
            "estado": "OK",
            "bytes": len(cuerpo),
            "comprimido": os.path.getsize(ruta_f),
            "elementos": elementos,
            "segundos": round(dur, 2),
        }
        print("    %-40s ✅ %6.1f KB → %5.1f KB comprimido · %.1f s"
              % (clave, len(cuerpo) / 1024,
                 os.path.getsize(ruta_f) / 1024, dur))
        time.sleep(ESPERA_S)
    return fichas


def capturar_qcent(ca, carpeta):
    """El TURBINADO POR CENTRAL del Ebro. Devuelve su ficha, como `capturar`.

    ⚠️ Son TRES llamadas encadenadas y no un endpoint, por eso vive fuera de
    `CONFEDERACIONES`: hay que preguntar qué estaciones tienen `QCENT`, pedir
    sus señales, y descargar un ZIP con un CSV por señal.

    ⚠️ EL CATÁLOGO SE PREGUNTA CADA VEZ, no se cablea la lista de señales. Si
    mañana el Ebro da de alta una central, entra sola; si da una de baja, se
    ve en `elementos`. Una lista fija habría capturado para siempre las seis
    de hoy sin que nadie se enterase de un alta.

    ⚠️ Y SE PIDE UN RANGO, NO UN DÍA: es la única fuente de este programa que
    recupera huecos. Ver `DIAS_QCENT` y el historial de la cabecera.
    """
    import requests
    clave = "saih_ebro_qcent"
    base = CONFEDERACIONES["ebro"]["base"]
    hoy = dt.date.today()
    desde = (hoy - dt.timedelta(days=DIAS_QCENT)).strftime("%d/%m/%Y")
    hasta = hoy.strftime("%d/%m/%Y")
    cab = {"User-Agent": "Revenergetica-Casandra/1.0 (archivador hidrologico)"}
    t0 = time.time()

    def fallo(paso, detalle):
        """⚠️ El paso que falló va en la ficha: «FALLO» a secas no dice si se
        cayó el catálogo o la descarga, y son averías distintas."""
        print("    %-40s ❌ %s: %s" % (clave, paso, detalle))
        return {clave: {"estado": "FALLO", "paso": paso, "detalle": detalle}}

    try:
        r = requests.get(base + "/api/datos-historicos/getEstaciones"
                                "?tipoConsolidado=diario&tiposSenal=QCENT",
                         timeout=15, verify=ca, headers=cab)
        if r.status_code != 200:
            return fallo("getEstaciones", "HTTP %d" % r.status_code)
        estaciones = json.loads(r.content.decode("utf-8"))
    except Exception as e:
        return fallo("getEstaciones", type(e).__name__)
    time.sleep(ESPERA_S)

    ids = [str(e.get("id", e.get("codigo", ""))) for e in estaciones]
    ids = [i for i in ids if i]
    if not ids:
        # ⚠️ VACIO y no FALLO: el servidor contestó y no había. Confundir «hoy
        # no hay» con «se rompió» es la trampa 7 de la casa.
        print("    %-40s ⚠️ el catálogo no da ninguna estación" % clave)
        return {clave: {"estado": "VACIO", "detalle": "0 estaciones con QCENT"}}

    try:
        r = requests.get(base + "/api/datos-historicos/getSenales"
                                "?tipoConsolidado=diario&tiposSenal=QCENT"
                                "&estaciones=" + ",".join(ids),
                         timeout=15, verify=ca, headers=cab)
        if r.status_code != 200:
            return fallo("getSenales", "HTTP %d" % r.status_code)
        senales = json.loads(r.content.decode("utf-8"))
    except Exception as e:
        return fallo("getSenales", type(e).__name__)
    time.sleep(ESPERA_S)

    sids = [str(s.get("id")) for s in senales if s.get("id") is not None]
    if not sids:
        print("    %-40s ⚠️ estaciones sin señal" % clave)
        return {clave: {"estado": "VACIO", "detalle": "0 señales",
                        "estaciones": len(ids)}}

    try:
        r = requests.get(base + "/api/datos-historicos/obtenerDatosHistoricos"
                         "?tipoConsolidado=diario&senalesSeleccionadas="
                         + ",".join(sids) + "&fechaIni=" + desde
                         + "&fechaFin=" + hasta + "&formato=csv",
                         timeout=120, verify=ca, headers=cab)
        if r.status_code != 200:
            return fallo("obtenerDatosHistoricos", "HTTP %d" % r.status_code)
    except Exception as e:
        return fallo("obtenerDatosHistoricos", type(e).__name__)
    dur = time.time() - t0

    # ⚠️ SE GUARDA SIEMPRE, incluso si no es un ZIP válido, y por el mismo
    # motivo que el archivador guarda el HTML crudo de SENDECO2 cuando no lo
    # entiende: el dato del día no se puede volver a pedir, y un cuerpo que
    # hoy no sabemos abrir se puede reparsear mañana. Lo que cambia es el
    # ESTADO, no si se guarda.
    ruta_f = os.path.join(carpeta, "%s.zip" % clave)
    with io.open(ruta_f, "wb") as f:
        f.write(r.content)

    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        nombres = z.namelist()
    except Exception:
        print("    %-40s ❌ la respuesta no es un ZIP (%d bytes, guardada)"
              % (clave, len(r.content)))
        return {clave: {"estado": "FALLO", "paso": "zip",
                        "detalle": "la respuesta no es un ZIP",
                        "bytes": len(r.content)}}

    # ⚠️ Se cuentan los CSV CON DATOS, no los ficheros: el ZIP trae uno por
    # señal aunque la señal esté muerta. El 12-sep-2026, de 6 señales, una
    # (`CH06T65QTOTA`, Cortijo) devolvió solo la cabecera — su serie acabó en
    # 2022 —, así que «6 ficheros» habría dado por vivo lo que no lo está.
    con_datos = 0
    for n in nombres:
        lineas = [x for x in z.read(n).decode("utf-8", "replace").splitlines()
                  if x.strip()]
        if len(lineas) > 1:
            con_datos += 1

    print("    %-40s ✅ %d señales · %d con datos · %5.1f KB · %.1f s"
          % (clave, len(sids), con_datos, len(r.content) / 1024, dur))
    return {clave: {
        "estado": "OK" if con_datos else "VACIO",
        "bytes": len(r.content),
        "comprimido": os.path.getsize(ruta_f),
        "elementos": con_datos,
        "estaciones": len(ids),
        "senales": len(sids),
        "desde": desde,
        "hasta": hasta,
        "segundos": round(dur, 2),
    }}


def fundir(anterior, fichas, ahora_iso, confederaciones=()):
    """M30. El veredicto del día, no el de la última pasada.

    Devuelve `(fuentes, pasadas, confederaciones_del_dia,
    previas_sin_registrar)`. Una fuente consta como FALLO **solo si
    ninguna pasada del día la trajo**; si una pasada anterior la trajo bien, se
    conserva aquélla y la de ahora queda anotada en `ultima_pasada`.

    ⚠️ Es una función PURA y vive fuera de `main()` a propósito: lo que se
    calcula dentro de un `main` no lo prueba nadie. Su prueba está en
    `--autotest`.

    ⚠️ Y NO ESCONDE NADA. El caso que preocupa —un servidor que lleva roto
    desde la mañana y parece bien porque a las 09:30 respondió— se ve en
    `ultima_pasada`, que dice qué pasó en la más reciente.
    """
    anterior = anterior or {}
    previas = anterior.get("fuentes", {}) or {}
    fuentes = dict(previas)

    for clave, nueva in fichas.items():
        vieja = previas.get(clave)
        if nueva.get("estado") == "OK":
            fuentes[clave] = dict(nueva, de_pasada_utc=ahora_iso)
        elif vieja and vieja.get("estado") == "OK":
            # ⚠️ El dato bueno está en disco: una pasada fallida hace
            # `continue` ANTES de escribir, así que no ha pisado el `.gz`.
            # El manifiesto se limita a decir la verdad del disco.
            fuentes[clave] = dict(vieja, ultima_pasada={
                "utc": ahora_iso,
                "estado": nueva.get("estado"),
                "detalle": nueva.get("detalle")})
        else:
            fuentes[clave] = dict(nueva, de_pasada_utc=ahora_iso)

    # ⚠️⚠️ UN MANIFIESTO ANTERIOR SIN `pasadas` NO ES UN DÍA SIN PASADAS.
    # Lo vio la ejecución real del 12-sep-2026 a las 20:00: el manifiesto del
    # día quedó diciendo «1 pasada» cuando ese día hubo TRES — las de 09:30 y
    # 14:00 las escribió la v1.02, que no registraba este campo. Sin esta
    # marca, ese día parecería de una sola pasada para siempre, y lo mismo le
    # pasaría a cualquier día en que se estrene una versión.
    #
    # No se inventa un número: se dice que hubo pasadas y que no se sabe
    # cuántas, con lo único que sí se sabe —cuántas fuentes había ya—.
    previas_sin_registrar = None
    if anterior and "pasadas" not in anterior and previas:
        previas_sin_registrar = {
            "motivo": "el manifiesto del día venía de una versión anterior a "
                      "la v1.03, que no registraba las pasadas",
            "fuentes_que_ya_habia": len(previas),
            "visto_el": ahora_iso,
        }

    pasadas = list(anterior.get("pasadas", []))
    pasadas.append({
        "utc": ahora_iso,
        "confederacion": sorted(confederaciones),
        "ok": sum(1 for f in fichas.values() if f.get("estado") == "OK"),
        "vacio": sum(1 for f in fichas.values() if f.get("estado") == "VACIO"),
        "fallo": sum(1 for f in fichas.values() if f.get("estado") == "FALLO"),
    })

    # ⚠️ LAS CUENCAS DEL DÍA, NO LAS DE ESTA PASADA. Si `fuentes` describe el
    # día, `confederacion` y `peso_cubierto` tienen que describir lo mismo, o
    # el manifiesto se contradice a sí mismo: con una pasada de solo el Ebro
    # decía cubrir el 22,76 % mientras sus fuentes traían el 77,71 %. Lo que
    # hizo cada pasada ya está en `pasadas`.
    confs = sorted(set(anterior.get("confederacion", []))
                   | set(confederaciones))
    return fuentes, pasadas, confs, previas_sin_registrar


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

    # --- v1.03 · la versión vive en un solo sitio -------------------------
    # ⚠️ La misma prueba que el archivador estrenó en su v3.14, y que el
    # 12-sep-2026 demostró servir: llevaba TRES DÍAS en rojo porque las v3.15
    # y v3.16 subieron la constante sin escribir su bloque de historial.
    en_cabecera = re.findall(r"^v(\d+\.\d+)", __doc__ or "", re.M)
    comprobar(bool(en_cabecera), "el historial de la cabecera tiene versiones")
    if en_cabecera:
        comprobar("v" + en_cabecera[0] == VERSION,
                  "⚠️ VERSION (%s) y el primer bloque del historial (v%s) "
                  "coinciden" % (VERSION, en_cabecera[0]))

    # --- v1.03 · D39: lo nuevo está declarado -----------------------------
    comprobar("tiempo_real_risr" in CONFEDERACIONES["duero"]["endpoints"],
              "D39 · el Duero captura la hidrología en tiempo real")
    comprobar("resumen_niveles" in CONFEDERACIONES["mino_sil"]["endpoints"],
              "D39 · el Miño-Sil captura el resumen de niveles")
    comprobar(all("marca" in e for c in CONFEDERACIONES.values()
                  for e in c["endpoints"].values() if e["formato"] == "html"),
              "⚠️ todo endpoint HTML declara su marca: un 200 no valida nada")
    comprobar(CONFEDERACIONES["duero"]["endpoints"]["tiempo_real_risr"]
              .get("contar") is not None,
              "⚠️ el visor del Duero declara QUÉ contar: ahí `<tr>` no mide "
              "nada (9 tablas, 32 celdas, 290 estaciones en el JavaScript)")
    comprobar(DIAS_QCENT >= 2,
              "QCENT pide un RANGO: es la única fuente que recupera huecos")

    # --- v1.03 · M30: el manifiesto dice el veredicto del DÍA -------------
    ayer = "2026-09-12T09:30:00+00:00"
    ahora_ = "2026-09-12T14:00:00+00:00"
    primera = {"a": {"estado": "OK", "bytes": 10},
               "b": {"estado": "FALLO", "detalle": "HTTP 500"}}
    fuentes1, pasadas1, confs1, _ = fundir(None, primera, ayer, ["ebro"])
    comprobar(fuentes1["a"]["estado"] == "OK" and len(pasadas1) == 1,
              "M30 · la primera pasada del día se escribe tal cual")

    man1 = {"fuentes": fuentes1, "pasadas": pasadas1}
    segunda = {"a": {"estado": "FALLO", "detalle": "timeout"},
               "b": {"estado": "OK", "bytes": 20}}
    man1["confederacion"] = confs1
    fuentes2, pasadas2, confs2, _ = fundir(man1, segunda, ahora_, ["duero"])

    # ⚠️ ÉSTA ES LA PRUEBA QUE JUSTIFICA M30, y falla con el código de la
    # v1.02: una pasada fallida degradaba el veredicto del día aunque el
    # fichero bueno siguiera en disco.
    comprobar(fuentes2["a"]["estado"] == "OK",
              "⚠️ M30 · una pasada fallida NO degrada una fuente que otra "
              "pasada del día ya trajo (con la v1.02 esto daba FALLO)")
    comprobar(fuentes2["a"].get("de_pasada_utc") == ayer,
              "M30 · y se dice DE QUÉ PASADA viene el dato que vale")
    comprobar(fuentes2["b"]["estado"] == "OK",
              "M30 · una fuente que se recupera pasa a OK")
    comprobar(len(pasadas2) == 2 and pasadas2[1]["fallo"] == 1,
              "M30 · el rastro de todas las pasadas se conserva")

    # ⚠️ Y LA OTRA MITAD: que fundir NO ESCONDA el fallo de ahora. Sin esto,
    # un servidor roto desde la mañana parecería sano toda la tarde.
    comprobar(fuentes2["a"].get("ultima_pasada", {}).get("estado") == "FALLO",
              "⚠️ M30 · el fallo de la última pasada queda VISIBLE en la "
              "ficha: fundir no es esconder")
    comprobar(fuentes2["a"].get("ultima_pasada", {}).get("detalle")
              == "timeout",
              "M30 · con su detalle, no solo el estado")

    # una fuente que nadie ha traído en todo el día sigue siendo FALLO
    fuentes3, _, _, _ = fundir({"fuentes": fuentes2, "pasadas": pasadas2},
                            {"c": {"estado": "FALLO", "detalle": "HTTP 503"}},
                            ahora_)
    comprobar(fuentes3["c"]["estado"] == "FALLO",
              "⚠️ M30 · lo que NINGUNA pasada trajo sigue constando FALLO")

    # ⚠️⚠️ Y el defecto que encontró la EJECUCIÓN REAL del 12-sep a las 20:00,
    # que ni el autotest ni la prueba en vivo habían visto: el día que se
    # estrena una versión, el manifiesto anterior no tiene `pasadas`, y decir
    # «1 pasada» de un día que tuvo tres es falso.
    viejo_v102 = {"fuentes": {"a": {"estado": "OK"}, "b": {"estado": "OK"}},
                  "confederacion": ["ebro"]}          # sin `pasadas`
    f4, p4, c4, previas4 = fundir(viejo_v102, {"a": {"estado": "OK"}},
                                  ahora_, ["ebro"])
    comprobar(previas4 is not None,
              "⚠️⚠️ M30 · un manifiesto anterior SIN `pasadas` no es un día "
              "sin pasadas: se marca (lo vio la ejecución real, no el autotest)")
    comprobar(previas4 and previas4["fuentes_que_ya_habia"] == 2,
              "M30 · y se dice lo único que se sabe: cuántas fuentes había ya")
    comprobar(len(p4) == 1,
              "M30 · no se inventa un número de pasadas que no se sabe")

    # ⚠️ Y la otra mitad: en un día normal NO se marca nada. Sin esto, la
    # marca saldría siempre y dejaría de significar algo (trampa 7).
    _, _, _, previas5 = fundir({"fuentes": f4, "pasadas": p4},
                               {"a": {"estado": "OK"}}, ahora_, ["ebro"])
    comprobar(previas5 is None,
              "⚠️ M30 · en una pasada normal NO se marca: la marca solo vale "
              "si aparece cuando toca")

    # ⚠️ El defecto que encontró la prueba EN VIVO y no el autotest: tras una
    # pasada parcial, el manifiesto decía cubrir el 22,76 % con fuentes del
    # 77,71 % dentro. Si `fuentes` es del día, `confederacion` también.
    comprobar(confs2 == ["duero", "ebro"],
              "⚠️ M30 · `confederacion` acumula las cuencas del DÍA: una "
              "pasada parcial no puede hacer que el manifiesto se contradiga")
    comprobar(pasadas2[1].get("confederacion") == ["duero"],
              "M30 · y lo que pidió cada pasada queda en `pasadas`")

    print("")
    print("  %d de %d comprobaciones pasan" % (hechas[0] - len(fallos),
                                               hechas[0]))
    return not fallos


# ============================================================================
def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raiz", default=CARPETA)
    # ⚠️ POR DEFECTO, TODAS. Hasta la v1.01 el defecto era solo `ebro`, que
    # pesa el 22,76 %: la tarea programada y el workflow llaman sin este
    # argumento, así que un defecto parcial habría dejado fuera el 77 % de
    # España sin que nadie lo notara. Un defecto que captura de menos es un
    # fallo mudo.
    p.add_argument("--confederacion", nargs="+", default=sorted(CONFEDERACIONES),
                   choices=sorted(CONFEDERACIONES),
                   help="una o varias. Por defecto, todas las configuradas")
    p.add_argument("--autotest", action="store_true")
    a = p.parse_args()

    if a.autotest:
        return 0 if autotest() else 1

    ahora = dt.datetime.now(dt.timezone.utc)
    peso = sum(CONFEDERACIONES[c]["peso"] for c in a.confederacion)
    print("  SAIH · %s · %s" % (", ".join(a.confederacion), ahora.isoformat()))
    print("  cobertura de estas cuencas: %.2f %% del volumen embalsado "
          "peninsular" % peso)

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

    # ⚠️ Una confederación que falla NO impide capturar las demás. Cada una
    # deja su estado en las fichas y el manifiesto las lleva todas: si el
    # servidor del Duero está caído, el Miño-Sil se captura igual. Perder una
    # captura es irreversible, y perder tres por culpa de una sería absurdo.
    fichas = {}
    for conf in a.confederacion:
        fichas.update(capturar(conf, ca, carpeta))

    # ⚠️ El turbinado va aparte porque no es un endpoint (ver `capturar_qcent`),
    # y solo si se ha pedido el Ebro: es suyo. ✅ Comprobado el 12-sep-2026:
    # ninguna de las otras dos cuencas publica turbinado por central.
    if "ebro" in a.confederacion:
        fichas.update(capturar_qcent(ca, carpeta))

    # M30 · el manifiesto del día se FUNDE con el que ya hubiera.
    ruta_m = os.path.join(carpeta, "manifiesto.json")
    anterior = None
    if os.path.isfile(ruta_m):
        try:
            with io.open(ruta_m, encoding="utf-8") as f:
                anterior = json.load(f)
        except Exception as e:
            # ⚠️ Un manifiesto ilegible NO tumba la captura ni se sobrescribe
            # en silencio: se avisa y se sigue como si fuera la primera pasada.
            # El dato ya está en disco, que es lo que no se puede perder.
            print("  ⚠️ el manifiesto del día no se puede leer (%s): se "
                  "escribe uno nuevo" % type(e).__name__)

    fuentes, pasadas, confs, previas = fundir(
        anterior, fichas, ahora.isoformat(), a.confederacion)
    peso_dia = sum(CONFEDERACIONES[c]["peso"] for c in confs)

    manifiesto = {"ejecucion_utc": ahora.isoformat(),
                  "primera_ejecucion_utc": (anterior or {}).get(
                      "primera_ejecucion_utc", ahora.isoformat()),
                  "pasadas": pasadas,
                  "confederacion": confs,
                  "peso_cubierto": round(peso_dia, 2),
                  "version": VERSION,
                  "fuentes": fuentes}
    if previas:
        manifiesto["pasadas_previas_sin_registrar"] = previas
    with io.open(ruta_m, "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=1)

    # ⚠️⚠️ Y EL MISMO CONTENIDO EN LA RAÍZ, COMO `ultimo.json`. No es un
    # duplicado por gusto: **es lo que el vigilante lee**, y sin él no puede
    # vigilar este archivo. Peor todavía, hasta `vigilante.py` v1.04 lo abría
    # sin red, así que su ausencia lanzaba una excepción que dejaba al
    # vigilante sin evaluar NINGUNA de sus seis alarmas — no sobre el SAIH:
    # sobre nada.
    #
    # El archivador hace exactamente esto mismo, y por eso el vigilante lo ve.
    # Aquí faltaba, y era la razón de fondo por la que el SAIH nacía siendo un
    # punto ciego aunque su `indice.csv` tuviera el formato correcto.
    #
    # Es la carpeta del día la que se sobrescribe cada pasada; éste, también:
    # «último» quiere decir el último, y su historia ya está en las carpetas.
    with io.open(os.path.join(a.raiz, "ultimo.json"), "w",
                 encoding="utf-8") as f:
        json.dump(dict(manifiesto, ruta=rel), f, ensure_ascii=False, indent=1)

    # ⚠️ Al índice va lo FUNDIDO, no la pasada suelta: el vigilante lee esto
    # para contestar «¿tenemos el dato del día?», y la respuesta correcta es la
    # del día. Lo que dio cada pasada queda en `pasadas` del manifiesto.
    ok, vacio, fallo = anotar_indice(a.raiz, rel, fuentes, ahora)
    print("")
    # ⚠️ DOS LÍNEAS Y NO UNA: la de arriba lista lo que ha hecho ESTA pasada y
    # el recuento es del DÍA. Con una sola línea, una pasada de 3 capturas
    # terminaba diciendo «7 OK» y parecía que había capturado siete.
    print("  esta pasada: %d OK · %d vacías · %d fallos"
          % (sum(1 for f in fichas.values() if f.get("estado") == "OK"),
             sum(1 for f in fichas.values() if f.get("estado") == "VACIO"),
             sum(1 for f in fichas.values() if f.get("estado") == "FALLO")))
    # ⚠️ «%d pasada(s)» a secas MIENTE el día que se estrena una versión:
    # las anteriores existieron y no están contadas. Se dice.
    cuantas = "%d" % len(pasadas)
    if previas:
        cuantas = "%d registrada(s), y antes hubo más sin registrar" % len(pasadas)
    print("  el día     : %d OK · %d vacías · %d fallos · %s · "
          "%.2f %% de cobertura" % (ok, vacio, fallo, cuantas, peso_dia))
    if previas:
        print("     ⚠️ %s (ya había %d fuentes)"
              % (previas["motivo"], previas["fuentes_que_ya_habia"]))
    # ⚠️ Devuelve 0 aunque haya fallos: quien avisa es el vigilante leyendo el
    # índice, no un workflow en rojo. Un workflow que se pone rojo cada vez que
    # una fuente falla llena de correos y acaba silenciado.
    return 0


if __name__ == "__main__":
    sys.exit(main())
