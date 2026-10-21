"""Fuentes de datos.

Define una interfaz común (FuenteDatos) y dos implementaciones concretas:
FuenteCSV y FuenteJSON. Las dos devuelven lo mismo: una lista de diccionarios
{campo: texto}. Así el resto de la aplicación no necesita saber de qué formato
vienen los datos.
"""
import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class ErrorDeDatos(Exception):
    """Error de lectura o validación de datos, con un mensaje comprensible."""


class FuenteDatos(ABC):
    """Contrato común: toda fuente sabe cargar un archivo y devolver filas."""

    @abstractmethod
    def cargar(self, ruta):
        """Devuelve una lista de diccionarios {campo: texto}."""

    @staticmethod
    def _verificar_archivo(ruta):
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorDeDatos(f"No se encontró el archivo: {ruta}")
        return ruta


class FuenteCSV(FuenteDatos):
    """Lee un archivo CSV con encabezado (UTF-8, con o sin BOM)."""

    def cargar(self, ruta):
        ruta = self._verificar_archivo(ruta)
        filas = []
        try:
            with open(ruta, newline="", encoding="utf-8-sig") as archivo:
                for numero, fila in enumerate(csv.DictReader(archivo), start=1):
                    if None in fila:
                        raise ErrorDeDatos(
                            f"{ruta.name}: la fila {numero} tiene más columnas "
                            "que el encabezado"
                        )
                    # Una celda ausente (fila corta) se trata como texto vacío.
                    filas.append({c: ("" if v is None else v) for c, v in fila.items()})
        except (UnicodeDecodeError, csv.Error) as error:
            raise ErrorDeDatos(f"No se pudo leer {ruta.name} como CSV UTF-8: {error}")
        if not filas:
            raise ErrorDeDatos(f"{ruta.name}: el archivo no tiene filas de datos")
        return filas


class FuenteJSON(FuenteDatos):
    """Lee un archivo JSON que contiene una lista de objetos.

    Cada objeto es una fila. Todos los valores se convierten a texto (y null a
    texto vacío) para que el resultado sea idéntico al de FuenteCSV.
    """

    def cargar(self, ruta):
        ruta = self._verificar_archivo(ruta)
        try:
            with open(ruta, encoding="utf-8-sig") as archivo:
                datos = json.load(archivo)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ErrorDeDatos(f"No se pudo leer {ruta.name} como JSON válido: {error}")
        if not isinstance(datos, list) or not all(isinstance(o, dict) for o in datos):
            raise ErrorDeDatos(
                f"{ruta.name}: se esperaba una lista de objetos "
                '(por ejemplo [{"campo": "valor"}, ...])'
            )
        if not datos:
            raise ErrorDeDatos(f"{ruta.name}: el archivo no tiene registros")
        return [
            {str(c): ("" if v is None else str(v)) for c, v in objeto.items()}
            for objeto in datos
        ]


def fuente_para(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ErrorDeDatos(
        f"Formato no soportado para '{Path(ruta).name}': use un archivo .csv o .json"
    )
