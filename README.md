# ConVRP: ruteo consistente con Gurobi

Implementación en gurobipy de una versión reducida del modelo de Campelo et al. (2019)
para el ruteo consistente multi-día (cada cliente atendido siempre por la misma ruta).

## Estructura

```
docs/modelo.md            Formulación algebraica completa, Big-M y diferencias con el paper
docs/pitch_modelo.md      Láminas y guion de la parte "modelo matemático" del pitch (≈1:15)
docs/instancias.md        Cómo se generaron las instancias y su calibración (Persona 2)
docs/sensibilidad.md      Sensibilidad de Q con Model.fixed(): resultados e interpretación
src/instancia.py          Lectura de instancias JSON → objeto Instancia
src/modelo.py             build_model(inst): construye el PLEM en gurobipy
src/validar.py            Extrae rutas y verifica la solución de forma independiente
src/main.py               Resuelve una instancia, valida y guarda el resultado
src/sensibilidad.py       Sensibilidad de la capacidad Q: m.fixed(), Pi, SARHSLow/SARHSUp
src/generar_ejemplo.py    Genera una instancia sintética de prueba
instancias/               Instancias en JSON (A, B, C, D y el ejemplo sintético)
resultados/               Salidas de las corridas
```

## Instalación

```bash
pip install -r requirements.txt
```


## Uso

```bash
cd src
python main.py ../instancias/ejemplo_15c.json --time-limit 600 --threads 1
```

Imprime las rutas de cada día, valida la solución y guarda un resumen en `resultados/`.

## Para el resto del equipo

`build_model` devuelve un objeto con el modelo y todas sus variables:

```python
from instancia import cargar_instancia
from modelo import build_model

inst = cargar_instancia("../instancias/ejemplo_15c.json")
mod = build_model(inst, verbose=False)

mod.m          # gurobipy.Model
mod.X, mod.Z   # variables binarias X[r,i,j,t], Z[r,i]
mod.A, mod.S, mod.F   # A[i,t] inicio de servicio, S[r] salida, F[r,t] retorno
mod.cap        # restricciones de capacidad cap[r,t]  → sensibilidad de Q
```

- **Persona 3 (relajación):** `lp = mod.m.relax(); lp.optimize()`.
- **Persona 2 (instancias y sensibilidad):** las instancias usan el formato JSON de
  `instancias/ejemplo_15c.json` (`ventana: null` = cliente sin ventana; `demanda` = una cifra por día,
  0 = no se visita). La sensibilidad de Q está en `src/sensibilidad.py` (ver abajo).
- **Persona 4 (configuraciones):** crear un modelo nuevo por corrida con `build_model` y fijar `Threads=1`,
  `TimeLimit=600` y el parámetro a probar.

## Sensibilidad de la capacidad Q

```bash
cd src
python sensibilidad.py ../instancias/A_capacidad.json --time-limit 600
python sensibilidad.py ../instancias/A_capacidad.json --time-limit 600 --escenarios -3 3   # reoptimiza con Q±3
```

Resuelve el MIP, hace `fx = m.fixed(); fx.optimize()` y reporta, para cada `cap[r,t]`, `Pi`,
`RHS`, `Slack`, `SARHSLow` y `SARHSUp`. Guarda `resultados/sensibilidad_<instancia>.csv/.json/.png`.

Al fijar las binarias, `cap[r,t]` queda sin variables libres: la carga es constante, así que
**`Pi = 0` en todas las restricciones**, `SARHSLow` es la carga de esa ruta ese día y `SARHSUp = inf`.
Es esperable y hay que interpretarlo (holgura y rango de validez), no es un error. El efecto
real de Q sobre el costo (que exige cambiar la asignación) se mide con `--escenarios` y con el
`Pi` de la relajación lineal. Detalle en [docs/sensibilidad.md](docs/sensibilidad.md).

## Prueba con la instancia de ejemplo

| Métrica | Valor |
|---|---|
| Tamaño | 1740 variables (1689 binarias), 1017 restricciones |
| Óptimo (default, 1 hilo) | 1368.78, en ~40–65 s y ~30 000 nodos |
| Relajación lineal | 882.24 → brecha de integralidad ≈ 35.5 % |

La instancia de ejemplo es sintética y solo sirve para probar el código.
