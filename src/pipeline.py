"""Flujo de procesamiento: validar, limpiar, seleccionar, contar y exportar.

Las funciones de transformación reciben tablas ya cargadas y devuelven
resultados nuevos: no leen ni escriben archivos y no modifican sus
argumentos. La escritura se concentra en exportar_resultados().
"""

import re
from datetime import datetime

import pandas as pd

from src.fuentes import ErrorDatos

COLUMNAS = ('viaje_id', 'inicio', 'fin', 'estacion_origen', 'estacion_destino')

# Un identificador es "ECO-" seguido de exactamente cuatro dígitos ASCII.
PATRON_ID = re.compile(r'ECO-[0-9]{4}')
# Forma textual de fecha y hora. No verifica el calendario: 2026-09-31 o la
# hora 25 respetan el patrón, por eso se complementa con datetime.strptime.
PATRON_FECHA_HORA = re.compile(
    r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}'
)
FORMATO_FECHA_HORA = '%Y-%m-%d %H:%M:%S'


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
    if not isinstance(valor, str) or PATRON_FECHA_HORA.fullmatch(valor) is None:
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
    faltan = [columna for columna in COLUMNAS if columna not in tabla.columns]
    if faltan:
        raise ErrorDatos('Faltan columnas: ' + ', '.join(faltan))
    if tabla.empty:
        raise ErrorDatos('La tabla de entrada está vacía.')


def _normalizar_texto(valor):
    if not isinstance(valor, str):
        return None
    valor = valor.strip()
    return valor if valor else None


def normalizar_campos(tabla):
    """Copia con espacios externos eliminados y textos vacíos como faltantes."""
    return tabla.map(_normalizar_texto)


def validar_recorridos(tabla):
    """Evalúa cada regla por fila: devuelve una tabla booleana (True = falla).

    Recibe una tabla normalizada con las columnas de COLUMNAS.
    """
    controles = pd.DataFrame(index=tabla.index)

    ids = tabla['viaje_id']
    id_presente = ids.map(texto_presente)
    controles['viaje_id faltante'] = ~id_presente
    controles['viaje_id con formato inválido'] = id_presente & ~ids.map(id_valido)
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
