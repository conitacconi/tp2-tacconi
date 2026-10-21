"""¿Qué cocino hoy? - Aplicación de consola.

Uso (desde la carpeta del proyecto):
    python src/main.py ranking
    python src/main.py cocinables --porciones 2
    python src/main.py faltantes REC-004
"""
import argparse
import sys
from pathlib import Path

import pipeline as pl
from fuentes import ErrorDeDatos, fuente_para

RAIZ = Path(__file__).resolve().parent.parent


def porciones_valida(texto):
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{texto}' no es un número entero")
    if valor < 1:
        raise argparse.ArgumentTypeError("las porciones deben ser 1 o más")
    return valor


def crear_parser():
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--recetas", default=str(RAIZ / "data" / "recetas.csv"),
                         help="archivo .csv o .json con las recetas")
    comunes.add_argument("--despensa", default=str(RAIZ / "data" / "despensa.csv"),
                         help="archivo .csv o .json con lo que hay en casa")
    comunes.add_argument("--porciones", type=porciones_valida, default=None,
                         help="escalar todas las recetas a este número de porciones")
    comunes.add_argument("--salida", default=None,
                         help="archivo CSV de resultado (por defecto, en outputs/)")
    comunes.add_argument("--rechazos", default=str(RAIZ / "outputs" / "rechazos.csv"),
                         help="archivo CSV donde se guardan las filas rechazadas")

    parser = argparse.ArgumentParser(
        prog="main.py", description="¿Qué cocino hoy? Compara recetas con tu despensa.")
    sub = parser.add_subparsers(dest="operacion", required=True)
    sub.add_parser("ranking", parents=[comunes],
                   help="todas las recetas, de la más a la menos cocinable")
    sub.add_parser("cocinables", parents=[comunes],
                   help="solo las recetas que podés hacer ya")
    faltantes = sub.add_parser("faltantes", parents=[comunes],
                               help="qué ingredientes te faltan para una receta")
    faltantes.add_argument("receta_id", help="identificador, por ejemplo REC-004")
    return parser


def cargar_datos(ruta_recetas, ruta_despensa):
    """Lee, valida y limpia las dos entradas. Devuelve (recetas, despensa, rechazos, informe)."""
    filas_r = fuente_para(ruta_recetas).cargar(ruta_recetas)
    filas_d = fuente_para(ruta_despensa).cargar(ruta_despensa)
    pl.validar_esquema(filas_r, pl.COLUMNAS_RECETAS, "recetas")
    pl.validar_esquema(filas_d, pl.COLUMNAS_DESPENSA, "despensa")

    filas_r = pl.normalizar_campos(filas_r)
    filas_d = pl.normalizar_campos(filas_d)
    validas_r, rechazos_r = pl.limpiar_recetas(filas_r)
    validas_d, rechazos_d = pl.limpiar_despensa(filas_d)
    if not validas_r:
        raise ErrorDeDatos("Ninguna fila de recetas es válida; revise el archivo y el archivo de rechazos.")

    recetas = pl.construir_recetas(validas_r)
    despensa = pl.construir_despensa(validas_d)
    informe = [
        f"Recetas:  {len(filas_r)} filas leídas, {len(validas_r)} válidas, "
        f"{len(rechazos_r)} rechazadas ({len(recetas)} recetas); "
        f"{sum(f['_modificada'] for f in filas_r)} filas con texto normalizado",
        f"Despensa: {len(filas_d)} filas leídas, {len(validas_d)} válidas, "
        f"{len(rechazos_d)} rechazadas ({len(despensa)} ingredientes); "
        f"{sum(f['_modificada'] for f in filas_d)} filas con texto normalizado",
    ]
    return recetas, despensa, rechazos_r + rechazos_d, informe


def main(argv=None):
    args = crear_parser().parse_args(argv)
    try:
        recetas, despensa, rechazos, informe = cargar_datos(args.recetas, args.despensa)
        print("\n".join(informe))
        pl.guardar_rechazos(rechazos, args.rechazos)
        print(f"Filas rechazadas guardadas en: {args.rechazos}\n")

        if args.operacion == "faltantes":
            identificador = args.receta_id.strip().upper()
            if identificador not in recetas:
                raise ErrorDeDatos(
                    f"No existe la receta '{args.receta_id}'. "
                    f"Recetas disponibles: {', '.join(sorted(recetas))}"
                )
            resultado = recetas[identificador].evaluar(despensa, args.porciones)
            pl.verificar_resultado([resultado])
            salida = args.salida or str(RAIZ / "outputs" / f"faltantes_{identificador}.csv")
            print(f"{resultado['receta']} ({resultado['receta_id']}) para "
                  f"{resultado['porciones']} porciones - cobertura {resultado['cobertura'] * 100:.0f}%")
            if resultado["cocinable"]:
                print("Tenés todo lo necesario. ¡A cocinar!")
            else:
                print("Te falta:")
                for f in resultado["faltantes"]:
                    print(f"  - {pl.texto_faltante(f)}")
            pl.guardar_lista_compras(resultado, salida)
        else:
            resultados = pl.evaluar_todas(recetas, despensa, args.porciones)
            pl.verificar_resultado(resultados)
            if args.operacion == "cocinables":
                resultados = [r for r in resultados if r["cocinable"]]
            salida = args.salida or str(RAIZ / "outputs" / f"{args.operacion}.csv")
            if resultados:
                print("\n".join(pl.tabla_resultados(resultados)))
            else:
                print("Con lo que hay en la despensa no se puede cocinar ninguna receta completa.")
            pl.guardar_resumen(resultados, salida)
        print(f"\nResultado guardado en: {salida}")
        return 0
    except ErrorDeDatos as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
