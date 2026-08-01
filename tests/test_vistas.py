# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""Las mutaciones externas apagan la ficha viva que acaba de quedar obsoleta."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest

import db
import economia
import equipo
import pantalla
import simulacion as sim
import vistas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (15, 15, 15)


def criatura(id_, nombre, activa, pantalla_msg_id) -> sim.Criatura:
    return sim.Criatura(
        id=id_, usuario_id="u1", guild_id="g1", especie="pulpo", nombre=nombre,
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
        hambre=80.0, animo=80.0, activa=activa,
        pantalla_msg_id=pantalla_msg_id,
    )


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "vistas.db")
    db.inicializar()


def interaccion_de(
    evento_id="evento", mensaje_id="ficha"
) -> tuple[Any, SimpleNamespace, SimpleNamespace]:
    respuesta = SimpleNamespace(
        edit_message=AsyncMock(),
        send_message=AsyncMock(),
    )
    canal = SimpleNamespace(id="canal", send=AsyncMock())
    interaccion = SimpleNamespace(
        id=evento_id,
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        message=SimpleNamespace(id=mensaje_id),
        response=respuesta,
        channel=canal,
    )
    return interaccion, respuesta, canal


def test_recibo_de_entrenamiento_detalla_efecto_costo_recompensa_y_tope():
    resultado = economia.ResultadoCuidado(
        criatura=criatura(1, "Mia", True, "ficha"),
        mensaje="Entrenamiento duro.",
        delta_asciicoins=1,
        usados=1,
    )

    assert vistas.texto_recibo_cuidado(resultado, sim.ENTRENAR) == (
        "-# 🏋️ Entrenar · fuerza +2 entrenamiento · +3 XP · "
        "coste base -15 comida · coste base -10 ánimo · "
        "🪙 +1 asciicoins · cuidado 1/12 UTC"
    )


def test_recibo_de_cuidado_conserva_topes_y_recompensa_de_evolucion():
    base = criatura(1, "Mia", True, "ficha")
    evolucionada = replace(base, nivel=5)

    topada = economia.ResultadoCuidado(
        criatura=base,
        mensaje="Entrenamiento duro.",
        delta_asciicoins=0,
        usados=economia.TOPE_CUIDADOS,
        topada=True,
    )
    assert vistas.texto_recibo_cuidado(topada, sim.ENTRENAR).endswith(
        "🪙 +0 asciicoins · cuidado 12/12 UTC (tope)"
    )

    evolucion = economia.ResultadoCuidado(
        criatura=evolucionada,
        mensaje="Entrenamiento duro.",
        etapa_anterior=base.etapa,
        delta_asciicoins=economia.PREMIO_EVOLUCION,
        delta_evolucion=economia.PREMIO_EVOLUCION,
        usados=economia.TOPE_CUIDADOS,
        evolucion_usadas=economia.TOPE_EVOLUCIONES,
        topada=True,
    )
    assert vistas.texto_recibo_cuidado(evolucion, sim.ENTRENAR).endswith(
        "🪙 +0 asciicoins · cuidado 12/12 UTC (tope) · "
        "evolución +10 · 1/1 UTC"
    )


def test_pantalla_inyecta_el_congelador_en_mochila_y_plantel(monkeypatch):
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    abrir_inventario = AsyncMock()
    abrir_plantel = AsyncMock()
    monkeypatch.setattr(vistas.tienda, "abrir_inventario", abrir_inventario)
    monkeypatch.setattr(vistas.equipo, "abrir_plantel", abrir_plantel)
    interaccion = SimpleNamespace()
    botones = {boton.custom_id: boton for boton in vistas.PantallaView().children}

    asyncio.run(botones["tama:inventario"].callback(interaccion))
    asyncio.run(botones["tama:plantel"].callback(interaccion))

    abrir_inventario.assert_awaited_once_with(interaccion, vistas.congelar)
    # El plantel recibe además el bautizo: es lo que le deja mandar a poner
    # nombre al recluta sin importar este módulo, que ya lo importa a él.
    abrir_plantel.assert_awaited_once_with(
        interaccion, vistas.congelar, vistas.bautizar
    )


