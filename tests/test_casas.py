"""El hogar: que nadie duerma en la calle de entrada y que la casa cuadre."""
import re
from datetime import datetime, timedelta, timezone

import pytest

import casas as cas
import cogs.social as social
import db
import economia
import jardin
import simulacion as sim
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)
ANSI = re.compile(r"\x1b\[[0-9;]*m")
PEQUENA = cas.CATALOGO["pequena"]
MEDIANA = cas.CATALOGO["mediana"]
GRANDE = cas.CATALOGO["grande"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "casas.db")
    db.inicializar()


def nacer(nombre="Kuro", activa=True, usuario="u1", especie="pulpo"):
    return db.crear(usuario, "g1", especie, nombre, STATS, T0, activa=activa)


def con_monedas(cuantas, usuario="u1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? "
            "AND guild_id = 'g1'",
            (cuantas, usuario),
        )


def monedas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciicoins


def hogar(usuario="u1", ahora=T0):
    return db.hogar_de(usuario, "g1", ahora)


# --- Nadie en la calle -----------------------------------------------------

def test_nadie_se_queda_sin_hogar():
    """Lo pedido: quien nunca ha mirado su casa no está en la calle, está en el
    refugio y con la semana entera por delante."""
    suyo = hogar()

    assert suyo.casa is None
    assert suyo.estado(T0) == cas.REFUGIO
    assert suyo.refugio_hasta == T0 + timedelta(days=cas.DIAS_DE_REFUGIO)


def test_la_semana_empieza_al_mirar_y_no_al_desplegar():
    """Por eso la fila se crea perezosamente: quien aparezca dentro de un mes se
    encuentra su semana entera, no gastada esperándole."""
    tarde = T0 + timedelta(days=30)
    suyo = hogar(ahora=tarde)

    assert suyo.estado(tarde) == cas.REFUGIO
    assert suyo.refugio_hasta == tarde + timedelta(days=cas.DIAS_DE_REFUGIO)


def test_la_estancia_no_se_reinicia_al_volver_a_mirar():
    primero = hogar()
    despues = hogar(ahora=T0 + timedelta(days=3))

    assert despues.refugio_hasta == primero.refugio_hasta


def test_al_acabarse_la_estancia_se_queda_a_la_intemperie():
    suyo = hogar()
    assert suyo.estado(suyo.refugio_hasta + timedelta(seconds=1)) == cas.INTEMPERIE
    assert suyo.comodidad(suyo.refugio_hasta + timedelta(seconds=1)) == 0


def test_el_hogar_es_de_cada_persona_y_servidor():
    db.hogar_de("u1", "g1", T0)
    assert db.hogar_de("u2", "g1", T0).casa is None
    assert db.hogar_de("u1", "g2", T0).casa is None


# --- Comprar y mudarse -----------------------------------------------------

def test_comprar_cobra_y_te_muda():
    nacer()
    con_monedas(1000)

    resultado = economia.comprar_casa("u1", "g1", MEDIANA, T0)

    assert resultado.ok
    assert resultado.casa == MEDIANA
    assert resultado.desde is None            # venía del refugio
    assert monedas() == 1000 - MEDIANA.precio
    assert hogar().casa == MEDIANA
    assert hogar().estado(T0) == cas.PROPIA


def test_comprar_una_casa_menor_no_cobra_ni_te_muda():
    """El mismo cerrojo que el doble clic del ropero: comprar lo que ya tienes,
    o algo peor, no puede cobrar."""
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", GRANDE, T0)
    saldo = monedas()

    for casa in (PEQUENA, MEDIANA, GRANDE):
        resultado = economia.comprar_casa("u1", "g1", casa, T0)
        assert not resultado.ok, casa.clave
        assert "Ya vives" in resultado.problema

    assert monedas() == saldo
    assert hogar().casa == GRANDE


def test_mudarse_a_una_mayor_dice_de_donde_vienes():
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", PEQUENA, T0)

    resultado = economia.comprar_casa("u1", "g1", GRANDE, T0)

    assert resultado.ok
    assert resultado.desde == PEQUENA
    assert monedas() == 3000 - PEQUENA.precio - GRANDE.precio


