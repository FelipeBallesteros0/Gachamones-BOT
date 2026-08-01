"""El ropero: comprar al armario, ponérselo y quitárselo sin perder nada."""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import economia
import logros
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
ROJO = cos.CATALOGO["tinte_rojo"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "ropero.db")
    db.inicializar()


def nacer(usuario="u1", nombre="Mia", activa=True):
    return db.crear(usuario, "g1", "pulpo", nombre, STATS, T0, activa=activa)


def con_gemas(cuantas, usuario="u1"):
    """Deja el monedero en esa cifra exacta, sin pasar por los logros."""
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciigems = ? WHERE usuario_id = ? AND guild_id = 'g1'",
            (cuantas, usuario),
        )


def gemas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciigems


def comprar(cosmetico=CORONA, usuario="u1"):
    return economia.comprar_cosmetico(usuario, "g1", cosmetico)


def poner(cosmetico=CORONA, usuario="u1"):
    return economia.equipar_cosmetico(usuario, "g1", cosmetico)


def quitar(tipo=cos.SOMBRERO, usuario="u1"):
    return economia.quitar_cosmetico(usuario, "g1", tipo)


def activa(usuario="u1"):
    return db.criatura_activa(usuario, "g1")


# --- Comprar ---------------------------------------------------------------

def test_comprar_cobra_lo_mete_en_el_ropero_y_se_lo_pone():
    """Que además se lo ponga es a propósito: es lo que espera quien acaba de
    gastarse sesenta gemas en una corona."""
    nacer()
    con_gemas(100)

    resultado = comprar()

    assert resultado.ok
    assert resultado.criatura.sombrero == "corona"
    assert db.ropero("u1", "g1") == {"corona"}
    assert gemas() == 100 - CORONA.precio
    assert resultado.saldo == gemas()
    # Y queda guardado, no sólo en el objeto devuelto.
    assert activa().sombrero == "corona"


def test_sin_gemas_suficientes_no_se_cobra_ni_entra_en_el_ropero():
    nacer()
    con_gemas(CORONA.precio - 1)

    resultado = comprar()

    assert not resultado.ok
    assert "faltan 1 asciigems" in resultado.problema
    assert gemas() == CORONA.precio - 1
    assert db.ropero("u1", "g1") == frozenset()
    assert activa().sombrero is None


def test_el_saldo_nunca_se_queda_en_negativo():
    """La condición viaja dentro del UPDATE justamente para esto."""
    nacer()
    con_gemas(0)

    for _ in range(3):
        assert not comprar().ok
    assert gemas() == 0


def test_comprar_lo_que_ya_tienes_no_cuesta_nada():
    """El doble clic: dos compras del mismo sombrero cobrarían 120 gemas y
    dejarían una corona. Y sigue valiendo aunque se lo hayas quitado, que es
    justo cuando el catálogo lo vuelve a ofrecer."""
    nacer()
    con_gemas(200)
    comprar()
    quitar()
    saldo = gemas()

    repetida = comprar()

    assert not repetida.ok
    assert "Ya tienes" in repetida.problema
    assert gemas() == saldo
    assert db.ropero("u1", "g1") == {"corona"}


def test_sin_gachamon_activo_se_compra_igual_y_va_al_ropero():
    """Antes hacía falta uno activo porque comprar era ponérselo. Ahora el
    ropero es tuyo, así que puedes comprar y equipar cuando tengas a quién."""
    con_gemas(200)
    resultado = comprar()

    assert resultado.ok
    assert resultado.criatura is None
    assert db.ropero("u1", "g1") == {"corona"}
    assert gemas() == 200 - CORONA.precio


def test_un_cosmetico_que_no_es_del_catalogo_no_se_cuela():
    nacer()
    con_gemas(200)
    falso = cos.Cosmetico("corona", cos.SOMBRERO, "Corona de mentira", "xx")

    with pytest.raises(ValueError):
        economia.comprar_cosmetico("u1", "g1", falso)
    with pytest.raises(ValueError):
        economia.equipar_cosmetico("u1", "g1", falso)
    with pytest.raises(ValueError):
        economia.quitar_cosmetico("u1", "g1", "peluca")
    assert gemas() == 200


