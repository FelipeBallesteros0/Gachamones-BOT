"""El arte de la pieza del departamento: su familia en el contrato, sus tamaños y la herramienta que reduce originales."""

import pytest
from PIL import Image

import departamento as dep
from herramientas import pieza
from web import arte


def test_la_pieza_tiene_su_familia_en_el_contrato():
    familia = [p for p in arte.piezas() if p.familia == "pieza"]
    rutas = {p.ruta for p in familia}
    assert {"pieza/suelo.png", "pieza/pared-izquierda.png", "pieza/pared-derecha.png"} <= rutas
    de_suelo = [m for m in dep.MUEBLES.values() if m.capa != dep.PARED]
    de_pared = [m for m in dep.MUEBLES.values() if m.capa == dep.PARED]
    assert len(familia) == 3 + 4 * len(de_suelo) + 2 * len(de_pared)
    for m in de_suelo:
        assert {f"pieza/muebles/{m.clave}-{o}.png" for o in arte.ORIENTACIONES} <= rutas
    for m in de_pared:
        assert {f"pieza/muebles/{m.clave}-se.png", f"pieza/muebles/{m.clave}-so.png"} <= rutas
        assert f"pieza/muebles/{m.clave}-no.png" not in rutas
        assert f"pieza/muebles/{m.clave}-ne.png" not in rutas


@pytest.mark.parametrize("ruta, tamano", [
    ("pieza/suelo.png", (512, 256)), ("pieza/pared-izquierda.png", (256, 640)),
    ("pieza/muebles/maceta-se.png", (512, 768)), ("pieza/muebles/felpudo-no.png", (512, 256)),
    ("pieza/muebles/cama_sencilla-so.png", (768, 896)), ("pieza/muebles/fuente-ne.png", (1024, 1024)),
    ("pieza/muebles/alfombra-se.png", (1024, 512)), ("pieza/muebles/cuadro-se.png", (256, 640)),
    ("pieza/muebles/cortinas-so.png", (512, 768)),
])
def test_cada_dibujo_mide_lo_que_ocupa(ruta, tamano):
    p = next(p for p in arte.piezas() if p.ruta == ruta)
    assert (p.ancho, p.alto) == tamano


def test_los_originales_miden_el_doble_de_lo_servido():
    servidas = {p.ruta: p for p in arte.piezas() if p.familia == "pieza"}
    originales = arte.originales_de_la_pieza()
    assert {o.ruta for o in originales} == set(servidas)
    for o in originales:
        assert (o.ancho, o.alto) == (servidas[o.ruta].ancho * 2, servidas[o.ruta].alto * 2)
    assert next(o for o in originales if o.ruta == "pieza/suelo.png").ancho == 1024


def test_cada_dibujo_de_la_pieza_tiene_su_archivo_del_tamano_justo():
    for p in (p for p in arte.piezas() if p.familia == "pieza"):
        with Image.open(arte.RAIZ / p.ruta) as imagen:
            assert imagen.size == (p.ancho, p.alto), p.ruta


def test_las_cuatro_orientaciones_de_relleno_no_son_el_mismo_dibujo():
    datos = {o: (arte.RAIZ / f"pieza/muebles/maceta-{o}.png").read_bytes() for o in arte.ORIENTACIONES}
    assert len(set(datos.values())) == 4


def test_reducir_escribe_la_copia_de_un_original_y_rechaza_el_de_otro_tamano(tmp_path, monkeypatch):
    fuentes, servido = tmp_path / "fuentes", tmp_path / "arte"
    monkeypatch.setattr(pieza, "FUENTES", fuentes)
    monkeypatch.setattr(pieza, "SERVIDO", servido)
    (fuentes / "pieza").mkdir(parents=True)
    Image.new("RGBA", (1024, 512), (10, 200, 30, 255)).save(fuentes / "pieza/suelo.png")
    assert pieza.reducir() == ["pieza/suelo.png"]
    with Image.open(servido / "pieza/suelo.png") as chica:
        assert chica.size == (512, 256) and chica.getpixel((256, 128))[:3] == (10, 200, 30)
    Image.new("RGBA", (1000, 500)).save(fuentes / "pieza/suelo.png")
    with pytest.raises(ValueError, match="1024"):
        pieza.reducir()


def test_lo_servido_es_la_reduccion_de_su_original_si_lo_hay():
    # Nadie entrega un original y se olvida de correr la herramienta: los píxeles coinciden.
    for o in arte.originales_de_la_pieza():
        original = pieza.FUENTES / o.ruta
        if original.exists():
            assert pieza.reducida(original).tobytes() == Image.open(arte.RAIZ / o.ruta).convert("RGBA").tobytes(), o.ruta
