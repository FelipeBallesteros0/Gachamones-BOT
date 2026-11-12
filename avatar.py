"""El avatar de quien juega: nombre, género, piel, pelo y ropa.

Es de la persona, no de un gachamon. Este módulo es puro: sólo conoce el
catálogo y qué vale; guardarlo es cosa de `db.py` y dibujarlo, del cliente.
"""
from __future__ import annotations

from dataclasses import dataclass

import especies as esp
import simulacion as sim


@dataclass(frozen=True)
class Opcion:
    clave: str
    nombre: str


GENEROS = (Opcion(esp.MACHO, "Masculino"), Opcion(esp.HEMBRA, "Femenino"))
PIELES = (
    Opcion("clara", "Clara"), Opcion("media", "Media"),
    Opcion("tostada", "Tostada"), Opcion("oscura", "Oscura"),
)
PELOS = (
    Opcion("corto", "Corto"), Opcion("largo", "Largo"), Opcion("rizado", "Rizado"),
    Opcion("coleta", "Coleta"), Opcion("rapado", "Rapado"),
)
COLORES_DE_PELO = (
    Opcion("negro", "Negro"), Opcion("castano", "Castaño"), Opcion("rubio", "Rubio"),
    Opcion("rojo", "Pelirrojo"), Opcion("cano", "Cano"), Opcion("azul", "Azul"),
)
ROPAS = (
    Opcion("poleron", "Polerón"), Opcion("camisa", "Camisa"),
    Opcion("vestido", "Vestido"), Opcion("overol", "Overol"),
)


@dataclass(frozen=True)
class Avatar:
    nombre: str
    genero: str
    piel: str
    pelo: str
    color_de_pelo: str
    ropa: str


def opciones() -> dict[str, tuple[Opcion, ...]]:
    return {
        "generos": GENEROS,
        "pieles": PIELES,
        "pelos": PELOS,
        "colores_de_pelo": COLORES_DE_PELO,
        "ropas": ROPAS,
    }


def _exigir(valor: str, catalogo: tuple[Opcion, ...], campo: str) -> str:
    if valor not in {o.clave for o in catalogo}:
        raise ValueError(f"Ese {campo} no existe.")
    return valor


def crear(
    nombre: str, genero: str, piel: str, pelo: str, color_de_pelo: str, ropa: str,
) -> Avatar:
    """Un avatar válido, con el nombre normalizado; `ValueError` si algo no vale."""
    return Avatar(
        nombre=sim.normalizar_nombre(nombre),
        genero=_exigir(genero, GENEROS, "género"),
        piel=_exigir(piel, PIELES, "color de piel"),
        pelo=_exigir(pelo, PELOS, "peinado"),
        color_de_pelo=_exigir(color_de_pelo, COLORES_DE_PELO, "color de pelo"),
        ropa=_exigir(ropa, ROPAS, "tipo de ropa"),
    )
