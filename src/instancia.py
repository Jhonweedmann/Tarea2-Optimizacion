"""Lectura de instancias del ConVRP (ruteo consistente multi-día).

Formato JSON esperado (ver instancias/ejemplo_15c.json):

{
  "nombre": "ejemplo_15c",
  "n_rutas": 3,
  "n_dias": 3,
  "capacidad": 100,
  "deposito": {"x": 50, "y": 50, "apertura": 0, "cierre": 480},
  "clientes": [
    {"id": 1, "x": 12, "y": 80, "servicio": 10,
     "ventana": [60, 180],          # o null si el cliente no tiene ventana
     "demanda": [15, 0, 20]}        # una demanda por día (0 = no se visita ese día)
  ]
}

Convenciones:
- El nodo 0 es el depósito; los clientes se numeran 1..n.
- Distancia euclidiana redondeada a 2 decimales; tiempo de viaje = distancia
  (convención de las instancias de Solomon, velocidad 1).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Instancia:
    nombre: str
    n_rutas: int
    n_dias: int
    Q: float                      # capacidad del vehículo
    E: float                      # apertura del depósito
    L: float                      # cierre del depósito
    coords: dict[int, tuple[float, float]]
    servicio: dict[int, float]    # s_i (depósito = 0)
    ventana: dict[int, tuple[float, float] | None]
    demanda: dict[tuple[int, int], float]   # (i, t) -> q_it
    dist: dict[tuple[int, int], float] = field(default_factory=dict)

    # ---- conjuntos -------------------------------------------------------
    @property
    def clientes(self) -> list[int]:
        return sorted(i for i in self.coords if i != 0)

    @property
    def rutas(self) -> range:
        return range(self.n_rutas)

    @property
    def dias(self) -> range:
        return range(self.n_dias)

    def N(self, t: int) -> list[int]:
        """Clientes con demanda positiva el día t."""
        return [i for i in self.clientes if self.demanda.get((i, t), 0) > 0]

    def V(self, t: int) -> list[int]:
        """Nodos del día t: depósito + clientes con demanda."""
        return [0] + self.N(t)

    def arcos(self, t: int) -> list[tuple[int, int]]:
        Vt = self.V(t)
        return [(i, j) for i in Vt for j in Vt if i != j]

    def tiempo(self, i: int, j: int) -> float:
        return self.dist[i, j]

    def tiene_ventana(self, i: int) -> bool:
        return self.ventana.get(i) is not None

    def resumen(self) -> str:
        dem = [sum(self.demanda.get((i, t), 0) for i in self.clientes) for t in self.dias]
        n_vent = sum(self.tiene_ventana(i) for i in self.clientes)
        lineas = [
            f"Instancia {self.nombre}: {len(self.clientes)} clientes, "
            f"{self.n_dias} días, {self.n_rutas} rutas, Q={self.Q}",
            f"  Depósito abierto [{self.E}, {self.L}]; clientes con ventana: {n_vent}",
        ]
        for t in self.dias:
            lineas.append(
                f"  Día {t}: {len(self.N(t))} clientes, demanda {dem[t]:.0f} "
                f"(utilización {dem[t] / (self.n_rutas * self.Q):.0%} de la flota)"
            )
        return "\n".join(lineas)


def cargar_instancia(ruta: str | Path) -> Instancia:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    dep = datos["deposito"]
    n_dias = int(datos["n_dias"])

    coords = {0: (float(dep["x"]), float(dep["y"]))}
    servicio = {0: 0.0}
    ventana: dict[int, tuple[float, float] | None] = {0: None}
    demanda: dict[tuple[int, int], float] = {}

    for c in datos["clientes"]:
        i = int(c["id"])
        if i == 0:
            raise ValueError("El id 0 está reservado para el depósito")
        coords[i] = (float(c["x"]), float(c["y"]))
        servicio[i] = float(c.get("servicio", 0))
        v = c.get("ventana")
        ventana[i] = (float(v[0]), float(v[1])) if v else None
        dem = c["demanda"]
        if len(dem) != n_dias:
            raise ValueError(f"Cliente {i}: se esperaban {n_dias} demandas, hay {len(dem)}")
        for t, q in enumerate(dem):
            if q > 0:
                demanda[i, t] = float(q)
        if not any(q > 0 for q in dem):
            raise ValueError(f"Cliente {i} no tiene demanda en ningún día")

    inst = Instancia(
        nombre=datos.get("nombre", Path(ruta).stem),
        n_rutas=int(datos["n_rutas"]),
        n_dias=n_dias,
        Q=float(datos["capacidad"]),
        E=float(dep.get("apertura", 0)),
        L=float(dep["cierre"]),
        coords=coords,
        servicio=servicio,
        ventana=ventana,
        demanda=demanda,
    )
    for i, (xi, yi) in coords.items():
        for j, (xj, yj) in coords.items():
            if i != j:
                inst.dist[i, j] = round(math.hypot(xi - xj, yi - yj), 2)
    return inst
