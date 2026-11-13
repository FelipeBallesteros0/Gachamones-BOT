"""Repetir una compra con el mismo evento no la cobra dos veces.

La web manda un evento con cada compra y, si la respuesta no le llega, repite la
petición con ese mismo evento. Sin evento —Discord— todo sigue como antes.
"""
from datetime import datetime, timezone

import pytest

import casas
import cosmeticos as cos
import db
import economia

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
OTRA = "u2"
STATS = (15, 15, 15, 15)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
FELPUDO = casas.MUEBLES["felpudo"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "acciones.db")
    db.inicializar()


def dar_monedas(usuario, cuantas):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, G)
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? "
            "AND guild_id = ?",
            (cuantas, usuario, G),
        )


def dar_gemas(usuario, cuantas):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, G)
        con.execute(
            "UPDATE monederos SET asciigems = ? WHERE usuario_id = ? "
            "AND guild_id = ?",
            (cuantas, usuario, G),
        )


def nace(nombre="Kuro", usuario=U):
    return db.crear(usuario, G, "pulpo", nombre, STATS, T0)


def anotadas():
    with db.conectar() as con:
        return con.execute("SELECT COUNT(*) AS n FROM acciones_unicas").fetchone()["n"]


# --- La casa ---------------------------------------------------------------

def test_repetir_la_compra_de_una_casa_con_el_mismo_evento_no_compra_otra(base):
    dar_monedas(U, 1000)
    pequena = casas.CATALOGO["pequena"]
    primera = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    segunda = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    assert primera.ok and not primera.replay
    assert segunda.ok and segunda.replay and segunda.casa_id == primera.casa_id
    assert len(db.hogar_leido(U, G, T0).casas) == 1
    assert economia.saldos(U, G).asciicoins == 1000 - pequena.precio == segunda.saldo


def test_sin_evento_cada_compra_de_casa_es_otra_casa(base):
    dar_monedas(U, 1000)
    pequena = casas.CATALOGO["pequena"]
    assert economia.comprar_casa(U, G, pequena, T0).ok and economia.comprar_casa(U, G, pequena, T0).ok
    assert len(db.hogar_leido(U, G, T0).casas) == 2


def test_un_evento_no_sirve_para_otra_cosa(base):
    dar_monedas(U, 2000)
    economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0, evento_id="evento-casa-1")
    with pytest.raises(RuntimeError):
        economia.comprar_casa(U, G, casas.CATALOGO["mediana"], T0, evento_id="evento-casa-1")


def test_un_rechazo_no_gasta_el_evento(base):
    pequena = casas.CATALOGO["pequena"]
    assert economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1").motivo == "faltan_monedas"
    dar_monedas(U, 1000)
    hecha = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    assert hecha.ok and not hecha.replay


def test_otra_casa_y_mejorar_una_son_peticiones_distintas(base):
    dar_monedas(U, 5000)
    pequena = casas.CATALOGO["pequena"]
    nueva = economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1")
    with pytest.raises(RuntimeError):
        economia.comprar_casa(
            U, G, pequena, T0, mejorar=nueva.casa_id, evento_id="evento-casa-1"
        )
    assert economia.saldos(U, G).asciicoins == 5000 - pequena.precio


def test_repetir_una_mejora_no_dice_que_no_se_puede_empeorar(base):
    dar_monedas(U, 5000)
    pequena, mediana = casas.CATALOGO["pequena"], casas.CATALOGO["mediana"]
    casa_id = economia.comprar_casa(U, G, pequena, T0).casa_id
    antes = economia.saldos(U, G).asciicoins
    primera = economia.comprar_casa(
        U, G, mediana, T0, mejorar=casa_id, evento_id="evento-mejora-1"
    )
    segunda = economia.comprar_casa(
        U, G, mediana, T0, mejorar=casa_id, evento_id="evento-mejora-1"
    )
    assert primera.ok and not primera.replay
    assert segunda.ok and segunda.replay and segunda.motivo is None
    assert segunda.casa == mediana and segunda.desde == pequena
    assert segunda.casa_id == primera.casa_id == casa_id
    cobrado = mediana.precio - casas.lo_que_dan_por(pequena)
    assert economia.saldos(U, G).asciicoins == antes - cobrado == segunda.saldo
    assert [c.casa for c in db.hogar_leido(U, G, T0).casas] == [mediana]


