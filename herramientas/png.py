"""Leer, escribir y componer PNG en Python puro, sin dependencias.

Se usa sólo al **generar** los retratos, nunca con el bot en marcha: `retrato.py`
se limita a devolver la ruta de un PNG ya compuesto. Por eso vivir sin Pillow
sale gratis — nadie tiene que instalar nada en la Raspberry para desplegar, y
quien quiera rehacer los dibujos tiene aquí todo lo que necesita.

Lento a propósito y sin optimizar: son unos pocos miles de imágenes que se
generan de tarde en tarde, y un bucle claro se lee mejor dentro de un año.
"""
from __future__ import annotations

import pathlib
import struct
import zlib


class Imagen:
    """Un mapa de bits RGBA, como una lista plana de bytes."""

    def __init__(self, ancho: int, alto: int, pixeles: bytearray):
        self.ancho, self.alto, self.pixeles = ancho, alto, pixeles

    @classmethod
    def vacia(cls, ancho: int, alto: int) -> "Imagen":
        return cls(ancho, alto, bytearray(ancho * alto * 4))

    def pixel(self, x: int, y: int) -> tuple[int, int, int, int]:
        i = (y * self.ancho + x) * 4
        return tuple(self.pixeles[i:i + 4])

    def poner(self, x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        i = (y * self.ancho + x) * 4
        self.pixeles[i:i + 4] = bytes(rgba)


def medidas(ruta: pathlib.Path) -> tuple[int, int]:
    """El ancho y el alto, leyendo sólo la cabecera.

    Existe para poder comprobar tamaños de muchos ficheros sin pagar el
    descifrado entero: `leer()` deshace los filtros píxel a píxel y en una suite
    de pruebas eso se nota. El IHDR va siempre justo tras la firma de 8 bytes.
    """
    cabecera = ruta.read_bytes()[:24]
    if cabecera[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{ruta.name} no es un PNG")
    return struct.unpack(">II", cabecera[16:24])


def leer(ruta: pathlib.Path) -> Imagen:
    """Decodifica un PNG RGBA de 8 bits.

    Un PNG guarda las filas comprimidas y cada una precedida de un byte que dice
    con qué **filtro** se codificó: los cinco que define el formato predicen
    cada byte a partir del de la izquierda, el de arriba o los dos. Hay que
    deshacerlos en orden, porque cada fila se apoya en la anterior ya resuelta.
    """
    b = ruta.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{ruta.name} no es un PNG")

    idat = b""
    ancho = alto = 0
    i = 8
    while i < len(b):
        largo = struct.unpack(">I", b[i:i + 4])[0]
        tipo = b[i + 4:i + 8]
        datos = b[i + 8:i + 8 + largo]
        if tipo == b"IHDR":
            ancho, alto = struct.unpack(">II", datos[:8])
            if (datos[8], datos[9]) != (8, 6):
                raise ValueError(f"{ruta.name}: hace falta RGBA de 8 bits")
        elif tipo == b"IDAT":
            idat += datos
        i += 12 + largo

    crudo = zlib.decompress(idat)
    fila_bytes = ancho * 4
    pixeles = bytearray(ancho * alto * 4)
    previa = bytearray(fila_bytes)
    p = 0
    for y in range(alto):
        filtro = crudo[p]
        linea = bytearray(crudo[p + 1:p + 1 + fila_bytes])
        p += 1 + fila_bytes
        for x in range(fila_bytes):
            izq = linea[x - 4] if x >= 4 else 0
            arr = previa[x]
            diag = previa[x - 4] if x >= 4 else 0
            if filtro == 1:
                linea[x] = (linea[x] + izq) & 0xFF
            elif filtro == 2:
                linea[x] = (linea[x] + arr) & 0xFF
            elif filtro == 3:
                linea[x] = (linea[x] + (izq + arr) // 2) & 0xFF
            elif filtro == 4:
                # Paeth: se queda con el vecino que mejor predice el píxel.
                estimado = izq + arr - diag
                da, db, dc = (abs(estimado - izq), abs(estimado - arr),
                              abs(estimado - diag))
                mejor = izq if da <= db and da <= dc else arr if db <= dc else diag
                linea[x] = (linea[x] + mejor) & 0xFF
        pixeles[y * fila_bytes:(y + 1) * fila_bytes] = linea
        previa = linea
    return Imagen(ancho, alto, pixeles)


def escribir(imagen: Imagen, ruta: pathlib.Path) -> None:
    """Guarda un PNG RGBA sin filtrar: el filtro 0 es «tal cual»."""
    crudo = bytearray()
    for y in range(imagen.alto):
        crudo.append(0)
        i = y * imagen.ancho * 4
        crudo += imagen.pixeles[i:i + imagen.ancho * 4]

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    cabecera = struct.pack(">IIBBBBB", imagen.ancho, imagen.alto, 8, 6, 0, 0, 0)
    ruta.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", cabecera)
        + trozo(b"IDAT", zlib.compress(bytes(crudo), 9))
        + trozo(b"IEND", b"")
    )


def encima(fondo: Imagen, capa: Imagen) -> Imagen:
    """El operador «over»: la capa se pinta sobre el fondo según su alfa.

    Con alfa recto —no premultiplicado—, que es como vienen los PNG:

        a = a₁ + a₂(1 - a₁)
        c = (c₁a₁ + c₂a₂(1 - a₁)) / a

    Los dos atajos de los extremos no son optimización sino corrección: donde la
    capa es opaca gana entera, y donde el resultado es transparente el color no
    está definido y dividir daría cero entre cero.
    """
    if (fondo.ancho, fondo.alto) != (capa.ancho, capa.alto):
        raise ValueError("las capas tienen que medir lo mismo")

    salida = Imagen.vacia(fondo.ancho, fondo.alto)
    for y in range(fondo.alto):
        for x in range(fondo.ancho):
            r2, g2, b2, a2 = fondo.pixel(x, y)
            r1, g1, b1, a1 = capa.pixel(x, y)
            if a1 == 255 or a2 == 0:
                salida.poner(x, y, (r1, g1, b1, a1))
                continue
            if a1 == 0:
                salida.poner(x, y, (r2, g2, b2, a2))
                continue
            fa, fb = a1 / 255, a2 / 255 * (1 - a1 / 255)
            a = fa + fb
            salida.poner(x, y, (
                round((r1 * fa + r2 * fb) / a),
                round((g1 * fa + g2 * fb) / a),
                round((b1 * fa + b2 * fb) / a),
                round(a * 255),
            ))
    return salida


def apilar(capas: list[Imagen]) -> Imagen:
    retrato = capas[0]
    for capa in capas[1:]:
        retrato = encima(retrato, capa)
    return retrato
