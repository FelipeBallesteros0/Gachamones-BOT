"""Preferencia pública Imagen/ASCII de las fichas."""
import sqlite3
from datetime import datetime, timezone

import pytest

import db
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "estilo-ficha.db")
    db.inicializar()


def geo(usuario="dueno", guild="g1") -> sim.Criatura:
    return db.crear(usuario, guild, "pedrusco", "Geo", STATS, T0)


def test_el_default_imagen_no_muta_ninguna_tabla_de_persona():
    assert db.estilo_de_ficha("u1", "g1") == "imagen"

    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM estilos_ficha").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM monederos").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM marcador_persona").fetchone()[0] == 0


def test_el_setter_persiste_y_aisla_el_estilo_por_servidor():
    db.guardar_estilo_de_ficha("u1", "g1", "ascii")
    db.guardar_estilo_de_ficha("u1", "g2", "imagen")
    db.inicializar()

    assert db.estilo_de_ficha("u1", "g1") == "ascii"
    assert db.estilo_de_ficha("u1", "g2") == "imagen"
    assert db.estilo_de_ficha("u2", "g1") == "imagen"


def test_la_restriccion_rechaza_un_estilo_invalido_incluso_por_sql():
    with pytest.raises(ValueError):
        db.guardar_estilo_de_ficha("u1", "g1", "automatico")

    with db.conectar() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO estilos_ficha (usuario_id, guild_id, estilo) "
            "VALUES ('u1', 'g1', 'automatico')"
        )


def test_cambiar_de_activa_conserva_el_estilo_de_la_persona():
    primera = geo()
    segunda = db.crear(
        "dueno", "g1", "chispa", "Reserva", STATS, T0, activa=False
    )
    db.guardar_estilo_de_ficha("dueno", "g1", "ascii")

    db.activar(segunda.id, "dueno", "g1")

    assert primera.id != segunda.id
    assert db.estilo_de_ficha("dueno", "g1") == "ascii"
