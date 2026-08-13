# Archivador diario — Fase 0 del proyecto BESS

Guarda cada día una foto de lo que estaba publicado y disponible en el momento
de ejecutarse: previsiones de eólica, solar y demanda, precios ya publicados,
**la predicción de temperatura de AEMET** y el precio del gas.

No modela nada. Solo deja constancia. Es la única pieza del proyecto cuyo
coste crece cada día que se retrasa, porque el dato de hoy no se puede
recuperar mañana.

---

## Puesta en marcha (una sola vez, ~15 minutos)

### 1. Crear el repositorio

En [github.com/new](https://github.com/new):

- **Nombre**: `bess-archivador` (o el que prefieras).
- **Visibilidad**: **público**, salvo que haya un motivo para lo contrario.
  Dos razones concretas, no ideológicas:
  1. En repositorios públicos los minutos de GitHub Actions son **gratis e
     ilimitados**; en privados hay una cuota mensual.
  2. Los commits llevan **marca de tiempo verificable por cualquiera**. Es
     exactamente la prueba que hace falta para demostrar que una previsión se
     generó *antes* de que se publicaran los precios reales. Para la acción de
     marketing, eso vale más que la propia previsión.

  Los datos son públicos de por sí (e·sios, ENTSO-E, AEMET, MIBGAS), y **los
  tokens nunca entran en el repositorio**: van en Secrets, que no se ven ni
  aunque el repositorio sea público.

### 2. Subir los dos archivos

Respetando esta estructura exacta — la carpeta `.github/workflows` no es
opcional, es donde GitHub busca los workflows:

```
bess-archivador/
├── archivador_diario.py
├── README.md
└── .github/
    └── workflows/
        └── archivador.yml
```

Desde la web: **Add file → Upload files**. Para crear la carpeta anidada,
escribe la ruta completa `.github/workflows/archivador.yml` en el nombre al
usar **Create new file**; GitHub crea las carpetas solo.

### 3. Cargar los tres tokens como Secrets

**Settings → Secrets and variables → Actions → New repository secret.**

Uno por token, con estos nombres exactos (mayúsculas incluidas):

| Nombre | Valor |
|---|---|
| `ESIOS_TOKEN` | El mismo que usas en Colab |
| `ENTSOE_TOKEN` | El mismo |
| `AEMET_TOKEN` | El mismo. **Caduca cada 3 meses** — ver más abajo |

Una vez guardados no se pueden volver a leer, solo sustituir. Es lo correcto.

### 4. Comprobar que Actions está activo

**Settings → Actions → General → Allow all actions**. En repositorios nuevos
suele venir activado.

### 5. Lanzarlo a mano la primera vez

Pestaña **Actions → Archivador diario BESS → Run workflow**. Funciona igual
desde la app de GitHub en el móvil.

No esperes al día siguiente para comprobar que funciona.

---

## Uso diario

**No hay uso diario.** Corre solo, **ocho veces al día**: al minuto 50 de las
2, 5, 8, 11, 14, 17, 20 y 23 (hora de Madrid).

Quien dispara no es el `schedule` de GitHub Actions, que descartó 22 de las 24
primeras ejecuciones, sino **un disparador externo (cron-job.org)** que llama a
la API de GitHub. El cron de GitHub se deja puesto como red de seguridad.

**La captura de las 11:50 es la intocable.** Medido sobre el propio archivo:
las series «Previsión diaria D+1» de e·sios (1775, 1777, 1779, 10358) se sellan
a las 10:50 y no son visibles por la API hasta cerca de las 11:45. Es la única
captura anterior al cierre de ofertas de las 12:00 que ve la previsión de
mañana; la de las 08:50 todavía tiene la de ayer.

Si algún día quieres forzarlo —porque quieres la foto a una hora concreta, o
porque la automática falló— **Actions → Run workflow**, también desde el móvil.

### El visor de móvil

`index.html` es una web de una sola página, sin dependencias, que lee el
archivo directamente y lo enseña en el móvil: estado del archivador, y
navegación por captura → fuente → serie con gráfico o tabla.

Se publica con **Settings → Pages → Source: Deploy from a branch → main /
(root)**. La URL resultante (`https://<usuario>.github.io/bess-archivador/`) se
abre en el móvil y se añade a la pantalla de inicio; a partir de ahí se
comporta como una app. Lleva `noindex`, así que no aparecerá en buscadores.

Los datos que muestra los pide a `raw.githubusercontent.com`, no a Pages: así
no depende de que Pages haya reconstruido el sitio y siempre enseña la última
captura.

### Comprobar que fue bien

Cada ejecución deja un resumen con el manifiesto completo del día: entra en la
ejecución desde la pestaña Actions y lo verás sin descargar nada. Dice, fuente
por fuente, si respondió, cuántos datos trajo y a qué hora.

Y si algo se rompe, GitHub te manda un correo. No hace falta vigilarlo.

---

## Cuatro cosas que conviene saber de antemano

**El cron de GitHub Actions es impuntual.** No es un fallo de configuración:
se retrasa habitualmente entre 5 y 30 minutos, y en horas de mucha carga
bastante más. Por eso está programado a las 08:30 y 09:45 UTC (10:30 y 11:45
en Madrid en verano, una hora antes en invierno), con margen de sobra hasta
las 13:00. Si algún día ves que la ejecución salió más tarde de lo previsto,
es esto y no hay nada que arreglar.

**Los workflows programados se desactivan tras 60 días sin actividad en el
repositorio.** Como este hace un commit cada día, no debería pasar; pero si
algún día ves que lleva tiempo sin correr, mira si GitHub lo ha desactivado y
reactívalo desde la pestaña Actions.

**El token de AEMET caduca cada tres meses.** Es lo más probable que se rompa,
y se rompe en silencio: el resto de fuentes seguirán funcionando y solo AEMET
aparecerá como fallida en el manifiesto. Cuando pase, pide uno nuevo y
actualiza el Secret. Merece la pena apuntarlo en el calendario.

**Una foto parcial se guarda igual.** Si una fuente falla, el programa guarda
lo que consiguió y lo deja anotado en el manifiesto. Es deliberado: perder la
foto entera del día por un fallo en una fuente sería el peor resultado
posible, porque ese día no vuelve. Solo devuelve error si no respondió
absolutamente nada.

---

## Qué se guarda, y por qué esto y no otra cosa

Tres ficheros en **ruta fija**, que no cambia nunca:

| Fichero | Contenido |
|---|---|
| `archivo/ultimo.json` | El manifiesto de la última captura |
| `archivo/indice.csv` | Una línea por captura, con el disparador que la lanzó |
| `archivo/catalogo.csv` | Qué es cada indicador: id, nombre y **descripción completa**. Acumulativo; solo se reescribe cuando REE cambia algo |

Y una carpeta **por captura**, en `archivo/AAAA/MM/AAAA-MM-DD/HHMM/`, donde
`HHMM` es la hora real de ejecución en Madrid — no la programada, para que el
retraso del cron quede registrado en vez de disimulado:

| Archivo | Contenido |
|---|---|
| `manifiesto.json` | Hora exacta de ejecución, estado de cada fuente, nº de registros, hashes |
| `esios_600_precio_spot.csv` | Precios publicados: últimos 8 días y, si ya está, mañana |
| `esios_602_energia_casada_diario.csv` | Energía casada en el mercado diario. Se publica tras la casación: nunca llega a D+1 |
| `esios_54*_prev_*.csv.gz` | Previsión de eólica, solar FV y solar térmica, **10 días vista** |
| **`esios_previsiones.csv.gz`** | **Todas** las previsiones del catálogo de e·sios (~60 indicadores) |
| `esios_previsiones_meta.csv` | Por indicador: estado, nº de filas y `values_updated_at` |
| `esios_previsiones_meta.csv` | Por indicador: estado, nº de filas y `values_updated_at` |
| `entsoe_A65_prev_demanda_es.csv` | Previsión de demanda peninsular |
| `entsoe_A69_prev_renovable_es.csv` | Previsión de generación renovable (solar y eólica) |
| `entsoe_A44_precio_francia.csv` | Precio day-ahead de Francia |
| `entsoe_A44_precio_es.csv` | Precio day-ahead de España vía ENTSO-E |
| `entsoe_A72_reserva_hidraulica.csv` | Reserva hidráulica (lectura semanal) |
| `aemet_prediccion_diaria.csv` | **Predicción** de temperatura a 7 días, 6 ciudades |
| `mibgas_gdaes.csv` | Precio del gas, producto GDAES |

Las ventanas son cortas a propósito: unos días, no el histórico completo. Se
trata de registrar lo nuevo y poder detectar revisiones, no de duplicar dos
años de datos cada mañana.

**El fichero grande va comprimido**, y no es un detalle menor: en plano, las
~60 series de previsión ocuparían unos 350 MB al año; comprimidas, 60 MB. Con
todo lo demás, el repositorio crece del orden de **110 MB al año**, que es
perfectamente asumible. Se lee con una línea:

```python
import pandas as pd
df = pd.read_csv("esios_previsiones.csv.gz")   # pandas descomprime solo
```

**Por qué se archivan TODAS las previsiones, incluidas las que hoy no usamos:**

Los indicadores 460, 2563 y 10249 están descartados como variable de
entrenamiento porque **se revisan después de publicarse**: lo que se descarga
hoy para una fecha pasada no es necesariamente lo que existía entonces.
Archivarlos a diario resuelve justo ese problema — a partir de la primera
ejecución tendremos su valor *tal como se publicó*, que es el único que un
modelo honesto puede usar. No se guardan por completismo: se rehabilitan.

Y con los indicadores cuyo significado aún no conocemos pasa algo parecido:
guardarlos cuesta unos KB al día, y no haberlos guardado cuesta el histórico
entero el día que resulten útiles. El catálogo se consulta en cada ejecución,
así que si REE publica un indicador nuevo, entra solo.

**Los dos datos que justifican todo esto:**

1. **La predicción de AEMET**, con su campo `elaborado`. La API solo devuelve
   la vigente: no hay forma de preguntar mañana qué decía hoy. Hoy el modelo
   se entrena con la temperatura *real* en lugar de la *prevista*, que es un
   sesgo optimista conocido y asumido. Esto lo arregla — pero solo hacia
   delante.
2. **El campo `values_updated_at`** de cada indicador de e·sios. Es lo que
   permitirá comprobar más adelante si una serie se revisó después de
   publicarse, que es la trampa que ya nos costó tres indicadores.

Y hay un tercer efecto, que no era el objetivo pero puede ser el primero en
dar fruto: **hoy nadie sabe con certeza qué está publicado a las 11:30**. Si
las previsiones de mañana ya están, si el precio de Francia aparece antes de
las 13:00, a qué hora se publica cada cosa. Con una semana de manifiestos,
esa pregunta queda respondida con datos en vez de con suposiciones.

---

## Cómo se conecta con el resto del proyecto

Este programa es la **Fase 0** del roadmap. No depende de nada y nada depende
de él para arrancar, pero:

- La **Fase 2** (cerrar el desajuste entre entrenamiento y producción) necesita
  varios meses de estas fotos para poder reentrenar con predicciones reales en
  lugar de con datos históricos.
- La **Fase 4a** (sombra de la previsión) se apoya en este registro para
  comparar lo que se predijo con lo que pasó.

Cuanto antes empiece a correr, antes estarán disponibles esas dos.
