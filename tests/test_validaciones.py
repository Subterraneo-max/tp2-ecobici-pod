"""Pruebas de validación y limpieza de registros (categoría B)."""

import unittest
from pathlib import Path

import pandas as pd

from src.fuentes import ErrorDatos, FuenteCSV, FuenteJSON
from src.pipeline import (fecha_hora_valida, id_valido, limpiar_viajes,
                          validar_esquema)

DATA = Path(__file__).resolve().parent.parent / 'data'


def viaje(numero=1, **cambios):
    """Registro válido de referencia; los argumentos reemplazan campos."""
    registro = {
        'viaje_id': f'ECO-{numero:04d}',
        'inicio': '2026-10-01 08:00:00',
        'fin': '2026-10-01 08:20:00',
        'estacion_origen': 'Estacion_A',
        'estacion_destino': 'Estacion_B',
    }
    registro.update(cambios)
    return registro


def tabla(*registros):
    return pd.DataFrame(list(registros))


def motivo_de(rechazados, viaje_id):
    return rechazados.loc[rechazados['viaje_id'] == viaje_id, 'motivo'].iloc[0]


class PruebasReglasIndividuales(unittest.TestCase):

    def test_identificador_valido(self):
        for valor in ('ECO-0001', 'ECO-9999'):
            with self.subTest(valor=valor):
                self.assertTrue(id_valido(valor))

    def test_identificador_invalido(self):
        # 'ECO-' seguido de dígitos arábigo-índicos: \d los aceptaría, pero
        # [0-9] sólo admite dígitos ASCII.
        for valor in ('ECO-1', 'eco-0001', 'ECO-00012', 'ECO-0001 ',
                      'XECO-0001', 'ECO_0001', 'ECO-٠١٢٣',
                      None, 1):
            with self.subTest(valor=valor):
                self.assertFalse(id_valido(valor))

    def test_fecha_correcta(self):
        for valor in ('2026-10-01 08:15:00', '2028-02-29 23:59:59'):
            with self.subTest(valor=valor):
                self.assertTrue(fecha_hora_valida(valor))

    def test_fecha_inexistente(self):
        # Respetan el patrón textual pero no existen en el calendario.
        for valor in ('2026-02-31 10:00:00', '2026-09-31 08:00:00',
                      '2027-02-29 10:00:00', '2026-13-01 10:00:00'):
            with self.subTest(valor=valor):
                self.assertFalse(fecha_hora_valida(valor))

    def test_fecha_mal_formada(self):
        for valor in ('2026/10/01 08:00:00', '01-10-2026 08:00:00',
                      '2026-10-01', '2026-10-01T08:00:00',
                      '2026-10-1 8:00:00', '', None):
            with self.subTest(valor=valor):
                self.assertFalse(fecha_hora_valida(valor))

    def test_hora_invalida(self):
        for valor in ('2026-10-01 24:00:00', '2026-10-01 25:10:00',
                      '2026-10-01 10:60:00', '2026-10-01 10:00:61'):
            with self.subTest(valor=valor):
                self.assertFalse(fecha_hora_valida(valor))


