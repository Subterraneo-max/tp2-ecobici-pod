# Revisión de calidad — EcoBici Data Analyzer

Este documento registra las verificaciones realizadas sobre el código y los
defectos reales encontrados y corregidos durante el desarrollo. Todo lo que
se describe aquí fue ejecutado; los mensajes de error citados son los
observados.

Entorno de la revisión: Windows 11, Python 3.14.5, pandas 3.1.0,
flake8 7.4.1. Fecha: 2026-10-23.

## Resumen

| Indicador | Resultado |
|---|---|
| Pruebas automáticas | 85 ejecutadas, 85 aprobadas (`python -m unittest discover -s tests -v`) |
| Defectos reales corregidos | 6 (D1 a D6) |
| Categorías de revisión | 6 obligatorias + nombres, imports, excepciones, rutas y dependencias |
| Mutaciones deliberadas detectadas por las pruebas | 13 de 13 |
| Estilo (flake8, PEP 8) | sin avisos |

## Procedimiento

1. **Desarrollo con pruebas.** Cada módulo se probó al escribirlo. D1 apareció
   en esta etapa.
2. **Sondeo de casos límite.** Con las 80 pruebas iniciales aprobadas, se
   ejecutó un script de sondeo (fuera del repositorio) que alimentó a la
   aplicación con entradas atípicas de cada categoría y registró el
   comportamiento observado.
3. **Corrección guiada por pruebas.** Para cada comportamiento incorrecto se
   escribió primero una prueba que lo reproduce, se comprobó que **fallaba**,
   se corrigió el código y se volvió a ejecutar la suite completa. Las
   correcciones D2 a D6 están en el commit `6698aa9`.
4. **Prueba de mutación.** Sobre una copia temporal del proyecto se
   introdujeron 13 errores deliberados, uno por vez, para comprobar que la
   suite los detecta (ver más abajo). El código del repositorio no se modificó.
5. **Contraste independiente.** El reporte del 1/10 al 7/10 se recalculó con
   un script que sólo usa el módulo `csv` y contadores, sin el código de la
   aplicación. Los seis valores de salidas, llegadas y balance coincidieron.
6. **Estilo.** `flake8` sobre `src`, `tests` y `scripts`.

## Defectos encontrados y corregidos

### D1 — El contrato de `cargar()` declaraba `None` para los faltantes

- **Descripción:** la documentación de `fuentes.py` afirmaba que cada valor
  devuelto era un `str` o `None`. Al ejecutar las fuentes, los faltantes
  aparecían como `NaN`: un código que preguntara `valor is None` no los
  detectaría.
- **Reproducción:** `FuenteCSV('data/viajes.csv').cargar().iloc[0].tolist()`
  devolvía `[..., 'Estacion_C', nan]` y las columnas eran
  `StringDtype(na_value=nan)`.
- **Causa:** pandas 3 vuelve a inferir el tipo de cada columna después de
  `DataFrame.map()`; en una columna de texto, el `None` devuelto por
  `_como_texto` se representa como `NaN`.
- **Archivo afectado:** `src/fuentes.py`.
- **Solución:** se corrigió el contrato documentado (módulo, `cargar()` y
  `_normalizar_valores()`): los faltantes se detectan con `pd.isna`, igual en
  CSV y JSON. El resto del flujo ya usaba `pd.isna`/`isinstance`.
- **Prueba:** `test_fuentes.test_tipos_compatibles_entre_formatos` fija el
  contrato corregido (todo valor presente es `str`; los dos faltantes del
  conjunto se detectan con `pd.isna` en ambos formatos).
- **Momento:** detectado durante el desarrollo, antes del primer commit de
  `fuentes.py` (por eso no hay una versión defectuosa en el historial).

### D2 — Un JSON en UTF-8 con BOM se rechazaba como "mal formado"

- **Descripción:** un archivo JSON válido guardado con BOM (marca que agregan
  algunos editores de Windows) producía
  `ErrorDatos: JSON mal formado ... Unexpected UTF-8 BOM`, mientras que un CSV
  con BOM se leía bien: el comportamiento dependía del formato.
- **Causa:** `FuenteJSON` abría el archivo con `encoding='utf-8'`, que no
  descarta el BOM; `json.load` lo rechaza.
- **Archivo afectado:** `src/fuentes.py`.
- **Solución:** ambas fuentes leen con `encoding='utf-8-sig'`, que acepta
  archivos con y sin BOM.
- **Prueba:** `test_fuentes.test_csv_y_json_con_bom_utf8` (antes de la
  corrección: `JSONDecodeError: Unexpected UTF-8 BOM`).

### D3 — Un JSON sin registros (`[]`) informaba "Faltan columnas"

- **Descripción:** con un JSON `[]`, el mensaje era
  `Faltan columnas: viaje_id, inicio, fin, estacion_origen, estacion_destino`,
  que no describe el problema real: el archivo no tiene registros.
