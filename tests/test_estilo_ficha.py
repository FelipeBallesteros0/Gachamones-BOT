"""Preferencia pública Imagen/ASCII de las fichas."""
import asyncio
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import aventura as av
import competir as comp
import cogs.aventura as cog_av
import cogs.competencias as cog_comp
import cogs.mascota as cog_mascota
import db
import economia
import especies as esp
import pantalla
import retrato
import simulacion as sim
import vistas

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "estilo-ficha.db")
    db.inicializar()


def geo(usuario="dueno", guild="g1") -> sim.Criatura:
    return db.crear(usuario, guild, "pedrusco", "Geo", STATS, T0)


def test_el_default_imagen_no_muta_ninguna_tabla_de_persona():
    assert db.estilo_de_ficha("u1", "g1") == "imagen"

    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM estilos_ficha").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM monederos").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM marcador_persona").fetchone()[0] == 0


def test_el_setter_persiste_y_aisla_el_estilo_por_servidor():
    db.guardar_estilo_de_ficha("u1", "g1", "ascii")
    db.guardar_estilo_de_ficha("u1", "g2", "imagen")
    db.inicializar()

    assert db.estilo_de_ficha("u1", "g1") == "ascii"
    assert db.estilo_de_ficha("u1", "g2") == "imagen"
    assert db.estilo_de_ficha("u2", "g1") == "imagen"


def test_la_restriccion_rechaza_un_estilo_invalido_incluso_por_sql():
    with pytest.raises(ValueError):
        db.guardar_estilo_de_ficha("u1", "g1", "automatico")

    with db.conectar() as con, pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO estilos_ficha (usuario_id, guild_id, estilo) "
            "VALUES ('u1', 'g1', 'automatico')"
        )


def test_cambiar_de_activa_conserva_el_estilo_de_la_persona():
    primera = geo()
    segunda = db.crear(
        "dueno", "g1", "chispa", "Reserva", STATS, T0, activa=False
    )
    db.guardar_estilo_de_ficha("dueno", "g1", "ascii")

    db.activar(segunda.id, "dueno", "g1", T0)

    assert primera.id != segunda.id
    assert db.estilo_de_ficha("dueno", "g1") == "ascii"


def test_la_ficha_propia_default_usa_imagen_sin_ascii_duplicado():
    ficha = vistas._ficha(geo(), T0)

    assert ficha["content"] is None
    assert {"embed", "file"} <= ficha.keys()
    assert "┏" not in ficha["embed"].description


def test_la_presentacion_especial_default_usa_retrato_sin_repetir_el_dibujo():
    criatura = replace(geo(), nivel=2)

    ficha = vistas.presentacion(
        criatura, pantalla.render_evolucion, esp.BEBE
    )

    assert ficha["content"] is None
    assert {"embed", "file"} <= ficha.keys()
    assert "ha evolucionado" in ficha["embed"].description
    arte = esp.arte_de(criatura.def_especie, criatura.etapa, esp.FELIZ)
    primera = next(linea for linea in arte.splitlines() if linea.strip())
    assert primera.strip() not in ficha["embed"].description


def test_la_presentacion_especial_respeta_ascii_aunque_haya_retrato():
    criatura = replace(geo(), nivel=2)
    db.guardar_estilo_de_ficha("dueno", "g1", "ascii")

    ficha = vistas.presentacion(
        criatura, pantalla.render_evolucion, esp.BEBE
    )

    assert set(ficha) == {"content"}
    assert "```ansi" in ficha["content"]


def test_la_presentacion_especial_sin_retrato_cae_a_ascii_y_limpia_adjuntos():
    sin_retrato = next(
        clave for clave in esp.ESPECIES if clave not in retrato.CON_ETAPAS_COMPLETAS
    )
    criatura = db.crear("dueno", "g1", sin_retrato, "Sin foto", STATS, T0)

    ficha = vistas._como_edicion(
        vistas.presentacion(criatura, pantalla.render_revelacion, T0)
    )

    assert "```ansi" in ficha["content"]
    assert ficha["attachments"] == []
    assert ficha["embed"] is None


