"""Pruebas del modelo del dominio (cantidades, Despensa y Receta)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dominio import (  # noqa: E402
    PATRON_ID_RECETA,
    Despensa,
    Receta,
    formatear_cantidad,
    parsear_cantidad,
)


def receta_de_prueba():
    """Receta chica: 2 porciones con un ingrediente de cada dimensión."""
    receta = Receta("REC-900", "Prueba", 2)
    receta.agregar_ingrediente("harina", "harina", 200.0, "masa")
    receta.agregar_ingrediente("leche", "leche", 300.0, "volumen")
    receta.agregar_ingrediente("huevo", "huevo", 2.0, "unidad")
    return receta


def despensa_de_prueba(**stock):
    despensa = Despensa()
    for nombre, (cantidad, dimension) in stock.items():
        despensa.agregar(nombre, cantidad, dimension)
    return despensa


class PruebasCantidades(unittest.TestCase):
    # 1. Casos normales
    def test_convierte_a_unidad_base(self):
        self.assertEqual(parsear_cantidad("200 g"), (200.0, "masa"))
        self.assertEqual(parsear_cantidad("1,5 kg"), (1500.0, "masa"))
        self.assertEqual(parsear_cantidad("0.3 kg"), (300.0, "masa"))
        self.assertEqual(parsear_cantidad("2 l"), (2000.0, "volumen"))
        self.assertEqual(parsear_cantidad("3u"), (3.0, "unidad"))
        self.assertEqual(parsear_cantidad("  250 ML "), (250.0, "volumen"))

    # 2. Entradas inválidas y casos límite
    def test_rechaza_formatos_invalidos(self):
        for texto in ["", "abc", "una pizca", "200", "g", "-5 g", "200 mg", "1,,5 kg", "2 cucharadas"]:
            with self.subTest(texto=texto):
                with self.assertRaises(ValueError):
                    parsear_cantidad(texto)

    def test_rechaza_cantidad_cero(self):
        with self.assertRaises(ValueError) as contexto:
            parsear_cantidad("0 g")
        self.assertIn("fuera de rango", str(contexto.exception))

    def test_regex_de_id_de_receta(self):
        self.assertTrue(PATRON_ID_RECETA.match("REC-001"))
        for texto in ["REC-1", "REC-0001", "rec-001", "PIZZA-1", "REC-00A", "REC-001 "]:
            with self.subTest(texto=texto):
                self.assertIsNone(PATRON_ID_RECETA.match(texto))

    def test_formatear_cantidad(self):
        self.assertEqual(formatear_cantidad(1500.0, "masa"), "1500 g")
        self.assertEqual(formatear_cantidad(0.5, "unidad"), "0.5 u")
        self.assertEqual(formatear_cantidad(100.0, "volumen"), "100 ml")


class PruebasReceta(unittest.TestCase):
    # 1. Caso normal
    def test_receta_cocinable_cuando_todo_alcanza(self):
        despensa = despensa_de_prueba(
            harina=(1000.0, "masa"), leche=(500.0, "volumen"), huevo=(6.0, "unidad"))
        resultado = receta_de_prueba().evaluar(despensa)
        self.assertTrue(resultado["cocinable"])
        self.assertEqual(resultado["cobertura"], 1.0)
        self.assertEqual(resultado["faltantes"], [])

    # 2. Casos límite y entradas inválidas
    def test_cantidad_justa_alcanza(self):
        despensa = despensa_de_prueba(
            harina=(200.0, "masa"), leche=(300.0, "volumen"), huevo=(2.0, "unidad"))
        self.assertTrue(receta_de_prueba().se_puede_cocinar(despensa))

    def test_estados_de_faltantes(self):
        despensa = despensa_de_prueba(harina=(50.0, "masa"), leche=(500.0, "unidad"))
        resultado = receta_de_prueba().evaluar(despensa)
        estados = {f["ingrediente"]: f["estado"] for f in resultado["faltantes"]}
        self.assertEqual(estados, {
            "harina": "insuficiente",
            "leche": "unidad incompatible",
            "huevo": "ausente",
        })
        harina = next(f for f in resultado["faltantes"] if f["ingrediente"] == "harina")
        self.assertAlmostEqual(harina["falta"], 150.0)
        self.assertEqual(resultado["cobertura"], 0.0)

    def test_ingrediente_faltante_no_se_toma_como_cero_silencioso(self):
        resultado = receta_de_prueba().evaluar(Despensa())
        self.assertEqual(len(resultado["faltantes"]), 3)
        self.assertTrue(all(f["estado"] == "ausente" for f in resultado["faltantes"]))

    def test_porciones_invalidas(self):
        with self.assertRaises(ValueError):
            Receta("REC-901", "Mala", 0)
        with self.assertRaises(ValueError):
            Receta("REC-902", "Mala", "4")
        with self.assertRaises(ValueError):
            receta_de_prueba().cantidades_para(0)

    def test_receta_sin_ingredientes_no_se_evalua(self):
        with self.assertRaises(ValueError):
            Receta("REC-903", "Vacia", 1).evaluar(Despensa())

    def test_ingrediente_repetido_en_receta(self):
        receta = receta_de_prueba()
        with self.assertRaises(ValueError):
            receta.agregar_ingrediente("harina", "harina", 10.0, "masa")

    # 3. Propiedades del resultado
    def test_escalar_es_proporcional(self):
        receta = receta_de_prueba()
        base = receta.cantidades_para()
        doble = receta.cantidades_para(4)       # 2 porciones -> 4 porciones
        mitad = receta.cantidades_para(1)
        for clave in base:
            self.assertAlmostEqual(doble[clave][1], base[clave][1] * 2)
            self.assertAlmostEqual(mitad[clave][1], base[clave][1] / 2)

    def test_cobertura_siempre_entre_0_y_1_y_coherente(self):
        receta = receta_de_prueba()
        casos = [
            Despensa(),
            despensa_de_prueba(harina=(500.0, "masa")),
            despensa_de_prueba(harina=(500.0, "masa"), huevo=(1.0, "unidad")),
            despensa_de_prueba(harina=(500.0, "masa"), leche=(1000.0, "volumen"), huevo=(9.0, "unidad")),
        ]
        for despensa in casos:
            for porciones in (None, 1, 2, 10):
                r = receta.evaluar(despensa, porciones)
                self.assertTrue(0.0 <= r["cobertura"] <= 1.0)
                esperado = (r["total_ingredientes"] - len(r["faltantes"])) / r["total_ingredientes"]
                self.assertAlmostEqual(r["cobertura"], esperado)
                self.assertEqual(r["cocinable"], r["cobertura"] == 1.0)

    def test_despensa_vacia_falta_todo_lo_necesario(self):
        receta = receta_de_prueba()
        resultado = receta.evaluar(Despensa(), 4)
        necesidades = receta.cantidades_para(4)
        for f in resultado["faltantes"]:
            clave = f["ingrediente"]
            self.assertAlmostEqual(f["falta"], necesidades[clave][1])


if __name__ == "__main__":
    unittest.main()
