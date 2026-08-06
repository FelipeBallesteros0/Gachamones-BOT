"""Las capas de los retratos: que estén todas y que se elija la que toca.

Antes esto vivía en `herramientas/componer.py`, que armaba los 1155 retratos de
antemano. Ahora se componen al vuelo y la lógica está en `retrato`, pero lo que
hay que vigilar es lo mismo: que no falte ningún dibujo de partida y que la
búsqueda de capas —por forma, por especie, global— elija la correcta.
"""
import pathlib

import pytest
from PIL import Image

import cosmeticos as cos
import especies as esp
import retrato

RAIZ = pathlib.Path(__file__).parent.parent
FORMAS = tuple(retrato.FORMA_ARCHIVO.values())


@pytest.fixture(autouse=True)
def sin_memoria():
    """Las cachés de `retrato` guardan rutas y cajas; varias pruebas cambian el
    suelo bajo sus pies con `monkeypatch`, así que se vacían entre una y otra."""
    retrato.olvidar()
    yield
    retrato.olvidar()


# --- Que no falte ningún dibujo de partida ---------------------------------

def test_cada_especie_con_retrato_tiene_sus_cinco_cuerpos():
    """El cerrojo de `CON_ETAPAS_COMPLETAS` no puede abrirse sin los dibujos.

    Y ahora importa más que antes: no hay retratos ya compuestos de respaldo, así
    que un cuerpo que falte es una ficha que revienta al pintarse.
    """
    faltan = [
        retrato._ruta_del_cuerpo(clave, etapa).relative_to(RAIZ)
        for clave in retrato.CON_ETAPAS_COMPLETAS
        for etapa in esp.ETAPAS
        if not retrato._ruta_del_cuerpo(clave, etapa).is_file()
    ]
    assert not faltan, f"sin dibujo de partida: {faltan}"


def test_estan_las_caras_y_los_sombreros_globales():
    """Las capas globales son el último recurso de la búsqueda: si falta una, no
    falla un retrato sino todos los de las especies que no tengan la suya."""
    faltan = [ruta.relative_to(RAIZ) for ruta in (
        *(retrato.FUENTES / "caras" / a for a in retrato.CARAS.values()),
        *(retrato.FUENTES / "sombreros" / f"{s.clave}.png" for s in cos.SOMBREROS),
    ) if not ruta.is_file()]
    assert not faltan, f"falta la capa global: {faltan}"


def test_hay_una_cara_por_animo():
    assert set(retrato.CARAS) == set(esp.ANIMOS)


def test_las_formas_del_archivo_cubren_las_cinco_etapas():
    assert set(retrato.FORMA_ARCHIVO) == set(esp.ETAPAS)


def test_el_nombre_del_archivo_sale_del_nombre_de_la_especie():
    """No hay tabla que mantener, y por eso hace falta que la deducción sea
    única: dos especies que se llamaran igual sin tildes se pisarían el dibujo
    en silencio."""
    nombres = {retrato._nombre_de_archivo(c) for c in esp.ESPECIES}
    assert len(nombres) == len(esp.ESPECIES)
    assert retrato._nombre_de_archivo("brote") == "magora"
    assert retrato._nombre_de_archivo("swampdon") == "swampdon"   # sin la tilde


# --- Que se elija la capa correcta -----------------------------------------

@pytest.mark.parametrize("archivo", [f"{s.clave}.png" for s in cos.SOMBREROS])
def test_geo_usa_sus_seis_sombreros_propios(archivo):
    assert retrato._ruta_de_capa("sombreros", "pedrusco", archivo, "adulto") == (
        retrato.FUENTES / "sombreros" / "geo" / archivo
    )


@pytest.mark.parametrize("forma", FORMAS)
@pytest.mark.parametrize("archivo", ("face_1.png", "face_2.png", "face_3.png"))
def test_geo_usa_sus_tres_caras_en_las_cinco_formas(archivo, forma):
    """Las mismas tres caras le sirven a las cinco formas de Geo, porque están
    colocadas donde las cinco piedras tienen superficie."""
    assert retrato._ruta_de_capa("caras", "pedrusco", archivo, forma) == (
        retrato.FUENTES / "caras" / "geo" / archivo
    )


@pytest.mark.parametrize("forma", FORMAS)
@pytest.mark.parametrize("carpeta,archivo", [
    ("caras", "face_1.png"), ("caras", "face_2.png"), ("caras", "face_3.png"),
    *(("sombreros", f"{s.clave}.png") for s in cos.SOMBREROS),
])
def test_piollito_y_magora_llevan_capas_propias_en_cada_forma(carpeta, archivo, forma):
    """Estas dos cambian de silueta de verdad al evolucionar —Piollito pasa de
    bola con pelusa a pájaro con las alas abiertas, Magora de brote en maceta a
    mandrágora—, y ni los ojos ni la coronilla quedan a la misma altura. Por eso
    repiten las nueve capas en las cinco formas, sombreros incluidos."""
    for clave, nombre in (("pollito", "piollito"), ("brote", "magora")):
        assert retrato._ruta_de_capa(carpeta, clave, archivo, forma) == (
            retrato.FUENTES / carpeta / nombre / forma / archivo
        )


def test_una_especie_sin_capas_propias_usa_las_globales():
    assert retrato._ruta_de_capa("caras", "chispa", "face_1.png", "cria") == (
        retrato.FUENTES / "caras" / "face_1.png"
    )
    assert retrato._ruta_de_capa("sombreros", "chispa", "aureola.png", "cria") == (
        retrato.FUENTES / "sombreros" / "aureola.png"
    )


