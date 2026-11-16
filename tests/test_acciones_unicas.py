"""Repetir una compra con el mismo evento no la cobra dos veces.

La web manda un evento con cada compra y, si la respuesta no le llega, repite la
petición con ese mismo evento. Sin evento —Discord— todo sigue como antes.
"""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import departamento as dep
import economia

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
OTRA = "u2"
STATS = (15, 15, 15, 15)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
FELPUDO = dep.MUEBLES["felpudo"]


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


def guardados(usuario=U):
    return [p.clave for p in db.departamento_leido(usuario, G).guardadas]


# --- Si anotar falla ---------------------------------------------------------

def test_si_anotar_la_compra_falla_no_se_cobra_ni_queda_mueble(base, monkeypatch):
    dar_monedas(U, 1000)

    def revienta(*_args, **_kwargs):
        raise RuntimeError("no se pudo anotar")

    monkeypatch.setattr(db, "anotar_accion_en", revienta)
    with pytest.raises(RuntimeError):
        economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-mueble-9")
    assert economia.saldos(U, G).asciicoins == 1000
    assert "felpudo" not in guardados()
    assert anotadas() == 0


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


# --- De quién es el evento --------------------------------------------------

def test_el_mismo_evento_de_otra_persona_no_es_un_replay(base):
    dar_monedas(U, 1000)
    dar_monedas(OTRA, 1000)
    assert economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-mueble-1").ok
    suya = economia.comprar_mueble(OTRA, G, FELPUDO, T0, evento_id="evento-mueble-1")
    assert suya.ok and not suya.replay
    assert guardados(OTRA).count("felpudo") == 1
    assert economia.saldos(OTRA, G).asciicoins == 1000 - FELPUDO.precio


# --- Lo que se anota --------------------------------------------------------

def test_sin_evento_no_se_anota_nada(base):
    nace()
    dar_monedas(U, 5000)
    dar_gemas(U, 500)
    economia.comprar_mueble(U, G, FELPUDO, T0)
    economia.ampliar_departamento(U, G, dep.ANCHO, T0)
    economia.comprar_cosmetico(U, G, CORONA)
    assert anotadas() == 0


def test_un_rechazo_no_se_anota(base):
    dar_monedas(U, 0)
    dar_gemas(U, 0)
    assert economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-1c").motivo == "faltan_monedas"
    economia.comprar_cosmetico(U, G, CORONA, evento_id="evento-1d")
    assert economia.ampliar_departamento(U, G, dep.ANCHO, T0, evento_id="evento-1e").motivo == "faltan_monedas"
    assert anotadas() == 0


def test_lo_anotado_se_lee_tal_cual(base):
    with db.conectar() as con:
        assert db.accion_hecha_en(con, "evento-1", U, G, "mueble") is None
        db.anotar_accion_en(
            con, "evento-1", U, G, "mueble", "felpudo", {"mueble_id": 3, "nota": None},
            T0,
        )
        assert db.accion_hecha_en(con, "evento-1", U, G, "mueble") == (
            "felpudo", {"mueble_id": 3, "nota": None}
        )
        assert db.accion_hecha_en(con, "evento-1", U, G, "ampliar") is None
        assert db.accion_hecha_en(con, "evento-1", OTRA, G, "mueble") is None


def test_arrancar_otra_vez_no_borra_lo_anotado(base):
    dar_monedas(U, 1000)
    economia.comprar_mueble(U, G, FELPUDO, T0, evento_id="evento-mueble-1")
    db.inicializar()
    assert anotadas() == 1
