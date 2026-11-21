"""Las reglas de una subida del dibujante: qué PNG vale, cómo sale limpio, cómo se guarda y qué se poda.

Los PNG se fabrican aquí, con Pillow o a mano (`png_crudo`) para lo que Pillow no
sabe escribir: 16 bits y grises de pocos bits con transparencia. Nunca se toca
el arte del repo.
"""
import hashlib
import io
import logging
import os
import shutil
import struct
import subprocess
import sys
import threading
import warnings
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageCms, PngImagePlugin

import arte_subido
import config
from herramientas import pieza as herramienta_pieza
from tests import perfiles_de_color
from web import arte

RAIZ = Path(__file__).resolve().parent.parent
FIRMA = b"\x89PNG\r\n\x1a\n"
CORAZON = "efectos/corazon.png"   # 32 × 32, familia `efectos`
SUELO = "pieza/suelo.png"         # se sube a 1024 × 512; el juego sirve 512 × 256
MACETA = "pieza/muebles/maceta-se.png"  # se sube a 1024 × 1536; el juego sirve 512 × 768
GRIS, RGB, PALETA, GRIS_Y_ALFA, RGBA = 0, 2, 3, 4, 6
CANALES = {GRIS: 1, RGB: 3, PALETA: 1, GRIS_Y_ALFA: 2, RGBA: 4}


def png_de(imagen: Image.Image, **opciones) -> bytes:
    salida = io.BytesIO()
    imagen.save(salida, "PNG", **opciones)
    return salida.getvalue()


def trozo(tipo: bytes, datos: bytes) -> bytes:
    return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))


def png_crudo(ancho, alto, profundidad, tipo, muestras, *extra) -> bytes:
    """Un PNG escrito a mano. `muestras` es el primer trozo de cada renglón, que se
    repite a lo ancho; cada muestra lleva un valor por canal. `extra` son trozos
    `(tipo, datos)` que van entre la cabecera y los datos."""
    valores = [v for x in range(ancho) for v in muestras[x % len(muestras)]]
    assert len(muestras[0]) == CANALES[tipo]
    if profundidad == 16:
        fila = b"".join(struct.pack(">H", v) for v in valores)
    elif profundidad == 8:
        fila = bytes(valores)
    else:
        bits = "".join(format(v, f"0{profundidad}b") for v in valores)
        bits += "0" * (-len(bits) % 8)
        fila = int(bits, 2).to_bytes(len(bits) // 8, "big")
    return (FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, profundidad, tipo, 0, 0, 0))
            + b"".join(trozo(t, d) for t, d in extra)
            + trozo(b"IDAT", zlib.compress((b"\x00" + fila) * alto)) + trozo(b"IEND", b""))


def trozos(png: bytes) -> list[bytes]:
    """Los tipos de trozo de un PNG, en orden."""
    tipos, i = [], len(FIRMA)
    while i < len(png):
        largo = struct.unpack(">I", png[i:i + 4])[0]
        tipos.append(png[i + 4:i + 8])
        i += 12 + largo
    return tipos


def dibujo(ancho, alto) -> Image.Image:
    """Una imagen RGBA con píxeles distintos y transparencias variadas, siempre la misma."""
    imagen = Image.new("RGBA", (ancho, alto))
    imagen.putdata([((x * 7) % 256, (y * 13) % 256, (x * y) % 256, (x + y) % 256)
                    for y in range(alto) for x in range(ancho)])
    return imagen


def lugar(ruta):
    encontrado = arte.lugar_de(ruta)
    assert encontrado is not None
    return encontrado


def preparada(cuerpo, ruta=CORAZON) -> tuple[bytes, str]:
    """Los datos y el nombre del original limpio, para lo que no mira la chica."""
    original, _ = arte_subido.preparar(cuerpo, lugar(ruta))
    return original.datos, original.nombre


def abierta(datos: bytes) -> Image.Image:
    imagen = Image.open(io.BytesIO(datos))
    imagen.load()
    return imagen


# --- Las medidas ---------------------------------------------------------------

