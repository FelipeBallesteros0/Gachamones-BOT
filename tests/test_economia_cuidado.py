import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

import db
import economia
import simulacion as sim
import vistas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def nacer(nombre="A", activa=True, guild="g1"):
    return db.crear("u1", guild, "pulpo", nombre, STATS, T0, activa=activa)


def cuidar(evento, guild, accion, cuando) -> economia.ResultadoCuidado:
    resultado = economia.ejecutar_cuidado(evento, "u1", guild, accion, cuando)
    assert resultado is not None
    return resultado


def limpiar(evento, cuando, guild="g1") -> economia.ResultadoCuidado:
    criatura = db.criatura_activa("u1", guild)
    assert criatura is not None
    db.guardar(replace(criatura, limpieza=0.0))
    return cuidar(evento, guild, sim.LIMPIAR, cuando)


def test_cuidado_acredita_y_replay_no_muta_dos_veces():
    activa = replace(nacer(), animo=40.0)
    db.guardar(activa)
    primero = cuidar("evento", "g1", sim.JUGAR, T0)
    guardada = db.criatura_activa("u1", "g1")
    assert guardada is not None
    replay = cuidar("evento", "g1", sim.JUGAR, T0)

    assert primero.delta_asciicoins == 1 and primero.usados == 1
    assert guardada.ten_velocidad > 0
    assert replay.replay and replay.delta_asciicoins == 1 and replay.usados == 1
    assert db.criatura_activa("u1", "g1") == guardada
    assert economia.saldos("u1", "g1").asciicoins == 51
    with pytest.raises(RuntimeError, match="otra acción"):
        economia.ejecutar_cuidado("evento", "u1", "g1", sim.LIMPIAR, T0)


def test_limpiar_a_una_criatura_limpia_queda_marcado_sin_efecto_y_no_paga():
    criatura = nacer()
    assert criatura.limpieza == 100.0

    resultado = cuidar("evento", "g1", sim.LIMPIAR, T0)

    assert resultado.sin_efecto and resultado.ok and resultado.espera is None
    assert resultado.mensaje
    assert resultado.delta_asciicoins == 0 and resultado.usados == 0
    assert db.espera_de(criatura.id, sim.LIMPIAR, T0) == timedelta(0)
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM operaciones_economia"
        ).fetchone()[0] == 0

    # Ni un cuidado que sí cambia algo ni `actualizar` se marcan sin efecto:
    # el primero tiene ficha que publicar y el segundo edita la suya en sitio.
    assert limpiar("sucia", T0).sin_efecto is False
    assert cuidar("refresco", "g1", sim.ACTUALIZAR, T0).sin_efecto is False


def test_tope_12_rollover_utc_y_aislamiento_por_servidor():
    nacer()
    nacer(nombre="Otro", guild="g2")
    resultados = [
        limpiar(f"dia-{i}", T0 + timedelta(minutes=54 * i))
        for i in range(13)
    ]
    assert [r.delta_asciicoins for r in resultados] == [1] * 12 + [0]
    assert resultados[-1].topada and resultados[-1].usados == 12

    otro = limpiar("otro-guild", T0, "g2")
    manana = limpiar("manana", T0 + timedelta(days=1, minutes=1))
    assert otro.delta_asciicoins == 1 and otro.usados == 1
    assert manana.delta_asciicoins == 1 and manana.usados == 1


def test_el_cupo_continua_al_cambiar_de_activa():
    a = nacer()
    b = nacer(nombre="B", activa=False)
    for i in range(5):
        assert limpiar(f"a-{i}", T0 + timedelta(minutes=54 * i)).delta_asciicoins == 1

    assert db.activar(b.id, "u1", "g1", T0 + timedelta(hours=5))
    resultados = [
        limpiar(f"b-{i}", T0 + timedelta(minutes=54 * i))
        for i in range(5, 13)
    ]
    resultado = resultados[-1]
    assert resultado.topada and resultado.usados == 12
    assert economia.saldos("u1", "g1").asciicoins == 62
    anterior = db.obtener(a.id)
    assert anterior is not None and anterior.activa is False


