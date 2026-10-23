# EcoBici Data Analyzer — Reporte operativo de movimientos de bicicletas

| | |
|---|---|
| **Materia** | Programación Orientada a Datos |
| **Carrera** | Licenciatura en Ciencia de Datos |
| **Universidad** | Universidad Católica Argentina (UCA), sede Rosario |
| **Trabajo** | Trabajo Práctico 2 — Individual |
| **Proyecto** | N.º 7 del Apéndice A de la consigna: *Reporte operativo de movimientos de Ecobici* |
| **Autor** | Tobias Moine |

Aplicación de consola en Python que lee registros de viajes en bicicleta
(CSV o JSON), valida y limpia los datos, selecciona un período y genera un
reporte por estación con salidas, llegadas y balance neto, verificando la
consistencia de los resultados.

---

## 1. Problema que resuelve

Una red de bicicletas compartidas registra cada viaje: cuándo y dónde se
retiró la bicicleta y cuándo y dónde se devolvió. Quien supervisa la
operación necesita responder preguntas como *¿de qué estaciones salieron más
bicicletas de las que llegaron durante la primera semana del mes?* Esa
respuesta orienta decisiones operativas: dónde reforzar la redistribución,
qué estaciones tienden a vaciarse y cuáles a llenarse.

**Usuario.** Un analista operativo o administrador del sistema, que recibe
los registros de viajes exportados y necesita un resumen confiable por
estación para un período elegido.

**Por qué es un problema.** Los registros de viajes rara vez llegan limpios:

- identificadores repetidos (el mismo viaje exportado dos veces o dos viajes
  con el mismo código);
- fechas imposibles (31 de septiembre) u horas inexistentes (25:10);
- campos vacíos, por ejemplo una estación de origen o destino sin registrar;
- inconsistencias temporales: viajes que terminan antes de empezar o que
  duran cero segundos;
- identificadores que no respetan el formato acordado.

Si estos registros se cuentan junto con los correctos, los balances quedan
mal: un duplicado suma dos salidas donde hubo una, un viaje sin destino suma
una salida sin la llegada correspondiente y el total deja de cerrar. Hacer el
conteo a mano, además, es lento, propenso a errores y difícil de repetir con
otro período o con un archivo nuevo.

**Cómo lo resuelve la aplicación.** El programa aplica siempre las mismas
reglas explícitas: aparta cada registro inválido con su motivo, cuenta sólo
los viajes válidos del período pedido y comprueba propiedades que todo
resultado correcto debe cumplir (por ejemplo, que la suma de balances de
todas las estaciones sea cero). Con las mismas entradas produce siempre los
mismos archivos de salida.

**Alcance de la primera versión.** Selecciona viajes por fecha de inicio y
calcula movimientos por estación. Queda fuera: el stock real de bicicletas
(no hay inventario inicial ni reposiciones), interfaces gráficas, bases de
datos y predicciones.

## 2. Solución propuesta

La aplicación realiza el flujo **leer → validar → limpiar → seleccionar →
contar → verificar → exportar**:

1. **Lee** los viajes desde un archivo `.csv` o `.json`, eligiendo el lector
   según la extensión.
2. **Valida el esquema**: que haya registros y estén las cinco columnas
   obligatorias.
3. **Valida cada registro** con reglas explícitas (identificador, fechas,
   horas, orden temporal, estaciones, duplicados).
4. **Separa** los viajes válidos de los rechazados; cada rechazo conserva sus
   valores originales, su número de registro y el motivo.
5. **Selecciona** los viajes cuyo inicio cae en el período pedido (ambos días
   completos).
6. **Registra movimientos**: por cada viaje, una salida en la estación de
   origen y una llegada en la de destino.
7. **Calcula el balance neto** por estación: `llegadas - salidas`.
8. **Verifica** la consistencia de los conteos y detiene la ejecución si
   alguna propiedad no se cumple.
9. **Exporta** el reporte, los registros rechazados y un resumen en JSON, y
   muestra los resultados en la consola.

## 3. Fuente de los datos

**Los datos son sintéticos.** No son viajes reales de Ecobici de Buenos Aires
ni de otra red, y no permiten sacar conclusiones sobre el uso real de un
sistema de bicicletas. Se generaron para disponer de una entrada controlada,
con errores conocidos y resultados que pueden verificarse a mano. Por ser
simulados, no hay una URL de origen.

