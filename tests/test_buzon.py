"""El buzón: un regalo sale de una mochila y entra en otro buzón a la vez.

Está en pausa —el día del cambio entrega lo que hubiera—, pero sus reglas se
quedan. Vienen de las pruebas de las casas, que se fueron con ellas.
"""
from datetime import datetime, timedelta, timezone

import pytest

import db
import huerto as hue
import objetos as objs

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GOLOSINAS = objs.CATALOGO["golosinas"]
PLACA = objs.CATALOGO["placa"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "buzon.db")
    db.inicializar()


def test_el_regalo_sale_de_tu_mochila_y_llega_a_su_buzon():
    db.regalar("u1", "g1", GOLOSINAS)

    assert db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "toma", T0
    )

    assert db.inventario("u1", "g1") == {}
    assert db.inventario("u2", "g1") == {}          # todavía en el buzón
    [regalo] = db.buzon_de("u2", "g1")
    assert regalo.objeto == GOLOSINAS.clave
    assert regalo.de_nombre == "Felipe" and regalo.nota == "toma"


def test_no_se_puede_regalar_lo_que_no_tienes():
    """Las dos mitades van juntas: un objeto que saliera de una mochila sin
    llegar a ningún buzón se habría perdido."""
    assert not db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0
    )
    assert db.buzon_de("u2", "g1") == []


def test_recoger_lo_pasa_a_la_mochila_y_vacia_el_buzon():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    recogido = db.recoger_del_buzon("u2", "g1", regalo.id)

    assert recogido is not None and recogido.objeto == GOLOSINAS.clave
    assert db.inventario("u2", "g1") == {GOLOSINAS.clave: 1}
    assert db.buzon_de("u2", "g1") == []


def test_el_mismo_regalo_no_se_recoge_dos_veces():
    """El doble clic: la condición viaja dentro del UPDATE, como en las compras."""
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    assert db.recoger_del_buzon("u2", "g1", regalo.id) is not None
    assert db.recoger_del_buzon("u2", "g1", regalo.id) is None
    assert db.inventario("u2", "g1") == {GOLOSINAS.clave: 1}


def test_no_se_recoge_el_regalo_de_otro():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    assert db.recoger_del_buzon("u3", "g1", regalo.id) is None
    assert len(db.buzon_de("u2", "g1")) == 1


def test_la_nota_es_opcional_y_cabe_en_una_linea():
    """Una nota con saltos rompería el listado, que pinta un regalo por renglón."""
    assert db.limpiar_nota("") == ""
    assert db.limpiar_nota("dos\nlíneas   y   huecos") == "dos líneas y huecos"
    assert len(db.limpiar_nota("x" * 500)) == db.LARGO_MAXIMO_NOTA


def test_el_buzon_es_de_cada_persona_y_servidor():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)

    assert len(db.buzon_de("u2", "g1")) == 1
    assert db.buzon_de("u2", "g2") == []
    assert db.buzon_de("u1", "g1") == []


def test_el_buzon_los_lista_del_mas_viejo_al_mas_nuevo():
    for objeto in (GOLOSINAS, PLACA):
        db.regalar("u1", "g1", objeto)
    db.mandar_regalo("u1", "A", "u2", "g1", GOLOSINAS.clave, "", T0)
    db.mandar_regalo("u1", "B", "u2", "g1", PLACA.clave, "", T0 + timedelta(days=1))

    assert [r.de_nombre for r in db.buzon_de("u2", "g1")] == ["A", "B"]


def test_el_poroto_se_puede_regalar_por_el_buzon():
    """Media gracia de que haya colores: te sobran unos y te faltan otros."""
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("rojo"))

    assert db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", hue.clave_de_poroto("rojo"), "te sobran", T0
    )
    [regalo] = db.buzon_de("u2", "g1")
    assert regalo.objeto == hue.clave_de_poroto("rojo")
