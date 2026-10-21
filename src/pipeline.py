"""Flujo de procesamiento: leer -> validar -> limpiar -> analizar -> comunicar.

Las funciones de este módulo reciben datos ya cargados (listas de diccionarios),
por lo que no dependen del formato del archivo de origen (CSV o JSON).
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

from dominio import (
    PATRON_ID_RECETA,
    TOLERANCIA,
    Despensa,
    Receta,
    formatear_cantidad,
    parsear_cantidad,
)
from fuentes import ErrorDeDatos

COLUMNAS_RECETAS = ["receta_id", "receta", "porciones", "ingrediente", "cantidad"]
COLUMNAS_DESPENSA = ["ingrediente", "cantidad"]
TODOS_LOS_CAMPOS = ["receta_id", "receta", "porciones", "ingrediente", "cantidad"]

PATRON_ENTERO = re.compile(r"^[0-9]+$")


# ---------------------------------------------------------------- texto ----
def limpiar_espacios(texto):
    """Quita espacios sobrantes al inicio, al final y repetidos en el medio."""
    return " ".join(texto.split())


def quitar_acentos(texto):
    """'jamón' -> 'jamon'. Sirve para comparar ingredientes sin importar tildes."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# ------------------------------------------------- esquema y normalización ----
def validar_esquema(filas, columnas_requeridas, nombre="archivo"):
    """Comprueba que haya filas y que existan las columnas necesarias."""
    if not filas:
        raise ErrorDeDatos(f"{nombre}: no tiene filas")
    presentes = set()
    for fila in filas:
        presentes.update(fila.keys())
    faltan = [c for c in columnas_requeridas if c not in presentes]
    if faltan:
        raise ErrorDeDatos(
            f"{nombre}: faltan las columnas {faltan}; "
            f"se encontraron {sorted(presentes)}"
        )


def normalizar_campos(filas):
    """Limpia el texto de cada fila y agrega campos auxiliares.

    Agrega: _fila (número de fila de datos, desde 1), _original (la fila tal
    como llegó), _modificada (True si la limpieza cambió algún texto) e
    ingrediente_clave (ingrediente sin tildes, usado para comparar).
    """
    salida = []
    for numero, fila in enumerate(filas, start=1):
        limpia = {"_fila": numero, "_original": dict(fila), "_modificada": False}
        for campo in TODOS_LOS_CAMPOS:
            crudo = fila.get(campo, "")
            texto = limpiar_espacios(crudo)
            if campo == "receta_id":
                texto = texto.upper()
            elif campo in ("ingrediente", "cantidad"):
                texto = texto.lower()
            if texto != crudo:
                limpia["_modificada"] = True
            limpia[campo] = texto
        limpia["ingrediente_clave"] = quitar_acentos(limpia["ingrediente"])
        salida.append(limpia)
    return salida


# --------------------------------------------------------------- limpieza ----
def _rechazo(origen, fila, motivo):
    return {
        "origen": origen,
        "fila": fila["_fila"],
        "motivo": motivo,
        "datos": json.dumps(fila["_original"], ensure_ascii=False),
    }


def _revisar_fila_receta(fila, cabeceras, dimensiones, vistos):
    """Devuelve (motivo, cantidad, dimensión). El motivo es None si la fila sirve."""
    for campo in COLUMNAS_RECETAS:
        if fila[campo] == "":
            return f"campo vacío: {campo}", None, None
    if not PATRON_ID_RECETA.match(fila["receta_id"]):
        return (
            f"id de receta inválido: '{fila['receta_id']}' "
            "(se espera REC- y tres dígitos, ejemplo REC-001)",
            None, None,
        )
    if not PATRON_ENTERO.match(fila["porciones"]) or int(fila["porciones"]) < 1:
        return (
            f"porciones inválidas: '{fila['porciones']}' "
            "(debe ser un entero mayor o igual a 1)",
            None, None,
        )
    try:
        cantidad, dimension = parsear_cantidad(fila["cantidad"])
    except ValueError as error:
        return str(error), None, None

    porciones = int(fila["porciones"])
    previo = cabeceras.get(fila["receta_id"])
    if previo is not None and previo != (fila["receta"], porciones):
        return (
            f"datos inconsistentes para {fila['receta_id']}: la primera fila válida "
            f"dice '{previo[0]}' con {previo[1]} porciones",
            None, None,
        )
    referencia = dimensiones.get(fila["ingrediente_clave"])
    if referencia is not None and referencia != dimension:
        return (
            f"unidad incompatible para '{fila['ingrediente']}': en otras filas se "
            f"mide en {referencia} y acá en {dimension}",
            None, None,
        )
    if (fila["receta_id"], fila["ingrediente_clave"]) in vistos:
        return (
            f"ingrediente repetido en {fila['receta_id']}: "
            f"'{fila['ingrediente']}' (se conserva la primera fila)",
            None, None,
        )
    return None, cantidad, dimension


