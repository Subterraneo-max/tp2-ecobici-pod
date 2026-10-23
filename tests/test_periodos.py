"""Pruebas de selección de períodos (categoría C)."""

import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.fuentes import ErrorDatos, FuenteCSV, FuenteJSON
from src.pipeline import limpiar_viajes, seleccionar_periodo, validar_periodo

DATA = Path(__file__).resolve().parent.parent / 'data'


def viajes_validos(*inicios_y_fines):
    """Construye viajes válidos ya limpios a partir de pares (inicio, fin)."""
    registros = [
        {'viaje_id': f'ECO-{numero:04d}', 'inicio': inicio, 'fin': fin,
         'estacion_origen': 'Estacion_A', 'estacion_destino': 'Estacion_B'}
        for numero, (inicio, fin) in enumerate(inicios_y_fines, start=1)
    ]
    validos, _ = limpiar_viajes(pd.DataFrame(registros))
    return validos


def ids(tabla):
    return list(tabla['viaje_id'])


class PruebasSeleccionPeriodo(unittest.TestCase):

    def setUp(self):
        self.viajes = viajes_validos(
            ('2026-09-30 23:59:59', '2026-10-01 00:10:00'),  # ECO-0001
            ('2026-10-01 00:00:00', '2026-10-01 00:20:00'),  # ECO-0002
            ('2026-10-02 12:00:00', '2026-10-02 12:30:00'),  # ECO-0003
            ('2026-10-03 23:59:59', '2026-10-04 00:15:00'),  # ECO-0004
            ('2026-10-04 00:00:00', '2026-10-04 00:30:00'),  # ECO-0005
        )

    def test_periodo_correcto(self):
        seleccion = seleccionar_periodo(self.viajes,
                                        '2026-10-02', '2026-10-03')
        self.assertEqual(ids(seleccion), ['ECO-0003', 'ECO-0004'])

    def test_primer_dia_incluido_desde_medianoche(self):
        seleccion = seleccionar_periodo(self.viajes,
                                        '2026-10-01', '2026-10-01')
        self.assertEqual(ids(seleccion), ['ECO-0002'])

    def test_ultimo_dia_incluido_hasta_el_ultimo_segundo(self):
        seleccion = seleccionar_periodo(self.viajes,
                                        '2026-10-03', '2026-10-03')
        self.assertEqual(ids(seleccion), ['ECO-0004'])

    def test_viajes_fuera_del_rango_se_excluyen(self):
        seleccion = seleccionar_periodo(self.viajes,
                                        '2026-10-01', '2026-10-03')
        self.assertNotIn('ECO-0001', ids(seleccion))  # un segundo antes
        self.assertNotIn('ECO-0005', ids(seleccion))  # medianoche siguiente

    def test_viaje_que_finaliza_fuera_del_periodo_se_incluye(self):
        # ECO-0004 empieza el 3/10 y termina el 4/10: cuenta por su inicio.
        self.assertIn('ECO-0004', ids(
            seleccionar_periodo(self.viajes, '2026-10-02', '2026-10-03')))
        self.assertNotIn('ECO-0004', ids(
            seleccionar_periodo(self.viajes, '2026-10-04', '2026-10-04')))

    def test_fecha_inicial_posterior_a_la_final(self):
        with self.assertRaisesRegex(ErrorDatos, 'posterior a la final'):
            seleccionar_periodo(self.viajes, '2026-10-05', '2026-10-01')

    def test_periodo_sin_viajes(self):
        seleccion = seleccionar_periodo(self.viajes,
                                        '2026-11-01', '2026-11-30')
        self.assertTrue(seleccion.empty)
        self.assertEqual(list(seleccion.columns), list(self.viajes.columns))

    def test_parametros_invalidos(self):
        for valor in ('2026/10/01', '2026-10-1', '01-10-2026', '2026-02-30',
                      '2026-10-01 08:00:00', '', None, 20261001,
                      datetime(2026, 10, 1, 8, 0)):
            with self.subTest(valor=valor):
                with self.assertRaises(ErrorDatos):
                    validar_periodo(valor, '2026-10-07')

    def test_acepta_objetos_date(self):
        self.assertEqual(validar_periodo(date(2026, 10, 1), '2026-10-07'),
                         (date(2026, 10, 1), date(2026, 10, 7)))

    def test_requiere_inicio_convertido_a_fecha(self):
        crudo = self.viajes.astype({'inicio': str})
        with self.assertRaisesRegex(ErrorDatos, 'limpiar_viajes'):
            seleccionar_periodo(crudo, '2026-10-01', '2026-10-07')

    def test_seleccion_determinista_y_entrada_intacta(self):
        empate = viajes_validos(
            ('2026-10-02 10:00:00', '2026-10-02 10:30:00'),
            ('2026-10-01 09:00:00', '2026-10-01 09:30:00'),
            ('2026-10-02 10:00:00', '2026-10-02 10:10:00'),
        )
        desordenado = empate.iloc[[2, 0, 1]]
        copia = desordenado.copy(deep=True)
        primera = seleccionar_periodo(desordenado, '2026-10-01', '2026-10-02')
        segunda = seleccionar_periodo(empate, '2026-10-01', '2026-10-02')
        self.assertEqual(ids(primera), ['ECO-0002', 'ECO-0001', 'ECO-0003'])
        pd.testing.assert_frame_equal(primera, segunda)
        pd.testing.assert_frame_equal(desordenado, copia)

    def test_igualdad_de_seleccion_csv_json(self):
        selecciones = []
        for fuente in (FuenteCSV(DATA / 'viajes.csv'),
                       FuenteJSON(DATA / 'viajes.json')):
            validos, _ = limpiar_viajes(fuente.cargar())
            selecciones.append(
                seleccionar_periodo(validos, '2026-10-01', '2026-10-07'))
        pd.testing.assert_frame_equal(*selecciones)
        self.assertEqual(len(selecciones[0]), 48)

    def test_viaje_limite_del_conjunto_de_datos(self):
        # ECO-0048: inicio 2026-10-07 23:50, fin 2026-10-08 00:15.
        validos, _ = limpiar_viajes(FuenteCSV(DATA / 'viajes.csv').cargar())
        primera_semana = seleccionar_periodo(validos,
                                             '2026-10-01', '2026-10-07')
        resto = seleccionar_periodo(validos, '2026-10-08', '2026-10-15')
        self.assertEqual(ids(primera_semana)[-1], 'ECO-0048')
        self.assertNotIn('ECO-0048', ids(resto))
        self.assertEqual(len(primera_semana) + len(resto), 80)


if __name__ == '__main__':
    unittest.main()
