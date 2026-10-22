"""Punto de entrada de la aplicación de consola.

Ejemplo, desde la raíz del proyecto:
    python -m src.main --entrada data/viajes.csv --desde 2026-10-01 \
        --hasta 2026-10-07 --salida outputs
"""

import argparse
import sys

from src.fuentes import ErrorDatos, crear_fuente
from src.pipeline import AplicacionEcobici, convertir_fecha, exportar_resultados


def fecha_argumento(texto):
    """Adapta convertir_fecha() al formato de errores de argparse."""
    try:
        return convertir_fecha(texto)
    except ErrorDatos as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def crear_parser():
    parser = argparse.ArgumentParser(
        prog='python -m src.main',
        description='Reporte de salidas, llegadas y balance neto de '
                    'bicicletas por estación para un período.',
    )
    parser.add_argument('--entrada', required=True,
                        help='archivo de viajes en formato .csv o .json')
    parser.add_argument('--desde', required=True, type=fecha_argumento,
                        help='primer día del período (AAAA-MM-DD), incluido')
    parser.add_argument('--hasta', required=True, type=fecha_argumento,
                        help='último día del período (AAAA-MM-DD), incluido')
    parser.add_argument('--salida', default='outputs',
                        help='directorio de resultados (por defecto: outputs)')
    return parser


def mostrar_resultados(reporte, resumen, rutas):
    registros = resumen['registros']
    periodo = resumen['periodo']
    movimientos = resumen['movimientos']
    print('EcoBici Data Analyzer - Reporte de movimientos por estación')
    print(f'Archivo de entrada: {resumen["archivo_entrada"]}')
    print(f'Período: {periodo["desde"]} a {periodo["hasta"]} '
          '(según fecha de inicio, ambos días incluidos)')
    print(f'Registros: {registros["originales"]} originales, '
          f'{registros["validos"]} válidos, '
          f'{registros["rechazados"]} rechazados')
    print(f'Viajes seleccionados: {resumen["viajes_seleccionados"]}')
    print()
    print(reporte.to_string(index=False))
    print()
    print(f'Totales: {movimientos["total_salidas"]} salidas, '
          f'{movimientos["total_llegadas"]} llegadas, '
          f'suma de balances = {movimientos["suma_balances"]}')
    print('Comprobaciones:')
    for nombre, cumple in resumen['comprobaciones'].items():
        print(f'  [{"OK" if cumple else "FALLA"}] {nombre}')
    print('Archivos generados:')
    for ruta in rutas.values():
        print(f'  {ruta}')


def main(argumentos=None):
    """Ejecuta el análisis; devuelve 0 si termina bien y 1 si hay un error."""
    args = crear_parser().parse_args(argumentos)
    try:
        fuente = crear_fuente(args.entrada)
        reporte, rechazados, resumen = AplicacionEcobici(fuente).ejecutar(
            args.desde, args.hasta)
        rutas = exportar_resultados(reporte, rechazados, resumen, args.salida)
    except (ErrorDatos, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    mostrar_resultados(reporte, resumen, rutas)
    return 0


if __name__ == '__main__':
    sys.exit(main())
