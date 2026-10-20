import argparse
import csv
import os
from datetime import datetime
from pathlib import Path
from time import perf_counter

import gurobipy as gp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from instancia import cargar_instancia
from modelo import build_model
RAIZ = Path(__file__).resolve().parent.parent

'''Configuraciones de Gurobi para evaluar'''
CONFIGURACIONES = {
    "baseline": {}, "Cuts=0": {"Cuts": 0}, "Presolve=0": {"Presolve": 0},
    "MIPFocus=1": {"MIPFocus": 1}, "MIPFocus=3": {"MIPFocus": 3},
    "Heuristics=0": {"Heuristics": 0},
}
'''Estados de gurobi'''
ESTADOS = {2: "OPTIMAL", 3: "INFEASIBLE", 4: "INF_OR_UNBD", 5: "UNBOUNDED",
           9: "TIME_LIMIT", 11: "INTERRUPTED", 13: "SUBOPTIMAL"}

def mod_nv(inst, limite, parametros=None, archivo=None):
    """Por cada instancia construye un modelo"""
    m = build_model(inst, verbose=False).m
    if archivo:
        m.read(str(archivo.relative_to(RAIZ)))
    for nombre, valor in (parametros or {}).items():
        m.setParam(nombre, valor)
    m.Params.Threads = 1
    m.Params.TimeLimit = limite
    return m

def resolver(inst, nombre, limite, parametros=None, archivo=None):
    '''Resuelve la instancia con los parámetros dados'''
    with mod_nv(inst, limite, parametros, archivo) as m:
        m.optimize()
        '''Devuelve un diccionario con los resultados de cada corrida'''
        return {
            "instancia": inst.nombre, "configuracion": nombre,
            "estado": ESTADOS.get(m.Status, str(m.Status)),
            "tiempo_s": m.Runtime, "gap_%": 100 * m.MIPGap if m.SolCount else None,
            "objetivo": m.ObjVal if m.SolCount else None,
            "cota": m.ObjBound, "nodos": int(m.NodeCount),
        }

def ajustar(inst, limite, presupuesto, carpeta):
    """Busca parámetros y los guarda para evaluarlos en otro modelo limpio."""
    with mod_nv(inst, limite) as m:
        m.Params.OutputFlag = 1
        m.Params.LogToConsole = 0
        m.Params.LogFile = str(carpeta.relative_to(RAIZ) / f"{inst.nombre}_tuning.log")
        m.Params.TuneTimeLimit = presupuesto
        inicio = perf_counter()
        m.tune()
        texto = f"Búsqueda: {perf_counter() - inicio:.2f} s. Conjuntos: {m.TuneResultCount}.\n"
        archivo = None
        if m.TuneResultCount:
            indice = 1 if gp.gurobi.version()[0] >= 13 and m.TuneResultCount > 1 else 0
            m.getTuneResult(indice)
            m.Params.OutputFlag = 0
            archivo = carpeta / f"{inst.nombre}_tuning.prm"
            m.write(str(archivo.relative_to(RAIZ)))
            texto += f"Se evaluará el conjunto {indice} desde cero\n"
        else:
            texto += "No hay parámetros disponibles: no se inventa una fila de tuning\n"
        (carpeta / f"{inst.nombre}_tuning.txt").write_text(texto, encoding="utf-8")
        return archivo

def grafico(filas, carpeta, limite):
    '''Gráfico con los resultados de cada instancia y configuración'''
    for instancia in dict.fromkeys(f["instancia"] for f in filas):
        datos = [f for f in filas if f["instancia"] == instancia]
        nombres = [f["configuracion"] for f in datos]
        fig, ejes = plt.subplots(1, 3, figsize=(13, 4))

        for eje, campo in zip(ejes, ["tiempo_s", "gap_%", "objetivo"]):
            valores = [
                f[campo] if f[campo] is not None else float("nan")
                for f in datos
            ]
            eje.bar(nombres, valores, color="#2878a5")

            for i, valor in enumerate(valores):
                if not (float("-inf") < valor < float("inf")):
                    eje.text(i, 0, "N/D", ha="center", va="bottom")

            eje.set_title(campo)
            eje.tick_params(axis="x", labelrotation=65)

        fig.suptitle(f"{instancia} | 1 hilo | límite {limite} s")
        fig.tight_layout()
        fig.savefig(carpeta / f"{instancia}.png", dpi=160)
        plt.close(fig)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("instancias", nargs="*", default=[str(RAIZ / "instancias/A_capacidad.json"),
                                                   str(RAIZ / "instancias/C_clusters.json")])
    p.add_argument("--prueba", action="store_true", help="2 s por corrida y 5 s de tuning; solo verificar")
    p.add_argument("--sin-tuning", action="store_true", help="ejecutar solo las seis configuraciones manuales")
    p.add_argument("--tune-time-limit", type=int, default=1800, choices=range(1800, 3601), metavar="1800..3600")
    a = p.parse_args()
    a.instancias = [str(Path(r).resolve()) for r in a.instancias]
    os.chdir(RAIZ) 

    limite, presupuesto = (2, 5) if a.prueba else (600, a.tune_time_limit)
    carpeta = RAIZ / "resultados" / ("prueba_" if a.prueba else "experimentos_")
    carpeta = carpeta.with_name(carpeta.name + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    carpeta.mkdir(parents=True)

    (carpeta / "ejecucion.txt").write_text(
        f"Gurobi {gp.gurobi.version()}; Threads=1; TimeLimit={limite}; TuneTimeLimit={presupuesto}\n"
        + "\n".join(str(Path(r).resolve()) for r in a.instancias), encoding="utf-8")
    filas = []
    with (carpeta / "resultados.csv").open("w", newline="", encoding="utf-8-sig") as salida:
        for ruta in a.instancias:
            inst = cargar_instancia(ruta)
            configuraciones = dict(CONFIGURACIONES)
            if not a.sin_tuning:
                configuraciones["tuning"] = {}
            for nombre, parametros in configuraciones.items():
                archivo = ajustar(inst, limite, presupuesto, carpeta) if nombre == "tuning" else None
                if nombre == "tuning" and archivo is None:
                    continue
                fila = resolver(inst, nombre, limite, parametros, archivo)
                if not filas:
                    escritor = csv.DictWriter(salida, fieldnames=list(fila))
                    escritor.writeheader()
                escritor.writerow(fila)
                salida.flush() 
                filas.append(fila)
                grafico(filas, carpeta, limite)

if __name__ == "__main__":
    main()