# --- Poner y quitar --------------------------------------------------------

def test_desequipar_no_pierde_el_cosmetico():
    """Lo pedido: te lo quitas, sigue siendo tuyo y te lo puedes volver a poner
    sin pagar otra vez."""
    nacer()
    con_gemas(200)
    comprar(CORONA)
    saldo = gemas()

    quitada = quitar(cos.SOMBRERO)

    assert quitada.ok
    assert quitada.sustituido == CORONA
    assert activa().sombrero is None
    assert db.ropero("u1", "g1") == {"corona"}

    devuelta = poner(CORONA)

    assert devuelta.ok
    assert activa().sombrero == "corona"
    assert gemas() == saldo          # ponérsela otra vez es gratis


def test_otro_del_mismo_tipo_no_destruye_al_anterior():
    """Lo que cambia respecto de antes: la corona que se quita para dejar sitio
    a la chistera sigue en el ropero."""
    nacer()
    con_gemas(200)
    comprar(CORONA)

    resultado = comprar(CHISTERA)

    assert resultado.ok
    assert resultado.sustituido == CORONA
    assert activa().sombrero == "chistera"
    assert db.ropero("u1", "g1") == {"corona", "chistera"}
    assert poner(CORONA).ok
    assert activa().sombrero == "corona"


def test_la_corona_se_puede_pasar_de_un_gachamon_a_otro():
    """El sentido de que el ropero sea tuyo: antes hacían falta dos coronas."""
    primero = nacer(nombre="Primero")
    segundo = db.crear("u1", "g1", "michi", "Segundo", STATS, T0, activa=False)
    con_gemas(200)
    comprar(CORONA)
    quitar(cos.SOMBRERO)

    db.activar(segundo.id, "u1", "g1", T0)
    assert poner(CORONA).ok

    assert db.por_id(segundo.id).sombrero == "corona"
    assert db.por_id(primero.id).sombrero is None
    assert gemas() == 200 - CORONA.precio   # una sola corona pagada


def test_no_se_puede_poner_lo_que_no_tienes():
    """El menú de personalizar caduca en dos minutos, pero se comprueba dentro
    de la transacción: no puede vestirse con lo que no ha comprado."""
    nacer()
    con_gemas(0)

    resultado = poner(CORONA)

    assert not resultado.ok
    assert "No tienes" in resultado.problema
    assert activa().sombrero is None


def test_quitar_lo_que_no_lleva_no_hace_nada():
    nacer()
    resultado = quitar(cos.SOMBRERO)

    assert not resultado.ok
    assert "no lleva nada" in resultado.problema


def test_poner_lo_que_ya_lleva_lo_dice_y_no_lo_repite():
    nacer()
    con_gemas(200)
    comprar(CORONA)

    resultado = poner(CORONA)

    assert not resultado.ok
    assert "ya lo lleva puesto" in resultado.problema


def test_los_de_tipos_distintos_conviven():
    nacer()
    con_gemas(300)
    comprar(CORONA)
    resultado = comprar(ROJO)

    assert resultado.sustituido is None
    puesta = activa()
    assert (puesta.sombrero, puesta.tinte) == ("corona", "tinte_rojo")


def test_el_ropero_sobrevive_a_la_muerte_de_todo_el_plantel():
    """Es tuyo, no suyo: se te mueren todos y sigues teniendo la corona."""
    nacer()
    con_gemas(200)
    comprar(CORONA)

    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre'",
            (T0.isoformat(),),
        )

    assert db.ropero("u1", "g1") == {"corona"}


def test_el_ropero_es_de_cada_persona_y_de_cada_servidor():
    nacer()
    nacer(usuario="u2", nombre="Ajeno")
    con_gemas(200)
    comprar(CORONA)

    assert db.ropero("u1", "g1") == {"corona"}
    assert db.ropero("u2", "g1") == frozenset()
    assert db.ropero("u1", "g2") == frozenset()


