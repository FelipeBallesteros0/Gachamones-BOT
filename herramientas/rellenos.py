"""Dibuja un relleno para cada pieza del contrato de arte (`web/arte.py`).

Se corre con `./venv/bin/python -m herramientas.rellenos`: escribe sólo los
archivos que falten, así que un dibujo de verdad nunca se pisa. Con `--todo`
rehace todas las piezas, también los dibujos de verdad que ya hubieran
reemplazado a su relleno: vuelven a ser relleno.

Es determinista: colores lisos, sin azar ni fechas, y dos corridas dan los
mismos bytes. El monigote del avatar es el que antes dibujaba el cliente con
código (a doble tamaño, repartido en capas que se apilan cuerpo, ropa y pelo);
hoy su forma vive sólo aquí y en los archivos que esto escribe.
"""

import colorsys
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import avatar
import departamento
from retrato import _sin_tildes
from web import arte, pueblo

TRANSPARENTE = (0, 0, 0, 0)
GRIS_TENUE = (255, 255, 255, 40)


# --- utilidades --------------------------------------------------------------

def _hex(texto: str, alfa: int = 255) -> tuple[int, int, int, int]:
    n = int(texto.lstrip("#"), 16)
    return (n >> 16 & 255, n >> 8 & 255, n & 255, alfa)


def _oscurecer(color: tuple, factor: float) -> tuple:
    return tuple(round(c * factor) for c in color[:3]) + (color[3],)


def _color_de_lugar(indice: int, claridad: float, saturacion: float = 0.55) -> tuple:
    """Un tono distinto por lugar, repartido por el círculo de colores."""
    r, g, b = colorsys.hsv_to_rgb((indice * 0.381966) % 1.0, saturacion, claridad)
    return (round(r * 255), round(g * 255), round(b * 255), 255)


def _letra(tamano: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=tamano)


def _guardar(imagen: Image.Image, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta, "PNG", optimize=True)


# --- el pueblo ---------------------------------------------------------------

def _fondo(ancho: int, alto: int) -> Image.Image:
    imagen = Image.new("RGBA", (ancho, alto), (112, 164, 92, 255))
    pincel = ImageDraw.Draw(imagen)
    letra = _letra(34)
    for fila, y in enumerate(range(10, alto, 90)):
        for x in range(-120 + (fila % 2) * 130, ancho, 260):
            pincel.text((x, y), "RELLENO", fill=(150, 190, 130, 255), font=letra)
    tierra = (196, 160, 108, 255)
    escala, grosor = 2, 28
    nodos = pueblo.DATOS["nodos"]
    for a, b in pueblo.DATOS["aristas"]:
        (xa, ya), (xb, yb) = nodos[a], nodos[b]
        pincel.line((xa * escala, ya * escala, xb * escala, yb * escala), fill=tierra, width=grosor)
    radio = grosor // 2
    for x, y in nodos.values():  # un círculo en cada punta y esquina las deja redondeadas
        pincel.ellipse((x * escala - radio, y * escala - radio, x * escala + radio, y * escala + radio),
                       fill=tierra)
    return imagen


