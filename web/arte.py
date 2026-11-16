"""El contrato de arte: qué archivos hay bajo `web/static/arte/`, cómo se llaman y cuánto miden.

Es el acuerdo entre el juego y quien dibuja: reemplazar un dibujo es guardar el
archivo nuevo con el mismo nombre y el mismo tamaño. Las piezas salen de los
catálogos (`pueblo`, `avatar`), así que añadir un lugar o un peinado añade su
pieza sola. Sin `discord` ni `db`.
"""

from dataclasses import dataclass
from pathlib import Path

import avatar
import cosmeticos
import departamento
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

# La pieza del departamento. Todo lo que sirve la página es la mitad del original.
CASILLA = (512, 256)  # el rombo de una casilla de suelo, servido
ALTURA = 512          # lo que sobresale un mueble o lo que mide la pared, servido
REDUCCION = 2
ORIENTACIONES = ("se", "so", "no", "ne")  # por giro 0, 1, 2 y 3: cada giro es un cuarto de vuelta


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
    # La puerta no se vende ni se guarda: no lleva ícono.
    for grupo, claves in (("objetos", objetos.CATALOGO), ("cosmeticos", cosmeticos.CATALOGO),
                          ("muebles", [m.clave for m in departamento.a_la_venta()])):
        lista += [Pieza(f"iconos/{grupo}/{clave}.png", *ICONO, "iconos") for clave in claves]
    lista += _piezas_de_la_pieza()
    return tuple(lista)


def tamano_de_mueble(mueble: departamento.Mueble) -> tuple[int, int]:
    """Lo que mide, servido, el dibujo de un mueble (el mismo en todas sus orientaciones)."""
    if mueble.capa == departamento.PARED:
        return mueble.ancho * CASILLA[0] // 2, mueble.ancho * CASILLA[1] // 2 + ALTURA
    lados = mueble.ancho + mueble.fondo
    extra = ALTURA if mueble.capa == departamento.BULTO else 0
    return lados * CASILLA[0] // 2, lados * CASILLA[1] // 2 + extra


def _piezas_de_la_pieza() -> list[Pieza]:
    lista = [Pieza("pieza/suelo.png", *CASILLA, "pieza")]
    lista += [Pieza(f"pieza/pared-{lado}.png", CASILLA[0] // 2, CASILLA[1] // 2 + ALTURA, "pieza")
              for lado in ("izquierda", "derecha")]
    for mueble in departamento.MUEBLES.values():
        orientaciones = ORIENTACIONES[:2] if mueble.capa == departamento.PARED else ORIENTACIONES
        lista += [Pieza(f"pieza/muebles/{mueble.clave}-{o}.png", *tamano_de_mueble(mueble), "pieza")
                  for o in orientaciones]
    return lista


def originales_de_la_pieza() -> tuple[Pieza, ...]:
    """Las mismas piezas de la pieza, a tamaño de original (el doble), tal como van bajo `fuentes/`."""
    return tuple(Pieza(p.ruta, p.ancho * REDUCCION, p.alto * REDUCCION, "pieza")
                 for p in piezas() if p.familia == "pieza")


def como_json() -> dict:
    return {"piezas": [{"ruta": p.ruta, "ancho": p.ancho, "alto": p.alto, "familia": p.familia}
                       for p in piezas()]}
