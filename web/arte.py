"""El contrato de arte: qué archivos hay bajo `web/static/arte/`, cómo se llaman y cuánto miden.

Es el acuerdo entre el juego y quien dibuja: reemplazar un dibujo es guardar el
archivo nuevo con el mismo nombre y el mismo tamaño. Las piezas salen de los
catálogos (`pueblo`, `avatar`), así que añadir un lugar o un peinado añade su
pieza sola. Sin `discord` ni `db`.
"""

from dataclasses import dataclass
from functools import cache
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


@dataclass(frozen=True)
class Lugar:
    """Un sitio donde el dibujante sube un dibujo.

    `ancho` y `alto` son la medida de subida; `reduccion` es cuántas veces más chico es
    lo que sirve el juego (1: lo mismo). `en_el_juego` dice si es una pieza del contrato
    (`piezas()`) o algo que el juego todavía no pinta. `objeto` es la clave del mueble
    en `pieza/muebles/*` y en `iconos/muebles/*`.
    """
    ruta: str
    ancho: int
    alto: int
    familia: str
    reduccion: int
    en_el_juego: bool
    objeto: str | None = None
    estado: str | None = None
    criatura: "Capa | None" = None  # noqa: F821  (`Capa` nace en otra tarea)


def _con_escena(clave: str) -> bool:
    """Si la pantalla de ese lugar es la del lugar, la que pinta su escena: donde se
    ofrece el departamento se ve la pieza, y la escena no la pintaría nadie."""
    return "departamento" not in pueblo.ofrece(clave)


def piezas() -> tuple[Pieza, ...]:
    """Todas las piezas del contrato, en un orden fijo."""
    lista = [Pieza("pueblo/fondo.png", 2 * pueblo.DATOS["ancho"], 2 * pueblo.DATOS["alto"], "pueblo")]
    lista += [Pieza(f"pueblo/lugares/{l}.png", LADO_LUGAR, LADO_LUGAR, "lugares") for l in pueblo.LUGARES]
    lista += [Pieza(f"escenas/{l}.png", *ESCENA, "escenas") for l in pueblo.LUGARES if _con_escena(l)]
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


@cache
def lugares() -> tuple[Lugar, ...]:
    """Todos los lugares de subida, en un orden fijo. Hoy, las piezas del contrato: la
    familia `pieza` se sube al doble de lo que sirve, las demás a su medida."""
    lista = []
    for p in piezas():
        reduccion = REDUCCION if p.familia == "pieza" else 1
        lista.append(Lugar(p.ruta, p.ancho * reduccion, p.alto * reduccion, p.familia, reduccion, True))
    return tuple(lista)


@cache
def _indice() -> dict[str, Lugar]:
    return {lugar.ruta: lugar for lugar in lugares()}


def lugar_de(ruta: str) -> Lugar | None:
    """El lugar con esa ruta, tal cual; `None` si no lo hay.

    Sólo se busca, no se arma nada con la ruta: una con `..`, con `\\` o con una barra
    delante no es de ningún lugar.
    """
    return _indice().get(ruta)


def olvidar() -> None:
    """Vacía lo calculado, para las pruebas que cambian los catálogos."""
    lugares.cache_clear()
    _indice.cache_clear()


@dataclass(frozen=True)
class Grupo:
    """Un puñado de piezas que se dibujan juntas: la tarjeta de un tablero.

    `clave` sale de las rutas (sin extensión), nunca del nombre; `nombre` es para
    quien dibuja y para el dueño.
    """
    clave: str
    nombre: str
    familia: str
    rutas: tuple[str, ...]


_ICONOS = {"muebles": "Iconos de los muebles", "objetos": "Iconos de los objetos",
           "cosmeticos": "Iconos de los cosméticos"}


def _grupo_de(ruta: str) -> tuple[str, str]:
    """La clave y el nombre del grupo de una pieza, según su ruta."""
    partes = ruta.removesuffix(".png").split("/")
    if ruta == "pueblo/fondo.png":
        return "pueblo/fondo", "Fondo del pueblo"
    if partes[:2] == ["pueblo", "lugares"]:
        return "pueblo/lugares", "Lugares del pueblo"
    if partes[0] == "escenas":
        return "escenas", "Escenas de los lugares"
    if partes[0] == "efectos":
        return "efectos", "Efectos"
    if partes[:2] == ["avatar", "cuerpo"]:
        return "avatar/cuerpo", "Cuerpos"
    if partes[:2] == ["avatar", "ropa"]:
        return "avatar/ropa", "Ropa"
    if partes[:2] == ["avatar", "pelo"]:
        for pelo in avatar.PELOS:
            if partes[2].startswith(f"{pelo.clave}-"):
                return f"avatar/pelo/{pelo.clave}", f"Peinado {pelo.nombre.lower()}"
    if partes[0] == "iconos" and partes[1] in _ICONOS:
        return f"iconos/{partes[1]}", _ICONOS[partes[1]]
    if ruta in ("pieza/suelo.png", "pieza/pared-izquierda.png", "pieza/pared-derecha.png"):
        return "pieza/paredes-y-suelo", "Paredes y suelo"
    if partes[:2] == ["pieza", "muebles"]:
        clave = partes[2].rsplit("-", 1)[0]
        if clave in departamento.MUEBLES:
            return f"pieza/muebles/{clave}", departamento.MUEBLES[clave].nombre
    raise ValueError(f"la pieza {ruta} no cae en ningún grupo del arte")


def grupos() -> tuple[Grupo, ...]:
    """Los lugares repartidos en grupos, en el orden de `lugares()`.

    Se calculan desde `lugares()`: uno que ningún grupo reconoce lanza `ValueError`.
    """
    por_clave: dict[str, tuple[str, str, list[str]]] = {}
    for lugar in lugares():
        clave, nombre = _grupo_de(lugar.ruta)
        _, _, rutas = por_clave.setdefault(clave, (nombre, lugar.familia, []))
        rutas.append(lugar.ruta)
    return tuple(Grupo(clave, nombre, familia, tuple(rutas))
                 for clave, (nombre, familia, rutas) in por_clave.items())


def como_json() -> dict:
    return {"piezas": [{"ruta": p.ruta, "ancho": p.ancho, "alto": p.alto, "familia": p.familia}
                       for p in piezas()]}