| Atributo | Valor |
|---|---|
| Procedimiento | Simulación con `random.Random(42)` de la biblioteca estándar |
| Script que los produce | `scripts/generar_datos.py` |
| Responsable de la generación | Tobias Moine (autor del trabajo) |
| Fecha de generación | 2026-10-23 |
| Semilla aleatoria | `42` |
| Archivos | `data/viajes.csv` y `data/viajes.json` (misma información) |
| Cantidad de registros | 88: 80 viajes válidos y 8 registros inválidos deliberados |
| Estaciones | 6 ficticias: `Estacion_A` a `Estacion_F` |
| Período cubierto | inicios entre el 1 y el 15 de octubre de 2026 |
| Licencia / condiciones de uso | Uso libre con fines educativos; no contienen datos personales |

**Unidad de análisis:** cada fila (CSV) u objeto (JSON) es **un viaje**.

**Variables:**

| Variable | Formato / unidad | Descripción |
|---|---|---|
| `viaje_id` | texto `ECO-NNNN` | Identificador único del viaje |
| `inicio` | `AAAA-MM-DD HH:MM:SS`, hora local | Retiro de la bicicleta |
| `fin` | `AAAA-MM-DD HH:MM:SS`, hora local | Devolución de la bicicleta |
| `estacion_origen` | texto | Estación donde comienza el viaje |
| `estacion_destino` | texto | Estación donde termina el viaje |

Los 8 registros inválidos incluyen un identificador duplicado (dos filas),
una fecha inexistente, una hora inexistente, un viaje que termina antes de
empezar, estaciones de origen y destino vacías y un identificador mal formado.
También hay dos viajes válidos fijos que documentan casos límite: uno que
empieza el 7/10 a las 23:50 y termina el 8/10, y un recorrido circular.

**Limitaciones:** horarios, duraciones y estaciones se sortean de manera
uniforme, por lo que no reflejan horas pico, días hábiles ni estaciones más
concurridas; la proporción de errores (8 de 88) se eligió para ejercitar las
validaciones. El detalle completo del procedimiento, la tabla de registros
inválidos y los sesgos está en [`data/README.md`](data/README.md).

## 4. Tecnologías utilizadas

- **Python 3.11 o superior** (probado con 3.14.5).
- **pandas 3.1.0**: lectura de CSV, operaciones tabulares, conversión de
  fechas y exportación. Es la única dependencia externa.
- Biblioteca estándar: `abc` (clase abstracta), `argparse` (argumentos de
  consola), `re` (expresiones regulares), `datetime` (validación de
  calendario), `json`, `csv` y `random` (generador de datos), `pathlib`
  (rutas) y `unittest` (pruebas).
- **Git y GitHub** para el control de versiones.

## 5. Organización del proyecto

```text
tp2-ecobici-pod/
├── README.md                 # este documento
├── requirements.txt          # dependencia: pandas
├── .gitignore                # excluye entorno virtual, cachés, secretos y material de cátedra
├── .gitattributes            # CSV y JSON con fin de línea LF en todos los sistemas
├── src/
│   ├── __init__.py           # paquete de la aplicación
│   ├── main.py               # aplicación de consola (argparse, salida por pantalla)
│   ├── fuentes.py            # ErrorDatos, FuenteDatos (abstracta), FuenteCSV, FuenteJSON
│   ├── dominio.py            # clase BalanceEstacion
│   └── pipeline.py           # validación, limpieza, período, balance, verificación, exportación
├── scripts/
│   └── generar_datos.py      # genera data/viajes.csv y data/viajes.json
├── data/
│   ├── README.md             # documentación de los datos
│   ├── viajes.csv
│   └── viajes.json
├── tests/                    # 85 pruebas con unittest
│   ├── test_fuentes.py       # lectura de archivos
│   ├── test_validaciones.py  # validación y limpieza
│   ├── test_periodos.py      # selección de períodos
│   ├── test_balance.py       # BalanceEstacion y balances
│   └── test_integracion.py   # flujo completo y archivos exportados
├── docs/
│   └── revision_calidad.md   # revisión de errores y defectos corregidos
└── outputs/                  # resultados del ejemplo de la sección 9
    ├── reporte_estaciones.csv
    ├── registros_rechazados.csv
    └── resumen.json
```

