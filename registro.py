#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""REGISTRO DE FALLOS DEL ARCHIVO — qué falló, cuándo, y durante cuánto.

⚠️ ESTE FICHERO NO ES DE CASANDRA. Va en `eolosbcn/bess-archivador`, junto a
`vigilante.py`, de donde importa todo el motor. Esta copia en `Casandra\` existe
para poder leerla sin abrir GitHub y para que quede bajo git; **la que manda es
la desplegada**. Por eso no lleva el prefijo `casandra_` ni entra en la
disciplina de versiones de esta carpeta: su versión va en el historial de abajo.

DE DÓNDE SALE
=============
Xevi, 8-sep-2026: *«necesitamos un archivo que registre lo que ha fallado en
cada ocasión de manera precisa. Pero no quiero crear algo que crezca y
crezca.»*

Las dos cosas no las cumple un solo fichero, y por eso son DOS:

  · `fallos_recientes.csv` — una línea por fallo, **ventana móvil de 30 días**.
    ✅ Medido sobre 427 capturas el 9-sep-2026: 1.261 fallos → **62,6 KB**, y
    el tamaño no crece con el tiempo porque al entrar una captura sale la de
    hace 30 días.
  · `episodios.csv` — una línea por **tramo continuo** de fallo, para siempre.
    ✅ Medido sobre 427 capturas el 9-sep-2026: 73 episodios → **4,4 KB**, o
    sea ~60 bytes por episodio y del orden de **55 KB al año** al ritmo actual.

⚠️ Esa cifra de 55 KB/año CORRIGE a la baja el «~138 KB/año» que estimó
`vigilante.py` v1.03 el 8-sep-2026, y la corrige porque aquélla era una
estimación y ésta es una medición del fichero ya escrito. No se persigue la
frase en `vigilante.py`: era conservadora, o sea que erraba por el lado bueno.

El primero contesta «¿qué está fallando ahora y desde cuándo?». El segundo,
«¿esto ya había pasado antes?». Ninguno de los dos contesta la pregunta del
otro, y por eso no se pueden fundir en uno.

⚠️ POR QUÉ ES UN PROGRAMA APARTE Y NO UNA OPCIÓN DEL VIGILANTE
==============================================================
Porque escribir exige `contents: write`, y **el vigilante corre con
`contents: read` a propósito**: su garantía es que un fallo suyo NO PUEDE tocar
el archivo. Meterle la escritura dentro habría cambiado esa garantía por
comodidad, y es la única que tiene.

El motor —`leer_capturas()`, `intervalos()`, `episodios()` y
`escribir_registro()`— vive en `vigilante.py`, que es donde están las trampas
ya medidas y encapsuladas (la clave canónica, el `.csv.gz` que es el mismo
fichero que el `.csv`, la tolerancia al parpadeo). Este programa es **el
llamador**: decide qué claves cuentan como fallo, lo ejecuta sobre cada archivo
y rinde cuentas del tamaño.

⚠️ POR QUÉ AQUÍ SÍ BASTA EL CRON DE GITHUB
==========================================
El cron de GitHub entrega entre el **42 % y el 67 %** (medido del 14 al
26-ago-2026), y por eso el archivador se dispara desde cron-job.org. Aquí **no
hace falta**, y la diferencia es de fondo, no de comodidad:

**El registro se RECONSTRUYE del archivo en cada pasada.** No acumula nada que
dependa de haber corrido ayer, así que una pasada perdida no pierde ningún
dato: la siguiente rehace la ventana entera. Lo único que crece de verdad es
`episodios.csv`, y ése se **funde** con lo que ya había en vez de reescribirse.

Al archivador un disparo perdido le cuesta una captura irrecuperable. A esto,
nada. Es la misma aritmética con un resultado distinto, y por eso se escribe.

⚠️ LAS FUENTES RETIRADAS NO CUENTAN COMO FALLO
==============================================
`RETIRADAS`, en `vigilante.py`, son fuentes que se mudaron **a propósito**, no
averías: `esios_catalogo_previsiones` pasó a `archivo/catalogo.csv` el
5-sep-2026. Si contaran, `fallos_recientes.csv` tendría una línea por captura y
por fuente retirada —cientos de líneas de contenido conocido— y `episodios.csv`
un episodio abierto para siempre. Enterrarían los fallos de verdad, que es justo
lo que este fichero existe para hacer visible. Es la trampa 7 de la casa
aplicada a un registro: *lo que sale siempre deja de informar*.

⚠️ Y NO SE SILENCIAN, que sería la trampa 6: la **alarma 6 del vigilante**
comprueba que el SUSTITUTO de cada retirada siga vivo. Aquí se toma la misma
decisión que ya toma la alarma 4, para que las dos digan lo mismo — y cada
pasada las **nombra por pantalla**, para que una retirada no se vuelva
invisible por costumbre.

QUÉ ARCHIVOS RECORRE
====================
Los que se le pasen en `--raiz`, uno o varios. Hoy son dos: `archivo`, el del
archivador, y `archivo_saih`, el del SAIH. Cada uno recibe **su propio par de
ficheros** dentro de su carpeta, porque son series con vidas distintas y
mezclarlas haría ilegibles las dos.

HISTORIAL
v1.02  11-sep-2026. **A19 gana su BOTÓN DE SIMULACRO**, que es lo que le
       faltaba para poder cerrarse: la alarma estaba desplegada y en verde, pero
       **no se había visto saltar**, y verla de otro modo exigiría parar el
       vigilante unas horas — o sea dejar el archivo irreproducible sin vigilar
       mientras dure. El simulacro **baja el umbral, no toca el dato**.

       ⚠⚠ **Y lleva dentro la lección de `vigilante.py` v1.02, que fue su fallo
       más peligroso:** se fuerza **SOLO si la alarma no saltaba ya**. Si el
       vigilante estuviera mudo de verdad mientras alguien lanza el ensayo, la
       incidencia sale **SIN** la marca `[SIMULACRO]` — porque una avería real
       etiquetada como simulacro es una avería que alguien descarta de un
       vistazo.

v1.01  11-sep-2026. **A19: `registro` pasa a vigilar al VIGILANTE.** Vive aquí
       y no allí porque un vigilante que se vigila a sí mismo no vigila nada: si
       está caído, no pregunta. Ver `vigilante.py` v1.06 para el razonamiento
       entero y para por qué se lee el registro de ejecuciones de GitHub en vez
       de un latido que él escriba.

       ⚠️ Esta entrada se escribe **a posteriori**: la v1.01 se desplegó en el
       commit `ff1f5d0` **sin subir el número ni anotar el cambio aquí**, que es
       la disciplina de versiones de la casa incumplida. Se anota con su fecha
       real y no se finge que no pasó.

v1.00  9-sep-2026. Versión inicial. El motor ya estaba en `vigilante.py` v1.03;
       lo que faltaba era el llamador y su workflow con permiso de escritura.
"""

import argparse
import io
import os
import sys

import vigilante


# ⚠️ NO es un umbral fino, es un DETECTOR DE DISPARATES, y su número sale de una
# cuenta, no de una intuición. ✅ Medido sobre 427 capturas el 9-sep-2026:
# 1.261 fallos ocupan 62,6 KB, o sea **50,8 bytes por línea**. El caso peor
# imaginable es que fallen LAS 17 fuentes en TODAS las capturas de la ventana:
# 17 × 427 × 50,8 B = **369 KB**. Por eso el techo son 1.000 KB y no 500: con
# 500 lo dispararía un mes catastrófico pero legítimo, y entonces el aviso
# estaría diciendo «la ventana no recorta» cuando la ventana funciona.
#
# Puesto en 1.000, solo puede saltar si la ventana móvil deja de recortar de
# verdad — que es el único fallo posible de este programa, y el que rompería la
# promesa de Xevi de «que no crezca y crezca».
TECHO_RECIENTES_KB = 1000.0


def carpeta_destino(raiz):
    """Dónde escribe `escribir_registro()`, para poder medir lo escrito.

    ⚠️ Es una COPIA DELIBERADA de la expresión que usa `escribir_registro()`
    en `vigilante.py`. Duplicar una regla es arriesgado —si allí cambia, aquí
    se queda vieja—, así que `registrar()` comprueba después que los dos
    ficheros existan de verdad donde esto dice. Si divergen, falla y lo dice,
    en vez de informar de un tamaño de algo que no se escribió.
    """
    return raiz if os.path.isfile(os.path.join(raiz, "indice.csv")) \
        else os.path.join(raiz, "archivo")


def claves_que_cuentan(info):
    """Qué claves cuenta como fallo su ausencia. Devuelve (claves, retiradas).

    Dos exclusiones, y las dos con motivo:

      · las **retiradas**, porque se mudaron a propósito (ver la cabecera);
      · las que aparecen menos de `MINIMO_PRESENCIAS` veces.

    ⚠️ El segundo filtro hoy no quita nada: `MINIMO_PRESENCIAS` vale **1**
    desde el 8-sep-2026, porque con 20 impedía avisar de una fuente vista pocas
    veces —✅ medido: con 1, 3, 10 o 20 salían las MISMAS 5 incidencias en 29
    días, o sea que no silenciaba nada y sí podía silenciar—. Se deja escrito
    para que este programa siga el criterio del vigilante si algún día cambia,
    en vez de tener el suyo propio y divergir en silencio.
    """
    claves, retiradas = set(), []
    for clave, (presencias, _, _) in info.items():
        if clave in vigilante.RETIRADAS:
            retiradas.append(clave)
            continue
        if presencias < vigilante.MINIMO_PRESENCIAS:
            continue
        claves.add(clave)
    return claves, sorted(retiradas)


def registrar(raiz):
    """Escribe los dos ficheros de UN archivo. Devuelve qué hizo, en un dict."""
    capturas, sin_carpeta = vigilante.leer_capturas(raiz)

    # ⚠️ NADA DE SEGUIR EN SILENCIO, Y NADA DE ESCRIBIR. Cero capturas no
    # significa «no hay novedad»: significa que el índice no se puede leer o que
    # las carpetas del archivo no están, que es el peor caso posible.
    # `escribir_registro()` ya se protege y no escribe, pero además hay que
    # DECIRLO y salir con error — si no, una pasada sobre un archivo roto se
    # vería igual que una pasada limpia.
    if not capturas:
        raise RuntimeError(
            "no he leido ni una captura en %r. O falta indice.csv, o sus "
            "carpetas no estan. NO se toca el registro: reescribirlo ahora "
            "borraria lo unico que sabemos de los fallos anteriores." % raiz)

    info = vigilante.intervalos(capturas)
    claves, retiradas = claves_que_cuentan(info)
    n_fallos, n_episodios = vigilante.escribir_registro(raiz, capturas, claves)

    destino = carpeta_destino(raiz)
    tam = {}
    for nombre in ("fallos_recientes.csv", "episodios.csv"):
        ruta = os.path.join(destino, nombre)
        if not os.path.isfile(ruta):
            # ⚠️ Esto solo puede pasar si `escribir_registro()` ha cambiado de
            # sitio y `carpeta_destino()` se ha quedado vieja. Falla en vez de
            # dar por bueno un tamaño que no ha medido.
            raise RuntimeError(
                "he llamado a escribir_registro() y %r no esta en %r. "
                "carpeta_destino() ya no coincide con vigilante.py."
                % (nombre, destino))
        tam[nombre] = os.path.getsize(ruta) / 1024.0

    return {
        "raiz": raiz,
        "destino": destino,
        "capturas": len(capturas),
        "sin_carpeta": sin_carpeta,
        "claves": len(claves),
        "retiradas": retiradas,
        "fallos": n_fallos,
        "episodios": n_episodios,
        "kb": tam,
    }


def contar(r, salida=None):
    """Rinde cuentas por pantalla. Devuelve el numero de avisos serios."""
    escribe = salida.write if salida else sys.stdout.write
    avisos = 0
    escribe("\n  %s\n" % r["raiz"])
    escribe("    capturas leidas ......... %d\n" % r["capturas"])
    if r["sin_carpeta"]:
        # No es un fallo: el indice puede citar carpetas que aun no estan.
        # Pero se dice, porque un continue mudo miente por omision.
        escribe("    filas sin carpeta ....... %d (se cuentan, no se ignoran)\n"
                % r["sin_carpeta"])
    escribe("    fuentes vigiladas ....... %d\n" % r["claves"])
    for k in r["retiradas"]:
        escribe("    retirada, no cuenta ..... %s  (su sustituto lo vigila "
                "la alarma 6)\n" % k)
    escribe("    fallos en la ventana .... %d  -> fallos_recientes.csv "
            "%.1f KB\n" % (r["fallos"], r["kb"]["fallos_recientes.csv"]))
    escribe("    episodios acumulados .... %d  -> episodios.csv "
            "%.1f KB\n" % (r["episodios"], r["kb"]["episodios.csv"]))

    if r["kb"]["fallos_recientes.csv"] > TECHO_RECIENTES_KB:
        avisos += 1
        escribe("    ATENCION: fallos_recientes.csv pasa de %.0f KB. La "
                "ventana movil de %d dias ha dejado de recortar.\n"
                % (TECHO_RECIENTES_KB, vigilante.DIAS_VENTANA))
    return avisos


def autotest():
    """Pruebas sin red y sin tocar el archivo de verdad."""
    import gzip
    import shutil
    import tempfile

    hechas, fallos = 0, []

    def comprobar(nombre, condicion, detalle=""):
        nonlocal hechas
        hechas += 1
        if not condicion:
            fallos.append("%s %s" % (nombre, detalle))

    def archivo_falso(raiz, capturas):
        """capturas = [(etiqueta, {fichero: contenido o None}), ...]"""
        os.makedirs(raiz)
        filas = ["fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta"]
        nombre_raiz = os.path.basename(os.path.normpath(raiz))
        for etq, ficheros in capturas:
            fecha, hora = etq.split("-")[0:3], etq.split("-")[3]
            fecha = "-".join(fecha)
            rel = "%s/%s" % (nombre_raiz, fecha)
            carpeta = os.path.join(raiz, fecha)
            if not os.path.isdir(carpeta):
                os.makedirs(carpeta)
            for n, contenido in ficheros.items():
                if contenido is None:
                    continue
                with gzip.open(os.path.join(carpeta, n), "wb") as f:
                    f.write(contenido.encode("utf-8"))
            filas.append("%s,%s,%sT00:00:00+00:00,1,0,0,1.0,%s"
                         % (fecha, hora, fecha, rel))
        with io.open(os.path.join(raiz, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            f.write("\n".join(filas) + "\n")

    # --- 1. un archivo sano produce los dos ficheros -----------------------
    tmp = tempfile.mkdtemp()
    try:
        raiz = os.path.join(tmp, "archivo_prueba")
        caps = []
        for i in range(1, 11):
            etq = "2026-09-%02d-0900" % i
            # `b.csv.gz` desaparece a partir de la septima captura.
            caps.append((etq, {"a.csv.gz": "a%d" % i,
                               "b.csv.gz": None if i >= 7 else "b%d" % i}))
        archivo_falso(raiz, caps)
        r = registrar(raiz)
        comprobar("1a capturas leidas", r["capturas"] == 10,
                  "-> %d" % r["capturas"])
        comprobar("1b las dos fuentes vigiladas", r["claves"] == 2,
                  "-> %d" % r["claves"])
        comprobar("1c hay fallos de b", r["fallos"] == 4,
                  "-> %d (esperaba 4: capturas 7 a 10)" % r["fallos"])
        comprobar("1d un solo episodio", r["episodios"] == 1,
                  "-> %d" % r["episodios"])
        comprobar("1e los ficheros existen",
                  os.path.isfile(os.path.join(raiz, "fallos_recientes.csv"))
                  and os.path.isfile(os.path.join(raiz, "episodios.csv")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 2. un archivo VACIO no se toca, y falla --------------------------
    # ⚠️ Es la prueba que impide el peor fallo posible: que una pasada sobre un
    # archivo roto reescriba el registro dejandolo en blanco. Lo que se guarda
    # es justamente lo que diria que el archivo se rompio.
    tmp = tempfile.mkdtemp()
    try:
        raiz = os.path.join(tmp, "archivo_vacio")
        os.makedirs(raiz)
        with io.open(os.path.join(raiz, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
        # Registro previo, con contenido que NO se debe perder.
        previo = os.path.join(raiz, "episodios.csv")
        with io.open(previo, "w", encoding="utf-8", newline="") as f:
            f.write("fuente,desde,hasta,capturas\nx,a,b,1\n")
        salto = False
        try:
            registrar(raiz)
        except RuntimeError:
            salto = True
        comprobar("2a un archivo vacio hace fallar", salto)
        with io.open(previo, encoding="utf-8") as f:
            comprobar("2b y NO ha tocado episodios.csv", "x,a,b,1" in f.read())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 3. una fuente retirada no cuenta como fallo ----------------------
    retirada = sorted(vigilante.RETIRADAS)[0] if vigilante.RETIRADAS else None
    if retirada:
        info = {retirada: (5, 1.0, 1.0), "otra": (5, 1.0, 1.0)}
        claves, vistas = claves_que_cuentan(info)
        comprobar("3a la retirada queda fuera", retirada not in claves)
        comprobar("3b y se nombra", vistas == [retirada], "-> %r" % vistas)
        comprobar("3c la otra sigue dentro", "otra" in claves)
    else:
        comprobar("3 no hay retiradas que probar", True)

    # --- 4. carpeta_destino coincide con la del vigilante -----------------
    tmp = tempfile.mkdtemp()
    try:
        raiz = os.path.join(tmp, "r")
        os.makedirs(os.path.join(raiz, "archivo"))
        comprobar("4a sin indice, destino es raiz/archivo",
                  carpeta_destino(raiz) == os.path.join(raiz, "archivo"))
        with io.open(os.path.join(raiz, "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("x\n")
        comprobar("4b con indice, destino es la raiz",
                  carpeta_destino(raiz) == raiz)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ═══ v1.02 · el simulacro de A19 ═══════════════════════════════════
    # ⚠️ Sin red: se inyecta la respuesta de la API. Lo que se prueba no es
    # que hable con GitHub —eso ya se probo contra la API real— sino la regla
    # de cuando se marca y cuando NO.
    def api(fin):
        return lambda camino, token=None: {"workflow_runs": [{"updated_at": fin}]}

    import datetime as _dt
    _ahora = _dt.datetime.now(_dt.timezone.utc)
    recien = (_ahora - _dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    antiguo = (_ahora - _dt.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

    sano = vigilante.alarma_vigilante_mudo("x/y", None, horas=6.0,
                                           consultar=api(recien))
    comprobar("5a sin simulacro y con el vigilante vivo, no hay incidencia",
              sano is None)

    forzada = vigilante.alarma_vigilante_mudo("x/y", None, horas=-1.0,
                                              consultar=api(recien))
    comprobar("5b con umbral forzado si hay incidencia",
              forzada is not None)

    # ⚠⚠ LA PRUEBA QUE IMPORTA, y es la leccion de `vigilante.py` v1.02: con
    # el vigilante MUDO DE VERDAD, el simulacro NO debe etiquetar la averia.
    real = vigilante.alarma_vigilante_mudo("x/y", None, horas=6.0,
                                           consultar=api(antiguo))
    comprobar("5c una averia REAL se detecta con el umbral normal",
              real is not None and "[SIMULACRO]" not in real.titulo,
              "-> %r" % (real.titulo if real else None))

    print("\n  AUTOTEST · %d comprobaciones · %d fallos"
          % (hechas, len(fallos)))
    for f in fallos:
        print("    FALLA: %s" % f)
    return 0 if not fallos else 1


def vigilar_al_vigilante(repo, horas, simulacro=False, consultar=None):
    """A19 · ¿ha corrido el vigilante? Abre incidencia si lleva mudo.

    ⚠⚠ VIVE AQUÍ Y NO EN `vigilante.py` POR UN MOTIVO DE FONDO: un vigilante
    que se vigila a sí mismo no vigila nada. Si está caído no pregunta, y su
    silencio vuelve a significar las dos cosas —que todo va bien, o que no
    hay nadie mirando—. Esto es otro workflow, con otro horario.

    ℹ︎ Lo que NO cubre, dicho para que nadie lo suponga: si `registro` también
    se para, nadie mira a ninguno de los dos. Cerrarlo del todo exigiría un
    servicio de fuera del repositorio, y no lo hay.
    """
    if not repo:
        print("\n  ⚠️ --solo-vigilante sin --repo: no hay a quién preguntar.")
        return 2
    token = os.environ.get("GITHUB_TOKEN") or None
    print("\n  ¿SIGUE VIVO EL VIGILANTE? · %s · umbral %.0f h" % (repo, horas))

    # ⚠️ El fallo de red NO se traga y NO se convierte en «todo bien»: se
    # dice y la pasada queda en rojo, que es una señal visible. Tragarlo
    # crearía el fallo mudo que esta comprobación viene a cerrar.
    try:
        inc = vigilante.alarma_vigilante_mudo(repo, token, horas=horas,
                                              consultar=consultar)
        # ⚠⚠ EL SIMULACRO FUERZA SOLO SI NO SALTABA YA, y ésa es la lección de
        # `vigilante.py` v1.02 —su fallo más peligroso—. Si el vigilante está
        # mudo de verdad mientras alguien lanza el ensayo, la incidencia sale
        # SIN la marca: una avería real etiquetada como simulacro es una avería
        # que alguien descarta de un vistazo pensando «ah, es la prueba».
        if inc is None and simulacro:
            inc = vigilante.alarma_vigilante_mudo(repo, token, horas=-1.0,
                                                  consultar=consultar)
            if inc is not None:
                inc = vigilante.Incidencia(inc.clave,
                                           "[SIMULACRO] " + inc.titulo,
                                           inc.cuerpo)
    except Exception as e:
        print("    ERROR al preguntar a la API: %s: %s" % (type(e).__name__, e))
        print("    ⚠️ NO se sabe si el vigilante ha corrido. Eso no es "
              "«todo bien».")
        return 2

    if inc is None:
        print("    ✅ ha corrido dentro del umbral.")
        return 0

    # El titulo ya empieza por el aviso: repetirlo aqui lo duplicaba.
    print("    %s" % inc.titulo)
    if not token:
        print("    (sin GITHUB_TOKEN: no se publica, solo se dice)")
        return 1
    creadas, omitidas = vigilante.publicar([inc], repo, token,
                                           etiqueta="vigilante")
    print("    incidencias: %d creada(s), %d ya abierta(s)"
          % (len(creadas), len(omitidas)))
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raiz", nargs="+", default=["archivo"],
                   help="carpeta(s) con indice.csv. Se puede repetir: "
                        "--raiz archivo archivo_saih")
    # ⚠⚠ A19 · `registro` vigila al VIGILANTE, y por eso vive aquí y no allí:
    # un vigilante que se vigila a sí mismo no vigila nada, porque si está
    # caído no pregunta. Estos dos son otro workflow y otro horario.
    p.add_argument("--repo",
                   help="dueño/repo: si se da, comprueba que el vigilante "
                        "haya corrido y abre incidencia si lleva mudo (A19)")
    p.add_argument("--vigilar-al-vigilante-horas", type=float, default=6.0,
                   help="dos veces su cadencia de 3 h (por defecto 6)")
    p.add_argument("--simulacro", default="no",
                   help="⚠️ `vigilante_mudo` fuerza la alarma A19 para verla "
                        "saltar. BAJA EL UMBRAL, no toca ningun fichero. Solo "
                        "fuerza si la alarma no saltaba ya: una averia real "
                        "nunca sale etiquetada como simulacro.")
    p.add_argument("--solo-vigilante", action="store_true",
                   help="⚠️ SOLO la comprobacion A19, sin reconstruir nada. "
                        "Va en su propio paso del workflow y DESPUES de "
                        "guardar: si un fallo de red al preguntar a la API "
                        "abortara la reconstruccion, el registro no llegaria "
                        "a commitearse. Lo que vigila al vigilante no puede "
                        "poner en riesgo lo que este programa existe para "
                        "escribir.")
    p.add_argument("--autotest", action="store_true")
    a = p.parse_args()

    if a.autotest:
        return autotest()

    if a.solo_vigilante:
        return vigilar_al_vigilante(a.repo, a.vigilar_al_vigilante_horas,
                                    simulacro=(a.simulacro == "vigilante_mudo"))

    print("\n  REGISTRO DE FALLOS · %d archivo(s)" % len(a.raiz))
    avisos, resultados = 0, []
    # ⚠️ Un archivo que falla NO impide registrar los demas, pero el programa
    # termina con error igualmente: el fallo se cuenta y se dice al final.
    errores = []
    for raiz in a.raiz:
        try:
            r = registrar(raiz)
        except Exception as e:
            errores.append((raiz, e))
            print("\n  %s\n    ERROR: %s" % (raiz, e))
            continue
        resultados.append(r)
        avisos += contar(r)

    print("")
    if errores:
        print("  %d archivo(s) con error, %d registrado(s)."
              % (len(errores), len(resultados)))
        return 2
    if avisos:
        print("  %d aviso(s). El registro se ha escrito igualmente." % avisos)
        return 1
    print("  %d archivo(s) registrado(s), sin avisos." % len(resultados))
    return 0


if __name__ == "__main__":
    sys.exit(main())
