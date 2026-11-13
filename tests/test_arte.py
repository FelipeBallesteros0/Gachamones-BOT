import json
import re
from collections import Counter

from PIL import Image

import avatar
import casas
import cosmeticos
import objetos
from web import arte, pueblo


def test_el_contrato_tiene_sus_199_piezas():
    piezas = arte.piezas()
    assert Counter(p.familia for p in piezas) == {
        "pueblo": 1, "lugares": 9, "escenas": 9, "avatar": 114, "efectos": 4, "iconos": 62,
    }
    assert len({p.ruta for p in piezas}) == len(piezas)
    rutas = {p.ruta: (p.ancho, p.alto) for p in piezas}
    assert rutas["pueblo/fondo.png"] == (2 * pueblo.DATOS["ancho"], 2 * pueblo.DATOS["alto"])
    assert rutas["pueblo/lugares/plaza.png"] == (160, 160)
    assert rutas["escenas/cementerio.png"] == (720, 480)
    assert rutas["avatar/cuerpo/oscura-paso2.png"] == (48, 84)
    assert rutas["avatar/pelo/coleta-azul-quieto.png"] == (48, 84)
    assert rutas["avatar/ropa/overol-paso1.png"] == (48, 84)
    assert rutas["efectos/marca.png"] == (32, 32)
    assert rutas["efectos/sombra.png"] == (32, 32)


def test_el_contrato_sale_de_los_catalogos():
    rutas = {p.ruta for p in arte.piezas()}
    for lugar in pueblo.LUGARES:
        assert f"pueblo/lugares/{lugar}.png" in rutas and f"escenas/{lugar}.png" in rutas
    for pose in arte.POSES:
        for piel in avatar.PIELES:
            assert f"avatar/cuerpo/{piel.clave}-{pose}.png" in rutas
        for ropa in avatar.ROPAS:
            assert f"avatar/ropa/{ropa.clave}-{pose}.png" in rutas
        for pelo in avatar.PELOS:
            for color in avatar.COLORES_DE_PELO:
                assert f"avatar/pelo/{pelo.clave}-{color.clave}-{pose}.png" in rutas


def test_cada_pieza_esta_y_mide_lo_que_debe():
    faltan, mal = [], []
    for pieza in arte.piezas():
        ruta = arte.RAIZ / pieza.ruta
        if not ruta.is_file():
            faltan.append(pieza.ruta)
            continue
        with Image.open(ruta) as imagen:
            if imagen.format != "PNG" or imagen.size != (pieza.ancho, pieza.alto):
                mal.append((pieza.ruta, imagen.format, imagen.size))
    assert not faltan, f"faltan dibujos: {faltan}"
    assert not mal, f"no miden lo que dice el contrato: {mal}"


def test_no_hay_dibujos_que_el_contrato_no_conozca():
    en_disco = {p.relative_to(arte.RAIZ).as_posix() for p in arte.RAIZ.rglob("*") if p.is_file()}
    assert en_disco == {p.ruta for p in arte.piezas()}


def test_el_cliente_recibe_el_mismo_contrato():
    escrito = json.loads((arte.RAIZ.parent / "datos" / "arte.json").read_text(encoding="utf-8"))
    assert escrito == arte.como_json()


def test_generar_no_pisa_un_dibujo_que_ya_esta(tmp_path, monkeypatch):
    from herramientas import rellenos

    monkeypatch.setattr(arte, "RAIZ", tmp_path / "arte")
    (tmp_path / "datos").mkdir()
    escritas = rellenos.generar()
    assert len(escritas) == 199
    corazon = arte.RAIZ / "efectos" / "corazon.png"
    propio = Image.new("RGBA", (32, 32), (1, 2, 3, 255))
    propio.save(corazon)
    assert rellenos.generar() == []
    with Image.open(corazon) as imagen:
        assert imagen.getpixel((0, 0)) == (1, 2, 3, 255)
    assert len(rellenos.generar(todo=True)) == 199