def test_cuidado_que_evoluciona_usa_la_presentacion_publica(monkeypatch):
    criatura = replace(geo(), nivel=2, pantalla_msg_id="ficha")
    resultado = economia.ResultadoCuidado(
        criatura=criatura,
        mensaje="Entrenamiento duro.",
        etapa_anterior=esp.BEBE,
        usados=1,
    )
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(db, "criatura_por_pantalla", Mock(return_value=criatura))
    monkeypatch.setattr(economia, "ejecutar_cuidado", Mock(return_value=resultado))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    monkeypatch.setattr(vistas, "publicar_pantalla", AsyncMock())
    monkeypatch.setattr(vistas.comun, "anunciar_logros", AsyncMock())
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    interaccion = SimpleNamespace(
        id="evento",
        user=SimpleNamespace(id="dueno"),
        guild_id="g1",
        message=SimpleNamespace(id="ficha"),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
        channel=canal,
    )

    asyncio.run(vistas._ejecutar(interaccion, sim.ENTRENAR))

    assert canal.send.await_count == 1
    assert canal.send.await_args.kwargs["content"] is None
    assert {"embed", "file"} <= canal.send.await_args.kwargs.keys()


def test_aventura_que_evoluciona_usa_la_presentacion_publica(monkeypatch):
    antes = replace(geo(), pantalla_msg_id="ficha")
    despues = replace(antes, nivel=2)
    confirmado = economia.ResultadoViaje(despues, antes=antes)
    monkeypatch.setattr(cog_av.db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(cog_av.db, "plantel", Mock(return_value=[]))
    monkeypatch.setattr(cog_av.economia, "ejecutar_viaje", Mock(return_value=confirmado))
    monkeypatch.setattr(cog_av.av, "tirar_hallazgo", Mock(return_value=av.NADA))
    monkeypatch.setattr(cog_av.av, "tirar_percance", Mock(return_value=None))
    monkeypatch.setattr(cog_av.av, "render_pruebas", Mock(return_value="PRUEBAS"))
    monkeypatch.setattr(cog_av, "_narrar", AsyncMock(return_value="NARRACIÓN"))
    monkeypatch.setattr(cog_av.comun, "anunciar_logros", AsyncMock())
    canal = SimpleNamespace(send=AsyncMock())
    dueño = SimpleNamespace(id="dueno", mention="<@dueno>", display_name="Dueño")
    viaje = SimpleNamespace(
        salida=SimpleNamespace(), bioma=SimpleNamespace(), nodos_superados=0
    )
    cog = cog_av.Aventura.__new__(cog_av.Aventura)
    cog._contar_lo_encontrado = AsyncMock()

    asyncio.run(cog.resolver(canal, dueño, "g1", antes, viaje))

    anuncios = [call.kwargs for call in canal.send.await_args_list if "file" in call.kwargs]
    assert len(anuncios) == 1
    assert anuncios[0]["content"] is None
    assert "ha evolucionado" in anuncios[0]["embed"].description


def test_competencia_que_evoluciona_usa_la_presentacion_publica(monkeypatch):
    antes = (
        replace(geo(), pantalla_msg_id="ficha-1"),
        db.crear("rival", "g1", "pedrusco", "Rival", STATS, T0),
    )
    despues = (replace(antes[0], nivel=2), antes[1])
    resultado = SimpleNamespace(
        replay=False,
        problema=None,
        encuentro=SimpleNamespace(orden=(0, 1)),
        antes=antes,
        despues=despues,
        rupturas=((), ()),
        recibos=(object(), object()),
    )
    monkeypatch.setattr(cog_comp.db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(
        cog_comp.economia, "ejecutar_competencia", Mock(return_value=resultado)
    )
    monkeypatch.setattr(cog_comp.comp, "fotogramas_de", Mock(return_value=[]))
    monkeypatch.setattr(cog_comp.comp, "resumen", Mock(return_value="RESUMEN"))
    monkeypatch.setattr(cog_comp, "texto_recibo_competencia", Mock(return_value="RECIBO"))
    monkeypatch.setattr(cog_comp.vistas, "congelar", AsyncMock())
    monkeypatch.setattr(cog_comp.vistas, "publicar_pantalla", AsyncMock())
    monkeypatch.setattr(cog_comp.comun, "anunciar_logros", AsyncMock())
    monkeypatch.setattr(cog_comp.db, "plantel", Mock(return_value=[]))
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    participantes = [
        SimpleNamespace(id="dueno", mention="<@dueno>", display_name="Dueño"),
        SimpleNamespace(id="rival", mention="<@rival>", display_name="Rival"),
    ]
    cog = cog_comp.Competencias.__new__(cog_comp.Competencias)
    cog._animar = AsyncMock()

    asyncio.run(cog.disputar(canal, participantes, comp.CARRERA, "g1", "evento"))

    anuncios = [call.kwargs for call in canal.send.await_args_list if "file" in call.kwargs]
    assert len(anuncios) == 1
    assert anuncios[0]["content"] is None
    assert "ha evolucionado" in anuncios[0]["embed"].description


def test_romper_el_huevo_usa_la_presentacion_publica(monkeypatch):
    monkeypatch.setattr(cog_mascota.db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(
        cog_mascota.esp, "elegir_del_huevo", Mock(return_value=esp.ESPECIES["pedrusco"])
    )
    monkeypatch.setattr(cog_mascota.esp, "tirar_stats_iniciales", Mock(return_value=STATS))
    monkeypatch.setattr(cog_mascota.esp, "tirar_genero", Mock(return_value=esp.MACHO))
    monkeypatch.setattr(cog_mascota.per, "tirar_caracter", Mock(return_value="sereno"))
    monkeypatch.setattr(cog_mascota.comun, "anunciar_logros_de_persona", AsyncMock())
    respuesta = SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock())
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="dueno", display_name="Dueño"),
        guild_id="g1",
        channel_id="canal",
        channel=SimpleNamespace(),
        response=respuesta,
        original_response=AsyncMock(return_value=SimpleNamespace(id="revelacion")),
    )

    asyncio.run(cog_mascota.HuevoView("dueno").romper.callback(interaccion))

    ficha = respuesta.edit_message.await_args.kwargs
    assert ficha["content"] is None
    assert len(ficha["attachments"]) == 1
    assert "¡Ha salido" in ficha["embed"].description


def test_la_ficha_propia_respeta_ascii_aunque_haya_retrato():
    criatura = geo()
    db.guardar_estilo_de_ficha("dueno", "g1", "ascii")

    ficha = vistas._ficha(criatura, T0)

    assert set(ficha) == {"content"}
    assert "Geo" in ficha["content"]


def test_imagen_sin_asset_cae_silenciosamente_a_ascii():
    sin_retrato = next(
        clave for clave in esp.ESPECIES if clave not in retrato.CON_ETAPAS_COMPLETAS
    )
    criatura = db.crear("dueno", "g1", sin_retrato, "Sin foto", STATS, T0)

    ficha = vistas._ficha(criatura, T0)

    assert set(ficha) == {"content"}
    assert "Sin foto" in ficha["content"]


def test_una_lapida_no_consulta_la_preferencia(monkeypatch):
    criatura = sim.avanzar(geo(), T0.replace(year=2027))
    assert not criatura.viva
    getter = Mock(side_effect=AssertionError("una lápida no consulta estilo"))
    monkeypatch.setattr(db, "estilo_de_ficha", getter)

    ficha = vistas._ficha(criatura, T0.replace(year=2027))

    getter.assert_not_called()
    assert set(ficha) == {"content"}
