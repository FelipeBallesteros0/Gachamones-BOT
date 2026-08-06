"""El retrato dibujado: qué criaturas lo tienen y cómo se arma.

**Se compone al vuelo.** En el repositorio viven sólo las capas —un cuerpo por
especie y forma, tres caras y un cosmético por sombrero— y el retrato se apila
en el momento de enseñarlo. Antes se guardaban los 1155 ya compuestos, que eran
27 MB creciendo hacia los 180 a medida que se redibujaban las especies, y todo
eso se clonaba entero en cada despliegue.

Lo que hizo viable el cambio fue medirlo en la Raspberry: apilar tres capas de
256×256 cuesta **1,7 s en Python puro y 72 ms con Pillow**. Con lo primero el
bot se congelaba en cada pulsación; con lo segundo cabe de sobra en una
interacción de Discord. Por eso Pillow es dependencia de producción y no un
capricho.

Encima hay una caché en memoria: la ficha se reedita a cada botón casi siempre
con la misma combinación, así que a partir de la segunda vez no se compone nada.

El nombre del archivo es `{animo}_{sombrero}.png`, con las mismas claves que ya
usan `especies` y `cosmeticos`. No hay tabla de equivalencias que mantener: si
mañana se añade un sombrero, el archivo se llama como su clave y ya está.
"""
from __future__ import annotations

import functools
import io
import unicodedata
from pathlib import Path

from PIL import Image

import cosmeticos as cos
import especies as esp
import simulacion as sim

FUENTES = Path(__file__).parent / "fuentes"

# El borde del embed va del color de la especie, que es lo que ata el retrato a
# la ficha. Son los mismos ocho colores del arte ANSI traducidos a RGB; se
# devuelve el número y no un objeto de Discord para no arrastrar la librería a
# un módulo que no la necesita.
COLORES = {
    esp.GRIS: 0x8A8A8A, esp.ROJO: 0xC0392B, esp.VERDE: 0x4CAF50,
    esp.AMARILLO: 0xD9A400, esp.AZUL: 0x3F7FD0, esp.ROSA: 0xD268A8,
    esp.CIAN: 0x3FB6C4, esp.BLANCO: 0xD8D8D8,
}
COLOR_POR_DEFECTO = 0x8A8A8A

# Las especies que ya tienen dibujadas SUS CINCO FORMAS. Se declaran a mano y no
# mirando qué carpetas hay: es el cerrojo de que esto siga acotado, y una
# carpeta a medio llenar dejaría fichas pidiendo una imagen que no está.
CON_ETAPAS_COMPLETAS = (
    "brote",        # Magora
    "chispa",       # Pyro
    "michi",        # Purreon
    "pedrusco",     # Geo
    "pollito",      # Piollito
    "pulpo",        # Octopul
    "slime",        # Gelatín
    "fantasma",     # Duskhouse
    "chatarra",     # Re-bot
    "dragoncito",   # Tsushimon
    "swampdon",     # Swampdón
)
CON_RETRATO = frozenset(
    (clave, etapa) for clave in CON_ETAPAS_COMPLETAS for etapa in esp.ETAPAS
)

SIN_SOMBRERO = "sin"
CARAS = {esp.FELIZ: "face_1.png", esp.NORMAL: "face_2.png", esp.MAL: "face_3.png"}

# Las formas se llamaron así al dibujarlas y el juego las llama de otra manera.
# Renombrar los originales rompería la costumbre de quien dibuja, y esta es la
# única tabla que queda: la de especies se deduce sola.
FORMA_ARCHIVO: dict[str, str] = dict(zip(
    esp.ETAPAS, ("cria", "niño", "adolecente", "adulto", "adulto_grande")
))

# Un respiro alrededor del dibujo para que no quede pegado al borde del embed.
MARGEN = 2

# Cuántos retratos ya armados se recuerdan. Pesan unos 21 KB de media, así que
# ciento veintiocho son unos tres megas: nada al lado de lo que ahorran, porque
# pulsar un botón vuelve a pintar la misma combinación una y otra vez.
RECORDADOS = 128


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


@functools.cache
def _nombre_de_archivo(clave: str) -> str:
    """De la clave interna al nombre con que se dibujó: «brote» -> «magora».

    Los dibujos se nombran por el **nombre** del bicho, que es el que sale en la
    hoja de producción; pedir la clave sería pedir que quien dibuja se acuerde
    de que Tsushimon es `dragoncito`.
    """
    return _sin_tildes(esp.ESPECIES[clave].nombre)


def _ruta_del_cuerpo(clave: str, etapa: str) -> Path:
    nombre = _nombre_de_archivo(clave)
    return FUENTES / "cuerpos" / f"{nombre}_body_{FORMA_ARCHIVO[etapa]}.png"


def _ruta_de_capa(carpeta: str, clave: str, archivo: str, forma: str) -> Path:
    """La capa más concreta que exista, de las tres que puede haber.

    Por forma, por especie o global, en ese orden. Lo de **por forma** hace
    falta desde que los cuerpos de una misma especie dejaron de ser el mismo
    dibujo agrandado: si la cría es una bola y el adulto un pájaro con las alas
    abiertas, ni los ojos ni la coronilla caen donde antes.
    """
    nombre = _nombre_de_archivo(clave)
    por_forma = FUENTES / carpeta / nombre / forma / archivo
    if por_forma.is_file():
        return por_forma
    especifica = FUENTES / carpeta / nombre / archivo
    return especifica if especifica.is_file() else FUENTES / carpeta / archivo