def _relleno(ruta: str) -> Image.Image:
    """Lo que `herramientas/rellenos.py` dibuja para esa pieza, sin mirar el archivo del repo.

    Las pruebas de los rellenos miran esto: el día que un dibujo de verdad
    reemplace a su relleno en el repo, no tienen por qué fallar.
    """
    from herramientas import rellenos

    pieza = next(p for p in arte.piezas() if p.ruta == ruta)
    return rellenos._dibujar(pieza).convert("RGBA")


def test_dos_lugares_no_tienen_el_mismo_relleno():
    lugares = [_relleno(f"pueblo/lugares/{l}.png").tobytes() for l in pueblo.LUGARES]
    escenas = [_relleno(f"escenas/{l}.png").tobytes() for l in pueblo.LUGARES]
    assert len(set(lugares)) == 9 and len(set(escenas)) == 9


def test_el_fondo_de_un_lugar_y_de_una_capa_es_transparente():
    for ruta in ("pueblo/lugares/casa.png", "avatar/pelo/corto-negro-quieto.png", "efectos/corazon.png",
                 "efectos/sombra.png"):
        with Image.open(arte.RAIZ / ruta) as imagen:
            assert imagen.convert("RGBA").getpixel((0, 0))[3] == 0, ruta


def test_el_relleno_de_la_sombra_es_una_elipse_achatada_oscura_y_translucida_al_centro():
    from herramientas import rellenos

    sombra = rellenos._efecto("sombra", arte.EFECTO[0])
    izquierda, arriba, derecha, abajo = sombra.getbbox()
    lado = arte.EFECTO[0]
    assert (izquierda, arriba) == (lado - derecha, lado - abajo)
    assert derecha - izquierda > 2 * (abajo - arriba)
    r, g, b, a = sombra.getpixel((lado // 2, lado // 2))
    assert max(r, g, b) < 60 and 0 < a < 255


def _rutas_de_iconos():
    return (
        [f"iconos/objetos/{c}.png" for c in objetos.CATALOGO]
        + [f"iconos/cosmeticos/{c}.png" for c in cosmeticos.CATALOGO]
        + [f"iconos/muebles/{c}.png" for c in casas.MUEBLES]
        + [f"iconos/casas/{c}.png" for c in casas.CATALOGO]
    )


def test_cada_cosa_que_se_compra_o_se_lleva_tiene_su_icono():
    rutas = {p.ruta: p for p in arte.piezas()}
    esperadas = _rutas_de_iconos()
    assert len(esperadas) == 62
    for ruta in esperadas:
        assert (rutas[ruta].ancho, rutas[ruta].alto, rutas[ruta].familia) == (48, 48, "iconos")


def test_las_rutas_de_los_iconos_pasan_el_filtro_del_cliente():
    forma = re.compile(r"^[a-z0-9_]+(-[a-z0-9_]+)*(/[a-z0-9_]+(-[a-z0-9_]+)*)*\.png$")
    for ruta in _rutas_de_iconos():
        assert forma.match(ruta), ruta


def test_los_rellenos_de_iconos_se_distinguen_y_tienen_fondo_transparente():
    por_grupo = {}
    for ruta in _rutas_de_iconos():
        grupo = ruta.split("/")[1]
        imagen = _relleno(ruta)
        assert imagen.getpixel((0, 0))[3] == 0, ruta
        assert imagen.getpixel((24, 5))[3] == 255, ruta
        por_grupo.setdefault(grupo, []).append((ruta, imagen.tobytes(), imagen.getpixel((6, 6))))
    for grupo, items in por_grupo.items():
        assert len({b for _, b, _ in items}) == len(items), grupo
    colores = {items[0][2] for items in por_grupo.values()}
    assert len(colores) == 4
    assert all(len({c for _, _, c in items}) == 1 for items in por_grupo.values())