def test_la_capa_se_busca_de_lo_concreto_a_lo_general(tmp_path, monkeypatch):
    """Por forma, por especie y global, en ese orden."""
    monkeypatch.setattr(retrato, "FUENTES", tmp_path)
    glob = tmp_path / "caras" / "face_1.png"
    glob.parent.mkdir()
    glob.touch()
    assert retrato._ruta_de_capa("caras", "pedrusco", "face_1.png", "cria") == glob

    especie = tmp_path / "caras" / "geo" / "face_1.png"
    especie.parent.mkdir()
    especie.touch()
    assert retrato._ruta_de_capa("caras", "pedrusco", "face_1.png", "cria") == especie

    forma = tmp_path / "caras" / "geo" / "cria" / "face_1.png"
    forma.parent.mkdir()
    forma.touch()
    assert retrato._ruta_de_capa("caras", "pedrusco", "face_1.png", "cria") == forma
    # Y la de otra forma sigue cayendo a la de la especie.
    assert retrato._ruta_de_capa("caras", "pedrusco", "face_1.png", "adulto") == especie


def test_cada_especie_apila_capas_del_mismo_tamaño():
    """Apilar capas de distinto tamaño es un `ValueError` al pintar la ficha.

    Puede pasar de verdad: la búsqueda cae a la capa **global** cuando la
    especie no tiene la suya, así que a una especie dibujada en otro lienzo a la
    que le falte un solo sombrero propio le revienta el retrato. Antes eso se
    veía al generar; ahora se vería en la cara de quien pulsa un botón.
    """
    problemas = []
    for clave in retrato.CON_ETAPAS_COMPLETAS:
        medidas = {}
        for etapa in esp.ETAPAS:
            forma = retrato.FORMA_ARCHIVO[etapa]
            rutas = [retrato._ruta_del_cuerpo(clave, etapa)]
            rutas += [retrato._ruta_de_capa("caras", clave, a, forma)
                      for a in retrato.CARAS.values()]
            rutas += [retrato._ruta_de_capa("sombreros", clave, f"{s.clave}.png", forma)
                      for s in cos.SOMBREROS]
            for ruta in rutas:
                with Image.open(ruta) as im:
                    medidas[ruta.relative_to(RAIZ).as_posix()] = im.size
        if len(set(medidas.values())) > 1:
            problemas.append((clave, medidas))
    assert not problemas, f"capas de distinto tamaño: {problemas}"


# --- La receta de componer -------------------------------------------------

def test_el_margen_es_el_que_llevan_los_retratos_de_siempre():
    """El número va clavado a propósito, no deducido de la constante.

    El margen es parte de cómo se ven las fichas desde el primer día. Cambiarlo
    no rompe nada al ejecutar, sólo mueve un poco todos los bichos dentro de su
    marco, y eso es de las cosas que nadie nota hasta que las compara.
    """
    assert retrato.MARGEN == 2


def test_la_caja_la_comparten_las_veintiuna_combinaciones():
    """Si cada combinación se recortara a su propia silueta, cambiar de humor o
    ponerse un sombrero movería al bicho dentro del embed."""
    import io
    tamaños = set()
    for animo in esp.ANIMOS:
        for sombrero in [retrato.SIN_SOMBRERO] + [s.clave for s in cos.SOMBREROS]:
            datos = retrato._armar("brote", "adulto_grande", animo, sombrero)
            with Image.open(io.BytesIO(datos)) as im:
                tamaños.add(im.size)
    assert len(tamaños) == 1, tamaños


def test_la_caja_encierra_todas_las_capas_con_su_margen():
    """La caja sale de unir las capas sueltas y no de componer las veintiuna,
    que es lo mismo y cuesta la décima parte. Aquí se comprueba que de verdad
    es lo mismo: ninguna capa se sale."""
    clave, etapa = "brote", "adulto"
    x0, y0, x1, y1 = retrato._caja(clave, etapa)
    forma = retrato.FORMA_ARCHIVO[etapa]
    rutas = [retrato._ruta_del_cuerpo(clave, etapa)]
    rutas += [retrato._ruta_de_capa("caras", clave, a, forma)
              for a in retrato.CARAS.values()]
    rutas += [retrato._ruta_de_capa("sombreros", clave, f"{s.clave}.png", forma)
              for s in cos.SOMBREROS]
    for ruta in rutas:
        with Image.open(ruta) as im:
            caja = im.convert("RGBA").getchannel("A").getbbox()
        assert caja is not None and (
            x0 <= caja[0] and y0 <= caja[1] and caja[2] <= x1 and caja[3] <= y1
        ), (ruta.name, caja, (x0, y0, x1, y1))
    # Y el margen está de verdad: la caja sobra por los cuatro lados.
    unida = [10 ** 9, 10 ** 9, -1, -1]
    for ruta in rutas:
        with Image.open(ruta) as im:
            c = im.convert("RGBA").getchannel("A").getbbox()
        unida = [min(unida[0], c[0]), min(unida[1], c[1]),
                 max(unida[2], c[2]), max(unida[3], c[3])]
    assert (x0, y0, x1, y1) == (unida[0] - retrato.MARGEN, unida[1] - retrato.MARGEN,
                                unida[2] + retrato.MARGEN, unida[3] + retrato.MARGEN)


def test_el_retrato_sale_al_doble_de_la_caja():
    """Discord no agranda la imagen de un embed más allá de su tamaño real, así
    que el ×2 no es un adorno: es lo que hace que el bicho se vea."""
    import io
    x0, y0, x1, y1 = retrato._caja("brote", "adulto")
    datos = retrato._armar("brote", "adulto", esp.NORMAL, retrato.SIN_SOMBRERO)
    with Image.open(io.BytesIO(datos)) as im:
        assert im.size == ((x1 - x0) * 2, (y1 - y0) * 2)
