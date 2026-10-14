# Formulación del ConVRP reducido

Versión reducida del modelo de Campelo, Neves-Moreira, Amorim y Almada-Lobo (2019),
*Consistent vehicle routing problem with service level agreements*, EJOR 273(1).
La numeración sigue la lista del enunciado de la tarea.

> **Revisar contra el paper.** Esta formulación se escribió a partir de la descripción
> del enunciado. Antes de la presentación hay que cotejar la notación y la numeración
> con el PDF y ajustar lo que difiera.

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
| $S_{rt}$ | continua | hora de salida de la ruta $r$ desde el depósito el día $t$ |
| $F_{rt}$ | continua | hora de retorno de la ruta $r$ al depósito el día $t$ |

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

$$A_{jt} \ge S_{rt} + \tau_{0j} - M_{0j}(1-X_{r0jt}) \qquad \forall r\in R,\ t\in T,\ j\in N_t$$

**(10) Coordinación con el retorno.** La ruta vuelve al depósito después de atender al último cliente.

$$F_{rt} \ge A_{it} + s_i + \tau_{i0} - M_{i0}(1-X_{ri0t}) \qquad \forall r\in R,\ t\in T,\ i\in N_t$$

**(11) Apertura del depósito.** Ninguna ruta sale antes de que abra el depósito.

$$S_{rt} \ge E \qquad \forall r\in R,\ t\in T$$

**(12) Cierre del depósito.** Toda ruta vuelve antes del cierre.

$$F_{rt} \le L \qquad \forall r\in R,\ t\in T$$

**(14) Capacidad.** La demanda de los clientes de una ruta, en cada día, no supera la capacidad del vehículo. Como la asignación $Z$ es fija para todo el horizonte, la capacidad se debe respetar el día de mayor carga de cada ruta.

$$\sum_{i\in N_t} q_{it}\, Z_{ri} \le Q \qquad \forall r\in R,\ t\in T$$

**(16) Dominio de las variables.**

$$X_{rijt},\ Z_{ri}\in\{0,1\};\qquad A_{it},\ S_{rt},\ F_{rt}\ge 0$$

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
valor posible del lado izquierdo, así que no corta ninguna solución factible.

## Fuera del alcance

- **(13)** Fechas de liberación de los pedidos ($rd_i$).
- **(15)** Duración máxima de una ruta.
- Varios períodos de despacho para un mismo cliente en un mismo día: cada cliente se visita a lo más una vez por día.

## Observaciones para la presentación

- Las rutas son **idénticas entre sí** (misma capacidad, mismo depósito), así que intercambiar sus etiquetas da soluciones equivalentes. Esa simetría agranda el árbol de branch-and-bound y es parte de por qué el modelo cuesta. No se agregan restricciones de ruptura de simetría para no alterar el modelo pedido.
- $S_{rt}$ y $F_{rt}$ solo están acotadas: en el óptimo pueden quedar en $E$ y $L$. Los horarios efectivos se obtienen de $A_{it}$.
