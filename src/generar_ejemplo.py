"""Genera una instancia sintética de PRUEBA para desarrollar y depurar el modelo.

Las instancias definitivas las construye la Persona 2 (a partir de Solomon /
Gehring & Homberger). Esta solo sirve para verificar que el código funciona.

Uso:  python src/generar_ejemplo.py --clientes 15 --semilla 7
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def generar(n_clientes=15, n_dias=3, n_rutas=3, semilla=7, frac_ventana=0.5,
            ancho_ventana=(60, 150), utilizacion=0.8, horizonte=480):
    rng = random.Random(semilla)
    clientes = []
    for i in range(1, n_clientes + 1):
        dias_visita = rng.sample(range(n_dias), k=rng.choice([2, 3]))
        demanda = [rng.randint(5, 25) if t in dias_visita else 0 for t in range(n_dias)]
        ventana = None
        if rng.random() < frac_ventana:
            ancho = rng.randint(*ancho_ventana)
            inicio = rng.randint(60, horizonte - ancho - 60)
            ventana = [inicio, inicio + ancho]
        clientes.append({
            "id": i, "x": rng.randint(0, 100), "y": rng.randint(0, 100),
            "servicio": 10, "ventana": ventana, "demanda": demanda,
        })
    max_dem = max(sum(c["demanda"][t] for c in clientes) for t in range(n_dias))
    capacidad = int(max_dem / (n_rutas * utilizacion)) + 1
    return {
        "nombre": f"ejemplo_{n_clientes}c",
        "descripcion": "Instancia sintética de prueba (no es la instancia final).",
        "n_rutas": n_rutas, "n_dias": n_dias, "capacidad": capacidad,
        "deposito": {"x": 50, "y": 50, "apertura": 0, "cierre": horizonte},
        "clientes": clientes,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--clientes", type=int, default=15)
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--salida", default=None)
    a = p.parse_args()
    datos = generar(n_clientes=a.clientes, semilla=a.semilla)
    salida = Path(a.salida or f"instancias/{datos['nombre']}.json")
    salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Instancia guardada en {salida}")
