"""Lo que sube el dibujante para reemplazar un recuadro provisional del arte.

Las reglas de una subida: qué PNG vale para qué pieza del contrato
(`web/arte.py`), cómo sale limpio y cómo se llama, y cómo se escribe y se poda en
la carpeta de lo subido. El historial y qué se conserva lo lleva `db`; `subir` y
`volver` juntan las dos cosas en su orden, y son lo único que tiene que llamar
quien recibe una subida o una vuelta atrás. Fuera de la base y de la carpeta que
se le pasa, no toca nada.
"""

import hashlib
import io
import logging
import os
import re
import struct
import tempfile
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageMath

import db
from web import arte

logger = logging.getLogger(__name__)

LIMITE_DE_BYTES = 24 * 1024 * 1024
# Lo que se le dice a quien sube algo de más de `LIMITE_DE_BYTES`: aquí, y en el 413 de
# la api del dibujante, que corta el cuerpo antes de que llegue entero.
PESA_DEMASIADO = "La imagen pesa más de 24 MB."
# Lo que puede tardar una subida entre escribir su archivo y anotarlo. Un archivo
# sin renglón más viejo que esto quedó huérfano, y la poda se lo lleva.
VIDA_DE_UN_HUERFANO = timedelta(hours=1)

_NOMBRE = re.compile(r"[0-9a-f]{64}\.png")
_TEMPORAL = re.compile(r"\.subiendo-[a-z0-9_]+\.tmp")
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
_CIERRE_PNG = b"\x00\x00\x00\x00IEND\xaeB`\x82"  # el trozo IEND, que es siempre el mismo
_GRIS, _RGB = 0, 2  # tipos de color de la cabecera de un PNG


