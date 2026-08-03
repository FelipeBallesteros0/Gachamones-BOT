"""Los originales de los retratos y la herramienta que los compone.

Lo que se vigila aquí es que **el repositorio se baste solo**: que estén todos
los dibujos de partida de las especies que enseñan retrato, y que la aritmética
de apilar y ampliar siga haciendo lo que hacía.

Lo que NO se vigila aquí es si los 1155 retratos de `arte/` siguen cuadrando con
sus originales: eso son cien segundos de CPU y no cabe en la suite. Para eso
está `herramientas/componer.py --comprobar`, que se pasa antes de desplegar.
"""
import pathlib
import sys

import pytest

import cosmeticos as cos
import especies as esp
import retrato

RAIZ = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))

import componer  # noqa: E402
import png  # noqa: E402


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
    """Las capas se comparten entre especies: si falta una, no falla un retrato
    sino todos."""
    faltan = [ruta.relative_to(RAIZ) for ruta in (
        *(componer.FUENTES / "caras" / a for a in componer.CARAS.values()),
        *(componer.FUENTES / "sombreros" / f"{s.clave}.png" for s in cos.SOMBREROS),
    ) if not ruta.is_file()]
    assert not faltan, f"falta la capa: {faltan}"


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


def test_ampliar_al_doble_repite_el_pixel_sin_inventar_colores():
    """Vecino más cercano: cada píxel se convierte en un cuadrado de 2×2 del
    mismo color. Es lo que deja ampliar el arte sin emborronarlo, y sólo vale
    porque los dibujos no tienen bordes suavizados."""
    imagen = png.Imagen.vacia(8, 8)
    imagen.poner(4, 4, (10, 20, 30, 255))

    doble = componer.recortar_y_doblar(imagen, (4, 4, 4, 4))

    lado = (1 + 2 * componer.MARGEN) * 2
    assert (doble.ancho, doble.alto) == (lado, lado)
    colores = {doble.pixel(x, y) for y in range(lado) for x in range(lado)}
    assert colores == {(10, 20, 30, 255), (0, 0, 0, 0)}
    esquina = componer.MARGEN * 2
    assert all(doble.pixel(esquina + dx, esquina + dy) == (10, 20, 30, 255)
               for dx in (0, 1) for dy in (0, 1))


def test_el_margen_sobrante_no_se_sale_del_lienzo():
    """Un dibujo pegado al borde —Duskhouse adulto grande ocupa 255 de 256— pide
    margen donde no hay lienzo. Eso es transparente, no un error ni un píxel
    tomado del otro extremo."""
    imagen = png.Imagen.vacia(4, 4)
    imagen.poner(0, 0, (255, 255, 255, 255))

    doble = componer.recortar_y_doblar(imagen, (0, 0, 0, 0))

    assert doble.pixel(0, 0) == (0, 0, 0, 0)
    assert doble.pixel(componer.MARGEN * 2, componer.MARGEN * 2) == (255, 255, 255, 255)


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
