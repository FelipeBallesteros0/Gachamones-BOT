import asyncio
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import competir as comp
import db
import economia
import simulacion as sim
from cogs.competencias import Competencias

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def nacer(usuario, activa=True):
    return db.crear(usuario, "g1", "pulpo", usuario, STATS, T0, activa=activa)


def competir(evento, cuando=T0, usuarios=("u1", "u2"), semilla=1):
    return economia.ejecutar_competencia(
        evento, usuarios, "g1", comp.CARRERA, cuando, random.Random(semilla)
    )


def test_competencia_acredita_6_al_ganador_y_4_al_resto_y_replay_no_muta():
    nacer("u1")
    nacer("u2")
    resultado = competir("evento")
    despues = (db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1"))
    replay = competir("evento")

    assert sorted(r.delta_competencia for r in resultado.recibos) == [4, 6]
    assert all(r.usados == 1 for r in resultado.recibos)
    assert replay.replay
    assert sorted(r.delta_competencia for r in replay.recibos) == [4, 6]
    assert despues == (db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1"))
    assert sum(economia.saldos(u, "g1").asciicoins for u in ("u1", "u2")) == 110


def test_cuarta_competencia_aplica_desgaste_pero_no_premia():
    nacer("u1")
    nacer("u2")
    resultados = [
        competir(f"evento-{i}", T0 + timedelta(minutes=11 * i), semilla=i)
        for i in range(4)
    ]
    assert all(r.delta_competencia == 0 and r.topada for r in resultados[-1].recibos)
    assert all(r.usados == 3 for r in resultados[-1].recibos)


def test_fallo_al_insertar_ledger_revierte_encuentro_completo():
    originales = (nacer("u1"), nacer("u2"))
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_premio BEFORE INSERT ON operaciones_economia "
            "BEGIN SELECT RAISE(ABORT, 'fallo premio'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="fallo premio"):
        competir("evento")

    assert originales == (
        db.criatura_activa("u1", "g1"), db.criatura_activa("u2", "g1")
    )
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM cooldowns").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_competencia_rechaza_invitado_sin_activa_sin_filas_ni_deltas():
    uno = nacer("u1")
    dos = nacer("u2", activa=False)
    resultado = competir("evento")

    assert resultado.problema and resultado.problema_usuario_id == "u2"
    assert db.obtener(uno.id) == uno and db.obtener(dos.id) == dos
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM monederos").fetchone()[0] == 0


def test_dos_resoluciones_concurrentes_del_mismo_evento_aplican_una_vez():
    nacer("u1")
    nacer("u2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: competir("mismo"), range(2)))

    assert sum(resultado.replay for resultado in resultados) == 1
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 2


def test_torneo_escribe_una_fila_por_persona_no_por_combate():
    for usuario in ("u1", "u2", "u3", "u4"):
        nacer(usuario)
    resultado = competir("torneo", usuarios=("u1", "u2", "u3", "u4"))
    assert len(resultado.recibos) == 4
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 4


def test_evolucion_de_competencia_comparte_el_tope_diario():
    primero = nacer("u1")
    nacer("u2")
    db.guardar(replace(primero, xp=24))
    resultado = competir("evento")
    evolucionados = [r for r in resultado.recibos if r.evoluciono]
    assert evolucionados
    assert sum(r.delta_evolucion for r in evolucionados) == 10


def test_fallo_de_discord_ocurre_despues_del_commit_y_retry_no_reenvia(monkeypatch):
    nacer("u1")
    nacer("u2")
    monkeypatch.setattr(db, "ahora_utc", lambda: T0)
    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock(side_effect=RuntimeError("discord caído"))
    canal = SimpleNamespace(send=AsyncMock())
    usuarios = [
        SimpleNamespace(id="u1", mention="<@u1>", display_name="u1"),
        SimpleNamespace(id="u2", mention="<@u2>", display_name="u2"),
    ]

    with pytest.raises(RuntimeError, match="discord caído"):
        asyncio.run(cog.disputar(canal, usuarios, comp.CARRERA, "g1", "mensaje-1"))
    saldos = tuple(economia.saldos(u, "g1") for u in ("u1", "u2"))
    asyncio.run(cog.disputar(canal, usuarios, comp.CARRERA, "g1", "mensaje-1"))

    assert cog._animar.await_count == 1
    assert tuple(economia.saldos(u, "g1") for u in ("u1", "u2")) == saldos
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia WHERE tipo = 'competencia'"
        ).fetchone()[0] == 2
