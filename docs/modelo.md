# Formulación del ConVRP reducido

Versión reducida del modelo de Campelo, Neves-Moreira, Amorim y Almada-Lobo (2019),
*Consistent vehicle routing problem with service level agreements*, EJOR 273(1), §3.1
(pág. 134–136). La numeración de las restricciones es la del paper. La formulación fue
cotejada con el PDF: las diferencias están en [Diferencias con el paper](#diferencias-con-el-paper).

## Situación

Una distribuidora atiende clientes durante varios días con una flota fija de rutas.
Para dar **consistencia de servicio**, cada cliente queda asignado a una misma ruta
(mismo conductor y vehículo) durante todo el horizonte, aunque su demanda cambie de un
día a otro y no todos los clientes se visiten todos los días.

## Conjuntos

| Símbolo | Significado |
|---|---|
| $T$ | días del horizonte de planificación |
| $R$ | rutas (vehículos/conductores), las mismas todos los días |
| $N$ | clientes |
| $N_t \subseteq N$ | clientes con demanda el día $t$ |
| $V_t = \{0\} \cup N_t$ | nodos del día $t$; el 0 es el depósito |
| $W \subseteq N$ | clientes con ventana de tiempo definida |

## Parámetros

| Símbolo | Significado |
|---|---|
| $d_{ij}$ | distancia entre $i$ y $j$ |
| $\tau_{ij}$ | tiempo de viaje entre $i$ y $j$ (igual a $d_{ij}$, velocidad 1) |
| $s_i$ | tiempo de servicio en el cliente $i$ |
| $q_{it}$ | demanda del cliente $i$ el día $t$ |
| $Q$ | capacidad de cada vehículo |
| $[a_i, b_i]$ | ventana de tiempo del cliente $i \in W$ |
| $[E, L]$ | horario de operación del depósito |
| $M_{ij}$ | constante Big-M calibrada para cada arco (ver abajo) |

## Variables

| Variable | Tipo | Significado |
|---|---|---|
| $X_{rijt}$ | binaria | 1 si la ruta $r$ recorre el arco $(i,j)$ el día $t$ |
| $Z_{ri}$ | binaria | 1 si el cliente $i$ queda asignado a la ruta $r$ (todo el horizonte) |
| $A_{it}$ | continua | instante en que comienza el servicio en $i$ el día $t$ |
| $S_r$ | continua | hora de salida planificada de la ruta $r$ desde el depósito (la misma todos los días) |
| $F_{rt}$ | continua | hora de retorno de la ruta $r$ al depósito el día $t$ |

## Correspondencia con la notación del paper

| Aquí | Paper | Aquí | Paper |
|---|---|---|---|
| $T$ | $\mathcal{D}$ | $X_{rijt}$ | $X^r_{ijt}$ |
| $N$ | $\mathcal{N}_C$ | $Z_{ri}$ | $Z^r_i$ |
| $W$ | $\mathcal{N}_{TW}$ | $A_{it}$ | $W_{it}$ |
| $d_{ij}$ | $td_{ij}$ | $S_r$ | $dW^r$ |
| $\tau_{ij}$ | $tt_{ij}$ | $F_{rt}$ | $rW^r_t$ |
| $s_i$ | $st_{it}$ | $[E, L]$ | $[aW, bW]$ |

## Modelo

**(1) Función objetivo.** Minimizar la distancia total recorrida por todas las rutas en todos los días.

$$\min \sum_{t\in T}\sum_{r\in R}\sum_{(i,j)\in V_t^2,\, i\ne j} d_{ij}\, X_{rijt}$$

**(2) Asignación cliente–ruta.** Cada cliente queda asignado a exactamente una ruta; esta es la restricción que impone la consistencia.

$$\sum_{r\in R} Z_{ri} = 1 \qquad \forall i\in N$$

**(3) Grado de salida.** Si el cliente está en la ruta $r$, ese día la ruta sale de él una vez; si no, no sale.

$$\sum_{j\in V_t,\, j\ne i} X_{rijt} = Z_{ri} \qquad \forall r\in R,\ t\in T,\ i\in N_t$$

**(4) Grado de entrada.** Lo mismo para la llegada al cliente.

$$\sum_{j\in V_t,\, j\ne i} X_{rjit} = Z_{ri} \qquad \forall r\in R,\ t\in T,\ i\in N_t$$

**(5) Salida del depósito.** Cada ruta sale del depósito a lo más una vez por día.

$$\sum_{j\in N_t} X_{r0jt} \le 1 \qquad \forall r\in R,\ t\in T$$

**(7) Tiempo de llegada (Big-M).** Si se va de $i$ a $j$, el servicio en $j$ empieza después de terminar en $i$ y viajar. Además elimina subtours, porque $s_i+\tau_{ij}>0$.

$$A_{jt} \ge A_{it} + s_i + \tau_{ij} - M_{ij}\Big(1-\sum_{r\in R} X_{rijt}\Big) \qquad \forall t\in T,\ i,j\in N_t,\ i\ne j$$

**(8) Ventanas de tiempo.** Solo para los clientes que tienen ventana.

$$a_i \le A_{it} \le b_i \qquad \forall t\in T,\ i\in N_t\cap W$$

**(9) Coordinación con la salida.** El primer cliente se atiende después de salir del depósito y viajar hasta él.

$$A_{jt} \ge S_r + \tau_{0j} - M_{0j}(1-X_{r0jt}) \qquad \forall r\in R,\ t\in T,\ j\in N_t$$

**(10) Coordinación con el retorno.** La ruta vuelve al depósito después de atender al último cliente.

$$F_{rt} \ge A_{it} + s_i + \tau_{i0} - M_{i0}(1-X_{ri0t}) \qquad \forall r\in R,\ t\in T,\ i\in N_t$$

**(11) Apertura del depósito.** Ninguna ruta sale antes de que abra el depósito.

$$S_r \ge E \qquad \forall r\in R$$

**(12) Cierre del depósito.** Toda ruta vuelve antes del cierre.

$$F_{rt} \le L \qquad \forall r\in R,\ t\in T$$

**(14) Capacidad.** La demanda de los clientes de una ruta, en cada día, no supera la capacidad del vehículo. Como la asignación $Z$ es fija para todo el horizonte, la capacidad se debe respetar el día de mayor carga de cada ruta.

$$\sum_{i\in N_t} q_{it}\, Z_{ri} \le Q \qquad \forall r\in R,\ t\in T$$

**(16) Dominio de las variables.**

$$X_{rijt},\ Z_{ri}\in\{0,1\};\qquad A_{it},\ S_r,\ F_{rt}\ge 0$$

## Calibración del Big-M

Un $M$ enorme es válido, pero debilita mucho la relajación lineal. Por eso se usa el
menor valor que mantiene válida cada restricción. Primero se calcula, para cada cliente,
el intervalo en que realmente puede empezar su servicio:

$$lo_i = \max(a_i,\ E + \tau_{0i}), \qquad hi_i = \min(b_i,\ L - s_i - \tau_{i0})$$

Si el cliente no tiene ventana se toma $a_i = E$ y $b_i = L$. Con eso:

| Restricción | Big-M |
|---|---|
| (7) | $M_{ij} = \max(0,\ hi_i + s_i + \tau_{ij} - lo_j)$ |
| (9) | $M_{0j} = \max(0,\ L + \tau_{0j} - lo_j)$ |
| (10) | $M_{i0} = \max(0,\ hi_i + s_i + \tau_{i0} - E)$ |

Cuando la restricción está "apagada" ($X=0$), el lado derecho queda por debajo del menor
valor posible del lado izquierdo, así que no corta ninguna solución factible. Que todo
cliente atendido cumpla $lo_i \le A_{it} \le hi_i$ se apoya en la desigualdad triangular de
las distancias euclidianas: ir por otro cliente nunca es más corto que ir directo.

## Fuera del alcance

- **(6)** y los varios períodos de despacho para un mismo cliente: cada cliente es un solo nodo y se visita a lo más una vez por día.
- **(13)** Fechas de liberación de los pedidos ($rd_i$).
- **(15)** Duración máxima de una ruta ($MD$).

## Diferencias con el paper

Las seis son decisiones de modelación; ninguna cambia el conjunto de soluciones factibles del problema reducido.

1. **Depósito en un solo nodo.** El paper usa dos nodos (0 de salida y $n{+}1$ de retorno), escribe (5) con "$=1$" y deja un arco ficticio $(0, n{+}1, t)$ para el día en que la ruta no sale. Aquí el depósito es solo el nodo 0, y (5) es "$\le 1$": no salir equivale a no usar ningún arco. Es la misma restricción con menos variables.
2. **(3)–(4) día por día.** El paper escribe $\sum_i \sum_{t\in\mathcal{D}} X^r_{ijt} = Z^r_j$, lo que leído al pie de la letra obliga a visitar cada nodo una sola vez en todo el horizonte. El texto del paper dice que cada nodo se visita "only when it has placed an order on that particular day", así que se impone por cada día $t$ con demanda.
3. **(7) agregada sobre las rutas.** El paper escribe una restricción por ruta, con $M(1-X^r_{ijt})$. Aquí se usa $M_{ij}(1-\sum_r X_{rijt})$: es válida porque a lo más una ruta usa el arco $(i,j)$ cada día, y es más fuerte. En la instancia de ejemplo la relajación sube de 856.3 a 882.24 y las restricciones bajan de 1957 a 1017.
4. **Un Big-M por arco** en vez de una sola constante $M$, calibrado como se explica arriba.
5. **Servicio constante.** El paper permite $st_{it}$ distinto por día; aquí $s_i$ es igual todos los días.
6. **$S_r$ y $F_{rt}$ sin rol activo.** Igual que en el paper, la salida es una por ruta ($dW^r$) y el retorno uno por ruta y día. Sin la (13), $S_r = E$ siempre es factible, así que en el modelo reducido $S_r$ y $F_{rt}$ solo acotan a los horarios del depósito.

## Observaciones para la presentación

- Las rutas son **idénticas entre sí** (misma capacidad, mismo depósito), así que intercambiar sus etiquetas da soluciones equivalentes. Esa simetría agranda el árbol de branch-and-bound y es parte de por qué el modelo cuesta. No se agregan restricciones de ruptura de simetría para no alterar el modelo pedido.
- $S_r$ y $F_{rt}$ solo están acotadas: en el óptimo pueden quedar en $E$ y $L$. Los horarios efectivos se obtienen de $A_{it}$.
