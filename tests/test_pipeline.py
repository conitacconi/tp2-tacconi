"""Pruebas del flujo completo (limpieza, evaluación, resultado) y de main.py."""
import contextlib
import csv
import io
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main as aplicacion  # noqa: E402
import pipeline as pl  # noqa: E402
from fuentes import ErrorDeDatos  # noqa: E402

DATOS = Path(__file__).resolve().parents[1] / "data"


def cargar(extension_recetas="csv", extension_despensa="csv"):
    return aplicacion.cargar_datos(
        DATOS / f"recetas.{extension_recetas}", DATOS / f"despensa.{extension_despensa}")


def ejecutar_main(*argumentos):
    """Corre main() capturando lo que imprime. Devuelve (código, stdout, stderr)."""
    salida, errores = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
        codigo = aplicacion.main(list(argumentos))
    return codigo, salida.getvalue(), errores.getvalue()


def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        return list(csv.DictReader(archivo))


class PruebasLimpieza(unittest.TestCase):
    def test_normalizacion_de_texto(self):
        filas = pl.normalizar_campos([
            {"receta_id": " rec-001 ", "ingrediente": "  HUEVO  ", "cantidad": "4  U"},
            {"receta_id": "REC-002", "ingrediente": "Jamón", "cantidad": "1 kg"},
        ])
        self.assertEqual(filas[0]["receta_id"], "REC-001")
        self.assertEqual(filas[0]["ingrediente"], "huevo")
        self.assertEqual(filas[0]["cantidad"], "4 u")
        self.assertTrue(filas[0]["_modificada"])
        self.assertEqual(filas[1]["ingrediente_clave"], "jamon")  # sin tilde para comparar

    def test_limpieza_de_recetas_con_datos_reales(self):
        recetas, _, rechazos, _ = cargar()
        self.assertEqual(len(recetas), 12)
        rechazos_recetas = [r for r in rechazos if r["origen"] == "recetas"]
        motivos = Counter(r["motivo"].split(":")[0].split(" para ")[0].split(" en ")[0]
                          for r in rechazos_recetas)
        self.assertEqual(len(rechazos_recetas), 7)
        self.assertEqual(motivos["campo vacío"], 1)
        self.assertEqual(motivos["id de receta inválido"], 1)
        self.assertEqual(motivos["formato de cantidad inválido"], 1)
        self.assertEqual(motivos["cantidad fuera de rango"], 1)
        self.assertEqual(motivos["unidad incompatible"], 1)
        self.assertEqual(motivos["datos inconsistentes"], 1)
        self.assertEqual(motivos["ingrediente repetido"], 1)

    def test_las_filas_rechazadas_no_alteran_los_datos_validos(self):
        recetas, _, _, _ = cargar()
        # La receta REC-001 conserva 1 solo huevo (el duplicado se rechazó, no se sumó).
        self.assertEqual(recetas["REC-001"].ingredientes["huevo"][1], 4.0)
        # La receta REC-006 no tiene sal (la fila con 0 g se rechazó, no se guardó un cero).
        self.assertNotIn("sal", recetas["REC-006"].ingredientes)

    def test_conservacion_de_filas(self):
        """Propiedad: filas leídas = filas válidas + filas rechazadas."""
        from fuentes import fuente_para
        for nombre, columnas, limpiar in (
            ("recetas", pl.COLUMNAS_RECETAS, pl.limpiar_recetas),
            ("despensa", pl.COLUMNAS_DESPENSA, pl.limpiar_despensa),
        ):
            with self.subTest(archivo=nombre):
                crudas = fuente_para(f"{nombre}.csv").cargar(DATOS / f"{nombre}.csv")
                validas, rechazos = limpiar(pl.normalizar_campos(crudas))
                self.assertEqual(len(crudas), len(validas) + len(rechazos))

    def test_despensa_normaliza_y_rechaza(self):
        _, despensa, rechazos, _ = cargar()
        self.assertEqual(len(despensa), 19)
        self.assertEqual(despensa.obtener("huevo"), (6.0, "unidad"))      # "  Huevo " limpio
        self.assertEqual(despensa.obtener("jamon"), (100.0, "masa"))      # "JAMON" sin tilde
        self.assertEqual(despensa.obtener("papa"), (1000.0, "masa"))      # 1 kg -> g
        self.assertEqual(despensa.obtener("sal"), (200.0, "masa"))        # se conserva la primera
        self.assertIsNone(despensa.obtener("pollo"))                       # "mucho" no es cantidad
        self.assertIsNone(despensa.obtener("morron"))                      # "0 u" fuera de rango
        self.assertEqual(len([r for r in rechazos if r["origen"] == "despensa"]), 4)