def test_cambiar_activo_congela_la_ficha_anterior_antes_de_responder(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    nueva = criatura(2, "Nueva", False, "ficha-nueva")
    monkeypatch.setattr(
        equipo.db, "criatura_activa", Mock(side_effect=[anterior, nueva])
    )
    monkeypatch.setattr(equipo.db, "activar", Mock(return_value=True))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    eventos = []

    async def responder(**_):
        eventos.append("respuesta")

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    menu = equipo.MenuPlantel([anterior, nueva], congelar)
    menu._values = [str(nueva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert eventos == [("congelar", canal, "ficha-anterior"), "respuesta"]


def test_cambiar_al_mismo_activo_no_congela(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    menu = equipo.MenuPlantel([anterior], congelar)
    menu._values = [str(anterior.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()
    activar.assert_not_called()


def test_cambio_de_activo_invalido_no_congela(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    ajena = criatura(2, "Ajena", False, "ficha-ajena")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    monkeypatch.setattr(equipo.db, "activar", Mock(return_value=False))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    menu = equipo.MenuPlantel([anterior, ajena], congelar)
    menu._values = [str(ajena.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()


# --- La ficha vive en su canal, no en el que se escribe ----------------------

def canal_falso(id_, guild=None):
    mensaje = SimpleNamespace(edit=AsyncMock())
    return SimpleNamespace(
        id=id_, guild=guild, mensaje=mensaje,
        fetch_message=AsyncMock(return_value=mensaje),
    )


def guild_falso(canales=(), hilos=()):
    """Un servidor como el de discord.py: `get_channel` no mira en los hilos."""
    por_id = {canal.id: canal for canal in canales}
    con_hilos = por_id | {hilo.id: hilo for hilo in hilos}
    return SimpleNamespace(
        get_channel=lambda cid: por_id.get(str(cid)),
        get_channel_or_thread=lambda cid: con_hilos.get(str(cid)),
    )


def dos_canales(guardado_id, actual_id, en_hilo=False):
    """El canal donde quedó la ficha y aquel donde se abre el menú."""
    guardado = canal_falso(guardado_id)
    if en_hilo:
        guild = guild_falso(hilos=(guardado,))
    else:
        guild = guild_falso(canales=(guardado,))
    return guardado, canal_falso(actual_id, guild=guild)


def menu_de_plantel(plantel, elegido, canal):
    """El `/plantel` de verdad: el menú abierto en un canal cualquiera."""
    menu = equipo.MenuPlantel(plantel, vistas.congelar)
    menu._values = [str(elegido.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=AsyncMock()),
    )
    return menu, interaccion


def test_congelar_va_al_canal_guardado_de_la_ficha_y_no_al_de_la_orden(bd_temporal):
    """Los menús sólo saben desde dónde se les abrió; la ficha sabe dónde está."""
    mia = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar_pantalla(mia.id, "555", "111")
    guardado, actual = dos_canales("111", "222")

    asyncio.run(vistas.congelar(actual, "555"))

    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert guardado.mensaje.edit.await_args.kwargs["view"].children[0].disabled


def test_cambiar_de_activo_desde_otro_canal_congela_la_ficha_donde_esta(bd_temporal):
    """`/plantel` se abre en cualquier canal; la ficha anterior no se mueve."""
    anterior = db.crear("u1", "g1", "pulpo", "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False)
    guardado, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()


def test_cambiar_de_activo_congela_la_ficha_que_quedo_en_un_hilo(bd_temporal):
    """Un hilo es un canal más donde jugar, y `get_channel` no lo encuentra."""
    anterior = db.crear("u1", "g1", "pulpo", "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False)
    hilo, actual = dos_canales("111", "222", en_hilo=True)

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    hilo.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert hilo.mensaje.edit.await_args.kwargs["view"].children[0].disabled


def test_cambiar_de_activo_con_un_canal_guardado_ilegible_responde_igual(bd_temporal):
    """Una ficha vieja con un canal que no es un número no rompe el menú."""
    anterior = db.crear("u1", "g1", "pulpo", "Anterior", STATS, T0)
    db.guardar_pantalla(anterior.id, "555", "canal-viejo")
    reserva = db.crear("u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False)
    _, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    actual.fetch_message.assert_awaited_once_with(555)
    interaccion.response.edit_message.assert_awaited_once()
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id


# --- El recluta que todavía no tiene nombre ---------------------------------

def test_elegir_a_un_recluta_sin_nombre_abre_el_bautizo(monkeypatch):
    """Elegirlo no es un error del que quejarse: es el momento de nombrarlo."""
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    bautizar = AsyncMock()
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock(), bautizar)
    menu._values = [str(recluta.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(cast(Any, interaccion)))

    bautizar.assert_awaited_once_with(interaccion, recluta)
    # Y no se activa: eso es justo lo que no puede pasar sin nombre.
    activar.assert_not_called()


def test_sin_bautizo_inyectado_se_explica_en_vez_de_activar(monkeypatch):
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock())
    menu._values = [str(recluta.id)]
    editar = AsyncMock()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=editar),
    )

    asyncio.run(menu.callback(cast(Any, interaccion)))

    activar.assert_not_called()
    assert editar.await_args is not None
    assert "nombre" in editar.await_args.kwargs["content"]


def test_el_recluta_sin_nombre_se_lista_sin_reventar_el_desplegable():
    """Discord rechaza una etiqueta vacía: sin esto el menú entero fallaría."""
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)

    menu = equipo.MenuPlantel([activa, recluta])
    texto = equipo.texto_del_plantel([activa, recluta])

    assert [opcion.label for opcion in menu.options] == ["Activa", sim.SIN_NOMBRE]
    assert sim.SIN_NOMBRE in texto
    assert "esperando nombre" in texto


def test_todas_las_rutas_de_ficha_viva_piden_las_seis_esperas(monkeypatch):
    viva = criatura(1, "Mia", True, None)
    esperas = Mock(return_value={})
    monkeypatch.setattr(db, "esperas_de_ficha", esperas)
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[viva]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(
        economia, "saldos", Mock(return_value=economia.Saldos(34, 0))
    )
    monkeypatch.setattr(pantalla, "render", Mock(return_value="ficha"))

    interaccion, _, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, viva, T0))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)

    esperas.reset_mock()
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), viva, T0))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)

    esperas.reset_mock()
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(db, "criatura_por_pantalla", Mock(return_value=viva))
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_cuidado",
        Mock(return_value=SimpleNamespace(criatura=viva, replay=False)),
    )
    interaccion, _, _ = interaccion_de()
    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)


