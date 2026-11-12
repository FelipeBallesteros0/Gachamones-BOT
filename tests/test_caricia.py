from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import identidad
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)
ESPERA = timedelta(minutes=19)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "caricia.db")
    db.inicializar()


def nacer(usuario="u", animo=50.0, **mas):
    creada = db.crear(usuario, "g", "pollito", "Pelusa", STATS, T0, **mas)
    db.guardar(replace(creada, animo=animo))
    return creada


def test_son_cinco_de_animo_cada_diecinueve_minutos_y_no_es_un_cuidado():
    assert sim.EFECTO_CARICIA == {"animo": 5}
    assert sim.COOLDOWNS[sim.ACARICIAR] == ESPERA
    assert sim.ACARICIAR not in sim.ACCIONES_DE_CUIDADO


def test_acariciar_sube_el_animo_y_nada_mas():
    antes = replace(nacer(), animo=50.0)
    despues = sim.aplicar_caricia(antes).criatura
    assert despues.animo == 55.0
    assert replace(despues, animo=50.0) == antes


def test_el_animo_no_pasa_de_cien():
    assert sim.aplicar_caricia(replace(nacer(), animo=98.0)).criatura.animo == 100.0


def test_a_una_muerta_no_se_la_acaricia():
    muerta = replace(nacer(), muerta_en=T0, causa_muerte="hambre")
    resultado = sim.aplicar_caricia(muerta)
    assert not resultado.ok and resultado.criatura == muerta


def test_la_primera_caricia_cuenta_y_queda_guardada():
    nacer()
    resultado = db.acariciar("u", "g", T0)
    assert resultado.ok and resultado.espera == ESPERA
    assert resultado.criatura.animo == 55.0
    assert db.criatura_activa("u", "g").animo == 55.0


def test_la_segunda_antes_de_tiempo_no_hace_nada_y_dice_cuanto_falta():
    nacer()
    db.acariciar("u", "g", T0)
    poco_despues = T0 + timedelta(minutes=5)
    segunda = db.acariciar("u", "g", poco_despues)
    assert not segunda.ok
    assert segunda.espera == timedelta(minutes=14)
    assert db.criatura_activa("u", "g").animo == 55.0


def test_a_los_diecinueve_minutos_vuelve_a_contar():
    nacer()
    db.acariciar("u", "g", T0)
    assert not db.acariciar("u", "g", T0 + ESPERA - timedelta(seconds=1)).ok
    assert db.acariciar("u", "g", T0 + ESPERA).ok


def test_no_da_experiencia_ni_monedas_ni_toca_el_tope():
    creada = nacer()
    db.acariciar("u", "g", T0)
    despues = db.criatura_activa("u", "g")
    assert (despues.xp, despues.nivel) == (creada.xp, creada.nivel)
    assert economia.saldos("u", "g") == economia.Saldos(50, 50)
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM operaciones_economia").fetchone()[0] == 0


def test_el_enfriamiento_es_de_cada_gachamon():
    nacer()
    otro = db.crear("u", "g", "pulpo", "Tinta", STATS, T0, activa=False)
    db.acariciar("u", "g", T0)
    assert db.activar(otro.id, "u", "g", T0)
    assert db.acariciar("u", "g", T0).ok


def test_sin_gachamon_no_hay_a_quien():
    assert db.acariciar("nadie", "g", T0) == db.ResultadoCaricia(False, None, timedelta(0))


def test_no_revive_ni_acaricia_a_quien_ya_murio_de_hambre():
    nacer()
    mucho_despues = T0 + timedelta(days=5)
    resultado = db.acariciar("u", "g", mucho_despues)
    assert not resultado.ok
    assert db.criatura_activa("u", "g") is None


def test_la_de_una_identidad_web_se_acaricia_igual():
    web = identidad.de_cuenta_web(12)
    nacer(usuario=web)
    assert db.acariciar(web, "g", T0).ok


def test_dos_caricias_a_la_vez_cuentan_una():
    nacer()
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(lambda _: db.acariciar("u", "g", T0), range(2)))
    assert sorted(r.ok for r in resultados) == [False, True]
    assert db.criatura_activa("u", "g").animo == 55.0