def _lugar(indice: int, lado: int) -> Image.Image:
    imagen = Image.new("RGBA", (lado, lado), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    pared = _color_de_lugar(indice, 0.9)
    techo = _color_de_lugar(indice, 0.55, 0.7)
    oscuro = (40, 36, 36, 255)
    base, ancho = lado - 4, lado - 28
    x0 = (lado - ancho) // 2
    # La casa se apoya en el borde inferior, que es donde va el nodo.
    pincel.rectangle((x0, base - 84, x0 + ancho, base), fill=pared, outline=oscuro, width=4)
    pincel.polygon([(x0 - 10, base - 80), (lado // 2, 10), (x0 + ancho + 10, base - 80)],
                   fill=techo, outline=oscuro)
    pincel.rectangle((lado // 2 - 12, base - 46, lado // 2 + 12, base), fill=oscuro)
    ventana = 14 + (indice % 3) * 4  # la forma también cambia un poco de un lugar a otro
    pincel.rectangle((x0 + 12, base - 66, x0 + 12 + ventana, base - 66 + ventana), fill=(250, 240, 200, 255),
                     outline=oscuro, width=2)
    return imagen


def _escena(indice: int, nombre: str, ancho: int, alto: int) -> Image.Image:
    pared = _color_de_lugar(indice, 0.85, 0.35)
    imagen = Image.new("RGBA", (ancho, alto), pared)
    pincel = ImageDraw.Draw(imagen)
    pincel.rectangle((0, alto * 2 // 3, ancho, alto), fill=_oscurecer(pared, 0.7))
    pincel.rectangle((0, alto // 2 - 56, ancho, alto // 2 + 56), fill=(30, 30, 30, 230))
    for dy, texto, tamano in ((-48, _sin_tildes(nombre).upper(), 48), (8, "RELLENO", 36)):
        letra = _letra(tamano)
        largo = pincel.textlength(texto, font=letra)
        pincel.text(((ancho - largo) / 2, alto // 2 + dy), texto, fill=(240, 240, 240, 255), font=letra)
    return imagen


# --- el avatar ---------------------------------------------------------------
# El monigote que antes dibujaba el cliente (unidades de 1 px, origen en los
# pies) a doble tamaño: el lienzo de 48 x 84 lleva los pies en (24, 80).

ESCALA = 2
PIES = (24, 80)
OJOS = _hex("#1d1d1f")
ZAPATOS = _hex("#3a3a3c")
BLANCO = _hex("#f5f3ee")
ORO = _hex("#e0a100")
# Cuánto se corre y se alza cada pierna (la de atrás, la de delante) en cada pose.
PASOS = {"quieto": ((0, 0), (0, 0)), "paso1": ((-2, 0), (2, 2)), "paso2": ((-2, 2), (2, 0))}


def _caja(pincel: ImageDraw.ImageDraw, color: tuple, x: float, y: float, ancho: float, alto: float) -> None:
    def px(v: float, origen: int) -> int:
        return origen + int(v * ESCALA + 0.5) if v >= 0 else origen - int(-v * ESCALA + 0.5)

    pincel.rectangle((px(x, PIES[0]), px(y, PIES[1]), px(x + ancho, PIES[0]) - 1, px(y + alto, PIES[1]) - 1),
                     fill=color)


def _lienzo() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    imagen = Image.new("RGBA", arte.AVATAR, TRANSPARENTE)
    return imagen, ImageDraw.Draw(imagen)


def _piernas(pincel, color, pose: str, ancho: int = 4, separacion: int = 1) -> None:
    for (desplazo, alza), x in zip(PASOS[pose], (-1 - ancho, separacion)):
        _caja(pincel, color, x + desplazo, -9 + alza, ancho, 9 - alza)
        _caja(pincel, ZAPATOS, x + desplazo, -2, ancho, 2)


def _cuerpo(piel: str, pose: str) -> Image.Image:
    color = _hex(_COLORES_DE_PIEL[piel])
    imagen, pincel = _lienzo()
    pincel.ellipse((PIES[0] - 18, PIES[1] - 5, PIES[0] + 18, PIES[1] + 5), fill=(0, 0, 0, 51))
    _piernas(pincel, color, pose)
    for x in (-8, 5):
        _caja(pincel, color, x, -19, 3, 11)
    _caja(pincel, color, -6, -31, 12, 11)
    _caja(pincel, OJOS, 0, -26, 2, 2)
    _caja(pincel, OJOS, 4, -26, 1.5, 2)
    return imagen


def _mangas(pincel, color, largo: float = 9) -> None:
    for x in (-8, 5):
        _caja(pincel, color, x, -19, 3, largo)


def _ropa(ropa: str, pose: str) -> Image.Image:
    color = _hex(_COLORES_DE_ROPA[ropa])
    imagen, pincel = _lienzo()
    if ropa == "poleron":
        _piernas(pincel, _hex("#2f3e63"), pose)
        _caja(pincel, color, -6, -20, 12, 12)
        _caja(pincel, _oscurecer(color, 0.75), -4, -20, 8, 1.5)
        _caja(pincel, BLANCO, -2, -18.5, 0.75, 3)
        _caja(pincel, BLANCO, 1.25, -18.5, 0.75, 3)
        _caja(pincel, _oscurecer(color, 0.85), -3, -13, 6, 3)
        _mangas(pincel, _oscurecer(color, 0.85))
    elif ropa == "camisa":
        _piernas(pincel, _hex("#4b4f5c"), pose)
        _caja(pincel, color, -6, -20, 12, 12)
        _caja(pincel, BLANCO, -3, -20, 2.5, 2)
        _caja(pincel, BLANCO, 0.5, -20, 2.5, 2)
        for y in (-17, -14, -11):
            _caja(pincel, _oscurecer(color, 0.6), -0.5, y, 1, 1)
        _caja(pincel, ZAPATOS, -6, -9, 12, 1)
        _mangas(pincel, _oscurecer(color, 0.9), 6)
    elif ropa == "vestido":
        # Las piernas son las de la piel (capa del cuerpo): aquí sólo la falda, que se mece con el paso.
        mecer = {"quieto": 0, "paso1": -1, "paso2": 1}[pose]
        _caja(pincel, color, -6, -20, 12, 7)
        _caja(pincel, color, -7, -13, 14, 7)
        _caja(pincel, _oscurecer(color, 0.75), -6, -14, 12, 1)
        _caja(pincel, _oscurecer(color, 0.8), -7 + mecer, -7, 14, 1)
        _mangas(pincel, _oscurecer(color, 0.85), 4)
    else:  # overol
        _piernas(pincel, color, pose)
        _caja(pincel, BLANCO, -6, -20, 12, 12)
        _caja(pincel, color, -6, -11, 12, 3)
        _caja(pincel, color, -4, -16, 8, 6)
        _caja(pincel, color, -5, -20, 2, 5)
        _caja(pincel, color, 3, -20, 2, 5)
        _caja(pincel, ORO, -4, -16, 1, 1)
        _caja(pincel, ORO, 3, -16, 1, 1)
        _caja(pincel, _oscurecer(color, 0.8), -2, -14, 4, 2)
        _mangas(pincel, BLANCO, 5)
    return imagen


def _pelo(pelo: str, color: str, pose: str, lazo: str = "#d9534f") -> Image.Image:
    # Igual en las tres poses. En la coleta el lazo era del color de la ropa; aquí es fijo.
    rgba, cinta = _hex(_COLORES_DE_PELO[color]), _hex(lazo)
    imagen, pincel = _lienzo()
    if pelo == "corto":
        _caja(pincel, rgba, -7, -33, 14, 5)
        _caja(pincel, rgba, -7, -31, 3, 6)
    elif pelo == "largo":
        _caja(pincel, rgba, -7, -33, 14, 5)
        _caja(pincel, rgba, -8, -31, 4, 13)
        _caja(pincel, rgba, 5, -29, 2, 3)
    elif pelo == "rizado":
        _caja(pincel, rgba, -8, -33, 16, 5)
        _caja(pincel, rgba, -7, -35, 4, 2)
        _caja(pincel, rgba, -2, -36, 4, 3)
        _caja(pincel, rgba, 3, -35, 4, 2)
        _caja(pincel, rgba, -9, -31, 4, 8)
        _caja(pincel, rgba, 6, -31, 2, 3)
    elif pelo == "coleta":
        _caja(pincel, rgba, -7, -33, 14, 5)
        _caja(pincel, rgba, -7, -31, 3, 5)
        _caja(pincel, rgba, -11, -30, 3, 9)
        _caja(pincel, cinta, -9, -31, 2, 2)
    else:  # rapado
        _caja(pincel, rgba, -6.5, -32, 13, 2.5)
        _caja(pincel, rgba, -7, -31, 1.5, 4)
    return imagen


# Los mismos colores que las muestras del selector del avatar (`MUESTRAS` en `web/static/js/entrada.js`).
_COLORES_DE_PIEL = {"clara": "#f6d5bd", "media": "#e8b48a", "tostada": "#c68a5c", "oscura": "#8a5636"}
_COLORES_DE_PELO = {"negro": "#2a2523", "castano": "#6b4226", "rubio": "#e2b552",
                    "rojo": "#c2502a", "cano": "#d4d4da", "azul": "#3a6fd8"}
_COLORES_DE_ROPA = {"poleron": "#d9534f", "camisa": "#4f9d69", "vestido": "#8f6ad8", "overol": "#3f6fb5"}


# --- los efectos -------------------------------------------------------------

def _efecto(nombre: str, lado: int) -> Image.Image:
    imagen = Image.new("RGBA", (lado, lado), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    c = lado / 2
    if nombre == "corazon":
        rojo = (226, 64, 92, 255)
        pincel.ellipse((3, 5, 17, 19), fill=rojo)
        pincel.ellipse((15, 5, 29, 19), fill=rojo)
        pincel.polygon([(4, 14), (28, 14), (16, 29)], fill=rojo)
    elif nombre == "estrella":
        puntas = []
        for i in range(10):
            radio = 14 if i % 2 == 0 else 6
            angulo = -math.pi / 2 + i * math.pi / 5
            puntas.append((c + radio * math.cos(angulo), c + radio * math.sin(angulo)))
        pincel.polygon(puntas, fill=(250, 204, 60, 255), outline=(190, 140, 20, 255))
    elif nombre == "sombra":
        # Una elipse achatada, oscura y translúcida, al centro: lo que el
        # gachamon pisa en el mapa. Del mismo negro que la del avatar.
        pincel.ellipse((2, 11, lado - 3, lado - 12), fill=(0, 0, 0, 51))
    else:  # marca de destino: un anillo con punto
        rojo = (226, 64, 92, 255)
        pincel.ellipse((3, 3, 29, 29), outline=rojo, width=4)
        pincel.ellipse((12, 12, 20, 20), fill=rojo)
    return imagen


# --- los íconos --------------------------------------------------------------
# A 48 x 48 no cabe «RELLENO»: el relleno se nota por su cuadro liso, de un color
# por grupo, con las letras del nombre de la clave (la primera palabra en grande
# y, debajo, la última si hay más de una: así una poción de 1d4 y una de 1d6 se distinguen).

_COLORES_DE_ICONO = {"objetos": (46, 125, 210, 255), "cosmeticos": (150, 70, 200, 255),
                     "muebles": (200, 110, 40, 255)}


def _icono(grupo: str, clave: str, lado: int) -> Image.Image:
    imagen = Image.new("RGBA", (lado, lado), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    pincel.rectangle((3, 3, lado - 4, lado - 4), fill=_COLORES_DE_ICONO[grupo], outline=(255, 255, 255, 255),
                     width=2)
    palabras = clave.split("_")
    renglones = [(palabras[0][:3], 16)]
    if len(palabras) > 1:
        renglones.append((palabras[-1][:4], 12))
    alto_total = sum(t for _, t in renglones) + 2 * (len(renglones) - 1)
    y = (lado - alto_total) / 2 - 2
    for texto, tamano in renglones:
        texto = texto.upper()
        letra = _letra(tamano)
        largo = pincel.textlength(texto, font=letra)
        pincel.text(((lado - largo) / 2, y), texto, fill=(255, 255, 255, 255), font=letra)
        y += tamano + 2
    return imagen


# --- la pieza del departamento ------------------------------------------------
# Relleno al tamaño servido. La casilla es un rombo que llena su lienzo; un tramo de
# pared, un paralelogramo; un mueble, una caja en perspectiva isométrica sobre su
# huella: su dibujo cubre a lo ancho el rombo que ocupa, su borde de abajo es la
# esquina de delante, y si no se pisa sobresale hacia arriba la altura del contrato.

_BLANCO = (255, 255, 255, 255)
_MARCA = (255, 214, 64, 255)
_TINTA = (20, 20, 24, 255)
# Hacia dónde mira el frente del mueble en el dibujo (x, y en pantalla).
_MIRA = {"se": (2, 1), "so": (-2, 1), "no": (-2, -1), "ne": (2, -1)}


def _rotular(pincel: ImageDraw.ImageDraw, centro: tuple, renglones: list[str], tamano: int) -> None:
    """Las letras de la clave, centradas, una línea por renglón."""
    x, y = centro
    alto = tamano + 6
    y0 = y - alto * (len(renglones) - 1) / 2
    for i, texto in enumerate(renglones):
        pincel.text((x, y0 + i * alto), texto, fill=_BLANCO, font=_letra(tamano), anchor="mm",
                    stroke_width=3, stroke_fill=_TINTA)


def _renglones_de(clave: str) -> list[str]:
    palabras = clave.split("_")
    texto = [palabras[0][:3].upper()]
    if len(palabras) > 1:
        texto.append(palabras[-1][:3].upper())
    return texto


def _casilla(ancho: int, alto: int) -> Image.Image:
    imagen = Image.new("RGBA", (ancho, alto), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    rombo = [(0, alto // 2), (ancho // 2, 0), (ancho - 1, alto // 2), (ancho // 2, alto - 1)]
    pincel.polygon(rombo, fill=(150, 130, 96, 255), outline=_BLANCO, width=4)
    _rotular(pincel, (ancho // 2, alto // 2), ["SUELO", "RELLENO"], 44)
    return imagen


def _tramo_de_pared(ancho: int, alto: int, lado: str, color: tuple, renglones: list[str],
                    mira: str | None = None) -> Image.Image:
    """Un paralelogramo de `ancho` y de `alto` total: su pendiente es la de la pared que sube por la
    izquierda (`se`, la pared izquierda) o por la derecha (`so`, la pared derecha)."""
    imagen = Image.new("RGBA", (ancho, alto), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    pendiente = ancho // 2
    if lado == "izquierda":
        puntos = [(0, pendiente), (ancho - 1, 0), (ancho - 1, alto - pendiente - 1), (0, alto - 1)]
    else:
        puntos = [(0, 0), (ancho - 1, pendiente), (ancho - 1, alto - 1), (0, alto - pendiente - 1)]
    pincel.polygon(puntos, fill=color, outline=_BLANCO, width=4)
    centro = (sum(x for x, _ in puntos) / 4, sum(y for _, y in puntos) / 4)
    _rotular(pincel, centro, renglones, 44 if ancho <= 256 else 60)
    if mira:
        _flecha(pincel, (centro[0], centro[1] + 90), mira, 0, 60)
    return imagen


def _flecha(pincel: ImageDraw.ImageDraw, centro: tuple, orientacion: str, inicio: float, largo: float) -> None:
    """Una flecha amarilla que sale de `centro` hacia donde mira el frente."""
    dx, dy = _MIRA[orientacion]
    norma = math.hypot(dx, dy)
    ux, uy = dx / norma, dy / norma
    cx, cy = centro
    punta = (cx + ux * largo, cy + uy * largo)
    base = (cx + ux * (largo - 40), cy + uy * (largo - 40))
    pincel.line((cx + ux * inicio, cy + uy * inicio, *base), fill=_MARCA, width=14)
    nx, ny = -uy, ux
    pincel.polygon([punta, (base[0] + nx * 30, base[1] + ny * 30), (base[0] - nx * 30, base[1] - ny * 30)],
                   fill=_MARCA, outline=_TINTA)


def _en_cara(esquinas: list[tuple], u: float, v: float) -> tuple:
    """Un punto dentro de un paralelogramo [a, b, c, d]: `u` de a a b, `v` de a a d."""
    (ax, ay), (bx, by), _, (dx, dy) = esquinas
    return (ax + (bx - ax) * u + (dx - ax) * v, ay + (by - ay) * u + (dy - ay) * v)


def _mueble_de_suelo(mueble: departamento.Mueble, indice: int, orientacion: str,
                     ancho: int, alto: int) -> Image.Image:
    imagen = Image.new("RGBA", (ancho, alto), TRANSPARENTE)
    pincel = ImageDraw.Draw(imagen)
    a, f = mueble.ancho, mueble.fondo
    if orientacion in ("so", "ne"):
        a, f = f, a  # girado un cuarto de vuelta: la huella cambia de lado, el lienzo no
    unidad = arte.CASILLA[0] // 2
    alza = arte.ALTURA if mueble.capa == departamento.BULTO else 0
    fondo_y = (a + f) * unidad // 2
    # Las cuatro esquinas de la huella al nivel del suelo y al de la tapa.
    arriba = [(f * unidad, 0), ((a + f) * unidad - 1, a * unidad // 2), (a * unidad, fondo_y - 1),
              (0, f * unidad // 2)]
    abajo = [(x, y + alza) for x, y in arriba]
    cima, izq, der, base = arriba[0], arriba[3], arriba[1], arriba[2]
    color = _color_de_lugar(indice, 0.9, 0.5)
    if alza:
        pincel.polygon([izq, base, abajo[2], abajo[3]], fill=_oscurecer(color, 0.7), outline=_BLANCO, width=3)
        pincel.polygon([base, der, abajo[1], abajo[2]], fill=_oscurecer(color, 0.5), outline=_BLANCO, width=3)
    pincel.polygon(arriba, fill=color, outline=_BLANCO, width=4)
    letras = _renglones_de(mueble.clave)
    centro = (sum(x for x, _ in arriba) / 4, sum(y for _, y in arriba) / 4)
    if alza:
        cara_izq = [izq, base, abajo[2], abajo[3]]
        cara_der = [base, der, abajo[1], abajo[2]]
        frente = {"se": cara_der, "so": cara_izq}.get(orientacion)
        otra = cara_izq if frente is not cara_izq else cara_der
        _rotular(pincel, _en_cara(otra, 0.5, 0.5), letras, 84)
        if frente:  # el frente se nota: una tapa clara con una manija, sobre la cara que mira
            marco = [_en_cara(frente, u, v) for u, v in ((0.12, 0.2), (0.88, 0.2), (0.88, 0.8), (0.12, 0.8))]
            pincel.polygon(marco, fill=_MARCA, outline=_TINTA)
        _flecha(pincel, centro, orientacion, 0, 100 * min(a, f))
    else:
        _rotular(pincel, centro, letras, 56)
        _flecha(pincel, centro, orientacion, 70, 125 * min(a, f))
    return imagen


def _pieza_del_departamento(partes: list[str], ancho: int, alto: int) -> Image.Image:
    nombre = partes[-1]
    if nombre == "suelo":
        return _casilla(ancho, alto)
    if nombre.startswith("pared-"):
        lado = nombre.removeprefix("pared-")
        return _tramo_de_pared(ancho, alto, lado, (120, 138, 170, 255),
                               ["PARED", lado[:3].upper(), "RELLENO"])
    clave, orientacion = nombre.rsplit("-", 1)
    mueble = departamento.MUEBLES[clave]
    indice = list(departamento.MUEBLES).index(clave)
    if mueble.capa == departamento.PARED:
        return _tramo_de_pared(ancho, alto, "izquierda" if orientacion == "se" else "derecha",
                               _color_de_lugar(indice, 0.9, 0.5), _renglones_de(clave), orientacion)
    return _mueble_de_suelo(mueble, indice, orientacion, ancho, alto)


# --- la generación -----------------------------------------------------------

def _dibujar(pieza: arte.Pieza) -> Image.Image:
    partes = pieza.ruta.removesuffix(".png").split("/")
    if pieza.familia == "pueblo":
        return _fondo(pieza.ancho, pieza.alto)
    if pieza.familia == "pieza":
        return _pieza_del_departamento(partes, pieza.ancho, pieza.alto)
    if pieza.familia == "iconos":
        return _icono(partes[1], partes[2], pieza.ancho)
    if pieza.familia == "efectos":
        return _efecto(partes[1], pieza.ancho)
    if pieza.familia in ("lugares", "escenas"):
        clave = partes[-1]
        indice = list(pueblo.LUGARES).index(clave)
        if pieza.familia == "lugares":
            return _lugar(indice, pieza.ancho)
        return _escena(indice, pueblo.LUGARES[clave].nombre, pieza.ancho, pieza.alto)
    capa, nombre = partes[1], partes[2]
    if capa == "pelo":
        pelo, color, pose = nombre.split("-")
        return _pelo(pelo, color, pose)
    clave, pose = nombre.split("-")
    return _cuerpo(clave, pose) if capa == "cuerpo" else _ropa(clave, pose)


def generar(todo: bool = False) -> list[str]:
    """Escribe el relleno de cada pieza que falte (o de todas) y devuelve las rutas escritas."""
    raiz = arte.RAIZ
    escritas = []
    for pieza in arte.piezas():
        destino = raiz / pieza.ruta
        if destino.exists() and not todo:
            continue
        imagen = _dibujar(pieza)
        assert imagen.size == (pieza.ancho, pieza.alto), pieza.ruta
        _guardar(imagen, destino)
        escritas.append(pieza.ruta)
    datos = raiz.parent / "datos"
    datos.mkdir(parents=True, exist_ok=True)
    (datos / "arte.json").write_text(
        json.dumps(arte.como_json(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return escritas


if __name__ == "__main__":
    for ruta in generar(todo="--todo" in sys.argv[1:]):
        print(ruta)
