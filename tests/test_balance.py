"""Pruebas de la clase BalanceEstacion y del balance por estación (categoría D)."""

import unittest
from pathlib import Path

import pandas as pd

from src.dominio import BalanceEstacion
from src.fuentes import ErrorDatos, FuenteCSV
from src.pipeline import (generar_balance, limpiar_viajes, listar_estaciones,
                          registrar_movimientos, seleccionar_periodo,
                          verificar_balance, verificar_registros)

DATA = Path(__file__).resolve().parent.parent / 'data'


def viajes(*recorridos):
    """Viajes válidos y limpios a partir de pares (origen, destino)."""
    registros = [
        {'viaje_id': f'ECO-{numero:04d}', 'inicio': '2026-10-01 08:00:00',
         'fin': '2026-10-01 08:30:00', 'estacion_origen': origen,
         'estacion_destino': destino}
        for numero, (origen, destino) in enumerate(recorridos, start=1)
    ]
    validos, _ = limpiar_viajes(pd.DataFrame(registros))
    return validos


def reporte_de(tabla, estaciones=()):
    return generar_balance(registrar_movimientos(tabla, estaciones))


def fila(reporte, estacion):
    return reporte.set_index('estacion').loc[estacion].to_dict()


class PruebasBalanceEstacion(unittest.TestCase):

    def test_registrar_una_llegada(self):
        balance = BalanceEstacion('Estacion_A')
        balance.registrar_llegada()
        self.assertEqual((balance.llegadas, balance.salidas), (1, 0))

    def test_registrar_una_salida(self):
        balance = BalanceEstacion('Estacion_A')
        balance.registrar_salida()
        self.assertEqual((balance.llegadas, balance.salidas), (0, 1))

    def test_balance_positivo(self):
        balance = BalanceEstacion('Estacion_A')
        balance.registrar_llegada(3)
        balance.registrar_salida()
        self.assertEqual(balance.calcular_balance(), 2)

    def test_balance_negativo(self):
        balance = BalanceEstacion('Estacion_A')
        balance.registrar_llegada()
        balance.registrar_salida(4)
        self.assertEqual(balance.calcular_balance(), -3)

    def test_balance_cero(self):
        nueva = BalanceEstacion('Estacion_A')
        self.assertEqual(nueva.calcular_balance(), 0)
        nueva.registrar_llegada(2)
        nueva.registrar_salida(2)
        self.assertEqual(nueva.calcular_balance(), 0)

    def test_validaciones_de_la_clase(self):
        for nombre in ('', '   ', None, 5):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ValueError):
                    BalanceEstacion(nombre)
        balance = BalanceEstacion('Estacion_A')
        for cantidad, error in ((0, ValueError), (-1, ValueError),
                                (1.5, TypeError), (True, TypeError)):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(error):
                    balance.registrar_llegada(cantidad)
        self.assertEqual(balance.llegadas, 0)

    def test_conteos_encapsulados(self):
        balance = BalanceEstacion('Estacion_A')
        with self.assertRaises(AttributeError):
            balance.llegadas = 10


