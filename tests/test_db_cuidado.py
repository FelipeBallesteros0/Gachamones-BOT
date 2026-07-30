"""Acciones de cuidado autoritativas en la capa pública de SQLite."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest

import db
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


class _CursorConCompuerta:
    def __init__(self, cursor, compuerta):
        self._cursor = cursor
        self._compuerta = compuerta

    def fetchone(self):
        fila = self._cursor.fetchone()
        # Si la lectura quedó fuera de una transacción, retenemos ambos hilos
        # aquí: la secuencia antigua read/check/write calcula así dos efectos.
        self._compuerta.wait(timeout=2)
        return fila


class _ConexionInstrumentada:
    def __init__(self, conexion, compuerta):
        self._conexion = conexion
        self._compuerta = compuerta

    def __enter__(self):
        self._conexion.__enter__()
        return self

    def __exit__(self, *args):
        return self._conexion.__exit__(*args)

    def execute(self, sql, *args):
        cursor = self._conexion.execute(sql, *args)
        if (
            sql.startswith("SELECT * FROM criaturas ")
            and not self._conexion.in_transaction
        ):
            return _CursorConCompuerta(cursor, self._compuerta)
        return cursor


def test_dos_cuidados_simultaneos_solo_aplican_un_efecto_y_un_cooldown(monkeypatch):
    """Dos clics concurrentes se serializan en la operación pública completa."""
    db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
    compuerta = Barrier(2)
    conectar_real = db.conectar
    monkeypatch.setattr(
        db,
        "conectar",
        lambda: _ConexionInstrumentada(conectar_real(), compuerta),
    )

    def jugar():
        return db.ejecutar_cuidado("u1", "g1", sim.JUGAR, T0)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [ejecutor.submit(jugar) for _ in range(2)]
        resultados = [futuro.result(timeout=5) for futuro in futuros]
    monkeypatch.setattr(db, "conectar", conectar_real)

    assert sum(resultado.ok for resultado in resultados) == 1
    bloqueado = next(resultado for resultado in resultados if not resultado.ok)
    assert bloqueado.espera == sim.COOLDOWNS[sim.JUGAR]

    guardada = db.criatura_activa("u1", "g1")
    assert guardada.hambre == 95.0
    assert guardada.ent_velocidad == 1
    assert guardada.xp == 2
    assert db.espera_de(guardada.id, sim.JUGAR, T0) == sim.COOLDOWNS[sim.JUGAR]


def test_fallo_al_guardar_cooldown_revierte_tambien_el_efecto():
    original = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
    with db.conectar() as con:
        con.execute(
            """CREATE TRIGGER abortar_cooldown
            BEFORE INSERT ON cooldowns
            BEGIN
                SELECT RAISE(ABORT, 'fallo de cooldown');
            END"""
        )

    with pytest.raises(sqlite3.IntegrityError, match="fallo de cooldown"):
        db.ejecutar_cuidado("u1", "g1", sim.JUGAR, T0)

    guardada = db.criatura_activa("u1", "g1")
    assert guardada == original
    assert db.espera_de(original.id, sim.JUGAR, T0) == timedelta(0)


def test_cuidado_sin_criatura_devuelve_el_estado_publico_vacio():
    assert db.ejecutar_cuidado("u1", "g1", sim.JUGAR, T0) is None


def test_cuidado_registra_la_muerte_al_avanzar():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)

    resultado = db.ejecutar_cuidado(
        "u1", "g1", sim.JUGAR, T0 + timedelta(days=10)
    )

    assert resultado is not None and not resultado.criatura.viva
    assert not resultado.ok and resultado.espera is None
    assert db.criatura_activa("u1", "g1") is None
    guardada = db.obtener(criatura.id)
    assert guardada is not None
    assert guardada.muerta_en == resultado.criatura.muerta_en


def test_alimentar_con_hambre_se_salta_el_cooldown_en_la_misma_transaccion():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
    db.guardar(replace(criatura, hambre=50.0))
    db.poner_cooldown(criatura.id, sim.ALIMENTAR, T0)

    resultado = db.ejecutar_cuidado("u1", "g1", sim.ALIMENTAR, T0)

    assert resultado is not None and resultado.ok
    assert resultado.criatura.hambre == 80.0
