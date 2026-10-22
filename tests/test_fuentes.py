"""Pruebas de lectura de archivos (categoría A)."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.fuentes import (ErrorDatos, FuenteCSV, FuenteDatos, FuenteJSON,
                         crear_fuente)
from src.pipeline import validar_esquema

DATA = Path(__file__).resolve().parent.parent / 'data'
COLUMNAS = ['viaje_id', 'inicio', 'fin', 'estacion_origen', 'estacion_destino']


class PruebasFuentes(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.directorio = Path(self._temporal.name)

    def tearDown(self):
        self._temporal.cleanup()

    def escribir(self, nombre, contenido):
        ruta = self.directorio / nombre
        ruta.write_text(contenido, encoding='utf-8')
        return ruta

    def test_csv_correcto(self):
        tabla = FuenteCSV(DATA / 'viajes.csv').cargar()
        self.assertEqual(tabla.shape, (88, 5))
        self.assertEqual(list(tabla.columns), COLUMNAS)

    def test_json_correcto(self):
        tabla = FuenteJSON(DATA / 'viajes.json').cargar()
        self.assertEqual(tabla.shape, (88, 5))
        self.assertEqual(list(tabla.columns), COLUMNAS)

    def test_equivalencia_csv_json(self):
        csv = FuenteCSV(DATA / 'viajes.csv').cargar()
        json = FuenteJSON(DATA / 'viajes.json').cargar()
        pd.testing.assert_frame_equal(csv, json)

    def test_archivo_inexistente(self):
        for clase in (FuenteCSV, FuenteJSON):
            with self.subTest(clase=clase.__name__):
                with self.assertRaisesRegex(FileNotFoundError, 'No existe'):
                    clase(self.directorio / 'ausente.txt').cargar()

    def test_archivo_vacio(self):
        for clase, nombre in ((FuenteCSV, 'vacio.csv'),
                              (FuenteJSON, 'vacio.json')):
            with self.subTest(clase=clase.__name__):
                ruta = self.escribir(nombre, '')
                with self.assertRaisesRegex(ErrorDatos, 'vacío'):
                    clase(ruta).cargar()

    def test_json_mal_formado(self):
        ruta = self.escribir('roto.json', '[{"viaje_id": "ECO-0001",]')
        with self.assertRaisesRegex(ErrorDatos, 'JSON mal formado'):
            FuenteJSON(ruta).cargar()

    def test_csv_mal_formado(self):
        ruta = self.escribir('roto.csv', 'a,b\n1,2\n3,4,5,6\n')
        with self.assertRaisesRegex(ErrorDatos, 'CSV mal formado'):
            FuenteCSV(ruta).cargar()

    def test_json_estructura_incorrecta(self):
        for contenido in ('{"viajes": []}', '[1, 2, 3]', '"texto"'):
            with self.subTest(contenido=contenido):
                ruta = self.escribir('estructura.json', contenido)
                with self.assertRaisesRegex(ErrorDatos, 'lista de objetos'):
                    FuenteJSON(ruta).cargar()

    def test_json_con_valor_anidado(self):
        ruta = self.escribir(
            'anidado.json', '[{"viaje_id": "ECO-0001", "fin": {"h": 1}}]')
        with self.assertRaisesRegex(ErrorDatos, 'Valor no admitido'):
            FuenteJSON(ruta).cargar()

    def test_conserva_identificadores_como_texto(self):
        ruta = self.escribir('ids.csv', 'viaje_id,codigo\nECO-0001,0007\n')
        tabla = FuenteCSV(ruta).cargar()
        self.assertEqual(tabla.loc[0, 'viaje_id'], 'ECO-0001')
        self.assertEqual(tabla.loc[0, 'codigo'], '0007')

    def test_tipos_compatibles_entre_formatos(self):
        # Defecto D1: los faltantes son NaN (pd.isna), no None.
        for tabla in (FuenteCSV(DATA / 'viajes.csv').cargar(),
                      FuenteJSON(DATA / 'viajes.json').cargar()):
            valores = tabla.to_numpy().ravel()
            faltantes = [v for v in valores if pd.isna(v)]
            presentes = [v for v in valores if not pd.isna(v)]
            self.assertEqual(len(faltantes), 2)
            self.assertTrue(all(isinstance(v, str) for v in presentes))

    def test_json_numeros_se_convierten_a_texto(self):
        ruta = self.escribir('numeros.json', '[{"viaje_id": 15, "x": null}]')
        tabla = FuenteJSON(ruta).cargar()
        self.assertEqual(tabla.loc[0, 'viaje_id'], '15')
        self.assertTrue(pd.isna(tabla.loc[0, 'x']))

    def test_crear_fuente_segun_extension(self):
        self.assertIsInstance(crear_fuente('a.csv'), FuenteCSV)
        self.assertIsInstance(crear_fuente('a.JSON'), FuenteJSON)
        with self.assertRaisesRegex(ErrorDatos, 'Formato no soportado'):
            crear_fuente('a.xlsx')

    def test_csv_y_json_con_bom_utf8(self):
        # Defecto D2: el JSON con BOM se rechazaba como mal formado.
        fila = ('ECO-0001', '2026-10-01 08:00:00', '2026-10-01 08:20:00',
                'Estacion_A', 'Estacion_B')
        csv = self.directorio / 'bom.csv'
        csv.write_text(','.join(COLUMNAS) + '\n' + ','.join(fila) + '\n',
                       encoding='utf-8-sig')
        json = self.directorio / 'bom.json'
        json.write_text(pd.DataFrame([fila], columns=COLUMNAS)
                        .to_json(orient='records'), encoding='utf-8-sig')
        pd.testing.assert_frame_equal(FuenteCSV(csv).cargar(),
                                      FuenteJSON(json).cargar())

    def test_json_lista_vacia_se_informa_como_tabla_vacia(self):
        # Defecto D3: se informaba "Faltan columnas" para un JSON sin registros.
        ruta = self.escribir('vacia.json', '[]')
        with self.assertRaisesRegex(ErrorDatos, 'vacía'):
            validar_esquema(FuenteJSON(ruta).cargar())

    def test_ruta_que_es_un_directorio(self):
        # Defecto D4: un directorio se informaba como archivo inexistente.
        with self.assertRaisesRegex(ErrorDatos, 'no es un archivo'):
            FuenteCSV(self.directorio).cargar()

    def test_fuente_abstracta_no_se_instancia(self):
        with self.assertRaises(TypeError):
            FuenteDatos('data/viajes.csv')


if __name__ == '__main__':
    unittest.main()