def test_lo_puesto_sobrevive_a_guardar_y_recargar():
    """Las cuatro columnas tienen que ir en `CAMPOS`, o se perderían en el
    primer cuidado."""
    bicho = nacer()
    con_gemas(300)
    comprar(CORONA)
    comprar(ROJO)

    db.guardar(db.por_id(bicho.id))

    otra_vez = db.por_id(bicho.id)
    assert (otra_vez.sombrero, otra_vez.tinte) == ("corona", "tinte_rojo")


# --- La mudanza de lo que ya estaba puesto ---------------------------------

def test_lo_puesto_se_muda_al_ropero_de_su_dueño():
    """Antes de esto, comprar era ponérselo y no había ropero. Lo que cada
    gachamon llevara encima pasa a ser de su dueño y **se queda puesto**."""
    bicho = nacer()
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET sombrero = 'corona', tinte = 'tinte_rojo' "
            "WHERE id = ?", (bicho.id,),
        )
        con.execute("DELETE FROM ropero")

    db.inicializar()

    assert db.ropero("u1", "g1") == {"corona", "tinte_rojo"}
    puesto = db.por_id(bicho.id)
    assert (puesto.sombrero, puesto.tinte) == ("corona", "tinte_rojo")


def test_la_mudanza_dos_veces_deja_lo_mismo():
    """Corre en cada arranque; a partir de la segunda tiene que ser inocua."""
    bicho = nacer()
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET sombrero = 'corona' WHERE id = ?", (bicho.id,)
        )
        con.execute("DELETE FROM ropero")

    db.inicializar()
    primera = db.ropero("u1", "g1")
    db.inicializar()
    db.inicializar()

    assert db.ropero("u1", "g1") == primera == {"corona"}


# --- Lo que se ve ----------------------------------------------------------

def test_los_dos_desplegables_de_la_tienda_caben_en_discord():
    """Veinticinco opciones por lista es el tope, y son 15 objetos + 23
    cosméticos: por eso van en dos y no en una. Los números salen del catálogo,
    no escritos aquí, para que esto avise al crecer."""
    import objetos as obj

    consumibles = tienda.MenuTienda()
    cosmeticos = tienda.MenuCosmeticos()

    assert len(consumibles.options) == len(obj.CATALOGO) <= 25
    assert len(cosmeticos.options) == len(cos.CATALOGO) <= 25
    for menu in (consumibles, cosmeticos):
        assert all(1 <= len(o.label) <= 100 for o in menu.options)
    # Y los dos juntos NO caben, que es el motivo de que estén separados.
    assert len(obj.CATALOGO) + len(cos.CATALOGO) > 25


def test_los_dos_desplegables_de_la_tienda_se_etiquetan_a_juego():
    """Reportado jugando: arriba ponía «¿Qué compras?» y abajo «💎 Cosméticos»,
    y uno al lado del otro no se leían como una pareja.

    La regla es la del sitio, no la del menú: **compartiendo mensaje se
    etiqueta**, porque lo que hace falta es distinguir en cuál mirar; el emoji
    de la moneda es de paso lo que dice con qué se paga cada lista.
    """
    consumibles = tienda.MenuTienda().placeholder
    cosmeticos = tienda.MenuCosmeticos().placeholder

    assert consumibles == "🪙 Consumibles"
    assert cosmeticos == "💎 Cosméticos"
    for etiqueta in (consumibles, cosmeticos):
        assert "?" not in etiqueta and "¿" not in etiqueta, etiqueta


def test_los_dos_de_personalizar_tambien_van_a_juego():
    nacer()
    poner = tienda.MenuPonerCosmetico(frozenset({"corona"})).placeholder
    quitar = tienda.MenuQuitarCosmetico(activa()).placeholder

    assert (poner, quitar) == ("Ponerle…", "Quitarle…")


