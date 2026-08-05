"""Los originales de los retratos y la herramienta que los compone.

Lo que se vigila aquí es que **el repositorio se baste solo**: que estén todos
los dibujos de partida de las especies que enseñan retrato, y que la aritmética
de apilar y ampliar siga haciendo lo que hacía.

Lo que NO se vigila aquí es si los 1155 retratos de `arte/` siguen cuadrando con
sus originales: eso son cien segundos de CPU y no cabe en la suite. Para eso
está `herramientas/componer.py --comprobar`, que se pasa antes de desplegar.
"""
import pathlib

import pytest

import cosmeticos as cos
import especies as esp
import retrato
from herramientas import componer, png

RAIZ = pathlib.Path(__file__).parent.parent


# --- Que no falte ningún original ------------------------------------------

def test_cada_especie_con_retrato_tiene_sus_cinco_originales():
    """El cerrojo de `retrato.py` no puede abrirse sin los dibujos de partida.

    Si faltan, el bot sigue funcionando —los retratos ya compuestos están en
    `arte/`— pero nadie puede rehacerlos: cambiar una cara obligaría a redibujar
    la especie entera. Es justo lo que se quiso evitar trayendo `fuentes/`.
    """
    por_clave = {clave: nombre
                 for nombre, clave in componer.claves_por_nombre().items()}
    faltan = [
        componer.ruta_del_cuerpo(por_clave[clave], etapa).relative_to(RAIZ)
        for clave in retrato.CON_ETAPAS_COMPLETAS
        for etapa in esp.ETAPAS
        if not componer.ruta_del_cuerpo(por_clave[clave], etapa).is_file()
    ]
    assert not faltan, f"sin dibujo de partida: {faltan}"


def test_estan_las_caras_y_todos_los_sombreros():
    """Las capas globales se comparten: si falta una, no falla un retrato
    sino todos."""
    faltan = [ruta.relative_to(RAIZ) for ruta in (
        *(componer.FUENTES / "caras" / a for a in componer.CARAS.values()),
        *(componer.FUENTES / "sombreros" / f"{s.clave}.png" for s in cos.SOMBREROS),
    ) if not ruta.is_file()]
    assert not faltan, f"falta la capa: {faltan}"


SOMBREROS_GEO = ("aureola.png", "chistera.png", "cinta.png",
                 "corona.png", "cuernos.png", "laurel.png")


@pytest.mark.parametrize("archivo", SOMBREROS_GEO)
def test_geo_usa_sus_seis_sombreros_propios(archivo):
    assert componer.ruta_de_capa('sombreros', 'geo', archivo) == (
        componer.FUENTES / 'sombreros' / 'geo' / archivo
    )


@pytest.mark.parametrize("forma", tuple(componer.FORMA_ARCHIVO.values()))
@pytest.mark.parametrize("archivo", ("face_1.png", "face_2.png", "face_3.png"))
def test_geo_usa_sus_tres_caras_en_las_cinco_formas(archivo, forma):
    """Las mismas tres caras le sirven a las cinco formas.

    No estaba garantizado: los cinco cuerpos son dibujos distintos —una bola,
    dos cubos en tres cuartos y dos pedruscos con patas—, y que un solo par de
    ojos caiga sobre superficie en los cinco es cosa de dónde se colocaron. El
    generador admite caras por forma si algún día hace falta; hoy no hace.
    """
    assert componer.ruta_de_capa('caras', 'geo', archivo, forma) == (
        componer.FUENTES / 'caras' / 'geo' / archivo
    )


def test_otra_especie_conserva_las_capas_globales():
    assert componer.ruta_de_capa('caras', 'pyro', 'face_1.png', 'cria') == (
        componer.FUENTES / 'caras' / 'face_1.png'
    )
    assert componer.ruta_de_capa('sombreros', 'pyro', 'aureola.png') == (
        componer.FUENTES / 'sombreros' / 'aureola.png'
    )