# --- La venta --------------------------------------------------------------

def test_repetir_una_venta_con_el_mismo_evento_no_cobra_otra_vez(base):
    dar_monedas(U, 5000)
    pequena = casas.CATALOGO["pequena"]
    casa_id = economia.comprar_casa(U, G, pequena, T0).casa_id
    nace()
    economia.comprar_mueble(U, G, FELPUDO, T0, casa_id=casa_id)
    antes = economia.saldos(U, G).asciicoins
    primera = economia.vender_casa(U, G, casa_id, T0, evento_id="evento-venta-1")
    segunda = economia.vender_casa(U, G, casa_id, T0, evento_id="evento-venta-1")
    assert primera.ok and not primera.replay
    assert (primera.guardados, primera.desalojados) == (1, 1)
    assert segunda.ok and segunda.replay and segunda.motivo is None
    assert segunda.cobrado == primera.cobrado == casas.lo_que_dan_por(pequena)
    assert segunda.casa == pequena
    assert (segunda.guardados, segunda.desalojados) == (1, 1)
    assert economia.saldos(U, G).asciicoins == antes + primera.cobrado == segunda.saldo


def test_una_venta_rechazada_no_gasta_el_evento(base):
    dar_monedas(U, 5000)
    assert economia.vender_casa(U, G, 1, T0, evento_id="evento-venta-1").motivo == "sin_casa"
    casa_id = economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0).casa_id
    hecha = economia.vender_casa(U, G, casa_id, T0, evento_id="evento-venta-1")
    assert hecha.ok and not hecha.replay


# --- El cosmético ----------------------------------------------------------

def test_repetir_la_compra_de_un_cosmetico_con_el_mismo_evento_no_cobra_otra_vez(base):
    nace()
    dar_gemas(U, 500)
    assert economia.comprar_cosmetico(U, G, CHISTERA).ok
    antes = economia.saldos(U, G).asciigems
    primera = economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-corona-1")
    segunda = economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-corona-1")
    assert primera.ok and not primera.replay and primera.sustituido == CHISTERA
    assert segunda.ok and segunda.replay and segunda.motivo is None
    assert segunda.sustituido == primera.sustituido == CHISTERA
    assert economia.saldos(U, G).asciigems == antes - CORONA.precio == segunda.saldo
    assert segunda.criatura is not None and segunda.criatura.sombrero == "corona"


def test_el_replay_del_cosmetico_trae_al_activo_de_ahora(base):
    dar_gemas(U, 500)
    sin_nadie = economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-corona-1")
    assert sin_nadie.ok and sin_nadie.criatura is None and sin_nadie.sustituido is None
    kuro = nace()
    segunda = economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-corona-1")
    assert segunda.ok and segunda.replay and segunda.sustituido is None
    assert segunda.criatura is not None and segunda.criatura.id == kuro.id
    assert economia.saldos(U, G).asciigems == 500 - CORONA.precio


# --- El mueble -------------------------------------------------------------

def test_repetir_la_compra_de_un_mueble_con_el_mismo_evento_no_cobra_otra_vez(base):
    dar_monedas(U, 5000)
    casa_id = economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0).casa_id
    antes = economia.saldos(U, G).asciicoins
    primera = economia.comprar_mueble(
        U, G, FELPUDO, T0, casa_id=casa_id, evento_id="evento-felpudo-1"
    )
    # Retirarlo después no cambia lo que pasó al comprarlo.
    assert economia.retirar_mueble(U, G, FELPUDO, T0, casa_id=casa_id).ok
    segunda = economia.comprar_mueble(
        U, G, FELPUDO, T0, casa_id=casa_id, evento_id="evento-felpudo-1"
    )
    assert primera.ok and not primera.replay and primera.colocado is True
    assert segunda.ok and segunda.replay and segunda.motivo is None
    assert segunda.colocado is primera.colocado is True
    assert segunda.mueble == FELPUDO
    assert segunda.casa == casas.CATALOGO["pequena"] and segunda.puestos == 0
    assert economia.saldos(U, G).asciicoins == antes - FELPUDO.precio == segunda.saldo


