import json
import re
from collections import Counter

from PIL import Image

import avatar
import cosmeticos
import departamento
import objetos
from web import arte, pueblo


def test_el_contrato_tiene_sus_270_piezas():
    piezas = arte.piezas()
    assert Counter(p.familia for p in piezas) == {
        "pueblo": 1, "lugares": 7, "escenas": 6, "avatar": 114, "efectos": 4, "iconos": 63, "pieza": 75,
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


def test_los_lugares_de_hoy_son_las_270_piezas_y_la_pieza_se_sube_al_doble():
    en_el_juego = [l for l in arte.lugares() if l.en_el_juego]
    assert [l.ruta for l in en_el_juego] == [p.ruta for p in arte.piezas()]
    assert len(en_el_juego) == 270
    por_ruta = {l.ruta: l for l in en_el_juego}
    assert (por_ruta["pieza/suelo.png"].ancho, por_ruta["pieza/suelo.png"].alto) == (1024, 512)
    assert (por_ruta["pieza/pared-izquierda.png"].ancho, por_ruta["pieza/pared-izquierda.png"].alto) == (512, 1280)
    assert (por_ruta["pieza/muebles/maceta-se.png"].ancho, por_ruta["pieza/muebles/maceta-se.png"].alto) == (1024, 1536)
    assert (por_ruta["pieza/muebles/fuente-ne.png"].ancho, por_ruta["pieza/muebles/fuente-ne.png"].alto) == (2048, 2048)
    assert all(l.reduccion == 2 for l in en_el_juego if l.familia == "pieza")
    icono = next(l for l in en_el_juego if l.familia == "iconos")
    assert (icono.ancho, icono.alto, icono.reduccion) == (48, 48, 1)
    # Lo servido es siempre la subida entre la reducción.
    servido = {p.ruta: (p.ancho, p.alto) for p in arte.piezas()}
    assert all((l.ancho // l.reduccion, l.alto // l.reduccion) == servido[l.ruta] for l in en_el_juego)


def test_un_lugar_se_busca_por_su_ruta_y_nada_mas():
    assert arte.lugar_de("efectos/corazon.png") == next(l for l in arte.lugares() if l.ruta == "efectos/corazon.png")
    for ruta in ("pieza/inventada.png", "efectos/corazon", "efectos/../efectos/corazon.png", "/efectos/corazon.png",
                 "efectos\\corazon.png", "efectos/corazon.png/", "EFECTOS/CORAZON.PNG", "", "efectos/corazon.png\x00"):
        assert arte.lugar_de(ruta) is None


def test_el_contrato_sale_de_los_catalogos():
    rutas = {p.ruta for p in arte.piezas()}
    for lugar in pueblo.LUGARES:
        assert f"pueblo/lugares/{lugar}.png" in rutas
        # La escena es el fondo de la pantalla del lugar: donde se ve el departamento, no hay.
        con_escena = "departamento" not in pueblo.ofrece(lugar)
        assert (f"escenas/{lugar}.png" in rutas) is con_escena, lugar
    assert "escenas/casa.png" not in rutas
    for pose in arte.POSES:
        for piel in avatar.PIELES:
            assert f"avatar/cuerpo/{piel.clave}-{pose}.png" in rutas
        for ropa in avatar.ROPAS:
            assert f"avatar/ropa/{ropa.clave}-{pose}.png" in rutas
        for pelo in avatar.PELOS:
            for color in avatar.COLORES_DE_PELO:
                assert f"avatar/pelo/{pelo.clave}-{color.clave}-{pose}.png" in rutas


def test_la_escena_de_un_lugar_sale_de_lo_que_ofrece_y_no_de_una_lista(monkeypatch):
    # Si la Tienda fuera tu departamento y tu casa dejara de serlo, las escenas se cambiarían solas.
    monkeypatch.setitem(pueblo.OFRECE, "tienda", ("departamento",))
    monkeypatch.delitem(pueblo.OFRECE, "casa")
    rutas = {p.ruta for p in arte.piezas()}
    assert "escenas/tienda.png" not in rutas and "escenas/casa.png" in rutas
    assert "pueblo/lugares/tienda.png" in rutas


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
    monkeypatch.setattr(arte, "RAIZ_POR_VENIR", tmp_path / "por_venir")
    (tmp_path / "datos").mkdir()
    escritas = rellenos.generar()
    assert len(escritas) == 270 + 16 + 134
    corazon = arte.RAIZ / "efectos" / "corazon.png"
    propio = Image.new("RGBA", (32, 32), (1, 2, 3, 255))
    propio.save(corazon)
    assert rellenos.generar() == []
    assert rellenos.generar(todo=False) == []
    with Image.open(corazon) as imagen:
        assert imagen.getpixel((0, 0)) == (1, 2, 3, 255)
    assert len(rellenos.generar(todo=True)) == 270 + 16 + 134


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
    escenas = [_relleno(p.ruta).tobytes() for p in arte.piezas() if p.familia == "escenas"]
    assert len(set(lugares)) == 7 and len(set(escenas)) == 6


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
        + [f"iconos/muebles/{m.clave}.png" for m in departamento.a_la_venta()]   # la puerta no lleva ícono
    )


def test_cada_cosa_que_se_compra_o_se_lleva_tiene_su_icono():
    rutas = {p.ruta: p for p in arte.piezas()}
    esperadas = _rutas_de_iconos()
    assert len(esperadas) == 63
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
    assert len(colores) == 3
    assert all(len({c for _, _, c in items}) == 1 for items in por_grupo.values())


def test_toda_pieza_cae_en_un_solo_grupo_de_una_sola_familia():
    lugares = arte.lugares()
    grupos = arte.grupos()
    sueltas = [r for g in grupos for r in g.rutas]
    assert sorted(sueltas) == sorted(l.ruta for l in lugares)
    familia = {l.ruta: l.familia for l in lugares}
    for g in grupos:
        assert g.rutas
        assert {familia[r] for r in g.rutas} == {g.familia}, g.clave


def test_las_claves_de_los_grupos_son_validas_y_unicas():
    grupos = arte.grupos()
    claves = [g.clave for g in grupos]
    assert len(set(claves)) == len(claves)
    for clave in claves:
        assert re.fullmatch(r"[a-z0-9/_-]{1,64}", clave), clave
        assert not clave.endswith(".png"), clave
    assert 25 <= len(grupos) <= 70


def test_los_nombres_de_los_grupos_dicen_algo():
    for g in arte.grupos():
        assert g.nombre.strip() and len(g.nombre) <= 120, g.clave


def test_el_corte_de_los_grupos():
    por_clave = {g.clave: g for g in arte.grupos()}
    cama = por_clave["pieza/muebles/cama"]
    assert cama.nombre == "Cama grande" and cama.familia == "pieza"
    assert sorted(cama.rutas) == sorted(f"pieza/muebles/cama-{o}.png" for o in arte.ORIENTACIONES)
    assert len(por_clave["pieza/muebles/cama_sencilla"].rutas) == 4
    assert len(por_clave["pieza/muebles/cuadro"].rutas) == 2
    assert len(por_clave["pieza/paredes-y-suelo"].rutas) == 3
    for pelo in avatar.PELOS:
        g = por_clave[f"avatar/pelo/{pelo.clave}"]
        assert g.nombre == f"Peinado {pelo.nombre.lower()}"
        assert len(g.rutas) == len(avatar.COLORES_DE_PELO) * len(arte.POSES)
    assert len(por_clave["avatar/cuerpo"].rutas) == len(avatar.PIELES) * len(arte.POSES)
    assert len(por_clave["avatar/ropa"].rutas) == len(avatar.ROPAS) * len(arte.POSES)
    for carpeta in ("muebles", "objetos", "cosmeticos"):
        assert por_clave[f"iconos/{carpeta}"].familia == "iconos"
    assert len(por_clave["escenas"].rutas) == 6
    assert por_clave["pueblo/fondo"].familia == "pueblo"
    assert len(por_clave["pueblo/lugares"].rutas) == 7
    assert len(por_clave["efectos"].rutas) == 4


def test_una_pieza_que_ningun_grupo_conoce_hace_fallar(monkeypatch):
    import pytest

    originales = arte.piezas()
    extra = arte.Pieza("rareza/algo.png", 1, 1, "avatar")
    monkeypatch.setattr(arte, "piezas", lambda: originales + (extra,))
    arte.olvidar()
    try:
        with pytest.raises(ValueError):
            arte.grupos()
    finally:
        monkeypatch.undo()
        arte.olvidar()


# --- El encendido de los cuatro muebles del juego ------------------------------

ENCENDIDOS = ("lampara", "calefactor", "chimenea", "fuente")


def test_los_cuatro_del_juego_tienen_su_encendido_en_su_grupo():
    assert arte.ENCENDIDOS == {c: "encendido" for c in ENCENDIDOS}
    por_clave = {g.clave: g for g in arte.grupos()}
    for clave in ENCENDIDOS:
        de_hoy = [f"pieza/muebles/{clave}-{o}.png" for o in arte.ORIENTACIONES]
        nuevos = [f"pieza/muebles/{clave}-encendido-{o}.png" for o in arte.ORIENTACIONES]
        grupo = por_clave[f"pieza/muebles/{clave}"]
        assert grupo.nombre == departamento.MUEBLES[clave].nombre
        assert list(grupo.rutas) == de_hoy + nuevos
        for ruta in nuevos:
            lugar = arte.lugar_de(ruta)
            assert (lugar.familia, lugar.reduccion, lugar.en_el_juego) == ("pieza", 2, False)
            assert (lugar.objeto, lugar.estado) == (clave, "encendido")
    assert arte.lugar_de("pieza/muebles/lampara-se.png").estado is None


def test_el_encendido_mide_lo_mismo_que_su_mueble():
    for clave in ENCENDIDOS:
        for o in arte.ORIENTACIONES:
            apagado = arte.lugar_de(f"pieza/muebles/{clave}-{o}.png")
            encendido = arte.lugar_de(f"pieza/muebles/{clave}-encendido-{o}.png")
            assert (encendido.ancho, encendido.alto) == (apagado.ancho, apagado.alto)


def test_el_encendido_no_entra_al_contrato_del_juego():
    assert len(arte.piezas()) == 270
    assert not any("encendido" in p.ruta for p in arte.piezas())
    assert not any("encendido" in p["ruta"] for p in arte.como_json()["piezas"])
    escrito = json.loads((arte.RAIZ.parent / "datos" / "arte.json").read_text(encoding="utf-8"))
    assert escrito == arte.como_json()
    assert len([l for l in arte.lugares() if l.en_el_juego]) == 270
    assert len(arte.lugares()) == 270 + 16 + 134
    # Los lugares nuevos van detrás de los del juego.
    assert all(l.en_el_juego for l in arte.lugares()[:270])


def test_cada_lugar_por_venir_tiene_su_provisional_y_no_sobra_ninguno():
    esperados = {l.ruta: (l.ancho // l.reduccion, l.alto // l.reduccion) for l in arte.lugares()
                 if not l.en_el_juego and l.familia in ("pieza", "iconos")}
    assert len(esperados) == 16 + 134
    en_disco = {p.relative_to(arte.RAIZ_POR_VENIR).as_posix() for p in arte.RAIZ_POR_VENIR.rglob("*")
                if p.is_file()}
    assert en_disco == set(esperados)
    for ruta, medida in esperados.items():
        with Image.open(arte.RAIZ_POR_VENIR / ruta) as imagen:
            assert imagen.format == "PNG" and imagen.size == medida, ruta
    # Nada de lo que no pinta el juego cuelga de lo que sirve.
    assert not any("encendido" in p.name for p in arte.RAIZ.rglob("*"))


def test_el_relleno_del_encendido_no_es_el_del_apagado():
    from herramientas import rellenos

    for clave in ENCENDIDOS:
        for o in arte.ORIENTACIONES:
            lugar = arte.lugar_de(f"pieza/muebles/{clave}-encendido-{o}.png")
            apagado = _relleno(f"pieza/muebles/{clave}-{o}.png")
            encendido = rellenos._dibujar_lugar(lugar).convert("RGBA")
            assert encendido.size == apagado.size == (lugar.ancho // 2, lugar.alto // 2)
            assert encendido.tobytes() != apagado.tobytes()


# --- Los 24 objetos que el juego todavía no tiene ------------------------------

COLORES = ("azul", "roja", "verde", "amarilla", "negra", "blanca")
# (clave, nombre, ancho, fondo, estado) tal cual la tabla del diseño.
LOS_24 = [
    ("consola_flappy", "Consola Flappy", 1, 1, None), ("consola_pong", "Consola Pong", 1, 1, None),
    ("mesa_gato", "Mesa de gato", 1, 1, None), ("atril", "Atril", 1, 1, None),
    ("tocadiscos", "Tocadiscos", 1, 1, "encendido"), ("mayordomo", "Mayordomo robot", 1, 1, None),
    ("puerta_cristal", "Puerta de cristal", 1, 1, "atravesable"), ("cableados", "Bloque de cableados", 1, 1, None),
    ("super_dado", "Súper Dado", 1, 1, None), ("mega_tv", "Mega TV", 2, 1, "encendido"),
    ("lampara_dragon", "Lámpara Dragón", 1, 1, "encendido"),
    *[(f"silla_{c}", f"Silla {c}", 1, 1, None) for c in COLORES],
    *[(f"mesa_{c}", f"Mesa {c}", 1, 1, None) for c in COLORES],
    ("balcon", "Balcón", 4, 1, None),
]
CLAVES_NUEVAS = [c for c, *_ in LOS_24]


def _rutas_de(clave, estado, orientaciones):
    rutas = [f"pieza/muebles/{clave}-{o}.png" for o in orientaciones]
    return rutas + ([f"pieza/muebles/{clave}-{estado}-{o}.png" for o in orientaciones] if estado else [])


def test_los_24_objetos_y_sus_claves():
    assert len(arte.POR_VENIR) == 24
    assert [(o.clave, o.nombre, o.ancho, o.fondo, o.estado) for o in arte.POR_VENIR] == LOS_24
    assert all(c not in departamento.MUEBLES for c in CLAVES_NUEVAS)
    assert all(o.capa == departamento.BULTO for o in arte.POR_VENIR[:-1])
    assert arte.POR_VENIR[-1] == arte.Objeto("balcon", "Balcón", ancho=4, fondo=1, capa=arte.FUERA)
    assert arte.FUERA == "fuera"


def test_los_objetos_nuevos_tienen_110_dibujos_y_24_iconos():
    nuevos = [l for l in arte.lugares() if not l.en_el_juego and l.objeto in CLAVES_NUEVAS]
    dibujos = [l for l in nuevos if l.familia == "pieza"]
    assert len(dibujos) == 110
    assert all((l.reduccion, l.en_el_juego) == (2, False) for l in dibujos)
    esperados = []
    for clave, _, _, _, estado in LOS_24:
        esperados += _rutas_de(clave, estado, ("se", "so") if clave == "balcon" else arte.ORIENTACIONES)
    assert [l.ruta for l in dibujos] == esperados
    iconos = [l for l in arte.lugares() if l.ruta.startswith("iconos/muebles/") and not l.en_el_juego]
    assert [l.ruta for l in iconos] == [f"iconos/muebles/{c}.png" for c in CLAVES_NUEVAS]
    assert all((l.ancho, l.alto, l.reduccion, l.familia) == (48, 48, 1, "iconos") for l in iconos)
    # Los dibujos van detrás de los encendidos de hoy y los íconos, detrás de todos los dibujos.
    rutas = [l.ruta for l in arte.lugares()]
    assert rutas[270 + 16:270 + 16 + 110] == esperados
    assert rutas[270 + 16 + 110:] == [l.ruta for l in iconos]


def test_las_medidas_de_los_objetos_nuevos():
    def medida(ruta):
        lugar = arte.lugar_de(ruta)
        return lugar.ancho, lugar.alto

    assert medida("pieza/muebles/consola_flappy-se.png") == (1024, 1536)
    assert medida("pieza/muebles/mega_tv-ne.png") == (1536, 1792)
    assert medida("pieza/muebles/mega_tv-encendido-so.png") == (1536, 1792)
    assert medida("pieza/muebles/balcon-se.png") == (2560, 2304)
    assert medida("iconos/muebles/balcon.png") == (48, 48)
    assert arte.tamano_de_mueble(arte.POR_VENIR[-1]) == (1280, 1152)
    assert arte.tamano_de_mueble(departamento.MUEBLES["maceta"]) == (512, 768)


def test_el_balcon_solo_tiene_se_y_so():
    rutas = {l.ruta for l in arte.lugares()}
    assert {"pieza/muebles/balcon-se.png", "pieza/muebles/balcon-so.png"} <= rutas
    assert not {"pieza/muebles/balcon-no.png", "pieza/muebles/balcon-ne.png"} & rutas
    assert len([r for r in rutas if "/balcon-" in r]) == 2


def test_la_puerta_de_cristal_atraviesa_y_no_se_enciende():
    rutas = {l.ruta for l in arte.lugares()}
    assert all(f"pieza/muebles/puerta_cristal-atravesable-{o}.png" in rutas for o in arte.ORIENTACIONES)
    assert not any("puerta_cristal-encendido" in r for r in rutas)
    assert arte.lugar_de("pieza/muebles/puerta_cristal-atravesable-se.png").estado == "atravesable"
    assert arte.lugar_de("pieza/muebles/puerta_cristal-se.png").estado is None


def test_los_objetos_nuevos_no_entran_al_juego():
    assert len(arte.piezas()) == 270
    assert not any(o in p.ruta for p in arte.piezas() for o in CLAVES_NUEVAS)
    escrito = json.loads((arte.RAIZ.parent / "datos" / "arte.json").read_text(encoding="utf-8"))
    assert escrito == arte.como_json()
    assert not any(o in p["ruta"] for p in escrito["piezas"] for o in CLAVES_NUEVAS)
    assert len([l for l in arte.lugares() if l.en_el_juego]) == 270
    assert not any(c in [m.clave for m in departamento.a_la_venta()] for c in CLAVES_NUEVAS)
    assert len(departamento.a_la_venta()) == 19
    assert not any(c in p.name for p in arte.RAIZ.rglob("*") for c in CLAVES_NUEVAS)


def test_cada_objeto_es_un_grupo_con_su_nombre_y_sus_dos_estados():
    por_clave = {g.clave: g for g in arte.grupos()}
    for clave, nombre, _, _, estado in LOS_24:
        grupo = por_clave[f"pieza/muebles/{clave}"]
        assert (grupo.nombre, grupo.familia) == (nombre, "pieza")
        assert list(grupo.rutas) == _rutas_de(clave, estado, ("se", "so") if clave == "balcon" else arte.ORIENTACIONES)
    assert len(por_clave["pieza/muebles/mega_tv"].rutas) == 8
    assert len(por_clave["pieza/muebles/balcon"].rutas) == 2
    # Una clave con guion bajo no se confunde con otra que empieza igual.
    assert len(por_clave["pieza/muebles/consola"].rutas) == 4
    assert len(por_clave["pieza/muebles/lampara"].rutas) == 8
    assert len(por_clave["pieza/muebles/lampara_dragon"].rutas) == 8
    assert len(por_clave["pieza/muebles/mesa_gato"].rutas) == 4


def test_los_iconos_nuevos_van_con_los_de_los_muebles():
    grupo = {g.clave: g for g in arte.grupos()}["iconos/muebles"]
    assert grupo.nombre == "Iconos de los muebles" and grupo.familia == "iconos"
    assert len(grupo.rutas) == 19 + 24
    assert not any(clave.startswith("iconos/muebles/") and clave != "iconos/muebles"
                   for clave in (g.clave for g in arte.grupos()))


def test_las_rutas_nuevas_pasan_el_filtro_del_cliente_y_de_la_tabla():
    import shutil
    import subprocess

    import db
    from pathlib import Path

    rutas = [l.ruta for l in arte.lugares() if not l.en_el_juego]
    assert all(db._RUTA_DE_ARTE.fullmatch(r) for r in rutas)
    node = shutil.which("node")
    if node is None:
        return
    raiz = Path(__file__).resolve().parent.parent
    programa = ("import { esRutaDeArte } from './web/static/js/arte.js';"
                "const rutas = JSON.parse(process.argv[1]);"
                "console.log(JSON.stringify(rutas.filter((r) => !esRutaDeArte(r))));")
    hecho = subprocess.run([node, "--input-type=module", "-e", programa, json.dumps(rutas)],
                           capture_output=True, text=True, cwd=raiz)
    assert hecho.returncode == 0, hecho.stderr
    assert json.loads(hecho.stdout) == []


def test_el_relleno_de_los_objetos_nuevos_se_entiende():
    from herramientas import rellenos

    for lugar in arte.lugares():
        if lugar.en_el_juego or lugar.objeto not in CLAVES_NUEVAS or lugar.familia != "pieza":
            continue
        imagen = rellenos._dibujar_lugar(lugar).convert("RGBA")
        assert imagen.size == (lugar.ancho // 2, lugar.alto // 2), lugar.ruta
        assert imagen.getbbox() is not None, lugar.ruta
    se = rellenos._dibujar_lugar(arte.lugar_de("pieza/muebles/balcon-se.png")).convert("RGBA")
    so = rellenos._dibujar_lugar(arte.lugar_de("pieza/muebles/balcon-so.png")).convert("RGBA")
    assert se.size == so.size == (1280, 1152) and se.tobytes() != so.tobytes()
    # Se miran en espejo: la tira de una va por donde la otra no.
    assert se.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes() != se.tobytes()
    for lugar in arte.lugares():
        if lugar.ruta.startswith("iconos/muebles/") and not lugar.en_el_juego:
            with Image.open(arte.RAIZ_POR_VENIR / lugar.ruta) as icono:
                assert icono.size == (48, 48), lugar.ruta
