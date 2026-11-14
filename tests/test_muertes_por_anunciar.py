from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import identidad

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TARDE = T0 + timedelta(days=5)
STATS = (10, 10, 10, 10)
G = "g"
ANA = "222222222222222222"
WEB = identidad.de_cuenta_web(1)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "muertes.db")
    db.inicializar()


def nace(usuario=ANA, nombre="Viejo", **mas):
    return db.crear(usuario, G, "pollito", nombre, STATS, T0, **mas)


def apuntes():
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(
            "SELECT criatura_id, relevo_id FROM muertes_por_anunciar "
            "ORDER BY criatura_id")]


def test_una_identidad_web_nunca_deja_apunte(monkeypatch):
    nace(usuario=WEB)
    muere = lambda c, ahora: replace(c, muerta_en=ahora, causa_muerte="hambre")
    monkeypatch.setattr(db, "avanzar", muere)
    monkeypatch.setattr(db, "_avanzar_en", lambda con, c, ahora: muere(c, ahora))
    assert db.activa_al_dia(WEB, G, TARDE) is None
    assert apuntes() == []


def test_una_base_sin_la_tabla_la_gana_al_inicializar():
    with db.conectar() as con:
        con.execute("DROP TABLE muertes_por_anunciar")
    db.inicializar()
    assert apuntes() == []