class PruebasAnalisis(unittest.TestCase):
    def test_recetas_cocinables_con_datos_reales(self):
        recetas, despensa, _, _ = cargar()
        resultados = pl.evaluar_todas(recetas, despensa)
        cocinables = {r["receta_id"] for r in resultados if r["cocinable"]}
        self.assertEqual(cocinables, {"REC-001", "REC-003", "REC-011", "REC-012"})

    def test_ranking_ordenado_por_cobertura(self):
        recetas, despensa, _, _ = cargar()
        resultados = pl.evaluar_todas(recetas, despensa)
        coberturas = [r["cobertura"] for r in resultados]
        self.assertEqual(coberturas, sorted(coberturas, reverse=True))
        self.assertEqual(resultados[-1]["receta_id"], "REC-006")  # la que menos tiene

    def test_estados_con_datos_reales(self):
        recetas, despensa, _, _ = cargar()
        resultados = {r["receta_id"]: r for r in pl.evaluar_todas(recetas, despensa)}
        # Panqueques: hay dulce de leche pero poco (100 g de 200 g).
        f = resultados["REC-004"]["faltantes"][0]
        self.assertEqual((f["ingrediente"], f["estado"]), ("dulce de leche", "insuficiente"))
        self.assertAlmostEqual(f["falta"], 100.0)
        # Budín: el limón está en gramos en la despensa y la receta lo pide en unidades.
        f = resultados["REC-010"]["faltantes"][0]
        self.assertEqual((f["ingrediente"], f["estado"]), ("limón", "unidad incompatible"))
        # Tostado: no hay pan de molde.
        f = resultados["REC-009"]["faltantes"][0]
        self.assertEqual((f["ingrediente"], f["estado"]), ("pan de molde", "ausente"))

    def test_caso_limite_cantidad_exacta_en_datos_reales(self):
        # Fideos pide 500 ml de puré de tomate y la despensa tiene exactamente 500 ml.
        recetas, despensa, _, _ = cargar()
        self.assertTrue(recetas["REC-003"].se_puede_cocinar(despensa))

    def test_escalar_porciones_cambia_el_resultado(self):
        recetas, despensa, _, _ = cargar()

        def cocinables_con(porciones):
            resultados = pl.evaluar_todas(recetas, despensa, porciones)
            return {r["receta_id"] for r in resultados if r["cocinable"]}

        # A 8 porciones no alcanza nada (ej.: tortilla pide 1200 g de papa y hay 1000 g).
        self.assertEqual(cocinables_con(8), set())
        # A 2 porciones alcanzan más recetas (calculado a mano): panqueques necesita
        # justo 100 g de dulce de leche (hay 100 g) y la tarta pasa a pedir 50 g de jamón.
        # El omelette (1 -> 2 porciones) deja de alcanzar: pide 160 g de queso y hay 150 g.
        self.assertEqual(cocinables_con(2), {"REC-001", "REC-003", "REC-004", "REC-007", "REC-012"})

    def test_verificar_resultado_acepta_resultados_buenos_y_falla_con_malos(self):
        recetas, despensa, _, _ = cargar()
        resultados = pl.evaluar_todas(recetas, despensa)
        pl.verificar_resultado(resultados)  # no debe lanzar nada
        resultados[0]["cobertura"] = 1.5
        with self.assertRaises(ErrorDeDatos):
            pl.verificar_resultado(resultados)

    def test_resultado_repetible(self):
        primero = pl.evaluar_todas(*cargar()[:2])
        segundo = pl.evaluar_todas(*cargar()[:2])
        self.assertEqual(primero, segundo)

    def test_csv_y_json_dan_el_mismo_resultado(self):
        desde_csv = pl.evaluar_todas(*cargar("csv", "csv")[:2])
        desde_json = pl.evaluar_todas(*cargar("json", "json")[:2])
        mezclado = pl.evaluar_todas(*cargar("csv", "json")[:2])
        self.assertEqual(desde_csv, desde_json)
        self.assertEqual(desde_csv, mezclado)


