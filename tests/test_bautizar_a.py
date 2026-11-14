"""Bautizar a un gachamon concreto es una regla del juego: `nacer.bautizar_a`."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import nacer

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
U = "222222222222222222"     # una identidad de Discord
OTRA = "333333333333333333"
G = "g"


@pytest.fixture(autouse=True)
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "bautizar.db")
    db.inicializar()


def nace(nombre, activa=True, usuario=U, guild=G):
    return db.crear(usuario, guild, "pollito", nombre, STATS, T0, activa=activa)


def test_bautizar_a_un_recluta():
    activa = nace("Ana")
    recluta = nace("", activa=False)
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET hambre = 42 WHERE id = ?", (recluta.id,))
    antes = db.por_id(recluta.id)

    bautizada = nacer.bautizar_a(
        U, G, recluta.id, "  Pelusa ", T0 + timedelta(hours=5)
    )

    assert bautizada.nombre == "Pelusa"
    assert bautizada.hambre == 42
    # Sólo se escribe el nombre: el resto de la fila sigue como estaba en la base.
    assert db.por_id(recluta.id) == replace(antes, nombre="Pelusa")
    assert db.criatura_activa(U, G).id == activa.id
    assert db.por_id(activa.id) == activa


def test_bautizar_a_rechaza_el_nombre_de_su_especie():
    nace("Ana")
    recluta = nace("", activa=False)

    with pytest.raises(nacer.NombreNoVale) as error:
        nacer.bautizar_a(
            U, G, recluta.id, recluta.def_especie.nombre.upper(), T0
        )

    assert str(error.value) == "Ese es el nombre de su especie. Ponle uno propio."
    assert db.por_id(recluta.id).nombre == ""


def test_bautizar_a_rechaza_un_nombre_que_no_vale():
    nace("Ana")
    recluta = nace("", activa=False)

    with pytest.raises(nacer.NombreNoVale, match="letras, números"):
        nacer.bautizar_a(U, G, recluta.id, "**Luna**", T0)

    assert db.por_id(recluta.id).nombre == ""


def test_bautizar_a_uno_con_nombre_es_ya_bautizado():
    activa = nace("Ana")
    con_nombre = nace("Bea", activa=False)

    for criatura in (activa, con_nombre):
        with pytest.raises(nacer.NoSePuedeBautizar) as error:
            nacer.bautizar_a(U, G, criatura.id, "Pelusa", T0)
        assert error.value.motivo == nacer.YA_BAUTIZADO
        assert str(error.value) == "Ese gachamon ya tiene nombre."

    assert db.por_id(activa.id).nombre == "Ana"
    assert db.por_id(con_nombre.id).nombre == "Bea"


def test_bautizar_a_uno_ajeno_o_muerto_es_no_esta():
    nace("Ana")
    ajena = nace("", activa=False, usuario=OTRA)
    de_otro_servidor = nace("", activa=False, guild="otro")
    muerta = nace("", activa=False)
    db.guardar(replace(muerta, muerta_en=T0, causa_muerte="hambre"))

    for criatura_id in (ajena.id, de_otro_servidor.id, muerta.id, 9999):
        with pytest.raises(nacer.NoSePuedeBautizar) as error:
            nacer.bautizar_a(U, G, criatura_id, "Pelusa", T0)
        assert error.value.motivo == nacer.NO_ESTA == "no_esta"
        assert str(error.value) == "Ese gachamon ya no está."

    for criatura in (ajena, de_otro_servidor, muerta):
        assert db.por_id(criatura.id).nombre == ""
