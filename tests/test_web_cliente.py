"""Lo que se puede vigilar del cliente leyendo sus archivos."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "web" / "static"
GUIONES = sorted((ESTATICOS / "js").glob("*.js"))


def test_hay_guiones_que_mirar():
    assert {g.name for g in GUIONES} >= {
        "api.js", "pantallas.js", "dom.js", "dibujo.js", "entrada.js", "principal.js",
    }


def test_nada_entra_en_la_pagina_como_marcado():
    prohibido = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")
    culpables = [
        f"{g.name}:{n}" for g in GUIONES
        for n, linea in enumerate(g.read_text(encoding="utf-8").splitlines(), 1)
        if prohibido.search(linea)
    ]
    assert not culpables, culpables


def test_el_cliente_no_depende_de_nada_de_fuera():
    for archivo in [ESTATICOS / "index.html", ESTATICOS / "estilo.css", *GUIONES]:
        texto = archivo.read_text(encoding="utf-8")
        assert "http://" not in texto and "https://" not in texto, archivo.name


def test_la_portada_carga_sus_archivos_por_la_ruta_con_version():
    portada = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    assert "static/__V__/estilo.css" in portada
    assert "static/__V__/js/principal.js" in portada
    assert 'type="module"' in portada and 'lang="es"' in portada
    assert 'name="viewport"' in portada


def test_los_modulos_se_importan_con_rutas_relativas():
    importa = re.compile(r"""from\s+['"]([^'"]+)['"]""")
    for guion in GUIONES:
        for ruta in importa.findall(guion.read_text(encoding="utf-8")):
            assert ruta.startswith("./") and ruta.endswith(".js"), f"{guion.name}: {ruta}"


def test_el_aviso_del_codigo_esta_escrito():
    entrada = (ESTATICOS / "js" / "entrada.js").read_text(encoding="utf-8")
    assert "/vincular" in entrada
    assert "no se lo pases a nadie" in entrada.lower()


def test_ningun_texto_del_cliente_usa_los_nombres_viejos():
    for archivo in [ESTATICOS / "index.html", *GUIONES]:
        assert not re.search(r"ascii\s?(coin|gem)", archivo.read_text(encoding="utf-8"), re.I)
