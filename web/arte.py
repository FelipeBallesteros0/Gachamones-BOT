"""El contrato de arte: qué archivos hay bajo `web/static/arte/`, cómo se llaman y cuánto miden.

Es el acuerdo entre el juego y quien dibuja: reemplazar un dibujo es guardar el
archivo nuevo con el mismo nombre y el mismo tamaño. Las piezas salen de los
catálogos (`pueblo`, `avatar`), así que añadir un lugar o un peinado añade su
pieza sola. Sin `discord` ni `db`.
"""

from dataclasses import dataclass
from pathlib import Path

import avatar
import casas
import cosmeticos
import objetos
from web import pueblo

RAIZ = Path(__file__).parent / "static" / "arte"
POSES = ("quieto", "paso1", "paso2")

LADO_LUGAR = 160
ESCENA = (720, 480)
AVATAR = (48, 84)
EFECTO = (32, 32)
EFECTOS = ("corazon", "estrella", "marca", "sombra")
ICONO = (48, 48)


@dataclass(frozen=True)
class Pieza:
    ruta: str
    ancho: int
    alto: int
    familia: str


def piezas() -> tuple[Pieza, ...]:
    """Todas las piezas del contrato, en un orden fijo."""
    lista = [Pieza("pueblo/fondo.png", 2 * pueblo.DATOS["ancho"], 2 * pueblo.DATOS["alto"], "pueblo")]
    lista += [Pieza(f"pueblo/lugares/{l}.png", LADO_LUGAR, LADO_LUGAR, "lugares") for l in pueblo.LUGARES]
    lista += [Pieza(f"escenas/{l}.png", *ESCENA, "escenas") for l in pueblo.LUGARES]
    for pose in POSES:
        lista += [Pieza(f"avatar/cuerpo/{p.clave}-{pose}.png", *AVATAR, "avatar") for p in avatar.PIELES]
    for pose in POSES:
        lista += [Pieza(f"avatar/ropa/{r.clave}-{pose}.png", *AVATAR, "avatar") for r in avatar.ROPAS]
    for pelo in avatar.PELOS:
        for color in avatar.COLORES_DE_PELO:
            lista += [Pieza(f"avatar/pelo/{pelo.clave}-{color.clave}-{pose}.png", *AVATAR, "avatar")
                      for pose in POSES]
    lista += [Pieza(f"efectos/{e}.png", *EFECTO, "efectos") for e in EFECTOS]
    for grupo, catalogo in (("objetos", objetos.CATALOGO), ("cosmeticos", cosmeticos.CATALOGO),
                            ("muebles", casas.MUEBLES), ("casas", casas.CATALOGO)):
        lista += [Pieza(f"iconos/{grupo}/{clave}.png", *ICONO, "iconos") for clave in catalogo]
    return tuple(lista)


def como_json() -> dict:
    return {"piezas": [{"ruta": p.ruta, "ancho": p.ancho, "alto": p.alto, "familia": p.familia}
                       for p in piezas()]}