def test_el_desplegable_que_va_solo_en_su_mensaje_si_pregunta():
    """La otra mitad de la regla, para que no se lea como «prohibido preguntar»
    y alguien vaya a igualar también éstos: van solos, no hay con qué
    confundirlos, y preguntar se lee mejor."""
    import equipo

    assert tienda.MenuInventario({}).placeholder == "¿Qué usas?"
    assert equipo.MenuPlantel([], None, None, None).placeholder == "¿A cuál sacas?"


def test_la_tienda_marca_lo_que_ya_tienes_en_vez_de_ofrecerlo():
    menu = tienda.MenuCosmeticos(frozenset({"corona"}))
    por_valor = {o.value: o.label for o in menu.options}

    assert "ya lo tienes" in por_valor["corona"]
    assert f"💎 {CHISTERA.precio}" in por_valor["chistera"]


def test_el_menu_de_quitar_solo_lista_lo_puesto():
    """No puede pasar de cuatro opciones pase lo que pase con el catálogo, que
    es justamente por lo que va aparte del de poner."""
    nacer()
    con_gemas(300)
    comprar(CORONA)
    comprar(ROJO)

    menu = tienda.MenuQuitarCosmetico(activa())

    assert {o.value for o in menu.options} == {cos.SOMBRERO, cos.TINTE}
    assert len(menu.options) <= len(cos.TIPOS) <= 25


def test_el_menu_de_poner_solo_lista_lo_que_tienes():
    menu = tienda.MenuPonerCosmetico(frozenset({"corona", "tinte_rojo"}))
    assert {o.value for o in menu.options} == {"corona", "tinte_rojo"}


def test_personalizar_dice_lo_que_lleva_y_cuanto_tienes():
    nacer()
    con_gemas(200)
    assert "ropero está vacío" in tienda.texto_de_personalizacion("u1", "g1")

    comprar(CORONA)
    texto = tienda.texto_de_personalizacion("u1", "g1")
    assert "Corona" in texto and "Mia" in texto and "**1** pieza" in texto


def test_personalizar_sin_gachamon_lo_dice():
    assert "No tienes ningún gachamon activo" in tienda.texto_de_personalizacion(
        "u1", "g1"
    )


def test_el_recibo_avisa_de_lo_que_se_le_quita_y_de_que_no_se_pierde():
    """Cobrarle sesenta gemas a alguien y quitarle la corona sin decírselo sería
    una faena; y hacerle creer que la ha perdido, otra."""
    nacer()
    con_gemas(200)
    comprar(CORONA)
    resultado = comprar(CHISTERA)

    texto = tienda.texto_resultado_compra_cosmetico(resultado, CHISTERA)
    assert "Chistera" in texto
    assert "Corona" in texto and "vuelve a tu ropero" in texto
    assert f"-{CHISTERA.precio}" in texto


def test_el_recibo_de_quitar_dice_que_sigue_siendo_tuyo():
    nacer()
    con_gemas(200)
    comprar(CORONA)

    texto = tienda.texto_resultado_quitar(quitar(cos.SOMBRERO))

    assert "Corona" in texto
    assert "Sigue en tu ropero" in texto


def test_el_recibo_de_lo_que_no_se_pudo_comprar_explica_por_que():
    nacer()
    con_gemas(0)
    resultado = comprar(CORONA)

    texto = tienda.texto_resultado_compra_cosmetico(resultado, CORONA)
    assert texto.startswith("❌")
    assert "logros" in texto


# --- Con los logros, de punta a punta ---------------------------------------

def test_las_gemas_de_los_logros_pagan_un_cosmetico():
    """El círculo entero: ganar medallas, cobrarlas y gastárselas."""
    bicho = nacer()
    db.apuntar(bicho.id, logros.CARRERAS, 100)
    recibo = economia.pagar_logros(bicho, T0)
    assert recibo.asciigems >= CORONA.precio

    resultado = comprar(CORONA)

    assert resultado.ok
    assert resultado.saldo == recibo.saldo - CORONA.precio
