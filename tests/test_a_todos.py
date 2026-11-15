"""«A todos»: un toque le hace un cuidado a cada gachamon que puede recibirlo."""
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import logros as lgr
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "a_todos.db")
    db.inicializar()


def con(nombre, activa=False, **barras) -> sim.Criatura:
    """Un gachamon de u1 en g1 con esas barras, tal como quedó en la base."""
    criatura = db.crear("u1", "g1", "pulpo", nombre, STATS, T0, activa=activa)
    db.guardar(replace(criatura, **barras))
    guardada = db.por_id(criatura.id)
    assert guardada is not None
    return guardada


def test_le_toca_a_cada_uno_que_puede_y_dice_a_cuantos():
    hambrienta = con("Ana", activa=True, hambre=50.0)
    llena = con("Bea", hambre=95.0)
    esperando = con("Cía", hambre=70.0)
    db.poner_cooldown(esperando.id, sim.ALIMENTAR, T0)
    hecho = economia.cuidar_a_todos("ev-todos", "u1", "g1", sim.ALIMENTAR, T0)
    assert hecho.tocados == (hambrienta.id,) and hecho.de_cuantos == 3
    assert hecho.delta_asciicoins == 1 and len(hecho.cuidados) == 1
    assert db.por_id(hambrienta.id).hambre == 80.0
    assert db.por_id(llena.id).hambre == 95.0          # no se empacha
    assert db.por_id(esperando.id).hambre == 70.0


def test_paga_como_cuidarlos_de_a_uno_y_solo_lo_que_cabe_en_el_tope():
    ids = [con("Ana", activa=True, limpieza=0.0).id] + [con(f"G{n}", limpieza=0.0).id for n in range(12)]
    hecho = economia.cuidar_a_todos("ev-13", "u1", "g1", sim.LIMPIAR, T0)
    assert hecho.tocados == tuple(ids) and hecho.de_cuantos == 13
    assert hecho.delta_asciicoins == economia.TOPE_CUIDADOS
    assert all(db.por_id(i).limpieza == 100.0 for i in ids)
    assert all(db.espera_de(i, sim.LIMPIAR, T0) == sim.COOLDOWNS[sim.LIMPIAR] for i in ids)
    assert all(db.marcador(i)[lgr.CUIDADOS] == 1 for i in ids)
    assert economia.saldos("u1", "g1").asciicoins == 50 + economia.TOPE_CUIDADOS


def test_repetir_el_evento_no_cuida_ni_paga_otra_vez():
    a = con("Ana", activa=True, animo=40.0)
    b = con("Bea", animo=40.0)
    primero = economia.cuidar_a_todos("ev-r", "u1", "g1", sim.JUGAR, T0)
    segundo = economia.cuidar_a_todos("ev-r", "u1", "g1", sim.JUGAR, T0 + timedelta(hours=3))
    assert segundo.replay and segundo.tocados == primero.tocados == (a.id, b.id)
    assert segundo.de_cuantos == 2 and segundo.delta_asciicoins == 2 and segundo.cuidados == ()
    assert db.por_id(a.id).animo == 65.0 and economia.saldos("u1", "g1").asciicoins == 52
    with pytest.raises(RuntimeError):
        economia.cuidar_a_todos("ev-r", "u1", "g1", sim.LIMPIAR, T0)


def test_antes_de_cuidar_les_pasa_el_tiempo():
    b = con("Bea", hambre=100.0)
    con("Ana", activa=True, hambre=100.0)
    tarde = T0 + timedelta(hours=30)
    economia.cuidar_a_todos("ev-t", "u1", "g1", sim.ALIMENTAR, tarde)
    assert db.por_id(b.id).hambre == pytest.approx(sim.avanzar(b, tarde).hambre + 30.0)


def test_si_no_le_toca_a_nadie_no_se_anota_y_se_puede_repetir():
    a = con("Ana", activa=True)                          # limpia
    nada = economia.cuidar_a_todos("ev-n", "u1", "g1", sim.LIMPIAR, T0)
    assert nada.tocados == () and nada.de_cuantos == 1 and not nada.replay
    db.guardar(replace(db.por_id(a.id), limpieza=10.0))
    ahora_si = economia.cuidar_a_todos("ev-n", "u1", "g1", sim.LIMPIAR, T0)
    assert ahora_si.tocados == (a.id,) and not ahora_si.replay


def test_sin_gachamones_no_hay_a_quien():
    muerta = con("Ana", activa=True, muerta_en=T0, causa_muerte="hambre")
    hecho = economia.cuidar_a_todos("ev-0", "u1", "g1", sim.JUGAR, T0)
    assert hecho.tocados == () and hecho.de_cuantos == 0
    assert db.por_id(muerta.id) == muerta


def test_a_todos_solo_con_un_cuidado():
    a = con("Ana", activa=True, limpieza=10.0)
    for accion in (sim.ACTUALIZAR, sim.CONVERSAR, "bailar"):
        with pytest.raises(ValueError):
            economia.cuidar_a_todos("ev-x", "u1", "g1", accion, T0)
    assert db.por_id(a.id) == a and economia.saldos("u1", "g1").asciicoins == 50


def test_un_fallo_a_medias_no_deja_a_nadie_cuidado(monkeypatch):
    a = con("Ana", activa=True, animo=40.0)
    b = con("Bea", animo=40.0)
    de_verdad, llamadas = db.poner_cooldown_en, []

    def falla_a_la_segunda(*args):
        llamadas.append(args)
        if len(llamadas) == 2:
            raise sqlite3.OperationalError("disco lleno")
        return de_verdad(*args)

    monkeypatch.setattr(db, "poner_cooldown_en", falla_a_la_segunda)
    with pytest.raises(sqlite3.OperationalError):
        economia.cuidar_a_todos("ev-f", "u1", "g1", sim.JUGAR, T0)
    assert db.por_id(a.id).animo == 40.0 and db.por_id(b.id).animo == 40.0
    assert economia.saldos("u1", "g1").asciicoins == 50