def test_las_medidas_del_contrato_son_las_de_cada_pieza():
    medidas = arte_subido.medidas()
    assert medidas == {p.ruta: (p.ancho, p.alto) for p in arte.piezas()}
    assert medidas[CORAZON] == (32, 32) and medidas[SUELO] == (512, 256)  # lo servido


# --- Lo que vale y cómo sale -----------------------------------------------------

def test_un_png_de_su_medida_sale_limpio_y_con_el_nombre_de_su_contenido():
    original = dibujo(32, 32)
    datos, nombre = preparada(png_de(original))
    assert nombre == hashlib.sha256(datos).hexdigest() + ".png"
    limpia = abierta(datos)
    assert limpia.format == "PNG" and limpia.mode == "RGBA" and limpia.size == (32, 32)
    assert limpia.tobytes() == original.tobytes()


def test_dos_subidas_iguales_dan_el_mismo_nombre():
    cuerpo = png_de(dibujo(32, 32))
    assert arte_subido.preparar(cuerpo, lugar(CORAZON)) == arte_subido.preparar(cuerpo, lugar(CORAZON))
    # La misma imagen guardada de otra forma (otra compresión, otro modo) también.
    otra = png_de(dibujo(32, 32), compress_level=0)
    assert otra != cuerpo
    assert preparada(otra)[1] == preparada(cuerpo)[1]


def test_un_png_con_metadatos_y_perfil_de_color_sale_sin_ellos():
    datos_extra = PngImagePlugin.PngInfo()
    datos_extra.add_text("Autor", "alguien")
    datos_extra.add_text("Comentario", "comprimido", zip=True)
    datos_extra.add_itxt("Descripción", "con tildes")
    datos_extra.add(b"gAMA", struct.pack(">I", 45455))
    datos_extra.add(b"prIv", b"lo que no es de nadie")
    original = dibujo(32, 32)
    cuerpo = png_de(original, pnginfo=datos_extra, icc_profile=b"un perfil de color",
                    exif=b"Exif\x00\x00MM\x00*\x00\x00\x00\x08\x00\x00", dpi=(300, 300))
    assert {b"tEXt", b"zTXt", b"iTXt", b"gAMA", b"prIv", b"iCCP", b"eXIf", b"pHYs"} <= set(trozos(cuerpo))
    datos, nombre = preparada(cuerpo)
    assert set(trozos(datos)) <= {b"IHDR", b"IDAT", b"IEND"}
    limpia = abierta(datos)
    assert limpia.info == {} and limpia.tobytes() == original.tobytes()
    assert nombre == preparada(png_de(original))[1]


TRNS = b"tRNS"


