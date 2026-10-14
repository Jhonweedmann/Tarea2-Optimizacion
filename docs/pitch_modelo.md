# Pitch: modelo matemático (Persona 1, ≈1:15)

Dos láminas y un guion de unas 180 palabras (≈1:15 a ritmo de exposición).
La formulación completa, con la explicación de cada restricción, está en [modelo.md](modelo.md).

---

## Lámina 1: Componentes del modelo

**Conjuntos:** días $T$, rutas $R$, clientes $N$; $N_t$ = clientes con pedido el día $t$; $W$ = clientes con ventana.

**Parámetros:** distancia $d_{ij}$, tiempo de viaje $\tau_{ij}$, servicio $s_i$, demanda $q_{it}$, capacidad $Q$, ventana $[a_i,b_i]$, horario del depósito $[E,L]$.

**Variables de decisión**

| | |
|---|---|
| $X_{rijt}\in\{0,1\}$ | la ruta $r$ recorre el arco $(i,j)$ el día $t$ |
| $Z_{ri}\in\{0,1\}$ | el cliente $i$ queda asignado a la ruta $r$ **para todo el horizonte** |
| $A_{it},\ S_r,\ F_{rt}\ge 0$ | inicio de servicio, salida y retorno al depósito |

**Objetivo (1):** $\min \sum_{t}\sum_{r}\sum_{(i,j)} d_{ij}\,X_{rijt}$

---

## Lámina 2: Restricciones

| Bloque | Restricción | Idea |
|---|---|---|
| Consistencia | (2) $\sum_r Z_{ri}=1$ | un cliente, una ruta, todos los días |
| Flujo | (3)–(4) $\sum_j X_{rijt}=\sum_j X_{rjit}=Z_{ri}$ | la ruta asignada entra y sale del cliente el día que hay pedido |
| Depósito | (5) $\sum_j X_{r0jt}\le 1$ | cada ruta sale a lo más una vez al día |
| Tiempo | (7) $A_{jt}\ge A_{it}+s_i+\tau_{ij}-M_{ij}(1-\sum_r X_{rijt})$ | propaga horarios y elimina subtours |
| Ventanas | (8) $a_i\le A_{it}\le b_i$ | solo clientes con ventana |
| Horarios | (9)–(12) | primera llegada después de $S_r$, retorno $F_{rt}$ y todo dentro de $[E,L]$ |
| Capacidad | (14) $\sum_i q_{it}Z_{ri}\le Q$ | por ruta y por día |

**Big-M calibrado:** $M_{ij}=hi_i+s_i+\tau_{ij}-lo_j$, con $[lo_i,hi_i]$ el intervalo real de servicio de cada cliente.

**Fuera del alcance:** (13) fechas de liberación, (15) duración máxima, varios períodos por cliente.

---

## Guion

> **[Lámina 1]** Modelamos el problema como un PLEM basado en Campelo y coautores, 2019.
> Hay dos decisiones binarias. $X$ dice qué arcos recorre cada ruta cada día. $Z$ es la
> clave del problema: asigna cada cliente a una ruta para *todo* el horizonte, y eso es lo
> que hace que el ruteo sea consistente. Además, tres variables continuas siguen los
> horarios. El objetivo es minimizar la distancia total de los tres días.
>
> **[Lámina 2]** La restricción 2 obliga a que cada cliente tenga una sola ruta. La 3 y la 4
> conectan los arcos con esa asignación: el día que el cliente pide, lo visita su ruta y
> ninguna otra. La 7 propaga los tiempos con un Big-M y de paso elimina subtours. Las 8 a
> 12 imponen las ventanas y el horario del depósito, y la 14 es la capacidad por día.
> Dos decisiones propias: calibramos un Big-M por arco con las ventanas de cada cliente, en
> vez de un número gigante, y sumamos la restricción 7 sobre las rutas. Ambas dan una
> relajación más ajustada. Dejamos fuera las fechas de liberación y la duración máxima.

**Si preguntan por qué (7) va sumada sobre $r$:** a lo más una ruta usa cada arco por día,
así que es válida. En la instancia de ejemplo la cota lineal sube de 856.3 a 882.24 y las
restricciones bajan de 1957 a 1017.