Las salidas de `outputs/` se conservan en el repositorio como ejemplo de
resultado; se regeneran con el comando de la sección 7.

## 6. Instalación

Requisitos: **Python 3.11 o superior** (la versión mínima que exige
pandas 3.1.0) y Git. El proyecto se probó con Python 3.14.5 en Windows 11,
con pandas 3.1.0 y numpy 2.5.4 (instalado automáticamente con pandas).

```bash
git clone https://github.com/Subterraneo-max/tp2-ecobici-pod.git
cd tp2-ecobici-pod
```

Se recomienda un entorno virtual:

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux o macOS:
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

## 7. Cómo ejecutar el programa

Todos los comandos se ejecutan **desde la raíz del proyecto** (la carpeta que
contiene `src/`), porque la aplicación se ejecuta como módulo del paquete
`src`.

Con el archivo CSV:

```bash
python -m src.main --entrada data/viajes.csv --desde 2026-10-01 --hasta 2026-10-07 --salida outputs
```

Con el archivo JSON (produce el mismo reporte):

```bash
python -m src.main --entrada data/viajes.json --desde 2026-10-01 --hasta 2026-10-07 --salida outputs
```

| Argumento | Obligatorio | Descripción |
|---|---|---|
| `--entrada` | sí | Archivo de viajes. La extensión (`.csv` o `.json`) determina el lector. |
| `--desde` | sí | Primer día del período, `AAAA-MM-DD`. Se incluye completo desde las 00:00:00. |
| `--hasta` | sí | Último día del período, `AAAA-MM-DD`. Se incluye completo hasta las 23:59:59. |
| `--salida` | no | Directorio donde se guardan los resultados (por defecto `outputs`; se crea si no existe). |

`python -m src.main --help` muestra la ayuda. El programa termina con código
`0` si el análisis se completa, `1` si hay un error en los datos o los
archivos (el mensaje se muestra en la consola) y `2` si los argumentos son
inválidos, por ejemplo una fecha inexistente como `2026-02-30`.

Para regenerar los datos sintéticos (opcional; produce archivos idénticos):

```bash
python scripts/generar_datos.py
```

## 8. Cómo ejecutar los tests

```bash
python -m unittest discover -s tests -v
```

Resultado actual: **`Ran 85 tests` — `OK`** (85 pruebas aprobadas).

| Archivo | Pruebas | Qué verifica |
|---|---|---|
| `test_fuentes.py` | 17 | Lectura de CSV y JSON, equivalencia entre formatos, archivo inexistente, vacío o mal formado, estructura JSON incorrecta, BOM, conservación de identificadores y tipos |
| `test_validaciones.py` | 27 | Identificadores válidos e inválidos, duplicados y su política, fechas y horas inexistentes o mal formadas, fin anterior al inicio, duración cero, estaciones y campos vacíos, nulos, motivos de rechazo, conservación de registros, viaje circular, independencia del formato |
| `test_periodos.py` | 13 | Primer y último día incluidos, viajes fuera de rango, viaje que termina fuera del período, período invertido o sin viajes, parámetros inválidos, determinismo, igualdad CSV/JSON |
| `test_balance.py` | 16 | `BalanceEstacion` (llegadas, salidas, balance positivo, negativo y cero, validaciones), viaje A→B, circular, sentidos opuestos, conservación de movimientos, suma de balances igual a cero, exclusión de registros inválidos, verificaciones |
| `test_integracion.py` | 12 | Flujo completo con CSV y JSON, exportación y relectura de archivos, reporte con datos conocidos y sin resultados, determinismo, códigos de salida y ejecución del comando documentado |

Las pruebas cubren los tres tipos que pide la consigna: casos normales
(resultados conocidos), entradas inválidas o límite, y propiedades del
resultado (conservación de cantidades, suma de balances igual a cero,
equivalencia CSV/JSON). Las que escriben archivos usan directorios
temporales: no modifican `data/` ni `outputs/`.

## 9. Resultados

