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
import cogs.competencias as cog_comp
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


def test_recibo_de_competencia_detalla_efecto_costo_recompensa_y_tope():
    recibo = economia.ReciboCompetencia(
        usuario_id="u1",
        delta_asciicoins=economia.PREMIO_GANADOR,
        delta_competencia=economia.PREMIO_GANADOR,
        delta_evolucion=0,
        usados=1,
    )

    assert cog_comp.texto_recibo_competencia(
        recibo, "<@u1>", gano=True, stat="velocidad"
    ) == (
        "-# <@u1> · velocidad +1 entrenamiento · +10 XP · "
        "coste base -10 comida · coste base -5 ánimo · "
        "🪙 +6 asciicoins · competencia 1/3 UTC"
    )


def test_recibo_de_competencia_conserva_topes_de_moneda_y_evolucion():
    recibo = economia.ReciboCompetencia(
        usuario_id="u1",
        delta_asciicoins=0,
        delta_competencia=0,
        delta_evolucion=0,
        usados=economia.TOPE_COMPETENCIAS,
        evolucion_usadas=economia.TOPE_EVOLUCIONES,
        topada=True,
        evoluciono=True,
        evolucion_topada=True,
    )

    assert cog_comp.texto_recibo_competencia(
        recibo, "<@u1>", gano=False, stat="fuerza"
    ).endswith(
        "🪙 +0 asciicoins · competencia 3/3 UTC (tope) · "
        "evolución +0 · evolución 1/1 UTC (tope)"
    )


def test_disputar_cinco_participantes_publica_recibos_emparejados_y_cabe(
    monkeypatch,
):
    usuarios = tuple(str(1_000_000_000_000_000_001 + n) for n in range(5))
    nombres = tuple(f"CriaturaLimite{n:010d}" for n in range(1, 6))
    assert all(len(nombre) == sim.LARGO_MAXIMO_NOMBRE for nombre in nombres)
    for usuario, nombre in zip(usuarios, nombres):
        db.crear(usuario, "g1", "pulpo", nombre, STATS, T0)

    resultado = competir("evento-cinco", usuarios=usuarios, semilla=1)
    assert resultado.encuentro is not None
    assert tuple(criatura.nombre for criatura in resultado.antes) == nombres
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    cog = Competencias.__new__(Competencias)
    cog._animar = AsyncMock()
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    participantes = [
        SimpleNamespace(
            id=int(usuario), mention=f"<@{usuario}>", display_name=nombre
        )
        for usuario, nombre in zip(usuarios, nombres)
    ]

    asyncio.run(
        cog.disputar(canal, participantes, comp.CARRERA, "g1", "publicacion")
    )

    canal.send.assert_awaited_once()
    resumen = canal.send.await_args.args[0]
    lineas = [linea for linea in resumen.splitlines() if linea.startswith("-# <@")]
    assert len(resumen) < 2000
    assert len(lineas) == 5
    assert [linea.split(" · ", 1)[0] for linea in lineas] == [
        f"-# <@{usuario}>" for usuario in usuarios
    ]
    ganador = resultado.encuentro.orden[0]
    assert sum("+10 XP" in linea for linea in lineas) == 1
    assert sum("+4 XP" in linea for linea in lineas) == 4
    for dorsal, linea in enumerate(lineas):
        assert f"+{10 if dorsal == ganador else 4} XP" in linea
        assert "velocidad +1 entrenamiento" in linea
        assert "coste base -10 comida" in linea
        assert "coste base -5 ánimo" in linea


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
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
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


def test_competencia_congela_todas_las_fichas_antes_de_animar_y_no_repite(
    monkeypatch,
):
    antes = (
        replace(nacer("u1"), pantalla_msg_id="ficha-1", canal_id="101"),
        replace(nacer("u2"), pantalla_msg_id="ficha-2", canal_id="102"),
    )
    despues = (replace(antes[0], nivel=2), antes[1])
    resultado = SimpleNamespace(
        replay=False,
        problema=None,
        encuentro=SimpleNamespace(orden=(0, 1)),
        antes=antes,
        despues=despues,
        subidas=(("fuerza",), ()),
        recibos=(object(), object()),
    )
    eventos = []

    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.comp, "fotogramas_de", lambda _: [["tramo"]])
    monkeypatch.setattr(cog_comp.comp, "resumen", lambda _: "resumen")
    monkeypatch.setattr(
        cog_comp, "texto_recibo_competencia", lambda *_, **__: "recibo"
    )

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    async def animar(canal, fotogramas):
        eventos.append(("animar", canal, fotogramas))

    async def publicar(canal, criatura, ahora, **kwargs):
        eventos.append(("publicar", criatura, kwargs))

    monkeypatch.setattr(cog_comp.vistas, "congelar", congelar)
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", publicar)
    cog = Competencias.__new__(Competencias)
    cog._animar = animar
    canales_anteriores = {
        101: SimpleNamespace(id=101),
        102: SimpleNamespace(id=102),
    }
    canal = SimpleNamespace(
        id=999,
        guild=SimpleNamespace(get_channel_or_thread=canales_anteriores.get),
        send=AsyncMock(),
    )
    participantes = [
        SimpleNamespace(id="u1", mention="<@u1>", display_name="u1"),
        SimpleNamespace(id="u2", mention="<@u2>", display_name="u2"),
    ]

    asyncio.run(cog.disputar(canal, participantes, comp.CARRERA, "g1", "evento"))

    assert eventos[:3] == [
        ("congelar", canales_anteriores[101], "ficha-1"),
        ("congelar", canales_anteriores[102], "ficha-2"),
        ("animar", canal, ["tramo"]),
    ]
    assert eventos[-1][0] == "publicar"
    assert eventos[-1][2] == {"ya_congelada": "ficha-1"}


@pytest.mark.parametrize(
    "resultado",
    [
        SimpleNamespace(replay=True, problema=None),
        SimpleNamespace(
            replay=False,
            problema="no puede competir",
            problema_usuario_id=None,
        ),
    ],
)
def test_competencia_repetida_o_rechazada_no_congela(monkeypatch, resultado):
    congelar = AsyncMock()
    monkeypatch.setattr(cog_comp.db, "ahora_utc", lambda: T0)
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", lambda *_: resultado
    )
    monkeypatch.setattr(cog_comp.vistas, "congelar", congelar)
    cog = Competencias.__new__(Competencias)
    canal = SimpleNamespace(send=AsyncMock())

    asyncio.run(cog.disputar(canal, [], comp.CARRERA, "g1", "evento"))

    congelar.assert_not_awaited()