@pytest.mark.parametrize("cuerpo, esperado", [
    pytest.param(png_crudo(32, 32, 8, PALETA, [(0,), (1,), (2,)],
                           (b"PLTE", bytes([255, 0, 0, 0, 255, 0, 0, 0, 255])), (TRNS, bytes([0, 128]))),
                 [(255, 0, 0, 0), (0, 255, 0, 128), (0, 0, 255, 255)], id="indexado-con-transparencia"),
    pytest.param(png_crudo(32, 32, 4, PALETA, [(0,), (1,), (2,)],
                           (b"PLTE", bytes([255, 0, 0, 0, 255, 0, 0, 0, 255])), (TRNS, bytes([0, 128]))),
                 [(255, 0, 0, 0), (0, 255, 0, 128), (0, 0, 255, 255)], id="indexado-de-4-bits"),
    pytest.param(png_crudo(32, 32, 8, GRIS, [(0,), (100,), (255,)], (TRNS, struct.pack(">H", 100))),
                 [(0, 0, 0, 255), (100, 100, 100, 0), (255, 255, 255, 255)], id="gris-con-transparencia"),
    pytest.param(png_crudo(32, 32, 4, GRIS, [(0,), (7,), (15,)]),
                 [(0, 0, 0, 255), (119, 119, 119, 255), (255, 255, 255, 255)], id="gris-de-4-bits"),
    pytest.param(png_crudo(32, 32, 2, GRIS, [(0,), (1,), (2,), (3,)], (TRNS, struct.pack(">H", 1))),
                 [(0, 0, 0, 255), (85, 85, 85, 0), (170, 170, 170, 255), (255, 255, 255, 255)],
                 id="gris-de-2-bits-con-transparencia"),
    pytest.param(png_crudo(32, 32, 1, GRIS, [(0,), (1,)], (TRNS, struct.pack(">H", 1))),
                 [(0, 0, 0, 255), (255, 255, 255, 0)], id="gris-de-1-bit-con-transparencia"),
    pytest.param(png_crudo(32, 32, 16, GRIS, [(0,), (0x1234,), (0xABCD,), (0xFFFF,)]),
                 [(0, 0, 0, 255), (0x12, 0x12, 0x12, 255), (0xAB, 0xAB, 0xAB, 255), (255, 255, 255, 255)],
                 id="gris-de-16-bits"),
    pytest.param(png_crudo(32, 32, 16, GRIS, [(0x1234,), (0x1200,), (0xFFFF,)], (TRNS, struct.pack(">H", 0x1234))),
                 [(0x12, 0x12, 0x12, 0), (0x12, 0x12, 0x12, 255), (255, 255, 255, 255)],
                 id="gris-de-16-bits-con-transparencia"),
    pytest.param(png_crudo(32, 32, 16, GRIS_Y_ALFA, [(0xFFFF, 0x8000), (0, 0xFFFF)]),
                 [(255, 255, 255, 128), (0, 0, 0, 255)], id="gris-y-alfa-de-16-bits"),
    pytest.param(png_crudo(32, 32, 16, RGBA, [(0xFFFF, 0, 0, 0x8000), (0, 0xFFFF, 0, 0)]),
                 [(255, 0, 0, 128), (0, 255, 0, 0)], id="rgba-de-16-bits"),
    pytest.param(png_crudo(32, 32, 8, RGB, [(1, 2, 3), (4, 5, 6)], (TRNS, struct.pack(">HHH", 4, 5, 6))),
                 [(1, 2, 3, 255), (4, 5, 6, 0)], id="rgb-con-transparencia"),
    pytest.param(png_crudo(32, 32, 16, RGB, [(0x1234, 0x5678, 0x9ABC), (0xFFFF, 0, 0)],
                           (TRNS, struct.pack(">HHH", 0x1234, 0x5678, 0x9ABC))),
                 [(0x12, 0x56, 0x9A, 0), (255, 0, 0, 255)], id="rgb-de-16-bits-con-transparencia"),
])
def test_cualquier_modo_de_png_sale_en_rgba_sin_perder_la_transparencia(cuerpo, esperado):
    datos, _ = preparada(cuerpo)
    limpia = abierta(datos)
    assert limpia.mode == "RGBA" and limpia.size == (32, 32)
    for y in (0, 31):
        assert [limpia.getpixel((x, y)) for x in range(len(esperado))] == esperado


def test_un_mueble_al_doble_sale_con_su_original_y_su_version_servida():
    original = dibujo(1024, 1536)
    grande, chica = arte_subido.preparar(png_de(original), lugar(MACETA))
    assert (grande.ancho, grande.alto, chica.ancho, chica.alto) == (1024, 1536, 512, 768)
    assert abierta(grande.datos).tobytes() == original.tobytes()
    assert abierta(chica.datos).size == (512, 768)
    assert abierta(chica.datos).tobytes() == arte_subido.a_lo_servido(original).tobytes()
    assert grande.nombre == hashlib.sha256(grande.datos).hexdigest() + ".png"
    assert chica.nombre == hashlib.sha256(chica.datos).hexdigest() + ".png"
    assert grande.nombre != chica.nombre


def test_fuera_de_la_pieza_el_original_y_la_chica_son_el_mismo_archivo():
    grande, chica = arte_subido.preparar(png_de(dibujo(32, 32)), lugar(CORAZON))
    assert chica is grande


def test_la_herramienta_reduce_igual_que_antes(tmp_path):
    """Mover la reducción a `arte_subido` no cambia lo que escribe `herramientas/pieza.py`."""
    original = dibujo(1024, 512)
    archivo = tmp_path / "suelo.png"
    original.save(archivo)
    antes = original.resize((512, 256), Image.LANCZOS)
    assert herramienta_pieza.reducida(archivo).tobytes() == antes.tobytes()


