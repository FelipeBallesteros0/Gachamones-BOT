"""Cambiar de gachamon activo es una regla del juego: `economia.cambiar_de_activo`."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import simulacion as sim

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TARDE = T0 + timedelta(days=5)
STATS = (10, 10, 10, 10)
U = "222222222222222222"     # una identidad de Discord
OTRA = "333333333333333333"
G = "g"


@pytest.fixture(autouse=True)
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "cambiar.db")
    db.inicializar()


def nace(nombre, activa=True, usuario=U, guild=G):
    return db.crear(usuario, guild, "pollito", nombre, STATS, T0, activa=activa)


def muere(criatura):
    """Como la dejaba la muerte de antes: con la comida en 0 y la marca puesta."""
    db.guardar(replace(criatura, hambre=0.0, muerta_en=T0, causa_muerte="hambre"))


def test_cambiar_no_le_borra_el_tiempo_a_la_que_entra():
    nace("Ana")
    b = nace("Bea", activa=False)
    cinco = T0 + timedelta(hours=5)
    resultado = economia.cambiar_de_activo(U, G, b.id, cinco)
    assert resultado.ok and resultado.criatura.id == b.id
    assert resultado.criatura.hambre == pytest.approx(sim.avanzar(b, cinco).hambre)
    assert resultado.criatura.hambre < 100.0
    assert db.por_id(b.id).actualizada_en == T0


def test_a_la_que_se_queda_le_sigue_pasando_el_tiempo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    resultado = economia.cambiar_de_activo(U, G, b.id, T0 + timedelta(hours=1))
    assert resultado.saliente.id == a.id and resultado.saliente.activa is False
    veinte = T0 + timedelta(hours=20)
    assert db.avanzar(db.por_id(a.id), veinte).hambre == pytest.approx(sim.avanzar(a, veinte).hambre)


def test_ir_y_volver_no_ahorra_ni_duplica_el_tiempo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    for hora, quien in enumerate((b, a, b, a, b), start=1):
        assert economia.cambiar_de_activo(U, G, quien.id, T0 + timedelta(hours=hora)).ok
    final = T0 + timedelta(hours=10)
    for c in (a, b):
        assert db.avanzar(db.por_id(c.id), final).hambre == pytest.approx(sim.avanzar(c, final).hambre)


def test_cambiar_al_que_ya_es_el_activo_no_toca_nada():
    a = nace("Ana")
    nace("Bea", activa=False)

    resultado = economia.cambiar_de_activo(U, G, a.id, T0 + timedelta(hours=5))

    assert resultado.motivo == "ya_es_el_activo"
    assert resultado.ok is False
    assert resultado.criatura.id == a.id
    guardada = db.por_id(a.id)
    assert guardada.actualizada_en == a.actualizada_en
    assert guardada.hambre == a.hambre


def test_no_se_saca_a_un_recluta_sin_nombre():
    a = nace("Ana")
    recluta = nace("", activa=False)

    resultado = economia.cambiar_de_activo(U, G, recluta.id, T0 + timedelta(hours=1))

    assert resultado.motivo == "sin_nombre"
    assert resultado.ok is False
    assert db.criatura_activa(U, G).id == a.id
    assert db.por_id(a.id) == a
    assert db.por_id(recluta.id) == recluta


def test_no_se_saca_a_uno_ajeno_muerto_ni_inexistente():
    a = nace("Ana")
    ajena = nace("Otra", activa=False, usuario=OTRA)
    de_otro_servidor = nace("Lejos", activa=False, guild="otro")
    muerta = nace("Muerta", activa=False)
    muere(muerta)
    muerta = db.por_id(muerta.id)

    for criatura_id in (ajena.id, de_otro_servidor.id, muerta.id, 9999):
        resultado = economia.cambiar_de_activo(
            U, G, criatura_id, T0 + timedelta(hours=1)
        )
        assert resultado.motivo == "no_esta"
        assert resultado.ok is False

    assert db.criatura_activa(U, G).id == a.id
    assert db.por_id(a.id) == a
    assert db.por_id(ajena.id) == ajena
    assert db.por_id(de_otro_servidor.id) == de_otro_servidor
    assert db.por_id(muerta.id) == muerta


def test_con_la_activa_muerta_de_antes_sale_el_relevo_y_el_cambio_sigue():
    a = nace("Ana")
    b = nace("Bea", activa=False)      # el relevo: el primero con nombre
    c = nace("Cata", activa=False)
    muere(a)

    resultado = economia.cambiar_de_activo(U, G, c.id, TARDE)

    assert resultado.ok
    assert db.criatura_activa(U, G).id == c.id
    # El relevo que sacó el remiendo es «la que estaba» y se queda en casa.
    assert resultado.saliente.id == b.id
    assert db.por_id(b.id).activa is False


def test_cambiar_con_la_saliente_en_cero_la_deja_viva_en_cero():
    a = nace("Ana")
    db.guardar(replace(a, hambre=0.0))
    b = nace("Bea", activa=False)

    resultado = economia.cambiar_de_activo(U, G, b.id, TARDE)

    assert resultado.ok
    assert db.criatura_activa(U, G).id == b.id
    saliente = db.por_id(a.id)
    assert saliente.viva and saliente.hambre == 0.0
    # Se queda en casa sin que se le guarde el paso del tiempo: lo que devuelve
    # la regla es cómo está ahora, no lo que quedó escrito.
    assert saliente.actualizada_en == T0 and saliente.activa is False
    assert resultado.saliente == db.avanzar(saliente, TARDE)
    assert resultado.saliente.viva and resultado.saliente.hambre == 0.0


def test_si_la_elegida_es_el_relevo_que_acaba_de_salir_ya_es_el_activo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    nace("Cata", activa=False)
    muere(a)

    resultado = economia.cambiar_de_activo(U, G, b.id, TARDE)

    assert resultado.motivo == "ya_es_el_activo"
    assert resultado.ok is False
    assert resultado.criatura.id == b.id
    assert db.criatura_activa(U, G).id == b.id
