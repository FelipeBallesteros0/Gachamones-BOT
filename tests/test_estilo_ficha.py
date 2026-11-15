"""El estilo de ficha ya no se usa, pero su tabla se queda con sus datos."""
import sqlite3

import pytest

import db


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "estilo-ficha.db")
    db.inicializar()


def test_la_restriccion_rechaza_un_estilo_invalido_por_sql():
    with db.conectar() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO estilos_ficha (usuario_id, guild_id, estilo) "
            "VALUES ('u1', 'g1', 'automatico')"
        )