def test_cuidar_desde_la_ficha_de_una_incubada_no_acredita():
    activa = nacer()
    incubada = nacer(nombre="B", activa=False)
    db.guardar_pantalla(incubada.id, "pantalla-b")
    respuesta = SimpleNamespace(send_message=AsyncMock())
    interaccion = SimpleNamespace(
        id=99,
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        message=SimpleNamespace(id="pantalla-b"),
        response=respuesta,
    )

    asyncio.run(vistas._ejecutar(cast(Any, interaccion), sim.JUGAR))

    respuesta.send_message.assert_awaited_once()
    assert "incubadora" in respuesta.send_message.await_args.args[0]
    assert db.criatura_activa("u1", "g1") == activa
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_ascender_tras_muerte_conserva_cupos_del_dia():
    a = nacer()
    b = nacer(nombre="B", activa=False)
    for i in range(12):
        assert limpiar(f"a-{i}", T0 + timedelta(minutes=54 * i)).delta_asciicoins == 1
    guardada = db.obtener(a.id)
    assert guardada is not None
    db.guardar(replace(guardada, muerta_en=T0, causa_muerte="prueba"))
    ascendida = db.ascender_de_la_incubadora("u1", "g1", T0 + timedelta(hours=12))
    assert ascendida is not None and ascendida.id == b.id

    resultado = limpiar("tras-ascenso", T0 + timedelta(hours=12))
    assert resultado.topada and resultado.delta_asciicoins == 0
    assert resultado.usados == 12


def test_evolucion_topada_con_otra_criatura_del_plantel():
    a = nacer()
    b = nacer(nombre="B", activa=False)
    db.guardar(replace(a, xp=24, hambre=50.0))
    primera = cuidar("evo-a", "g1", sim.ALIMENTAR, T0)
    assert primera.evoluciono and primera.delta_evolucion == 10

    db.activar(b.id, "u1", "g1", T0 + timedelta(minutes=24))
    guardada = db.obtener(b.id)
    assert guardada is not None
    db.guardar(replace(guardada, xp=24, hambre=50.0))
    segunda = cuidar(
        "evo-b", "g1", sim.ALIMENTAR, T0 + timedelta(minutes=24)
    )
    assert segunda.evoluciono and segunda.delta_evolucion == 0
    assert segunda.evolucion_usadas == 1
    assert segunda.delta_asciicoins == 1


def test_dos_cuidados_compiten_por_el_ultimo_cupo_sin_sobrepasarlo():
    nacer()
    for i in range(11):
        assert limpiar(f"previo-{i}", T0 + timedelta(minutes=54 * i)).delta_asciicoins == 1
    criatura = db.criatura_activa("u1", "g1")
    assert criatura is not None
    db.guardar(replace(criatura, limpieza=0.0))
    ahora = T0 + timedelta(hours=11)

    def cuidar_concurrente(datos):
        evento, accion = datos
        return cuidar(evento, "g1", accion, ahora)

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(
            cuidar_concurrente,
            (("ultimo-jugar", sim.JUGAR), ("ultimo-limpiar", sim.LIMPIAR)),
        ))
    assert sorted(r.delta_asciicoins for r in resultados) == [0, 1]
    assert sum(r.topada for r in resultados) == 1
    assert economia.saldos("u1", "g1").asciicoins == 62


def test_fallo_del_ledger_revierte_criatura_cooldown_y_saldo():
    original = replace(nacer(), animo=40.0)
    db.guardar(original)
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_cuidado BEFORE INSERT ON operaciones_economia "
            "BEGIN SELECT RAISE(ABORT, 'fallo ledger'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="fallo ledger"):
        economia.ejecutar_cuidado("evento", "u1", "g1", sim.JUGAR, T0)

    assert db.criatura_activa("u1", "g1") == original
    assert db.espera_de(original.id, sim.JUGAR, T0) == timedelta(0)
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