class PruebasLimpieza(unittest.TestCase):

    def test_identificador_duplicado(self):
        validos, rechazados = limpiar_viajes(
            tabla(viaje(1), viaje(1), viaje(2)))
        self.assertEqual(list(validos['viaje_id']), ['ECO-0002'])
        self.assertEqual(list(rechazados['motivo']),
                         ['viaje_id duplicado', 'viaje_id duplicado'])

    def test_politica_duplicados_rechaza_todas_las_copias(self):
        entrada = tabla(viaje(5), viaje(1),
                        viaje(5, estacion_origen='Estacion_C'),
                        viaje(5, estacion_destino='Estacion_D'))
        validos, rechazados = limpiar_viajes(entrada)
        self.assertEqual(list(validos['viaje_id']), ['ECO-0001'])
        self.assertEqual(list(rechazados['registro']), [1, 3, 4])

    def test_fin_anterior_al_inicio(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, fin='2026-10-01 07:59:59')))
        self.assertEqual(motivo_de(rechazados, 'ECO-0002'),
                         'fin no posterior al inicio')

    def test_duracion_cero(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, fin='2026-10-01 08:00:00')))
        self.assertEqual(motivo_de(rechazados, 'ECO-0002'),
                         'fin no posterior al inicio')

    def test_estacion_origen_faltante(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, estacion_origen=None)))
        self.assertEqual(motivo_de(rechazados, 'ECO-0002'),
                         'estacion_origen faltante')

    def test_estacion_destino_faltante(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, estacion_destino=None)))
        self.assertEqual(motivo_de(rechazados, 'ECO-0002'),
                         'estacion_destino faltante')

    def test_campos_vacios_o_solo_espacios(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, estacion_origen=''),
            viaje(3, estacion_destino='   '), viaje(4, inicio=' ')))
        self.assertEqual(
            list(rechazados['motivo']),
            ['estacion_origen faltante', 'estacion_destino faltante',
             'inicio faltante'])

    def test_datos_nulos(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, viaje_id=None), viaje(3, fin=float('nan'))))
        self.assertEqual(list(rechazados['motivo']),
                         ['viaje_id faltante', 'fin faltante'])

    def test_nulos_en_identificador_no_cuentan_como_duplicados(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, viaje_id=None), viaje(3, viaje_id=None)))
        self.assertEqual(list(rechazados['motivo']),
                         ['viaje_id faltante', 'viaje_id faltante'])

    def test_estructura_invalida(self):
        with self.assertRaises(TypeError):
            validar_esquema([viaje(1)])
        with self.assertRaisesRegex(ErrorDatos, 'Faltan columnas: fin'):
            limpiar_viajes(tabla(viaje(1)).drop(columns='fin'))
        with self.assertRaisesRegex(ErrorDatos, 'vacía'):
            limpiar_viajes(pd.DataFrame(columns=list(viaje(1))))

    def test_registros_mezclados(self):
        entrada = tabla(viaje(1), viaje(2, viaje_id='ECO-2'), viaje(3),
                        viaje(4, inicio='2026-02-30 08:00:00'), viaje(5))
        validos, rechazados = limpiar_viajes(entrada)
        self.assertEqual(list(validos['viaje_id']),
                         ['ECO-0001', 'ECO-0003', 'ECO-0005'])
        self.assertEqual(list(rechazados['viaje_id']),
                         ['ECO-2', 'ECO-0004'])

    def test_rechazo_con_varios_motivos(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, viaje_id='ECO-X', fin='2026-10-01 25:00:00',
                            estacion_destino=None)))
        self.assertEqual(
            rechazados.loc[0, 'motivo'],
            'viaje_id con formato inválido; fin inválido; '
            'estacion_destino faltante')

    def test_conservacion_de_registros_y_entrada_intacta(self):
        entrada = tabla(viaje(1), viaje(1), viaje(2, inicio='x'), viaje(3))
        copia = entrada.copy(deep=True)
        validos, rechazados = limpiar_viajes(entrada)
        self.assertEqual(len(validos) + len(rechazados), len(entrada))
        pd.testing.assert_frame_equal(entrada, copia)

    def test_rechazados_conservan_valores_originales(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, estacion_origen='  ', fin='ayer')))
        fila = rechazados.iloc[0]
        self.assertEqual(fila['registro'], 2)
        self.assertEqual(fila['estacion_origen'], '  ')
        self.assertEqual(fila['fin'], 'ayer')

    def test_viaje_circular_es_valido(self):
        validos, rechazados = limpiar_viajes(tabla(
            viaje(1, estacion_destino='Estacion_A')))
        self.assertEqual(len(validos), 1)
        self.assertTrue(rechazados.empty)

    def test_errores_de_conversion_se_registran(self):
        _, rechazados = limpiar_viajes(tabla(
            viaje(1), viaje(2, inicio='ayer'), viaje(3, fin='N/A')))
        self.assertEqual(list(rechazados['motivo']),
                         ['inicio inválido', 'fin inválido'])

    def test_espacios_externos_se_normalizan(self):
        validos, _ = limpiar_viajes(tabla(
            viaje(1, viaje_id=' ECO-0001 ', estacion_origen=' Estacion_A')))
        self.assertEqual(validos.loc[0, 'viaje_id'], 'ECO-0001')
        self.assertEqual(validos.loc[0, 'estacion_origen'], 'Estacion_A')

    def test_valores_no_textuales_se_validan_por_su_texto(self):
        # Defecto D5: un id entero o un Timestamp se informaban como faltantes.
        validos, rechazados = limpiar_viajes(tabla(
            viaje(1, inicio=pd.Timestamp('2026-10-01 08:00:00')),
            viaje(2, viaje_id=2)))
        self.assertEqual(list(validos['viaje_id']), ['ECO-0001'])
        self.assertEqual(list(rechazados['motivo']),
                         ['viaje_id con formato inválido'])

    def test_sin_viajes_validos_detiene_el_flujo(self):
        with self.assertRaisesRegex(ErrorDatos, 'No quedan viajes válidos'):
            limpiar_viajes(tabla(viaje(1, inicio='x'), viaje(2, fin=None)))

    def test_independencia_del_formato_de_entrada(self):
        validos_csv, rechazados_csv = limpiar_viajes(
            FuenteCSV(DATA / 'viajes.csv').cargar())
        validos_json, rechazados_json = limpiar_viajes(
            FuenteJSON(DATA / 'viajes.json').cargar())
        pd.testing.assert_frame_equal(validos_csv, validos_json)
        pd.testing.assert_frame_equal(rechazados_csv, rechazados_json)

    def test_motivos_del_conjunto_de_datos(self):
        _, rechazados = limpiar_viajes(FuenteCSV(DATA / 'viajes.csv').cargar())
        esperado = {
            'ECO-0081': 'viaje_id duplicado',
            'ECO-0082': 'inicio inválido',
            'ECO-0083': 'fin inválido',
            'ECO-0084': 'fin no posterior al inicio',
            'ECO-0085': 'estacion_origen faltante',
            'ECO-0086': 'estacion_destino faltante',
            'ECO-87': 'viaje_id con formato inválido',
        }
        self.assertEqual(len(rechazados), 8)
        obtenido = dict(zip(rechazados['viaje_id'], rechazados['motivo']))
        self.assertEqual(obtenido, esperado)


if __name__ == '__main__':
    unittest.main()