def test_el_replay_del_mueble_en_una_casa_ya_vendida_no_nombra_casa(base):
    dar_monedas(U, 5000)
    casa_id = economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0).casa_id
    economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-felpudo-1")
    assert economia.vender_casa(U, G, casa_id, T0).ok
    antes = economia.saldos(U, G).asciicoins
    segunda = economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-felpudo-1")
    assert segunda.ok and segunda.replay and segunda.colocado is True
    assert (segunda.casa, segunda.comodidad, segunda.puestos) == (None, 0, 0)
    assert economia.saldos(U, G).asciicoins == antes == segunda.saldo


def test_el_mismo_mueble_en_otra_casa_es_otra_peticion(base):
    dar_monedas(U, 5000)
    casa_id = economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0).casa_id
    economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-felpudo-1")
    with pytest.raises(RuntimeError):
        economia.comprar_mueble(
            U, G, FELPUDO, T0, casa_id=casa_id, evento_id="evento-felpudo-1"
        )


# --- De quién es el evento --------------------------------------------------

def test_el_mismo_evento_de_otra_persona_no_es_un_replay(base):
    dar_monedas(U, 1000)
    dar_monedas(OTRA, 1000)
    pequena = casas.CATALOGO["pequena"]
    assert economia.comprar_casa(U, G, pequena, T0, evento_id="evento-casa-1").ok
    suya = economia.comprar_casa(OTRA, G, pequena, T0, evento_id="evento-casa-1")
    assert suya.ok and not suya.replay
    assert len(db.hogar_leido(OTRA, G, T0).casas) == 1
    assert economia.saldos(OTRA, G).asciicoins == 1000 - pequena.precio


# --- Lo que se anota --------------------------------------------------------

def test_sin_evento_no_se_anota_nada(base):
    nace()
    dar_monedas(U, 5000)
    dar_gemas(U, 500)
    casa_id = economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0).casa_id
    economia.comprar_casa(U, G, casas.CATALOGO["mediana"], T0, mejorar=casa_id)
    economia.comprar_mueble(U, G, FELPUDO, T0)
    economia.comprar_cosmetico(U, G, CORONA)
    economia.vender_casa(U, G, casa_id, T0)
    assert anotadas() == 0


def test_un_rechazo_no_se_anota(base):
    dar_monedas(U, 0)
    dar_gemas(U, 0)
    economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0, evento_id="evento-1a")
    economia.vender_casa(U, G, 1, T0, evento_id="evento-1b")
    economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-1c")
    economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-1d")
    assert anotadas() == 0


def test_lo_anotado_se_lee_tal_cual(base):
    with db.conectar() as con:
        assert db.accion_hecha_en(con, "evento-1", U, G, "casa") is None
        db.anotar_accion_en(
            con, "evento-1", U, G, "casa", "pequena", {"casa_id": 3, "desde": None},
            T0,
        )
        assert db.accion_hecha_en(con, "evento-1", U, G, "casa") == (
            "pequena", {"casa_id": 3, "desde": None}
        )
        assert db.accion_hecha_en(con, "evento-1", U, G, "venta") is None
        assert db.accion_hecha_en(con, "evento-1", OTRA, G, "casa") is None


def test_arrancar_otra_vez_no_borra_lo_anotado(base):
    dar_monedas(U, 1000)
    economia.comprar_casa(U, G, casas.CATALOGO["pequena"], T0, evento_id="evento-casa-1")
    db.inicializar()
    assert anotadas() == 1
