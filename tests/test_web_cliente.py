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


def test_el_mapa_pone_la_sombra_del_gachamon_con_su_pieza():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "efectos/sombra.png" in mapa


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


# --- la Tienda -------------------------------------------------------------------

def _guion(nombre: str) -> str:
    return (ESTATICOS / "js" / nombre).read_text(encoding="utf-8")


def _sin_comentarios(codigo: str) -> str:
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"(^|\s)//.*$", r"\1", codigo, flags=re.M)


def test_la_tienda_esta_y_se_usa():
    assert {"tienda.js", "compras.js"} <= {g.name for g in GUIONES}
    principal = _guion("principal.js")
    assert "./tienda.js" in principal
    # Una fila más en la tabla de las pantallas.
    assert re.search(r"^\s*tienda:", principal, re.M)


def test_la_tienda_compra_con_reintentos_y_un_evento_por_toque():
    tienda = _guion("tienda.js")
    assert "conReintentos" in tienda and "nuevoEvento" in tienda
    assert "innerHTML" not in tienda and "http" not in tienda


def test_los_reintentos_viven_en_api_y_el_lugar_los_usa():
    assert re.search(r"export\s+(async\s+)?function\s+conReintentos\b", _guion("api.js"))
    lugar = _guion("lugar.js")
    assert not re.search(r"function\s+conReintentos\b", lugar)
    assert "conReintentos(" in lugar


def test_desde_la_tienda_del_pueblo_se_entra_a_comprar_y_la_ficha_dice_el_titulo():
    lugar = _guion("lugar.js")
    assert "vista: 'tienda'" in lugar or 'vista: "tienda"' in lugar
    assert "ofrece" in lugar
    assert re.search(r"\bg\.titulo\b|gachamon\.titulo\b", lugar)


def test_las_pantallas_de_la_tienda_no_escriben_precios_ni_claves_del_catalogo():
    import casas as cas
    import cosmeticos as cos
    import objetos as obj

    objetos, cosmeticos = obj.a_la_venta(), cos.CATALOGO.values()
    casas, muebles = cas.CATALOGO.values(), cas.MUEBLES.values()
    claves = {p.clave for p in (*objetos, *cosmeticos, *casas, *muebles)}
    precios = {p.precio for p in (*objetos, *cosmeticos, *casas, *muebles)}
    for nombre in ("tienda.js", "compras.js"):
        codigo = _sin_comentarios(_guion(nombre))
        citadas = set(re.findall(r"""['"`]([a-z0-9_]+)['"`]""", codigo))
        assert not citadas & claves, (nombre, citadas & claves)
        numeros = {int(n) for n in re.findall(r"(?<![\w.])\d+(?![\w.])", codigo)}
        assert not numeros & precios, (nombre, numeros & precios)
