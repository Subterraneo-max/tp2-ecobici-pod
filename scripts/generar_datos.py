"""Genera el conjunto sintético de viajes de EcoBici Data Analyzer.

Produce data/viajes.csv y data/viajes.json con la misma información:
80 viajes válidos y 8 registros inválidos diseñados a propósito.

Uso, desde la raíz del proyecto:
    python scripts/generar_datos.py
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEMILLA = 42
ESTACIONES = tuple(f'Estacion_{letra}' for letra in 'ABCDEF')
COLUMNAS = ('viaje_id', 'inicio', 'fin', 'estacion_origen', 'estacion_destino')
FORMATO = '%Y-%m-%d %H:%M:%S'
PRIMER_DIA = datetime(2026, 10, 1)
CANTIDAD_DIAS = 15
CANTIDAD_ALEATORIOS = 78
PROBABILIDAD_CIRCULAR = 0.1
DIRECTORIO_DATOS = Path(__file__).resolve().parent.parent / 'data'

# Dos viajes válidos fijos para documentar casos límite del período:
# uno empieza el 7/10 y termina el 8/10; el otro es un recorrido circular.
VIAJES_DISENADOS = (
    (datetime(2026, 10, 7, 23, 50), 25, 'Estacion_B', 'Estacion_E'),
    (datetime(2026, 10, 1, 7, 5), 40, 'Estacion_C', 'Estacion_C'),
)


def generar_viajes_validos(rng):
    """Devuelve 80 viajes válidos ordenados por inicio, con ids correlativos.
    """
    viajes = list(VIAJES_DISENADOS)
    for _ in range(CANTIDAD_ALEATORIOS):
        dia = PRIMER_DIA + timedelta(days=rng.randrange(CANTIDAD_DIAS))
        # Inicio entre 06:00 y 22:59 y duración de 4 a 60 minutos: el viaje
        # termina el mismo día y nunca después del 15 de octubre.
        inicio = dia + timedelta(hours=rng.randint(6, 22),
                                 minutes=rng.randrange(60))
        duracion = rng.randint(4, 60)
        origen = rng.choice(ESTACIONES)
        if rng.random() < PROBABILIDAD_CIRCULAR:
            destino = origen
        else:
            destino = rng.choice([e for e in ESTACIONES if e != origen])
        viajes.append((inicio, duracion, origen, destino))

    viajes.sort(key=lambda viaje: viaje[0])
    return [
        {
            'viaje_id': f'ECO-{numero:04d}',
            'inicio': inicio.strftime(FORMATO),
            'fin': (inicio + timedelta(minutes=duracion)).strftime(FORMATO),
            'estacion_origen': origen,
            'estacion_destino': destino,
        }
        for numero, (inicio, duracion, origen, destino)
        in enumerate(viajes, start=1)
    ]


def generar_registros_invalidos():
    """Devuelve 8 registros con errores deliberados (uno o más por fila).

    El identificador ECO-0081 aparece dos veces: la política de duplicados
    rechaza ambos registros, por lo que el total de válidos sigue siendo 80.
    """
    return [
        {'viaje_id': 'ECO-0081', 'inicio': '2026-10-03 09:00:00',
         'fin': '2026-10-03 09:20:00', 'estacion_origen': 'Estacion_A',
         'estacion_destino': 'Estacion_B'},
        {'viaje_id': 'ECO-0081', 'inicio': '2026-10-03 10:15:00',
         'fin': '2026-10-03 10:40:00', 'estacion_origen': 'Estacion_D',
         'estacion_destino': 'Estacion_A'},
        # 31 de septiembre: respeta el patrón textual pero no existe.
        {'viaje_id': 'ECO-0082', 'inicio': '2026-09-31 08:00:00',
         'fin': '2026-10-01 08:30:00', 'estacion_origen': 'Estacion_B',
         'estacion_destino': 'Estacion_C'},
        # Hora 25: respeta el patrón textual pero no es una hora válida.
        {'viaje_id': 'ECO-0083', 'inicio': '2026-10-06 18:40:00',
         'fin': '2026-10-06 25:10:00', 'estacion_origen': 'Estacion_E',
         'estacion_destino': 'Estacion_F'},
        # Inconsistencia temporal: termina antes de empezar.
        {'viaje_id': 'ECO-0084', 'inicio': '2026-10-09 14:30:00',
         'fin': '2026-10-09 14:05:00', 'estacion_origen': 'Estacion_F',
         'estacion_destino': 'Estacion_A'},
        {'viaje_id': 'ECO-0085', 'inicio': '2026-10-11 07:45:00',
         'fin': '2026-10-11 08:10:00', 'estacion_origen': None,
         'estacion_destino': 'Estacion_D'},
        {'viaje_id': 'ECO-0086', 'inicio': '2026-10-12 19:00:00',
         'fin': '2026-10-12 19:35:00', 'estacion_origen': 'Estacion_C',
         'estacion_destino': None},
        # Identificador que no respeta el patrón ECO-NNNN.
        {'viaje_id': 'ECO-87', 'inicio': '2026-10-14 12:00:00',
         'fin': '2026-10-14 12:30:00', 'estacion_origen': 'Estacion_A',
         'estacion_destino': 'Estacion_E'},
    ]


def mezclar_registros(validos, invalidos, rng):
    """Inserta los inválidos en posiciones pseudoaleatorias reproducibles."""
    registros = list(validos)
    for registro in invalidos:
        registros.insert(rng.randrange(len(registros) + 1), registro)
    return registros


def guardar_csv(registros, ruta):
    with ruta.open('w', encoding='utf-8', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS,
                                  lineterminator='\n')
        escritor.writeheader()
        escritor.writerows(registros)


def guardar_json(registros, ruta):
    with ruta.open('w', encoding='utf-8', newline='\n') as archivo:
        json.dump(registros, archivo, ensure_ascii=False, indent=2)
        archivo.write('\n')


def main():
    rng = random.Random(SEMILLA)
    validos = generar_viajes_validos(rng)
    invalidos = generar_registros_invalidos()
    registros = mezclar_registros(validos, invalidos, rng)

    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    guardar_csv(registros, DIRECTORIO_DATOS / 'viajes.csv')
    guardar_json(registros, DIRECTORIO_DATOS / 'viajes.json')
    print(f'Registros generados: {len(registros)} '
          f'({len(validos)} válidos, {len(invalidos)} inválidos)')
    print(f'Archivos: {DIRECTORIO_DATOS / "viajes.csv"} y '
          f'{DIRECTORIO_DATOS / "viajes.json"}')


if __name__ == '__main__':
    main()
