import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import discord

import config
import db
import identidad
import vistas
from cogs import mascota as cog_mascota

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TARDE = T0 + timedelta(days=5)
STATS = (10, 10, 10, 10)
G = "g"
ANA = "222222222222222222"
WEB = identidad.de_cuenta_web(1)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "muertes.db")
    db.inicializar()


def nace(usuario=ANA, nombre="Viejo", **mas):
    return db.crear(usuario, G, "pollito", nombre, STATS, T0, **mas)


def apuntes():
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(
            "SELECT criatura_id, relevo_id FROM muertes_por_anunciar "
            "ORDER BY criatura_id")]


def test_la_muerte_de_una_identidad_de_discord_queda_apuntada():
    muerto = nace()
    assert db.activa_al_dia(ANA, G, TARDE) is None
    apuntadas = db.muertes_por_anunciar()
    assert [(m.id, r) for m, r in apuntadas] == [(muerto.id, None)]
    assert apuntadas[0][0].causa_muerte == "hambre"


def test_el_relevo_apuntado_es_el_que_sale_y_es_el_que_se_devuelve():
    muerto = nace()
    relevo = nace(nombre="Tinta", activa=False)
    devuelto = db.activa_al_dia(ANA, G, TARDE)
    assert devuelto.id == relevo.id
    assert apuntes() == [(muerto.id, relevo.id)]
    (m, r), = db.muertes_por_anunciar()
    assert m.id == muerto.id and r.id == relevo.id


def test_dos_llamadas_dejan_un_solo_apunte():
    nace()
    nace(nombre="Tinta", activa=False)
    db.activa_al_dia(ANA, G, TARDE)
    db.activa_al_dia(ANA, G, TARDE)
    assert len(apuntes()) == 1


def test_una_muerte_que_registro_el_bot_no_deja_apunte():
    muerto = nace()
    db.guardar(db.avanzar(db.por_id(muerto.id), TARDE))
    db.activa_al_dia(ANA, G, TARDE)
    assert apuntes() == []


def test_una_identidad_web_nunca_deja_apunte(monkeypatch):
    nace(usuario=WEB)
    muere = lambda c, ahora: replace(c, muerta_en=ahora, causa_muerte="hambre")
    monkeypatch.setattr(db, "avanzar", muere)
    monkeypatch.setattr(db, "_avanzar_en", lambda con, c, ahora: muere(c, ahora))
    assert db.activa_al_dia(WEB, G, TARDE) is None
    assert apuntes() == []


def test_acariciar_a_uno_que_murio_de_hambre_lo_deja_apuntado():
    muerto = nace()
    assert not db.acariciar(ANA, G, TARDE).ok
    assert apuntes() == [(muerto.id, None)]


def test_muerte_anunciada_borra_y_se_puede_repetir():
    muerto = nace()
    db.activa_al_dia(ANA, G, TARDE)
    db.muerte_anunciada(muerto.id)
    db.muerte_anunciada(muerto.id)
    assert apuntes() == [] and db.muertes_por_anunciar() == []


def test_un_relevo_que_ya_no_esta_activo_o_murio_sale_como_none():
    nace()
    relevo = nace(nombre="Tinta", activa=False)
    db.activa_al_dia(ANA, G, TARDE)
    db.guardar(replace(db.por_id(relevo.id), activa=False))
    assert db.muertes_por_anunciar()[0][1] is None
    db.guardar(replace(db.por_id(relevo.id), activa=True, muerta_en=TARDE,
                       causa_muerte="hambre"))
    assert db.muertes_por_anunciar()[0][1] is None


def test_sin_activa_saca_al_de_la_incubadora_que_tiene_nombre():
    espera = nace(activa=False)
    assert db.activa_al_dia(ANA, G, T0).id == espera.id
    assert db.criatura_activa(ANA, G).id == espera.id


def test_sin_activa_y_con_uno_sin_nombre_no_cambia_nada():
    sin_nombre = nace(nombre="", activa=False)
    assert db.activa_al_dia(ANA, G, T0) is None
    assert db.criatura_activa(ANA, G) is None
    assert db.por_id(sin_nombre.id).activa is False


def test_dos_a_la_vez_dejan_un_apunte_y_un_relevo():
    muerto = nace()
    relevo = nace(nombre="Tinta", activa=False)
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(
            lambda _: db.activa_al_dia(ANA, G, TARDE), range(2)))
    assert [r.id for r in resultados] == [relevo.id, relevo.id]
    assert apuntes() == [(muerto.id, relevo.id)]


