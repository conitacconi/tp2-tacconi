"""Pruebas de lectura: FuenteCSV, FuenteJSON y equivalencia entre ambas."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fuentes import ErrorDeDatos, FuenteCSV, FuenteDatos, FuenteJSON, fuente_para  # noqa: E402
from pipeline import COLUMNAS_RECETAS, validar_esquema  # noqa: E402

DATOS = Path(__file__).resolve().parents[1] / "data"


class PruebasFuentes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def escribir(self, nombre, contenido):
        ruta = self.tmp / nombre
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    # 1. Caso normal
    def test_lee_los_archivos_de_muestra(self):
        filas = FuenteCSV().cargar(DATOS / "recetas.csv")
        self.assertEqual(len(filas), 70)
        self.assertEqual(set(filas[0]), set(COLUMNAS_RECETAS))
        self.assertEqual(len(FuenteJSON().cargar(DATOS / "despensa.json")), 23)

    def test_ambas_fuentes_cumplen_el_contrato(self):
        self.assertIsInstance(FuenteCSV(), FuenteDatos)
        self.assertIsInstance(FuenteJSON(), FuenteDatos)
        with self.assertRaises(TypeError):
            FuenteDatos()  # clase abstracta: no se puede instanciar

    # 3. Propiedad: CSV y JSON equivalentes dan exactamente lo mismo
    def test_csv_y_json_son_equivalentes(self):
        for nombre in ("recetas", "despensa"):
            with self.subTest(archivo=nombre):
                desde_csv = FuenteCSV().cargar(DATOS / f"{nombre}.csv")
                desde_json = FuenteJSON().cargar(DATOS / f"{nombre}.json")
                self.assertEqual(desde_csv, desde_json)

    def test_fuente_para_elige_por_extension(self):
        self.assertIsInstance(fuente_para("x.csv"), FuenteCSV)
        self.assertIsInstance(fuente_para("x.JSON"), FuenteJSON)

    # 2. Entradas inválidas: las fallas de lectura NO se ocultan
    def test_archivo_inexistente(self):
        for fuente in (FuenteCSV(), FuenteJSON()):
            with self.assertRaises(ErrorDeDatos) as contexto:
                fuente.cargar(self.tmp / "no_existe")
            self.assertIn("No se encontró", str(contexto.exception))

    def test_extension_no_soportada(self):
        with self.assertRaises(ErrorDeDatos):
            fuente_para("datos.xlsx")

    def test_json_mal_formado(self):
        ruta = self.escribir("roto.json", '[{"a": 1,')
        with self.assertRaises(ErrorDeDatos) as contexto:
            FuenteJSON().cargar(ruta)
        self.assertIn("JSON válido", str(contexto.exception))

    def test_json_que_no_es_lista_de_objetos(self):
        for contenido in ('{"a": 1}', "[1, 2, 3]", "[]"):
            with self.subTest(contenido=contenido):
                ruta = self.escribir("raro.json", contenido)
                with self.assertRaises(ErrorDeDatos):
                    FuenteJSON().cargar(ruta)

    def test_csv_vacio_o_solo_encabezado(self):
        for contenido in ("", "a,b\n"):
            with self.subTest(contenido=contenido):
                ruta = self.escribir("vacio.csv", contenido)
                with self.assertRaises(ErrorDeDatos):
                    FuenteCSV().cargar(ruta)

    def test_csv_con_fila_de_mas_columnas(self):
        ruta = self.escribir("ancho.csv", "a,b\n1,2,3\n")
        with self.assertRaises(ErrorDeDatos):
            FuenteCSV().cargar(ruta)

    def test_json_convierte_numeros_y_nulos_a_texto(self):
        ruta = self.escribir("tipos.json", '[{"a": 4, "b": null, "c": "x"}]')
        self.assertEqual(FuenteJSON().cargar(ruta), [{"a": "4", "b": "", "c": "x"}])

    def test_esquema_con_columna_faltante(self):
        ruta = self.escribir("incompleto.csv", "receta_id,receta\nREC-001,Algo\n")
        filas = FuenteCSV().cargar(ruta)
        with self.assertRaises(ErrorDeDatos) as contexto:
            validar_esquema(filas, COLUMNAS_RECETAS, "recetas")
        self.assertIn("faltan las columnas", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