def _abrir(ruta: Path) -> Image.Image:
    with Image.open(ruta) as imagen:
        return imagen.convert("RGBA")


@functools.cache
def _caja(clave: str, etapa: str) -> tuple[int, int, int, int]:
    """El encuadre que comparten las 21 combinaciones de esta forma.

    Comparten caja **a propósito**: si cada una se recortara a su propia
    silueta, cambiar de humor o ponerse un sombrero movería al bicho dentro del
    embed y parecería que da saltos.

    Se calcula uniendo la caja de cada capa suelta y no componiendo las 21, que
    es lo mismo y cuesta la décima parte: apilar no pone tinta donde no la
    había en ninguna capa.
    """
    forma = FORMA_ARCHIVO[etapa]
    capas = [_ruta_del_cuerpo(clave, etapa)]
    capas += [_ruta_de_capa("caras", clave, a, forma) for a in CARAS.values()]
    capas += [_ruta_de_capa("sombreros", clave, f"{s.clave}.png", forma)
              for s in cos.SOMBREROS]

    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for ruta in capas:
        # Sólo el canal alfa: un píxel con color pero transparente del todo no
        # es tinta, y mirando los cuatro canales contaría como tal.
        caja = _abrir(ruta).getchannel("A").getbbox()
        if caja is None:
            continue
        x0, y0 = min(x0, caja[0]), min(y0, caja[1])
        x1, y1 = max(x1, caja[2]), max(y1, caja[3])
    if x1 < 0:
        raise ValueError(f"{clave}/{etapa}: todas las capas están vacías")
    return x0 - MARGEN, y0 - MARGEN, x1 + MARGEN, y1 + MARGEN


@functools.lru_cache(maxsize=RECORDADOS)
def _armar(clave: str, etapa: str, animo: str, sombrero: str) -> bytes:
    """Apila, recorta al encuadre común y amplía al doble.

    El ×2 es de vecino más cercano y no inventa ni un color: cada píxel se
    convierte en un cuadrado de 2×2 del mismo color. Hace falta porque Discord
    no agranda la imagen de un embed más allá de su tamaño real.
    """
    forma = FORMA_ARCHIVO[etapa]
    imagen = _abrir(_ruta_del_cuerpo(clave, etapa))
    imagen = Image.alpha_composite(
        imagen, _abrir(_ruta_de_capa("caras", clave, CARAS[animo], forma)))
    if sombrero != SIN_SOMBRERO:
        imagen = Image.alpha_composite(
            imagen,
            _abrir(_ruta_de_capa("sombreros", clave, f"{sombrero}.png", forma)))

    # Recortar fuera del lienzo rellena con transparente, que es justo lo que se
    # quiere cuando el dibujo llega al borde y el margen se sale.
    recorte = imagen.crop(_caja(clave, etapa))
    doble = recorte.resize((recorte.width * 2, recorte.height * 2), Image.NEAREST)

    buzon = io.BytesIO()
    doble.save(buzon, "PNG")
    return buzon.getvalue()


def _capas_de(criatura: sim.Criatura) -> tuple[str, str, str, str] | None:
    """Las cuatro claves que identifican un retrato, o `None` si le toca ASCII.

    Devuelve `None` para las criaturas **teñidas** a propósito. El tinte se
    resolverá dibujando una imagen por color, y hasta entonces enseñar el
    retrato sin teñir sería peor que no enseñarlo: alguien pagó por tener su
    Pyro azul y lo vería rojo.
    """
    if (criatura.especie, criatura.etapa) not in CON_RETRATO or criatura.tinte:
        return None
    sombrero = criatura.sombrero or SIN_SOMBRERO
    if sombrero != SIN_SOMBRERO and sombrero not in {s.clave for s in cos.SOMBREROS}:
        # Un sombrero desconocido no puede dejar la ficha a medias: es
        # preferible caer al arte ASCII, que siempre está.
        return None
    return criatura.especie, criatura.etapa, criatura.animo_visual, sombrero


def imagen_de(criatura: sim.Criatura) -> bytes | None:
    """El PNG del retrato ya armado, o `None` si le toca seguir en ASCII."""
    capas = _capas_de(criatura)
    return _armar(*capas) if capas else None


def nombre_del_adjunto(criatura: sim.Criatura) -> str:
    """Cómo se llama el fichero al subirlo.

    Discord ata la imagen de un embed a un adjunto por su nombre, con
    `attachment://<nombre>`. Que el nombre y la imagen salgan del mismo sitio es
    lo que evita el fallo clásico: si no coinciden, la imagen sale vacía y no
    hay error en ninguna parte.
    """
    capas = _capas_de(criatura)
    if capas is None:
        raise ValueError("esta criatura no tiene retrato")
    return "_".join(capas) + ".png"


def color_de(criatura: sim.Criatura) -> int:
    """El color del borde de la ficha: el de su especie.

    No mira el tinte porque una criatura teñida no llega hasta aquí:
    `imagen_de` la devuelve a ASCII antes.
    """
    return COLORES.get(criatura.def_especie.color, COLOR_POR_DEFECTO)


def olvidar() -> None:
    """Vacía las cachés. Para las pruebas, que cambian las capas bajo los pies."""
    _armar.cache_clear()
    _caja.cache_clear()
    _nombre_de_archivo.cache_clear()
