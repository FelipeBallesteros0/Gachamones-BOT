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
U = "222222222222222222"     # una identidad de Discord: tiene aviso de hambre
OTRA = "333333333333333333"
G = "g"


@pytest.fixture(autouse=True)
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "cambiar.db")
    db.inicializar()


def nace(nombre, activa=True, usuario=U, guild=G):
    return db.crear(usuario, guild, "pollito", nombre, STATS, T0, activa=activa)


def muere(criatura):
    db.guardar(replace(criatura, muerta_en=T0, causa_muerte="hambre"))


def apuntadas():
    with db.conectar() as con:
        return [f["criatura_id"] for f in con.execute(
            "SELECT criatura_id FROM muertes_por_anunciar ORDER BY criatura_id")]


def relojes(criatura_id):
    with db.conectar() as con:
        fila = con.execute(
            "SELECT muere_en, avisa_en FROM criaturas WHERE id = ?",
            (criatura_id,),
        ).fetchone()
    return fila["muere_en"], fila["avisa_en"]


def test_cambiar_pone_al_dia_a_la_que_sale():
    a = nace("Ana")
    db.guardar(replace(a, hambre=100.0))
    a = db.por_id(a.id)
    b = nace("Bea", activa=False)
    cinco = T0 + timedelta(hours=5)

    resultado = economia.cambiar_de_activo(U, G, b.id, cinco)

    assert resultado.ok
    assert resultado.motivo is None
    assert db.criatura_activa(U, G).id == b.id
    guardada = db.por_id(a.id)
    assert guardada.actualizada_en == cinco
    assert guardada.hambre == pytest.approx(sim.avanzar(a, cinco).hambre)
    assert guardada.hambre < 100
    # Y vuelve a la incubadora como cualquier otra: sin relojes que corran.
    assert guardada.activa is False
    assert relojes(a.id) == (None, None)
    assert resultado.saliente == guardada
    assert resultado.criatura.id == b.id


def test_la_que_entra_sale_con_su_reloj_al_dia():
    nace("Ana")
    b = nace("Bea", activa=False)
    ahora = T0 + timedelta(hours=3)

    resultado = economia.cambiar_de_activo(U, G, b.id, ahora)

    entra = db.por_id(b.id)
    assert entra.activa is True
    assert entra.actualizada_en == ahora
    muere_en, avisa_en = relojes(b.id)
    assert muere_en is not None and avisa_en is not None
    assert datetime.fromisoformat(muere_en) == sim.momento_de_muerte(entra)
    assert resultado.criatura == entra


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


def test_si_la_que_sale_ya_estaba_muerta_se_registra_y_se_cambia_igual():
    a = nace("Ana")
    b = nace("Bea", activa=False)      # el relevo: el primero con nombre
    c = nace("Cata", activa=False)
    assert sim.momento_de_muerte(a) < TARDE

    resultado = economia.cambiar_de_activo(U, G, c.id, TARDE)

    assert resultado.ok
    assert db.por_id(a.id).muerta_en is not None
    assert apuntadas() == [a.id]
    assert db.criatura_activa(U, G).id == c.id
    # El relevo que sacó la muerte es «la que estaba» y vuelve a la incubadora;
    # y el bot anuncia la muerte sin presentarlo como relevo, porque ya no lo es.
    assert resultado.saliente.id == b.id
    assert db.por_id(b.id).activa is False
    assert [(m.id, r) for m, r in db.muertes_por_anunciar()] == [(a.id, None)]


def test_si_la_elegida_es_el_relevo_que_acaba_de_salir_ya_es_el_activo():
    a = nace("Ana")
    b = nace("Bea", activa=False)
    nace("Cata", activa=False)

    resultado = economia.cambiar_de_activo(U, G, b.id, TARDE)

    assert resultado.motivo == "ya_es_el_activo"
    assert resultado.ok is False
    assert resultado.criatura.id == b.id
    assert db.criatura_activa(U, G).id == b.id
    assert db.por_id(a.id).muerta_en is not None
    assert apuntadas() == [a.id]


def test_si_muere_al_ponerla_al_dia_dentro_se_apunta_y_el_cambio_sigue(monkeypatch):
    """Lo que pasa si otro proceso la dejó viva entre `activa_al_dia` y la
    transacción: la que sale se guarda muerta, se apunta, y se cambia igual."""
    a = nace("Ana")
    nace("Bea", activa=False)
    c = nace("Cata", activa=False)
    monkeypatch.setattr(db, "activa_al_dia", lambda *_: None)

    resultado = economia.cambiar_de_activo(U, G, c.id, TARDE)

    assert resultado.ok
    muerta = db.por_id(a.id)
    assert muerta.muerta_en is not None and muerta.causa_muerte == "hambre"
    assert resultado.saliente == muerta
    assert apuntadas() == [a.id]
    assert db.criatura_activa(U, G).id == c.id