- **Causa:** `validar_esquema` comprobaba las columnas antes que la cantidad
  de filas, y una lista vacía produce un DataFrame sin columnas.
- **Archivo afectado:** `src/pipeline.py` (`validar_esquema`).
- **Solución:** se controla primero que haya filas:
  `La tabla de entrada está vacía: no hay registros.`
- **Prueba:** `test_fuentes.test_json_lista_vacia_se_informa_como_tabla_vacia`
  (antes: la expresión `vacía` no aparecía en el mensaje).

### D4 — Una ruta a un directorio se informaba como archivo inexistente

- **Descripción:** `FuenteCSV(<directorio>).cargar()` respondía
  `FileNotFoundError: No existe el archivo`, aunque la ruta existía.
- **Causa:** `comprobar_archivo` usaba sólo `Path.is_file()`, que es falso
  tanto para rutas inexistentes como para directorios.
- **Archivo afectado:** `src/fuentes.py` (`FuenteDatos.comprobar_archivo`).
- **Solución:** se distingue `exists()` (archivo inexistente) de
  `is_file()` (`ErrorDatos: La ruta no es un archivo`).
- **Prueba:** `test_fuentes.test_ruta_que_es_un_directorio`.

### D5 — Valores no textuales se marcaban como "faltantes"

- **Descripción:** al pasar a `limpiar_viajes` un DataFrame construido a mano
  con un identificador entero (`2`) o un `pd.Timestamp` en `inicio`, el motivo
  era `viaje_id faltante` / `inicio faltante`. El dato existía: el motivo era
  falso y un viaje válido con `Timestamp` se rechazaba.
- **Causa:** `_normalizar_texto` devolvía `None` para todo valor que no fuera
  `str`, confundiendo "no es texto" con "falta".
- **Archivo afectado:** `src/pipeline.py` (`_normalizar_texto`).
- **Solución:** sólo los faltantes (`pd.isna`) pasan a `None`; el resto se
  convierte a texto y se valida con las reglas habituales. Un id `2` ahora se
  informa como `viaje_id con formato inválido` y un `Timestamp` correcto se
  acepta.
- **Prueba:** `test_validaciones.test_valores_no_textuales_se_validan_por_su_texto`
  (antes: `ErrorDatos: No quedan viajes válidos para analizar.`).

### D6 — Los archivos exportados dependían del sistema operativo

- **Descripción:** en Windows, `reporte_estaciones.csv`,
  `registros_rechazados.csv` y `resumen.json` se escribían con fin de línea
  `\r\n`; en Linux o macOS se escribirían con `\n`. Las mismas entradas no
  producían los mismos bytes en distintos equipos.
- **Causa:** `DataFrame.to_csv` usa `os.linesep` por defecto y `open()` en
  modo texto traduce `\n` a `\r\n` en Windows.
- **Archivo afectado:** `src/pipeline.py` (`exportar_resultados`); se agregó
  `.gitattributes` para conservar LF en CSV y JSON al clonar.
- **Solución:** `lineterminator='\n'` en `to_csv` y `newline='\n'` al escribir
  el JSON.
- **Prueba:** `test_integracion.test_exportacion_independiente_del_sistema_operativo`
  (antes: `b'\r\n' unexpectedly found` en los tres archivos).

## Verificaciones por categoría

### 1. Lectura y conversión de archivos

| Caso | Resultado |
|---|---|
| CSV y JSON del conjunto: forma, columnas y equivalencia exacta | correcto |
| Archivo inexistente / vacío / CSV y JSON mal formados | error explícito, sin tablas vacías silenciosas |
| JSON que no es lista de objetos, o con un valor anidado | `ErrorDatos` |
| CSV en Latin-1 | `ErrorDatos: ... no está codificado en UTF-8` |
| CSV sólo con encabezado | `La tabla de entrada está vacía` |
| Texto `NA` como nombre de estación | se conserva como texto (no se convierte en faltante) |
| Identificadores con ceros a la izquierda | se conservan (`dtype=str`) |
| Contrato de faltantes, BOM en JSON, `[]`, directorio como ruta | **D1, D2, D3, D4** |

### 2. Validación de identificadores y duplicados

| Caso | Resultado |
|---|---|
| Patrón `ECO-[0-9]{4}` con `re.fullmatch` (rechaza `ECO-00012`, `XECO-0001`, minúsculas, dígitos no ASCII) | correcto |
| Duplicados que sólo difieren en espacios externos | se normalizan y se detectan |
| Varios identificadores faltantes | se informan como faltantes, no como duplicados |
| Política: todas las copias de un id repetido se rechazan | correcto (3 copias → 3 rechazos) |
| Valores no textuales en un DataFrame directo | **D5** |

### 3. Fechas y selección de períodos