Salida real del primer comando de la sección 7 (período del 1 al 7 de octubre
de 2026):

```text
EcoBici Data Analyzer - Reporte de movimientos por estación
Archivo de entrada: viajes.csv
Período: 2026-10-01 a 2026-10-07 (según fecha de inicio, ambos días incluidos)
Registros: 88 originales, 80 válidos, 8 rechazados
Viajes seleccionados: 48

  estacion  salidas  llegadas  balance
Estacion_A        7        11        4
Estacion_B        4        12        8
Estacion_C       12         8       -4
Estacion_D        6         7        1
Estacion_E       13         2      -11
Estacion_F        6         8        2

Totales: 48 salidas, 48 llegadas, suma de balances = 0
Comprobaciones:
  [OK] originales_igual_validos_mas_rechazados
  [OK] total_salidas_igual_viajes
  [OK] total_llegadas_igual_viajes
  [OK] suma_balances_igual_cero
  [OK] balance_igual_llegadas_menos_salidas
  [OK] estaciones_sin_repetir
Archivos generados:
  outputs\reporte_estaciones.csv
  outputs\registros_rechazados.csv
  outputs\resumen.json
```

(En Linux o macOS las rutas se muestran con `/`.)

**Cómo leer el reporte:**

- **salidas**: viajes del período que comenzaron en la estación.
- **llegadas**: viajes del período que terminaron en la estación.
- **balance** = llegadas − salidas. En `Estacion_E` salieron 13 bicicletas y
  llegaron 2: balance −11, la estación "perdió" movimientos netos y es
  candidata a recibir bicicletas en una redistribución. En `Estacion_B`
  llegaron 12 y salieron 4: balance +8, tendencia a acumular bicicletas. Un
  balance 0 indica equilibrio entre entradas y salidas, no que la estación
  esté vacía.
- Cada viaje aporta exactamente una salida y una llegada; por eso los totales
  son iguales a la cantidad de viajes seleccionados (48) y los balances suman
  0. El viaje `ECO-0048` empieza el 7/10 a las 23:50 y termina el 8/10: se
  cuenta en este período porque el criterio es la fecha de inicio.

**Archivos exportados:**

- `outputs/reporte_estaciones.csv`: la tabla anterior (`estacion, salidas,
  llegadas, balance`), ordenada por estación.
- `outputs/registros_rechazados.csv`: los 8 registros apartados con sus
  valores originales, el número de registro en el archivo (1 = primer
  registro después del encabezado) y el motivo.
- `outputs/resumen.json`: archivo de entrada, período y criterio, cantidades
  de registros (originales, válidos, rechazados), viajes seleccionados,
  totales de movimientos y resultado de cada comprobación.

Fragmento de `outputs/registros_rechazados.csv`:

```text
registro,viaje_id,inicio,fin,estacion_origen,estacion_destino,motivo
1,ECO-0086,2026-10-12 19:00:00,2026-10-12 19:35:00,Estacion_C,,estacion_destino faltante
24,ECO-0081,2026-10-03 09:00:00,2026-10-03 09:20:00,Estacion_A,Estacion_B,viaje_id duplicado
39,ECO-87,2026-10-14 12:00:00,2026-10-14 12:30:00,Estacion_A,Estacion_E,viaje_id con formato inválido
41,ECO-0083,2026-10-06 18:40:00,2026-10-06 25:10:00,Estacion_E,Estacion_F,fin inválido
```

Un período sin viajes (por ejemplo `--desde 2026-11-01 --hasta 2026-11-30`)
también funciona: el reporte lista las 6 estaciones con todos los valores en
0 y todas las comprobaciones se cumplen.

## 10. Validaciones y limpieza

**Validaciones que detienen el análisis** (el programa informa el error y
termina con código 1):

- archivo inexistente, ruta que no es un archivo, archivo vacío, CSV o JSON
  mal formado, codificación distinta de UTF-8, extensión no soportada;
- JSON cuya raíz no es una lista de objetos o con valores anidados;
- tabla sin registros o sin alguna de las columnas obligatorias
  (`viaje_id`, `inicio`, `fin`, `estacion_origen`, `estacion_destino`);
