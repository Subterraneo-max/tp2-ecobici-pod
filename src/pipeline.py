"""Flujo de procesamiento: validar, limpiar, seleccionar, contar y exportar.

Las funciones de transformación reciben tablas ya cargadas y devuelven
resultados nuevos: no leen ni escriben archivos y no modifican sus
argumentos. La escritura se concentra en exportar_resultados().
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.dominio import BalanceEstacion
from src.fuentes import ErrorDatos, FuenteDatos

COLUMNAS = ('viaje_id', 'inicio', 'fin', 'estacion_origen', 'estacion_destino')

# Un identificador es "ECO-" seguido de exactamente cuatro dígitos ASCII.
PATRON_ID = re.compile(r'ECO-[0-9]{4}')
# Forma textual de fecha y hora. No verifica el calendario: 2026-09-31 o la
# hora 25 respetan el patrón, por eso se complementa con datetime.strptime.
PATRON_FECHA_HORA = re.compile(
    r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}'
)
FORMATO_FECHA_HORA = '%Y-%m-%d %H:%M:%S'
# Parámetros del período: sólo la fecha, AAAA-MM-DD.
PATRON_FECHA = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
FORMATO_FECHA = '%Y-%m-%d'
COLUMNAS_REPORTE = ('estacion', 'salidas', 'llegadas', 'balance')


# ---------------------------------------------------------------------------
# Reglas sobre valores individuales
# ---------------------------------------------------------------------------

def texto_presente(valor):
    """True si el valor es un texto con al menos un carácter visible."""
    return isinstance(valor, str) and valor.strip() != ''


def id_valido(valor):
    """True si el valor respeta completo el patrón ECO-NNNN."""
    return isinstance(valor, str) and PATRON_ID.fullmatch(valor) is not None


def fecha_hora_valida(valor):
    """Comprueba la forma AAAA-MM-DD HH:MM:SS y que exista en el calendario."""
    if not isinstance(valor, str):
        return False
    if PATRON_FECHA_HORA.fullmatch(valor) is None:
        return False
    try:
        datetime.strptime(valor, FORMATO_FECHA_HORA)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# Esquema, normalización y limpieza
# ---------------------------------------------------------------------------

def validar_esquema(tabla):
    """Detiene el flujo si la tabla no permite el análisis."""
    if not isinstance(tabla, pd.DataFrame):
        raise TypeError('Se esperaba un DataFrame de pandas.')
    # Primero la cantidad de filas: un JSON [] no tiene columnas, pero el
    # problema real es que no contiene registros.
    if len(tabla) == 0:
        raise ErrorDatos('La tabla de entrada está vacía: no hay registros.')
    faltan = [columna for columna in COLUMNAS if columna not in tabla.columns]
    if faltan:
        raise ErrorDatos('Faltan columnas: ' + ', '.join(faltan))


def _normalizar_texto(valor):
    """Texto sin espacios externos; faltantes y textos vacíos pasan a None.

    Un valor que no es texto (por ejemplo, un número o un Timestamp en un
    DataFrame construido a mano) se valida por su representación textual:
    no se lo confunde con un dato faltante.
    """
    if pd.api.types.is_scalar(valor) and pd.isna(valor):
        return None
    valor = str(valor).strip()
    return valor if valor else None


def normalizar_campos(tabla):
    """Copia sin espacios externos y con los textos vacíos como faltantes."""
    return tabla.map(_normalizar_texto)


def validar_recorridos(tabla):
    """Evalúa cada regla por fila: devuelve una tabla booleana (True = falla).

    Recibe una tabla normalizada con las columnas de COLUMNAS.
    """
    controles = pd.DataFrame(index=tabla.index)

    ids = tabla['viaje_id']
    id_presente = ids.map(texto_presente)
    controles['viaje_id faltante'] = ~id_presente
    controles['viaje_id con formato inválido'] = (
        id_presente & ~ids.map(id_valido))
    # Política de duplicados: se rechazan TODAS las filas con un id repetido,
    # en lugar de elegir arbitrariamente cuál conservar.
    controles['viaje_id duplicado'] = id_presente & ids.duplicated(keep=False)

    instantes = {}
    validas = {}
    for columna in ('inicio', 'fin'):
        presente = tabla[columna].map(texto_presente)
        validas[columna] = tabla[columna].map(fecha_hora_valida)
        controles[f'{columna} faltante'] = ~presente
        controles[f'{columna} inválido'] = presente & ~validas[columna]
        instantes[columna] = pd.to_datetime(
            tabla[columna].where(validas[columna]), format=FORMATO_FECHA_HORA
        )
    ambas_validas = validas['inicio'] & validas['fin']
    controles['fin no posterior al inicio'] = ambas_validas & (
        instantes['fin'] <= instantes['inicio']
    )

    # Un viaje circular (origen igual a destino) es válido: no se controla.
    for columna in ('estacion_origen', 'estacion_destino'):
        controles[f'{columna} faltante'] = ~tabla[columna].map(texto_presente)
    return controles


def limpiar_viajes(tabla):
    """Separa los viajes válidos de los rechazados, sin modificar la entrada.

    Devuelve (validos, rechazados):
    - validos: columnas normalizadas; inicio y fin convertidos a datetime.
    - rechazados: valores originales, número de registro y motivo.
    """
    validar_esquema(tabla)
    original = tabla.loc[:, list(COLUMNAS)].reset_index(drop=True)
    trabajo = normalizar_campos(original)
    controles = validar_recorridos(trabajo)

    invalidos = controles.any(axis=1)
    motivos = controles.apply(lambda fila: '; '.join(fila.index[fila]), axis=1)

    rechazados = original.loc[invalidos].copy()
    rechazados.insert(0, 'registro', rechazados.index + 1)
    rechazados['motivo'] = motivos.loc[invalidos]
    rechazados = rechazados.reset_index(drop=True)

    validos = trabajo.loc[~invalidos].copy()
    if validos.empty:
        raise ErrorDatos('No quedan viajes válidos para analizar.')
    for columna in ('inicio', 'fin'):
        validos[columna] = pd.to_datetime(validos[columna],
                                          format=FORMATO_FECHA_HORA)
    return validos.reset_index(drop=True), rechazados


# ---------------------------------------------------------------------------
# Parámetros de consulta y selección del período
# ---------------------------------------------------------------------------

def convertir_fecha(texto):
    """Convierte un parámetro AAAA-MM-DD en date, con mensajes claros."""
    if not isinstance(texto, str) or PATRON_FECHA.fullmatch(texto) is None:
        raise ErrorDatos(f'Fecha con formato inválido: {texto!r}. '
                         'Use AAAA-MM-DD, por ejemplo 2026-10-01.')
    try:
        return datetime.strptime(texto, FORMATO_FECHA).date()
    except ValueError:
        raise ErrorDatos(
            f'La fecha {texto} no existe en el calendario.') from None


def _como_fecha(valor):
    if isinstance(valor, str):
        return convertir_fecha(valor)
    # datetime es subclase de date; se rechaza para no ignorar su hora.
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    raise ErrorDatos(f'Parámetro de fecha inválido: {valor!r}.')


def validar_periodo(desde, hasta):
    """Devuelve (desde, hasta) como date; exige desde <= hasta."""
    desde, hasta = _como_fecha(desde), _como_fecha(hasta)
    if desde > hasta:
        raise ErrorDatos(f'La fecha inicial ({desde}) es posterior a la '
                         f'final ({hasta}).')
    return desde, hasta


def seleccionar_periodo(viajes, desde, hasta):
    """Viajes cuyo INICIO cae entre desde y hasta, ambos días completos.

    El orden del resultado (inicio, viaje_id) es determinista.
    """
    desde, hasta = validar_periodo(desde, hasta)
    if not pd.api.types.is_datetime64_any_dtype(viajes['inicio']):
        raise ErrorDatos('La columna inicio debe ser de tipo fecha: '
                         'ejecute limpiar_viajes antes de seleccionar.')
    comienzo = pd.Timestamp(desde)
    limite = pd.Timestamp(hasta) + pd.Timedelta(days=1)
    en_periodo = (viajes['inicio'] >= comienzo) & (viajes['inicio'] < limite)
    return (viajes.loc[en_periodo]
            .sort_values(['inicio', 'viaje_id'])
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Movimientos y balance por estación
# ---------------------------------------------------------------------------

def listar_estaciones(viajes):
    """Estaciones que aparecen como origen o destino, en orden alfabético."""
    origenes = set(viajes['estacion_origen'])
    destinos = set(viajes['estacion_destino'])
    return sorted(origenes | destinos)


def registrar_movimientos(viajes, estaciones=()):
    """Suma una salida en el origen y una llegada en el destino de cada viaje.

    estaciones permite incluir en el resultado estaciones sin movimientos
    en el período. Devuelve un diccionario {nombre: BalanceEstacion}.
    """
    balances = {nombre: BalanceEstacion(nombre) for nombre in estaciones}
    for origen, destino in zip(viajes['estacion_origen'],
                               viajes['estacion_destino']):
        for nombre in (origen, destino):
            if nombre not in balances:
                balances[nombre] = BalanceEstacion(nombre)
        balances[origen].registrar_salida()
        balances[destino].registrar_llegada()
    return dict(sorted(balances.items()))


def generar_balance(balances):
    """Tabla del reporte: una fila por estación, ordenada por nombre."""
    filas = [balance.a_diccionario() for balance in balances.values()]
    reporte = pd.DataFrame(filas, columns=COLUMNAS_REPORTE)
    reporte = reporte.astype({'salidas': 'int64', 'llegadas': 'int64',
                              'balance': 'int64'})
    return reporte.sort_values('estacion').reset_index(drop=True)


def verificar_balance(reporte, cantidad_viajes):
    """Comprueba propiedades del reporte; falla si alguna no se cumple."""
    salidas = int(reporte['salidas'].sum())
    llegadas = int(reporte['llegadas'].sum())
    comprobaciones = {
        'total_salidas_igual_viajes': salidas == cantidad_viajes,
        'total_llegadas_igual_viajes': llegadas == cantidad_viajes,
        'suma_balances_igual_cero': int(reporte['balance'].sum()) == 0,
        'balance_igual_llegadas_menos_salidas': bool(
            (reporte['balance']
             == reporte['llegadas'] - reporte['salidas']).all()
        ),
        'estaciones_sin_repetir': bool(reporte['estacion'].is_unique),
    }
    return _exigir(comprobaciones,
                   'El reporte de estaciones no es consistente')


def verificar_registros(originales, validos, rechazados):
    """Ningún registro se pierde: originales = válidos + rechazados."""
    comprobaciones = {
        'originales_igual_validos_mas_rechazados':
            originales == validos + rechazados,
    }
    return _exigir(comprobaciones,
                   'Se perdieron registros durante la limpieza')


def _exigir(comprobaciones, mensaje):
    fallidas = [nombre for nombre, cumple in comprobaciones.items()
                if not cumple]
    if fallidas:
        raise ErrorDatos(f'{mensaje}: ' + ', '.join(fallidas))
    return comprobaciones


# ---------------------------------------------------------------------------
# Resumen, exportación y coordinación del flujo
# ---------------------------------------------------------------------------

def construir_resumen(archivo, desde, hasta, cantidades, reporte,
                      comprobaciones):
    """Diccionario serializable con los totales y controles del análisis."""
    return {
        'archivo_entrada': archivo,
        'periodo': {
            'desde': desde.isoformat(),
            'hasta': hasta.isoformat(),
            'criterio': 'viajes cuyo inicio cae entre ambas fechas, '
                        'con los dos días completos incluidos',
        },
        'registros': {
            'originales': cantidades['originales'],
            'validos': cantidades['validos'],
            'rechazados': cantidades['rechazados'],
        },
        'viajes_seleccionados': cantidades['seleccionados'],
        'estaciones_en_reporte': len(reporte),
        'movimientos': {
            'total_salidas': int(reporte['salidas'].sum()),
            'total_llegadas': int(reporte['llegadas'].sum()),
            'suma_balances': int(reporte['balance'].sum()),
        },
        'comprobaciones': comprobaciones,
    }


def exportar_resultados(reporte, rechazados, resumen, directorio):
    """Escribe los tres archivos de salida y devuelve sus rutas."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    rutas = {
        'reporte': directorio / 'reporte_estaciones.csv',
        'rechazados': directorio / 'registros_rechazados.csv',
        'resumen': directorio / 'resumen.json',
    }
    # Fin de línea '\n' explícito: sin él, pandas y open() usan '\r\n' en
    # Windows y los archivos dependerían del sistema operativo.
    reporte.to_csv(rutas['reporte'], index=False, encoding='utf-8',
                   lineterminator='\n')
    rechazados.to_csv(rutas['rechazados'], index=False, encoding='utf-8',
                      lineterminator='\n')
    with rutas['resumen'].open('w', encoding='utf-8', newline='\n') as archivo:
        json.dump(resumen, archivo, ensure_ascii=False, indent=2)
        archivo.write('\n')
    return rutas