| Caso | Resultado |
|---|---|
| 31/09, 30/02, 29/02 en año no bisiesto, mes 13 | rechazados por `datetime.strptime` |
| Hora 24 o 25, minuto 60, segundo 60 o 61 | rechazados |
| Formatos `2026/10/01`, `01-10-2026`, `2026-10-01T08:00:00`, `2026-10-1 8:00:00` | rechazados por la regex |
| Años 0001 y 9999 en los datos o en los parámetros | se procesan sin desbordamiento (pandas 3) |
| Inicio a las 00:00:00 del primer día y a las 23:59:59 del último | incluidos |
| Inicio a las 00:00:00 del día siguiente o 23:59:59 del día anterior | excluidos |
| Viaje que empieza dentro y termina fuera del período | incluido (criterio: fecha de inicio) |
| Período invertido, fecha imposible, `datetime` con hora como parámetro | `ErrorDatos` |

No se encontraron defectos en esta categoría.

### 4. Conteos y balances

| Caso | Resultado |
|---|---|
| Reporte 1/10–7/10 contra un conteo independiente con `csv` | coincide en las 6 estaciones |
| Viaje A→B, circular, dos viajes opuestos | conteos esperados |
| Total de salidas = total de llegadas = viajes seleccionados | verificado en 4 períodos |
| Suma de balances = 0, incluso en período sin viajes | verificado |
| Registros inválidos agregados a un conjunto | el reporte no cambia |
| Nombres que difieren en mayúsculas (`Estacion_A` / `estacion_a`) | se cuentan como estaciones distintas: es una **decisión documentada**, no un defecto |

No se encontraron defectos en esta categoría.

### 5. Exportación de resultados

| Caso | Resultado |
|---|---|
| Totales del resumen | tipos `int` de Python (serializables en JSON) |
| Releer `reporte_estaciones.csv` y `resumen.json` | igual a lo calculado |
| Directorio de salida inexistente (anidado) | se crea |
| Salidas de CSV y de JSON | idénticas byte a byte, salvo `archivo_entrada` |
| Dos ejecuciones iguales | archivos idénticos byte a byte |
| `--salida` apunta a un archivo existente | `main` informa el `OSError` del sistema y devuelve 1 (se dejó así: el mensaje es comprensible y no se escriben salidas) |
| Fin de línea dependiente del sistema operativo | **D6** |

### 6. Integración entre módulos

| Caso | Resultado |
|---|---|
| `AplicacionEcobici` con `FuenteCSV` y con `FuenteJSON` (polimorfismo) | mismo reporte |
| `AplicacionEcobici` con algo que no es `FuenteDatos` | `TypeError` |
| `main()` con archivo inexistente o período invertido | mensaje en `stderr`, código 1, sin salidas |
| Fecha imposible en `--desde` | argparse informa el error, código 2 |
| Comando documentado en el README, en un proceso aparte | código 0 y resultados esperados |
| DataFrame construido a mano (sin pasar por una fuente) | **D5** |

### Nombres, imports, excepciones, rutas y dependencias

- `flake8`: sin imports sin uso, nombres indefinidos ni avisos de estilo.
- Imports absolutos `from src...`: requieren ejecutar desde la raíz con
  `python -m src.main` y `python -m unittest ...`, como indica el README.
- Excepciones: los errores de datos usan `ErrorDatos` (subclase de
  `ValueError`); `main` sólo captura `ErrorDatos` y `OSError`, de modo que un
  error de programación no se oculta.
- Rutas: `pathlib.Path` en todo el proyecto; las pruebas ubican `data/` a
  partir de `__file__` y escriben sólo en directorios temporales.
- Dependencias: la única biblioteca externa es pandas (`requirements.txt`).
  flake8 se usó sólo como herramienta de revisión y no es necesario para
  ejecutar el programa ni las pruebas.

## Prueba de mutación

Cada fila es un error introducido a propósito en una copia temporal del
proyecto. "Detectada" significa que al menos una prueba falló.

| Mutación | Resultado |
|---|---|
| El período incluye la medianoche del día siguiente (`<=` en lugar de `<`) | detectada (3 fallas) |
| Selección por `fin` en lugar de `inicio` | detectada (13 fallas) |
| Salida y llegada invertidas en el origen | detectada |
| Balance calculado como salidas − llegadas | detectada |
| Duplicados: se conserva la primera copia | detectada (11 fallas) |
| Duración cero aceptada (`<` en lugar de `<=`) | detectada |
| Sin comprobación de calendario (sólo regex) | detectada |
| `re.search` en lugar de `re.fullmatch` para el id | detectada (3 fallas) |
| Viajes circulares rechazados | detectada |
| Estaciones sin movimientos omitidas del reporte | detectada (1 falla) |
| JSON sin control de "lista de objetos" | detectada (1 falla) |
| Sin eliminar espacios externos | detectada |
| Verificación de balance desactivada | detectada (2 fallas) |

## Pendientes conocidos

- La aplicación se probó en Windows 11 con Python 3.14.5 y pandas 3.1.0. No
  se ejecutó en otros sistemas operativos ni en otras versiones de Python.
- Los nombres de estación distinguen mayúsculas y minúsculas (decisión
  documentada en el README).