def test_la_capa_se_busca_de_lo_concreto_a_lo_general(tmp_path, monkeypatch):
    """Por forma, por especie y global, en ese orden."""
    monkeypatch.setattr(componer, 'FUENTES', tmp_path)
    glob = tmp_path / 'caras' / 'face_1.png'
    glob.parent.mkdir()
    glob.touch()
    assert componer.ruta_de_capa('caras', 'geo', 'face_1.png', 'cria') == glob

    especie = tmp_path / 'caras' / 'geo' / 'face_1.png'
    especie.parent.mkdir()
    especie.touch()
    assert componer.ruta_de_capa('caras', 'geo', 'face_1.png', 'cria') == especie

    forma = tmp_path / 'caras' / 'geo' / 'cria' / 'face_1.png'
    forma.parent.mkdir()
    forma.touch()
    assert componer.ruta_de_capa('caras', 'geo', 'face_1.png', 'cria') == forma
    # Y la de otra forma sigue cayendo a la de la especie.
    assert componer.ruta_de_capa('caras', 'geo', 'face_1.png', 'adulto') == especie


def test_cada_especie_apila_capas_del_mismo_tamaño():
    """Apilar capas de distinto tamaño es un `ValueError` a media generación.

    Puede pasar de verdad ahora que las especies se van pasando a un lienzo de
    128: `ruta_de_capa()` cae a la capa **global** cuando la especie no tiene la
    suya, y las globales siguen siendo de 256. A una especie ya convertida a la
    que le falte un solo sombrero propio, el generador le revienta.

    Comprobarlo aquí cuesta unas decenas de cabeceras y convierte ese fallo en
    algo que se ve antes de dibujar nada.
    """
    por_clave = {clave: nombre
                 for nombre, clave in componer.claves_por_nombre().items()}
    problemas = []
    for clave in retrato.CON_ETAPAS_COMPLETAS:
        nombre = por_clave[clave]
        cuerpos = {
            componer.ruta_del_cuerpo(nombre, etapa): png.medidas(
                componer.ruta_del_cuerpo(nombre, etapa))
            for etapa in esp.ETAPAS
        }
        capas = {
            ruta: png.medidas(ruta)
            for ruta in (
                *(componer.ruta_de_capa("caras", nombre, a,
                                        componer.FORMA_ARCHIVO[etapa])
                  for a in componer.CARAS.values()
                  for etapa in esp.ETAPAS),
                *(componer.ruta_de_capa("sombreros", nombre, f"{s.clave}.png")
                  for s in cos.SOMBREROS),
            )
        }
        tamaños = set(cuerpos.values()) | set(capas.values())
        if len(tamaños) > 1:
            culpables = {r.relative_to(RAIZ).as_posix(): t
                         for r, t in {**cuerpos, **capas}.items()}
            problemas.append((clave, culpables))

    assert not problemas, f"capas de distinto tamaño: {problemas}"


def test_hay_una_cara_por_animo():
    assert set(componer.CARAS) == set(esp.ANIMOS)


def test_el_nombre_del_archivo_sale_del_nombre_de_la_especie():
    """No hay tabla que mantener, y por eso hace falta que la deducción sea
    única: dos especies que se llamaran igual sin tildes se pisarían el dibujo
    en silencio."""
    por_nombre = componer.claves_por_nombre()
    assert len(por_nombre) == len(esp.ESPECIES)


def test_las_formas_del_archivo_cubren_las_cinco_etapas():
    assert set(componer.FORMA_ARCHIVO) == set(esp.ETAPAS)


# --- La aritmética de componer ---------------------------------------------

def lisa(ancho, alto, rgba):
    imagen = png.Imagen.vacia(ancho, alto)
    for y in range(alto):
        for x in range(ancho):
            imagen.poner(x, y, rgba)
    return imagen


def test_lo_opaco_de_arriba_tapa_lo_de_abajo():
    fondo = lisa(2, 2, (255, 0, 0, 255))
    capa = lisa(2, 2, (0, 0, 255, 255))
    assert png.encima(fondo, capa).pixel(0, 0) == (0, 0, 255, 255)


