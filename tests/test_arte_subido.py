"""Las reglas de una subida del dibujante: qué PNG vale, cómo sale limpio, cómo se guarda y qué se poda.

Los PNG se fabrican aquí, con Pillow o a mano (`png_crudo`) para lo que Pillow no
sabe escribir: 16 bits y grises de pocos bits con transparencia. Nunca se toca
el arte del repo.
"""
import hashlib
import io
import os
import struct
import subprocess
import sys
import threading
import warnings
import zlib
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

import arte_subido
import config
from herramientas import pieza as herramienta_pieza
from web import arte

RAIZ = Path(__file__).resolve().parent.parent
FIRMA = b"\x89PNG\r\n\x1a\n"
CORAZON = "efectos/corazon.png"   # 32 × 32, familia `efectos`
SUELO = "pieza/suelo.png"         # 512 × 256, familia `pieza`: se acepta también 1024 × 512
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


def pieza(ruta):
    encontrada = arte_subido.pieza_de(ruta)
    assert encontrada is not None
    return encontrada


def abierta(datos: bytes) -> Image.Image:
    imagen = Image.open(io.BytesIO(datos))
    imagen.load()
    return imagen


# --- Qué es una pieza ---------------------------------------------------------

def test_una_ruta_del_contrato_es_su_pieza():
    corazon = arte_subido.pieza_de(CORAZON)
    assert (corazon.ruta, corazon.ancho, corazon.alto, corazon.familia) == (CORAZON, 32, 32, "efectos")


@pytest.mark.parametrize("ruta", [
    "pieza/inventada.png", "efectos/corazon", "efectos/../efectos/corazon.png", "../efectos/corazon.png",
    "/efectos/corazon.png", "efectos\\corazon.png", "efectos/corazon.png/", "EFECTOS/CORAZON.PNG",
    "efectos//corazon.png", "", "efectos/corazon.png\x00",
])
def test_lo_que_no_esta_en_el_contrato_no_es_una_pieza(ruta):
    assert arte_subido.pieza_de(ruta) is None


def test_las_medidas_del_contrato_son_las_de_cada_pieza():
    medidas = arte_subido.medidas()
    assert medidas == {p.ruta: (p.ancho, p.alto) for p in arte.piezas()}
    assert medidas[CORAZON] == (32, 32) and medidas[SUELO] == (512, 256)


# --- Lo que vale y cómo sale -----------------------------------------------------

def test_un_png_de_su_medida_sale_limpio_y_con_el_nombre_de_su_contenido():
    original = dibujo(32, 32)
    datos, nombre = arte_subido.preparar(png_de(original), pieza(CORAZON))
    assert nombre == hashlib.sha256(datos).hexdigest() + ".png"
    limpia = abierta(datos)
    assert limpia.format == "PNG" and limpia.mode == "RGBA" and limpia.size == (32, 32)
    assert limpia.tobytes() == original.tobytes()


def test_dos_subidas_iguales_dan_el_mismo_nombre():
    cuerpo = png_de(dibujo(32, 32))
    assert arte_subido.preparar(cuerpo, pieza(CORAZON)) == arte_subido.preparar(cuerpo, pieza(CORAZON))
    # La misma imagen guardada de otra forma (otra compresión, otro modo) también.
    otra = png_de(dibujo(32, 32), compress_level=0)
    assert otra != cuerpo
    assert arte_subido.preparar(otra, pieza(CORAZON))[1] == arte_subido.preparar(cuerpo, pieza(CORAZON))[1]


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
    datos, nombre = arte_subido.preparar(cuerpo, pieza(CORAZON))
    assert set(trozos(datos)) <= {b"IHDR", b"IDAT", b"IEND"}
    limpia = abierta(datos)
    assert limpia.info == {} and limpia.tobytes() == original.tobytes()
    assert nombre == arte_subido.preparar(png_de(original), pieza(CORAZON))[1]


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
    datos, _ = arte_subido.preparar(cuerpo, pieza(CORAZON))
    limpia = abierta(datos)
    assert limpia.mode == "RGBA" and limpia.size == (32, 32)
    for y in (0, 31):
        assert [limpia.getpixel((x, y)) for x in range(len(esperado))] == esperado


