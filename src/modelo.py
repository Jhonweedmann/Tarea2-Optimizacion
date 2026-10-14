"""Modelo PLEM del ConVRP reducido (Campelo et al., 2019) en gurobipy.

La numeración de las restricciones sigue la lista del enunciado de la tarea:
(1) objetivo, (2) asignación cliente-ruta, (3)-(4) grado, (5) salida del depósito,
(7) tiempo de llegada con Big-M, (8) ventanas, (9)-(10) salida/retorno,
(11)-(12) horario del depósito, (14) capacidad, (16) dominio de las variables.

Uso:
    from instancia import cargar_instancia
    from modelo import build_model
    inst = cargar_instancia("instancias/ejemplo_15c.json")
    mod = build_model(inst)
    mod.m.optimize()
"""
from __future__ import annotations

from dataclasses import dataclass

import gurobipy as gp
from gurobipy import GRB

from instancia import Instancia


@dataclass
class ModeloConVRP:
    m: gp.Model
    inst: Instancia
    X: gp.tupledict        # X[r,i,j,t] arco (i,j) recorrido por la ruta r el día t
    Z: gp.tupledict        # Z[r,i]     cliente i asignado a la ruta r (todos los días)
    A: gp.tupledict        # A[i,t]     inicio de servicio en i el día t
    S: gp.tupledict        # S[r]       salida planificada de la ruta r (igual todos los días, dW^r)
    F: gp.tupledict        # F[r,t]     retorno de la ruta r al depósito el día t
    cap: gp.tupledict      # restricciones (14), para el análisis de sensibilidad de Q
    big_m: dict            # valores de M usados, por si se quieren reportar


# ---------------------------------------------------------------------------
# Big-M calibrado
# ---------------------------------------------------------------------------
def ventanas_efectivas(inst: Instancia) -> dict[int, tuple[float, float]]:
    """Intervalo [lo_i, hi_i] en que puede comenzar el servicio en i.

    lo_i = max(a_i, E + t_0i): no se puede llegar antes de salir del depósito.
    hi_i = min(b_i, L - s_i - t_i0): hay que poder volver antes del cierre.
    Si el cliente no tiene ventana se usa a_i = E y b_i = L.
    """
    vent = {}
    for i in inst.clientes:
        a, b = inst.ventana[i] if inst.tiene_ventana(i) else (inst.E, inst.L)
        lo = max(a, inst.E + inst.tiempo(0, i))
        hi = min(b, inst.L - inst.servicio[i] - inst.tiempo(i, 0))
        if lo > hi + 1e-9:
            raise ValueError(
                f"Cliente {i} es inatendible: ventana efectiva [{lo:.1f}, {hi:.1f}] vacía"
            )
        vent[i] = (lo, hi)
    return vent


