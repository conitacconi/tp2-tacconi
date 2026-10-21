# Datos

Este directorio contiene las entradas de ejemplo de la aplicación. Cada conjunto está en dos formatos
equivalentes (CSV y JSON), y la aplicación lee cualquiera de los dos.

| Archivo | Contenido | Filas |
|---|---|---|
| `recetas.csv` / `recetas.json` | Ingredientes de 12 recetas caseras | 70 (63 válidas + 7 con errores a propósito) |
| `despensa.csv` / `despensa.json` | Lo que hay disponible en casa | 23 (19 válidas + 4 con errores a propósito) |

## Fuente y condiciones de uso

- **Fuente:** datos de ejemplo elaborados para este trabajo. No provienen de ninguna fuente externa ni de
  un sitio web, por lo que no hay URL ni fecha de consulta.
- **Responsable:** Tacconi (autor del trabajo).
- **Fecha de elaboración:** 20 de octubre de 2026.
- **Licencia / condiciones:** uso libre con fines educativos. No contienen datos personales, credenciales
  ni información sensible.
- **Tipo de dato:** simulado. Las cantidades son aproximadas y fueron inventadas con fines didácticos:
  no son recetas de referencia ni información nutricional.

## Unidad de análisis

- En `recetas.*`, **cada fila es un ingrediente de una receta** (por ejemplo: "la Tortilla de papas lleva
  600 g de papa").
- En `despensa.*`, **cada fila es un ingrediente disponible en casa** con su cantidad.

## Variables

**recetas.\***

| Variable | Tipo | Descripción |
|---|---|---|
| `receta_id` | texto | Identificador con formato `REC-` y tres dígitos (ej. `REC-001`) |
| `receta` | texto | Nombre de la receta |
| `porciones` | entero ≥ 1 | Porciones para las que están pensadas las cantidades |
| `ingrediente` | texto | Nombre del ingrediente |
| `cantidad` | texto | Número y unidad: `g`, `kg`, `ml`, `l` o `u` (ej. `200 g`, `0,5 l`) |

**despensa.\***

| Variable | Tipo | Descripción |
|---|---|---|
| `ingrediente` | texto | Nombre del ingrediente |
| `cantidad` | texto | Número y unidad, con el mismo formato que en las recetas |

## Filas con errores a propósito

Los archivos incluyen filas defectuosas para demostrar y probar la limpieza. La aplicación las rechaza
y las lista, con su motivo, en `outputs/rechazos.csv` (ver el README principal).

## Cómo se relacionan el CSV y el JSON

El JSON es una lista de objetos con los mismos campos que las columnas del CSV, y contiene exactamente
las mismas filas en el mismo orden (incluidas las defectuosas). La única diferencia de forma es que
`porciones` aparece como número en el JSON. Las pruebas verifican que leer uno u otro produce lo mismo.

## Limitaciones

- Son pocos datos (12 recetas) y no representan la cocina de ninguna región en particular.
- Los nombres de ingredientes deben coincidir entre recetas y despensa (se ignoran mayúsculas, espacios
  extra y tildes, pero no hay sinónimos: `tomate` y `tomates` serían ingredientes distintos).
- Las cantidades "a gusto" o "una pizca" no se pueden representar y se rechazan.