def test_responder_y_publicar_pasan_el_saldo_de_la_persona_y_servidor(monkeypatch):
    viva = replace(
        criatura(1, "Mia", True, None),
        usuario_id="persona-correcta",
        guild_id="servidor-correcto",
    )
    saldos = Mock(return_value=economia.Saldos(asciicoins=34, asciigems=0))
    esperas = {sim.AVENTURA: timedelta(minutes=36)}
    render = Mock(return_value="ficha")
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(db, "esperas_de_ficha", Mock(return_value=esperas))
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[viva]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(pantalla, "render", render)

    interaccion, _, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, viva, T0))

    saldos.assert_called_once_with("persona-correcta", "servidor-correcto")
    assert render.call_args.kwargs["esperas"] == esperas
    assert render.call_args.kwargs["asciicoins"] == 34

    saldos.reset_mock()
    render.reset_mock()
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), viva, T0))

    saldos.assert_called_once_with("persona-correcta", "servidor-correcto")
    assert render.call_args.kwargs["esperas"] == esperas
    assert render.call_args.kwargs["asciicoins"] == 34


def test_responder_y_publicar_no_consultan_saldo_para_una_lapida(monkeypatch):
    lapida = replace(
        criatura(1, "Mia", False, None),
        nacida_en=T0,
        actualizada_en=T0,
        muerta_en=T0,
    )
    saldos = Mock(side_effect=AssertionError("una lápida no consulta saldo"))
    render = Mock(return_value="lápida")
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(db, "esperas_de_ficha", Mock(return_value={}))
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(db, "plantel", Mock(return_value=[]))
    monkeypatch.setattr(db, "guardar_pantalla", Mock())
    monkeypatch.setattr(pantalla, "render", render)

    interaccion, respuesta, _ = interaccion_de()
    interaccion.channel_id = "canal"
    interaccion.original_response = AsyncMock(
        return_value=SimpleNamespace(id="respuesta")
    )
    asyncio.run(vistas.responder_pantalla(interaccion, lapida, T0))

    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), lapida, T0))

    saldos.assert_not_called()
    respuesta.send_message.assert_awaited_once_with("lápida")
    canal.send.assert_awaited_once_with("lápida")
    assert [llamada.kwargs["asciicoins"] for llamada in render.call_args_list] == [
        None,
        None,
    ]


