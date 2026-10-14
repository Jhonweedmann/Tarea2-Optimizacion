"""Extracción y verificación independiente de una solución del ConVRP.

La validación NO confía en el modelo: reconstruye cada ruta siguiendo los arcos
y vuelve a revisar todas las condiciones del problema con los datos originales.
"""
from __future__ import annotations

from modelo import ModeloConVRP

TOL = 1e-4


def extraer_solucion(mod: ModeloConVRP) -> dict:
    """Devuelve las rutas como listas de nodos [0, i1, i2, ..., 0] por (r, t)."""
    inst = mod.inst
    asign = {i: r for r in inst.rutas for i in inst.clientes if mod.Z[r, i].X > 0.5}
    rutas = {}
    for t in inst.dias:
        for r in inst.rutas:
            sucesor = {i: j for (rr, i, j, tt), v in mod.X.items()
                       if rr == r and tt == t and v.X > 0.5}
            camino = [0]
            if 0 in sucesor:
                actual = sucesor[0]
                while actual != 0 and len(camino) <= len(inst.clientes) + 1:
                    camino.append(actual)
                    actual = sucesor.get(actual, 0)
                camino.append(0)
            rutas[r, t] = {
                "camino": camino,
                "arcos": sucesor,
                "salida": mod.S[r, t].X,
                "retorno": mod.F[r, t].X,
                "llegadas": {i: mod.A[i, t].X for i in camino[1:-1]},
            }
    return {"asignacion": asign, "rutas": rutas, "objetivo": mod.m.ObjVal}


def validar_solucion(mod: ModeloConVRP, sol: dict | None = None) -> list[str]:
    """Lista de errores encontrados (vacía si la solución es válida)."""
    inst = mod.inst
    sol = sol or extraer_solucion(mod)
    errores: list[str] = []
    asign, rutas = sol["asignacion"], sol["rutas"]

    # Consistencia: cada cliente con exactamente una ruta
    for i in inst.clientes:
        n = sum(mod.Z[r, i].X > 0.5 for r in inst.rutas)
        if n != 1:
            errores.append(f"Cliente {i} asignado a {n} rutas")

    distancia_total = 0.0
    for (r, t), ruta in rutas.items():
        camino = ruta["camino"]
        visitados = camino[1:-1]

        # Todos los arcos usados deben estar en el camino desde el depósito (sin subtours)
        if len(ruta["arcos"]) != max(0, len(camino) - 1):
            errores.append(f"Ruta {r} día {t}: hay arcos fuera del recorrido (subtour)")
        if len(set(visitados)) != len(visitados):
            errores.append(f"Ruta {r} día {t}: visita un cliente dos veces")

        # Visita exactamente a los clientes asignados con demanda ese día
        esperados = {i for i in inst.N(t) if asign.get(i) == r}
        if set(visitados) != esperados:
            errores.append(
                f"Ruta {r} día {t}: visita {sorted(visitados)}, debería visitar {sorted(esperados)}")

        # Capacidad
        carga = sum(inst.demanda[i, t] for i in visitados)
        if carga > inst.Q + TOL:
            errores.append(f"Ruta {r} día {t}: carga {carga} > Q={inst.Q}")

        if not visitados:
            continue

        # Tiempos: horario del depósito, precedencias y ventanas
        S, F, A = ruta["salida"], ruta["retorno"], ruta["llegadas"]
        if S < inst.E - TOL or F > inst.L + TOL:
            errores.append(f"Ruta {r} día {t}: fuera del horario del depósito ({S:.1f}-{F:.1f})")
        prev, listo = 0, S
        for i in visitados:
            if A[i] < listo + inst.tiempo(prev, i) - TOL:
                errores.append(f"Ruta {r} día {t}: llega a {i} antes de lo físicamente posible")
            if inst.tiene_ventana(i):
                a, b = inst.ventana[i]
                if not (a - TOL <= A[i] <= b + TOL):
                    errores.append(f"Cliente {i} día {t}: servicio en {A[i]:.1f} fuera de [{a}, {b}]")
            prev, listo = i, A[i] + inst.servicio[i]
        if F < listo + inst.tiempo(prev, 0) - TOL:
            errores.append(f"Ruta {r} día {t}: retorno al depósito inconsistente")

        distancia_total += sum(inst.dist[a, b] for a, b in zip(camino, camino[1:]))

    if abs(distancia_total - sol["objetivo"]) > 1e-3 * max(1, sol["objetivo"]):
        errores.append(f"Distancia recalculada {distancia_total:.2f} ≠ objetivo {sol['objetivo']:.2f}")
    return errores


def imprimir_solucion(mod: ModeloConVRP, sol: dict | None = None) -> None:
    inst = mod.inst
    sol = sol or extraer_solucion(mod)
    print(f"\nDistancia total: {sol['objetivo']:.2f}")
    for r in inst.rutas:
        clientes_r = sorted(i for i, rr in sol["asignacion"].items() if rr == r)
        print(f"\nRuta {r} (clientes fijos: {clientes_r})")
        for t in inst.dias:
            ruta = sol["rutas"][r, t]
            if len(ruta["camino"]) <= 2:
                print(f"  Día {t}: no sale")
                continue
            vis = ruta["camino"][1:-1]
            carga = sum(inst.demanda[i, t] for i in vis)
            pasos = " → ".join(
                "D" if i == 0 else f"{i}@{ruta['llegadas'][i]:.0f}" for i in ruta["camino"])
            # S y F del modelo son holguras (solo acotan); se reportan los horarios efectivos
            sale = ruta["llegadas"][vis[0]] - inst.tiempo(0, vis[0])
            vuelve = ruta["llegadas"][vis[-1]] + inst.servicio[vis[-1]] + inst.tiempo(vis[-1], 0)
            print(f"  Día {t}: {pasos}  | carga {carga:.0f}/{inst.Q:.0f}, "
                  f"sale ≤{sale:.0f}, vuelve ≥{vuelve:.0f}")