def test_el_doble_de_una_pieza_de_la_pieza_se_reduce_como_lo_reduce_la_herramienta(tmp_path):
    original = dibujo(1024, 512)
    archivo = tmp_path / "suelo.png"
    original.save(archivo)
    datos, _ = arte_subido.preparar(archivo.read_bytes(), pieza(SUELO))
    limpia = abierta(datos)
    assert limpia.size == (512, 256)
    assert limpia.tobytes() == herramienta_pieza.reducida(archivo).tobytes()


def test_una_pieza_de_la_pieza_tambien_vale_a_su_medida_y_entonces_no_se_reduce():
    original = dibujo(512, 256)
    datos, _ = arte_subido.preparar(png_de(original), pieza(SUELO))
    assert abierta(datos).tobytes() == original.tobytes()


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
        arte_subido.preparar(cuerpo, pieza(ruta))
    assert rechazo.value.mensaje == str(rechazo.value)
    return rechazo.value.mensaje


def test_una_imagen_con_la_medida_de_otra_pieza_se_rechaza_diciendo_la_esperada_y_la_recibida():
    mensaje = no_vale(png_de(dibujo(48, 48)))
    assert "48 × 48 px" in mensaje and "32 × 32 px" in mensaje


def test_en_la_pieza_el_rechazo_dice_las_dos_medidas_que_valen():
    mensaje = no_vale(png_de(dibujo(256, 128)), SUELO)
    assert "256 × 128 px" in mensaje and "512 × 256 px" in mensaje and "1024 × 512 px" in mensaje


def test_el_doble_solo_vale_en_la_familia_de_la_pieza():
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


def test_un_png_de_4_mb_vale_y_uno_de_un_byte_mas_no():
    assert arte_subido.LIMITE_DE_BYTES == 4 * 1024 * 1024
    datos, _ = arte_subido.preparar(png_que_pesa(arte_subido.LIMITE_DE_BYTES), pieza(CORAZON))
    assert len(datos) < 1000
    assert "4 MB" in no_vale(png_que_pesa(arte_subido.LIMITE_DE_BYTES + 1))


def test_una_bomba_de_descompresion_se_rechaza_por_su_medida_sin_abrirla():
    bomba = (FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", 100_000, 100_000, 8, 6, 0, 0, 0))
             + trozo(b"IDAT", zlib.compress(b"\x00" * 1000)) + trozo(b"IEND", b""))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mensaje = no_vale(bomba)
    assert "100000 × 100000 px" in mensaje


# --- Guardar --------------------------------------------------------------------

def preparado(semilla=0) -> tuple[bytes, str]:
    imagen = dibujo(32, 32)
    imagen.putpixel((0, 0), (semilla, 0, 0, 255))
    return arte_subido.preparar(png_de(imagen), pieza(CORAZON))


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

def test_podar_borra_solo_lo_que_no_se_conserva(tmp_path):
    guardados = [preparado(semilla) for semilla in range(4)]
    nombres = [nombre for _, nombre in guardados]
    for datos, nombre in guardados:
        arte_subido.guardar(tmp_path, nombre, datos)
    borrados = arte_subido.podar(tmp_path, nombres, {nombres[0], nombres[2]})
    assert sorted(borrados) == sorted([nombres[1], nombres[3]])
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([nombres[0], nombres[2]])


def test_podar_no_falla_si_un_archivo_ya_no_estaba(tmp_path):
    _, nombre = preparado()
    assert arte_subido.podar(tmp_path, [nombre], set()) == []


def test_podar_nunca_borra_fuera_de_la_carpeta_ni_lo_que_no_es_un_archivo_subido(tmp_path):
    carpeta = tmp_path / "arte_subido"
    carpeta.mkdir()
    fuera = tmp_path / ("b" * 64 + ".png")
    fuera.write_bytes(b"de otro")
    otros = ["nota.txt", "C" * 64 + ".png", "c" * 63 + ".png", ".temporal.tmp"]
    for nombre in otros:
        (carpeta / nombre).write_bytes(b"de otro")
    candidatos = [*otros, "../" + fuera.name, str(fuera), "../arte_subido/nota.txt"]
    assert arte_subido.podar(carpeta, candidatos, set()) == []
    assert fuera.exists()
    assert sorted(p.name for p in carpeta.iterdir()) == sorted(otros)


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
