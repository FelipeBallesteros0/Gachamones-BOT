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
# Los originales de la pieza (el doble de lo servido), con las mismas rutas que `RAIZ`.
FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
# Lo que el juego todavía no pinta pero el dibujante ya sube: sus provisionales viven aquí, fuera de lo que se sirve.
RAIZ_POR_VENIR = Path(__file__).parent / "arte_por_venir"
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


# Los muebles del juego que tendrán un segundo dibujo, y cómo se llama su estado.
ENCENDIDOS = {"lampara": "encendido", "calefactor": "encendido", "chimenea": "encendido", "fuente": "encendido"}


# La forma del balcón: una tira por fuera de la pared, que no es suelo, ni bulto, ni pared.
FUERA = "fuera"


@dataclass(frozen=True)
class Objeto:
    """Un objeto que el juego todavía no tiene: lo que el dibujante ya dibuja de él.

    `ancho`, `fondo` y `capa` miden como los de un `departamento.Mueble`; `estado` es el
    nombre de su segundo dibujo, si lo tiene."""
    clave: str
    nombre: str
    ancho: int = 1
    fondo: int = 1
    capa: str = departamento.BULTO
    estado: str | None = None


COLORES = ("azul", "roja", "verde", "amarilla", "negra", "blanca")

# Los 24 objetos, en el orden de su tabla: los once primeros, las seis sillas, las seis mesas y el balcón.
POR_VENIR: tuple[Objeto, ...] = (
    Objeto("consola_flappy", "Consola Flappy"),
    Objeto("consola_pong", "Consola Pong"),
    Objeto("mesa_gato", "Mesa de gato"),
    Objeto("atril", "Atril"),
    Objeto("tocadiscos", "Tocadiscos", estado="encendido"),
    Objeto("mayordomo", "Mayordomo robot"),
    Objeto("puerta_cristal", "Puerta de cristal", estado="atravesable"),
    Objeto("cableados", "Bloque de cableados"),
    Objeto("super_dado", "Súper Dado"),
    Objeto("mega_tv", "Mega TV", ancho=2, estado="encendido"),
    Objeto("lampara_dragon", "Lámpara Dragón", estado="encendido"),
    *(Objeto(f"silla_{c}", f"Silla {c}") for c in COLORES),
    *(Objeto(f"mesa_{c}", f"Mesa {c}") for c in COLORES),
    Objeto("balcon", "Balcón", ancho=4, fondo=1, capa=FUERA),
)


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


def tamano_de_mueble(mueble: departamento.Mueble | Objeto) -> tuple[int, int]:
    """Lo que mide, servido, el dibujo de un mueble (el mismo en todas sus orientaciones).

    El balcón (`FUERA`) mide como un bulto de su huella."""
    if mueble.capa == departamento.PARED:
        return mueble.ancho * CASILLA[0] // 2, mueble.ancho * CASILLA[1] // 2 + ALTURA
    lados = mueble.ancho + mueble.fondo
    extra = ALTURA if mueble.capa in (departamento.BULTO, FUERA) else 0
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
    """Todos los lugares de subida, en un orden fijo: primero las piezas del contrato (la
    familia `pieza` se sube al doble de lo que sirve, las demás a su medida) y detrás lo
    que el juego todavía no pinta."""
    lista = []
    for p in piezas():
        reduccion = REDUCCION if p.familia == "pieza" else 1
        lista.append(Lugar(p.ruta, p.ancho * reduccion, p.alto * reduccion, p.familia, reduccion, True))
    for clave, estado in ENCENDIDOS.items():
        ancho, alto = tamano_de_mueble(departamento.MUEBLES[clave])
        lista += [Lugar(f"pieza/muebles/{clave}-{estado}-{o}.png", ancho * REDUCCION, alto * REDUCCION,
                        "pieza", REDUCCION, False, objeto=clave, estado=estado)
                  for o in ORIENTACIONES]
    for objeto in POR_VENIR:
        ancho, alto = tamano_de_mueble(objeto)
        orientaciones = ORIENTACIONES[:2] if objeto.capa == FUERA else ORIENTACIONES
        rutas = [(f"pieza/muebles/{objeto.clave}-{o}.png", None) for o in orientaciones]
        if objeto.estado:
            rutas += [(f"pieza/muebles/{objeto.clave}-{objeto.estado}-{o}.png", objeto.estado)
                      for o in orientaciones]
        lista += [Lugar(ruta, ancho * REDUCCION, alto * REDUCCION, "pieza", REDUCCION, False,
                        objeto=objeto.clave, estado=estado) for ruta, estado in rutas]
    lista += [Lugar(f"iconos/muebles/{o.clave}.png", *ICONO, "iconos", 1, False) for o in POR_VENIR]
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


def _nombre_de_objeto(clave: str) -> str | None:
    if clave in departamento.MUEBLES:
        return departamento.MUEBLES[clave].nombre
    return next((o.nombre for o in POR_VENIR if o.clave == clave), None)


def _grupo_de(ruta: str, objeto: str | None = None) -> tuple[str, str]:
    """La clave y el nombre del grupo de una pieza, según su ruta y, si lo tiene, su objeto.

    El de un mueble sale de su `objeto` y no de partir el nombre del archivo: el estado
    (`encendido`, `atravesable`) y las claves con guion bajo lo harían frágil."""
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
        clave = objeto or partes[2].rsplit("-", 1)[0]
        nombre = _nombre_de_objeto(clave)
        if nombre is not None:
            return f"pieza/muebles/{clave}", nombre
    raise ValueError(f"la pieza {ruta} no cae en ningún grupo del arte")


def grupos() -> tuple[Grupo, ...]:
    """Los lugares repartidos en grupos, en el orden de `lugares()`.

    Se calculan desde `lugares()`: uno que ningún grupo reconoce lanza `ValueError`.
    """
    por_clave: dict[str, tuple[str, str, list[str]]] = {}
    for lugar in lugares():
        clave, nombre = _grupo_de(lugar.ruta, lugar.objeto)
        _, _, rutas = por_clave.setdefault(clave, (nombre, lugar.familia, []))
        rutas.append(lugar.ruta)
    return tuple(Grupo(clave, nombre, familia, tuple(rutas))
                 for clave, (nombre, familia, rutas) in por_clave.items())


def como_json() -> dict:
    return {"piezas": [{"ruta": p.ruta, "ancho": p.ancho, "alto": p.alto, "familia": p.familia}
                       for p in piezas()]}
