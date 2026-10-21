# EcoBici Data Analyzer — Reporte operativo de movimientos de bicicletas

Trabajo Práctico 2 (individual) — Programación Orientada a Datos
Licenciatura en Ciencia de Datos — Universidad Católica Argentina, sede Rosario
Proyecto N.º 7 del Apéndice A de la consigna: *Reporte operativo de movimientos de Ecobici*.

> Documento en construcción: este README se completa a medida que avanza el desarrollo.

## Problema que resuelve

Quien supervisa una red de bicicletas compartidas necesita saber, para un
período determinado, cuántas bicicletas salieron de cada estación y cuántas
llegaron a ella. Esa información se obtiene a partir de los registros de
viajes, pero esos registros pueden contener identificadores repetidos, fechas
imposibles, campos vacíos o viajes que terminan antes de empezar. Contar a mano
sobre datos con errores produce balances incorrectos y difíciles de repetir.

## Solución propuesta

Una aplicación de consola en Python que lee los viajes desde CSV o JSON,
valida cada registro, aparta los inválidos con su motivo, selecciona los viajes
de un período y genera un reporte por estación con salidas, llegadas y balance
neto (`llegadas - salidas`), verificando la consistencia de los conteos.

## Alcance de la primera versión

- Datos sintéticos y reproducibles (6 estaciones ficticias, 88 registros).
- Selección de viajes por fecha de inicio, con ambos días del período incluidos.
- El balance representa movimientos, **no** stock disponible: no se incorpora
  inventario inicial ni reposiciones.
- Fuera de alcance: interfaces gráficas, bases de datos, predicciones.
