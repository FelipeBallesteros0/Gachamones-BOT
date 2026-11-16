"""La frase de «salir con él», compartida por la Incubadora y el departamento.

Las dos rutas cambian de activo con `economia.cambiar_de_activo` y contestan lo
mismo; la frase vive aquí para que ni se copie ni se importen en círculo.

Ojo: este módulo es `web.salir`; no importa `discord` ni nada que lo importe.
"""
from __future__ import annotations

import economia

NO_ESTA = "Ese gachamon ya no está."


def dicho_de_salir(hecho: economia.ResultadoCambio) -> dict:
    if hecho.ok:
        return {"ok": True, "clave": None, "mensaje": f"Ahora sales con {hecho.criatura.nombre}."}
    if hecho.motivo == "ya_es_el_activo":
        # Lo que ya está como se pidió es un sí: un toque doble no enseña un error.
        return {
            "ok": True, "clave": None,
            "mensaje": f"{hecho.criatura.nombre} ya es tu gachamon activo.",
        }
    if hecho.motivo == "no_esta":
        return {"ok": False, "clave": "no_esta", "mensaje": NO_ESTA}
    # Un motivo que no conocemos es un fallo nuestro y no se disfraza.
    raise RuntimeError(f"sacar sin frase: {hecho.motivo!r}")