def limpiar_recetas(filas):
    """Separa las filas de recetas en (válidas, rechazadas).

    Decisión de limpieza: una fila con cualquier problema se RECHAZA y se
    registra con su motivo; nunca se corrige "a ojo" ni se reemplaza por cero.
    """
    validas, rechazos = [], []
    cabeceras = {}    # receta_id -> (nombre, porciones) de la primera fila válida
    dimensiones = {}  # ingrediente -> dimensión de la primera fila válida
    vistos = set()    # pares (receta_id, ingrediente) ya aceptados
    for fila in filas:
        motivo, cantidad, dimension = _revisar_fila_receta(
            fila, cabeceras, dimensiones, vistos
        )
        if motivo is not None:
            rechazos.append(_rechazo("recetas", fila, motivo))
            continue
        porciones = int(fila["porciones"])
        cabeceras.setdefault(fila["receta_id"], (fila["receta"], porciones))
        dimensiones.setdefault(fila["ingrediente_clave"], dimension)
        vistos.add((fila["receta_id"], fila["ingrediente_clave"]))
        aceptada = dict(fila)
        aceptada.update(
            porciones_int=porciones, cantidad_base=cantidad, dimension=dimension
        )
        validas.append(aceptada)
    return validas, rechazos


def limpiar_despensa(filas):
    """Separa las filas de la despensa en (válidas, rechazadas)."""
    validas, rechazos = [], []
    vistos = set()
    for fila in filas:
        motivo = None
        for campo in COLUMNAS_DESPENSA:
            if fila[campo] == "":
                motivo = f"campo vacío: {campo}"
                break
        if motivo is None:
            try:
                cantidad, dimension = parsear_cantidad(fila["cantidad"])
            except ValueError as error:
                motivo = str(error)
        if motivo is None and fila["ingrediente_clave"] in vistos:
            motivo = (
                f"ingrediente repetido en la despensa: '{fila['ingrediente']}' "
                "(se conserva la primera fila)"
            )
        if motivo is not None:
            rechazos.append(_rechazo("despensa", fila, motivo))
            continue
        vistos.add(fila["ingrediente_clave"])
        aceptada = dict(fila)
        aceptada.update(cantidad_base=cantidad, dimension=dimension)
        validas.append(aceptada)
    return validas, rechazos


# ----------------------------------------------------------- construcción ----
def construir_recetas(filas_validas):
    """Arma un diccionario receta_id -> Receta a partir de filas ya validadas."""
    recetas = {}
    for fila in filas_validas:
        identificador = fila["receta_id"]
        if identificador not in recetas:
            recetas[identificador] = Receta(
                identificador, fila["receta"], fila["porciones_int"]
            )
        recetas[identificador].agregar_ingrediente(
            fila["ingrediente_clave"], fila["ingrediente"],
            fila["cantidad_base"], fila["dimension"],
        )
    return recetas


def construir_despensa(filas_validas):
    despensa = Despensa()
    for fila in filas_validas:
        despensa.agregar(
            fila["ingrediente_clave"], fila["cantidad_base"], fila["dimension"]
        )
    return despensa


# --------------------------------------------------------------- análisis ----
def evaluar_todas(recetas, despensa, porciones=None):
    """Evalúa todas las recetas y las ordena de la más a la menos cocinable.

    Orden: mayor cobertura primero; si empatan, por nombre (sin tildes) y por id.
    Cada receta se evalúa de forma independiente: no se descuenta stock entre ellas.
    """
    resultados = [r.evaluar(despensa, porciones) for r in recetas.values()]
    resultados.sort(
        key=lambda r: (-r["cobertura"], quitar_acentos(r["receta"].lower()), r["receta_id"])
    )
    return resultados


