"""Los rechazos de compra dicen por qué, con una clave, además de su frase."""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import departamento as dep
import economia
import objetos as obj

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
SOMBRERO = next(c for c in cos.CATALOGO.values() if c.tipo == cos.SOMBRERO)


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "motivos.db")
    db.inicializar()


def dar(monedas=0, gemas=0, usuario=U):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, G)
        con.execute(
            "UPDATE monederos SET asciicoins = ?, asciigems = ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (monedas, gemas, usuario, G),
        )


def rechazo(resultado, motivo):
    assert resultado.ok is False
    assert resultado.motivo == motivo
    assert isinstance(resultado.problema, str) and resultado.problema


# --- Lo que no se vende ----------------------------------------------------

def test_lo_que_no_se_vende_no_se_compra(base):
    poroto = obj.CATALOGO["poroto_rojo"]
    assert not poroto.se_vende
    with pytest.raises(ValueError):
        economia.comprar("evento-0001", U, G, poroto, T0)
    assert db.inventario(U, G) == {}


def test_a_la_venta_es_el_catalogo_sin_lo_que_se_cosecha_o_se_cocina():
    """Ni la semilla, desde que se fue el huerto por casa."""
    claves = [o.clave for o in obj.a_la_venta()]
    assert claves == [c for c, o in obj.CATALOGO.items() if o.se_vende]
    assert len(claves) == 15 and "semilla" not in claves and "poroto_rojo" not in claves


# --- Cosméticos ------------------------------------------------------------

def test_el_cosmetico_que_ya_tienes_dice_ya_lo_tienes(base):
    dar(gemas=500)
    assert economia.comprar_cosmetico(U, G, SOMBRERO).ok
    rechazo(economia.comprar_cosmetico(U, G, SOMBRERO), "ya_lo_tienes")


def test_el_cosmetico_sin_gemas_suficientes_dice_faltan_gemas(base):
    dar(gemas=0)
    rechazo(economia.comprar_cosmetico(U, G, SOMBRERO), "faltan_gemas")


# --- Lo que sale bien no lleva motivo ---------------------------------------

def test_todo_lo_que_sale_bien_lleva_motivo_none(base):
    dar(monedas=5000, gemas=500)
    resultados = [economia.comprar_cosmetico(U, G, SOMBRERO)]
    comprado = economia.comprar_mueble(U, G, dep.MUEBLES["felpudo"], T0)
    resultados += [
        comprado,
        economia.poner_mueble(U, G, comprado.mueble_id, 2, 2, 0, T0),
        economia.guardar_mueble(U, G, comprado.mueble_id, T0),
        economia.ampliar_departamento(U, G, dep.ANCHO, T0),
    ]
    assert all(r.ok for r in resultados)
    assert all(r.motivo is None for r in resultados)
