# ¿Qué cocino hoy?

**Autor:** Constanza Tacconi
**Materia:** Programación Orientada a Datos — Licenciatura en Ciencia de Datos, UCA (2026)
**Trabajo:** TP 2 individual

Aplicación de consola en Python que compara un recetario con lo que hay en la heladera y la alacena, y
responde qué recetas se pueden cocinar ya, cuáles están cerca y qué ingredientes faltan.

## 1. Problema, usuario y solución propuesta

**Problema.** Hay días en que se abre la heladera y no se sabe qué cocinar. Revisar a ojo cada receta
contra lo que hay es lento y propenso a errores: se pasa por alto que una receta pide 200 g de algo y solo
quedan 100 g, o que hay que escalar las cantidades porque se cocina para otro número de personas.

**Usuario.** Una persona que cocina en casa y quiere decidir qué preparar sin ir al supermercado, o saber
qué comprar para completar una receta.

**Solución.** Un programa que lee un recetario y una despensa (CSV o JSON), valida y limpia los datos, y
para cada receta calcula qué tan cubierta está con lo disponible.

**Qué puede hacer quien lo usa** (tres operaciones):

| Operación | Qué responde |
|---|---|
| `ranking` | Todas las recetas, de la más cocinable a la menos cocinable |
| `cocinables` | Solo las recetas que se pueden hacer ya con lo que hay |
| `faltantes REC-004` | Qué ingredientes faltan para una receta y cuánto de cada uno |

En todas se puede indicar `--porciones N` para escalar las recetas a otro número de comensales.

**Resultado e interpretación.** Cada receta recibe una *cobertura*: el porcentaje de sus ingredientes que
alcanzan con la despensa (ingredientes que alcanzan ÷ ingredientes totales). Una cobertura del 100 % significa
que se puede cocinar ya. Menos del 100 % indica cuántos ingredientes faltan y cuáles son. Cada ingrediente
que no alcanza queda en uno de tres estados:

- `ausente`: no está en la despensa.
- `insuficiente`: hay, pero menos de lo necesario (se informa cuánto falta).
- `unidad incompatible`: está, pero medido en otra dimensión que la receta (por ejemplo gramos contra unidades), por lo que no se puede comparar.

**Alcance de la primera versión.**

- Incluye: lectura de CSV y JSON, validación y limpieza con registro de filas rechazadas, escalado lineal
  de porciones, ranking, filtro de recetas cocinables y lista de faltantes, con salida a archivos CSV.
- Queda fuera: interfaz web o gráfica, descontar stock entre recetas (cada una se evalúa de forma
  independiente), conversión entre dimensiones (gramos ↔ unidades ↔ mililitros), sinónimos de ingredientes
  y recomendaciones nutricionales.

## 2. Datos

Detalle completo en [`data/README.md`](data/README.md). Resumen:

- **Fuente:** datos de ejemplo elaborados para este trabajo (simulados, sin fuente externa). Uso libre con
  fines educativos, sin datos personales.
- **Unidad de análisis:** en `recetas.*`, cada fila es un ingrediente de una receta; en `despensa.*`, cada
  fila es un ingrediente disponible.
- **Tamaño:** 70 filas y 5 variables en `recetas`; 23 filas y 2 variables en `despensa`. Los dos están
  disponibles en CSV y JSON equivalentes.
- **Limitaciones:** pocos datos, cantidades aproximadas y sin sinónimos entre nombres de ingredientes.

## 3. Instalación y uso

Requiere Python 3.11 o superior (probado con 3.11, 3.12 y 3.13). No necesita instalar bibliotecas: usa solo
la biblioteca estándar.

```bash
git clone https://github.com/conitacconi/tp2-tacconi.git
cd tp2-tacconi
```

(En Mac/Linux, si `python` no existe, usar `python3`.)

**Ejecutar la aplicación** (desde la carpeta del proyecto):

```bash
python src/main.py ranking
python src/main.py cocinables
python src/main.py faltantes REC-004
python src/main.py ranking --porciones 2
python src/main.py ranking --recetas data/recetas.json --despensa data/despensa.json
```

Opciones comunes a las tres operaciones:

| Opción | Para qué sirve | Valor por defecto |
|---|---|---|
| `--recetas` | Archivo `.csv` o `.json` con las recetas | `data/recetas.csv` |
| `--despensa` | Archivo `.csv` o `.json` con la despensa | `data/despensa.csv` |
| `--porciones N` | Escalar todas las recetas a N porciones (entero ≥ 1) | Las de cada receta |
| `--salida` | Dónde guardar el CSV de resultado | `outputs/<operación>.csv` |
| `--rechazos` | Dónde guardar las filas rechazadas | `outputs/rechazos.csv` |

**Ejecutar las pruebas:**

