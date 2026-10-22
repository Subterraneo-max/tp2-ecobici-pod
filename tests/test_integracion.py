"""Pruebas de integración y de resultados exportados (categoría E)."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.fuentes import FuenteCSV, FuenteJSON
from src.main import main
from src.pipeline import AplicacionEcobici, exportar_resultados

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / 'data'

# Resultado del conjunto de datos para el 1/10 al 7/10, contrastado con un
# conteo independiente hecho con el módulo csv.
ESPERADO_PRIMERA_SEMANA = pd.DataFrame({
    'estacion': [f'Estacion_{letra}' for letra in 'ABCDEF'],
    'salidas': [7, 4, 12, 6, 13, 6],
    'llegadas': [11, 12, 8, 7, 2, 8],
    'balance': [4, 8, -4, 1, -11, 2],
})

# Conjunto pequeño con resultado calculado a mano para el 1/10 al 2/10.
VIAJES_CONOCIDOS = [
    ['ECO-0001', '2026-10-01 08:00:00', '2026-10-01 08:20:00', 'A', 'B'],
    ['ECO-0002', '2026-10-01 09:00:00', '2026-10-01 09:30:00', 'B', 'C'],
    ['ECO-0003', '2026-10-02 10:00:00', '2026-10-02 10:15:00', 'C', 'B'],
    ['ECO-0004', '2026-10-02 23:50:00', '2026-10-03 00:10:00', 'A', 'A'],
    ['ECO-0005', '2026-10-03 08:00:00', '2026-10-03 08:30:00', 'B', 'A'],
    ['ECO-0007', '2026-10-01 12:00:00', '2026-10-01 11:00:00', 'A', 'C'],
]
COLUMNAS = ['viaje_id', 'inicio', 'fin', 'estacion_origen', 'estacion_destino']


class PruebasIntegracion(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.directorio = Path(self._temporal.name)

    def tearDown(self):
        self._temporal.cleanup()

    def ejecutar(self, fuente, desde='2026-10-01', hasta='2026-10-07'):
        return AplicacionEcobici(fuente).ejecutar(desde, hasta)

    def test_flujo_csv_completo(self):
        reporte, rechazados, resumen = self.ejecutar(
            FuenteCSV(DATA / 'viajes.csv'))
        pd.testing.assert_frame_equal(reporte, ESPERADO_PRIMERA_SEMANA)
        self.assertEqual(len(rechazados), 8)
        self.assertEqual(resumen['viajes_seleccionados'], 48)
        self.assertTrue(all(resumen['comprobaciones'].values()))

    def test_flujo_json_completo(self):
        reporte, _, resumen = self.ejecutar(FuenteJSON(DATA / 'viajes.json'))
        pd.testing.assert_frame_equal(reporte, ESPERADO_PRIMERA_SEMANA)
        self.assertEqual(resumen['archivo_entrada'], 'viajes.json')
        self.assertEqual(resumen['movimientos'],
                         {'total_salidas': 48, 'total_llegadas': 48,
                          'suma_balances': 0})

    def test_csv_y_json_producen_el_mismo_resultado(self):
        reporte_csv, rechazados_csv, resumen_csv = self.ejecutar(
            FuenteCSV(DATA / 'viajes.csv'), '2026-10-01', '2026-10-15')
        reporte_json, rechazados_json, resumen_json = self.ejecutar(
            FuenteJSON(DATA / 'viajes.json'), '2026-10-01', '2026-10-15')
        pd.testing.assert_frame_equal(reporte_csv, reporte_json)
        pd.testing.assert_frame_equal(rechazados_csv, rechazados_json)
        del resumen_csv['archivo_entrada'], resumen_json['archivo_entrada']
        self.assertEqual(resumen_csv, resumen_json)

    def test_exportacion_de_csv(self):
        reporte, rechazados, resumen = self.ejecutar(
            FuenteCSV(DATA / 'viajes.csv'))
        rutas = exportar_resultados(reporte, rechazados, resumen,
                                    self.directorio / 'nuevo' / 'dir')
        pd.testing.assert_frame_equal(pd.read_csv(rutas['reporte']),
                                      ESPERADO_PRIMERA_SEMANA)
        releidos = pd.read_csv(rutas['rechazados'], dtype=str)
        self.assertEqual(list(releidos.columns), ['registro'] + COLUMNAS + ['motivo'])
        self.assertEqual(len(releidos), 8)

    def test_exportacion_de_json(self):
        reporte, rechazados, resumen = self.ejecutar(
            FuenteCSV(DATA / 'viajes.csv'))
        rutas = exportar_resultados(reporte, rechazados, resumen, self.directorio)
        with rutas['resumen'].open(encoding='utf-8') as archivo:
            releido = json.load(archivo)
        self.assertEqual(releido, resumen)
        self.assertEqual(releido['periodo']['desde'], '2026-10-01')
        self.assertEqual(releido['registros'],
                         {'originales': 88, 'validos': 80, 'rechazados': 8})

    def test_reporte_con_datos_conocidos(self):
        tabla = pd.DataFrame(VIAJES_CONOCIDOS, columns=COLUMNAS)
        ruta_csv = self.directorio / 'conocidos.csv'
        ruta_json = self.directorio / 'conocidos.json'
        tabla.to_csv(ruta_csv, index=False)
        ruta_json.write_text(tabla.to_json(orient='records'), encoding='utf-8')
        esperado = pd.DataFrame({'estacion': ['A', 'B', 'C'],
                                 'salidas': [2, 1, 1],
                                 'llegadas': [1, 2, 1],
                                 'balance': [-1, 1, 0]})
        for fuente in (FuenteCSV(ruta_csv), FuenteJSON(ruta_json)):
            with self.subTest(fuente=type(fuente).__name__):
                reporte, rechazados, resumen = self.ejecutar(
                    fuente, '2026-10-01', '2026-10-02')
                pd.testing.assert_frame_equal(reporte, esperado)
                self.assertEqual(list(rechazados['viaje_id']), ['ECO-0007'])
                self.assertEqual(resumen['viajes_seleccionados'], 4)

    def test_reporte_sin_resultados(self):
        reporte, rechazados, resumen = self.ejecutar(
            FuenteCSV(DATA / 'viajes.csv'), '2027-01-01', '2027-01-31')
        self.assertEqual(len(reporte), 6)
        self.assertTrue((reporte[['salidas', 'llegadas', 'balance']] == 0)
                        .all().all())
        self.assertEqual(resumen['viajes_seleccionados'], 0)
        self.assertTrue(all(resumen['comprobaciones'].values()))
        rutas = exportar_resultados(reporte, rechazados, resumen, self.directorio)
        self.assertEqual(len(pd.read_csv(rutas['reporte'])), 6)

    def test_determinismo_de_la_aplicacion(self):
        contenidos = []
        for nombre in ('primera', 'segunda'):
            salida = self.directorio / nombre
            with contextlib.redirect_stdout(io.StringIO()):
                codigo = main(['--entrada', str(DATA / 'viajes.csv'),
                               '--desde', '2026-10-01', '--hasta', '2026-10-15',
                               '--salida', str(salida)])
            self.assertEqual(codigo, 0)
            contenidos.append({ruta.name: ruta.read_bytes()
                               for ruta in sorted(salida.iterdir())})
        self.assertEqual(len(contenidos[0]), 3)
        self.assertEqual(contenidos[0], contenidos[1])

    def test_originales_igual_validos_mas_rechazados(self):
        for fuente in (FuenteCSV(DATA / 'viajes.csv'),
                       FuenteJSON(DATA / 'viajes.json')):
            with self.subTest(fuente=type(fuente).__name__):
                _, rechazados, resumen = self.ejecutar(fuente)
                registros = resumen['registros']
                self.assertEqual(registros['originales'], 88)
                self.assertEqual(registros['validos'] + registros['rechazados'],
                                 registros['originales'])
                self.assertEqual(registros['rechazados'], len(rechazados))

    def test_main_informa_errores_con_codigo_de_salida(self):
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), \
                contextlib.redirect_stderr(errores):
            ausente = main(['--entrada', str(self.directorio / 'no.csv'),
                            '--desde', '2026-10-01', '--hasta', '2026-10-07',
                            '--salida', str(self.directorio)])
            invertido = main(['--entrada', str(DATA / 'viajes.json'),
                              '--desde', '2026-10-07', '--hasta', '2026-10-01',
                              '--salida', str(self.directorio)])
            with self.assertRaises(SystemExit) as fecha_imposible:
                main(['--entrada', str(DATA / 'viajes.csv'),
                      '--desde', '2026-02-30', '--hasta', '2026-10-07'])
        self.assertEqual((ausente, invertido), (1, 1))
        self.assertEqual(fecha_imposible.exception.code, 2)
        self.assertIn('No existe el archivo', errores.getvalue())
        self.assertIn('posterior a la final', errores.getvalue())
        self.assertEqual(list(self.directorio.iterdir()), [])

    def test_comando_documentado_en_el_readme(self):
        entorno = dict(os.environ, PYTHONIOENCODING='utf-8')
        resultado = subprocess.run(
            [sys.executable, '-m', 'src.main', '--entrada', 'data/viajes.csv',
             '--desde', '2026-10-01', '--hasta', '2026-10-07',
             '--salida', str(self.directorio)],
            cwd=RAIZ, capture_output=True, text=True, encoding='utf-8',
            env=entorno, check=False)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn('Viajes seleccionados: 48', resultado.stdout)
        self.assertIn('[OK] suma_balances_igual_cero', resultado.stdout)


if __name__ == '__main__':
    unittest.main()
