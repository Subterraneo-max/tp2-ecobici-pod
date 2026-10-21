# Datos: viajes sintéticos de EcoBici Data Analyzer

## Origen y naturaleza

Los datos de esta carpeta son **sintéticos**: fueron generados por el script
`scripts/generar_datos.py` de este repositorio. **No son viajes reales** de
Ecobici de Buenos Aires ni de ninguna otra red, y no permiten extraer
conclusiones sobre el uso real de un sistema de bicicletas. Su propósito es
contar con una entrada controlada, cuyos resultados se pueden anticipar, para
demostrar y probar la aplicación.

| Atributo | Valor |
|---|---|
| Procedimiento | Simulación con el módulo `random` de Python (`random.Random(42)`) |
| Script | `scripts/generar_datos.py` |
| Responsable de la generación | Tobias Moine (autor del trabajo práctico) |
| Fecha de generación | 2026-10-23 |
| Semilla aleatoria | `42` |
| Archivos | `viajes.csv` y `viajes.json` (misma información en dos formatos) |
| Registros | 88 en total: 80 viajes válidos y 8 registros inválidos deliberados |
| Estaciones | 6 estaciones ficticias: `Estacion_A` a `Estacion_F` |
| Período cubierto | Inicios entre el 1 y el 15 de octubre de 2026 |
| Licencia / condiciones de uso | Uso libre con fines educativos; al ser datos simulados no contienen información personal |

## Unidad de análisis

Cada fila (CSV) u objeto (JSON) representa **un viaje en bicicleta**: un
traslado que comienza en una estación y termina en otra (o en la misma, si es
un recorrido circular).

## Variables

| Variable | Tipo | Formato / unidad | Descripción |
|---|---|---|---|
| `viaje_id` | texto | `ECO-NNNN` (cuatro dígitos) | Identificador único del viaje |
| `inicio` | fecha y hora | `AAAA-MM-DD HH:MM:SS`, hora local sin zona horaria | Momento en que se retira la bicicleta |
| `fin` | fecha y hora | `AAAA-MM-DD HH:MM:SS`, hora local sin zona horaria | Momento en que se devuelve la bicicleta |
| `estacion_origen` | texto | nombre de estación | Estación donde comienza el viaje |
| `estacion_destino` | texto | nombre de estación | Estación donde termina el viaje |

La duración no se almacena: se deduce de `fin - inicio`. Un valor faltante se
representa con una celda vacía en el CSV y con `null` en el JSON.

## Formato de los archivos

- `viajes.csv`: UTF-8, separador coma, primera fila de encabezado.
- `viajes.json`: UTF-8, una **lista de objetos**, uno por viaje, con las mismas
  claves que las columnas del CSV.

## Procedimiento de generación

1. Se crean 78 viajes aleatorios. Para cada uno se sortea el día (1 a 15 de
   octubre de 2026), la hora de inicio (06:00 a 22:59), la duración (4 a 60
   minutos) y la estación de origen. Con probabilidad 0,1 el destino coincide
   con el origen (recorrido circular); si no, se sortea otra estación.
2. Se agregan 2 viajes válidos fijos que documentan casos límite:
   - un viaje que empieza el 7/10 a las 23:50 y termina el 8/10 a las 00:15;
   - un recorrido circular `Estacion_C → Estacion_C` el 1/10.
3. Los 80 viajes se ordenan por inicio y reciben los identificadores
   `ECO-0001` a `ECO-0080`.
4. Se insertan 8 registros inválidos en posiciones pseudoaleatorias
   (reproducibles con la misma semilla).

Para regenerar los archivos, desde la raíz del proyecto:

```bash
python scripts/generar_datos.py
```

Con la misma semilla se obtienen archivos idénticos byte a byte.

## Registros inválidos deliberados

| Identificador | Problema | Motivo esperado de rechazo |
|---|---|---|
| `ECO-0081` (2 filas) | Identificador repetido | `viaje_id duplicado` (se rechazan ambas filas) |
| `ECO-0082` | Inicio `2026-09-31 08:00:00`: el 31 de septiembre no existe | `inicio inválido` |
| `ECO-0083` | Fin `2026-10-06 25:10:00`: la hora 25 no existe | `fin inválido` |
| `ECO-0084` | Termina (14:05) antes de empezar (14:30) | `fin no posterior al inicio` |
| `ECO-0085` | Estación de origen vacía | `estacion_origen faltante` |
| `ECO-0086` | Estación de destino vacía | `estacion_destino faltante` |
| `ECO-87` | No respeta el patrón `ECO-NNNN` | `viaje_id con formato inválido` |

Los registros duplicados se diseñaron con un identificador que no usa ningún
viaje válido, para que la política de duplicados (rechazar todas las filas
repetidas) mantenga el resultado esperado de **80 válidos y 8 rechazados**.

## Limitaciones y sesgos

- Las estaciones, horarios y duraciones se sortean con distribuciones
  uniformes: no reproducen patrones reales (horas pico, días hábiles,
  estaciones más concurridas, clima).
- La proporción de errores (8 de 88, cerca del 9 %) fue elegida para ejercitar
  las validaciones, no para representar la calidad de datos de un sistema real.
- No hay viajes que empiecen antes de las 06:00 ni duraciones mayores a una
  hora; sólo el viaje fijo de las 23:50 cruza la medianoche.
- El conjunto es pequeño (88 registros) para que los resultados puedan
  verificarse a mano.