class NoVale(ValueError):
    """Lo pedido no vale para esa pieza: una imagen que no sirve, o volver a una anterior
    que no hay. `mensaje` dice por qué, para quien lo pidió."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


def medidas() -> dict[str, tuple[int, int]]:
    """Lo que mide hoy cada pieza del contrato, servida: lo que pide `db.arte_vigente`."""
    return {p.ruta: (p.ancho, p.alto) for p in arte.piezas()}


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


def a_lo_servido(original: Image.Image, reduccion: int = arte.REDUCCION) -> Image.Image:
    """Un original (el doble, de `fuentes/pieza/` o de lo que sube el dibujante), reducido a
    lo que sirve la página.

    A la mitad y con `LANCZOS`: es la reducción de `herramientas/pieza.py`.
    """
    return original.resize((original.width // reduccion, original.height // reduccion),
                           Image.LANCZOS)


def _medida(ancho: int, alto: int) -> str:
    return f"{ancho} × {alto} px"


@dataclass(frozen=True)
class Imagen:
    """Un PNG ya limpio, con su nombre (`<sha256 de los bytes>.png`) y su medida."""
    datos: bytes
    nombre: str
    ancho: int
    alto: int


def _como_imagen(imagen: Image.Image) -> Imagen:
    salida = io.BytesIO()
    imagen.save(salida, "PNG", optimize=True)
    datos = salida.getvalue()
    return Imagen(datos, hashlib.sha256(datos).hexdigest() + ".png", imagen.width, imagen.height)


def preparar(cuerpo: bytes, lugar: arte.Lugar) -> tuple[Imagen, Imagen]:
    """El original limpio y la versión chica que sirve el juego, para ese lugar.

    Sólo vale un PNG de hasta `LIMITE_DE_BYTES`, entero y de la medida de subida del
    lugar. Se abre de verdad, se pasa a RGBA y se vuelve a escribir sin nada más que los
    píxeles: ni textos, ni perfil de color, ni exif. La chica es ese original reducido
    (`a_lo_servido`); si el lugar no se reduce (`reduccion == 1`), es el mismo objeto.
    Lo que no vale lanza `NoVale`, sin haber escrito nada.
    """
    if len(cuerpo) > LIMITE_DE_BYTES:
        raise NoVale(PESA_DEMASIADO)
    ancho, alto, profundidad, tipo = _cabecera(cuerpo)
    # Un PNG acaba en su cierre. Lo que no, llegó cortado (o trae algo pegado detrás).
    if not cuerpo.endswith(_CIERRE_PNG):
        raise NoVale("El PNG está dañado o incompleto.")
    if (ancho, alto) != (lugar.ancho, lugar.alto):
        raise NoVale(f"La imagen mide {_medida(ancho, alto)} y esta pieza pide "
                     f"{_medida(lugar.ancho, lugar.alto)}.")
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
    # Una imagen nueva, sin el `info` de la original: lo que no son píxeles no pasa.
    limpia = Image.frombytes("RGBA", rgba.size, rgba.tobytes())
    original = _como_imagen(limpia)
    if lugar.reduccion == 1:
        return original, original
    return original, _como_imagen(a_lo_servido(limpia, lugar.reduccion))


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
    descriptor, temporal = tempfile.mkstemp(dir=carpeta, prefix=".subiendo-", suffix=".tmp")
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


def _mas_viejo_que(entrada: Path, limite: float) -> bool:
    try:
        return entrada.lstat().st_mtime < limite
    except FileNotFoundError:
        return False


def podar(carpeta: Path, conservar: Collection[str], conocidos: Collection[str],
          ahora: datetime) -> list[str]:
    """Borra de `carpeta` lo que ya no hace falta y devuelve lo borrado.

    Se llama con la base tomada para escribir (`db.podar_arte` le pasa `conservar` y
    `conocidos`), para que ninguna subida se anote mientras tanto. Borra:

    - los archivos subidos que nombra el historial (`conocidos`) y no se conservan;
    - los huérfanos de más de `VIDA_DE_UN_HUERFANO`: archivos subidos que el historial
      no nombra (su subida no llegó a anotarse) y temporales que quedaron a medias.
      Uno más reciente puede ser una subida en camino, y no se toca.

    Sólo mira lo que está directamente en la carpeta, y nunca nada que no tenga
    nombre de archivo subido o de temporal. Lo que no se puede borrar se avisa en el
    registro y se deja: la subida que poda ya está hecha, y no falla por esto.
    """
    if not carpeta.is_dir():
        return []
    limite = (ahora - VIDA_DE_UN_HUERFANO).timestamp()
    borrados = []
    for entrada in sorted(carpeta.iterdir()):
        nombre = entrada.name
        if _NOMBRE.fullmatch(nombre):
            sobra = nombre not in conservar and (nombre in conocidos or _mas_viejo_que(entrada, limite))
        else:
            sobra = bool(_TEMPORAL.fullmatch(nombre)) and _mas_viejo_que(entrada, limite)
        if not sobra:
            continue
        try:
            entrada.unlink()
        except FileNotFoundError:
            continue
        except OSError as fallo:
            logger.warning("No se pudo podar %s: %s", entrada, fallo)
            continue
        borrados.append(nombre)
    return borrados


def subir(carpeta: Path, lugar: arte.Lugar, cuerpo: bytes, quien: str, ahora: datetime) -> str:
    """Una subida entera, en su orden, y el nombre de lo que quedó vigente (la chica).

    1. `preparar`: lo que no vale lanza `NoVale` sin haber tocado nada.
    2. `guardar`: los dos archivos, enteros, antes de anotarlos.
    3. El renglón, con el original: desde aquí es la vigente y ninguna poda la toca.
    4. `guardar` otra vez: una poda de otra subida que se cruzó entre los pasos 2 y 3
       pudo llevarse alguno (era una imagen vieja que nadie conservaba), y aquí se repone.
       Si siguen ahí, no hace nada.
    5. La poda, con la base tomada.
    """
    original, chica = preparar(cuerpo, lugar)
    imagenes = (original, chica) if chica is not original else (original,)
    for imagen in imagenes:
        guardar(carpeta, imagen.nombre, imagen.datos)
    db.subir_arte(lugar.ruta, chica.nombre, chica.ancho, chica.alto, quien, ahora,
                  original=original.nombre, ancho_original=original.ancho,
                  alto_original=original.alto)
    for imagen in imagenes:
        guardar(carpeta, imagen.nombre, imagen.datos)
    db.podar_arte(lambda conservar, conocidos: podar(carpeta, conservar, conocidos, ahora))
    return chica.nombre


def volver(carpeta: Path, lugar: arte.Lugar, a: str, quien: str, ahora: datetime) -> str | None:
    """Vuelve atrás `a` "anterior" o `a` "provisional"; devuelve lo que quedó vigente.

    «anterior» retrocede una subida (`db.volver_a_la_anterior`), saltando las imágenes
    que ya no están en la carpeta; desde el provisional vuelve a la última subida, y
    si no queda ninguna, lanza `NoVale`. Volver no cambia lo que se conserva, así que
    no poda.
    """
    if a == "provisional":
        db.volver_al_provisional(lugar.ruta, quien, ahora)
        return None
    if a != "anterior":
        raise ValueError(f"no se vuelve a {a!r}")
    try:
        return db.volver_a_la_anterior(lugar.ruta, quien, ahora, lambda archivo: (carpeta / archivo).is_file())
    except db.NoHayAnterior:
        raise NoVale("No hay una imagen anterior.") from None
