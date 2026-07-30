"""Acciones de cuidado autoritativas en la capa pública de SQLite."""
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


def test_dos_cuidados_simultaneos_solo_aplican_un_efecto_y_un_cooldown():
    """Dos clics concurrentes se serializan en la operación pública completa."""
    db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)
    barrera = Barrier(2)

    def jugar():
        barrera.wait()
        return db.ejecutar_cuidado("u1", "g1", sim.JUGAR, T0)

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(lambda _: jugar(), range(2)))

    assert sum(resultado.ok for resultado in resultados) == 1
    bloqueado = next(resultado for resultado in resultados if not resultado.ok)
    assert bloqueado.espera == sim.COOLDOWNS[sim.JUGAR]

    guardada = db.criatura_viva("u1", "g1")
    assert guardada.hambre == 95.0
    assert guardada.ent_velocidad == 1
    assert guardada.xp == 2
    assert db.espera_de(guardada.id, sim.JUGAR, T0) == sim.COOLDOWNS[sim.JUGAR]


def test_cuidado_sin_criatura_devuelve_el_estado_publico_vacio():
    assert db.ejecutar_cuidado("u1", "g1", sim.JUGAR, T0) is None


def test_cuidado_registra_la_muerte_al_avanzar():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", (15, 15, 15), T0)

    resultado = db.ejecutar_cuidado(
        "u1", "g1", sim.JUGAR, T0 + timedelta(days=10)
    )

    assert resultado is not None and not resultado.criatura.viva
    assert not resultado.ok and resultado.espera is None
    assert db.criatura_viva("u1", "g1") is None
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
