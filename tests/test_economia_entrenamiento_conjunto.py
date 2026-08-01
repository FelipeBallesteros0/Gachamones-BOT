import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import logros
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia.db")
    db.inicializar()


def pareja():
    activa = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    reserva = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    return activa, reserva


def seleccion(activa, reserva, **cambios):
    datos = dict(
        activo_id=activa.id,
        activo_nombre=activa.nombre,
        reserva_id=reserva.id,
        reserva_nombre=reserva.nombre,
    )
    datos.update(cambios)
    return economia.SeleccionEntrenamientoConjunto(**datos)


def entrenar(evento, elegida, ahora=T0):
    return economia.ejecutar_entrenamiento_conjunto(
        evento, "u1", "g1", elegida, ahora
    )


def filas_economia():
    with db.conectar() as con:
        return con.execute(
            "SELECT * FROM operaciones_economia ORDER BY tipo"
        ).fetchall()


def test_persiste_la_pareja_cooldowns_marcadores_y_una_oportunidad():
    activa, reserva = pareja()

    resultado = entrenar("evento", seleccion(activa, reserva))

    despues_activa = db.obtener(activa.id)
    despues_reserva = db.obtener(reserva.id)
    assert despues_activa is not None and despues_reserva is not None
    assert resultado.participantes[0].criatura == despues_activa
    assert resultado.participantes[1].criatura == despues_reserva
    assert (despues_activa.xp, despues_reserva.xp) == (2, 2)
    assert (despues_activa.ent_fuerza, despues_reserva.ent_fuerza) == (1, 1)
    assert (despues_activa.hambre, despues_reserva.hambre) == (90.0, 90.0)
    assert (despues_activa.animo, despues_reserva.animo) == (95.0, 95.0)
    assert despues_activa.activa and not despues_reserva.activa
    assert db.espera_de(activa.id, sim.ENTRENAR, T0) == sim.COOLDOWNS[sim.ENTRENAR]
    assert db.espera_de(reserva.id, sim.ENTRENAR, T0) == sim.COOLDOWNS[sim.ENTRENAR]
    assert db.marcador(activa.id)[logros.CUIDADOS] == 1
    assert db.marcador(reserva.id)[logros.CUIDADOS] == 1
    assert resultado.delta_asciicoins == 1
    assert resultado.usados == 1
    assert economia.saldos("u1", "g1").asciicoins == 51
    filas = filas_economia()
    assert len(filas) == 1 and filas[0]["tipo"] == "cuidado"
    assert filas[0]["solicitud"] == json.dumps(
        {
            "accion": "entrenar",
            "activo": {"id": activa.id, "nombre": "Mia"},
            "modo": "conjunto",
            "reserva": {"id": reserva.id, "nombre": "Lúa"},
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def test_solo_la_activa_avanza_el_tiempo_y_la_reserva_conserva_su_reloj():
    activa, reserva = pareja()
    ahora = T0 + timedelta(hours=1)

    entrenar("evento", seleccion(activa, reserva), ahora)

    despues_activa = db.obtener(activa.id)
    despues_reserva = db.obtener(reserva.id)
    assert despues_activa is not None and despues_reserva is not None
    assert despues_activa.actualizada_en == ahora
    assert despues_activa.hambre < 90.0
    assert despues_reserva.actualizada_en == T0
    assert despues_reserva.hambre == 90.0
    assert not despues_reserva.activa


def test_el_tope_de_cuidado_no_impide_el_entrenamiento():
    activa, reserva = pareja()
    fecha = T0.date().isoformat()
    with db.conectar() as con:
        for i in range(economia.TOPE_CUIDADOS):
            con.execute(
                "INSERT INTO operaciones_economia VALUES (?, ?, ?, 'cuidado', ?, "
                "'acreditada', 1, 'previa')",
                (f"previa-{i}", "u1", "g1", fecha),
            )

    resultado = entrenar("evento", seleccion(activa, reserva))

    assert resultado.topada and resultado.delta_asciicoins == 0
    assert resultado.usados == economia.TOPE_CUIDADOS
    activa_guardada = db.obtener(activa.id)
    reserva_guardada = db.obtener(reserva.id)
    assert activa_guardada is not None and reserva_guardada is not None
    assert activa_guardada.xp == reserva_guardada.xp == 2
    assert db.marcador(activa.id)[logros.CUIDADOS] == 1
    assert db.marcador(reserva.id)[logros.CUIDADOS] == 1
    assert filas_economia()[-1]["resultado"] == "topada"


@pytest.mark.parametrize("evolucionan", [(True, False), (True, True)])
def test_una_o_dos_evoluciones_producen_una_sola_oportunidad(evolucionan):
    activa, reserva = pareja()
    if evolucionan[0]:
        db.guardar(replace(activa, xp=sim.xp_para_subir(1) - 1))
    if evolucionan[1]:
        db.guardar(replace(reserva, xp=sim.xp_para_subir(1) - 1))

    resultado = entrenar("evento", seleccion(activa, reserva))

    assert tuple(p.evoluciono for p in resultado.participantes) == evolucionan
    assert resultado.delta_evolucion == economia.PREMIO_EVOLUCION
    assert resultado.delta_asciicoins == (
        economia.PREMIO_CUIDADO + economia.PREMIO_EVOLUCION
    )
    assert [fila["tipo"] for fila in filas_economia()] == ["cuidado", "evolucion"]
    assert economia.saldos("u1", "g1").asciicoins == 61


def test_sin_evolucion_no_escribe_oportunidad_de_evolucion():
    activa, reserva = pareja()
    resultado = entrenar("evento", seleccion(activa, reserva))
    assert not any(p.evoluciono for p in resultado.participantes)
    assert resultado.delta_evolucion == 0
    assert [fila["tipo"] for fila in filas_economia()] == ["cuidado"]


def test_evolucion_topada_se_registra_una_vez_y_no_oculta_el_cuidado():
    activa, reserva = pareja()
    db.guardar(replace(activa, xp=sim.xp_para_subir(1) - 1))
    with db.conectar() as con:
        con.execute(
            "INSERT INTO operaciones_economia VALUES "
            "('previa', 'u1', 'g1', 'evolucion', ?, 'acreditada', 10, 'x')",
            (T0.date().isoformat(),),
        )

    resultado = entrenar("evento", seleccion(activa, reserva))

    assert resultado.participantes[0].evoluciono
    assert resultado.delta_evolucion == 0
    assert resultado.evolucion_usadas == economia.TOPE_EVOLUCIONES
    assert resultado.delta_asciicoins == economia.PREMIO_CUIDADO
    filas_evento = [fila for fila in filas_economia() if fila["evento_id"] == "evento"]
    assert [fila["tipo"] for fila in filas_evento] == ["cuidado", "evolucion"]
    assert filas_evento[1]["resultado"] == "topada"


def test_replay_gana_a_la_identidad_caduca_y_el_conflicto_falla():
    activa, reserva = pareja()
    elegida = seleccion(activa, reserva)
    primero = entrenar("evento", elegida)
    estado = (db.obtener(activa.id), db.obtener(reserva.id))
    assert estado[0] is not None and estado[1] is not None
    db.guardar(replace(estado[0], nombre="Renombrada"))

    replay = entrenar("evento", elegida)

    assert primero.delta_asciicoins == replay.delta_asciicoins == 1
    assert replay.replay and replay.participantes == ()
    assert db.obtener(reserva.id) == estado[1]
    with pytest.raises(RuntimeError, match="otra selección"):
        entrenar(
            "evento",
            seleccion(activa, reserva, reserva_nombre="Otro nombre"),
        )


def test_dos_llamadas_concurrentes_del_mismo_evento_aplican_una_vez():
    activa, reserva = pareja()
    elegida = seleccion(activa, reserva)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: entrenar("mismo", elegida), range(2)))

    assert sum(resultado.replay for resultado in resultados) == 1
    activa_guardada = db.obtener(activa.id)
    reserva_guardada = db.obtener(reserva.id)
    assert activa_guardada is not None and reserva_guardada is not None
    assert activa_guardada.xp == reserva_guardada.xp == 2
    assert len(filas_economia()) == 1