def test_actualizar_edita_la_ficha_viva_con_estado_y_controles_actuales(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.crear("u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False)
    economia.saldos("u1", "g1")
    with db.conectar() as con:
        con.execute(
            "UPDATE monederos SET asciicoins = 73 "
            "WHERE usuario_id = 'u1' AND guild_id = 'g1'"
        )
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(hours=6)
    db.poner_cooldown(criatura.id, sim.JUGAR, ahora - timedelta(minutes=1))
    db.poner_cooldown_persona(
        "u1", "g1", sim.AVENTURA, ahora - timedelta(minutes=1)
    )
    db.poner_efecto(criatura.id, "fuerza", 3, ahora - timedelta(minutes=1))
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    guardada = db.obtener(criatura.id)
    assert guardada is not None
    contenido = respuesta.edit_message.await_args.kwargs["content"]
    vista = respuesta.edit_message.await_args.kwargs["view"]
    esperado = pantalla.render(
        guardada,
        ahora,
        esperas=db.esperas_de_ficha(
            guardada, ahora, pantalla.ACCIONES_EN_FICHA
        ),
        efectos=db.efectos_activos(guardada.id, ahora),
        en_la_incubadora=1,
        asciicoins=73,
    )
    respuesta.edit_message.assert_awaited_once()
    assert contenido == esperado
    assert contenido.count(
        "-# 🪙 73 asciicoins · 🎒 Mochila para gastarlos"
    ) == 1
    assert contenido != pantalla.render(criatura, ahora)
    assert guardada.actualizada_en == ahora and guardada.hambre < criatura.hambre
    assert pantalla.ICONOS_ACCION[sim.JUGAR] in contenido
    assert pantalla.ICONOS_ACCION[sim.AVENTURA] in contenido
    assert pantalla.EMOJI_POCION in contenido
    assert pantalla.EMOJI_INCUBADORA in contenido
    assert isinstance(vista, vistas.PantallaView)
    assert all(not getattr(boton, "disabled") for boton in vista.children)
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


def test_actualizar_que_descubre_muerte_edita_la_misma_ficha_sin_botones(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(days=10)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    saldos = Mock(side_effect=AssertionError("una lápida no consulta saldo"))
    monkeypatch.setattr(economia, "saldos", saldos)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    guardada = db.obtener(criatura.id)
    assert guardada is not None and not guardada.viva
    respuesta.edit_message.assert_awaited_once_with(
        content=pantalla.render(guardada, ahora), view=None
    )
    saldos.assert_not_called()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


@pytest.mark.parametrize("caso", ["muerta-tras-ascenso", "sin-mapeo"])
def test_actualizar_ficha_obsoleta_no_muta_ni_edita(
    bd_temporal, monkeypatch, caso
):
    ahora = T0 + timedelta(days=10)
    if caso == "muerta-tras-ascenso":
        antigua = db.crear("u1", "g1", "pulpo", "Antigua", STATS, T0)
        reserva = db.crear(
            "u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False
        )
        db.guardar_pantalla(antigua.id, "ficha", "canal")
        db.guardar(sim.avanzar(antigua, ahora))
        ascendida = db.ascender_de_la_incubadora("u1", "g1", ahora)
        assert ascendida is not None and ascendida.id == reserva.id

    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    ejecutar_cuidado = Mock(return_value=None)
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas.economia, "ejecutar_cuidado", ejecutar_cuidado)
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    ejecutar_cuidado.assert_not_called()
    respuesta.send_message.assert_awaited_once_with(
        "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ephemeral=True,
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


@pytest.mark.parametrize(
    ("caso", "accion", "estado", "recibo"),
    [
        (
            "alimentar",
            sim.ALIMENTAR,
            {"hambre": 50.0, "animo": 70.0},
            "-# 🍖 Alimentar · comida 80 · ánimo 70 · +1 XP · "
            "🪙 +1 asciicoins · cuidado 1/12 UTC",
        ),
        (
            "empacho",
            sim.ALIMENTAR,
            {"hambre": 100.0, "animo": 5.0},
            "-# 🍖 Alimentar · comida 100 · ánimo 0 · +1 XP · "
            "🪙 +1 asciicoins · cuidado 1/12 UTC",
        ),
        (
            "jugar",
            sim.JUGAR,
            {"hambre": 80.0, "animo": 70.0},
            "-# 🪀 Jugar · ánimo 95 · velocidad +1 entrenamiento · +2 XP · "
            "coste base -5 comida · 🪙 +1 asciicoins · cuidado 1/12 UTC",
        ),
        (
            "entrenar",
            sim.ENTRENAR,
            {"hambre": 80.0, "animo": 70.0},
            "-# 🏋️ Entrenar · fuerza +2 entrenamiento · +3 XP · "
            "coste base -15 comida · coste base -10 ánimo · "
            "🪙 +1 asciicoins · cuidado 1/12 UTC",
        ),
        (
            "limpiar",
            sim.LIMPIAR,
            {"limpieza": 25.0},
            "-# 🧼 Limpiar · aseo 100 · +0 XP · "
            "🪙 +1 asciicoins · cuidado 1/12 UTC",
        ),
    ],
)
def test_cuidado_publica_resultado_real_y_recibo_unificado(
    bd_temporal, monkeypatch, caso, accion, estado, recibo
):
    criatura = replace(
        db.crear("u1", "g1", "pulpo", "Mia", STATS, T0), **estado
    )
    db.guardar(criatura)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)

    if caso == "empacho":
        ejecutar_cuidado = economia.ejecutar_cuidado

        def ejecutar_con_otra_narrativa(*args):
            resultado = ejecutar_cuidado(*args)
            assert resultado is not None
            return replace(
                resultado, mensaje="Narrativa sustituida sin palabra clave."
            )

        monkeypatch.setattr(
            vistas.economia, "ejecutar_cuidado", ejecutar_con_otra_narrativa
        )

    interaccion, _, _ = interaccion_de()
    asyncio.run(vistas._ejecutar(interaccion, accion))

    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert aviso.splitlines()[-1] == recibo
    if caso == "empacho":
        assert aviso.startswith("Narrativa sustituida sin palabra clave.\n")
        assert "salud +1" not in aviso


def test_cuidado_sin_efecto_responde_en_privado_sin_congelar_ni_publicar(
    bd_temporal, monkeypatch
):
    """Limpiar a quien ya está limpia no genera ficha: sólo el aviso privado."""
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.LIMPIAR))

    # El texto esperado sale del dominio, no de una copia literal aquí: el
    # estado no cambió, así que repetir la acción devuelve el mismo resultado.
    dominio = economia.ejecutar_cuidado("otro", "u1", "g1", sim.LIMPIAR, T0)
    assert dominio is not None and dominio.sin_efecto
    respuesta.send_message.assert_awaited_once_with(
        dominio.mensaje + "\n-# Sus vetas permanecen quietas.", ephemeral=True
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


def test_cuidado_con_tension_no_dice_que_no_deja_marca(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar(replace(criatura, hambre=40.0))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, _, _ = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ENTRENAR))

    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert "Algo se pone en movimiento bajo sus vetas." in aviso
    assert "permanecen quietas" not in aviso


