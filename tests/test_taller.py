"""Comprar cosméticos: cobrar bien, sustituir bien y no cobrar de más."""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import economia
import logros
import simulacion as sim
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
ROJO = cos.CATALOGO["tinte_rojo"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "taller.db")
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


# --- Cobrar ----------------------------------------------------------------

def test_comprar_cobra_las_gemas_y_se_lo_pone():
    nacer()
    con_gemas(100)

    resultado = comprar()

    assert resultado.ok
    assert resultado.criatura.sombrero == "corona"
    assert gemas() == 100 - CORONA.precio
    assert resultado.saldo == gemas()
    # Y queda guardado, no sólo en el objeto devuelto.
    assert db.criatura_activa("u1", "g1").sombrero == "corona"


def test_sin_gemas_suficientes_no_se_cobra_ni_se_pone_nada():
    nacer()
    con_gemas(CORONA.precio - 1)

    resultado = comprar()

    assert not resultado.ok
    assert "faltan 1 asciigems" in resultado.problema
    assert gemas() == CORONA.precio - 1
    assert db.criatura_activa("u1", "g1").sombrero is None


def test_el_saldo_nunca_se_queda_en_negativo():
    """La condición viaja dentro del UPDATE justamente para esto."""
    nacer()
    con_gemas(0)

    for _ in range(3):
        assert not comprar().ok
    assert gemas() == 0


def test_comprar_lo_que_ya_lleva_no_cuesta_nada():
    """El doble clic: dos compras del mismo sombrero cobrarían 120 gemas y
    dejarían un sombrero."""
    nacer()
    con_gemas(200)
    comprar()
    saldo = gemas()

    repetida = comprar()

    assert not repetida.ok
    assert "ya lo lleva puesto" in repetida.problema
    assert gemas() == saldo


def test_sin_gachamon_activo_no_se_compra():
    con_gemas(200)
    resultado = comprar()

    assert not resultado.ok
    assert "ningún gachamon activo" in resultado.problema
    assert gemas() == 200


def test_un_cosmetico_que_no_es_del_catalogo_no_se_cuela():
    nacer()
    con_gemas(200)
    falso = cos.Cosmetico("corona", cos.SOMBRERO, "Corona de mentira", "xx")

    with pytest.raises(ValueError):
        economia.comprar_cosmetico("u1", "g1", falso)
    assert gemas() == 200


# --- Uno de cada tipo ------------------------------------------------------

def test_otro_del_mismo_tipo_sustituye_al_anterior():
    nacer()
    con_gemas(200)
    comprar(CORONA)

    resultado = comprar(CHISTERA)

    assert resultado.ok
    assert resultado.sustituido == CORONA
    assert db.criatura_activa("u1", "g1").sombrero == "chistera"
    assert gemas() == 200 - CORONA.precio - CHISTERA.precio


def test_los_de_tipos_distintos_conviven():
    nacer()
    con_gemas(300)
    comprar(CORONA)
    resultado = comprar(ROJO)

    assert resultado.sustituido is None
    puesta = db.criatura_activa("u1", "g1")
    assert (puesta.sombrero, puesta.tinte) == ("corona", "tinte_rojo")


def test_lo_comprado_es_del_gachamon_y_no_de_la_persona():
    """Como las medallas: si cambias de activo, la corona se queda con el que la
    llevaba."""
    coronado = nacer(nombre="Coronado")
    otro = db.crear("u1", "g1", "michi", "Otro", STATS, T0, activa=False)
    con_gemas(200)
    comprar()

    assert db.por_id(coronado.id).sombrero == "corona"
    assert db.por_id(otro.id).sombrero is None


def test_lo_puesto_sobrevive_a_guardar_y_recargar():
    """Las cuatro columnas nuevas tienen que ir en `CAMPOS`, o se perderían en
    el primer cuidado."""
    bicho = nacer()
    con_gemas(300)
    comprar(CORONA)
    comprar(ROJO)

    recargada = db.por_id(bicho.id)
    db.guardar(recargada)

    otra_vez = db.por_id(bicho.id)
    assert (otra_vez.sombrero, otra_vez.tinte) == ("corona", "tinte_rojo")


# --- Lo que se ve ----------------------------------------------------------

def test_el_menu_cabe_en_las_opciones_de_discord():
    """Veinticinco es el tope. El día que no quepan hay que partir el menú por
    tipos, no recortar el catálogo."""
    assert len(cos.CATALOGO) <= 25
    menu = tienda.MenuTaller()
    assert len(menu.options) == len(cos.CATALOGO)
    assert all(1 <= len(o.label) <= 100 for o in menu.options)


def test_el_taller_dice_lo_que_lleva_puesto():
    nacer()
    con_gemas(200)
    assert "no lleva nada puesto" in tienda.texto_del_taller("u1", "g1")

    comprar(CORONA)
    texto = tienda.texto_del_taller("u1", "g1")
    assert "Corona" in texto and "Mia" in texto


def test_el_taller_sin_gachamon_lo_dice_y_no_ofrece_menu():
    assert "No tienes ningún gachamon activo" in tienda.texto_del_taller("u1", "g1")


def test_el_recibo_avisa_de_lo_que_se_pierde():
    """Cobrarle sesenta gemas a alguien y quitarle la corona sin decírselo sería
    una faena."""
    nacer()
    con_gemas(200)
    comprar(CORONA)
    resultado = comprar(CHISTERA)

    texto = tienda.texto_resultado_cosmetico(resultado, CHISTERA)
    assert "Chistera" in texto
    assert "Se queda sin **Corona**" in texto
    assert f"-{CHISTERA.precio}" in texto


def test_el_recibo_de_lo_que_no_se_pudo_comprar_explica_por_que():
    nacer()
    con_gemas(0)
    resultado = comprar(CORONA)

    texto = tienda.texto_resultado_cosmetico(resultado, CORONA)
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