def test_lo_transparente_de_arriba_no_pinta_nada():
    fondo = lisa(2, 2, (255, 0, 0, 255))
    assert png.encima(fondo, lisa(2, 2, (0, 0, 255, 0))).pixel(0, 0) == (255, 0, 0, 255)


def test_sobre_el_vacio_la_capa_queda_tal_cual():
    """Es el caso del sombrero que sobresale de la cabeza: fuera del cuerpo no
    hay con qué mezclar, y mezclar con negro transparente lo ensuciaría."""
    capa = lisa(2, 2, (10, 200, 30, 128))
    assert png.encima(png.Imagen.vacia(2, 2), capa).pixel(0, 0) == (10, 200, 30, 128)


def test_capas_de_distinto_tamaño_no_se_mezclan():
    with pytest.raises(ValueError):
        png.encima(lisa(2, 2, (0, 0, 0, 255)), lisa(3, 3, (0, 0, 0, 255)))


def test_el_margen_es_el_que_llevan_los_retratos_ya_compuestos():
    """El número va clavado a propósito, no deducido de la constante.

    El margen no es una preferencia: es parte de cómo están hechos los 1155 PNG
    que hay en `arte/`. Cambiarlo no rompe nada al ejecutar —el bot seguiría
    sirviendo los de antes— pero deja los retratos y su receta contando cosas
    distintas, y el descuadre sólo aparecería al regenerar meses después. Si de
    verdad se quiere otro margen: cámbialo, regenera las especies con
    `herramientas/componer.py` y actualiza este número.
    """
    assert componer.MARGEN == 2


def test_recortar_no_amplia_ni_mueve_el_pixel():
    """1:1. Un píxel del original es un píxel del retrato, en su sitio.

    Esto ampliaba ×2 cuando los originales eran de 256. Con el pixelart de 128
    lo que se dibuja es lo que se ve; si algún día vuelve a ampliar, el dibujo
    dejará de decidirse píxel a píxel y este test lo cazará.
    """
    imagen = png.Imagen.vacia(8, 8)
    imagen.poner(4, 4, (10, 20, 30, 255))

    recorte = componer.recortar(imagen, (4, 4, 4, 4))

    lado = 1 + 2 * componer.MARGEN
    assert (recorte.ancho, recorte.alto) == (lado, lado)
    colores = {recorte.pixel(x, y) for y in range(lado) for x in range(lado)}
    assert colores == {(10, 20, 30, 255), (0, 0, 0, 0)}
    assert recorte.pixel(componer.MARGEN, componer.MARGEN) == (10, 20, 30, 255)
    # Y sólo ése: nada de cuadrados de 2×2.
    assert sum(1 for y in range(lado) for x in range(lado)
               if recorte.pixel(x, y)[3]) == 1


def test_el_margen_sobrante_no_se_sale_del_lienzo():
    """Un dibujo pegado al borde pide margen donde no hay lienzo. Eso es
    transparente, no un error ni un píxel tomado del otro extremo."""
    imagen = png.Imagen.vacia(4, 4)
    imagen.poner(0, 0, (255, 255, 255, 255))

    recorte = componer.recortar(imagen, (0, 0, 0, 0))

    assert recorte.pixel(0, 0) == (0, 0, 0, 0)
    assert recorte.pixel(componer.MARGEN, componer.MARGEN) == (255, 255, 255, 255)


# --- El códec ---------------------------------------------------------------

def test_el_codec_lee_lo_que_escribe(tmp_path):
    original = png.Imagen.vacia(5, 3)
    for x in range(5):
        original.poner(x, 1, (x * 40, 255 - x * 40, 128, 200))

    ruta = tmp_path / "prueba.png"
    png.escribir(original, ruta)
    vuelta = png.leer(ruta)

    assert (vuelta.ancho, vuelta.alto) == (5, 3)
    assert vuelta.pixeles == original.pixeles


def test_lo_que_no_es_png_se_rechaza(tmp_path):
    ruta = tmp_path / "no.png"
    ruta.write_bytes(b"esto no es una imagen")
    with pytest.raises(ValueError):
        png.leer(ruta)
