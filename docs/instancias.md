# Instancias 

Cuatro instancias en `instancias/`, todas con 3 días, 3 rutas por día y ≥ 15 clientes.
Se usan **dos** como instancias oficiales de la tarea y las otras como respaldo/control.
Los archivos `.json` tienen el formato que lee `src/instancia.py`; los campos extra
(`descripcion`, `origen`, `construccion`, `id_solomon`) los ignora el lector y quedan
como documentación.

## Cómo se generaron

1. **Base: Solomon (CVRPLIB).** Se toma un subconjunto de 16–20 clientes de una instancia
   con ventanas de tiempo (R201, RC201 o C101) y se conservan sus coordenadas, su tiempo de
   servicio y su depósito. `id_solomon` guarda el cliente original.
2. **Multi-día (no viene en CVRPLIB).** Cada cliente pide 2 o 3 de los 3 días. La demanda de
   cada día es `max(1, round(demanda_solomon × U(0.5, 1.5)))`; los días sin pedido llevan 0 y
   el cliente no se visita ese día.
3. **Ventanas solo en algunos clientes.** Entre 40 % y 50 % de los clientes conserva su ventana
   de Solomon, ensanchada: `centro ± semiancho × factor`, recortada a `[apertura, cierre]`.
   El resto va con `ventana: null` (sin restricción de horario más allá del depósito).
4. **Capacidad.** `Q = ceil(carga del día más cargado / (3 × utilización_objetivo))`: 3 rutas
   y la utilización que se quiere en el peor día. Mientras más cerca de 100 %, más difícil es
   empaquetar, y la consistencia obliga a que la misma asignación sirva los tres días.
5. **Horario del depósito.** `[0, cierre]` con el cierre de la instancia de Solomon.

Cada archivo guarda en `construccion` la familia, la semilla y los parámetros usados,
así que se pueden regenerar.

## Resumen

| Instancia | Origen | Clientes | Con ventana | Servicio | Horizonte | Q | Utilización por día (flota) | Ventanas: factor |
|---|---|---|---|---|---|---|---|---|
| `A_capacidad` | R201 | 20 | 8 | 10 | 1000 | 64 | 82 / 91 / 87 % | ×2,5 |
| `B_ventanas` | RC201 | 20 | 10 | 10 | 960 | 122 | 69 / 82 / 87 % | ×3 |
| `C_clusters` | C101 | 16 | 6 | 90 | 1236 | 94 | 86 / 92 / 84 % | ×5 |
| `D_capacidad_holgada` | RC201 | 16 | 8 | 10 | 960 | 116 | 51 / 68 / 70 % | ×3 |


## Tamaño y licencia

Todas quedan bajo el límite de la licencia de `pip` (2000 variables y 2000 restricciones),
pero con poco margen (hasta 1840 variables). Agregar clientes obliga a usar la licencia
académica.
