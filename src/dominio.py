"""Modelo del dominio: cantidades, despensa y receta.

Todas las cantidades se guardan en una unidad base según su dimensión:
    masa    -> gramos (g)       [acepta g y kg]
    volumen -> mililitros (ml)  [acepta ml y l]
    unidad  -> unidades (u)     [acepta u]
No se puede convertir entre dimensiones (por ejemplo, gramos a unidades).
"""
import re

UNIDADES = {
    "g": ("masa", 1.0),
    "kg": ("masa", 1000.0),
    "ml": ("volumen", 1.0),
    "l": ("volumen", 1000.0),
    "u": ("unidad", 1.0),
}
UNIDAD_BASE = {"masa": "g", "volumen": "ml", "unidad": "u"}

# Expresión regular 1: una cantidad es un número (con punto o coma decimal),
# espacios opcionales y una unidad conocida. Ejemplos válidos: "200 g", "1,5 kg", "2u".
PATRON_CANTIDAD = re.compile(r"^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|u)$", re.ASCII)

# Expresión regular 2: el identificador de receta es REC- seguido de 3 dígitos.
PATRON_ID_RECETA = re.compile(r"^REC-\d{3}$", re.ASCII)

TOLERANCIA = 1e-9


def parsear_cantidad(texto):
    """Convierte '1,5 kg' en (1500.0, 'masa').

    La expresión regular solo comprueba la forma del texto; que la cantidad sea
    mayor que cero es una regla aparte que la regex no puede expresar.
    """
    limpio = texto.strip().lower()
    coincidencia = PATRON_CANTIDAD.match(limpio)
    if not coincidencia:
        raise ValueError(
            f"formato de cantidad inválido: '{texto}' "
            "(se espera número y unidad g, kg, ml, l o u; ejemplo: '200 g')"
        )
    numero = float(coincidencia.group(1).replace(",", "."))
    dimension, factor = UNIDADES[coincidencia.group(2)]
    valor = numero * factor
    if valor <= 0:
        raise ValueError(f"cantidad fuera de rango: '{texto}' (debe ser mayor que cero)")
    return valor, dimension


def formatear_cantidad(valor, dimension):
    """Texto legible: (1500.0, 'masa') -> '1500 g'."""
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return f"{texto} {UNIDAD_BASE[dimension]}"


class Despensa:
    """Lo que hay disponible en casa: ingrediente -> (cantidad base, dimensión)."""

    def __init__(self):
        self._stock = {}

    def agregar(self, ingrediente, cantidad, dimension):
        if ingrediente in self._stock:
            raise ValueError(f"'{ingrediente}' ya está en la despensa")
        self._stock[ingrediente] = (cantidad, dimension)

    def obtener(self, ingrediente):
        """Devuelve (cantidad, dimensión) o None si el ingrediente no está."""
        return self._stock.get(ingrediente)

    def __len__(self):
        return len(self._stock)


class Receta:
    """Una receta con sus ingredientes para cierta cantidad de porciones."""

    def __init__(self, receta_id, nombre, porciones):
        if not isinstance(porciones, int) or porciones < 1:
            raise ValueError(f"porciones inválidas para {receta_id}: {porciones!r}")
        self.receta_id = receta_id
        self.nombre = nombre
        self.porciones = porciones
        # clave del ingrediente -> (nombre para mostrar, cantidad base, dimensión)
        self.ingredientes = {}

    def agregar_ingrediente(self, clave, nombre, cantidad, dimension):
        if clave in self.ingredientes:
            raise ValueError(f"'{nombre}' está repetido en {self.receta_id}")
        self.ingredientes[clave] = (nombre, cantidad, dimension)

    def cantidades_para(self, porciones=None):
        """Cantidades necesarias para `porciones` (escala lineal).

        Si porciones es None se usan las porciones originales de la receta.
        """
        if porciones is None:
            factor = 1.0
        else:
            if not isinstance(porciones, int) or porciones < 1:
                raise ValueError(f"porciones inválidas: {porciones!r}")
            factor = porciones / self.porciones
        return {
            clave: (nombre, cantidad * factor, dimension)
            for clave, (nombre, cantidad, dimension) in self.ingredientes.items()
        }

    def evaluar(self, despensa, porciones=None):
        """Compara la receta con la despensa y devuelve un diccionario resumen.

        Cada ingrediente queda en uno de estos estados:
            ok                 -> alcanza
            insuficiente       -> hay, pero menos de lo necesario
            ausente            -> no está en la despensa
            unidad incompatible-> está, pero en otra dimensión (ej. gramos vs unidades)
        """
        if not self.ingredientes:
            raise ValueError(f"{self.receta_id} no tiene ingredientes")
        necesidades = self.cantidades_para(porciones)
        faltantes = []
        for clave, (nombre, necesario, dimension) in necesidades.items():
            en_stock = despensa.obtener(clave)
            if en_stock is None:
                estado, disponible, dim_stock, falta = "ausente", None, None, necesario
            else:
                disponible, dim_stock = en_stock
                if dim_stock != dimension:
                    estado, falta = "unidad incompatible", necesario
                elif necesario - disponible > TOLERANCIA:
                    estado, falta = "insuficiente", necesario - disponible
                else:
                    continue  # el ingrediente alcanza
            faltantes.append({
                "ingrediente": nombre,
                "estado": estado,
                "dimension": dimension,
                "necesario": necesario,
                "disponible": disponible,
                "dimension_despensa": dim_stock,
                "falta": falta,
            })
        total = len(necesidades)
        return {
            "receta_id": self.receta_id,
            "receta": self.nombre,
            "porciones": self.porciones if porciones is None else porciones,
            "total_ingredientes": total,
            "faltantes": faltantes,
            "cobertura": (total - len(faltantes)) / total,
            "cocinable": not faltantes,
        }

    def se_puede_cocinar(self, despensa, porciones=None):
        return self.evaluar(despensa, porciones)["cocinable"]