def calcular_big_m(inst: Instancia) -> dict:
    """M más pequeño que mantiene válidas las restricciones (7), (9) y (10).

    (7)  A_j >= A_i + s_i + t_ij - M_ij (1 - x):  M_ij = hi_i + s_i + t_ij - lo_j
    (9)  A_j >= S_r + t_0j        - M_0j (1 - x):  M_0j = L + t_0j - lo_j
    (10) F_r >= A_i + s_i + t_i0  - M_i0 (1 - x):  M_i0 = hi_i + s_i + t_i0 - E
    Un M ajustado fortalece la relajación lineal (menor brecha de integralidad).
    """
    v = ventanas_efectivas(inst)
    s, t = inst.servicio, inst.tiempo
    M = {}
    for i in inst.clientes:
        for j in inst.clientes:
            if i != j:
                M[i, j] = max(0.0, v[i][1] + s[i] + t(i, j) - v[j][0])
        M[0, i] = max(0.0, inst.L + t(0, i) - v[i][0])
        M[i, 0] = max(0.0, v[i][1] + s[i] + t(i, 0) - inst.E)
    return M


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
def build_model(inst: Instancia, nombre: str | None = None, verbose: bool = True) -> ModeloConVRP:
    m = gp.Model(nombre or f"ConVRP_{inst.nombre}")
    if not verbose:
        m.Params.OutputFlag = 0

    R, T, C = inst.rutas, inst.dias, inst.clientes
    s, q, Q, E, L = inst.servicio, inst.demanda, inst.Q, inst.E, inst.L
    M = calcular_big_m(inst)   # también verifica que cada cliente sea atendible

    # ---- variables (16) -----------------------------------------------------
    idx_x = [(r, i, j, t) for t in T for (i, j) in inst.arcos(t) for r in R]
    X = m.addVars(idx_x, vtype=GRB.BINARY, name="X")
    Z = m.addVars(R, C, vtype=GRB.BINARY, name="Z")
    A = m.addVars([(i, t) for t in T for i in inst.N(t)], lb=E, ub=L, name="A")
    S = m.addVars(R, lb=E, ub=L, name="S")
    F = m.addVars(R, T, lb=E, ub=L, name="F")

    # ---- (1) función objetivo: distancia total ------------------------------
    m.setObjective(
        gp.quicksum(inst.dist[i, j] * X[r, i, j, t] for (r, i, j, t) in idx_x),
        GRB.MINIMIZE,
    )

    # ---- (2) cada cliente se asigna a una única ruta (consistencia) ----------
    m.addConstrs((Z.sum("*", i) == 1 for i in C), name="asig")

    for t in T:
        Nt, Vt = inst.N(t), inst.V(t)

        # ---- (3) grado de salida y (4) grado de entrada ---------------------
        # Si i está en la ruta r, ese día la ruta r sale de i y entra a i
        # exactamente una vez; si no, la ruta r no lo toca.
        m.addConstrs(
            (gp.quicksum(X[r, i, j, t] for j in Vt if j != i) == Z[r, i]
             for r in R for i in Nt), name=f"sale[{t}]")
        m.addConstrs(
            (gp.quicksum(X[r, j, i, t] for j in Vt if j != i) == Z[r, i]
             for r in R for i in Nt), name=f"entra[{t}]")

        # ---- (5) cada ruta sale del depósito a lo más una vez por día -------
        m.addConstrs(
            (gp.quicksum(X[r, 0, j, t] for j in Nt) <= 1 for r in R), name=f"dep[{t}]")

        # ---- (7) propagación del tiempo de llegada (Big-M) ------------------
        # También elimina subtours, porque s_i + t_ij > 0.
        m.addConstrs(
            (A[j, t] >= A[i, t] + s[i] + inst.tiempo(i, j)
             - M[i, j] * (1 - gp.quicksum(X[r, i, j, t] for r in R))
             for i in Nt for j in Nt if i != j), name=f"tiempo[{t}]")

        # ---- (8) ventanas de tiempo (solo clientes con ventana) -------------
        for i in Nt:
            if inst.tiene_ventana(i):
                a, b = inst.ventana[i]
                m.addConstr(A[i, t] >= a, name=f"vent_ini[{i},{t}]")
                m.addConstr(A[i, t] <= b, name=f"vent_fin[{i},{t}]")

        # ---- (9) primera llegada respecto de la salida del depósito ---------
        m.addConstrs(
            (A[j, t] >= S[r] + inst.tiempo(0, j) - M[0, j] * (1 - X[r, 0, j, t])
             for r in R for j in Nt), name=f"salida[{t}]")

        # ---- (10) retorno al depósito tras el último cliente ----------------
        m.addConstrs(
            (F[r, t] >= A[i, t] + s[i] + inst.tiempo(i, 0) - M[i, 0] * (1 - X[r, i, 0, t])
             for r in R for i in Nt), name=f"retorno[{t}]")

    # ---- (11)-(12) horario de operación del depósito ------------------------
    m.addConstrs((S[r] >= E for r in R), name="dep_abre")
    m.addConstrs((F[r, t] <= L for r in R for t in T), name="dep_cierra")

    # ---- (14) capacidad del vehículo, por ruta y día ------------------------
    cap = m.addConstrs(
        (gp.quicksum(q[i, t] * Z[r, i] for i in inst.N(t)) <= Q for r in R for t in T),
        name="cap")

    m.update()
    return ModeloConVRP(m=m, inst=inst, X=X, Z=Z, A=A, S=S, F=F, cap=cap, big_m=M)
