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
v1.09  18-sep-2026. **El umbral de A19 pasa a una CONSTANTE, porque el de la
    v1.07 no llegó nunca a producción.** La v1.07 subió `horas` de 6 a 9 como
    DEFECTO de `alarma_vigilante_mudo`, con su medición. Pero a esa función no
    la llama el vigilante: la llama `registro.py`, que le pasaba su propio
    defecto de 6 h, y `registro.yml` no le da otro. ✅ Medido el 18-sep-2026
    sobre 7 días (del 12 al 18-sep): A19 saltó los 7, con el vigilante parado
    entre 6,04 y 7,67 h; con 9 h no habría saltado ninguno. La reconstrucción
    reproduce lo que pasó en 7 de 7 días, que es su control
    (`Casandra\analisis\a19_20260918\`). La #18 iba y venía cada día, que es la
    trampa 7: un aviso que salta siempre deja de ser un aviso.

    Ahora el umbral es `HORAS_VIGILANTE_MUDO`, vive solo aquí y `registro.py`
    v1.04 lo lee. Lo que hace el vigilante no cambia: él no llama a A19.

v1.08  13-sep-2026. **Lo que B4 dejó, y lo que la revisión del plan encontró**
    (bloque **B32** del plan `20260913-C` de Casandra, decisión D54 de Xevi).

    ⚠️⚠️ **LOS SIMULACROS DE LAS ALARMAS 7 Y 8 NO SE PODÍAN LANZAR.** La v1.07
    escribió el código de `captura_critica` e `indicadores` dentro de
    `comprobar()`, pero `--simulacro` conservó los seis `choices` de antes y el
    desplegable del workflow también: **dos alarmas que nunca se vieron saltar**,
    la trampa 8 de la casa dentro del arreglo que la aplicaba. Ahora la lista
    de simulacros es UNA constante (`SIMULACROS`), la usa `argparse`, la copia el
    `vigilante.yml`, y el autotest comprueba que cada nombre tiene su rama en
    `comprobar()`: un ensayo que no se puede lanzar no es un ensayo.

    **N-operacion-11 · las alarmas 4 y 5 se apagaban al salir la avería de la
    ventana.** La 4 exige que la fuente haya aparecido DENTRO de las
    `CAPTURAS_A_LEER` capturas, y una fuente desaparecida hace más de ~62 días
    deja de estar en `info`: la alarma se apaga justo cuando la avería se hace
    vieja. Entra `alarma_desaparecido_larga`: la MEMORIA LARGA lista los
    ficheros de TODAS las capturas del índice (solo `listdir`, sin huellas:
    barato) y avisa de cualquiera que existió, no está en `RETIRADAS` y no
    aparece en la ventana entera. Solo actúa cuando el índice es más largo que
    la ventana: ✅ medido el 13-sep, el índice tiene 466 capturas y la ventana
    500, así que hoy la ventana contiene el archivo entero y la memoria larga
    no puede dar nada; se llena hacia el 17-18-sep. La 5 tenía el hueco
    simétrico: una fuente sin UN solo cambio en toda la ventana tiene intervalo
    de cambio infinito, `umbral_de` devuelve None y no se mira nunca. Entra
    `CONGELADO_SIN_CAMBIO = 200`: presente ≥ 200 capturas sin cambiar es aviso.
    ✅ Calibrado el 13-sep sobre 466 capturas: el intervalo de cambio más largo
    es el del A72 (51,8 capturas; umbral 155), así que ninguna fuente real se
    acerca; hoy 0 fuentes con intervalo infinito.

    **M35 · la degradación PARCIAL de una familia** (alarma 9,
    `alarma_degradacion_parcial`): la alarma 2 solo ve una familia MUDA entera;
    una familia con parte de sus fuentes caídas durante horas no la veía nadie.
    Se lee el manifiesto de las últimas `M35_VENTANA = 24` capturas y se avisa
    si la familia lleva ≥ `M35_RACHA = 4` capturas seguidas parcial, o
    ≥ `M35_MINIMO_EN_VENTANA = 5` parciales en esas 24. ✅ Calibrado el 13-sep
    sobre las 466 capturas, con todos los manifiestos (no el último de cada
    día, que escondía la mitad): la racha más larga fue 3 (entsoe) y el máximo
    en 24 seguidas 3 (aemet y entsoe) → **0 falsos positivos** sobre el archivo
    real, y el caso que motiva la alarma —una fuente de una familia caída medio
    día— se vería a las 4 capturas. ⚠️ La avería que MÁS pasa no la caza M35 y
    se dice: la captura de las 11:5x llega PARCIAL por 429 de AEMET (✅ 12 de 466
    capturas, 7 de ellas la 11:5x, 3 de los últimos 7 días), siempre en rachas
    de 1; eso lo arregla el archivador v3.18 con el reintento diferido dentro
    de la misma pasada, y M35 lo vería si se volviera persistente.

    Y dos precisiones: `CAPTURAS_A_LEER` decía «28 ms por captura»; ✅ medido el
    13-sep en la máquina de Xevi sobre 466 capturas, **121 ms** (56,5 s), así
    que las 500 son ~60 s, dentro del `timeout-minutes: 5`. Y nace el simulacro
    `desaparecido_largo` para poder pulsar la memoria larga.

v1.07  12-sep-2026. **A19 daba por vivo a un vigilante que fallaba en cada
    pasada**, y con ella entran la captura critica, M34 y el asignado que
    faltaba. Bloque **B4**.

    ⚠️⚠️ **A19 · «HA CORRIDO» NO ERA «HA TERMINADO BIEN».** La v1.06 pedia
    `status=completed` y solo miraba `updated_at`, asi que una pasada que
    termino en `failure` contaba como vigilancia: el vigilante podia llevar
    dias reventando en cada ejecucion y A19 lo daba por sano. Es el fallo que
    A19 existe para cerrar —silencio leido como «todo bien»— cometido dentro
    de A19. Ahora se busca la ultima pasada con `conclusion == "success"`, y
    si las mas recientes fallaron se dice cuantas.

    ⚠️ **Y nace `vigilante_degradado`**, con clave propia: si la ultima buena
    sigue dentro de plazo pero las posteriores fallan, se avisa ANTES de que
    el vigilante se quede mudo del todo.

    ⚠️ **El umbral de A19 pasa de 6 h a 9 h, con su medicion.** ✅ Sobre 47
    huecos entre pasadas el maximo fue **5,89 h** —a SIETE MINUTOS del umbral
    que habia— y ✅ **27 de 31 ranuras `schedule` entregadas (87 %)** con
    retraso maximo de **127 min**. O sea que 6 h no era «el doble de la
    cadencia», era el borde del ruido normal.

    ⚠️⚠️ **ALARMA 7 · LA CAPTURA DE LAS 11:5x.** Es el horizonte de
    informacion entero de Casandra —la foto de lo que se sabia al cerrar las
    ofertas— y perderla no degrada un dia, lo invalida. Hasta hoy no la veia
    nadie: la alarma 1 mira la antiguedad de la ULTIMA captura, asi que con
    las siguientes llegando en hora el archivo parece al dia; y el hueco que
    deja perderla mide **6,00 h exactas** contra un `> 6.0`, o sea que
    tampoco saltaba por antiguedad, por dos centesimas.

    Se escribe como IDENTIDAD y no como umbral (trampa 10): si un dia tiene
    capturas DESPUES de la franja y ninguna DENTRO, la de la franja se
    perdio. ⚠️ La franja **no es simetrica**: las 12:00 son el cierre de
    ofertas y son un limite DURO; el de abajo es blando, porque una captura a
    las 11:35 pierde quince minutos de informacion pero sigue valiendo. ✅
    Calibrada sobre 33 dias del archivo: 25 a las 11:50, 6 a las 11:51, y con
    la franja abierta a las 11:30 quedan dentro **33 de 33**. Y se autocalibra:
    un archivo que nunca captura a esa hora —el del SAIH— no dispara nunca.

    **ALARMA 8 · M34 · LOS INDICADORES QUE SE PIERDEN DENTRO DE UN FICHERO.**
    La unidad de vigilancia era el fichero, y `esios_previsiones` es UN
    fichero con 114 indicadores dentro: podia llegar puntual, pesar lo normal,
    cambiar cada dia y traer 26 series menos. ⚠️ El umbral se calibra solo
    **agrupando por `pedidos`**, porque ✅ sobre 448 capturas `indicadores_ok`
    va de 94 a 835 —hay capturas ligeras y completas— y una cifra fija no
    avisaria nunca o avisaria siempre. ✅ Con el corte en el 90 % de la
    mediana de su grupo, las 448 capturas pasan: **0 falsos positivos**, y el
    caso de M34 (88 sobre una mediana de 114) da 77 % y se ve.

    ⚠️ **`publicar()` deja de tener `asignar_a=None` por defecto.** El
    12-sep-2026 la incidencia **#15** —la primera vez que A19 salto de
    verdad— se abrio SIN ASIGNADO y no le llego a nadie, porque `registro.py`
    llamaba sin ese argumento. «No asignar» nunca es lo que se quiere en
    produccion, y un defecto que calla es el mismo fallo esperando al
    siguiente que llame.

    ❌ **LO QUE ESTA VERSION NO LLEVA, y se dice para que nadie lo de por
    hecho:** **M35** (degradacion parcial de una familia dentro de una
    captura) y **N-operacion-11** (las alarmas 4 y 5 se apagan cuando la
    averia sale de la ventana de 500 capturas, ~62 dias). Los dos siguen
    abiertos. M35 necesita un umbral por captura calibrado del propio archivo
    y no cabia sin repetir el trabajo de M34 a otra escala; el de los 62 dias
    es BAJO y esta identificado «por lectura», sin caso real todavia.

v1.06  11-sep-2026. **A19: nadie vigilaba al vigilante.** Si su workflow se
       paraba —desactivado, con cuota agotada, o fallando— no pasaba nada
       visible: **devolvia 0 siempre y su silencio se leia como «todo
       bien»**. Es el mismo fallo mudo que el existe para cazar, dentro de el.

       ⚠⚠ **NO se hace con un latido que el escriba**, que era lo que pedia
       la ficha, por dos motivos. El primero es que **no puede**: su workflow
       se declara `contents: read`, y darle escritura para dejar constancia le
       quitaria la propiedad que lo hace inofensivo —«aunque tuviera un fallo
       no podria modificar el archivo»—. El segundo pesa mas: un latido es
       una **firma** que el deja, y aqui hay una **identidad** disponible, el
       registro de ejecuciones de GitHub, que es la fuente autorizada de si
       corrio o no. Trampa 10 de la casa.

       ⚠️ **Y quien pregunta no es el.** `alarma_vigilante_mudo` la llama
       `registro.py`, que es otro workflow con otro horario: un vigilante que
       se vigila a si mismo **no vigila nada**, porque si esta caido no
       pregunta. Que los dos caigan a la vez es mucho menos probable que uno.

       ℹ︎ Lo que esto NO cubre, dicho para que nadie lo suponga: si `registro`
       tambien se para, nadie mira a ninguno de los dos. Cubrirlo del todo
       exigiria un servicio de fuera, y no lo hay.

v1.05  11-sep-2026. **A17: la alarma 6 no podia dispararse JAMAS, y nadie lo
       noto porque su silencio se leia como «todo bien».** Mediía
       `os.path.getmtime` del sustituto, y `actions/checkout` **reescribe el
       `mtime` de todos los ficheros al clonar**: en el runner la edad valia
       siempre ~0 y `edad > 48` no se cumplia nunca. La alarma se ejecutaba
       cada 3 horas, no daba error, y no miraba nada.

       ⚠️ Es la **trampa 10** de la casa: se media un METADATO que el entorno
       reescribe en vez de un DATO que el fichero declara. Ahora se lee la
       columna que `RETIRADAS[...]["fecha_por"]` nombre —hoy `visto` del
       catalogo—, que es **contenido** y sobrevive al checkout.

       ⚠⚠ Y el arreglo obvio NO servia: `git log -1 --format=%ct -- <ruta>`
       devolveria la fecha del unico commit que el checkout se trae, porque
       el workflow no pide `fetch-depth`. Habria cambiado una alarma que
       nunca salta por otra que lee un numero plausible y falso.

       ✅ **Y el simulacro `sustituto` pasa a forzarla de verdad.** Estaba
       aceptado en la linea de ordenes y ya ponia la marca `[SIMULACRO]`,
       pero la llamada era `alarma_sustituto_muerto(raiz)` sin forzar nada:
       un ensayo que no probaba nada. Ademas **no estaba en el desplegable
       del workflow**, asi que nadie lo pulso nunca para descubrirlo.

       ℹ︎ Efecto lateral util: el fallo deja de ser reproducible solo en el
       runner. Un fichero con fecha vieja dentro y `mtime` de ahora —que es
       exactamente lo que hace el checkout— se fabrica en local, y el banco
       de pruebas lo hace.

v1.04  9-sep-2026. **El vigilante pasa a vigilar DOS archivos**, el del
       archivador y el del SAIH, y los tres cambios que hacen falta son los
       tres la misma trampa: **evitar una alarma que salte siempre**.

       El SAIH ya no se captura en GitHub —`saihebro.com` no es alcanzable
       desde los runners— sino desde la máquina de Xevi, que empuja lo
       capturado a `archivo_saih/`. Sin esto era un punto ciego, y de los
       gordos: ⚠️ **nunca llegó a vigilarse**, porque el workflow desplegado
       decía `--raiz archivo` a secas. Lo que se comprobó el 8-sep fue que el
       formato del índice servía, no que estuviera conectado.

       · **`--etiqueta`**, y es la pieza que permite ejecutarlo dos veces.
         `publicar()` filtra las issues abiertas por etiqueta y con ellas
         calcula `claves_ahora`; compartiendo etiqueta, **cada archivo vería
         las incidencias del otro como recuperadas y se las cerraría cada tres
         horas**, con un comentario diciendo que ya no arde.
       · **`--horas`**, umbral de la alarma 1. El SAIH se captura 3 veces al
         día y su hueco nocturno es de **13,5 h**: con el umbral de 6 h del
         archivador saltaría todas las mañanas.
       · **`RETIRADAS` declara su archivo.** Sin eso, la alarma 6 buscaría
         `archivo_saih/catalogo.csv` —que no existe ni debe existir— y abriría
         una incidencia permanente.
       · ⚠️⚠️ **Y el cuarto, que es el grave: un `ultimo.json` que falta ya no
         mata al vigilante.** Lo abría con un `io.open()` sin red, así que su
         ausencia lanzaba una excepción que se llevaba por delante la función
         entera: **cero alarmas evaluadas y nada publicado**. La avería más
         tonta imaginable apagaba el sistema de avisos completo. Ahora es una
         incidencia más —`sin_ultimo`— y las otras cinco alarmas siguen
         corriendo. Se arregla también por el otro lado: `saih_captura.py`
         v1.01 escribe su `ultimo.json`, que es lo que faltaba de verdad.

       ⚠️ Ninguno de los tres se ve leyendo el código: los tres aparecen solo
       al preguntarse qué haría cada alarma sobre el archivo nuevo. Es la
       trampa 8 —la comprobación cruzada que está escrita y no se hace—
       aplicada a una alarma que se da por buena porque funciona en otro sitio.

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

       **Y todo lo que sigue entró DESPUÉS, empujado por el criterio de Xevi
       de esa misma tarde: «es mejor una alarma duplicada que ninguna alarma»
       y «el problema es que algo que deba generar una alarma no lo haga».**

       **`RETIRADAS` y la ALARMA 6.** La primera incidencia que abrió la
       alarma 4 —la #7— era una detección correcta y **no una avería**:
       `esios_catalogo_previsiones` se mudó a `archivo/catalogo.csv` el
       5-sep-2026, en ruta fija. Sin una tabla de retiradas, esa incidencia
       se reabriría para siempre. ⚠️⚠️ Pero una lista de «no me avises de
       esto» **esconde averías**, así que cada retirada declara
       OBLIGATORIAMENTE su sustituto y la **alarma 6** comprueba que ese
       sustituto sigue vivo. **No se silencia: se redirige.**

       ❌ **Se quita `MINIMO_PRESENCIAS = 20`**, que impedía que una fuente
       vista pocas veces disparara nunca. Era una protección que elimina
       alarmas, y ✅ medido: con mínimo 1, 3, 10 o 20 salen **exactamente las
       mismas 5 incidencias** en 29 días. No silenciaba nada, porque el
       trabajo ya lo hacían el umbral-múltiplo y la guarda de longitud.

       ⚠️ **Y el caso que enseña el criterio, porque sin él suena a eslogan:**
       al añadir la alarma 6 fallaron 6 pruebas heredadas, y la reacción iba a
       ser ponerle la guarda «si no hay capturas, no avises». Eso habría
       silenciado **en producción** el peor caso posible —que el archivo
       entero haya desaparecido— para que unos escenarios sintéticos dejaran
       de quejarse. Lo que fallaba no era la alarma: eran los escenarios.

       **AVISOS DE RECUPERACIÓN Y RECAÍDA.** Los destapó una analogía de Xevi:
       *«es como eliminar una alarma de incendios a los 20 min mientras sigue
       el incendio, y en el otro lado de la casa se piensan que ya no hay
       fuego»*. El antiduplicado impedía abrir una incidencia repetida —bien—
       pero dejaba un hueco: **la incidencia abierta decía que empezó un
       incendio y no decía si seguía ardiendo.** ⚠️ Y pasó de verdad ese día:
       Xevi cerró la #6 sin que nada le dijera que ENTSO-E había vuelto;
       había vuelto a las 20:51, pero lo supo por casualidad de horario.
       Ahora el vigilante **comenta en la incidencia cuando el estado
       CAMBIA** —al recuperarse y al recaer—, con marcadores HTML para no
       repetirse. ⚠️ **No la cierra: informa.** Cerrar sigue siendo decisión
       de Xevi.

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
import glob
import os
import sys
import time

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

# ⚠️ A19 · HORAS SIN UNA PASADA BUENA DEL VIGILANTE ANTES DE AVISAR (v1.09).
# ---------------------------------------------------------------------------
# Vive AQUÍ y en ningún otro sitio. La v1.07 subió el umbral de 6 a 9 h con su
# medición (ver `alarma_vigilante_mudo`), pero como DEFECTO de la función, y a
# la función no la llama el vigilante: la llama `registro.py`, que le pasaba
# su propio defecto de 6 h. El cambio no llegó nunca a la comprobación que
# corre. Desde la v1.09 `registro.py` lee esta constante en vez de tener la
# suya: un número que vive en dos sitios acaba valiendo dos cosas.
HORAS_VIGILANTE_MUDO = 9.0

# --- alarmas 4 y 5 y registro de fallos (v1.03) -----------------------------
CAPTURAS_A_LEER = 500      # ⚠️ tope del barrido. Medido el 7-sep: 28 ms por
#                            captura; ✅ el 13-sep en la máquina de Xevi, 121 ms
#                            sobre 466 (56,5 s), o sea ~60 s con 500. Sin tope, en un año habría
#                            ~5.256 capturas y el barrido tardaría 147 s cada
#                            tres horas. 500 son ~35 días, de sobra para medir
#                            cadencias y detectar desapariciones.
DIAS_VENTANA = 30          # ventana móvil de fallos_recientes.csv
# ⚠️ MINIMO_PRESENCIAS = 1, o sea DESACTIVADO, y es deliberado. Empezó en 20
# —«una fuente vista menos de 20 veces no avisa»— y eso era una protección que
# elimina alarmas. ✅ Medido sobre 419 capturas: con mínimo 1, 3, 10 o 20 salen
# EXACTAMENTE las mismas 5 incidencias de desaparecido y 0 de congelado en 29
# días. No silenciaba nada, porque ese trabajo ya lo hacen dos cosas mejores:
# el umbral como MÚLTIPLO del intervalo propio de cada fuente —una que solo
# sale en las capturas completas tiene intervalo 38 y umbral 114, y se trata
# sola— y la guarda `u >= len(capturas)`, que descarta a las que no tienen
# historia suficiente. Se deja la constante en 1 en vez de borrarla para que
# la decisión quede a la vista.
MINIMO_PRESENCIAS = 1
FACTOR_ALARMA = 3.0        # se avisa a 3× el intervalo normal de la fuente
MINIMO_CAPTURAS_ALARMA = 8  # suelo: nunca avisar antes de 8 capturas
TOLERANCIA_CIERRE = 2      # aciertos seguidos para cerrar un episodio

# --- v1.08 · N-operacion-11, M35 y los simulacros -----------------------------
# Alarma 5 sin cambio alguno: presente estas capturas seguidas con la MISMA
# huella es aviso aunque su intervalo de cambio sea infinito. ✅ 13-sep, 466
# capturas: el intervalo de cambio más largo es 51,8 (A72, umbral 155).
CONGELADO_SIN_CAMBIO = 200
# M35: una familia PARCIALMENTE caída (ni sana ni muda entera). ✅ 13-sep, sobre
# las 466 capturas y todos los manifiestos: racha máxima 3, máximo 3 en 24
# seguidas. Con 4 y 5, 0 falsos positivos hoy.
M35_VENTANA = 24
M35_RACHA = 4
M35_MINIMO_EN_VENTANA = 5
ESTADOS_DEGRADADOS = ("FALLO", "VACIO", "PARCIAL")   # OMITIDA no es avería
# ⚠️ UNA lista, y la usan argparse, el autotest y —copiada— vigilante.yml. La
# v1.07 tenía dos alarmas cuyo simulacro no estaba aquí y nunca se vio saltar.
SIMULACROS = ("antiguedad", "fuente_muda", "caducidad", "desaparecido",
              "congelado", "sustituto", "captura_critica", "indicadores",
              "degradacion", "desaparecido_largo")
EXTENSIONES = (".csv", ".csv.gz", ".json", ".gz")

# ⚠️ FUENTES RETIRADAS A PROPÓSITO — no son averías, y sin esta tabla la
# alarma 4 abriría una incidencia por cada una en cada pasada, para siempre.
#
# ⚠️⚠️ CADA ENTRADA DECLARA A DÓNDE SE FUE EL DATO, Y ES OBLIGATORIO. Una
# lista de «no me avises de esto» esconde averías: si mañana el fichero
# sustituto dejara de actualizarse, habríamos silenciado el nombre viejo y
# nadie se enteraría. **No se silencia: se redirige**, y el vigilante
# comprueba que el sustituto sigue vivo (alarma 6).
RETIRADAS = {
    "esios_catalogo_previsiones": {
        # ⚠️ `archivo` dice A QUÉ RAÍZ pertenece esta retirada, y no es
        # decorativo. Desde el 9-sep-2026 el vigilante corre también sobre
        # `archivo_saih`, y sin esta clave la alarma 6 buscaría
        # `archivo_saih/catalogo.csv` —que no existe ni debe existir—, abriría
        # una incidencia y la mantendría abierta para siempre. Es la trampa 7
        # de la casa: un aviso que salta siempre deja de ser un aviso.
        "archivo": "archivo",
        "sustituto": "catalogo.csv",
        # ⚠️ COMO se fecha este sustituto, desde la v1.05. No se mira su
        # `mtime` —el checkout lo reescribe— sino la fecha que el archivador
        # ESCRIBE DENTRO, en esta columna. Una retirada cuyo sustituto no se
        # pueda fechar avisa, porque no poder fecharlo es no vigilarlo.
        "fecha_por": "columna:visto",
        "desde": "2026-09-05",
        "motivo":
            "el archivador lo mudó a `archivo/catalogo.csv`, en ruta fija y "
            "acumulativa, y dejó de escribirlo dentro de cada captura. ✅ "
            "Comprobado el 8-sep-2026: 1.561 filas y su columna `visto` marca "
            "el día en curso. Fue la primera incidencia que abrió la alarma 4 "
            "(#7) y resultó ser un cambio deliberado, no una avería.",
    },
}


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
# ⚠️⚠️ EL CRITERIO QUE GOBIERNA ESTE PROGRAMA — Xevi, 8-sep-2026
# ============================================================================
#   «Para mí recibir alarmas de más no es problema. Lo investigamos y llegamos
#    a una conclusión. EL PROBLEMA ES QUE ALGO QUE DEBA GENERAR UNA ALARMA NO
#    LO HAGA.»
#
#   «A veces es mejor una alarma que no sepamos bien qué es e investigar, que
#    empezar a poner protecciones que eliminen alarmas. Es mejor una alarma
#    duplicada que ninguna alarma.»
#
# ⚠️ NO deroga la trampa 7 de la casa —un aviso que salta SIEMPRE deja de ser
# un aviso—, la ordena: lo que se combate es el aviso CONSTANTE, no el aviso
# que hay que investigar. Un falso positivo ocasional se mira y se cierra; uno
# permanente se convierte en `RETIRADAS` con su motivo escrito.
#
# ⚠️⚠️ Y va con el caso que lo obligó a formularlo, porque sin él suena a
# eslogan. Al añadir la alarma 6 fallaron 6 pruebas heredadas, y la reacción
# iba a ser ponerle una guarda: «si no hay capturas, no avises». Eso habría
# silenciado EN PRODUCCIÓN el peor caso posible —que el archivo entero haya
# desaparecido— para que unos escenarios sintéticos dejaran de quejarse. Lo
# que fallaba no era la alarma: eran los escenarios.
#
# La regla práctica que sale de ahí: **antes de añadir una condición que
# impide que una alarma salte, escribe qué avería quedaría muda.** Si la
# respuesta es «ninguna», adelante; si es «esta», no.
# ============================================================================

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
        if k in RETIRADAS:
            continue           # retirada a propósito: la vigila la alarma 6
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
    """Presente, pero con el mismo contenido > 3× su intervalo de cambio.

    v1.08 · N-operacion-11: una fuente que NUNCA cambió dentro de la ventana
    tiene intervalo de cambio infinito, `umbral_de` devuelve None y hasta hoy
    no se miraba jamás. Ahora, presente ≥ CONGELADO_SIN_CAMBIO capturas sin un
    solo cambio es aviso.
    """
    avisos = []
    for k, (n, _, ic) in sorted(info.items()):
        if n < MINIMO_PRESENCIAS:
            continue
        if ic == float("inf"):
            if n >= CONGELADO_SIN_CAMBIO:
                desde = next(e for e, d in capturas if d.get(k) is not None)
                avisos.append((k, n, desde))
            continue
        u = umbral_de(ic)
        if u is None or u >= len(capturas):
            continue
        ult = [d.get(k) for _, d in capturas[-u:]]
        if all(h is not None for h in ult) and len(set(ult)) == 1:
            avisos.append((k, u, capturas[-u][0]))
    return avisos


def fuentes_de_fichero_historicas(raiz):
    """{clave canónica: última etiqueta de captura en que apareció}, sobre TODAS
    las capturas del índice y sin calcular huellas (solo `listdir`): es la
    MEMORIA LARGA de la alarma 4 (v1.08, N-operacion-11). Devuelve también
    cuántas filas tiene el índice, para saber si es más largo que la ventana.
    """
    idx = os.path.join(raiz, "indice.csv")
    if not os.path.isfile(idx):
        idx = os.path.join(raiz, "archivo", "indice.csv")
    if not os.path.isfile(idx):
        return {}, 0
    base = os.path.dirname(os.path.dirname(idx))
    with io.open(idx, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    ultima = {}
    for fila in filas:
        carpeta = os.path.join(base, fila.get("ruta", ""))
        if not os.path.isdir(carpeta):
            continue
        etiqueta = "%s-%s" % (fila.get("fecha"), fila.get("hora"))
        for n in os.listdir(carpeta):
            if n.endswith(EXTENSIONES) and n != "manifiesto.json":
                ultima[canonico(n)] = etiqueta
    return ultima, len(filas)


def alarma_desaparecido_larga(raiz, capturas, info):
    """Fuentes que existieron y llevan MÁS que la ventana entera sin aparecer.

    La alarma 4 solo ve lo que está en `info`, y `info` sale de la ventana: una
    fuente ausente desde antes de la ventana no está en ninguna parte. Aquí se
    compara la memoria larga con la ventana. Solo actúa cuando el índice es
    más largo que la ventana; si no, la alarma 4 ya lo ve todo. Devuelve
    [(clave, capturas de la ventana, última etiqueta en que se vio)].
    """
    if not capturas:
        return []
    historicas, total = fuentes_de_fichero_historicas(raiz)
    if total <= len(capturas):
        return []
    en_ventana = {k for _, d in capturas for k, h in d.items() if h is not None}
    avisos = []
    for k, ultima in sorted(historicas.items()):
        if k in RETIRADAS or k in en_ventana:
            continue
        avisos.append((k, len(capturas), ultima))
    return avisos


def alarma_degradacion_parcial(raiz, ventana=M35_VENTANA, racha_minima=M35_RACHA,
                               minimo_en_ventana=M35_MINIMO_EN_VENTANA):
    """M35 · una familia con PARTE de sus fuentes caídas, de forma persistente.

    La alarma 2 salta cuando una familia entera calla; esto es lo de en medio:
    ni sana ni muda. Se leen los manifiestos de las últimas `ventana` capturas
    del índice y, por familia, se cuenta en cuántas está parcial (alguna fuente
    en ESTADOS_DEGRADADOS y no todas). Aviso si la racha final es ≥
    `racha_minima` o si hay ≥ `minimo_en_ventana` parciales en la ventana.
    ✅ Calibrado el 13-sep-2026 sobre 466 capturas: racha máxima 3 y máximo 3
    en 24 seguidas; con 4 y 5, 0 falsos positivos. Devuelve
    [(familia, racha, parciales en la ventana, capturas leídas, fuentes caídas
    en la última parcial, su etiqueta)].
    """
    idx = os.path.join(raiz, "indice.csv")
    if not os.path.isfile(idx):
        idx = os.path.join(raiz, "archivo", "indice.csv")
    if not os.path.isfile(idx):
        return []
    base = os.path.dirname(os.path.dirname(idx))
    with io.open(idx, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))[-ventana:]
    por_familia = collections.defaultdict(list)
    for fila in filas:
        rm = os.path.join(base, fila.get("ruta", ""), "manifiesto.json")
        try:
            with io.open(rm, encoding="utf-8") as f:
                fuentes = (json.load(f).get("fuentes") or {})
        except Exception:
            continue           # un manifiesto ilegible no aporta; lo vigila la 1
        etiqueta = "%s-%s" % (fila.get("fecha"), fila.get("hora"))
        fams = collections.defaultdict(dict)
        for k, v in fuentes.items():
            fams[familia_de(k)][k] = (v or {}).get("estado")
        for fam, d in fams.items():
            malas = sorted(k for k, e in d.items() if e in ESTADOS_DEGRADADOS)
            por_familia[fam].append((etiqueta, malas, len(d)))
    avisos = []
    for fam, serie in sorted(por_familia.items()):
        parciales = [(e, m, tot) for e, m, tot in serie if 0 < len(m) < tot]
        racha = 0
        for e, m, tot in reversed(serie):
            if 0 < len(m) < tot:
                racha += 1
            else:
                break
        if racha >= racha_minima or len(parciales) >= minimo_en_ventana:
            e, m, tot = parciales[-1]
            avisos.append((fam, racha, len(parciales), len(serie), m, e))
    return avisos


def fecha_declarada_dentro(ruta, columna):
    """La fecha MÁS NUEVA que el propio fichero declara en `columna`.

    ⚠️ Se parsea con el módulo `csv` y NO partiendo por comas: las
    descripciones del catálogo llevan comas y saltos de línea dentro de
    comillas. ✅ Comprobado sobre `archivo/catalogo.csv` el 11-sep-2026:
    2.583 filas, y su `visto` más nuevo es el día en curso.

    Devuelve `None` si el fichero no declara ninguna fecha legible. ⚠️ Y eso
    NO significa «está bien»: significa «no lo estoy vigilando», que es
    justo el fallo mudo que esta alarma existe para evitar. Quien llama avisa.
    """
    mejor = None
    try:
        with io.open(ruta, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                v = (fila.get(columna) or "").strip()
                # Formato AAAA-MM-DD, comparable como texto.
                if len(v) == 10 and v[4] == "-" and v[7] == "-":
                    if mejor is None or v > mejor:
                        mejor = v
    except (OSError, UnicodeDecodeError, csv.Error):
        return None
    return mejor


def consulta_github(camino, token=None):
    """Un GET a la API de GitHub. Devuelve el JSON.

    ⚠️ Se escribe aparte y NO se reaprovecha el `api()` de `publicar()`, que
    es casi igual. No es descuido: `publicar()` habla por red y **no lo cubre
    ninguna prueba** —no se puede sin credencial—, y refactorizarlo para
    compartir ocho lineas arriesga justo lo unico que hace util al vigilante:
    poder abrir la incidencia. Duplicar aqui es la opcion barata; tocar alli,
    la cara.
    """
    import urllib.request
    cabeceras = {"Accept": "application/vnd.github+json",
                 "User-Agent": "vigilante-bess"}
    if token:
        cabeceras["Authorization"] = "Bearer " + token
    pet = urllib.request.Request("https://api.github.com" + camino,
                                 headers=cabeceras, method="GET")
    with urllib.request.urlopen(pet, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def alarma_vigilante_mudo(repo, token=None, flujo="vigilante.yml",
                          horas=HORAS_VIGILANTE_MUDO, ahora=None,
                          consultar=None):
    """¿Ha corrido el vigilante CON ÉXITO en las ultimas `horas`? (A19)

    ⚠⚠ QUIEN LLAMA A ESTO NO ES EL VIGILANTE, y es la mitad del asunto. La
    llama `registro.py`, que corre una vez al dia desde OTRO workflow. Un
    vigilante que se vigila a si mismo no vigila nada: si esta caido, no
    pregunta, y su silencio vuelve a significar las dos cosas.

    ⚠️ Se mide sobre `updated_at` —cuando la pasada TERMINO— y no sobre
    `created_at`: una pasada encolada y nunca ejecutada no cuenta como que el
    vigilante miró.

    ⚠️⚠️ **«HA CORRIDO» NO ES «HA TERMINADO»: TIENE QUE HABER TERMINADO
    BIEN** (v1.07). Hasta la v1.06 se pedia `status=completed` y solo se
    miraba `updated_at`, asi que **una pasada que termino en `failure` contaba
    como vigilancia**: el vigilante podia llevar dias fallando en cada
    ejecucion y A19 lo daba por vivo. Es el mismo fallo que A19 existe para
    cerrar —silencio leido como «todo bien»— cometido dentro de A19.

    Ahora se piden las ultimas pasadas completadas y se busca la mas reciente
    con `conclusion == "success"`. Si la ultima termino mal, se dice **cual y
    cuantas**: «lleva 3 pasadas fallando» y «no ha corrido» son averias
    distintas y se arreglan distinto.

    `horas` = 9 **desde la v1.07**, y el cambio va con su medicion. ✅ Sobre
    47 huecos entre pasadas, el maximo observado fue **5,89 h** —a SIETE
    MINUTOS del umbral de 6 h que habia—, y ✅ **27 de 31 ranuras `schedule`
    entregadas (87 %)** con retraso maximo de **127 min**. O sea: 6 h no era
    «el doble de la cadencia», era el borde del ruido normal, y GitHub se
    salta una ranura de cada ocho. Con 9 h queda margen sobre el peor hueco
    medido mas el peor retraso, sin tardar un dia en enterarse — y sin caer en
    la trampa 7, que es un aviso que salta siempre.

    ⚠️⚠️ **Y ESAS 9 h NO LLEGARON A PRODUCCIÓN HASTA LA v1.09.** `registro.py`,
    que es quien llama, pasaba `horas=6.0` desde su propia línea de órdenes, así
    que el defecto de aquí no se usaba nunca. Hoy el umbral es la constante
    `HORAS_VIGILANTE_MUDO`, y `registro.py` v1.04 la lee.

    ⚠️ **Los fallos de red NO se tragan.** Si la consulta revienta, la
    excepcion sube: quien llama la enseña y deja la pasada en rojo, que es una
    señal visible. Tragarsela seria crear el fallo mudo que esto viene a
    cerrar (trampa 6: ningun `continue` mudo).

    Devuelve una `Incidencia` o `None`.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    consultar = consultar or consulta_github
    # ⚠️ 10 y no 1: con `per_page=1` solo se ve la ultima, y si esa fallo no
    # hay forma de saber si la anterior fue bien. Diez pasadas son ~30 h de
    # cadencia, suficiente para distinguir «una fallo» de «lleva dias».
    datos = consultar("/repos/%s/actions/workflows/%s/runs"
                      "?per_page=10&status=completed" % (repo, flujo), token)
    pasadas = datos.get("workflow_runs") or []

    if not pasadas:
        return Incidencia(
            "vigilante_mudo:%s" % flujo,
            "⚠️ El vigilante NO ha corrido NUNCA (`%s`)" % flujo,
            "La API de GitHub no devuelve ninguna pasada completada de "
            "`%s`.\n\n⚠️ Mientras eso sea cierto, **el archivo no esta "
            "vigilado por nadie**, y su silencio no significa que este bien: "
            "significa que no lo mira nadie." % flujo)

    # ⚠️ LA QUE CUENTA ES LA ULTIMA QUE TERMINO BIEN. Una pasada en `failure`
    # no ha vigilado nada, por muy reciente que sea.
    buenas = [p for p in pasadas if p.get("conclusion") == "success"]
    fallidas_seguidas = 0
    for p in pasadas:
        if p.get("conclusion") == "success":
            break
        fallidas_seguidas += 1

    if not buenas:
        ultima = pasadas[0].get("conclusion") or "sin conclusion"
        return Incidencia(
            "vigilante_mudo:%s" % flujo,
            "⚠️ Ninguna de las ultimas %d pasadas del vigilante termino bien "
            "(`%s`)" % (len(pasadas), flujo),
            "La mas reciente termino en **`%s`**, y en las %d que devuelve la "
            "API **no hay ni una** con `conclusion = success`.\n\n"
            "⚠️⚠️ El workflow se esta ejecutando, asi que por fuera parece "
            "vivo —hay pasadas, y son recientes—, pero **no esta vigilando "
            "nada**: cada una revienta antes de comprobar las alarmas. Es "
            "peor que estar parado, porque el calendario de Actions se ve "
            "verde de actividad.\n\n"
            "**Que mirar:** el registro de la ultima pasada en la pestaña "
            "Actions; lo mas tipico es una credencial caducada o un cambio de "
            "la API de GitHub." % (ultima, len(pasadas)))

    fin = buenas[0].get("updated_at") or ""
    try:
        cuando = dt.datetime.strptime(fin, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
    except ValueError:
        # ⚠️ Una fecha que no se entiende NO es «esta bien»: es que no se
        # puede saber, y eso se dice. Nunca se devuelve None por no entender.
        return Incidencia(
            "vigilante_mudo:%s" % flujo,
            "⚠️ No se puede fechar la ultima pasada del vigilante (`%s`)"
            % flujo,
            "La API devolvio `updated_at` = `%s`, que no se entiende.\n\n"
            "⚠️ No poder fechar la ultima pasada es no saber si el archivo "
            "esta vigilado." % fin)

    edad = (ahora - cuando).total_seconds() / 3600.0
    if edad <= horas:
        # ⚠️ Aunque haya una pasada buena dentro del plazo, si las MAS
        # RECIENTES fallaron hay que decirlo: el vigilante se esta degradando
        # y el aviso llega antes de que se quede mudo del todo.
        if fallidas_seguidas:
            return Incidencia(
                "vigilante_degradado:%s" % flujo,
                "⚠️ Las %d ultimas pasadas del vigilante han fallado (`%s`)"
                % (fallidas_seguidas, flujo),
                "La ultima que termino BIEN fue el **%s**, hace **%.1f h**, "
                "asi que todavia esta dentro del plazo de %.0f h y el archivo "
                "sigue vigilado.\n\n⚠️ Pero las **%d** posteriores han "
                "terminado en fallo. Si esto sigue, A19 pasara a decir que el "
                "vigilante esta mudo; esto es el aviso de antes.\n\n"
                "**Que mirar:** el registro de la ultima pasada en Actions."
                % (fin, edad, horas, fallidas_seguidas))
        return None
    return Incidencia(
        "vigilante_mudo:%s" % flujo,
        "⚠️ El vigilante lleva %.0f h sin vigilar (`%s`)" % (edad, flujo),
        "Su ultima pasada **con exito** termino el **%s**, hace **%.0f "
        "horas**, y su cadencia es de 3 h.\n\nCausas tipicas: el workflow "
        "desactivado a "
        "mano, GitHub desactivando los `schedule` por inactividad del "
        "repositorio, o pasadas que fallan sin que nadie las mire.\n\n"
        "⚠⚠ Mientras dure, **el archivo no esta vigilado**: las alarmas no se "
        "ejecutan, y su silencio se lee como «todo bien». Es exactamente el "
        "fallo mudo que el vigilante existe para cerrar, aplicado a el mismo."
        % (fin, edad))


def capturas_por_dia(raiz):
    """{fecha: [horas]} del índice, como cadenas «HHMM». Función pura."""
    ruta = os.path.join(raiz, "indice.csv")
    if not os.path.isfile(ruta):
        return {}
    dias = collections.defaultdict(list)
    with io.open(ruta, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            fecha = (fila.get("fecha") or "").strip()
            hora = (fila.get("hora") or "").strip()
            if fecha and hora.isdigit() and len(hora) == 4:
                dias[fecha].append(hora)
    return {d: sorted(h) for d, h in dias.items()}


def alarma_captura_critica(raiz, desde="1130", hasta="1200", dias_atras=30):
    """¿Se ha perdido la captura de las 11:5x? (B4, 12-sep-2026)

    ⚠️⚠️ NO ES UNA CAPTURA MÁS. La de las 11:5x de D−1 es **el horizonte de
    información entero** de Casandra: es la foto de lo que se sabía al cerrar
    las ofertas del diario, y la regla Q3 dice que una variable es la versión
    disponible a esa hora. Perderla no degrada un día, lo **invalida** para
    entrenar y para medir.

    ⚠️ Y HASTA HOY NO SE VEÍA. La alarma 1 mira la antigüedad de la ÚLTIMA
    captura, así que perder una intermedia no la despierta: el archivador
    captura ~14 veces al día, y con las siguientes llegando en hora el archivo
    parece al día. Peor: el hueco que deja perder la de las 11:5x medía
    **6,00 h exactas**, y la comparación era `> 6.0` — o sea que ni siquiera
    por antigüedad saltaba, por dos centésimas.

    ⚠️⚠️ SE ESCRIBE COMO IDENTIDAD Y NO COMO UMBRAL, que es lo que la casa
    manda preferir (trampa 10): **si un día tiene capturas DESPUÉS de la
    franja pero ninguna DENTRO, la de la franja se perdió**. No hay nada que
    calibrar, no depende del reloj de quien ejecuta ni de husos horarios, y un
    solo contraejemplo la desmiente.

    ⚠️ Y SE AUTOCALIBRA: si el archivo no tiene capturas en esa franja en
    NINGÚN día, esta alarma no aplica y devuelve `[]` — es lo que la hace
    inocua sobre el archivo del SAIH, que se captura a las 09:30, 14:00 y
    20:00 y nunca a las 11:5x. Sin esto saltaría todos los días en el SAIH,
    que es la trampa 7.

    ⚠️⚠️ LA FRANJA NO ES SIMÉTRICA, Y ESO ES LO QUE HAY QUE ENTENDER PARA NO
    «ARREGLARLA» MAL. El límite de arriba, las **12:00**, es DURO: es el cierre
    de ofertas del diario, y una captura posterior ya no dice lo que se sabía
    al ofertar. El de abajo es blando: una captura a las 11:35 es peor que una
    a las 11:50 —pierde quince minutos de información— pero **sigue valiendo**,
    porque es anterior al cierre.

    ✅ Calibrada sobre el archivo real el 12-sep-2026, 33 días: la captura del
    mediodía cae a las **11:50 en 25 días** y a las **11:51 en 6**; el resto se
    reparte entre 11:43 (2), 11:45, 11:48, 11:38, 11:32, 11:29, 11:22 y 11:01
    —los días iniciales, cuando se disparaba a mano—. Con la franja abierta a
    las 11:30 quedan dentro **33 de 33**; con 11:45 se escapaban 2 días que
    tenían captura válida, y habrían salido como pérdida sin serlo.

    Devuelve la lista de fechas a las que les falta.
    """
    dias = capturas_por_dia(raiz)
    if not dias:
        return []
    en_franja = {d: [h for h in hs if desde <= h < hasta]
                 for d, hs in dias.items()}
    # ¿aplica aquí? Si nunca hubo una, este archivo no captura a esa hora.
    if not any(en_franja.values()):
        return []

    faltan = []
    for fecha in sorted(dias)[-dias_atras:]:
        if en_franja.get(fecha):
            continue
        # ⚠️ Solo cuenta como PERDIDA si ese día siguió capturando después: si
        # no hay ninguna posterior, puede que el día aún no haya llegado a esa
        # hora, o que el archivo empiece ahí. No se acusa sin prueba.
        if any(h >= hasta for h in dias[fecha]):
            faltan.append(fecha)
    return faltan


FRACCION_M34 = 0.90        # ver `alarma_indicadores_perdidos`


def alarma_indicadores_perdidos(raiz, fraccion=FRACCION_M34, ultimas=1):
    """M34 · Un fichero puede traer 26 indicadores menos sin que nada lo note.

    ⚠️⚠️ LA UNIDAD DE VIGILANCIA ERA EL FICHERO, y ése es el hueco. Todas las
    alarmas de arriba preguntan «¿está el fichero?» y «¿ha cambiado?». Pero
    `esios_previsiones` es UN fichero que dentro trae CIENTO CATORCE
    indicadores: puede llegar puntual, pesar lo normal, cambiar cada día — y
    traer veintiséis series menos. Para el vigilante era una captura perfecta.

    El dato ya estaba escrito y nadie lo miraba: el manifiesto trae
    `indicadores_ok`, `indicadores_vacios`, `indicadores_fallidos` y
    `pedidos` en cada captura. Esto es solo mirarlo, que es lo que lo hacía
    «el caso más barato de cerrar» de la auditoría del 9-sep-2026.

    ⚠️ EL UMBRAL SE CALIBRA SOLO, Y AGRUPANDO POR `pedidos`. Un umbral
    absoluto no vale: ✅ medido sobre 448 capturas, `indicadores_ok` va de
    **94 a 835** porque hay dos clases de captura —la ligera pide ~138 y la
    completa 1.550—, y una cifra fija o no avisaría nunca o avisaría siempre.
    Agrupando por cuántos se pidieron, cada grupo es estrechísimo:

        pedidos= 138  n=261   ok 113..116  (mediana 114)
        pedidos= 143  n= 70   ok 113..129  (mediana 115)
        pedidos= 110  n= 43   ok  94.. 96  (mediana  94)
        pedidos=1550  n= 21   ok 777..835  (mediana 790)

    ✅ Con el corte en el **90 % de la mediana de su propio grupo**, las 448
    capturas del archivo pasan: **0 falsos positivos**. Y el caso que M34
    denuncia —26 indicadores menos sobre 114— da 77 %, muy por debajo del
    corte, así que se vería. Un umbral que no avisa de nada hoy y sí del caso
    que lo motivó es justo lo que se busca (trampa 7 por los dos lados).

    Devuelve `[(fuente, ruta, ok, mediana, pedidos)]` de las últimas capturas.
    """
    destino = raiz if os.path.isfile(os.path.join(raiz, "indice.csv")) \
        else os.path.join(raiz, "archivo")
    patron = os.path.join(destino, "*", "*", "*", "*", "manifiesto.json")
    ficheros = sorted(glob.glob(patron))
    if not ficheros:
        return []

    # (fuente, pedidos) -> [ok]; y la última captura de cada fuente aparte
    historia = collections.defaultdict(list)
    recientes = {}
    for ruta in ficheros:
        try:
            with io.open(ruta, encoding="utf-8") as f:
                fuentes = (json.load(f).get("fuentes") or {})
        except Exception:
            # ⚠️ Un manifiesto ilegible no tumba la alarma NI se cuenta como
            # sano: simplemente no aporta. Lo vigila la alarma de antigüedad.
            continue
        for nombre, ficha in fuentes.items():
            ok = ficha.get("indicadores_ok")
            ped = ficha.get("pedidos")
            if not isinstance(ok, int) or not isinstance(ped, int) or not ped:
                continue
            historia[(nombre, ped)].append(ok)
            recientes.setdefault(nombre, []).append((ruta, ok, ped))

    avisos = []
    for nombre, lista in recientes.items():
        for ruta, ok, ped in lista[-ultimas:]:
            valores = sorted(historia[(nombre, ped)])
            # ⚠️ Con menos de 5 capturas del mismo tamaño no hay mediana que
            # merezca el nombre: no se avisa, y no se da por bueno tampoco —
            # simplemente no se puede decir nada todavía.
            if len(valores) < 5:
                continue
            mediana = valores[len(valores) // 2]
            if ok < fraccion * mediana:
                avisos.append((nombre, ruta, ok, mediana, ped))
    return avisos


def alarma_sustituto_muerto(raiz, ahora=None, horas=48.0):
    """El fichero al que se mudó una fuente retirada, ¿sigue vivo?

    ⚠️ ES LA MITAD QUE HACE HONESTA A `RETIRADAS`. Saltarse una fuente
    retirada sin comprobar su sustituto sería silenciar el nombre viejo y
    perder el dato sin que nadie avise — la trampa 6 de la casa, un fallo
    mudo, creado por la propia defensa contra los falsos positivos.

    ⚠⚠ **NO SE MIRA EL `mtime`, Y ÉSE FUE EL FALLO** (A17, corregido en la
    v1.05). `actions/checkout` reescribe la fecha de modificación de todos
    los ficheros al clonar, así que EN EL RUNNER la edad valía siempre ~0 y
    `edad > horas` **no podía cumplirse jamás**. Se ejecutaba cada 3 horas,
    no daba error, y su silencio no significaba nada. Es la trampa 10 de la
    casa: un METADATO que el entorno reescribe, en vez de un DATO que el
    fichero declara.

    Ahora se lee la fecha que el archivador ESCRIBE DENTRO del fichero —la
    columna que declare `RETIRADAS[...]["fecha_por"]`—, que es contenido y
    por tanto sobrevive al checkout.

    ⚠️ La fecha declarada es de día y sin hora, así que la edad se mide desde
    su medianoche UTC: con el umbral de 48 h la alarma salta cuando el
    sustituto lleva **dos días** sin verse. `horas` es generoso a propósito,
    porque lo que se detecta es que dejó de tocarse, no un retraso de unas
    horas.

    Tercer elemento de cada aviso: `None` si el fichero no existe, la cadena
    `"sin_fecha"` si existe y no se puede fechar, y las horas si está viejo.
    """
    avisos = []
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    base = raiz if os.path.isfile(os.path.join(raiz, "indice.csv")) \
        else os.path.join(raiz, "archivo")
    # ⚠️ El nombre de la carpeta raíz, para saber qué retiradas son de ESTE
    # archivo. `archivo_saih/` no tiene ninguna, y sin este filtro heredaría
    # las de `archivo/` y avisaría de que le falta un `catalogo.csv` que nunca
    # debió tener. Ver el comentario de `RETIRADAS`.
    nombre = os.path.basename(os.path.normpath(base))
    for viejo, d in sorted(RETIRADAS.items()):
        if d.get("archivo", "archivo") != nombre:
            continue
        p = os.path.join(base, d["sustituto"])
        if not os.path.isfile(p):
            avisos.append((viejo, d["sustituto"], None))
            continue
        modo = d.get("fecha_por", "")
        columna = modo.split(":", 1)[1] if modo.startswith("columna:") else None
        fecha = fecha_declarada_dentro(p, columna) if columna else None
        if fecha is None:
            avisos.append((viejo, d["sustituto"], "sin_fecha"))
            continue
        visto = dt.datetime.strptime(fecha, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc)
        edad = (ahora - visto).total_seconds() / 3600.0
        if edad > horas:
            avisos.append((viejo, d["sustituto"], edad))
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


def comprobar(raiz, ahora=None, token_aemet=None, simulacro=None,
              umbral_horas=None):
    """Devuelve la lista de incidencias. Función PURA: no habla con la red.

    `simulacro` fuerza una de las condiciones sin tocar un solo fichero, que es
    la prueba de disparo de F−1: el archivo sigue sano y lo que cambia es la
    regla, no el dato.

    ⚠️ `umbral_horas` existe desde el 9-sep-2026 porque **no todos los archivos
    tienen la misma cadencia**. `UMBRAL_HORAS = 6` está bien para el
    archivador, que captura ~14 veces al día. El archivo del SAIH se captura
    **tres veces al día** desde la máquina de Xevi —09:30, 14:00 y 20:00—, así
    que su hueco nocturno es de **13,5 h**: con el umbral de 6 h saltaría la
    alarma TODAS LAS MAÑANAS, y un aviso que salta siempre deja de ser un
    aviso (trampa 7). Sin valor, se usa la constante de siempre.
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
    umbral = 0.0 if simulacro == "antiguedad" \
        else (UMBRAL_HORAS if umbral_horas is None else umbral_horas)
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
    # ⚠️⚠️ AQUÍ HABÍA UN `io.open()` SIN RED, y era el peor fallo posible de
    # este programa. Si `ultimo.json` no está, la excepción se lleva por delante
    # la función entera: **no se evalúa ninguna de las seis alarmas y no se
    # publica nada**. O sea que la avería más tonta —un fichero que falta—
    # apagaba el vigilante completo, en silencio, dejándolo en rojo.
    #
    # Salió al conectar `archivo_saih`, que escribe `manifiesto.json` en la
    # carpeta del día pero no escribía `ultimo.json` en la raíz. Se arregla por
    # los dos lados: `saih_captura.py` v1.01 ya lo escribe, y aquí su ausencia
    # pasa a ser UNA INCIDENCIA MÁS en vez de una excepción.
    ruta_ultimo = os.path.join(raiz, "ultimo.json")
    ultimo, ausente = None, None
    if not os.path.isfile(ruta_ultimo):
        ausente = "no existe"
    else:
        try:
            with io.open(ruta_ultimo, encoding="utf-8") as f:
                ultimo = json.load(f)
        except ValueError as e:
            ausente = "existe pero no es JSON válido (%s)" % e
    fuentes = (ultimo or {}).get("fuentes") or {}

    if ausente:
        incidencias.append(Incidencia(
            "sin_ultimo",
            "%s⚠️ Falta `ultimo.json` en `%s`" % (marca("antiguedad"), raiz),
            "El vigilante necesita `%s` para saber qué fuentes trajo la última "
            "captura, y ese fichero **%s**.\n\n"
            "⚠️ Hasta la v1.04 esto no era una incidencia sino una EXCEPCIÓN, "
            "que dejaba al vigilante sin evaluar ninguna alarma. Ahora se "
            "avisa y las demás comprobaciones siguen.\n\n"
            "**Qué mirar:** que el capturador de este archivo escriba "
            "`ultimo.json` en su raíz, con el mismo contenido que el "
            "`manifiesto.json` de la captura."
            % (ruta_ultimo, ausente)))
    elif not fuentes:
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

        # ---- 4.bis · la memoria larga (v1.08, N-operacion-11) -------------
        largas = alarma_desaparecido_larga(raiz, capturas, info)
        if simulacro == "desaparecido_largo":
            largas = list(largas) + [("__simulacro__", len(capturas), capturas[0][0])]
        for k, n_ventana, ultima in largas:
            es_sintetica = (k == "__simulacro__")
            incidencias.append(Incidencia(
                "desaparecido_largo:%s" % k,
                "%s⚠️ La fuente `%s` lleva más de %d capturas sin aparecer"
                % ("[SIMULACRO] " if es_sintetica else "", k, n_ventana),
                "`%s` existió en el archivo (última vez: `%s`) y **no aparece en "
                "ninguna de las %d capturas de la ventana**. La alarma 4 no la "
                "ve: solo mira fuentes que hayan aparecido dentro de la ventana, "
                "y esta avería es más vieja que la ventana entera.\n\n⚠️ Si es "
                "una retirada a propósito, va en `RETIRADAS` con su sustituto; "
                "si no, el dato se está perdiendo desde `%s`."
                % (k, ultima, n_ventana, ultima)))

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

    # --- 6: el SUSTITUTO de una fuente retirada dejó de tocarse ------------
    # ⚠️ Sin esto, `RETIRADAS` sería una lista de silencio y el dato podría
    # perderse sin que nadie avisara.
    # ⚠⚠ El simulacro la FUERZA con un umbral imposible, como hacen las
    # demás. Hasta la v1.05 esta llamada iba sin `horas`, así que la opción
    # `sustituto` se aceptaba, ponía la marca `[SIMULACRO]` y **no probaba
    # nada** — y encima no estaba en el desplegable del workflow, así que
    # nadie la pulso nunca para enterarse.
    for viejo, sust, edad in alarma_sustituto_muerto(
            raiz, ahora, horas=-1.0 if simulacro == "sustituto" else 48.0):
        incidencias.append(Incidencia(
            "sustituto:%s" % sust,
            "%s⚠️ `%s` sustituyó a `%s` y %s"
            % (marca("sustituto"), sust, viejo,
               "NO EXISTE" if edad is None
               else "no declara ninguna fecha legible"
               if isinstance(edad, str)
               else "lleva %.0f h sin verse" % edad),
            "La fuente `%s` está declarada como RETIRADA A PROPÓSITO en "
            "`RETIRADAS`, y su dato se mudó a `%s`.\n\n%s\n\n⚠️ Ese fichero "
            "**%s**, así que el dato se ha perdido de verdad: la alarma 4 no "
            "avisa de la fuente vieja precisamente porque se declaró "
            "retirada, y sin esta comprobación el fallo sería mudo."
            % (viejo, sust, RETIRADAS[viejo]["motivo"],
               "no existe" if edad is None
               else "existe pero no declara ninguna fecha legible, o sea que "
               "NO SE ESTÁ VIGILANDO" if isinstance(edad, str)
               else "lleva %.0f horas sin verse" % edad)))

    # ---- 9. M35 · degradación PARCIAL de una familia, persistente (v1.08) --
    degradadas = alarma_degradacion_parcial(raiz)
    if simulacro == "degradacion" and not degradadas:
        degradadas = [("__simulacro__", M35_RACHA, M35_MINIMO_EN_VENTANA,
                       M35_VENTANA, ["(ninguna)"], "(ninguna)")]
    for fam, racha, cuantas, de, caidas, etiqueta in degradadas:
        incidencias.append(Incidencia(
            "degradacion:%s" % fam,
            "%s⚠️ La familia `%s` tiene parte de sus fuentes caídas de forma "
            "persistente (%d seguidas; %d de las últimas %d)"
            % (marca("degradacion"), fam, racha, cuantas, de),
            "La familia `%s` no está muda —eso lo vería la alarma 2— pero lleva "
            "**%d capturas seguidas** con alguna fuente en FALLO, VACIO o "
            "PARCIAL, y **%d de las últimas %d** en ese estado.\n\n"
            "- Última captura parcial: `%s`\n- Fuentes caídas en ella: %s\n\n"
            "Umbrales calibrados sobre el archivo real (13-sep-2026, 466 "
            "capturas): racha ≥ %d o ≥ %d en %d; la racha máxima observada era "
            "3 y el máximo en 24 seguidas 3, así que hoy no salta en falso. "
            "⚠️ La captura de las 11:5x PARCIAL por 429 de AEMET (rachas de 1) "
            "no la caza esta alarma: la arregla el archivador v3.18 con el "
            "reintento diferido."
            % (fam, racha, cuantas, de, etiqueta, ", ".join("`%s`" % c for c in caidas),
               M35_RACHA, M35_MINIMO_EN_VENTANA, M35_VENTANA)))

    # ---- 8. M34 · indicadores perdidos DENTRO de un fichero (v1.07) ------
    perdidos = alarma_indicadores_perdidos(raiz)
    if simulacro == "indicadores" and not perdidos:
        perdidos = [("__simulacro__", "(ninguna)", 0, 114, 138)]
    for nombre, ruta, ok, mediana, ped in perdidos:
        incidencias.append(Incidencia(
            "indicadores:%s" % nombre,
            "%s⚠️ `%s` ha traído %d indicadores y lo normal son %d"
            % (marca("indicadores"), nombre, ok, mediana),
            "La última captura de `%s` trae **%d** indicadores de los **%d** "
            "pedidos, y la mediana de las capturas que piden lo mismo es "
            "**%d**.\n\n⚠️⚠️ El fichero ESTÁ, pesa lo normal y ha cambiado, "
            "así que ninguna de las otras alarmas lo ve: miran el fichero, y "
            "esto se pierde **dentro** de él.\n\n"
            "- Captura: `%s`\n\n"
            "El umbral no es fijo: es el **%.0f %%** de la mediana de las "
            "capturas del mismo tamaño, calculada del propio archivo. ✅ Con "
            "él, las 448 capturas de hoy pasan sin avisar."
            % (nombre, ok, ped, mediana, ruta, FRACCION_M34 * 100)))

    # ---- 7. la captura de las 11:5x (v1.07) ------------------------------
    # ⚠️ Va al final y con su propia clave para no pisar a la alarma 1: son
    # averías distintas —«el archivo está parado» frente a «el archivo está al
    # día y le falta LA captura que importa»— y se arreglan distinto.
    perdidas = alarma_captura_critica(raiz)
    if simulacro == "captura_critica" and not perdidas:
        perdidas = ["__simulacro__"]
    if perdidas:
        incidencias.append(Incidencia(
            "captura_critica",
            "%s⚠️ Falta la captura de las 11:5x en %d día(s)"
            % (marca("captura_critica"), len(perdidas)),
            "Días sin captura en la franja **11:45-12:00** que sí tienen "
            "capturas posteriores: %s.\n\n"
            "⚠️⚠️ **Esa captura es el horizonte de información entero**: es la "
            "foto de lo que se sabía al cerrar las ofertas del diario, y la "
            "regla Q3 dice que una variable es la versión disponible a esa "
            "hora. Un día sin ella no se puede usar para entrenar ni para "
            "medir, y **no se puede recuperar**: las previsiones que había a "
            "esa hora ya no las sirve nadie.\n\n"
            "⚠️ La alarma 1 no lo ve, y no es un descuido suyo: mira la "
            "antigüedad de la ÚLTIMA captura, así que con las siguientes "
            "llegando en hora el archivo parece al día. El hueco que deja "
            "perder ésta mide **6,00 h exactas** y el umbral era `> 6.0`."
            % ", ".join("`%s`" % d for d in perdidas)))

    return incidencias


# ============================================================================
# PUBLICACIÓN — la única parte que habla con la red
# ============================================================================

# Marcadores invisibles en los comentarios. Van en HTML por el mismo motivo
# que la clave en el cuerpo: no se ven al leer y sobreviven a que alguien edite
# el texto.
MARCA_RECUPERADA = "<!-- vigilante: recuperada -->"
MARCA_RECAIDA = "<!-- vigilante: recaida -->"


def transiciones(claves_ahora, estado_por_issue):
    """Qué incidencias han CAMBIADO de estado desde la última pasada.

    `estado_por_issue` es {clave: ultimo_marcador} donde el marcador es
    `MARCA_RECUPERADA`, `MARCA_RECAIDA` o None si nunca se comentó.

    Devuelve (recuperadas, recaidas): las que estaban fallando y ya no, y las
    que se habían recuperado y vuelven a fallar.

    ⚠️ SOLO SE COMENTA EN LOS CAMBIOS. Un comentario cada 3 horas diciendo
    «sigue fallando» sería la trampa 7 por el lado del volumen: al tercer día
    nadie leería la incidencia. Lo que falta hoy no es repetición, es saber
    **cuándo dejó de arder**.
    """
    recuperadas, recaidas = [], []
    for clave, ultimo in sorted(estado_por_issue.items()):
        falla_ahora = clave in claves_ahora
        if not falla_ahora and ultimo != MARCA_RECUPERADA:
            recuperadas.append(clave)
        elif falla_ahora and ultimo == MARCA_RECUPERADA:
            recaidas.append(clave)
    return recuperadas, recaidas


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


def publicar(incidencias, repo, token, etiqueta="vigilante",
             asignar_a=ASIGNAR_A):
    """Abre una issue por incidencia, si no hay ya una abierta con su clave.

    ⚠️⚠️ EL DEFECTO ES `ASIGNAR_A`, NO `None`, DESDE LA v1.07, y el motivo es
    un fallo que se vio en producción: el 12-sep-2026 la incidencia **#15**
    —la primera vez que A19 saltó de verdad— se abrió **sin asignado** y no le
    llegó a nadie. La causa era que `registro.py` llamaba a esta función sin
    ese argumento, y el defecto `None` significaba «no asignes».

    «No asignar» **nunca** es lo que se quiere en producción: una issue sin
    asignado solo la ve quien esté *watching* del repositorio. Con el defecto
    callado, el fallo estaba esperando a cualquiera que llamase sin acordarse
    — y llamó. Quien quiera de verdad no asignar, que pase `asignar_a=None`
    y se le vea escribirlo.

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
    numero_de = {}
    for issue in abiertas:
        cuerpo = issue.get("body") or ""
        for linea in cuerpo.splitlines():
            if linea.startswith("<!-- clave:"):
                clave = linea.split(":", 1)[1].strip().rstrip("->").strip()
                ya.add(clave)
                numero_de[clave] = issue.get("number")

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

    # --- LOS AVISOS DE CAMBIO DE ESTADO ------------------------------------
    # ⚠️ Sin esto, una incidencia abierta dice que empezó un incendio y no dice
    # si sigue ardiendo. Xevi cerró la #6 el 8-sep-2026 sin que nada le dijera
    # que ENTSO-E había vuelto; había vuelto, pero por casualidad de horario.
    claves_ahora = {i.clave for i in incidencias}
    estado = {}
    for clave, numero in numero_de.items():
        # ⚠️ Solo el ÚLTIMO comentario decide: una incidencia puede haberse
        # recuperado, recaído y recuperado otra vez, y lo que importa es dónde
        # está ahora, no su historia.
        try:
            coms = api("/repos/%s/issues/%d/comments?per_page=100"
                       % (repo, numero))
        except Exception:
            # ⚠️ Nada de continue mudo: se dice y se sigue con las demás.
            print("  ⚠️ no se pudieron leer los comentarios de la #%d" % numero)
            estado[clave] = None
            continue
        ultimo = None
        for c in coms:
            cuerpo = c.get("body") or ""
            if MARCA_RECUPERADA in cuerpo:
                ultimo = MARCA_RECUPERADA
            elif MARCA_RECAIDA in cuerpo:
                ultimo = MARCA_RECAIDA
        estado[clave] = ultimo

    recuperadas, recaidas = transiciones(claves_ahora, estado)
    ahora_txt = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for clave in recuperadas:
        api("/repos/%s/issues/%d/comments" % (repo, numero_de[clave]),
            {"body": "✅ **Recuperada** el %s. El vigilante ya no detecta esta "
                     "condición.\n\n⚠️ La incidencia **NO se cierra sola**: "
                     "cerrarla es tu decisión. Este aviso existe porque una "
                     "incidencia abierta decía que empezó un incendio y no "
                     "decía si seguía ardiendo.\n\n%s"
                     % (ahora_txt, MARCA_RECUPERADA)})
        print("  ✅ comentada la recuperación de `%s` (#%d)"
              % (clave, numero_de[clave]))

    for clave in recaidas:
        api("/repos/%s/issues/%d/comments" % (repo, numero_de[clave]),
            {"body": "⚠️ **Vuelve a fallar** el %s, después de haberse dado "
                     "por recuperada.\n\nUna avería que va y viene suele ser "
                     "peor que una constante: se cierra en cuanto se mira y "
                     "vuelve cuando nadie está delante.\n\n%s"
                     % (ahora_txt, MARCA_RECAIDA)})
        print("  ⚠️ comentada la RECAÍDA de `%s` (#%d)"
              % (clave, numero_de[clave]))

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
            # ⚠️ El escenario tiene que parecerse al archivo REAL, y desde el
            # 5-sep-2026 un archivo real tiene `catalogo.csv` —ahí se mudó el
            # catálogo de previsiones—. Sin este fichero la alarma 6 avisaba,
            # con razón, de que el sustituto no existe.
            #
            # ⚠️⚠️ Y se arregla AQUÍ, no en la alarma. La tentación era ponerle
            # a la alarma una guarda del tipo «si no hay capturas, no avises»,
            # y eso habría silenciado en producción el peor caso posible —que
            # el archivo entero haya desaparecido— para que una prueba dejara
            # de quejarse. Criterio de Xevi, 8-sep-2026: «es mejor una alarma
            # duplicada que ninguna alarma».
            with io.open(os.path.join(tmp, "catalogo.csv"), "w",
                         encoding="utf-8") as f:
                f.write("id,grupo,nombre,visto\n1,x,y,2026-09-07\n")

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


    print("\n-- avisos de recuperación y recaída --------------------------")
    # ⚠️ La primera de todas: que el camino SIN incidencias llegue a publicar.
    # Sin esto, el aviso de recuperación solo salía si algo seguía fallando.
    import inspect
    fuente_main = inspect.getsource(main)
    trozo = fuente_main.split("if not incidencias:")[1].split("if a.publicar:")[0]
    # ⚠️ Se quitan los COMENTARIOS antes de mirar. La primera versión de esta
    # prueba buscaba el texto «return 0» y lo encontraba dentro del comentario
    # que explica el arreglo — o sea, miraba la forma y no el fondo, que es
    # justo el fallo que viene a evitar.
    codigo = "\n".join(l for l in trozo.splitlines()
                       if not l.strip().startswith("#"))
    comprobar_que("return 0" not in codigo,
                  "⚠️ sin incidencias NO se sale antes de publicar(): el aviso "
                  "de recuperación tiene que salir justo cuando todo va bien")
    comprobar_que(transiciones({"a"}, {"a": None}) == ([], []),
                  "sigue fallando y nunca se comentó: no se dice nada")
    comprobar_que(transiciones(set(), {"a": None}) == (["a"], []),
                  "⚠️ dejó de fallar: se avisa de la RECUPERACIÓN")
    comprobar_que(transiciones(set(), {"a": MARCA_RECUPERADA}) == ([], []),
                  "⚠️ ya se avisó de la recuperación: NO se repite cada 3 h")
    comprobar_que(transiciones({"a"}, {"a": MARCA_RECUPERADA}) == ([], ["a"]),
                  "⚠️ vuelve a fallar tras recuperarse: se avisa de la RECAÍDA")
    comprobar_que(transiciones({"a"}, {"a": MARCA_RECAIDA}) == ([], []),
                  "y la recaída tampoco se repite")
    comprobar_que(transiciones(set(), {"a": MARCA_RECAIDA}) == (["a"], []),
                  "tras una recaída, la siguiente recuperación SÍ se avisa")
    comprobar_que(transiciones({"a", "b"}, {}) == ([], []),
                  "sin incidencias abiertas no hay transiciones que comentar")

    print("\n-- el silenciador está desactivado ---------------------------")
    comprobar_que(MINIMO_PRESENCIAS <= 1,
                  "⚠️ MINIMO_PRESENCIAS está en 1: medido que con 1, 3, 10 o "
                  "20 salen las mismas 5 incidencias, así que silenciaba sin "
                  "aportar")
    rarita = [("c%02d" % i, {"rara": "h%d" % i} if i < 5 else {})
              for i in range(200)]
    # con intervalo 40 el umbral es 120, y 120 < 200: la alarma SÍ puede verla
    comprobar_que(any(a[0] == "rara"
                      for a in alarma_desaparecido(rarita,
                                                   intervalos(rarita))),
                  "⚠️ una fuente vista solo 5 veces YA puede disparar: antes "
                  "el mínimo de 20 la dejaba muda para siempre")

    print("\n-- RETIRADAS y su sustituto ---------------------------------")
    comprobar_que(all("sustituto" in d and "motivo" in d
                      for d in RETIRADAS.values()),
                  "⚠️ toda retirada declara sustituto y motivo: sin eso sería "
                  "una lista de silencio")
    retirada = [("c%02d" % i,
                 {"esios_catalogo_previsiones": "h"} if i < 20 else {"otra": "g"})
                for i in range(60)]
    comprobar_que(not alarma_desaparecido(retirada, intervalos(retirada)),
                  "una fuente RETIRADA no dispara la alarma 4")
    with tempfile.TemporaryDirectory() as base4:
        # ⚠️ La raíz se llama `archivo` a propósito, y desde la v1.04 hace
        # falta: `RETIRADAS` declara a qué archivo pertenece cada entrada, y el
        # filtro compara con el NOMBRE de la carpeta raíz. Estas tres pruebas
        # usaban el temporal a pelo —`tmp4hs73k`— y empezaron a fallar al
        # añadirlo. No era un falso positivo del banco: era el banco diciendo
        # que la regla nueva depende del nombre de la carpeta, que es cierto y
        # conviene tener escrito.
        tmp4 = os.path.join(base4, "archivo")
        os.makedirs(tmp4)
        with io.open(os.path.join(tmp4, "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("fecha,hora,ruta\n")
        comprobar_que(len(alarma_sustituto_muerto(tmp4)) == 1,
                      "⚠️ si el sustituto NO EXISTE, la alarma 6 avisa")

        cat = os.path.join(tmp4, "catalogo.csv")
        ahora = dt.datetime(2026, 9, 11, 12, 0, tzinfo=dt.timezone.utc)

        # ⚠️ v1.05 · un sustituto que existe pero NO se puede fechar avisa.
        # No poder fecharlo es no vigilarlo, y darlo por bueno sería el fallo
        # mudo que esta alarma existe para evitar. Antes de la v1.05 esto
        # pasaba por «recién escrito, no avisa».
        with io.open(cat, "w", encoding="utf-8") as f:
            f.write("id\n1\n")
        comprobar_que(len(alarma_sustituto_muerto(tmp4, ahora)) == 1,
                      "⚠️ un sustituto sin fecha legible AVISA: no poder "
                      "fecharlo es no vigilarlo")

        with io.open(cat, "w", encoding="utf-8") as f:
            f.write("id,visto\n1,2026-09-11\n")
        comprobar_que(not alarma_sustituto_muerto(tmp4, ahora),
                      "con `visto` del día en curso, no avisa")

        # ⚠⚠⚠ LA PRUEBA DE A17, Y ES LA QUE IMPORTA. Se fabrica en local lo
        # que hace `actions/checkout`: contenido VIEJO y `mtime` de AHORA. La
        # v1.04 miraba el `mtime` y habría dicho «fresco»; la v1.05 mira el
        # contenido y dice la verdad. Si esta prueba pasara con el código
        # viejo, no probaría nada.
        with io.open(cat, "w", encoding="utf-8") as f:
            f.write("id,visto\n1,2026-09-01\n")
        os.utime(cat, None)          # ← esto es el checkout
        fresco = (time.time() - os.path.getmtime(cat)) / 3600.0
        comprobar_que(fresco < 1.0,
                      "el fichero tiene `mtime` de hace %.2f h: para la v1.04 "
                      "estaba fresco" % fresco)
        avisos = alarma_sustituto_muerto(tmp4, ahora)
        comprobar_que(len(avisos) == 1 and avisos[0][2] > 48.0,
                      "⚠⚠ y aun así la v1.05 AVISA, porque su `visto` es del "
                      "1-sep: %s h" % (round(avisos[0][2]) if avisos else "—"))

        comprobar_que(len(alarma_sustituto_muerto(tmp4, ahora, horas=-1)) == 1,
                      "y con umbral imposible avisa igual (es lo que usa el "
                      "simulacro `sustituto`)")

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

    # ---- v1.04: los tres cambios que hacen posible vigilar DOS archivos ----
    # Los tres existen para lo mismo —que ninguna alarma salte siempre sobre el
    # archivo nuevo—, así que se prueban por su EFECTO, no por su forma.

    print("\n-- v1.04 · un `ultimo.json` que falta NO mata al vigilante ---")
    with tempfile.TemporaryDirectory() as tmp5:
        with io.open(os.path.join(tmp5, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            ahora_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
            f.write("2026-09-09,0930,%s,2,0,0,17.3,x/2026-09-09\n" % ahora_iso)
        # ⚠️ Antes de la v1.04 esta llamada lanzaba FileNotFoundError y el
        # vigilante no evaluaba NINGUNA alarma. La prueba es que ahora vuelve.
        claves = {i.clave for i in comprobar(tmp5)}
        comprobar_que("sin_ultimo" in claves,
                      "⚠️ sin `ultimo.json` avisa en vez de reventar")
        comprobar_que("sin_fuentes" not in claves,
                      "y no avisa además de «sin fuentes»: es una cosa, no dos")

    print("\n-- v1.04 · umbral de antigüedad por archivo -----------------")
    with tempfile.TemporaryDirectory() as tmp3:
        hace_13h = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=13.5)
        with io.open(os.path.join(tmp3, "indice.csv"), "w",
                     encoding="utf-8", newline="") as f:
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
            f.write("%s,%s,%s,2,0,0,17.3,x/%s\n"
                    % (hace_13h.strftime("%Y-%m-%d"),
                       hace_13h.strftime("%H%M"), hace_13h.isoformat(),
                       hace_13h.strftime("%Y-%m-%d")))
        # Un `ultimo.json` sano, para que lo único que se mida sea el umbral.
        with io.open(os.path.join(tmp3, "ultimo.json"), "w",
                     encoding="utf-8") as f:
            json.dump({"fuentes": {"saih_a": {"estado": "OK"},
                                   "saih_b": {"estado": "OK"}}}, f)
        claves_6 = {i.clave for i in comprobar(tmp3)}
        claves_30 = {i.clave for i in comprobar(tmp3, umbral_horas=30.0)}
        comprobar_que("antiguedad" in claves_6,
                      "con el umbral de 6 h, 13,5 h SÍ dispara (archivador)")
        comprobar_que("antiguedad" not in claves_30,
                      "⚠️ con 30 h NO dispara: es el hueco nocturno normal "
                      "del SAIH, y avisar de él sería la trampa 7")

    print("\n-- v1.04 · las retiradas son de UN archivo -------------------")
    with tempfile.TemporaryDirectory() as tmp4:
        # Un archivo que se llama `archivo_saih` y no tiene `catalogo.csv`.
        saih = os.path.join(tmp4, "archivo_saih")
        os.makedirs(saih)
        with io.open(os.path.join(saih, "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
        comprobar_que(alarma_sustituto_muerto(saih) == [],
                      "⚠️ el archivo del SAIH NO hereda las retiradas del "
                      "archivador (si no, incidencia abierta para siempre)")
        # Y el del archivador sí las mira: sin `catalogo.csv`, avisa.
        arch = os.path.join(tmp4, "archivo")
        os.makedirs(arch)
        with io.open(os.path.join(arch, "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
        comprobar_que(len(alarma_sustituto_muerto(arch)) == len(RETIRADAS),
                      "y el del archivador sí las mira, las %d"
                      % len(RETIRADAS))

    print("\n-- v1.06 · A19 · nadie vigila al vigilante -------------------")
    ah19 = dt.datetime(2026, 9, 11, 12, 0, tzinfo=dt.timezone.utc)

    def api_falsa(fin, inicio=None, conclusion="success", antes=()):
        """Una respuesta de la API con una pasada que terminó en `fin`.

        ⚠️ `conclusion` es EXPLÍCITA desde la v1.07 y por defecto «success»:
        hasta la v1.06 estas respuestas no llevaban el campo, y el código daba
        por vigilancia cualquier pasada terminada. `antes` son las pasadas MÁS
        RECIENTES que ésta (la API las devuelve de nueva a vieja).
        """
        pasada = {"updated_at": fin, "conclusion": conclusion}
        if inicio:
            pasada["created_at"] = inicio
        return lambda camino, token=None: {
            "workflow_runs": (list(antes) + [pasada]) if fin is not None
            else []}

    comprobar_que(
        alarma_vigilante_mudo("x/y", ahora=ah19,
                              consultar=api_falsa("2026-09-11T10:25:00Z"))
        is None,
        "una pasada de hace 1,6 h no avisa")

    inc19 = alarma_vigilante_mudo("x/y", ahora=ah19,
                                  consultar=api_falsa("2026-09-10T12:00:00Z"))
    comprobar_que(inc19 is not None and "24 h" in inc19.titulo,
                  "⚠️ 24 h sin correr SÍ avisa, y lo dice con su cifra")

    comprobar_que(
        alarma_vigilante_mudo("x/y", ahora=ah19, consultar=api_falsa(None))
        is not None,
        "⚠️ si no ha corrido NUNCA avisa: 0 pasadas no es «todo bien»")

    comprobar_que(
        alarma_vigilante_mudo("x/y", ahora=ah19,
                              consultar=api_falsa("no-es-una-fecha"))
        is not None,
        "⚠️ una fecha ilegible avisa: no poder fecharla es no saber")

    # ⚠️ Que mida cuándo TERMINÓ y no cuándo se encoló. Una pasada creada
    # hace 20 h y terminada hace 1 no significa que el vigilante llevara 20 h
    # sin mirar; medir `created_at` daría una alarma falsa cada vez que GitHub
    # encola, que es la trampa 7.
    comprobar_que(
        alarma_vigilante_mudo(
            "x/y", ahora=ah19,
            consultar=api_falsa("2026-09-11T11:00:00Z",
                                inicio="2026-09-10T16:00:00Z")) is None,
        "⚠️ mide `updated_at` (cuándo TERMINÓ), no `created_at`")

    # ⚠️ Y un fallo de red SUBE. Tragarlo crearía el fallo mudo que esto
    # viene a cerrar: quien pregunta y no puede, no sabe —no está bien—.
    def api_rota(camino, token=None):
        raise OSError("sin red")
    try:
        alarma_vigilante_mudo("x/y", ahora=ah19, consultar=api_rota)
        subio = False
    except OSError:
        subio = True
    comprobar_que(subio,
                  "⚠️ un fallo de red SUBE, no se traga (trampa 6)")

    # ---- v1.07 · «ha corrido» no es «ha terminado bien» -----------------
    # ⚠️⚠️ LA PRUEBA QUE EXIGE B4, y que FALLA con el código de la v1.06: una
    # pasada reciente que terminó en `failure` no ha vigilado nada, y la v1.06
    # la contaba como vigilancia porque solo miraba `updated_at`.
    inc_f = alarma_vigilante_mudo(
        "x/y", ahora=ah19,
        consultar=api_falsa("2026-09-11T11:00:00Z", conclusion="failure"))
    comprobar_que(inc_f is not None,
                  "⚠️⚠️ v1.07 · una pasada reciente en `failure` NO cuenta "
                  "como vigilancia (con la v1.06 esto daba «todo bien»)")

    # y el mensaje tiene que distinguir las dos averías
    comprobar_que(inc_f is not None and "termino bien" in inc_f.titulo,
                  "v1.07 · y lo dice por su nombre: ninguna terminó bien")

    # una pasada sin `conclusion` tampoco es un éxito demostrado
    comprobar_que(
        alarma_vigilante_mudo(
            "x/y", ahora=ah19,
            consultar=api_falsa("2026-09-11T11:00:00Z", conclusion=None))
        is not None,
        "⚠️ v1.07 · sin `conclusion` no consta que terminara bien, y lo que "
        "no consta no se supone")

    # DEGRADACIÓN: la última buena está dentro de plazo, pero las dos
    # posteriores fallaron. Avisa, y con otra clave para no pisar A19.
    fallo1 = {"updated_at": "2026-09-11T11:30:00Z", "conclusion": "failure"}
    fallo2 = {"updated_at": "2026-09-11T11:45:00Z", "conclusion": "failure"}
    inc_d = alarma_vigilante_mudo(
        "x/y", ahora=ah19,
        consultar=api_falsa("2026-09-11T10:25:00Z", antes=[fallo2, fallo1]))
    comprobar_que(inc_d is not None and inc_d.clave.startswith(
        "vigilante_degradado"),
        "⚠️ v1.07 · si las últimas pasadas fallan pero aún hay una buena "
        "dentro de plazo, avisa ANTES de quedarse mudo")
    comprobar_que(inc_d is not None and "2 ultimas" in inc_d.titulo,
                  "v1.07 · y dice cuántas llevan fallando")

    # ⚠️ Y la otra mitad: con todo bien, ni una cosa ni la otra. Sin esto, la
    # alarma nueva podría saltar siempre y nadie lo notaría (trampa 7).
    comprobar_que(
        alarma_vigilante_mudo(
            "x/y", ahora=ah19,
            consultar=api_falsa("2026-09-11T10:25:00Z")) is None,
        "⚠️ v1.07 · con la última pasada buena y reciente, NO avisa")

    # ---- v1.07 · la captura de las 11:5x --------------------------------
    print("\n-- v1.07 · M34 · indicadores perdidos dentro del fichero ----")
    with tempfile.TemporaryDirectory() as tmp:
        # ⚠️⚠️ EL `indice.csv` NO ES DECORADO. `alarma_indicadores_perdidos`
        # resuelve su destino asi: la raiz si tiene indice.csv dentro, y si no
        # `raiz/archivo`. Sin este fichero, la prueba apuntaba a
        # `tmp/archivo/archivo` —que no existe—, el glob no encontraba NINGUN
        # manifiesto y la alarma devolvia [] siempre. Las tres primeras
        # comprobaciones pasaban en VERDE SOBRE NADA, y solo se vio porque la
        # cuarta esperaba un aviso y no llegaba.
        os.makedirs(os.path.join(tmp, "archivo"), exist_ok=True)
        with io.open(os.path.join(tmp, "archivo", "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("fecha,hora,ruta,ok,vacio,fallo\n")

        def manifiesto(dia, hora, ok, pedidos=138, fuente="esios_previsiones"):
            d = os.path.join(tmp, "archivo", "2026", "09", dia, hora)
            os.makedirs(d, exist_ok=True)
            with io.open(os.path.join(d, "manifiesto.json"), "w",
                         encoding="utf-8") as f:
                json.dump({"fuentes": {fuente: {
                    "estado": "OK", "indicadores_ok": ok,
                    "pedidos": pedidos}}}, f)

        # seis capturas normales: 114 de 138
        for i, h in enumerate(["0850", "1150", "1450", "1750", "2050", "2350"]):
            manifiesto("2026-09-10", h, 114)
        comprobar_que(alarma_indicadores_perdidos(
            os.path.join(tmp, "archivo")) == [],
            "v1.07 · M34 · con los indicadores de siempre, no avisa")

        # ⚠️⚠️ LA QUE IMPORTA: el fichero llega, pesa lo normal y cambia, pero
        # trae 26 indicadores menos. Ninguna otra alarma lo ve.
        manifiesto("2026-09-11", "0850", 88)
        avisos = alarma_indicadores_perdidos(os.path.join(tmp, "archivo"))
        comprobar_que(len(avisos) == 1 and avisos[0][2] == 88,
                      "⚠️⚠️ v1.07 · M34 · 26 indicadores menos SÍ avisan, "
                      "aunque el fichero esté, pese lo normal y haya cambiado")

        # ⚠️ Y no se compara con capturas de OTRO tamaño: la completa pide
        # 1.550 y trae ~790, que con un umbral absoluto sería «se ha caído».
        manifiesto("2026-09-11", "1150", 790, pedidos=1550)
        avisos = alarma_indicadores_perdidos(os.path.join(tmp, "archivo"))
        comprobar_que(all(a[4] != 1550 for a in avisos),
                      "⚠️ v1.07 · M34 · una captura COMPLETA no se compara con "
                      "las ligeras: 790 de 1.550 es lo suyo, no una caída")

    with tempfile.TemporaryDirectory() as tmp2:
        os.makedirs(os.path.join(tmp2, "archivo"), exist_ok=True)
        with io.open(os.path.join(tmp2, "archivo", "indice.csv"), "w",
                     encoding="utf-8") as f:
            f.write("fecha,hora,ruta,ok,vacio,fallo\n")

        def m2(dia, hora, ok):
            d = os.path.join(tmp2, "archivo", "2026", "09", dia, hora)
            os.makedirs(d, exist_ok=True)
            with io.open(os.path.join(d, "manifiesto.json"), "w",
                         encoding="utf-8") as f:
                json.dump({"fuentes": {"x": {"indicadores_ok": ok,
                                             "pedidos": 138}}}, f)
        # ⚠️ Con pocas capturas NO se opina: tres no hacen una mediana, y
        # avisar con ellas sería inventarse una normalidad.
        m2("2026-09-10", "0850", 114)
        m2("2026-09-10", "1150", 114)
        m2("2026-09-10", "1450", 10)
        comprobar_que(alarma_indicadores_perdidos(
            os.path.join(tmp2, "archivo")) == [],
            "⚠️ v1.07 · M34 · con menos de 5 capturas del mismo tamaño no se "
            "opina: no hay mediana que merezca el nombre")

    print("\n-- v1.07 · la captura de las 11:5x --------------------------")
    with tempfile.TemporaryDirectory() as tmp:
        cab = ("fecha,hora,ejecucion_madrid,ejecucion_utc,version,modo,"
               "disparo,ok,vacio,fallo,omitida,parcial,kb_total,ruta,run_id\n")

        def indice(filas):
            with io.open(os.path.join(tmp, "indice.csv"), "w",
                         encoding="utf-8") as f:
                f.write(cab + "".join(
                    "%s,%s,,,v1,ligero,schedule,1,0,0,0,0,1,r,1\n" % (d, h)
                    for d, h in filas))

        # día completo: tiene la de las 11:50 -> nada que avisar
        indice([("2026-09-10", "0850"), ("2026-09-10", "1150"),
                ("2026-09-10", "1750")])
        comprobar_que(alarma_captura_critica(tmp) == [],
                      "v1.07 · con la captura de las 11:50, no avisa")

        # ⚠️ LA QUE IMPORTA: falta la del mediodía y el día siguió capturando.
        # Es el caso que la alarma 1 NO ve, porque el archivo queda al día.
        # ⚠️ El indice lleva DIAS BUENOS delante, y no es decorado: sin
        # ninguno, la alarma concluye —bien— que este archivo no captura a esa
        # hora y no aplica. La primera version de esta prueba no los tenia y
        # fallo por eso: el irreal era el caso de prueba, no el codigo.
        indice([("2026-09-08", "1150"), ("2026-09-09", "1150"),
                ("2026-09-11", "0850"), ("2026-09-11", "1750")])
        comprobar_que(alarma_captura_critica(tmp) == ["2026-09-11"],
                      "⚠️⚠️ v1.07 · si falta la del mediodía y hay capturas "
                      "POSTERIORES, se avisa (la alarma 1 no lo ve: el "
                      "archivo queda al día)")

        # ⚠️ Y la otra mitad: sin capturas posteriores NO se acusa. El día
        # puede no haber llegado a esa hora todavía.
        indice([("2026-09-10", "1150"), ("2026-09-11", "0850")])
        comprobar_que(alarma_captura_critica(tmp) == [],
                      "⚠️ v1.07 · sin capturas posteriores no se acusa: puede "
                      "que el día aún no haya llegado a esa hora")

        # el límite de arriba es DURO: las 12:01 ya es después del cierre
        indice([("2026-09-08", "1150"), ("2026-09-09", "1150"),
                ("2026-09-11", "1201"), ("2026-09-11", "1750")])
        comprobar_que(alarma_captura_critica(tmp) == ["2026-09-11"],
                      "⚠️ v1.07 · las 12:01 NO valen: el cierre de ofertas es "
                      "a las 12:00 y después ya no es lo que se sabía")

        # el de abajo es blando: las 11:35 son peores pero valen
        indice([("2026-09-10", "1135"), ("2026-09-10", "1750")])
        comprobar_que(alarma_captura_critica(tmp) == [],
                      "v1.07 · las 11:35 valen: son anteriores al cierre")

        # ⚠️ AUTOCALIBRADO: un archivo que NUNCA captura a esa hora —el del
        # SAIH, que va a 09:30, 14:00 y 20:00— no dispara nunca. Sin esto
        # saltaría todos los días, que es la trampa 7.
        indice([("2026-09-10", "0930"), ("2026-09-10", "1400"),
                ("2026-09-10", "2000"), ("2026-09-11", "0930"),
                ("2026-09-11", "1400")])
        comprobar_que(alarma_captura_critica(tmp) == [],
                      "⚠️ v1.07 · un archivo que nunca captura a esa hora (el "
                      "del SAIH) NO dispara: la alarma se autocalibra")

    print("\n-- v1.08 · los simulacros existen de verdad -------------------")
    import inspect as _inspect
    fuente_comprobar = _inspect.getsource(comprobar)
    for nombre in SIMULACROS:
        comprobar_que(('simulacro == "%s"' % nombre) in fuente_comprobar,
                      "el simulacro `%s` tiene su rama en comprobar()" % nombre)
    comprobar_que({"captura_critica", "indicadores", "degradacion",
                   "desaparecido_largo"} <= set(SIMULACROS),
                  "⚠️ v1.08 · las alarmas 7, 8, 9 y la memoria larga se pueden PULSAR")

    print("\n-- v1.08 · alarma 4 con memoria larga (N-operacion-11) -------")
    with tempfile.TemporaryDirectory() as tmp6:
        def _cap(fecha, hora, ficheros):
            carpeta = os.path.join(tmp6, "x", fecha, hora)
            os.makedirs(carpeta)
            for n in ficheros:
                with io.open(os.path.join(carpeta, n), "w", encoding="utf-8") as g:
                    g.write("dato\n")
            return "%s/x/%s/%s" % (os.path.basename(tmp6), fecha, hora)
        rutas = [_cap("2026-08-01", "1000", ["a.csv", "b.csv", "esios_catalogo_previsiones.csv"]),
                 _cap("2026-08-02", "1000", ["a.csv"]),
                 _cap("2026-08-03", "1000", ["a.csv"])]
        with io.open(os.path.join(tmp6, "indice.csv"), "w", encoding="utf-8", newline="") as f:
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
            ahora6 = dt.datetime.now(dt.timezone.utc).isoformat()
            for r in rutas:
                f.write("%s,%s,%s,1,0,0,1.0,%s\n" % (r.split("/")[2], r.split("/")[3], ahora6, r))
        caps2 = leer_capturas(tmp6, limite=2)[0]
        info2 = intervalos(caps2)
        largas = alarma_desaparecido_larga(tmp6, caps2, info2)
        comprobar_que([l[0] for l in largas] == ["b"],
                      "una fuente vista solo ANTES de la ventana sale por la memoria larga")
        comprobar_que(largas and largas[0][2] == "2026-08-01-1000",
                      "y dice cuándo se vio por última vez")
        comprobar_que(all(l[0] != "esios_catalogo_previsiones" for l in largas),
                      "una RETIRADA declarada no sale")
        caps3 = leer_capturas(tmp6, limite=3)[0]
        comprobar_que(alarma_desaparecido_larga(tmp6, caps3, intervalos(caps3)) == [],
                      "si la ventana contiene el archivo entero, la memoria larga calla "
                      "(la alarma 4 ya lo ve)")
        claves6 = {i.clave for i in comprobar(tmp6, simulacro="desaparecido_largo")}
        comprobar_que("desaparecido_largo:__simulacro__" in claves6,
                      "el simulacro `desaparecido_largo` fabrica su incidencia sintética")

    print("\n-- v1.08 · alarma 5 sin ningún cambio ------------------------")
    quietas = [("e%03d" % i, {"k": "misma"}) for i in range(CONGELADO_SIN_CAMBIO)]
    comprobar_que(alarma_congelado(quietas, intervalos(quietas)) == [("k", CONGELADO_SIN_CAMBIO, "e000")],
                  "presente %d capturas con la misma huella y sin un cambio: avisa" % CONGELADO_SIN_CAMBIO)
    pocas = quietas[:CONGELADO_SIN_CAMBIO - 1]
    comprobar_que(alarma_congelado(pocas, intervalos(pocas)) == [],
                  "con una menos, todavía no (el intervalo infinito antes no se miraba nunca)")

    print("\n-- v1.08 · M35, degradación parcial de una familia -----------")
    with tempfile.TemporaryDirectory() as tmp7:
        def _man(fecha, hora, fuentes):
            carpeta = os.path.join(tmp7, "x", fecha, hora)
            os.makedirs(carpeta)
            with io.open(os.path.join(carpeta, "manifiesto.json"), "w", encoding="utf-8") as g:
                json.dump({"fuentes": {k: {"estado": e} for k, e in fuentes.items()}}, g)
            return "%s/x/%s/%s" % (os.path.basename(tmp7), fecha, hora)
        filas7 = []
        for i in range(6):
            estado_b = "FALLO" if i >= 1 else "OK"          # 5 seguidas parcial
            filas7.append(_man("2026-09-1%d" % i, "1000",
                               {"x_a": "OK", "x_b": estado_b, "y_a": "OK", "y_b": "OK"}))
        with io.open(os.path.join(tmp7, "indice.csv"), "w", encoding="utf-8", newline="") as f:
            f.write("fecha,hora,ruta\n")
            for r in filas7:
                f.write("%s,%s,%s\n" % (r.split("/")[2], r.split("/")[3], r))
        deg = alarma_degradacion_parcial(tmp7)
        comprobar_que([d[0] for d in deg] == ["x"] and deg[0][1] == 5 and deg[0][4] == ["x_b"],
                      "5 capturas seguidas con x_b caída y x_a viva: la familia x sale, la y no")
        comprobar_que(alarma_degradacion_parcial(tmp7, racha_minima=6, minimo_en_ventana=6) == [],
                      "con los umbrales por encima de la racha, calla")
    with tempfile.TemporaryDirectory() as tmp8:
        carpeta = os.path.join(tmp8, "x", "2026-09-10", "1000")
        os.makedirs(carpeta)
        with io.open(os.path.join(carpeta, "manifiesto.json"), "w", encoding="utf-8") as g:
            json.dump({"fuentes": {"x_a": {"estado": "FALLO"}, "x_b": {"estado": "FALLO"}}}, g)
        with io.open(os.path.join(tmp8, "indice.csv"), "w", encoding="utf-8", newline="") as f:
            f.write("fecha,hora,ruta\n2026-09-10,1000,%s/x/2026-09-10/1000\n" % os.path.basename(tmp8))
        comprobar_que(alarma_degradacion_parcial(tmp8, racha_minima=1, minimo_en_ventana=1) == [],
                      "una familia MUDA entera no es parcial: eso es la alarma 2")
    with tempfile.TemporaryDirectory() as tmp9:
        with io.open(os.path.join(tmp9, "indice.csv"), "w", encoding="utf-8", newline="") as f:
            ahora_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            f.write("fecha,hora,ejecucion_utc,ok,vacio,fallo,kb_total,ruta\n")
            f.write("2026-09-13,0930,%s,2,0,0,17.3,x/2026-09-13\n" % ahora_iso)
        claves9 = {i.clave for i in comprobar(tmp9, simulacro="degradacion")}
        comprobar_que("degradacion:__simulacro__" in claves9,
                      "el simulacro `degradacion` fabrica su incidencia sintética")

    print("\n-- v1.04 · la etiqueta llega a la issue ---------------------")
    inc = Incidencia("x", "titulo", "cuerpo")
    comprobar_que(peticion_de_issue(inc, "vigilante-saih")["labels"]
                  == ["vigilante-saih"],
                  "⚠️ la etiqueta viaja hasta la petición: es lo único que "
                  "impide que un archivo cierre las alarmas del otro")

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
    # ⚠️⚠️ LA ETIQUETA ES LO QUE AÍSLA UN ARCHIVO DE OTRO, y sin ella este
    # programa NO se puede ejecutar dos veces. `publicar()` lista las
    # incidencias abiertas filtrando por etiqueta y construye con ellas
    # `claves_ahora`; si los dos archivos compartieran etiqueta, cada pasada
    # vería las incidencias del otro como AUSENTES y las declararía
    # «recuperadas» — o sea que se cerrarían mutuamente las alarmas cada tres
    # horas, y encima con un comentario diciendo que ya no arde.
    p.add_argument("--etiqueta", default="vigilante",
                   help="etiqueta de las issues. UNA POR ARCHIVO: la del "
                        "archivador es `vigilante` y la del SAIH, "
                        "`vigilante-saih`")
    p.add_argument("--horas", type=float, default=None,
                   help="umbral de la alarma de antigüedad. Por defecto %.0f, "
                        "que vale para el archivador; el SAIH se captura 3 "
                        "veces al día y necesita más" % UMBRAL_HORAS)
    p.add_argument("--simulacro",
                   choices=list(SIMULACROS),   # v1.08: UNA lista (ver cabecera)
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
                            simulacro=a.simulacro,
                            umbral_horas=a.horas)


    if a.simulacro:
        print("⚠️  SIMULACRO «%s»: la regla se fuerza, los ficheros NO se "
              "tocan.\n" % a.simulacro)

    if not incidencias:
        print("✅ Sin incidencias. El archivo está al día y ninguna fuente "
              "está muda.")
    else:
        print("Se han encontrado %d incidencia(s):\n" % len(incidencias))
        for i in incidencias:
            print("  [%s] %s" % (i.clave, i.titulo))

    # ⚠️⚠️ AQUÍ NO SE SALE AUNQUE NO HAYA INCIDENCIAS, y es el arreglo de un
    # fallo real del 8-sep-2026. Antes había un `return 0` justo encima, y eso
    # hacía que `publicar()` —donde vive el aviso de RECUPERACIÓN— no se
    # llamara nunca cuando todo iba bien. O sea: **el aviso de «ya no arde»
    # solo se mandaba si algo seguía ardiendo**, que es exactamente la
    # analogía del incendio que este código venía a resolver.
    #
    # Xevi desplegó el v1.03, no le llegó ningún comentario y preguntó si es
    # que no sabía verlo. No: era esto.
    #
    # Cerrar el ciclo de las incidencias abiertas es el OTRO trabajo de
    # `publicar()`, y es el más importante justo cuando no hay novedades.
    if a.publicar:
        repo = os.environ.get("GITHUB_REPOSITORY")
        token = os.environ.get("GITHUB_TOKEN")
        if not repo or not token:
            print("\n⚠️ Falta GITHUB_REPOSITORY o GITHUB_TOKEN: no se publica.")
            return 1
        creadas, omitidas = publicar(incidencias, repo, token,
                                     etiqueta=a.etiqueta,
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
