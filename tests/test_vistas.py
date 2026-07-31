"""Las mutaciones externas apagan la ficha viva que acaba de quedar obsoleta."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
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


def criatura(id_, nombre, activa, pantalla_msg_id):
    return sim.Criatura(
        id=id_, usuario_id="u1", guild_id="g1", especie="pulpo", nombre=nombre,
        nacida_en=None, actualizada_en=None,
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
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
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
    monkeypatch.setattr(equipo.db, "activar", Mock())
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
    equipo.db.activar.assert_not_called()


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


def dos_canales(guardado_id, actual_id):
    """El canal donde quedó la ficha y aquel donde se abre el menú."""
    guardado = canal_falso(guardado_id)
    actual = canal_falso(
        actual_id,
        guild=SimpleNamespace(
            get_channel=lambda cid: guardado if str(cid) == guardado_id else None
        ),
    )
    return guardado, actual


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

    menu = equipo.MenuPlantel([anterior, reserva], vistas.congelar)
    menu._values = [str(reserva.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=actual,
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()


# --- El recluta que todavía no tiene nombre ---------------------------------

def test_elegir_a_un_recluta_sin_nombre_abre_el_bautizo(monkeypatch):
    """Elegirlo no es un error del que quejarse: es el momento de nombrarlo."""
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    monkeypatch.setattr(equipo.db, "activar", Mock())
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    bautizar = AsyncMock()
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock(), bautizar)
    menu._values = [str(recluta.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    bautizar.assert_awaited_once_with(interaccion, recluta)
    # Y no se activa: eso es justo lo que no puede pasar sin nombre.
    equipo.db.activar.assert_not_called()


def test_sin_bautizo_inyectado_se_explica_en_vez_de_activar(monkeypatch):
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    monkeypatch.setattr(equipo.db, "activar", Mock())
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock())
    menu._values = [str(recluta.id)]
    editar = AsyncMock()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=editar),
    )

    asyncio.run(menu.callback(interaccion))

    equipo.db.activar.assert_not_called()
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


def test_actualizar_edita_la_ficha_viva_con_estado_y_controles_actuales(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", "pulpo", "Mia", STATS, T0)
    db.crear("u1", "g1", "pulpo", "Reserva", STATS, T0, activa=False)
    db.guardar_pantalla(criatura.id, "ficha", "canal")
    ahora = T0 + timedelta(hours=6)
    db.poner_cooldown(criatura.id, sim.JUGAR, ahora - timedelta(minutes=1))
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
        esperas=db.esperas(guardada.id, ahora),
        efectos=db.efectos_activos(guardada.id, ahora),
        en_la_incubadora=1,
    )
    respuesta.edit_message.assert_awaited_once()
    assert contenido == esperado
    assert contenido != pantalla.render(criatura, ahora)
    assert guardada.actualizada_en == ahora and guardada.hambre < criatura.hambre
    assert pantalla.ICONOS_ACCION[sim.JUGAR] in contenido
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
    interaccion, respuesta, canal = interaccion_de()

    asyncio.run(vistas._ejecutar(interaccion, sim.ACTUALIZAR))

    guardada = db.obtener(criatura.id)
    assert guardada is not None and not guardada.viva
    respuesta.edit_message.assert_awaited_once_with(
        content=pantalla.render(guardada, ahora), view=None
    )
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
            "-# 🧼 Limpiar · limpieza 100 · +0 XP · "
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
        dominio.mensaje, ephemeral=True
    )
    respuesta.edit_message.assert_not_awaited()
    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    canal.send.assert_not_awaited()


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
    respuesta.edit_message.assert_not_awaited()
    respuesta.send_message.assert_not_awaited()
    canal.send.assert_not_awaited()

    asyncio.run(vistas._ejecutar(interaccion, sim.ALIMENTAR))

    congelar.assert_awaited_once()
    publicar.assert_awaited_once()
    respuesta.send_message.assert_awaited_once_with(
        "Esta interacción ya estaba procesada.", ephemeral=True
    )