def test_cuidado_con_ruptura_deja_el_eco_al_anuncio_existente(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar(replace(
        criatura, hambre=40.0,
        ten_fuerza=19.0, ten_velocidad=19.0, ten_salud=19.0,
    ))
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=T0))
    monkeypatch.setattr(vistas, "_congelar_pulsada", AsyncMock())
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, _, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ENTRENAR))

    canal.send.assert_awaited_once()
    assert "🪵" in canal.send.await_args.args[0]
    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert "movimiento bajo sus vetas" not in aviso
    assert "permanecen quietas" not in aviso


def test_cuidado_normal_congela_publica_y_replay_responde_privado(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(hours=6)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "_congelar_pulsada", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once_with(interaccion)
    publicar.assert_awaited_once()
    llamada = publicar.await_args
    assert llamada is not None
    assert llamada.args[0] is canal
    assert llamada.args[1].id == criatura.id
    assert llamada.args[2] == ahora
    assert "Sus vetas permanecen quietas." in llamada.kwargs["aviso"]
    respuesta.edit_message.assert_not_awaited()
    respuesta.send_message.assert_not_awaited()
    canal.send.assert_not_awaited()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once()
    publicar.assert_awaited_once()
    respuesta.send_message.assert_awaited_once_with(
        "Esta interacción ya estaba procesada.", ephemeral=True
    )


def test_el_menu_del_plantel_aguanta_el_plantel_lleno():
    """Lo único que podía romperse al subir el tope es la cantidad: Discord no
    admite más de 25 opciones en un desplegable ni 2000 caracteres de mensaje,
    y la lista lleva una línea por gachamon."""
    lleno = [
        criatura(i, f"Gachamon {i}", i == 1, f"ficha-{i}")
        for i in range(1, db.MAXIMO_PLANTEL + 1)
    ]

    menu = equipo.MenuPlantel(lleno)
    texto = equipo.texto_del_plantel(lleno)

    assert len(menu.options) == db.MAXIMO_PLANTEL <= 25
    assert all(1 <= len(o.label) <= 100 for o in menu.options)
    assert all(len(o.description) <= 100 for o in menu.options)
    assert len(texto) < 2000, len(texto)
    # Y sale uno por gachamon, no uno de menos.
    assert texto.count("Gachamon ") == db.MAXIMO_PLANTEL
