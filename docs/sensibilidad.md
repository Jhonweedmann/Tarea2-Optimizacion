# Sensibilidad de la capacidad Q (Persona 2)

Código: `src/sensibilidad.py`. Resultados: `resultados/sensibilidad_<instancia>.csv/.json/.png`.

```bash
cd src
python sensibilidad.py ../instancias/A_capacidad.json --time-limit 600
python sensibilidad.py ../instancias/A_capacidad.json --time-limit 600 --escenarios -3 3 --time-limit-escenarios 600
```

## Método

1. Resolver el MIP (`Threads=1`, `TimeLimit=600`) y quedarse con la mejor solución.
2. `fx = m.fixed(); fx.optimize()`: LP con las variables enteras (X, Z) fijas en esa solución.
3. Para cada restricción de capacidad (14), `cap[r,t]`, leer `Pi`, `RHS`, `Slack`, `SARHSLow`, `SARHSUp`.
4. Complementos: precio sombra de la relajación lineal y re-optimización del MIP con Q ± δ.
