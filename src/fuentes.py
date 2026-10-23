"""Fuentes de datos: lectura de viajes desde CSV o JSON.

Las fuentes sólo convierten un archivo en una tabla. La validación del
significado de cada registro se realiza después, en pipeline.py.

Contrato común de cargar(): devuelve un DataFrame de columnas de texto en el
que cada valor es un str o un faltante (detectable con pd.isna). Así, un
mismo conjunto de datos produce exactamente la misma tabla sin importar el
formato del archivo.
"""

import json
import math
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class ErrorDatos(ValueError):
    """La entrada no cumple el contrato de la aplicación."""


class FuenteDatos(ABC):
    """Abstracción común para leer registros desde un archivo."""

    def __init__(self, ruta):
        self._ruta = Path(ruta)

    @property
    def ruta(self):
        return self._ruta

    def comprobar_archivo(self):
        """Falla con un mensaje claro si el archivo no existe o está vacío."""
        if not self.ruta.exists():
            raise FileNotFoundError(f'No existe el archivo: {self.ruta}')
        if not self.ruta.is_file():
            raise ErrorDatos(f'La ruta no es un archivo: {self.ruta}')
        if self.ruta.stat().st_size == 0:
            raise ErrorDatos(f'El archivo está vacío: {self.ruta.name}')

    @abstractmethod
    def cargar(self):
        """Devuelve un DataFrame con valores str o faltantes (pd.isna)."""
        raise NotImplementedError

    def _normalizar_valores(self, tabla):
        """Convierte cada celda a str o faltante sin modificar la tabla.

        pandas representa los faltantes de una columna de texto como NaN,
        aunque _como_texto devuelva None; por eso se detectan con pd.isna.
        """
        return tabla.astype(object).map(_como_texto)


def _como_texto(valor):
    """Representa un valor escalar como texto; los faltantes como None."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return str(valor)
    raise ErrorDatos(
        f'Valor no admitido en la entrada ({type(valor).__name__}): '
        'cada campo debe ser texto, número o vacío.'
    )


class FuenteCSV(FuenteDatos):
    """Lee un CSV con encabezado, separado por comas y codificado en UTF-8."""

    def cargar(self):
        self.comprobar_archivo()
        try:
            # Sólo la celda vacía se interpreta como faltante: textos como
            # "NA" o "null" se conservan y luego los evalúa la validación.
            # utf-8-sig acepta archivos con o sin BOM (marca que agregan
            # algunos editores de Windows al guardar en UTF-8).
            tabla = pd.read_csv(self.ruta, dtype=str, encoding='utf-8-sig',
                                keep_default_na=False, na_values=[''])
        except pd.errors.EmptyDataError as error:
            raise ErrorDatos(
                f'El CSV no tiene encabezado ni datos: {self.ruta.name}'
            ) from error
        except pd.errors.ParserError as error:
            raise ErrorDatos(
                f'CSV mal formado en {self.ruta.name}: {error}'
            ) from error
        except UnicodeDecodeError as error:
            raise ErrorDatos(
                f'El CSV {self.ruta.name} no está codificado en UTF-8.'
            ) from error
        return self._normalizar_valores(tabla)


class FuenteJSON(FuenteDatos):
    """Lee un JSON cuya raíz es una lista de objetos planos (uno por viaje)."""

    def cargar(self):
        self.comprobar_archivo()
        try:
            with self.ruta.open(encoding='utf-8-sig') as archivo:
                contenido = json.load(archivo)
        except json.JSONDecodeError as error:
            raise ErrorDatos(
                f'JSON mal formado en {self.ruta.name}: {error.msg} '
                f'(línea {error.lineno}, columna {error.colno}).'
            ) from error
        except UnicodeDecodeError as error:
            raise ErrorDatos(
                f'El JSON {self.ruta.name} no está codificado en UTF-8.'
            ) from error

        if not isinstance(contenido, list) or not all(
            isinstance(registro, dict) for registro in contenido
        ):
            raise ErrorDatos(
                'El JSON debe ser una lista de objetos (registros).')
        return self._normalizar_valores(pd.DataFrame(contenido))


def crear_fuente(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    ruta = Path(ruta)
    fuentes = {'.csv': FuenteCSV, '.json': FuenteJSON}
    clase = fuentes.get(ruta.suffix.lower())
    if clase is None:
        raise ErrorDatos(
            f'Formato no soportado: "{ruta.suffix}". '
            'Use un archivo .csv o .json.'
        )
    return clase(ruta)
