# ConVRP: ruteo consistente con Gurobi

Implementación en gurobipy de una versión reducida del modelo de Campelo et al. (2019)
para el ruteo consistente multi-día (cada cliente atendido siempre por la misma ruta).

## Estructura

```
docs/modelo.md            Formulación algebraica completa, Big-M y diferencias con el paper
docs/pitch_modelo.md      Láminas y guion de la parte "modelo matemático" del pitch (≈1:15)
src/instancia.py          Lectura de instancias JSON → objeto Instancia
src/modelo.py             build_model(inst): construye el PLEM en gurobipy
src/validar.py            Extrae rutas y verifica la solución de forma independiente
src/main.py               Resuelve una instancia, valida y guarda el resultado
src/generar_ejemplo.py    Genera una instancia sintética de prueba
instancias/               Instancias en JSON
resultados/               Salidas de las corridas
```

## Instalación

```bash
pip install -r requirements.txt
```

La licencia que trae `pip` está limitada a 2000 variables y 2000 restricciones.
La instancia de ejemplo (15 clientes) ya ocupa ~1740 variables, así que para
instancias más grandes se necesita la **licencia académica gratuita** de Gurobi
(gurobi.com → Academia → Named-User Academic License, luego `grbgetkey <clave>`).

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

- **Persona 2 (relajación):** `lp = mod.m.relax(); lp.optimize()`.
- **Persona 2 (instancias):** usar el mismo formato JSON que `instancias/ejemplo_15c.json`. `ventana: null` = cliente sin ventana; `demanda` = una cifra por día (0 = no se visita).
- **Persona 3 (configuraciones):** crear un modelo nuevo por corrida con `build_model` y fijar `Threads=1`, `TimeLimit=600` y el parámetro a probar.
- **Persona 4 (sensibilidad):** tras optimizar, `fx = mod.m.fixed(); fx.optimize()` y leer `Pi`, `SARHSLow`, `SARHSUp` de las restricciones `cap[r,t]` (en `fx` se obtienen con `fx.getConstrByName("cap[0,1]")`).
  Ojo: al fijar las binarias, `cap[r,t]` queda sin variables, así que su precio sombra
  sale 0 y `SARHSLow` es la carga de esa ruta ese día. Eso es esperable y hay que
  interpretarlo (holgura de capacidad), no es un error.

## Prueba con la instancia de ejemplo

| Métrica | Valor |
|---|---|
| Tamaño | 1740 variables (1689 binarias), 1017 restricciones |
| Óptimo (default, 1 hilo) | 1368.78, en ~40–65 s y ~30 000 nodos |
| Relajación lineal | 882.24 → brecha de integralidad ≈ 35.5 % |

La instancia de ejemplo es sintética y solo sirve para probar el código. Las instancias
finales salen de Solomon / Gehring & Homberger (Persona 2).
