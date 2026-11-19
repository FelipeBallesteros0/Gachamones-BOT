"""El arte de la pieza del departamento: su familia en el contrato, sus tamaños y la herramienta que reduce originales."""

import pytest
from PIL import Image

import departamento as dep
from herramientas import pieza, rellenos
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


def test_la_puerta_tiene_sus_dos_dibujos_y_ningun_icono():
    rutas = {p.ruta: p for p in arte.piezas()}
    se, so = rutas["pieza/muebles/puerta-se.png"], rutas["pieza/muebles/puerta-so.png"]
    assert (se.ancho, se.alto) == (256, 640) and (so.ancho, so.alto) == (256, 640)
    assert "pieza/muebles/puerta-no.png" not in rutas and "pieza/muebles/puerta-ne.png" not in rutas
    assert "iconos/muebles/puerta.png" not in rutas
    assert len(arte.piezas()) == 275


def test_el_relleno_de_la_puerta_no_es_el_de_un_cuadro():
    for lado in ("se", "so"):
        puerta = _relleno(f"pieza/muebles/puerta-{lado}.png")
        cuadro = _relleno(f"pieza/muebles/cuadro-{lado}.png")
        assert puerta.size == cuadro.size and puerta.tobytes() != cuadro.tobytes()


def test_el_relleno_de_la_puerta_es_un_vano_oscuro_enmarcado_de_arriba_abajo():
    for lado in ("se", "so"):
        imagen = _relleno(f"pieza/muebles/puerta-{lado}.png")
        ancho, alto = imagen.size
        x = ancho // 2
        # En la vertical del medio: el hueco oscuro y opaco, de arriba abajo, y no el color de un cuadro.
        oscuros = [y for y in range(alto) if imagen.getpixel((x, y))[3] == 255 and max(imagen.getpixel((x, y))[:3]) < 90]
        assert len(oscuros) > 0.4 * alto, lado
        # Un marco claro alrededor del hueco, en la misma fila.
        fila = [imagen.getpixel((i, alto // 2)) for i in range(ancho)]
        claros = [i for i, c in enumerate(fila) if c[3] == 255 and max(c[:3]) > 100]
        assert claros and min(claros) < x < max(claros), lado
        transparentes = imagen.getchannel("A").histogram()[0]
        assert transparentes / (ancho * alto) <= 0.5, lado


def test_el_relleno_de_la_puerta_es_el_mismo_cada_vez():
    for lado in ("se", "so"):
        assert _relleno(f"pieza/muebles/puerta-{lado}.png").tobytes() == _relleno(f"pieza/muebles/puerta-{lado}.png").tobytes()


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


def _relleno(ruta: str) -> Image.Image:
    """Lo que `herramientas/rellenos.py` dibuja para esa pieza, sin mirar el archivo del repo."""
    pieza_del_contrato = next(p for p in arte.piezas() if p.ruta == ruta)
    return rellenos._dibujar(pieza_del_contrato).convert("RGBA")


def test_las_cuatro_orientaciones_de_relleno_no_son_el_mismo_dibujo():
    # Se prueba el generador, no los archivos del repo: el día que el dibujante
    # entregue una maceta igual por dos lados, su commit no tiene por qué fallar.
    for m in (m for m in dep.MUEBLES.values() if m.capa != dep.PARED):
        dibujos = {_relleno(f"pieza/muebles/{m.clave}-{o}.png").tobytes() for o in arte.ORIENTACIONES}
        assert len(dibujos) == 4, m.clave


def test_el_dibujo_de_un_mueble_que_no_se_pisa_llena_al_menos_la_mitad_de_su_caja():
    # Hoy tocar un mueble va por la silueta de su caja entera, y eso coincide con
    # lo que se ve sólo mientras el dibujo llene la caja. Esta prueba es el aviso
    # de que llegó un dibujo más bajo (o un cuadro más chico que su tramo).
    for p in arte.piezas():
        if not p.ruta.startswith("pieza/muebles/"):
            continue
        clave = p.ruta.removeprefix("pieza/muebles/").rsplit("-", 1)[0]
        if dep.MUEBLES[clave].capa == dep.SUELO:
            continue
        with Image.open(arte.RAIZ / p.ruta) as imagen:
            transparentes = imagen.convert("RGBA").getchannel("A").histogram()[0]
        parte = transparentes / (p.ancho * p.alto)
        assert parte <= 0.5, (
            f"{p.ruta} deja transparente el {parte:.0%} de su caja, más de la mitad. Hoy tocar un mueble va por "
            "la silueta de su caja entera, y eso sólo coincide con lo que se ve mientras el dibujo la llene: con "
            "este dibujo, tocar el aire de encima lo elegiría a él en vez de lo que se ve detrás. Antes de "
            "aceptarlo hay que pasar a mirar lo que se ve del dibujo en el punto tocado (`queSeToco`, en "
            "web/static/js/proyeccion.js), como dicen los pendientes del rework 5 en "
            "docs/superpowers/plans/2026-11-12-gachamon-web-pendientes.md («Lo primero al llegar arte más bajo "
            "que su caja»)."
        )


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