def test_sin_monedas_suficientes_no_se_muda_nadie():
    con_monedas(PEQUENA.precio - 1)

    resultado = economia.comprar_casa("u1", "g1", PEQUENA, T0)

    assert not resultado.ok
    assert "faltan 1 asciicoins" in resultado.problema
    assert monedas() == PEQUENA.precio - 1
    assert hogar().casa is None


def test_el_saldo_nunca_se_queda_en_negativo():
    con_monedas(0)
    for _ in range(3):
        assert not economia.comprar_casa("u1", "g1", PEQUENA, T0).ok
    assert monedas() == 0


def test_una_casa_que_no_es_del_catalogo_no_se_cuela():
    con_monedas(3000)
    falsa = cas.Casa("pequena", "Chabola", 0, 999, 99, 999, 3, 9)

    with pytest.raises(ValueError):
        economia.comprar_casa("u1", "g1", falsa, T0)
    assert monedas() == 3000


def test_el_refugio_no_se_compra():
    """No está en el catálogo a propósito: es donde se empieza, no un producto."""
    assert cas.REFUGIO not in cas.CATALOGO
    assert cas.EL_REFUGIO.precio == 0


# --- Los números del catálogo ----------------------------------------------

def test_comprar_siempre_sube_de_comodidad():
    """Es lo que hace que valga la pena mudarse: la casa más humilde tiene que
    superar al refugio, o comprar sería un castigo."""
    for casa in cas.CATALOGO.values():
        assert casa.comodidad > cas.EL_REFUGIO.comodidad, casa.clave


def test_el_techo_sube_con_el_tamano():
    """Con un techo común, la casa grande desperdiciaría siete de sus diez
    huecos: comprarla sólo valdría para mirarla."""
    por_tamano = sorted(cas.CATALOGO.values(), key=lambda c: c.tamano)
    for menor, mayor in zip(por_tamano, por_tamano[1:]):
        assert mayor.techo > menor.techo
        assert mayor.huecos > menor.huecos
        assert mayor.precio > menor.precio
        assert mayor.comodidad > menor.comodidad


def test_el_techo_de_cada_casa_es_alcanzable_amueblandola_entera():
    """Un techo al que no se puede llegar es un número que miente.

    Ata el catálogo con el presupuesto de mobiliario de la entrega 2: si alguien
    sube un techo o baja los huecos sin tocar `MAX_COMODIDAD_POR_MUEBLE`, esto
    avisa. Y el margen tiene que existir: llegar al techo nada más comprar
    dejaría los huecos sin sentido.
    """
    for casa in cas.CATALOGO.values():
        margen = casa.techo - casa.comodidad
        assert margen > 0, casa.clave
        assert margen <= casa.huecos * cas.MAX_COMODIDAD_POR_MUEBLE, casa.clave


# --- El dibujo -------------------------------------------------------------

def _sin_color(texto):
    return [l for l in ANSI.sub("", texto).splitlines() if not l.startswith("```")]


def _eje(linea):
    marcas = [i for i, ch in enumerate(linea) if ch in "/\\╭╮╰╯│"]
    return (marcas[0] + marcas[-1]) / 2 if marcas else None


@pytest.mark.parametrize("cuantos", [0, 1, 3, 5, 6, 10])
def test_el_tejado_va_centrado_sobre_el_marco(cuantos):
    """Es de donde han salido todos los descuadres de este proyecto: centrar el
    adorno sobre su propio eje en vez de sobre el del dibujo. Se mide el ancho
    visible, sin los códigos de color."""
    vivos = [_criatura(i) for i in range(cuantos)]
    for casa in (cas.EL_REFUGIO, *cas.CATALOGO.values()):
        lineas = _sin_color(cas.render(vivos, casa))
        ejes = {_eje(l) for l in lineas if _eje(l) is not None}
        assert len(ejes) == 1, (casa.clave, cuantos, sorted(ejes))


def test_todas_las_lineas_del_marco_miden_lo_mismo():
    lineas = _sin_color(cas.render([_criatura(i) for i in range(4)], GRANDE))
    marco = [l for l in lineas if l.startswith(("╭", "│", "╰"))]
    assert {len(l) for l in marco} == {jardin.ANCHO + 2}