- ningún viaje válido después de la limpieza;
- parámetros de consulta inválidos: formato distinto de `AAAA-MM-DD`, fecha
  inexistente o fecha inicial posterior a la final;
- alguna comprobación de consistencia que no se cumple.

**Reglas por registro** (el registro se aparta y se guarda con su motivo):

| Regla | Motivo registrado |
|---|---|
| Identificador ausente | `viaje_id faltante` |
| Identificador que no cumple `ECO-[0-9]{4}` | `viaje_id con formato inválido` |
| Identificador repetido | `viaje_id duplicado` |
| Inicio / fin ausente | `inicio faltante` / `fin faltante` |
| Inicio / fin que no cumple el formato o no existe en el calendario | `inicio inválido` / `fin inválido` |
| Fin igual o anterior al inicio (incluye duración cero) | `fin no posterior al inicio` |
| Estación de origen / destino ausente | `estacion_origen faltante` / `estacion_destino faltante` |

**Decisiones de limpieza:**

- Antes de validar se eliminan los espacios al principio y al final de cada
  campo, y un campo vacío o con sólo espacios cuenta como faltante.
- **Política de duplicados:** se rechazan **todas** las filas que comparten un
  identificador, porque no hay un criterio confiable para decidir cuál es la
  correcta. En los datos, las dos filas `ECO-0081` se rechazan.
- Un registro puede tener varios motivos; se informan todos, separados por
  `; `.
- Un **viaje circular** (origen igual a destino) es válido: puede ser un paseo
  que vuelve al punto de partida. Suma una salida y una llegada en la misma
  estación.
- Los nombres de estación distinguen mayúsculas y minúsculas
  (`Estacion_A` y `estacion_a` serían estaciones distintas).
- No se corrige ni se imputa ningún valor: los registros rechazados no
  intervienen en los conteos y quedan disponibles para su revisión.
- Se cumple siempre `originales = válidos + rechazados`.

## 11. Arquitectura del código

**Funciones con responsabilidades separadas (`pipeline.py`).** Las
transformaciones reciben tablas y devuelven tablas nuevas sin modificar sus
argumentos ni tocar archivos; la lectura está en `fuentes.py` y la escritura
se concentra en `exportar_resultados()`.

| Función | Responsabilidad |
|---|---|
| `validar_esquema(tabla)` | Comprueba que haya registros y columnas obligatorias |
| `normalizar_campos(tabla)` | Quita espacios externos; vacíos pasan a faltantes |
| `validar_recorridos(tabla)` | Devuelve una tabla booleana con una columna por regla |
| `limpiar_viajes(tabla)` | Devuelve `(validos, rechazados)` con motivos; convierte fechas |
| `validar_periodo(desde, hasta)` | Valida los parámetros de la consulta |
| `seleccionar_periodo(viajes, desde, hasta)` | Filtra por fecha de inicio, orden determinista |
| `registrar_movimientos(viajes, estaciones)` | Acumula salidas y llegadas en objetos `BalanceEstacion` |
| `generar_balance(balances)` | Construye el reporte por estación |
| `verificar_balance(reporte, cantidad)` / `verificar_registros(...)` | Comprueban las propiedades del resultado |
| `construir_resumen(...)` / `exportar_resultados(...)` | Arman y escriben las salidas |

**Clases.**

- `FuenteDatos` (`fuentes.py`): clase abstracta (`ABC`) que define el
  contrato `cargar()` → DataFrame de texto. Encapsula la ruta (`_ruta`,
  expuesta con `@property` de sólo lectura) y comparte con sus subclases la
  comprobación del archivo y la normalización de valores.
- `FuenteCSV` y `FuenteJSON`: **heredan** de `FuenteDatos` y **sobrescriben**
  `cargar()` para su formato. Ambas devuelven exactamente la misma tabla para
  los mismos datos.
- `BalanceEstacion` (`dominio.py`): modelo del dominio. Guarda el nombre de la
  estación y los conteos de llegadas y salidas como atributos encapsulados
  (sólo se modifican con `registrar_llegada()` y `registrar_salida()`, que
  validan la cantidad) y calcula `calcular_balance()` = llegadas − salidas.
  Participa realmente en el cálculo: `registrar_movimientos()` crea un objeto
  por estación y cada fila del reporte sale de su método `a_diccionario()`.