def verificar_resultado(resultados):
    """Comprueba propiedades que SIEMPRE deben cumplirse. Si no, falla en voz alta."""
    for r in resultados:
        total, n_faltantes = r["total_ingredientes"], len(r["faltantes"])
        if total < 1:
            raise ErrorDeDatos(f"resultado inconsistente: {r['receta_id']} sin ingredientes")
        if not 0.0 <= r["cobertura"] <= 1.0:
            raise ErrorDeDatos(f"resultado inconsistente: cobertura fuera de [0, 1] en {r['receta_id']}")
        if abs(r["cobertura"] - (total - n_faltantes) / total) > TOLERANCIA:
            raise ErrorDeDatos(f"resultado inconsistente: cobertura mal calculada en {r['receta_id']}")
        if r["cocinable"] != (n_faltantes == 0):
            raise ErrorDeDatos(f"resultado inconsistente: 'cocinable' no coincide con los faltantes en {r['receta_id']}")
        for f in r["faltantes"]:
            if f["falta"] <= 0 or f["falta"] > f["necesario"] + TOLERANCIA:
                raise ErrorDeDatos(f"resultado inconsistente: faltante inválido en {r['receta_id']}")


# ----------------------------------------------------------- comunicación ----
def texto_faltante(f):
    """Una línea legible para un ingrediente que no alcanza."""
    necesario = formatear_cantidad(f["necesario"], f["dimension"])
    if f["estado"] == "ausente":
        return f"{f['ingrediente']}: no está en la despensa (necesita {necesario})"
    disponible = formatear_cantidad(f["disponible"], f["dimension_despensa"])
    if f["estado"] == "unidad incompatible":
        return (
            f"{f['ingrediente']}: unidad incompatible (la receta pide {necesario} "
            f"y la despensa tiene {disponible})"
        )
    falta = formatear_cantidad(f["falta"], f["dimension"])
    return (
        f"{f['ingrediente']}: insuficiente (necesita {necesario}, "
        f"hay {disponible}, falta {falta})"
    )


def tabla_resultados(resultados):
    """Devuelve las líneas de una tabla de texto para mostrar en consola."""
    filas = [("ID", "Receta", "Porc.", "Cobertura", "Estado")]
    for r in resultados:
        n = len(r["faltantes"])
        estado = "LISTA PARA COCINAR" if r["cocinable"] else f"faltan {n} ingrediente(s)"
        filas.append((
            r["receta_id"], r["receta"], str(r["porciones"]),
            f"{r['cobertura'] * 100:.0f}%", estado,
        ))
    anchos = [max(len(fila[i]) for fila in filas) for i in range(5)]
    lineas = []
    for indice, fila in enumerate(filas):
        lineas.append("  ".join(texto.ljust(anchos[i]) for i, texto in enumerate(fila)).rstrip())
        if indice == 0:
            lineas.append("  ".join("-" * ancho for ancho in anchos))
    return lineas


def _abrir_salida(ruta):
    ruta = Path(ruta)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        return open(ruta, "w", newline="", encoding="utf-8-sig")
    except OSError as error:
        raise ErrorDeDatos(f"No se pudo escribir el archivo {ruta}: {error}")


def guardar_resumen(resultados, ruta):
    """Guarda un CSV con una fila por receta."""
    with _abrir_salida(ruta) as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([
            "receta_id", "receta", "porciones", "cobertura_pct",
            "cocinable", "ingredientes_faltantes",
        ])
        for r in resultados:
            escritor.writerow([
                r["receta_id"], r["receta"], r["porciones"],
                f"{r['cobertura'] * 100:.1f}",
                "si" if r["cocinable"] else "no",
                "; ".join(texto_faltante(f) for f in r["faltantes"]),
            ])


def guardar_lista_compras(resultado, ruta):
    """Guarda un CSV con una fila por ingrediente que falta en una receta."""
    with _abrir_salida(ruta) as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["ingrediente", "estado", "necesario", "disponible", "falta"])
        for f in resultado["faltantes"]:
            disponible = (
                "0" if f["disponible"] is None
                else formatear_cantidad(f["disponible"], f["dimension_despensa"])
            )
            escritor.writerow([
                f["ingrediente"], f["estado"],
                formatear_cantidad(f["necesario"], f["dimension"]),
                disponible,
                formatear_cantidad(f["falta"], f["dimension"]),
            ])


def guardar_rechazos(rechazos, ruta):
    """Guarda un CSV con las filas rechazadas y el motivo de cada una."""
    with _abrir_salida(ruta) as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["origen", "fila", "motivo", "datos"])
        for r in rechazos:
            escritor.writerow([r["origen"], r["fila"], r["motivo"], r["datos"]])