def test_eventos_distintos_concurrentes_dejan_un_exito_y_un_cooldown():
    activa, reserva = pareja()
    elegida = seleccion(activa, reserva)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(
            pool.map(lambda evento: entrenar(evento, elegida), ("uno", "dos"))
        )

    assert sorted(resultado.problema or "ok" for resultado in resultados) == [
        "cooldown",
        "ok",
    ]
    activa_guardada = db.obtener(activa.id)
    reserva_guardada = db.obtener(reserva.id)
    assert activa_guardada is not None and reserva_guardada is not None
    assert activa_guardada.xp == reserva_guardada.xp == 2
    assert len(filas_economia()) == 1


@pytest.mark.parametrize("tabla", ["cooldowns", "marcador"])
def test_fallo_del_segundo_participante_revierte_toda_la_pareja(tabla):
    activa, reserva = pareja()
    with db.conectar() as con:
        con.execute(
            f"CREATE TRIGGER rompe_segundo BEFORE INSERT ON {tabla} "
            f"WHEN NEW.criatura_id = {reserva.id} "
            "BEGIN SELECT RAISE(ABORT, 'fallo segundo'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="fallo segundo"):
        entrenar("evento", seleccion(activa, reserva))

    assert db.obtener(activa.id) == activa
    assert db.obtener(reserva.id) == reserva
    assert db.espera_de(activa.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.espera_de(reserva.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.marcador(activa.id) == db.marcador(reserva.id) == {}
    assert filas_economia() == []
    assert economia.saldos("u1", "g1").asciicoins == 50


def test_fallo_al_guardar_la_reserva_revierte_el_guardado_del_activo():
    activa, reserva = pareja()
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_reserva BEFORE UPDATE ON criaturas "
            f"WHEN OLD.id = {reserva.id} "
            "BEGIN SELECT RAISE(ABORT, 'fallo reserva'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="fallo reserva"):
        entrenar("evento", seleccion(activa, reserva))

    assert db.obtener(activa.id) == activa
    assert db.obtener(reserva.id) == reserva
    assert filas_economia() == []


def test_fallo_del_ledger_revierte_criaturas_cooldowns_marcadores_y_saldo():
    activa, reserva = pareja()
    with db.conectar() as con:
        con.execute(
            "CREATE TRIGGER rompe_ledger BEFORE INSERT ON operaciones_economia "
            "BEGIN SELECT RAISE(ABORT, 'fallo ledger'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="fallo ledger"):
        entrenar("evento", seleccion(activa, reserva))

    assert db.obtener(activa.id) == activa
    assert db.obtener(reserva.id) == reserva
    assert db.espera_de(activa.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.espera_de(reserva.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.marcador(activa.id) == db.marcador(reserva.id) == {}
    assert filas_economia() == []
    assert economia.saldos("u1", "g1").asciicoins == 50


def _alterar_identidad(caso, activa, reserva):
    elegida = seleccion(activa, reserva)
    if caso == "activo_id":
        tercera = db.crear(
            "u1", "g1", "michi", "Nube", STATS, T0, activa=False
        )
        assert db.activar(tercera.id, "u1", "g1", T0)
    elif caso == "activo_nombre":
        db.guardar(replace(activa, nombre="Otra"))
    elif caso == "reserva_falta":
        with db.conectar() as con:
            con.execute("DELETE FROM criaturas WHERE id = ?", (reserva.id,))
    elif caso == "reserva_es_activa":
        elegida = seleccion(
            activa,
            reserva,
            reserva_id=activa.id,
            reserva_nombre=activa.nombre,
        )
    elif caso == "reserva_dueño":
        with db.conectar() as con:
            con.execute(
                "UPDATE criaturas SET usuario_id = 'u2' WHERE id = ?",
                (reserva.id,),
            )
    elif caso == "reserva_guild":
        with db.conectar() as con:
            con.execute(
                "UPDATE criaturas SET guild_id = 'g2' WHERE id = ?",
                (reserva.id,),
            )
    elif caso == "reserva_muerta":
        db.guardar(replace(reserva, muerta_en=T0, causa_muerte="prueba"))
    elif caso == "reserva_nombre":
        db.guardar(replace(reserva, nombre="Otra"))
    elif caso == "reserva_activa":
        assert db.activar(reserva.id, "u1", "g1", T0)
    elif caso == "reserva_sin_nombre":
        db.guardar(replace(reserva, nombre=""))
    return elegida


@pytest.mark.parametrize(
    "caso,problema",
    [
        ("activo_id", "activo_caduco"),
        ("activo_nombre", "activo_caduco"),
        ("reserva_falta", "reserva_caduca"),
        ("reserva_es_activa", "reserva_caduca"),
        ("reserva_dueño", "reserva_caduca"),
        ("reserva_guild", "reserva_caduca"),
        ("reserva_muerta", "reserva_caduca"),
        ("reserva_nombre", "reserva_caduca"),
        ("reserva_activa", "activo_caduco"),
        ("reserva_sin_nombre", "reserva_caduca"),
    ],
)
def test_identidad_caduca_no_muta_la_pareja_ni_escribe_ledger(caso, problema):
    activa, reserva = pareja()
    elegida = _alterar_identidad(caso, activa, reserva)
    antes = (db.obtener(activa.id), db.obtener(reserva.id))

    resultado = entrenar("evento", elegida)

    assert resultado.problema == problema
    assert (db.obtener(activa.id), db.obtener(reserva.id)) == antes
    assert filas_economia() == []


@pytest.mark.parametrize("bloqueada", ["activa", "reserva"])
def test_cooldown_de_cualquiera_rechaza_sin_mutacion_ni_ledger(bloqueada):
    activa, reserva = pareja()
    criatura = activa if bloqueada == "activa" else reserva
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    antes = (db.obtener(activa.id), db.obtener(reserva.id))

    resultado = entrenar("evento", seleccion(activa, reserva))

    assert resultado.problema == "cooldown"
    assert resultado.bloqueada is not None
    assert resultado.bloqueada.id == criatura.id
    assert resultado.espera == sim.COOLDOWNS[sim.ENTRENAR]
    assert (db.obtener(activa.id), db.obtener(reserva.id)) == antes
    assert filas_economia() == []


def test_muerte_perezosa_persiste_solo_la_activa():
    activa, reserva = pareja()
    db.guardar(replace(activa, hambre=0.1))

    resultado = entrenar(
        "evento", seleccion(activa, reserva), T0 + timedelta(hours=1)
    )

    muerta = db.obtener(activa.id)
    assert resultado.problema == "activo_muerto"
    assert muerta is not None and not muerta.viva
    assert db.obtener(reserva.id) == reserva
    assert filas_economia() == []
    assert db.marcador(activa.id) == db.marcador(reserva.id) == {}


def test_evento_incompleto_o_de_otro_tipo_falla_antes_del_plantel():
    activa, reserva = pareja()
    with db.conectar() as con:
        con.execute(
            "INSERT INTO operaciones_economia VALUES "
            "('evento', 'u1', 'g1', 'compra', ?, 'saldo_insuficiente', 0, 'x')",
            (T0.date().isoformat(),),
        )

    with pytest.raises(RuntimeError, match="incompleto"):
        entrenar("evento", seleccion(activa, reserva))
