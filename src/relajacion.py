"""Relajación continua y brecha de integralidad (Persona 3).

Reutiliza instancia.py y modelo.py del repositorio (no los modifica).

Hace tres cosas:
  1. Resuelve la relajación lineal (model.relax(): X, Z en [0,1]) -> z_LP.
  2. Obtiene z_MILP (mejor incumbente) resolviendo el entero con Threads=1,
     o leyéndolo de un resultado ya guardado por main.py (--milp-json), para no
     repetir 10 minutos de cómputo.
  3. Calcula la brecha de integralidad (zMILP - zLP) / zMILP * 100.

Extra (--comparar-m): repite la relajación con un Big-M "genérico" muy grande, para
mostrar cuánto debilita la cota un M mal calibrado frente al M ajustado del modelo.

Uso (desde la carpeta src):
    python relajacion.py ../instancias/B_ventanas.json
    python relajacion.py ../instancias/B_ventanas.json --milp-json ../resultados/inst_B_ventanas_solucion.json
    python relajacion.py ../instancias/B_ventanas.json --time-limit 600 --comparar-m

Resultados: resultados/relajacion_<instancia>.json y una fila en
resultados/relajacion_resumen.csv (una fila por instancia, para las tablas del pitch).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from gurobipy import GRB

import modelo
from instancia import cargar_instancia
from modelo import build_model

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"


def brecha_integralidad(z_milp: float, z_lp: float) -> float:
    """(zMILP - zLP) / zMILP * 100"""
    return (z_milp - z_lp) / z_milp * 100.0


def resolver_relajacion(inst, threads: int = 1, time_limit: float = 600, big_m_generico=None):
    """Relaja las binarias con model.relax() y resuelve el LP.

    big_m_generico: si se da un número, reemplaza TODOS los M ajustados por ese valor
    (solo para el experimento de comparación). Devuelve (z_LP, tiempo, info).
    """
    original = modelo.calcular_big_m
    if big_m_generico is not None:
        modelo.calcular_big_m = lambda ins: {k: big_m_generico for k in original(ins)}
    try:
        mod = build_model(inst, verbose=False)
    finally:
        modelo.calcular_big_m = original

    lp = mod.m.relax()
    lp.Params.OutputFlag = 0
    lp.Params.Threads = threads
    lp.Params.TimeLimit = time_limit
    lp.optimize()
    if lp.Status != GRB.OPTIMAL:
        raise RuntimeError(f"La relajación no terminó en óptimo (estado {lp.Status})")

    M = list(mod.big_m.values()) if big_m_generico is None else [big_m_generico]
    # fracción de arcos X fraccionales en la solución LP (qué tan "lejos" de entera)
    xs = [v.X for v in lp.getVars() if v.VarName.startswith("X[")]
    frac = sum(1 for x in xs if 1e-6 < x < 1 - 1e-6) / max(1, len(xs))
    info = {
        "M_promedio": sum(M) / len(M), "M_max": max(M),
        "iteraciones": int(lp.IterCount), "x_fraccionales_%": 100 * frac,
        "n_vars": mod.m.NumVars, "n_restr": mod.m.NumConstrs,
    }
    return lp.ObjVal, lp.Runtime, info


def obtener_milp(inst, threads: int, time_limit: float, milp_json: str | None):
    """Devuelve dict con objetivo, cota, gap_%, tiempo_s, estado del MIP."""
    if milp_json:
        d = json.loads(Path(milp_json).read_text(encoding="utf-8"))
        if d.get("objetivo") is None:
            raise RuntimeError("El resultado guardado no tiene solución factible")
        return {"objetivo": d["objetivo"], "cota": d["cota"], "gap_%": d["gap_%"],
                "tiempo_s": d["tiempo_s"], "estado": d["estado"]}
    mod = build_model(inst, verbose=False)
    mod.m.Params.OutputFlag = 0
    mod.m.Params.Threads = threads
    mod.m.Params.TimeLimit = time_limit
    mod.m.optimize()
    if mod.m.SolCount == 0:
        raise RuntimeError("El MIP no encontró solución factible en el tiempo límite")
    return {"objetivo": mod.m.ObjVal, "cota": mod.m.ObjBound, "gap_%": 100 * mod.m.MIPGap,
            "tiempo_s": mod.m.Runtime,
            "estado": "OPTIMAL" if mod.m.Status == GRB.OPTIMAL else "TIME_LIMIT"}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("instancia")
    p.add_argument("--time-limit", type=float, default=600)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--milp-json", default=None,
                   help="resultado de main.py con el objetivo del MIP (evita resolverlo de nuevo)")
    p.add_argument("--comparar-m", action="store_true",
                   help="repite la relajación con un Big-M genérico enorme")
    a = p.parse_args()

    inst = cargar_instancia(a.instancia)
    print(inst.resumen())

    z_lp, t_lp, info = resolver_relajacion(inst, a.threads, a.time_limit)
    print(f"\nRelajación continua: z_LP = {z_lp:.4f}  ({t_lp:.2f} s, {info['iteraciones']} iteraciones)")
    print(f"  Big-M ajustado: promedio {info['M_promedio']:.0f}, máximo {info['M_max']:.0f}")
    print(f"  Arcos X fraccionales en la solución LP: {info['x_fraccionales_%']:.1f} %")

    milp = obtener_milp(inst, a.threads, a.time_limit, a.milp_json)
    z_milp = milp["objetivo"]
    brecha = brecha_integralidad(z_milp, z_lp)
    brecha_cota = brecha_integralidad(z_milp, milp["cota"])
    print(f"\nModelo entero ({milp['estado']}): z_MILP = {z_milp:.4f}, "
          f"mejor cota B&B = {milp['cota']:.4f}, gap solver = {milp['gap_%']:.2f} %")
    print(f"Brecha de integralidad = (zMILP - zLP)/zMILP = {brecha:.2f} %")
    print(f"  (la cota que alcanza branch & bound en el tiempo dado cierra la brecha a "
          f"{brecha_cota:.2f} %)")
    assert z_lp <= z_milp + 1e-6, "ERROR: z_LP > z_MILP, la relajación debería ser cota inferior"
    print("  Chequeo de dualidad débil: z_LP <= z_MILP  OK")

    resultado = {
        "instancia": inst.nombre, "z_LP": z_lp, "z_MILP": z_milp,
        "brecha_integralidad_%": brecha, "cota_MIP": milp["cota"], "gap_solver_%": milp["gap_%"],
        "estado_MIP": milp["estado"], "tiempo_LP_s": t_lp, **info,
    }

    if a.comparar_m:
        M_gen = 10 * inst.L
        z_lp2, _, info2 = resolver_relajacion(inst, a.threads, a.time_limit, big_m_generico=M_gen)
        b2 = brecha_integralidad(z_milp, z_lp2)
        print(f"\nComparación con Big-M genérico M = {M_gen:.0f} (10 x cierre del depósito):")
        print(f"  z_LP = {z_lp2:.4f}  -> brecha {b2:.2f} %   "
              f"(con M ajustado: z_LP = {z_lp:.4f}, brecha {brecha:.2f} %)")
        resultado.update({"z_LP_M_generico": z_lp2, "M_generico": M_gen,
                          "brecha_M_generico_%": b2})

    RESULTADOS.mkdir(exist_ok=True)
    out = RESULTADOS / f"relajacion_{inst.nombre}.json"
    out.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = RESULTADOS / "relajacion_resumen.csv"
    nuevo = not csv_path.exists()
    campos = ["instancia", "z_LP", "z_MILP", "brecha_integralidad_%", "cota_MIP",
              "gap_solver_%", "estado_MIP", "M_promedio", "M_max", "x_fraccionales_%",
              "z_LP_M_generico", "brecha_M_generico_%"]
    with open(csv_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        w.writerow(resultado)
    print(f"\nGuardado en {out} y {csv_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