# --- Lo que no vale ---------------------------------------------------------------

def no_vale(cuerpo, ruta=CORAZON) -> str:
    with pytest.raises(arte_subido.NoVale) as rechazo:
        arte_subido.preparar(cuerpo, lugar(ruta))
    assert rechazo.value.mensaje == str(rechazo.value)
    return rechazo.value.mensaje


def test_una_imagen_con_la_medida_de_otra_pieza_se_rechaza_diciendo_la_esperada_y_la_recibida():
    mensaje = no_vale(png_de(dibujo(48, 48)))
    assert "48 × 48 px" in mensaje and "32 × 32 px" in mensaje


def test_la_medida_servida_de_un_mueble_se_rechaza_nombrando_la_de_subida():
    assert no_vale(png_de(dibujo(512, 768)), MACETA) == \
        "La imagen mide 512 × 768 px y esta pieza pide 1024 × 1536 px."
    assert no_vale(png_de(dibujo(512, 256)), SUELO) == \
        "La imagen mide 512 × 256 px y esta pieza pide 1024 × 512 px."


def test_el_doble_tampoco_vale_fuera_de_la_familia_de_la_pieza():
    mensaje = no_vale(png_de(dibujo(64, 64)))
    assert "64 × 64 px" in mensaje and "32 × 32 px" in mensaje


def otro_formato(formato: str) -> bytes:
    salida = io.BytesIO()
    dibujo(32, 32).convert("RGB").save(salida, formato)
    return salida.getvalue()


@pytest.mark.parametrize("cuerpo", [
    pytest.param(b"", id="vacio"),
    pytest.param(b"hola, soy un png", id="texto"),
    pytest.param(FIRMA, id="solo-la-firma"),
    pytest.param(FIRMA + b"basura que no es un trozo de nada", id="firma-y-basura"),
    pytest.param(otro_formato("JPEG"), id="jpeg"),
    pytest.param(otro_formato("GIF"), id="gif"),
    pytest.param(otro_formato("BMP"), id="bmp"),
    pytest.param(b"GIF89a" + png_de(dibujo(32, 32))[6:], id="png-con-otra-firma"),
])
def test_lo_que_dice_ser_png_y_no_lo_es_se_rechaza(cuerpo):
    no_vale(cuerpo)


def danado(cuerpo: bytes, posicion: int) -> bytes:
    roto = bytearray(cuerpo)
    roto[posicion] ^= 0xFF
    return bytes(roto)


BIEN = png_de(dibujo(32, 32))


@pytest.mark.parametrize("cuerpo", [
    pytest.param(BIEN[:-1], id="sin-el-ultimo-byte"),
    pytest.param(BIEN[:-12], id="sin-el-final"),
    pytest.param(BIEN[:len(BIEN) // 2], id="a-la-mitad"),
    pytest.param(BIEN[:40], id="solo-la-cabecera"),
    pytest.param(danado(BIEN, len(BIEN) // 2), id="un-byte-cambiado"),
    pytest.param(FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 6, 0, 0, 0))
                 + trozo(b"IDAT", zlib.compress(b"\x00" * 10)) + trozo(b"IEND", b""), id="datos-de-menos"),
    pytest.param(FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 6, 0, 0, 0))
                 + trozo(b"IDAT", b"esto no es zlib") + trozo(b"IEND", b""), id="datos-que-no-se-descomprimen"),
])
def test_un_png_truncado_o_danado_se_rechaza(cuerpo):
    no_vale(cuerpo)


def png_que_pesa(tamano: int) -> bytes:
    """Un PNG válido de 32 × 32 que pesa exactamente `tamano` bytes, rellenado con un trozo privado."""
    base = png_crudo(32, 32, 8, RGBA, [(1, 2, 3, 4)])
    relleno = tamano - len(base) - 12
    cuerpo = base[:33] + trozo(b"prVt", b"\x00" * relleno) + base[33:]
    assert len(cuerpo) == tamano
    return cuerpo