class AplicacionEcobici:
    """Coordina el flujo completo a partir de una fuente de datos.

    La aplicación TIENE una fuente (composición): cualquier objeto
    FuenteDatos sirve, por lo que CSV y JSON recorren el mismo flujo.
    """

    def __init__(self, fuente):
        if not isinstance(fuente, FuenteDatos):
            raise TypeError('La aplicación necesita una FuenteDatos.')
        self._fuente = fuente

    def ejecutar(self, desde, hasta):
        """Devuelve (reporte, rechazados, resumen) para el período pedido."""
        desde, hasta = validar_periodo(desde, hasta)
        entrada = self._fuente.cargar()
        validos, rechazados = limpiar_viajes(entrada)
        control_registros = verificar_registros(len(entrada), len(validos),
                                                len(rechazados))
        seleccion = seleccionar_periodo(validos, desde, hasta)
        balances = registrar_movimientos(seleccion, listar_estaciones(validos))
        reporte = generar_balance(balances)
        control_balance = verificar_balance(reporte, len(seleccion))

        cantidades = {
            'originales': len(entrada),
            'validos': len(validos),
            'rechazados': len(rechazados),
            'seleccionados': len(seleccion),
        }
        resumen = construir_resumen(self._fuente.ruta.name, desde, hasta,
                                    cantidades, reporte,
                                    {**control_registros, **control_balance})
        return reporte, rechazados, resumen