```bash
python -m unittest discover -s tests -v
```

Cada ejecución con los mismos archivos de entrada produce exactamente el mismo resultado.

## 4. Ejemplo de resultado

`python src/main.py ranking`:

```text
Recetas:  70 filas leídas, 63 válidas, 7 rechazadas (12 recetas); 3 filas con texto normalizado
Despensa: 23 filas leídas, 19 válidas, 4 rechazadas (19 ingredientes); 3 filas con texto normalizado

ID       Receta                         Porc.  Cobertura  Estado
-------  -----------------------------  -----  ---------  -----------------------
REC-003  Fideos con salsa               4      100%       LISTA PARA COCINAR
REC-011  Omelette de queso              1      100%       LISTA PARA COCINAR
REC-012  Puré de papas                  4      100%       LISTA PARA COCINAR
REC-001  Tortilla de papas              4      100%       LISTA PARA COCINAR
REC-010  Budín de limón                 8      83%        faltan 1 ingrediente(s)
REC-004  Panqueques con dulce de leche  4      83%        faltan 1 ingrediente(s)
REC-002  Milanesas al horno             4      80%        faltan 1 ingrediente(s)
REC-009  Tostado de jamón y queso       2      75%        faltan 1 ingrediente(s)
REC-005  Arroz con pollo                4      67%        faltan 2 ingrediente(s)
REC-008  Guiso de lentejas              4      67%        faltan 2 ingrediente(s)
REC-007  Tarta de jamón y queso         6      67%        faltan 2 ingrediente(s)
REC-006  Ensalada mixta                 2      40%        faltan 3 ingrediente(s)
```

`python src/main.py faltantes REC-007`:

```text
Tarta de jamón y queso (REC-007) para 6 porciones - cobertura 67%
Te falta:
  - jamón: insuficiente (necesita 150 g, hay 100 g, falta 50 g)
  - queso: insuficiente (necesita 200 g, hay 150 g, falta 50 g)
```

Cómo leerlo: la tarta tiene 6 ingredientes y 4 alcanzan (67 %); los otros dos están en la despensa pero en
menor cantidad. El budín de limón queda en 83 % porque el limón figura en la despensa en gramos (250 g) y
la receta lo pide en unidades: la aplicación lo marca como `unidad incompatible` en lugar de adivinar una
equivalencia.

## 5. Organización del código

```text
tp2-tacconi/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── main.py        # argumentos de consola y coordinación del flujo
│   ├── fuentes.py     # FuenteDatos (abstracta), FuenteCSV, FuenteJSON, ErrorDeDatos
│   ├── dominio.py     # Receta, Despensa, parseo de cantidades y expresiones regulares
│   └── pipeline.py    # normalizar, validar, limpiar, evaluar, verificar y guardar
├── tests/
│   ├── test_dominio.py
│   ├── test_fuentes.py
│   └── test_pipeline.py
├── data/
│   ├── README.md
│   ├── recetas.csv / recetas.json
│   └── despensa.csv / despensa.json
└── outputs/           # se crea al ejecutar; no se versiona
```

**Flujo** (leer → inspeccionar y validar → limpiar y transformar → analizar → comunicar):

```text
fuente_para(ruta).cargar(ruta)      # leer CSV o JSON
validar_esquema(filas, columnas)    # inspeccionar: filas y columnas necesarias
normalizar_campos(filas)            # limpiar espacios, mayúsculas y tildes
limpiar_recetas / limpiar_despensa  # separar filas válidas y rechazadas (con motivo)
construir_recetas / construir_despensa
evaluar_todas(recetas, despensa)    # analizar: cobertura y faltantes
verificar_resultado(resultados)     # comprobar propiedades que siempre deben cumplirse
guardar_resumen / guardar_rechazos  # comunicar
```

### Conceptos del curso aplicados y por qué

- **Funciones con una responsabilidad cada una.** Leer, validar, normalizar, limpiar, evaluar y guardar
  son funciones separadas en `pipeline.py`. Reciben datos ya cargados, así que no dependen del formato de
  origen y se pueden probar por separado.
- **Clases del dominio.** `Receta` reúne sus atributos (id, nombre, porciones, ingredientes) y su
  comportamiento (`cantidades_para`, `evaluar`, `se_puede_cocinar`). `Despensa` guarda lo disponible y
  garantiza que un ingrediente no se cargue dos veces.
- **Abstracción de fuentes.** `FuenteDatos` es una clase abstracta con el método `cargar()`; `FuenteCSV` y
  `FuenteJSON` la implementan y devuelven la misma representación (lista de diccionarios de texto). La
  aplicación elige la fuente por extensión con `fuente_para()`, y puede mezclar formatos (por ejemplo,
  recetas en JSON y despensa en CSV).