def _justo_despues_de_leer(monkeypatch, que_pasa):
    """`db.avanzar` es lo último que corre antes de que `activa_al_dia` abra su
    transacción: lo que se haga aquí es lo que ocurre «entre medias»."""
    original = db.avanzar
    hecho = []

    def envoltorio(criatura, ahora):
        resultado = original(criatura, ahora)
        if not hecho:
            hecho.append(True)
            que_pasa(resultado)
        return resultado

    monkeypatch.setattr(db, "avanzar", envoltorio)


def test_si_el_bot_guarda_la_muerte_entre_medias_no_se_apunta(monkeypatch):
    nace()
    _justo_despues_de_leer(monkeypatch, db.guardar)   # lo que haría el bucle
    db.activa_al_dia(ANA, G, TARDE)
    assert apuntes() == []


def test_la_muerte_se_guarda_sobre_la_fila_releida(monkeypatch):
    muerto = nace()
    _justo_despues_de_leer(
        monkeypatch, lambda _: db.guardar_pantalla(muerto.id, "999", "5"))
    db.activa_al_dia(ANA, G, TARDE)
    fila = db.por_id(muerto.id)
    assert fila.muerta_en is not None and fila.pantalla_msg_id == "999"
    assert apuntes() == [(muerto.id, None)]


# -- el bucle del bot ---------------------------------------------------------

def correr_bucle(monkeypatch):
    canal = SimpleNamespace(send=AsyncMock())
    monkeypatch.setattr(vistas, "congelar", AsyncMock())
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    monkeypatch.setattr(config, "CANAL_PRINCIPAL", 1)
    monkeypatch.setattr(db, "ahora_utc", lambda: TARDE)
    cog = cog_mascota.Mascota(SimpleNamespace(get_channel=lambda _: canal))
    asyncio.run(cog_mascota.Mascota.revisar_muertes.coro(cog))
    return canal


def textos(canal):
    return [c.args[0] for c in canal.send.await_args_list]


def test_el_bucle_anuncia_lo_apuntado_una_sola_vez(monkeypatch):
    nace(nombre="Viejo")
    nace(nombre="Tinta", activa=False)
    db.activa_al_dia(ANA, G, TARDE)           # lo registra la web
    assert db.pendientes_de_morir(TARDE) == []

    canal = correr_bucle(monkeypatch)
    enviados = textos(canal)
    assert any("**Viejo** ha muerto de hambre" in t for t in enviados)
    assert any("**Tinta**" in t for t in enviados)
    assert apuntes() == []

    canal = correr_bucle(monkeypatch)
    assert canal.send.await_count == 0


def test_el_bucle_no_anuncia_dos_veces_la_que_procesa_el_mismo(monkeypatch):
    muerto = nace(nombre="Viejo")
    with db.conectar() as con:                # un apunte de la web, a la vez
        con.execute("INSERT INTO muertes_por_anunciar VALUES (?, NULL)",
                    (muerto.id,))
    canal = correr_bucle(monkeypatch)
    muertes = [t for t in textos(canal) if "ha muerto de hambre" in t]
    assert len(muertes) == 1
    assert apuntes() == []


def test_una_base_sin_la_tabla_la_gana_al_inicializar():
    with db.conectar() as con:
        con.execute("DROP TABLE muertes_por_anunciar")
    db.inicializar()
    assert apuntes() == []


def test_un_anuncio_que_falla_se_registra_y_no_se_reintenta(monkeypatch):
    primera = nace(nombre="Primera")
    segunda = nace(usuario="333333333333333333", nombre="Segunda")
    db.activa_al_dia(ANA, G, TARDE)
    db.activa_al_dia(segunda.usuario_id, G, TARDE)
    assert len(apuntes()) == 2

    fallo = discord.HTTPException(SimpleNamespace(status=500, reason="x"), "x")
    enviar = AsyncMock(side_effect=[fallo, None, None])
    monkeypatch.setattr(vistas, "congelar", AsyncMock())
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    monkeypatch.setattr(config, "CANAL_PRINCIPAL", 1)
    monkeypatch.setattr(db, "ahora_utc", lambda: TARDE)
    canal = SimpleNamespace(send=enviar)
    cog = cog_mascota.Mascota(SimpleNamespace(get_channel=lambda _: canal))
    asyncio.run(cog_mascota.Mascota.revisar_muertes.coro(cog))

    assert apuntes() == []
    enviados = [c.args[0] for c in enviar.await_args_list]
    assert any("**Segunda** ha muerto" in t for t in enviados)

    enviar.reset_mock(side_effect=True)
    asyncio.run(cog_mascota.Mascota.revisar_muertes.coro(cog))
    assert enviar.await_count == 0
    assert primera.id  # la que falló no vuelve
