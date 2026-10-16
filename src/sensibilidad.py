"""Análisis de sensibilidad de la capacidad Q con Model.fixed()

Pasos:
  1. Resolver el PLEM (Threads=1, TimeLimit configurable) y quedarse con la mejor solución.
  2. fx = m.fixed(): modelo LP con las variables enteras fijadas en esa solución.
  3. Resolver fx y leer, para cada restricción de capacidad cap[r,t] (14):
       Pi (precio sombra), RHS (= Q), Slack, SARHSLow y SARHSUp.
  4. (Opcional, --escenarios) re-optimizar el MIP con otros valores de Q para medir el
     efecto *real* de Q sobre la distancia, que fixed() no puede ver (ver nota abajo).

NOTA SOBRE LA INTERPRETACIÓN
Al fijar las binarias Z, la carga de cada ruta/día queda constante, así que cambiar Q
no cambia el costo: Pi = 0 en TODAS las restricciones cap (también en las "apretadas").
Lo que sí informa fixed() es el rango de validez: la solución sigue siendo factible y
óptima (con la asignación fija) mientras SARHSLow <= Q <= SARHSUp. SARHSLow es la carga
de la ruta ese día; SARHSUp = inf. El precio sombra "con reoptimización" (cuánto cuesta
bajar Q y obligar a cambiar la asignación) se estima con --escenarios y con la
relajación lineal (Pi agregado de las cap en el LP).

Uso:
    python sensibilidad.py ../instancias/A_capacidad.json --time-limit 600
    python sensibilidad.py ../instancias/A_capacidad.json --escenarios -4 -2 2 4
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import sys
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

from instancia import Instancia, cargar_instancia
from modelo import build_model

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"
INF = 1e20  # Gurobi usa +-1e20 para "infinito" en los rangos de sensibilidad


def _fmt(v: float) -> str:
    if v >= INF:
        return "inf"
    if v <= -INF:
        return "-inf"
    return f"{v:.2f}"


def resolver_mip(inst: Instancia, time_limit: float, threads: int = 1, verbose: bool = False):
    mod = build_model(inst, verbose=verbose)
    mod.m.Params.TimeLimit = time_limit
    mod.m.Params.Threads = threads
    mod.m.optimize()
    return mod


def sensibilidad_capacidad(mod) -> list[dict]:
    """Resuelve m.fixed() y devuelve una fila por restricción cap[r,t]."""
    m, inst = mod.m, mod.inst
    if m.SolCount == 0:
        raise RuntimeError("No hay solución entera: no se puede construir fixed()")
    fx = m.fixed()
    fx.Params.OutputFlag = 0
    fx.Params.Threads = 1
    fx.optimize()
    if fx.Status != GRB.OPTIMAL:
        raise RuntimeError(f"fixed() terminó con estado {fx.Status}")

    filas = []
    for r in inst.rutas:
        for t in inst.dias:
            c = fx.getConstrByName(f"cap[{r},{t}]")
            carga = sum(inst.demanda[i, t] for i in inst.N(t) if mod.Z[r, i].X > 0.5)
            filas.append({
                "ruta": r, "dia": t,
                "clientes": sum(mod.Z[r, i].X > 0.5 for i in inst.N(t)),
                "carga": carga,
                "RHS_Q": c.RHS,
                "holgura": c.Slack,
                "utilizacion_%": 100 * carga / inst.Q,
                "Pi": c.Pi,
                "SARHSLow": c.SARHSLow,
                "SARHSUp": c.SARHSUp,
            })
    return filas


def pi_relajacion(inst: Instancia, threads: int = 1) -> dict:
    """Referencia: duales de cap[r,t] en la relajación lineal (sin fijar nada).

    La suma de los Pi es la derivada de zLP respecto de Q si Q cambia en las 9
    restricciones a la vez (válida dentro del rango de la base óptima del LP).
    """
    mod = build_model(inst, verbose=False)
    lp = mod.m.relax()
    lp.Params.OutputFlag = 0
    lp.Params.Threads = threads
    lp.optimize()
    pis = {(r, t): lp.getConstrByName(f"cap[{r},{t}]").Pi for r in inst.rutas for t in inst.dias}
    return {"zLP": lp.ObjVal, "Pi_total": sum(pis.values()), "Pi": pis}


def reoptimizar_con_Q(inst: Instancia, deltas: list[float], time_limit: float, threads: int = 1):
    """Resuelve el MIP completo con Q + delta: costo real de ajustar la capacidad."""
    filas = []
    for d in deltas:
        inst2 = dataclasses.replace(inst, Q=inst.Q + d)
        try:
            mod = resolver_mip(inst2, time_limit, threads)
        except ValueError as e:      # cliente inatendible, etc.
            filas.append({"Q": inst2.Q, "delta": d, "estado": f"ERROR {e}"})
            continue
        m = mod.m
        ok = m.SolCount > 0
        filas.append({
            "Q": inst2.Q, "delta": d,
            "estado": "OPTIMAL" if m.Status == GRB.OPTIMAL else
                      "INFEASIBLE" if m.Status == GRB.INFEASIBLE else
                      "TIME_LIMIT" if m.Status == GRB.TIME_LIMIT else str(m.Status),
            "objetivo": m.ObjVal if ok else None,
            "cota": m.ObjBound if ok or m.Status == GRB.TIME_LIMIT else None,
            "gap_%": 100 * m.MIPGap if ok else None,
            "tiempo_s": m.Runtime,
        })
    return filas


def imprimir(inst: Instancia, mod, filas: list[dict], rel: dict | None, esc: list[dict] | None):
    m = mod.m
    print(f"\n=== Sensibilidad de Q — {inst.nombre} ===")
    print(f"MIP: obj={m.ObjVal:.2f}  cota={m.ObjBound:.2f}  gap={100 * m.MIPGap:.3f}%  "
          f"({'óptimo' if m.Status == GRB.OPTIMAL else 'mejor incumbente'})   Q={inst.Q:g}")
    print("\nRestricciones de capacidad (14) en el modelo fixed():")
    print(f"{'ruta':>4} {'día':>3} {'cli':>3} {'carga':>6} {'Q':>5} {'holg':>5} {'util%':>6} "
          f"{'Pi':>6} {'SARHSLow':>9} {'SARHSUp':>8}")
    for f in sorted(filas, key=lambda f: -f["carga"]):
        print(f"{f['ruta']:>4} {f['dia']:>3} {f['clientes']:>3} {f['carga']:>6.0f} {f['RHS_Q']:>5.0f} "
              f"{f['holgura']:>5.0f} {f['utilizacion_%']:>6.1f} {f['Pi']:>6.2f} "
              f"{_fmt(f['SARHSLow']):>9} {_fmt(f['SARHSUp']):>8}")

    q_min = max(f["SARHSLow"] for f in filas)
    criticas = [f for f in filas if f["holgura"] < 1e-6]
    print(f"\nInterpretación:")
    print(f"  - Pi = 0 en todas: con Z fija la carga es constante, Q no mueve el costo "
          f"({'se cumple' if all(abs(f['Pi']) < 1e-9 for f in filas) else 'ATENCIÓN: hay Pi ≠ 0'}).")
    print(f"  - Rango de validez conjunto: la solución sigue siendo factible y óptima "
          f"(con la asignación fija) para {q_min:.0f} <= Q <= inf.")
    limitantes = ", ".join(f"r{f['ruta']}d{f['dia']}" for f in filas if abs(f['SARHSLow'] - q_min) < 1e-6)
    if inst.Q - q_min < 1e-6:
        print(f"    No hay margen para bajar Q: ya está en el límite (lo fijan {limitantes}).")
    else:
        print(f"    Se puede reducir Q hasta {q_min:.0f} (−{inst.Q - q_min:.0f}, "
              f"{100 * (inst.Q - q_min) / inst.Q:.1f}%) sin cambiar rutas ni costo; "
              f"la ruta/día que lo limita es {limitantes}.")
    if criticas:
        print(f"  - Restricciones saturadas (holgura 0): "
              + ", ".join(f"r{f['ruta']}d{f['dia']}" for f in criticas))
    n_apretadas = sum(f["utilizacion_%"] >= 90 for f in filas)
    print(f"  - {n_apretadas} de {len(filas)} ruta-día tienen utilización ≥ 90 %.")

    if rel:
        print(f"\nReferencia — relajación lineal: zLP={rel['zLP']:.2f}, "
              f"suma de Pi de cap = {rel['Pi_total']:.3f} "
              f"(≈ cambio de zLP por unidad de Q en todas las rutas a la vez)")
    if esc:
        print("\nReoptimización con otros Q (efecto real de Q sobre el costo):")
        print(f"{'Q':>6} {'ΔQ':>5} {'estado':>11} {'objetivo':>10} {'cota':>9} {'gap%':>7} {'t(s)':>7} {'Δobj/ΔQ':>9}")
        for e in esc:
            if e.get("objetivo") is None:
                print(f"{e['Q']:>6g} {e['delta']:>+5g} {e['estado']:>11}")
                continue
            pend = (e["objetivo"] - m.ObjVal) / e["delta"] if e["delta"] else float("nan")
            print(f"{e['Q']:>6g} {e['delta']:>+5g} {e['estado']:>11} {e['objetivo']:>10.2f} "
                  f"{e['cota']:>9.2f} {e['gap_%']:>7.2f} {e['tiempo_s']:>7.1f} {pend:>9.2f}")
        if any(e.get("estado") != "OPTIMAL" for e in esc):
            print("  Ojo: donde el estado no es OPTIMAL, 'objetivo' es solo la mejor incumbente y "
                  "Δobj/ΔQ es ruidoso.\n  Solo valen como cotas: z*(Q') está entre 'cota' y 'objetivo'. "
                  "Subir --time-limit-escenarios (p. ej. 600).")


def guardar(inst: Instancia, mod, filas, rel, esc):
    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / f"sensibilidad_{inst.nombre}"
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        for f in filas:
            w.writerow({k: (_fmt(v) if k in ("SARHSLow", "SARHSUp") else v) for k, v in f.items()})
    resumen = {
        "instancia": inst.nombre, "Q": inst.Q,
        "objetivo": mod.m.ObjVal, "cota": mod.m.ObjBound, "gap_%": 100 * mod.m.MIPGap,
        "estado": "OPTIMAL" if mod.m.Status == GRB.OPTIMAL else "TIME_LIMIT",
        "Q_minimo_sin_cambiar_solucion": max(f["SARHSLow"] for f in filas),
        "Pi_max_abs": max(abs(f["Pi"]) for f in filas),
        "relajacion": ({"zLP": rel["zLP"], "Pi_total": rel["Pi_total"]} if rel else None),
        "escenarios_Q": esc,
        "filas": [{k: (None if isinstance(v, float) and abs(v) >= INF else v) for k, v in f.items()}
                  for f in filas],
    }
    base.with_suffix(".json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    print(f"\nGuardado en {base.with_suffix('.csv')} y {base.with_suffix('.json')}")
    return base


def grafico(inst: Instancia, filas, base: Path):
    """Carga de cada ruta/día frente a Q (para el pitch)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no está instalado: se omite el gráfico")
        return
    filas = sorted(filas, key=lambda f: (f["ruta"], f["dia"]))
    etiquetas = [f"R{f['ruta']}·D{f['dia']}" for f in filas]
    cargas = [f["carga"] for f in filas]
    colores = ["#c0392b" if f["utilizacion_%"] >= 90 else "#2e86c1" for f in filas]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(etiquetas, cargas, color=colores)
    ax.axhline(inst.Q, color="black", ls="--", lw=1.2, label=f"Q = {inst.Q:g}")
    q_min = max(f["SARHSLow"] for f in filas)
    ax.axhline(q_min, color="#c0392b", ls=":", lw=1.2, label=f"SARHSLow máx = {q_min:g}")
    ax.set_ylabel("Carga de la ruta")
    ax.set_title(f"{inst.nombre}: carga por ruta-día vs. capacidad (rojo: utilización ≥ 90 %)")
    ax.legend(loc="upper center", ncol=2, frameon=False)
    ax.set_ylim(0, inst.Q * 1.22)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    out = base.with_suffix(".png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"Gráfico en {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("instancia")
    p.add_argument("--time-limit", type=float, default=600)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--escenarios", type=float, nargs="*", default=[],
                   help="variaciones de Q (ej. -4 -2 2 4) para reoptimizar el MIP")
    p.add_argument("--time-limit-escenarios", type=float, default=300)
    p.add_argument("--sin-relajacion", action="store_true")
    p.add_argument("--sin-grafico", action="store_true")
    a = p.parse_args()

    inst = cargar_instancia(a.instancia)
    print(inst.resumen())
    mod = resolver_mip(inst, a.time_limit, a.threads)
    filas = sensibilidad_capacidad(mod)
    rel = None if a.sin_relajacion else pi_relajacion(inst, a.threads)
    esc = reoptimizar_con_Q(inst, a.escenarios, a.time_limit_escenarios, a.threads) if a.escenarios else None
    imprimir(inst, mod, filas, rel, esc)
    base = guardar(inst, mod, filas, rel, esc)
    if not a.sin_grafico:
        grafico(inst, filas, base)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
