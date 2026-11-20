"""Lo que sube el dibujante para reemplazar un recuadro provisional del arte.

Las reglas de una subida: qué PNG vale para qué pieza del contrato
(`web/arte.py`), cómo sale limpio y cómo se llama, y cómo se escribe y se poda en
la carpeta de lo subido. No sabe de la base: el historial y qué se conserva lo
lleva `db`, y quien recibe la subida junta las dos cosas. Fuera de escribir y
borrar en la carpeta que se le pasa, no toca nada.
"""

import hashlib
import io
import os
import re
import struct
import tempfile
from collections.abc import Collection, Iterable
from pathlib import Path

from PIL import Image, ImageMath

from web import arte

LIMITE_DE_BYTES = 4 * 1024 * 1024

_NOMBRE = re.compile(r"[0-9a-f]{64}\.png")
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
_CIERRE_PNG = b"\x00\x00\x00\x00IEND\xaeB`\x82"  # el trozo IEND, que es siempre el mismo
_GRIS, _RGB = 0, 2  # tipos de color de la cabecera de un PNG


class NoVale(ValueError):
    """Lo subido no sirve para esa pieza. `mensaje` dice por qué, para quien lo subió."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


def pieza_de(ruta: str) -> arte.Pieza | None:
    """La pieza del contrato con esa ruta, tal cual; `None` si no la hay.

    Sólo se busca, no se arma nada con la ruta: una con `..`, con `\\` o con una
    barra delante no es de ninguna pieza (`tests/test_arte.py` fija la forma de las
    del contrato).
    """
    return next((p for p in arte.piezas() if p.ruta == ruta), None)


def medidas() -> dict[str, tuple[int, int]]:
    """Lo que mide hoy cada pieza del contrato, servida: lo que pide `db.arte_vigente`."""
    return {p.ruta: (p.ancho, p.alto) for p in arte.piezas()}


def _aceptadas(pieza: arte.Pieza) -> tuple[tuple[int, int], ...]:
    """Las medidas que valen: la exacta y, en la familia `pieza`, también la del original (el doble)."""
    exacta = (pieza.ancho, pieza.alto)
    if pieza.familia != "pieza":
        return (exacta,)
    return exacta, (pieza.ancho * arte.REDUCCION, pieza.alto * arte.REDUCCION)


def _cabecera(cuerpo: bytes) -> tuple[int, int, int, int]:
    """Ancho, alto, bits por muestra y tipo de color, leídos de la cabecera sin abrir la imagen.

    Leerlos antes es lo que impide que una bomba de descompresión (una cabecera que
    promete millones de píxeles) llegue a abrirse: sólo se abre lo que ya mide lo
    que pide su pieza.
    """
    if len(cuerpo) < 33 or not cuerpo.startswith(_FIRMA_PNG) or cuerpo[12:16] != b"IHDR":
        raise NoVale("El archivo no es un PNG.")
    return struct.unpack(">IIBB", cuerpo[16:26])


def _a_rgba(imagen: Image.Image, profundidad: int, tipo: int) -> Image.Image:
    """La imagen en RGBA de 8 bits, con su transparencia.

    Pillow lo hace bien salvo con los grises de 16 bits (los satura en vez de
    escalarlos), con el gris transparente de los grises de 2 y 4 bits (no lo escala
    como a los píxeles) y con el color transparente del RGB de 16 bits (lo compara
    con los píxeles ya reducidos a 8). Los grises se pasan aquí a mano; ese color,
    a 8 bits como los píxeles.
    """
    transparente = imagen.info.get("transparency")
    if tipo == _GRIS:
        valores = imagen.convert("I")
        gris = (valores.point(lambda v: v / 256) if profundidad == 16 else valores).convert("L")
        if transparente is None:
            alfa = Image.new("L", imagen.size, 255)
        else:
            if profundidad in (2, 4):  # el de 1 bit ya lo escala Pillow
                transparente = transparente * 255 // ((1 << profundidad) - 1)
            alfa = ImageMath.lambda_eval(
                lambda m: m["convert"](m["notequal"](m["v"], transparente) * 255, "L"), v=valores)
        return Image.merge("RGBA", (gris, gris, gris, alfa))
    if tipo == _RGB and profundidad == 16 and transparente is not None:
        imagen.info["transparency"] = tuple(c >> 8 for c in transparente)
    return imagen.convert("RGBA")


def a_lo_servido(original: Image.Image) -> Image.Image:
    """Un original de la familia `pieza` (el doble), reducido a lo que sirve la página.

    A la mitad y con `LANCZOS`: es la reducción de `herramientas/pieza.py`, que la usa
    para los originales de `fuentes/`.
    """
    return original.resize((original.width // arte.REDUCCION, original.height // arte.REDUCCION),
                           Image.LANCZOS)


def _medida(ancho: int, alto: int) -> str:
    return f"{ancho} × {alto} px"


def preparar(cuerpo: bytes, pieza: arte.Pieza) -> tuple[bytes, str]:
    """El PNG limpio para esa pieza y su nombre (`<sha256 de los bytes limpios>.png`).

    Sólo vale un PNG de hasta `LIMITE_DE_BYTES`, entero y de la medida de la pieza
    (o el doble, en la familia `pieza`, que se reduce). Se abre de verdad, se pasa a
    RGBA y se vuelve a escribir sin nada más que los píxeles: ni textos, ni perfil de
    color, ni exif. Sale siempre a la medida de la pieza. Lo que no vale lanza
    `NoVale`, sin haber escrito nada.
    """
    if len(cuerpo) > LIMITE_DE_BYTES:
        raise NoVale("La imagen pesa más de 4 MB.")
    ancho, alto, profundidad, tipo = _cabecera(cuerpo)
    # Un PNG acaba en su cierre. Lo que no, llegó cortado (o trae algo pegado detrás).
    if not cuerpo.endswith(_CIERRE_PNG):
        raise NoVale("El PNG está dañado o incompleto.")
    aceptadas = _aceptadas(pieza)
    if (ancho, alto) not in aceptadas:
        pedidas = " o ".join(_medida(*m) for m in aceptadas)
        raise NoVale(f"La imagen mide {_medida(ancho, alto)} y esta pieza pide {pedidas}.")
    # Lo que puede fallar al decodificar un archivo dañado no es una lista cerrada
    # (Pillow lanza OSError, SyntaxError, ValueError, EOFError, struct.error…): todo
    # fallo aquí dentro es que el PNG no se puede leer.
    try:
        with Image.open(io.BytesIO(cuerpo), formats=["PNG"]) as imagen:
            imagen.verify()
        with Image.open(io.BytesIO(cuerpo), formats=["PNG"]) as imagen:
            if imagen.format != "PNG" or imagen.size != (ancho, alto):
                raise NoVale("El archivo no es un PNG.")
            imagen.load()
            rgba = _a_rgba(imagen, profundidad, tipo)
    except NoVale:
        raise
    except Exception as fallo:
        raise NoVale("El PNG está dañado o incompleto.") from fallo
    if rgba.size != (pieza.ancho, pieza.alto):
        rgba = a_lo_servido(rgba)
    # Una imagen nueva, sin el `info` de la original: lo que no son píxeles no pasa.
    limpia = Image.frombytes("RGBA", rgba.size, rgba.tobytes())
    salida = io.BytesIO()
    limpia.save(salida, "PNG", optimize=True)
    datos = salida.getvalue()
    return datos, hashlib.sha256(datos).hexdigest() + ".png"


def guardar(carpeta: Path, nombre: str, datos: bytes) -> Path:
    """Escribe `datos` en `carpeta/nombre` y devuelve la ruta.

    `nombre` tiene que ser el de su contenido, como lo da `preparar`. Se escribe
    entero en un temporal de la misma carpeta, se fuerza al disco y se renombra:
    nadie ve nunca un archivo a medias con el nombre final. Si ya existe, no se
    reescribe (mismo nombre, mismo contenido). Crea la carpeta, pero no lo que
    hay encima.
    """
    if not _NOMBRE.fullmatch(nombre) or hashlib.sha256(datos).hexdigest() + ".png" != nombre:
        raise ValueError(f"{nombre!r} no es el nombre del contenido que se guarda")
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / nombre
    if destino.exists():
        return destino
    descriptor, temporal = tempfile.mkstemp(dir=carpeta, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as archivo:
            archivo.write(datos)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
    except BaseException:
        Path(temporal).unlink(missing_ok=True)
        raise
    # Que el nombre nuevo también llegue al disco, no sólo el contenido.
    directorio = os.open(carpeta, os.O_RDONLY)
    try:
        os.fsync(directorio)
    finally:
        os.close(directorio)
    return destino


def podar(carpeta: Path, candidatos: Iterable[str], conservar: Collection[str]) -> list[str]:
    """Borra de `carpeta` los `candidatos` que no están en `conservar`; devuelve los borrados.

    Los candidatos son los archivos del historial de la pieza que se acaba de tocar, y
    `conservar` lo que `db.archivos_que_se_conservan` dice que sigue haciendo falta: la
    vigente y las cinco últimas distintas de cada pieza. Un archivo que todavía no está
    en el historial (una subida a medio camino) no es candidato, así que no se toca.
    Nunca borra fuera de la carpeta ni nada que no tenga nombre de archivo subido.
    """
    borrados = []
    for nombre in sorted(set(candidatos) - set(conservar)):
        if not _NOMBRE.fullmatch(nombre):
            continue
        try:
            (carpeta / nombre).unlink()
        except FileNotFoundError:
            continue
        borrados.append(nombre)
    return borrados
