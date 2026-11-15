"""Bautizar a un gachamon concreto es una regla del juego: `nacer.bautizar_a`."""
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import nacer
from test_camas import poner_camas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
U = "222222222222222222"     # una identidad de Discord
OTRA = "333333333333333333"
G = "g"


@pytest.fixture(autouse=True)
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "bautizar.db")
    db.inicializar()


def nace(nombre, activa=True, usuario=U, guild=G, se_nombro_solo=False):
    return db.crear(
        usuario, guild, "pollito", nombre, STATS, T0, activa=activa,
        se_nombro_solo=se_nombro_solo,
    )


def recluta_de(nombre="Brote", **cambios):
    """Un recluta: no es el activo y se puso el nombre él solo."""
    return nace(nombre, activa=False, se_nombro_solo=True, **cambios)


def test_bautizar_a_un_recluta():
    activa = nace("Ana")
    recluta = recluta_de()
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET hambre = 42 WHERE id = ?", (recluta.id,))
    antes = db.por_id(recluta.id)

    bautizada = nacer.bautizar_a(
        U, G, recluta.id, "  Pelusa ", T0 + timedelta(hours=5)
    )

    assert bautizada.nombre == "Pelusa"
    assert bautizada.hambre == 42
    # Sólo se escribe el nombre: el resto de la fila sigue como estaba en la base.
    assert db.por_id(recluta.id) == replace(antes, nombre="Pelusa", se_nombro_solo=False)
    assert db.criatura_activa(U, G).id == activa.id
    assert db.por_id(activa.id) == activa


def test_bautizar_a_rechaza_el_nombre_de_su_especie():
    nace("Ana")
    recluta = recluta_de()

    with pytest.raises(nacer.NombreNoVale) as error:
        nacer.bautizar_a(
            U, G, recluta.id, recluta.def_especie.nombre.upper(), T0
        )

    assert str(error.value) == "Ese es el nombre de su especie. Ponle uno propio."
    assert db.por_id(recluta.id).nombre == "Brote"


def test_bautizar_a_rechaza_un_nombre_que_no_vale():
    nace("Ana")
    recluta = recluta_de()

    with pytest.raises(nacer.NombreNoVale, match="letras, números"):
        nacer.bautizar_a(U, G, recluta.id, "**Luna**", T0)

    assert db.por_id(recluta.id).nombre == "Brote"


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
    ajena = recluta_de("Mote", usuario=OTRA)
    de_otro_servidor = recluta_de("Miga", guild="otro")
    muerta = recluta_de("Nube")
    db.guardar(replace(muerta, muerta_en=T0, causa_muerte="hambre"))

    for criatura_id in (ajena.id, de_otro_servidor.id, muerta.id, 9999):
        with pytest.raises(nacer.NoSePuedeBautizar) as error:
            nacer.bautizar_a(U, G, criatura_id, "Pelusa", T0)
        assert error.value.motivo == nacer.NO_ESTA == "no_esta"
        assert str(error.value) == "Ese gachamon ya no está."

    for criatura in (ajena, de_otro_servidor, muerta):
        assert db.por_id(criatura.id).nombre == criatura.nombre


def test_al_que_se_nombro_solo_se_le_cambia_el_nombre_una_vez():
    nace("Ana")
    poner_camas(U, 2, G)
    recluta = nacer.unir_recluta(
        U, G, especie="pollito", stats=STATS, genero=esp.MACHO,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(5),
    )

    with pytest.raises(nacer.NombreNoVale):
        nacer.bautizar_a(U, G, recluta.id, recluta.def_especie.nombre, T0)
    assert db.por_id(recluta.id) == recluta              # sigue pudiendo

    bautizada = nacer.bautizar_a(U, G, recluta.id, "Rayo", T0)

    assert bautizada.nombre == "Rayo" and bautizada.se_nombro_solo is False
    assert db.por_id(recluta.id) == bautizada
    with pytest.raises(nacer.NoSePuedeBautizar) as error:
        nacer.bautizar_a(U, G, recluta.id, "Otra", T0)
    assert error.value.motivo == nacer.YA_BAUTIZADO
    assert db.por_id(recluta.id).nombre == "Rayo"
