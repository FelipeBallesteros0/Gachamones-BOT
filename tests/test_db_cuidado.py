"""Acciones de cuidado autoritativas en la economía SQLite."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def test_dos_cuidados_simultaneos_solo_aplican_un_efecto_y_un_cooldown():
    db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(
            lambda evento: economia.ejecutar_cuidado(
                evento, "u1", "g1", sim.JUGAR, T0
            ),
            ("clic-1", "clic-2"),
        ))

    assert sum(resultado.ok for resultado in resultados) == 1
    bloqueado = next(resultado for resultado in resultados if not resultado.ok)
    assert bloqueado.espera == sim.COOLDOWNS[sim.JUGAR]
    guardada = db.criatura_activa("u1", "g1")
    assert guardada.hambre == 95.0
    assert guardada.ent_velocidad == 1
    assert guardada.xp == 2
    assert economia.saldos("u1", "g1").asciicoins == 51


def test_fallo_al_guardar_cooldown_revierte_criatura_y_premio():
    original = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER abortar_cooldown BEFORE INSERT ON cooldowns "
            "BEGIN SELECT RAISE(ABORT, 'fallo de cooldown'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="fallo de cooldown"):
        economia.ejecutar_cuidado("clic", "u1", "g1", sim.JUGAR, T0)

    assert db.criatura_activa("u1", "g1") == original
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_rechazos_sin_mutacion_no_escriben_recibo():
    assert economia.ejecutar_cuidado("sin", "u1", "g1", sim.JUGAR, T0) is None
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_cuidado_registra_la_muerte_al_avanzar_sin_recibo():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    resultado = economia.ejecutar_cuidado(
        "tarde", "u1", "g1", sim.JUGAR, T0 + timedelta(days=10)
    )

    assert resultado is not None and not resultado.criatura.viva and not resultado.ok
    assert db.obtener(criatura.id).muerta_en == resultado.criatura.muerta_en
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_alimentar_con_hambre_se_salta_el_cooldown_en_la_misma_transaccion():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15, 15), T0)
    db.guardar(replace(criatura, hambre=50.0))
    db.poner_cooldown(criatura.id, sim.ALIMENTAR, T0)

    resultado = economia.ejecutar_cuidado(
        "comer", "u1", "g1", sim.ALIMENTAR, T0
    )
    assert resultado is not None and resultado.ok
    assert resultado.criatura.hambre == 80.0