- **Expresiones regulares (dos).**
  - `^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|u)$` valida la **forma** de una cantidad: número con punto o coma
    decimal, espacios opcionales y una unidad conocida (`200 g`, `1,5 kg`, `2u`). No valida que el valor sea
    positivo: eso se comprueba aparte, porque una regex no puede expresarlo.
  - `^REC-\d{3}$` valida el identificador de receta.
- **Validaciones con mensajes comprensibles.** Cada fila rechazada indica su motivo; los errores de lectura
  (archivo inexistente, JSON mal formado, extensión no soportada, receta inexistente) frenan el programa
  con un mensaje claro en lugar de ocultarse.

## 6. Decisiones de limpieza

Principio: **una fila con cualquier problema se rechaza y se registra con su motivo; nunca se corrige "a
ojo" ni se reemplaza por cero.** Lo que sí se normaliza (sin rechazar la fila): espacios sobrantes,
mayúsculas y tildes en el nombre del ingrediente, y la unidad (`kg` → `g`, `l` → `ml`).

Reglas, en el orden en que se aplican a una fila de receta:

1. Ningún campo puede estar vacío.
2. `receta_id` debe cumplir `REC-` + 3 dígitos.
3. `porciones` debe ser un entero ≥ 1.
4. `cantidad` debe tener formato válido y ser mayor que cero.
5. Todas las filas de una misma receta deben coincidir en nombre y porciones con la primera fila válida.
6. Un ingrediente debe usar siempre la misma dimensión (masa, volumen o unidad) que en su primera aparición.
7. Un ingrediente no puede repetirse dentro de la misma receta (se conserva la primera fila).

En la despensa se aplican las reglas 1 y 4 (más el rechazo de ingredientes repetidos). Con los datos de
ejemplo se rechazan estas 11 filas (el número es el de fila de datos, sin contar el encabezado):

| Archivo | Fila | Motivo |
|---|---|---|
| recetas | 64 | Ingrediente repetido en REC-001: `huevo` |
| recetas | 65 | Formato de cantidad inválido: `una pizca` |
| recetas | 66 | Campo vacío: ingrediente |
| recetas | 67 | Cantidad fuera de rango: `0 g` |
| recetas | 68 | Unidad incompatible para `aceite` (en otras filas se mide en volumen) |
| recetas | 69 | Datos inconsistentes en REC-007 (la primera fila dice 6 porciones, esta dice 8) |
| recetas | 70 | Id de receta inválido: `PIZZA-1` |
| despensa | 20 | Ingrediente repetido: `sal` (se conserva la primera fila) |
| despensa | 21 | Campo vacío: ingrediente |
| despensa | 22 | Formato de cantidad inválido: `mucho` |
| despensa | 23 | Cantidad fuera de rango: `0 u` |

Además, 3 filas de recetas y 3 de despensa se normalizaron (por ejemplo `JAMON` → `jamon`, que coincide
con `jamón` de las recetas).

Un ingrediente que no está en la despensa **no se trata como un error ni como "cero oculto"**: se informa
explícitamente como `ausente`.

## 7. Verificación

Las 48 pruebas automáticas cubren, como mínimo:

1. **Casos normales:** conversión de unidades, receta cocinable, ranking y operaciones de consola.
2. **Entradas inválidas y casos límite:** formatos de cantidad incorrectos, cantidad exactamente igual a la
   necesaria, despensa vacía, archivos inexistentes o mal formados, porciones inválidas.
3. **Propiedades del resultado:** la cobertura siempre está entre 0 y 1 y es coherente con los faltantes;
   filas leídas = válidas + rechazadas; escalar porciones es proporcional; con la despensa vacía falta
   exactamente lo necesario; **leer CSV o JSON produce el mismo resultado**; repetir la ejecución da lo mismo.

Además, `verificar_resultado()` comprueba estas propiedades en cada ejecución de la aplicación y falla en
voz alta si alguna no se cumple.

## 8. Interpretación y limitaciones

- La cobertura mide cuántos ingredientes alcanzan, no cuánto pesan: una receta con 5 de 6 ingredientes
  (83 %) puede faltarle justo el ingrediente principal.
- Cada receta se evalúa de forma independiente: si dos recetas cocinables usan el mismo ingrediente, la
  despensa podría no alcanzar para hacer las dos.
- El escalado de porciones es lineal. En la práctica la sal, las especias o los tiempos de cocción no
  escalan así.
- No hay conversión entre masa, volumen y unidades (por ejemplo, 1 limón no equivale a una cantidad de
  gramos); esos casos se señalan como `unidad incompatible`.
- Los nombres de ingredientes deben coincidir tras ignorar mayúsculas, espacios y tildes; no hay sinónimos.
- Los datos son de ejemplo y pequeños: sirven para demostrar el funcionamiento, no para conclusiones
  generales sobre cocina.