class PruebasAplicacion(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.comunes = ["--rechazos", str(self.tmp / "rechazos.csv")]

    def tearDown(self):
        self._tmp.cleanup()

    def test_ranking_genera_archivos(self):
        salida = self.tmp / "ranking.csv"
        codigo, texto, _ = ejecutar_main("ranking", "--salida", str(salida), *self.comunes)
        self.assertEqual(codigo, 0)
        self.assertIn("LISTA PARA COCINAR", texto)
        self.assertEqual(len(leer_csv(salida)), 12)
        self.assertEqual(len(leer_csv(self.tmp / "rechazos.csv")), 11)

    def test_cocinables_filtra(self):
        salida = self.tmp / "cocinables.csv"
        codigo, _, _ = ejecutar_main("cocinables", "--salida", str(salida), *self.comunes)
        self.assertEqual(codigo, 0)
        filas = leer_csv(salida)
        self.assertEqual({f["receta_id"] for f in filas}, {"REC-001", "REC-003", "REC-011", "REC-012"})
        self.assertTrue(all(f["cocinable"] == "si" for f in filas))

    def test_faltantes_de_una_receta(self):
        salida = self.tmp / "faltantes.csv"
        codigo, texto, _ = ejecutar_main("faltantes", "rec-007", "--salida", str(salida), *self.comunes)
        self.assertEqual(codigo, 0)
        self.assertIn("jamón", texto)
        self.assertEqual({f["ingrediente"] for f in leer_csv(salida)}, {"jamón", "queso"})

    def test_receta_inexistente_da_error_claro(self):
        codigo, _, errores = ejecutar_main("faltantes", "REC-999", *self.comunes)
        self.assertEqual(codigo, 1)
        self.assertIn("No existe la receta", errores)

    def test_archivo_inexistente_da_error_claro(self):
        codigo, _, errores = ejecutar_main("ranking", "--recetas", str(self.tmp / "nada.csv"), *self.comunes)
        self.assertEqual(codigo, 1)
        self.assertIn("No se encontró", errores)

    def test_porciones_invalidas_las_rechaza_argparse(self):
        for valor in ("0", "-2", "dos"):
            with self.subTest(valor=valor):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        aplicacion.main(["ranking", "--porciones", valor, *self.comunes])

    def test_funciona_con_json(self):
        salida = self.tmp / "ranking_json.csv"
        codigo, _, _ = ejecutar_main(
            "ranking", "--recetas", str(DATOS / "recetas.json"),
            "--despensa", str(DATOS / "despensa.json"), "--salida", str(salida), *self.comunes)
        self.assertEqual(codigo, 0)
        salida_csv = self.tmp / "ranking_csv.csv"
        ejecutar_main("ranking", "--salida", str(salida_csv), *self.comunes)
        self.assertEqual(leer_csv(salida), leer_csv(salida_csv))

    def test_despensa_sin_ningun_ingrediente_util(self):
        despensa = self.tmp / "vacia.csv"
        despensa.write_text("ingrediente,cantidad\npollo,mucho\n", encoding="utf-8")
        salida = self.tmp / "cocinables.csv"
        codigo, texto, _ = ejecutar_main(
            "cocinables", "--despensa", str(despensa), "--salida", str(salida), *self.comunes)
        self.assertEqual(codigo, 0)
        self.assertIn("no se puede cocinar ninguna", texto)
        self.assertEqual(leer_csv(salida), [])


if __name__ == "__main__":
    unittest.main()