- `AplicacionEcobici` (`pipeline.py`): coordina el flujo completo. **Tiene**
  una fuente (composición) en lugar de heredar de ella.
- `ErrorDatos`: excepción para entradas que no cumplen el contrato, con
  mensajes comprensibles.

**Polimorfismo.** `AplicacionEcobici.ejecutar()` llama a
`self._fuente.cargar()` sin saber si la fuente es CSV o JSON;
`crear_fuente()` elige la clase según la extensión del archivo. Agregar otro
formato sólo requiere una nueva subclase de `FuenteDatos`.

**Expresiones regulares** (con `re.fullmatch`, que exige que **todo** el texto
cumpla el patrón):

- `ECO-[0-9]{4}`: identificador de viaje. `[0-9]` admite sólo dígitos ASCII.
- `[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}`: forma de fecha y
  hora de `inicio` y `fin`.
- `[0-9]{4}-[0-9]{2}-[0-9]{2}`: forma de los parámetros `--desde` y `--hasta`.

Una regex sólo comprueba la forma: `2026-09-31 08:00:00` la cumple aunque esa
fecha no existe. Por eso cada fecha se complementa con
`datetime.strptime()`, que rechaza días y horas inexistentes.

**Pipeline de datos:**

```text
FuenteCSV / FuenteJSON .cargar()
        │  DataFrame de texto
        ▼
validar_esquema → normalizar_campos → validar_recorridos → limpiar_viajes
        │                                                     │
        │ validos                                  rechazados ┘──► registros_rechazados.csv
        ▼
seleccionar_periodo → registrar_movimientos (BalanceEstacion) → generar_balance
        │
        ▼
verificar_registros + verificar_balance → construir_resumen → exportar_resultados
                                                              ├─► reporte_estaciones.csv
                                                              └─► resumen.json
```

## 12. Interpretación y limitaciones

- **El balance representa movimientos, no inventario.** Un balance de +8 no
  significa que la estación tenga 8 bicicletas: no se conoce cuántas había al
  comenzar el período ni las reposiciones realizadas por camiones de
  redistribución. Indica sólo la diferencia entre llegadas y salidas.
- Los viajes se asignan al período por su **fecha de inicio**; un viaje que
  termina después del último día igual cuenta su llegada.
- Los datos son sintéticos y uniformes: los números del ejemplo no describen
  ninguna red real.
- El análisis depende de la calidad de los nombres de estación: dos nombres
  escritos distinto se tratan como estaciones distintas.
- Fechas y horas se interpretan como hora local sin zona horaria.
- Probado en Windows 11 con Python 3.14.5 y pandas 3.1.0; no se probó en
  otros sistemas operativos.

## 13. Reproducibilidad

1. Instalar las dependencias fijadas: `python -m pip install -r requirements.txt`.
2. (Opcional) Regenerar los datos: `python scripts/generar_datos.py`. Con la
   semilla 42 se obtienen archivos idénticos byte a byte a los del repositorio.
3. Ejecutar el análisis:
   `python -m src.main --entrada data/viajes.csv --desde 2026-10-01 --hasta 2026-10-07 --salida outputs`.
   El resultado coincide con el de la sección 9 y con los archivos de
   `outputs/`.
4. Ejecutar las pruebas: `python -m unittest discover -s tests -v`.

La salida es determinista: no incluye marcas de tiempo, las tablas se ordenan
de manera fija (estación; inicio e identificador) y los archivos se escriben
con codificación UTF-8 y fin de línea `\n` en cualquier sistema operativo. Dos
ejecuciones con las mismas entradas producen archivos idénticos (lo verifica
`test_determinismo_de_la_aplicacion`), y el CSV y el JSON del conjunto de
datos producen el mismo reporte.

## 14. Calidad y control de versiones

- La revisión de errores, las seis categorías auditadas y los defectos
  corregidos (con su causa, solución y prueba) están en
  [`docs/revision_calidad.md`](docs/revision_calidad.md).
- El historial de Git registra el avance por etapas: estructura inicial,
  datos y lectores, dominio y validaciones, pipeline y aplicación, pruebas,
  correcciones de la auditoría, estilo y documentación.
