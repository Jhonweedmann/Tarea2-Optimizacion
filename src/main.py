"""Resuelve una instancia del ConVRP, valida la solución y guarda el resultado.

Uso:
    python src/main.py instancias/ejemplo_15c.json
    python src/main.py instancias/ejemplo_15c.json --time-limit 600 --threads 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gurobipy import GRB

from instancia import cargar_instancia
from modelo import build_model
from validar import extraer_solucion, imprimir_solucion, validar_solucion

ESTADOS = {GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT",
           GRB.INFEASIBLE: "INFEASIBLE", GRB.INF_OR_UNBD: "INF_OR_UNBD"}


def resolver(ruta_instancia: str, time_limit: float = 600, threads: int = 1,
             verbose: bool = True) -> dict:
    inst = cargar_instancia(ruta_instancia)
    print(inst.resumen())

    mod = build_model(inst, verbose=verbose)
    m = mod.m
    print(f"\nModelo: {m.NumVars} variables ({m.NumBinVars} binarias), {m.NumConstrs} restricciones")

    m.Params.TimeLimit = time_limit
    m.Params.Threads = threads
    m.optimize()

    resultado = {
        "instancia": inst.nombre,
        "estado": ESTADOS.get(m.Status, str(m.Status)),
        "tiempo_s": round(m.Runtime, 2),
        "objetivo": m.ObjVal if m.SolCount else None,
        "cota": m.ObjBound,
        "gap_%": round(100 * m.MIPGap, 4) if m.SolCount else None,
        "nodos": int(m.NodeCount),
    }
    if m.SolCount:
        sol = extraer_solucion(mod)
        imprimir_solucion(mod, sol)
        errores = validar_solucion(mod, sol)
        resultado["valida"] = not errores
        print("\nValidación:", "OK, la solución cumple todas las restricciones" if not errores
              else "\n  " + "\n  ".join(errores))
        resultado["rutas"] = {
            f"r{r}_d{t}": v["camino"] for (r, t), v in sol["rutas"].items()}
        resultado["asignacion"] = {str(i): r for i, r in sol["asignacion"].items()}
    else:
        print("\nNo se encontró solución factible.")

    out = Path(__file__).resolve().parent.parent / "resultados" / f"{inst.nombre}_solucion.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(f"\nResumen: {resultado['estado']}, obj={resultado['objetivo']}, "
          f"gap={resultado['gap_%']}%, {resultado['tiempo_s']} s → {out}")
    return resultado


if __name__ == "__main__":
    # En Windows la consola por defecto (cp1252) no imprime "→" y el script se cae
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("instancia")
    p.add_argument("--time-limit", type=float, default=600)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--silencioso", action="store_true")
    a = p.parse_args()
    resolver(a.instancia, a.time_limit, a.threads, verbose=not a.silencioso)