class PruebasMovimientos(unittest.TestCase):

    def test_viaje_de_a_hacia_b(self):
        reporte = reporte_de(viajes(('Estacion_A', 'Estacion_B')))
        self.assertEqual(fila(reporte, 'Estacion_A'),
                         {'salidas': 1, 'llegadas': 0, 'balance': -1})
        self.assertEqual(fila(reporte, 'Estacion_B'),
                         {'salidas': 0, 'llegadas': 1, 'balance': 1})

    def test_viaje_circular(self):
        reporte = reporte_de(viajes(('Estacion_C', 'Estacion_C')))
        self.assertEqual(len(reporte), 1)
        self.assertEqual(fila(reporte, 'Estacion_C'),
                         {'salidas': 1, 'llegadas': 1, 'balance': 0})

    def test_dos_viajes_en_sentidos_opuestos(self):
        reporte = reporte_de(viajes(('Estacion_A', 'Estacion_B'),
                                    ('Estacion_B', 'Estacion_A')))
        for estacion in ('Estacion_A', 'Estacion_B'):
            with self.subTest(estacion=estacion):
                self.assertEqual(fila(reporte, estacion),
                                 {'salidas': 1, 'llegadas': 1, 'balance': 0})

    def test_conservacion_de_llegadas_y_salidas(self):
        tabla = viajes(('Estacion_A', 'Estacion_B'), ('Estacion_A', 'Estacion_C'),
                       ('Estacion_C', 'Estacion_C'), ('Estacion_B', 'Estacion_A'),
                       ('Estacion_D', 'Estacion_A'))
        reporte = reporte_de(tabla)
        self.assertEqual(int(reporte['llegadas'].sum()), 5)
        self.assertEqual(int(reporte['salidas'].sum()), 5)
        self.assertEqual(fila(reporte, 'Estacion_A'),
                         {'salidas': 2, 'llegadas': 2, 'balance': 0})
        self.assertEqual(fila(reporte, 'Estacion_D'),
                         {'salidas': 1, 'llegadas': 0, 'balance': -1})

    def test_suma_de_balances_igual_a_cero_en_varios_periodos(self):
        validos, _ = limpiar_viajes(FuenteCSV(DATA / 'viajes.csv').cargar())
        estaciones = listar_estaciones(validos)
        for desde, hasta in (('2026-10-01', '2026-10-15'),
                             ('2026-10-01', '2026-10-07'),
                             ('2026-10-08', '2026-10-08'),
                             ('2026-12-01', '2026-12-31')):
            with self.subTest(desde=desde, hasta=hasta):
                seleccion = seleccionar_periodo(validos, desde, hasta)
                reporte = reporte_de(seleccion, estaciones)
                self.assertEqual(int(reporte['balance'].sum()), 0)
                verificar_balance(reporte, len(seleccion))

    def test_registros_invalidos_no_alteran_los_conteos(self):
        buenos = [('ECO-0001', 'Estacion_A', 'Estacion_B'),
                  ('ECO-0002', 'Estacion_B', 'Estacion_C')]
        malos = [('ECO-0003', None, 'Estacion_A'),
                 ('ECO-3', 'Estacion_A', 'Estacion_C'),
                 ('ECO-0004', 'Estacion_C', 'Estacion_A'),
                 ('ECO-0004', 'Estacion_C', 'Estacion_B')]

        def reporte_para(recorridos):
            tabla = pd.DataFrame(
                [{'viaje_id': i, 'inicio': '2026-10-01 08:00:00',
                  'fin': '2026-10-01 08:30:00', 'estacion_origen': o,
                  'estacion_destino': d} for i, o, d in recorridos])
            validos, _ = limpiar_viajes(tabla)
            return reporte_de(validos)

        pd.testing.assert_frame_equal(reporte_para(buenos),
                                      reporte_para(buenos + malos))

    def test_estaciones_sin_movimientos_aparecen_en_cero(self):
        reporte = reporte_de(viajes(('Estacion_B', 'Estacion_A')),
                             ['Estacion_C', 'Estacion_A', 'Estacion_B'])
        self.assertEqual(list(reporte.columns),
                         ['estacion', 'salidas', 'llegadas', 'balance'])
        self.assertEqual(list(reporte['estacion']),
                         ['Estacion_A', 'Estacion_B', 'Estacion_C'])
        self.assertEqual(fila(reporte, 'Estacion_C'),
                         {'salidas': 0, 'llegadas': 0, 'balance': 0})


class PruebasVerificacion(unittest.TestCase):

    def test_verificar_balance_detecta_inconsistencias(self):
        reporte = reporte_de(viajes(('Estacion_A', 'Estacion_B')))
        self.assertTrue(all(verificar_balance(reporte, 1).values()))
        with self.assertRaisesRegex(ErrorDatos, 'total_salidas_igual_viajes'):
            verificar_balance(reporte, 2)
        alterado = reporte.copy()
        alterado.loc[0, 'balance'] = 5
        with self.assertRaisesRegex(ErrorDatos, 'suma_balances_igual_cero'):
            verificar_balance(alterado, 1)

    def test_verificar_registros_detecta_perdidas(self):
        self.assertEqual(verificar_registros(88, 80, 8),
                         {'originales_igual_validos_mas_rechazados': True})
        with self.assertRaisesRegex(ErrorDatos, 'Se perdieron registros'):
            verificar_registros(88, 79, 8)


if __name__ == '__main__':
    unittest.main()
