import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

import db


def _conectar(ruta):
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    return con


def test_migra_legacy_reiniciando_exactamente_50_50(tmp_path, monkeypatch):
    ruta = tmp_path / "legacy.db"
    with _conectar(ruta) as con:
        con.execute(
            "CREATE TABLE monederos (usuario_id TEXT, guild_id TEXT, gemas INTEGER, "
            "PRIMARY KEY (usuario_id, guild_id))"
        )
        con.execute("INSERT INTO monederos VALUES ('u', 'g', 9876)")
    monkeypatch.setattr(db, "RUTA", ruta)

    db.inicializar()
    with db.conectar() as con:
        fila = con.execute("SELECT * FROM monederos").fetchone()
    assert tuple(fila) == ("u", "g", 50, 50)

    db.inicializar()
    with db.conectar() as con:
        assert tuple(con.execute("SELECT * FROM monederos").fetchone()) == tuple(fila)


def test_rellena_monederos_de_criaturas_e_inventario(tmp_path, monkeypatch):
    ruta = tmp_path / "backfill.db"
    monkeypatch.setattr(db, "RUTA", ruta)
    db.inicializar()
    with db.conectar() as con:
        con.execute("DELETE FROM monederos")
        con.execute(
            "INSERT INTO inventario VALUES ('solo-inventario', 'g', 'placa', 1)"
        )
    db.inicializar()
    with db.conectar() as con:
        filas = con.execute(
            "SELECT usuario_id, asciicoins, asciigems FROM monederos"
        ).fetchall()
    assert [tuple(fila) for fila in filas] == [("solo-inventario", 50, 50)]


def test_forma_desconocida_falla_sin_tocar_datos(tmp_path, monkeypatch):
    ruta = tmp_path / "rara.db"
    with _conectar(ruta) as con:
        con.execute("CREATE TABLE monederos (usuario_id TEXT, saldo INTEGER)")
        con.execute("INSERT INTO monederos VALUES ('u', 77)")
    monkeypatch.setattr(db, "RUTA", ruta)

    with pytest.raises(RuntimeError, match="desconocida"):
        db.inicializar()
    with _conectar(ruta) as con:
        assert tuple(con.execute("SELECT * FROM monederos").fetchone()) == ("u", 77)


def test_fallo_de_ddl_revierte_y_conserva_legacy(tmp_path, monkeypatch):
    ruta = tmp_path / "rollback.db"
    with _conectar(ruta) as con:
        con.execute(
            "CREATE TABLE monederos (usuario_id TEXT, guild_id TEXT, gemas INTEGER, "
            "PRIMARY KEY (usuario_id, guild_id))"
        )
        con.execute("INSERT INTO monederos VALUES ('u', 'g', 123)")
    monkeypatch.setattr(db, "RUTA", ruta)
    monkeypatch.setattr(db, "DDL_MONEDEROS", "CREATE TABLE monederos (")

    with pytest.raises(sqlite3.OperationalError):
        db.inicializar()
    with _conectar(ruta) as con:
        assert tuple(con.execute("SELECT * FROM monederos").fetchone()) == ("u", "g", 123)
        assert tuple(row[1] for row in con.execute("PRAGMA table_info(monederos)")) == (
            "usuario_id", "guild_id", "gemas"
        )


def test_inicializaciones_concurrentes_convergen(tmp_path, monkeypatch):
    ruta = tmp_path / "concurrente.db"
    with _conectar(ruta) as con:
        con.execute(
            "CREATE TABLE monederos (usuario_id TEXT, guild_id TEXT, gemas INTEGER, "
            "PRIMARY KEY (usuario_id, guild_id))"
        )
        con.execute("INSERT INTO monederos VALUES ('u', 'g', 9)")
    monkeypatch.setattr(db, "RUTA", ruta)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: db.inicializar(), range(2)))
    with db.conectar() as con:
        assert tuple(con.execute("SELECT * FROM monederos").fetchone()) == ("u", "g", 50, 50)
