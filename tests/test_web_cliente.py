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


def test_la_pantalla_principal_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"lugar.js", "tiempo.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./lugar.js" in principal


def test_la_pantalla_principal_dice_desfallecido_y_no_inventa_errores_al_acariciar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "esfallecid" in lugar
    assert "acariciar" in lugar and "cuidar" in lugar
    assert "visibilitychange" in lugar


def test_el_estilo_piensa_en_el_celular_y_en_el_computador():
    estilo = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert "min-width: 900px" in estilo
    assert "prefers-reduced-motion" in estilo


def test_el_avatar_ya_no_se_dibuja_con_codigo():
    dibujo = (ESTATICOS / "js" / "dibujo.js").read_text(encoding="utf-8")
    assert "dibujarAvatar" not in dibujo and "COLORES_DE_PIEL" not in dibujo
    for nombre in ("entrada.js", "lugar.js"):
        assert "./avatar.js" in (ESTATICOS / "js" / nombre).read_text(encoding="utf-8")


def test_el_arte_se_pide_por_la_ruta_con_version():
    arte = (ESTATICOS / "js" / "arte.js").read_text(encoding="utf-8")
    assert "import.meta.url" in arte


def test_el_mapa_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"mapa.js", "pueblo.js", "arte.js", "avatar.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./mapa.js" in principal


def test_el_mapa_no_lleva_el_pueblo_escrito_en_el_codigo():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    logica = (ESTATICOS / "js" / "pueblo.js").read_text(encoding="utf-8")
    assert "pueblo.json" in mapa
    for clave in ("incubadora", "cementerio", "estadio", "barrio"):
        assert clave not in mapa and clave not in logica


def test_el_boton_de_volver_dice_hacia_donde_con_lo_que_traen_los_datos():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "hacia" in mapa
    assert "Volver a ${" not in mapa


def test_el_mapa_se_puede_usar_sin_el_lienzo_y_respeta_a_quien_no_quiere_movimiento():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "aria-hidden" in mapa and "prefers-reduced-motion" in mapa
    assert "requestAnimationFrame" in mapa and "cancelAnimationFrame" in mapa


def test_desde_un_lugar_se_va_al_pueblo():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "vista: 'pueblo'" in lugar or 'vista: "pueblo"' in lugar


def test_la_pantalla_del_lugar_dice_donde_estas_y_avisa_lo_del_lugar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "lugar.nombre" in lugar and "lugar.aviso" in lugar
    assert "escenas/" in lugar
