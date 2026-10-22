"""Modelo del dominio: movimientos de bicicletas en una estación."""


class BalanceEstacion:
    """Acumula las salidas y llegadas de una estación en un período.

    El balance neto es llegadas - salidas: un valor positivo indica que
    llegaron más bicicletas de las que salieron. No representa el stock
    disponible, porque no incluye inventario inicial ni reposiciones.
    """

    def __init__(self, estacion):
        if not isinstance(estacion, str) or not estacion.strip():
            raise ValueError('El nombre de la estación debe ser un texto no vacío.')
        self._estacion = estacion
        self._llegadas = 0
        self._salidas = 0

    @property
    def estacion(self):
        return self._estacion

    @property
    def llegadas(self):
        return self._llegadas

    @property
    def salidas(self):
        return self._salidas

    def registrar_llegada(self, cantidad=1):
        """Suma bicicletas que terminaron su viaje en esta estación."""
        self._llegadas += _validar_cantidad(cantidad)

    def registrar_salida(self, cantidad=1):
        """Suma bicicletas que comenzaron su viaje en esta estación."""
        self._salidas += _validar_cantidad(cantidad)

    def calcular_balance(self):
        return self._llegadas - self._salidas

    def a_diccionario(self):
        """Fila del reporte: estación, salidas, llegadas y balance."""
        return {
            'estacion': self._estacion,
            'salidas': self._salidas,
            'llegadas': self._llegadas,
            'balance': self.calcular_balance(),
        }

    def __repr__(self):
        return (f'BalanceEstacion({self._estacion!r}, salidas={self._salidas}, '
                f'llegadas={self._llegadas})')


def _validar_cantidad(cantidad):
    """Una cantidad de movimientos debe ser un entero positivo."""
    if isinstance(cantidad, bool) or not isinstance(cantidad, int):
        raise TypeError('La cantidad de movimientos debe ser un número entero.')
    if cantidad <= 0:
        raise ValueError('La cantidad de movimientos debe ser mayor que cero.')
    return cantidad