def test_el_tejado_crece_con_la_casa():
    altos = [len(cas.tejado(c)) for c in
             sorted(cas.CATALOGO.values(), key=lambda c: c.tamano)]
    assert altos == sorted(altos) and altos[0] < altos[-1]


def _criatura(i):
    especies = ("pulpo", "michi", "pollito", "brote", "slime",
                "pedrusco", "chispa", "fantasma", "chatarra", "dragoncito")
    return sim.Criatura(
        id=i + 1, usuario_id="u1", guild_id="g1", especie=especies[i % 10],
        nombre=f"Bicho{i}", nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )


def test_la_casa_cabe_en_un_mensaje_de_discord():
    """Con diez el jardín ya mide más de mil caracteres; el tejado y el suelo
    tienen que dejarlo por debajo del tope de Discord."""
    texto = social.texto_de_la_casa(
        cas.Hogar(GRANDE, T0), [_criatura(i) for i in range(10)], "Felipe", T0
    )
    assert len(texto) < 2000


# --- Lo que se ve ----------------------------------------------------------

def test_la_casa_dibuja_a_todos_los_vivos_y_no_solo_al_activo():
    """Lo pedido: `/casa` enseña el plantel entero, no la ficha del activo."""
    nacer("Activo")
    nacer("Reserva", activa=False)
    muerto = nacer("Muerto", activa=False)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' "
            "WHERE id = ?", (T0.isoformat(), muerto.id),
        )

    texto = social.texto_de_la_casa(hogar(), db.plantel("u1", "g1"), "Felipe", T0)

    assert "Activo" in texto and "Reserva" in texto
    assert "Muerto" not in texto


def test_el_refugio_dice_cuanto_queda_y_la_intemperie_que_se_acabo():
    suyo = hogar()
    en_refugio = social.texto_de_la_casa(suyo, [], "Felipe", T0)
    fuera = social.texto_de_la_casa(
        suyo, [], "Felipe", suyo.refugio_hasta + timedelta(days=1)
    )

    assert "refugio" in en_refugio and "días de estancia" in en_refugio
    assert "intemperie" in fuera and "Se acabó" in fuera


def test_la_comodidad_se_enseña_sin_porcentaje():
    """Deja de ser un porcentaje al subir los techos por encima de 100: quien
    viera «118 %» pensaría que hay un fallo."""
    texto = social.texto_de_la_casa(cas.Hogar(GRANDE, T0), [], "Felipe", T0)
    assert f"Comodidad {GRANDE.comodidad}" in texto
    assert "%" not in texto


def test_la_mudanza_se_canta_diciendo_de_donde_vienes():
    con_monedas(3000)
    del_refugio = economia.comprar_casa("u1", "g1", PEQUENA, T0)
    subiendo = economia.comprar_casa("u1", "g1", GRANDE, T0)

    assert "se trasladó del refugio a su nueva **Casa pequeña**" in (
        tienda.texto_de_la_mudanza("Felipe", del_refugio)
    )
    assert "de Casa pequeña a su nueva **Casa grande**" in (
        tienda.texto_de_la_mudanza("Felipe", subiendo)
    )


# --- La tienda -------------------------------------------------------------

def test_la_tienda_sigue_cabiendo_en_los_limites_con_las_casas():
    """Tres desplegables, uno por fila: Discord admite cinco filas y cada lista
    no puede pasar de 25 opciones."""
    import cosmeticos as cos
    import objetos as obj

    menus = (tienda.MenuTienda(), tienda.MenuCosmeticos(), tienda.MenuCasas())
    vista = tienda.VistaConMenu(*menus)

    assert len(vista.children) == 3 <= 5
    for menu in menus:
        assert 1 <= len(menu.options) <= 25
    assert len(obj.CATALOGO) + len(cos.CATALOGO) + len(cas.CATALOGO) > 25


def test_el_desplegable_marca_donde_vives_y_lo_que_se_te_quedo_pequeño():
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", MEDIANA, T0)

    por_valor = {
        o.value: o.label for o in tienda.MenuCasas(hogar()).options
    }

    assert "se te quedó pequeña" in por_valor["pequena"]
    assert "aquí vives" in por_valor["mediana"]
    assert f"🪙 {GRANDE.precio}" in por_valor["grande"]