def test_un_png_de_24_mb_vale_y_uno_de_un_byte_mas_no():
    assert arte_subido.LIMITE_DE_BYTES == 24 * 1024 * 1024
    datos, _ = preparada(png_que_pesa(arte_subido.LIMITE_DE_BYTES))
    assert len(datos) < 1000
    assert no_vale(png_que_pesa(arte_subido.LIMITE_DE_BYTES + 1)) == "La imagen pesa más de 24 MB."


def test_una_bomba_de_descompresion_se_rechaza_por_su_medida_sin_abrirla(monkeypatch):
    # 9000 × 9000 a 1 bit: pesa unos 10 KB, se decodificaría en unos 300 MB en RGBA y queda
    # por debajo del tope propio de Pillow, así que sólo la para mirar la medida antes.
    fila = b"\x00" * (1 + 9000 // 8)
    bomba = (FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", 9000, 9000, 1, 0, 0, 0, 0))
             + trozo(b"IDAT", zlib.compress(fila * 9000, 9)) + trozo(b"IEND", b""))
    assert len(bomba) < 20_000 and 9000 * 9000 < Image.MAX_IMAGE_PIXELS
    abiertas = []

    def no_abrir(*args, **opciones):
        abiertas.append(args)
        raise AssertionError("se llegó a abrir la bomba")

    monkeypatch.setattr(arte_subido.Image, "open", no_abrir)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mensaje = no_vale(bomba, SUELO)
    assert "9000 × 9000 px" in mensaje and "1024 × 512 px" in mensaje
    assert abiertas == []


# --- Guardar --------------------------------------------------------------------

def preparado(semilla=0) -> tuple[bytes, str]:
    imagen = dibujo(32, 32)
    imagen.putpixel((0, 0), (semilla, 0, 0, 255))
    return preparada(png_de(imagen))


def test_guardar_escribe_el_archivo_entero_con_su_nombre(tmp_path):
    carpeta = tmp_path / "arte_subido"
    datos, nombre = preparado()
    destino = arte_subido.guardar(carpeta, nombre, datos)
    assert destino == carpeta / nombre
    assert sorted(p.name for p in carpeta.iterdir()) == [nombre]
    assert destino.read_bytes() == datos


def test_guardar_no_reescribe_lo_que_ya_esta(tmp_path):
    datos, nombre = preparado()
    destino = arte_subido.guardar(tmp_path, nombre, datos)
    antes = destino.stat()
    arte_subido.guardar(tmp_path, nombre, datos)
    despues = destino.stat()
    assert (despues.st_ino, despues.st_mtime_ns) == (antes.st_ino, antes.st_mtime_ns)
    assert sorted(p.name for p in tmp_path.iterdir()) == [nombre]


def test_guardar_no_deja_nada_a_medias_si_la_escritura_falla(tmp_path, monkeypatch):
    datos, nombre = preparado()

    def sin_disco(_descriptor):
        raise OSError("el disco se llenó")

    monkeypatch.setattr(arte_subido.os, "fsync", sin_disco)
    with pytest.raises(OSError, match="se llenó"):
        arte_subido.guardar(tmp_path, nombre, datos)
    assert list(tmp_path.iterdir()) == []


def test_el_nombre_final_no_existe_hasta_que_el_archivo_esta_entero_en_disco(tmp_path, monkeypatch):
    datos, nombre = preparado()
    pasos = []
    fsync, replace = os.fsync, os.replace

    def fsync_espia(descriptor):
        pasos.append(("fsync", (tmp_path / nombre).exists()))
        fsync(descriptor)

    def replace_espia(origen, destino):
        origen = Path(origen)
        pasos.append(("replace", origen.parent == tmp_path, origen.read_bytes() == datos, Path(destino).exists()))
        # El temporal tiene la forma que la poda reconoce como temporal.
        assert origen.name.startswith(".subiendo-") and origen.name.endswith(".tmp")
        replace(origen, destino)

    monkeypatch.setattr(arte_subido.os, "fsync", fsync_espia)
    monkeypatch.setattr(arte_subido.os, "replace", replace_espia)
    arte_subido.guardar(tmp_path, nombre, datos)
    # El contenido llega al disco con otro nombre, en la misma carpeta; luego se
    # renombra, y luego se asienta la carpeta con el nombre nuevo.
    assert pasos == [("fsync", False), ("replace", True, True, False), ("fsync", True)]


@pytest.mark.parametrize("nombre", [
    "../fuera.png", "nota.txt", "a" * 64 + ".png", "A" * 64 + ".png", "/tmp/" + "a" * 64 + ".png",
])
def test_guardar_solo_acepta_el_nombre_de_su_contenido(tmp_path, nombre):
    datos, _ = preparado()
    with pytest.raises(ValueError):
        arte_subido.guardar(tmp_path, nombre, datos)
    assert list(tmp_path.iterdir()) == []


def test_dos_guardados_a_la_vez_del_mismo_archivo_dejan_uno_entero(tmp_path):
    datos, nombre = preparado()
    salida = threading.Barrier(8)
    errores = []

    def guardar():
        salida.wait()
        try:
            arte_subido.guardar(tmp_path, nombre, datos)
        except Exception as error:  # se mira después, fuera del hilo
            errores.append(error)

    hilos = [threading.Thread(target=guardar) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert errores == []
    assert sorted(p.name for p in tmp_path.iterdir()) == [nombre]
    assert (tmp_path / nombre).read_bytes() == datos


# --- Podar ---------------------------------------------------------------------

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def con_hora(archivo: Path, hora: datetime) -> Path:
    os.utime(archivo, (hora.timestamp(), hora.timestamp()))
    return archivo


def escrito(archivo: Path, hora: datetime) -> Path:
    archivo.write_bytes(b"de otro")
    return con_hora(archivo, hora)


def guardados(carpeta, cuantos, hora=AHORA) -> list[str]:
    nombres = []
    for semilla in range(cuantos):
        datos, nombre = preparado(semilla)
        con_hora(arte_subido.guardar(carpeta, nombre, datos), hora)
        nombres.append(nombre)
    return nombres


def test_podar_borra_lo_conocido_que_no_se_conserva_aunque_sea_nuevo(tmp_path):
    nombres = guardados(tmp_path, 4)
    borrados = arte_subido.podar(tmp_path, {nombres[0], nombres[2]}, set(nombres), AHORA)
    assert sorted(borrados) == sorted([nombres[1], nombres[3]])
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([nombres[0], nombres[2]])


def test_podar_borra_los_huerfanos_de_mas_de_una_hora_y_deja_los_recientes(tmp_path):
    """Un huérfano es un archivo subido sin renglón (su subida no llegó a anotarse) o un
    temporal que quedó a medias. Uno reciente puede ser una subida en camino: no se toca."""
    hace_dos_horas, hace_un_rato = AHORA - timedelta(hours=2), AHORA - timedelta(minutes=50)
    viejo, reciente, conservado = guardados(tmp_path, 3, hace_dos_horas)
    con_hora(tmp_path / reciente, hace_un_rato)
    temporal_viejo = escrito(tmp_path / ".subiendo-abc123_x.tmp", hace_dos_horas)
    temporal_reciente = escrito(tmp_path / ".subiendo-zzz999.tmp", hace_un_rato)
    borrados = arte_subido.podar(tmp_path, {conservado}, set(), AHORA)
    assert sorted(borrados) == sorted([viejo, temporal_viejo.name])
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([reciente, conservado, temporal_reciente.name])


def test_lo_que_no_se_puede_podar_se_avisa_y_no_falla(tmp_path, caplog):
    carpeta = tmp_path / "arte_subido"
    nombre, = guardados(carpeta, 1)
    carpeta.chmod(0o500)
    try:
        if os.access(carpeta, os.W_OK):
            pytest.skip("aquí se puede escribir en una carpeta de sólo lectura (¿root?)")
        assert arte_subido.podar(carpeta, set(), {nombre}, AHORA) == []
    finally:
        carpeta.chmod(0o700)
    assert (carpeta / nombre).exists()
    assert "No se pudo podar" in caplog.text


def test_podar_sin_carpeta_no_hace_nada(tmp_path):
    assert arte_subido.podar(tmp_path / "no-existe", set(), {"a" * 64 + ".png"}, AHORA) == []


def test_podar_nunca_borra_fuera_de_la_carpeta_ni_lo_que_no_es_un_archivo_subido(tmp_path):
    carpeta = tmp_path / "arte_subido"
    carpeta.mkdir()
    hace_un_mes = AHORA - timedelta(days=30)
    fuera = escrito(tmp_path / ("b" * 64 + ".png"), hace_un_mes)
    otros = ["nota.txt", "C" * 64 + ".png", "c" * 63 + ".png", ".temporal.tmp", "subiendo-abc.tmp",
             ".subiendo-abc.tmp.png", "c" * 64 + ".png.tmp"]
    for nombre in otros:
        escrito(carpeta / nombre, hace_un_mes)
    (carpeta / ("d" * 64 + ".png")).mkdir()  # una carpeta con nombre de archivo subido
    conocidos = {*otros, "../" + fuera.name, str(fuera), "d" * 64 + ".png"}
    assert arte_subido.podar(carpeta, set(), conocidos, AHORA) == []
    assert fuera.exists()
    assert sorted(p.name for p in carpeta.iterdir()) == sorted([*otros, "d" * 64 + ".png"])


# --- Dónde vive lo subido ----------------------------------------------------------

def carpeta_configurada(entorno: dict) -> Path:
    variables = {k: v for k, v in os.environ.items() if k not in ("RUTA_BD", "RUTA_ARTE_SUBIDO")}
    salida = subprocess.run(
        [sys.executable, "-c", "import config; print(config.RUTA_ARTE_SUBIDO)"],
        cwd=RAIZ, env={**variables, **entorno}, capture_output=True, text=True, check=True,
    )
    return Path(salida.stdout.strip())


def test_lo_subido_vive_junto_a_la_base_salvo_que_se_diga_otra_carpeta(tmp_path):
    # Vacía, la variable vale como si no estuviera (y el `.env` no la pisa).
    base = {"RUTA_BD": str(tmp_path / "juego" / "tamagotchi.db"), "RUTA_ARTE_SUBIDO": ""}
    assert carpeta_configurada(base) == tmp_path / "juego" / "arte_subido"
    otra = tmp_path / "otra" / "parte"
    assert carpeta_configurada({**base, "RUTA_ARTE_SUBIDO": str(otra)}) == otra


def test_lo_subido_no_entra_en_git():
    if shutil.which("git") is None or subprocess.run(
            ["git", "rev-parse", "--git-dir"], cwd=RAIZ, capture_output=True).returncode != 0:
        pytest.skip("no es un clon de git (una copia sacada con `git archive`)")
    salida = subprocess.run(["git", "check-ignore", "-q", "arte_subido/" + "a" * 64 + ".png"], cwd=RAIZ)
    assert salida.returncode == 0


def test_sin_carpeta_propia_ninguna_prueba_escribe_en_la_de_verdad():
    """Fija la guardia de `conftest.py`: por defecto `config.RUTA_ARTE_SUBIDO` cuelga de
    un directorio que no existe y que nadie crea, así que guardar ahí falla en vez
    de escribir en la carpeta de producción (en la Pi la suite corre allí)."""
    datos, nombre = preparado()
    assert not config.RUTA_ARTE_SUBIDO.parent.exists()
    with pytest.raises(FileNotFoundError):
        arte_subido.guardar(config.RUTA_ARTE_SUBIDO, nombre, datos)
    assert not config.RUTA_ARTE_SUBIDO.parent.exists()


# --- El color ---------------------------------------------------------------------

P3 = ((0.680, 0.320), (0.265, 0.690), (0.150, 0.060))
D65 = (0.3127, 0.3290)


def _de_un_pixel(pixel, **opciones) -> Image.Image:
    """Un RGBA de 32 × 32 de un solo color, con el alfa de `pixel` en la última columna."""
    imagen = Image.new("RGBA", (32, 32), pixel)
    imagen.putpixel((31, 31), pixel[:3] + (77,))
    return imagen


def _limpia_con_perfil(imagen, perfil) -> Image.Image:
    return abierta(preparada(png_de(imagen, icc_profile=perfil))[0])


def test_un_png_con_perfil_p3_sale_en_srgb_y_sin_perfil():
    perfil = perfiles_de_color.perfil_rgb(P3, D65, 2.2)
    cuerpo = png_de(_de_un_pixel((200, 100, 50, 255)), icc_profile=perfil)
    datos, _ = preparada(cuerpo)
    assert b"iCCP" not in trozos(datos)
    salida = abierta(datos)
    rojo, verde, azul, alfa = salida.getpixel((0, 0))
    assert rojo >= 200 and verde <= 100 and azul <= 50
    assert max(abs(a - b) for a, b in zip((rojo, verde, azul), (200, 100, 50))) >= 5
    assert alfa == 255 and salida.getpixel((31, 31))[3] == 77


def test_un_png_con_perfil_srgb_sale_casi_igual():
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    original = dibujo(32, 32)
    salida = _limpia_con_perfil(original, srgb)
    assert salida.getchannel("A").tobytes() == original.getchannel("A").tobytes()
    assert all(abs(a - b) <= 1 for a, b in zip(salida.convert("RGB").tobytes(), original.convert("RGB").tobytes()))


def test_un_png_sin_perfil_sale_con_los_pixeles_intactos():
    original = dibujo(32, 32)
    assert abierta(preparada(png_de(original))[0]).tobytes() == original.tobytes()


def test_un_perfil_ilegible_se_descarta_y_se_avisa(caplog):
    original = dibujo(32, 32)
    with caplog.at_level(logging.WARNING, logger="arte_subido"):
        datos, _ = preparada(png_de(original, icc_profile=b"un perfil de color"))
    assert b"iCCP" not in trozos(datos)
    assert abierta(datos).tobytes() == original.tobytes()
    assert [r.levelno for r in caplog.records] == [logging.WARNING]


def test_un_gris_con_perfil_se_deja_como_hoy(caplog):
    # Un perfil de grises (el RGB de las pruebas con el espacio cambiado): no es RGB, no se convierte.
    perfil = bytearray(perfiles_de_color.perfil_rgb(P3, D65, 2.2))
    perfil[16:20] = b"GRAY"
    original = Image.new("L", (32, 32))
    original.putdata([(x * 8) % 256 for x in range(32 * 32)])
    with caplog.at_level(logging.WARNING, logger="arte_subido"):
        salida = _limpia_con_perfil(original, bytes(perfil))
    assert salida.tobytes() == original.convert("RGBA").tobytes()
    assert not caplog.records


def test_el_balcon_de_su_medida_vale():
    """El tope de peso deja pasar un PNG real de la medida del balcón: 2560 × 2304 y menos de 24 MB."""
    ruta = "pieza/muebles/balcon-se.png"
    assert (lugar(ruta).ancho, lugar(ruta).alto) == (2560, 2304)
    cuerpo = png_de(dibujo(2560, 2304), compress_level=1)
    assert len(cuerpo) < arte_subido.LIMITE_DE_BYTES
    original, chica = arte_subido.preparar(cuerpo, lugar(ruta))
    assert abierta(chica.datos).size == (1280, 1152)
    assert abierta(original.datos).size == (2560, 2304)


# --- Las capas de las criaturas -------------------------------------------------

CAPA = "criaturas/dragoncito/adulto/cara-feliz-se.png"


def test_una_capa_se_sube_a_1024_y_se_guarda_con_su_version_de_256():
    original = dibujo(1024, 1024)
    grande, chica = arte_subido.preparar(png_de(original), lugar(CAPA))
    assert (grande.ancho, grande.alto, chica.ancho, chica.alto) == (1024, 1024, 256, 256)
    assert abierta(grande.datos).tobytes() == original.tobytes()
    assert abierta(chica.datos).tobytes() == arte_subido.a_lo_servido(original, 4).tobytes()
    assert abierta(chica.datos).tobytes() == original.resize((256, 256), Image.LANCZOS).tobytes()
    assert grande.nombre != chica.nombre


def test_una_capa_de_la_medida_chica_se_rechaza():
    with pytest.raises(arte_subido.NoVale) as fallo:
        arte_subido.preparar(png_de(dibujo(256, 256)), lugar(CAPA))
    assert fallo.value.mensaje == "La imagen mide 256 × 256 px y esta pieza pide 1024 × 1024 px."
