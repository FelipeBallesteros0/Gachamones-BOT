# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""Las mutaciones externas apagan la ficha viva que acaba de quedar obsoleta."""
import asyncio
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, call

import discord
import pytest

import competir as comp
import db
import economia
import equipo
import especies as esp
import pantalla
import retrato
import simulacion as sim
import vistas

# Un bicho SIN retrato dibujado. Estos tests miran la ficha de TEXTO; si la
# especie tuviera imagen, la ficha sería un embed y dejarían de comprobar lo
# suyo. Se busca en vez de fijarse para que dibujar más especies no los rompa.
SIN_RETRATO = next(
    c for c in esp.ESPECIES if c not in retrato.CON_ETAPAS_COMPLETAS
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def estilo_imagen(monkeypatch):
    monkeypatch.setattr(db, "estilo_de_ficha", lambda *_: "imagen")


def criatura(id_, nombre, activa, pantalla_msg_id) -> sim.Criatura:
    return sim.Criatura(
        id=id_, usuario_id="u1", guild_id="g1", especie=SIN_RETRATO,
        nombre=nombre,
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
        "-# 🏋️ Entrenar fuerza · fuerza +2 entrenamiento · +3 XP · "
        "coste base -15 comida · coste base -10 ánimo · "
        "🪙 +1 asciicoins · cuidado 1/12 UTC"
    )


def test_recibos_de_cuidado_redondean_los_stats_vivos():
    fraccionaria = replace(
        criatura(1, "Mia", True, "ficha"),
        hambre=89.5837,
        animo=99.9991,
        limpieza=42.4999,
    )
    resultado = economia.ResultadoCuidado(
        criatura=fraccionaria,
        mensaje="Ñam.",
        delta_asciicoins=1,
        usados=1,
        ent_salud_ganada=1,
    )

    recibos = {
        accion: vistas.texto_recibo_cuidado(resultado, accion)
        for accion in (sim.ALIMENTAR, sim.JUGAR, sim.ENTRENAR, sim.LIMPIAR)
    }
    assert recibos[sim.ALIMENTAR] == (
        "-# 🍖 Alimentar · comida 90 · ánimo 100 · salud +1 entrenamiento · "
        "+1 XP · 🪙 +1 asciicoins · cuidado 1/12 UTC"
    )
    assert recibos[sim.JUGAR] == (
        "-# 🪀 Jugar · ánimo 100 · velocidad +1 entrenamiento · +2 XP · "
        "coste base -5 comida · 🪙 +1 asciicoins · cuidado 1/12 UTC"
    )
    empacho = replace(resultado, ent_salud_ganada=0)
    assert "salud" not in vistas.texto_recibo_cuidado(empacho, sim.ALIMENTAR)

    decimal_vivo = re.compile(r"(?:comida|ánimo|aseo) -?\d+\.\d+")
    for recibo in recibos.values():
        assert not decimal_vivo.search(f"{recibo} · versión 1.2.3")


def test_recibo_de_cuidado_conserva_topes_y_recompensa_de_evolucion():
    base = criatura(1, "Mia", True, "ficha")
    evolucionada = replace(base, nivel=5)

    topada = economia.ResultadoCuidado(
        criatura=base,
        mensaje="Entrenamiento duro.",
        delta_asciicoins=0,
        usados=5,
        topada=True,
    )
    assert vistas.texto_recibo_cuidado(topada, sim.ENTRENAR).endswith(
        "🪙 +0 asciicoins (tope diario) · cuidado 5/12 UTC"
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
        "🪙 +0 asciicoins (tope diario) · cuidado 12/12 UTC · "
        "evolución +10 · 1/1 UTC"
    )


def test_abrir_entrenamiento_conjunto_filtra_y_captura_reservas_elegibles(
    bd_temporal, monkeypatch
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    elegible = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    db.crear("u1", "g1", "michi", "", STATS, T0, activa=False)
    muerta = db.crear(
        "u1", "g1", "michi", "Nube", STATS, T0, activa=False
    )
    db.guardar(replace(muerta, muerta_en=T0, causa_muerte="prueba"))
    db.guardar_pantalla(activa.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once()
    llamada = respuesta.send_message.await_args
    assert llamada is not None and llamada.kwargs["ephemeral"] is True
    vista = llamada.kwargs["view"]
    assert isinstance(vista, vistas.VistaEntrenamientoConjunto)
    menu = vista.children[0]
    assert isinstance(menu, vistas.MenuEntrenamientoConjunto)
    assert [(opcion.value, opcion.label) for opcion in menu.options] == [
        (str(elegible.id), "Lúa")
    ]
    assert menu.activo == (activa.id, "Mia")
    assert menu.reservas == {str(elegible.id): (elegible.id, "Lúa")}


def test_abrir_entrenamiento_conjunto_rechaza_ficha_caduca_o_sin_reservas(
    bd_temporal
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(activa.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de(mensaje_id="otra")

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once_with(
        "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ephemeral=True,
    )

    interaccion, respuesta, _ = interaccion_de()
    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))
    respuesta.send_message.assert_awaited_once_with(
        "No tienes ninguna reserva viva y con nombre para entrenar.",
        ephemeral=True,
    )


def test_menu_entrenamiento_conjunto_acusa_antes_de_publicar_y_anuncia_ambos(
    monkeypatch
):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    participantes = (
        sim.aplicar_entrenamiento_conjunto(activa),
        sim.aplicar_entrenamiento_conjunto(reserva),
    )
    resultado = economia.ResultadoEntrenamientoConjunto(
        participantes=participantes, delta_asciicoins=1, usados=1
    )
    eventos = []

    def ejecutar(*args):
        eventos.append(("economia", args))
        return resultado

    async def responder(**kwargs):
        eventos.append(("respuesta", kwargs))

    async def publicar(*args, **kwargs):
        eventos.append(("publicar", args, kwargs))

    async def anunciar(*args):
        eventos.append(("logro", args))

    monkeypatch.setattr(vistas.economia, "ejecutar_entrenamiento_conjunto", ejecutar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    monkeypatch.setattr(vistas.comun, "anunciar_logros", anunciar)
    monkeypatch.setattr(vistas.db, "ahora_utc", Mock(return_value=T0))
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha")
    menu._values = [str(reserva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        id="selector",
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert [evento[0] for evento in eventos] == [
        "economia",
        "respuesta",
        "publicar",
        "logro",
        "logro",
    ]
    llamada_economia = eventos[0][1]
    assert llamada_economia[:3] == ("selector", "u1", "g1")
    assert llamada_economia[3] == economia.SeleccionEntrenamientoConjunto(
        1, "Mia", 2, "Lúa"
    )
    assert llamada_economia[4] == T0
    respuesta = eventos[1][1]
    assert respuesta == {
        "content": "Entrenamiento conjunto completado.",
        "view": None,
    }
    publicacion = eventos[2]
    assert publicacion[1][:3] == (canal, participantes[0].criatura, T0)
    aviso = publicacion[2]["aviso"]
    assert "**Mia** + **Lúa**" in aviso
    assert "+2 XP · fuerza +1 entrenamiento · -10 comida · -5 ánimo" in aviso
    assert aviso.count("cuidado 1/12 UTC") == 1
    assert [evento[1][1].id for evento in eventos[3:]] == [1, 2]


def test_recibo_conjunto_separa_el_tope_monetario_del_contador_de_cuidado():
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    resultado = economia.ResultadoEntrenamientoConjunto(
        participantes=(
            sim.aplicar_entrenamiento_conjunto(activa),
            sim.aplicar_entrenamiento_conjunto(reserva),
        ),
        topada=True,
        usados=5,
    )

    recibo = vistas.texto_resultado_entrenamiento_conjunto(resultado)

    assert "🪙 +0 asciicoins (tope diario) · cuidado 5/12 UTC" in recibo
    assert "cuidado 5/12 UTC (tope)" not in recibo


@pytest.mark.parametrize(
    "resultado,texto",
    [
        (
            economia.ResultadoEntrenamientoConjunto(replay=True),
            "Esta interacción ya estaba procesada.",
        ),
        (
            economia.ResultadoEntrenamientoConjunto(problema="activo_caduco"),
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
        ),
        (
            economia.ResultadoEntrenamientoConjunto(problema="reserva_caduca"),
            "Ese compañero ya no está disponible. "
            "Abre «Entrenar fuerza juntos» otra vez.",
        ),
    ],
)
def test_menu_entrenamiento_conjunto_cierra_errores_sin_publicar(
    monkeypatch, resultado, texto
):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_entrenamiento_conjunto",
        Mock(return_value=resultado),
    )
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha")
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(content=texto, view=None)
    publicar.assert_not_awaited()


def test_menu_entrenamiento_conjunto_nombra_quien_tiene_el_cooldown(monkeypatch):
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    resultado = economia.ResultadoEntrenamientoConjunto(
        problema="cooldown", bloqueada=reserva, espera=timedelta(minutes=7)
    )
    monkeypatch.setattr(
        vistas.economia,
        "ejecutar_entrenamiento_conjunto",
        Mock(return_value=resultado),
    )
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha")
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Todavía no. Lúa puede volver a entrenar en 7 min.", view=None
    )


def test_menu_entrenamiento_conjunto_falla_cerrado_si_el_valor_no_fue_capturado():
    activa = criatura(1, "Mia", True, "ficha")
    reserva = criatura(2, "Lúa", False, None)
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha")
    menu._values = ["999"]
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Ese compañero ya no está disponible. "
        "Abre «Entrenar fuerza juntos» otra vez.",
        view=None,
    )


def interaccion_de_selector():
    mensaje = SimpleNamespace(id="ficha", edit=AsyncMock())
    return SimpleNamespace(
        user=SimpleNamespace(id="u1"),
        guild_id="g1",
        message=mensaje,
        response=SimpleNamespace(
            type=None, send_message=AsyncMock(), edit_message=AsyncMock()
        ),
        channel=SimpleNamespace(),
    )


@pytest.mark.parametrize(
    "valor,tipo",
    [
        (comp.CARRERA, comp.CARRERA),
        (comp.SUMO, comp.SUMO),
        (comp.TOTEM, comp.TOTEM),
    ],
)
def test_selector_social_abre_la_modalidad_elegida(monkeypatch, valor, tipo):
    abrir = AsyncMock()
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_seleccion_rivales", abrir)
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    selector._values = [valor]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    abrir.assert_awaited_once_with(interaccion, tipo)


@pytest.mark.parametrize(
    "custom_id,valor",
    [("tama:desafiar", comp.CARRERA), ("tama:mas_acciones", "tienda")],
)
def test_selectores_acusan_antes_de_restaurar_el_placeholder(
    monkeypatch, custom_id, valor
):
    acuse = asyncio.Event()
    edicion_empezo = asyncio.Event()
    liberar_edicion = asyncio.Event()

    async def responder(*args, **kwargs):
        interaccion.response.type = discord.InteractionResponseType.channel_message
        acuse.set()

    async def editar(**kwargs):
        edicion_empezo.set()
        await liberar_edicion.wait()

    helper = AsyncMock(side_effect=responder)
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_seleccion_rivales", helper)
    monkeypatch.setattr(vistas.tienda, "abrir_tienda", helper)
    interaccion = interaccion_de_selector()
    interaccion.message.edit.side_effect = editar
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == custom_id
    )
    selector._values = [valor]

    async def comprobar():
        tarea = asyncio.create_task(selector.callback(interaccion))
        await edicion_empezo.wait()
        acusado_antes = acuse.is_set()
        liberar_edicion.set()
        await tarea
        assert acusado_antes

    asyncio.run(comprobar())
    helper.assert_awaited_once()


def test_selector_no_reedita_si_el_helper_ya_actualizo_el_mensaje(monkeypatch):
    async def actualizar(*args):
        interaccion.response.type = discord.InteractionResponseType.message_update

    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "_ejecutar", AsyncMock(side_effect=actualizar))
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:mas_acciones"
    )
    selector._values = [sim.ACTUALIZAR]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_not_awaited()


def test_selector_social_conserva_entrenar_juntos(monkeypatch):
    abrir = AsyncMock()
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "abrir_entrenamiento_conjunto", abrir)
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    selector._values = ["entrenar_juntos"]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    abrir.assert_awaited_once_with(interaccion)


@pytest.mark.parametrize(
    "valor,helper,args",
    [
        (sim.ACTUALIZAR, "ejecutar", (sim.ACTUALIZAR,)),
        ("inventario", "inventario", (vistas.congelar,)),
        ("tienda", "tienda", ()),
        (
            "plantel",
            "plantel",
            (vistas.congelar, vistas.bautizar, vistas.publicar_pantalla),
        ),
        ("personalizar", "personalizar", (vistas.republicar_ficha,)),
    ],
)
def test_selector_de_gestion_delega_una_vez_al_helper_actual(
    monkeypatch, valor, helper, args
):
    helpers = {nombre: AsyncMock() for nombre in (
        "ejecutar", "inventario", "tienda", "plantel", "personalizar"
    )}
    monkeypatch.setattr(vistas, "_es_de_otro", AsyncMock(return_value=False))
    monkeypatch.setattr(vistas, "_ejecutar", helpers["ejecutar"])
    monkeypatch.setattr(vistas.tienda, "abrir_inventario", helpers["inventario"])
    monkeypatch.setattr(vistas.tienda, "abrir_tienda", helpers["tienda"])
    monkeypatch.setattr(vistas.equipo, "abrir_plantel", helpers["plantel"])
    monkeypatch.setattr(
        vistas.tienda, "abrir_personalizacion", helpers["personalizar"]
    )
    interaccion = interaccion_de_selector()
    selector = next(
        hijo
        for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:mas_acciones"
    )
    selector._values = [valor]

    asyncio.run(selector.callback(interaccion))

    interaccion.message.edit.assert_awaited_once_with(view=selector.view)
    helpers[helper].assert_awaited_once_with(interaccion, *args)
    assert sum(mock.await_count for mock in helpers.values()) == 1


@pytest.mark.parametrize(
    "tipo,maximo,copy",
    [
        (comp.CARRERA, 4, "entre 1 y 4 rivales"),
        (comp.SUMO, 3, "1 o 3 rivales"),
        (comp.TOTEM, 4, "entre 1 y 4 rivales"),
        (comp.LABERINTO, 4, "entre 1 y 4 rivales"),
    ],
)
def test_cada_modalidad_abre_seleccion_privada_con_sus_cantidades(
    tipo, maximo, copy
):
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(
        get_cog=Mock(return_value=SimpleNamespace(_retar=AsyncMock()))
    )

    asyncio.run(vistas.abrir_seleccion_rivales(interaccion, tipo))

    llamada = interaccion.response.send_message.await_args
    assert llamada is not None and llamada.kwargs["ephemeral"] is True
    assert copy in llamada.args[0]
    vista = llamada.kwargs["view"]
    assert isinstance(vista, vistas.VistaSeleccionRivales)
    selector = vista.children[0]
    assert isinstance(selector, discord.ui.UserSelect)
    assert selector.min_values == 1
    assert selector.max_values == maximo


def test_el_menu_social_ofrece_el_laberinto():
    """La opción tiene que existir y despachar por el camino genérico."""
    menu = next(
        hijo for hijo in vistas.PantallaView().children
        if hijo.custom_id == "tama:desafiar"
    )
    opciones = {opcion.value: opcion.label for opcion in menu.options}

    assert opciones[comp.LABERINTO] == "Laberinto de Ecos"
    assert comp.LABERINTO in comp.CUANTOS_CABEN
    assert vistas.MenuSeleccionRivales(comp.LABERINTO).max_values == 4


@pytest.mark.parametrize(
    "tipo", [comp.CARRERA, comp.SUMO, comp.TOTEM, comp.LABERINTO]
)
def test_seleccion_de_rivales_termina_en_el_seam_canonico(tipo):
    rivales = [SimpleNamespace(id="u2"), SimpleNamespace(id="u3")]
    retar = AsyncMock()
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(
        get_cog=Mock(return_value=SimpleNamespace(_retar=retar))
    )
    selector = vistas.MenuSeleccionRivales(tipo)
    selector._values = rivales

    asyncio.run(selector.callback(interaccion))

    retar.assert_awaited_once_with(
        interaccion, tuple(rivales), tipo, canal_publico=interaccion.channel
    )


def test_selector_de_rivales_reserva_una_sola_delegacion_con_dos_callbacks():
    rivales = [SimpleNamespace(id="u2")]
    entro_en_retar = asyncio.Event()
    liberar_retar = asyncio.Event()

    async def retar(*args, **kwargs):
        if not entro_en_retar.is_set():
            entro_en_retar.set()
            await liberar_retar.wait()

    delegado = AsyncMock(side_effect=retar)
    selector = vistas.MenuSeleccionRivales(comp.CARRERA)
    selector._values = rivales
    primera = interaccion_de_selector()
    segunda = interaccion_de_selector()
    cog = SimpleNamespace(_retar=delegado)
    primera.client = SimpleNamespace(get_cog=Mock(return_value=cog))
    segunda.client = SimpleNamespace(get_cog=Mock(return_value=cog))

    async def competir_dos_veces():
        tarea_primera = asyncio.create_task(selector.callback(primera))
        await entro_en_retar.wait()
        await selector.callback(segunda)
        liberar_retar.set()
        await tarea_primera

    asyncio.run(competir_dos_veces())

    delegado.assert_awaited_once_with(
        primera, tuple(rivales), comp.CARRERA, canal_publico=primera.channel
    )
    segunda.response.send_message.assert_awaited_once_with(
        "Este selector ya se usó. Abre `/mascota` para elegir rivales de nuevo.",
        ephemeral=True,
    )


def test_seleccion_temporal_solo_responde_a_quien_la_abrio():
    vista = vistas.VistaSeleccionRivales("u1", comp.CARRERA)
    interaccion = interaccion_de_selector()
    interaccion.user.id = "u2"

    permitido = asyncio.run(vista.interaction_check(interaccion))

    assert not permitido
    interaccion.response.send_message.assert_awaited_once_with(
        "Este selector de rivales no es tuyo.", ephemeral=True
    )


def test_cog_de_competencias_ausente_falla_sin_crash():
    interaccion = interaccion_de_selector()
    interaccion.client = SimpleNamespace(get_cog=Mock(return_value=None))

    asyncio.run(vistas.abrir_seleccion_rivales(interaccion, comp.CARRERA))

    interaccion.response.send_message.assert_awaited_once_with(
        "Las competencias no están disponibles en este momento.", ephemeral=True
    )

    selector = vistas.MenuSeleccionRivales(comp.CARRERA)
    selector._values = [SimpleNamespace(id="u2")]
    asyncio.run(selector.callback(interaccion))
    interaccion.response.edit_message.assert_awaited_once_with(
        content="Las competencias no están disponibles en este momento.", view=None
    )


def test_entrenamiento_conjunto_reutiliza_el_rechazo_de_ficha_ajena(bd_temporal):
    ajena = db.crear("u2", "g1", SIN_RETRATO, "Ajena", STATS, T0)
    db.guardar_pantalla(ajena.id, "ficha", "canal")
    interaccion, respuesta, _ = interaccion_de()

    asyncio.run(vistas.abrir_entrenamiento_conjunto(interaccion))

    respuesta.send_message.assert_awaited_once_with(
        "Ese es el gachamon de <@u2>. "
        "Saca el tuyo con `/mascota` o `/huevo`.",
        ephemeral=True,
    )


def test_fallo_de_publicacion_deja_commit_y_el_replay_no_republica(
    bd_temporal, monkeypatch
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    reserva = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    db.guardar_pantalla(activa.id, "ficha", "canal")
    monkeypatch.setattr(vistas.db, "ahora_utc", Mock(return_value=T0))
    publicar = AsyncMock(side_effect=RuntimeError("Discord cayó"))
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    monkeypatch.setattr(vistas.comun, "anunciar_logros", AsyncMock())
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha")
    menu._values = [str(reserva.id)]
    interaccion, respuesta, _ = interaccion_de(evento_id="selector")

    with pytest.raises(RuntimeError, match="Discord cayó"):
        asyncio.run(menu.callback(interaccion))

    activa_guardada = db.obtener(activa.id)
    reserva_guardada = db.obtener(reserva.id)
    assert activa_guardada is not None and reserva_guardada is not None
    assert activa_guardada.xp == reserva_guardada.xp == 2
    asyncio.run(menu.callback(interaccion))
    assert publicar.await_count == 1
    assert respuesta.edit_message.await_args_list == [
        call(content="Entrenamiento conjunto completado.", view=None),
        call(content="Esta interacción ya estaba procesada.", view=None),
    ]


def test_muerte_lazy_congela_ficha_activa_autoritativa_y_no_toca_reserva(
    bd_temporal, monkeypatch
):
    activa = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    reserva = db.crear(
        "u1", "g1", "michi", "Lúa", STATS, T0, activa=False
    )
    db.guardar(replace(activa, hambre=0.1))
    db.guardar_pantalla(activa.id, "ficha-b", "canal")
    monkeypatch.setattr(
        vistas.db, "ahora_utc", Mock(return_value=T0 + timedelta(hours=1))
    )
    congelar = AsyncMock()
    publicar = AsyncMock()
    monkeypatch.setattr(vistas, "congelar", congelar)
    monkeypatch.setattr(vistas, "publicar_pantalla", publicar)
    menu = vistas.MenuEntrenamientoConjunto(activa, [reserva], "ficha-a")
    menu._values = [str(reserva.id)]
    interaccion, respuesta, canal = interaccion_de(evento_id="selector")

    asyncio.run(menu.callback(interaccion))

    respuesta.edit_message.assert_awaited_once_with(
        content="Tu gachamon ya no está entre nosotros.", view=None
    )
    congelar.assert_awaited_once_with(canal, "ficha-b")
    canal.send.assert_awaited_once()
    publicar.assert_not_awaited()
    assert db.obtener(reserva.id) == reserva


def test_cambiar_activo_congela_responde_y_publica_en_ese_orden(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    nueva = criatura(2, "Nueva", True, "ficha-nueva")
    ahora = object()
    monkeypatch.setattr(
        equipo.db, "criatura_activa", Mock(side_effect=[anterior, nueva])
    )
    eventos = []

    def activar(*args):
        eventos.append(("activar", *args))
        return True

    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=ahora))

    async def responder(**_):
        eventos.append("respuesta")

    async def congelar(canal, mensaje_id):
        eventos.append(("congelar", canal, mensaje_id))

    async def publicar(canal, criatura_nueva, instante):
        eventos.append(("publicar", canal, criatura_nueva, instante))

    menu = equipo.MenuPlantel([anterior, nueva], congelar, None, publicar)
    menu._values = [str(nueva.id)]
    canal = SimpleNamespace()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=responder),
    )

    asyncio.run(menu.callback(interaccion))

    assert eventos == [
        ("activar", nueva.id, "u1", "g1", ahora),
        ("congelar", canal, "ficha-anterior"),
        "respuesta",
        ("publicar", canal, nueva, ahora),
    ]


def test_cambiar_al_mismo_activo_no_congela_ni_publica(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([anterior], congelar, publicar=publicar)
    menu._values = [str(anterior.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()
    publicar.assert_not_awaited()
    activar.assert_not_called()


def test_cambio_de_activo_invalido_no_congela_ni_publica(monkeypatch):
    anterior = criatura(1, "Anterior", True, "ficha-anterior")
    ajena = criatura(2, "Ajena", False, "ficha-ajena")
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=anterior))
    monkeypatch.setattr(equipo.db, "activar", Mock(return_value=False))
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    congelar = AsyncMock()
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([anterior, ajena], congelar, publicar=publicar)
    menu._values = [str(ajena.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(interaccion))

    congelar.assert_not_awaited()
    publicar.assert_not_awaited()


# --- La ficha vive en su canal, no en el que se escribe ----------------------

def canal_falso(id_, guild=None):
    mensaje = SimpleNamespace(edit=AsyncMock())
    return SimpleNamespace(
        id=id_, guild=guild, mensaje=mensaje,
        fetch_message=AsyncMock(return_value=mensaje),
        send=AsyncMock(return_value=SimpleNamespace(id=999)),
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
    menu = equipo.MenuPlantel(
        plantel, vistas.congelar, publicar=vistas.publicar_pantalla
    )
    menu._values = [str(elegido.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=canal,
        response=SimpleNamespace(edit_message=AsyncMock()),
    )
    return menu, interaccion


def test_congelar_va_al_canal_guardado_de_la_ficha_y_no_al_de_la_orden(bd_temporal):
    """Los menús sólo saben desde dónde se les abrió; la ficha sabe dónde está."""
    mia = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.guardar_pantalla(mia.id, "555", "111")
    guardado, actual = dos_canales("111", "222")

    asyncio.run(vistas.congelar(actual, "555"))

    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert guardado.mensaje.edit.await_args.kwargs["view"].children[0].disabled


def test_cambiar_de_activo_publica_ficha_canonica_en_el_canal_actual(
    bd_temporal, monkeypatch
):
    """La ficha vieja se congela donde estaba y la nueva nace donde se eligió."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    guardado, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id
    esperado = pantalla.render(
        activa,
        T0,
        esperas=db.esperas_de_ficha(activa, T0, pantalla.ACCIONES_EN_FICHA),
        efectos=db.efectos_activos(activa.id, T0),
        en_la_incubadora=1,
        asciicoins=economia.saldos("u1", "g1").asciicoins,
    )
    actual.send.assert_awaited_once()
    assert actual.send.await_args.kwargs["content"] == esperado
    vista = actual.send.await_args.kwargs["view"]
    assert isinstance(vista, vistas.PantallaView)
    assert all(not boton.disabled for boton in vista.children)
    guardado.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert guardado.mensaje.edit.await_args.kwargs["view"].children[0].disabled
    recargada = db.por_id(reserva.id)
    assert recargada is not None
    assert (recargada.pantalla_msg_id, recargada.canal_id) == ("999", "222")


def test_cambiar_activo_congela_la_ficha_vieja_de_la_que_regresa(
    bd_temporal, monkeypatch
):
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear(
        "u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, canal_id="111", activa=False
    )
    db.guardar_pantalla(reserva.id, "777", "111")
    guardado, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    assert guardado.fetch_message.await_args_list == [call(555), call(777)]
    assert guardado.mensaje.edit.await_count == 2
    assert all(
        llamada.kwargs["view"].children[0].disabled
        for llamada in guardado.mensaje.edit.await_args_list
    )
    actual.send.assert_awaited_once()
    assert all(
        not boton.disabled for boton in actual.send.await_args.kwargs["view"].children
    )


def test_cambiar_de_activo_congela_en_hilo_y_publica_en_canal_actual(
    bd_temporal, monkeypatch
):
    """Un hilo es un canal más donde jugar, y `get_channel` no lo encuentra."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    hilo, actual = dos_canales("111", "222", en_hilo=True)

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    hilo.fetch_message.assert_awaited_once_with(555)
    actual.fetch_message.assert_not_awaited()
    assert hilo.mensaje.edit.await_args.kwargs["view"].children[0].disabled
    actual.send.assert_awaited_once()
    recargada = db.por_id(reserva.id)
    assert recargada is not None and recargada.canal_id == "222"


def test_cambiar_de_activo_con_un_canal_guardado_ilegible_responde_igual(bd_temporal):
    """Una ficha vieja con un canal que no es un número no rompe el menú."""
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0)
    db.guardar_pantalla(anterior.id, "555", "canal-viejo")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    _, actual = dos_canales("111", "222")

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    asyncio.run(menu.callback(interaccion))

    actual.fetch_message.assert_awaited_once_with(555)
    interaccion.response.edit_message.assert_awaited_once()
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id


def test_si_el_canal_no_deja_publicar_el_cambio_sigue_hecho_y_acusado(
    bd_temporal, monkeypatch
):
    """Sin permiso para escribir queda el `/mascota` de la respuesta efímera."""
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock(return_value=T0))
    anterior = db.crear("u1", "g1", SIN_RETRATO, "Anterior", STATS, T0, canal_id="111")
    db.guardar_pantalla(anterior.id, "555", "111")
    reserva = db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
    guardado, actual = dos_canales("111", "222")
    actual.send = AsyncMock(side_effect=discord.HTTPException(
        SimpleNamespace(status=403, reason="Forbidden"), "Missing Permissions"
    ))

    menu, interaccion = menu_de_plantel([anterior, reserva], reserva, actual)
    with pytest.raises(discord.HTTPException):
        asyncio.run(menu.callback(interaccion))

    # Lo que se guardó y lo que se contestó pasó antes de intentar publicar: el
    # cambio está hecho, la ficha vieja congelada y la persona ya sabe volver.
    activa = db.criatura_activa("u1", "g1")
    assert activa is not None and activa.id == reserva.id
    guardado.fetch_message.assert_awaited_once_with(555)
    contenido = interaccion.response.edit_message.await_args.kwargs["content"]
    assert "/mascota" in contenido


# --- El recluta que todavía no tiene nombre ---------------------------------

def test_elegir_a_un_recluta_sin_nombre_abre_el_bautizo_sin_publicar(monkeypatch):
    """Elegirlo no es un error del que quejarse: es el momento de nombrarlo."""
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    bautizar = AsyncMock()
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock(), bautizar, publicar)
    menu._values = [str(recluta.id)]
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    asyncio.run(menu.callback(cast(Any, interaccion)))

    bautizar.assert_awaited_once_with(interaccion, recluta)
    publicar.assert_not_awaited()
    # Y no se activa: eso es justo lo que no puede pasar sin nombre.
    activar.assert_not_called()


def test_sin_bautizo_inyectado_se_explica_sin_activar_ni_publicar(monkeypatch):
    activa = criatura(1, "Activa", True, "ficha-activa")
    recluta = criatura(2, sim.NOMBRE_PENDIENTE, False, None)
    monkeypatch.setattr(equipo.db, "criatura_activa", Mock(return_value=activa))
    activar = Mock()
    monkeypatch.setattr(equipo.db, "activar", activar)
    monkeypatch.setattr(equipo.db, "ahora_utc", Mock())
    publicar = AsyncMock()
    menu = equipo.MenuPlantel([activa, recluta], AsyncMock(), publicar=publicar)
    menu._values = [str(recluta.id)]
    editar = AsyncMock()
    interaccion = SimpleNamespace(
        user=SimpleNamespace(id="u1"), guild_id="g1", channel=SimpleNamespace(),
        response=SimpleNamespace(edit_message=editar),
    )

    asyncio.run(menu.callback(cast(Any, interaccion)))

    activar.assert_not_called()
    publicar.assert_not_awaited()
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
    estilo = Mock(return_value="imagen")
    monkeypatch.setattr(db, "esperas_de_ficha", esperas)
    monkeypatch.setattr(db, "estilo_de_ficha", estilo)
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
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)

    esperas.reset_mock()
    estilo.reset_mock()
    canal = SimpleNamespace(
        id="canal",
        send=AsyncMock(return_value=SimpleNamespace(id="publicada")),
    )
    asyncio.run(vistas.publicar_pantalla(cast(Any, canal), viva, T0))
    esperas.assert_called_once_with(viva, T0, pantalla.ACCIONES_EN_FICHA)
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)

    esperas.reset_mock()
    estilo.reset_mock()
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
    estilo.assert_called_once_with(viva.usuario_id, viva.guild_id)


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
    respuesta.send_message.assert_awaited_once_with(content="lápida")
    canal.send.assert_awaited_once_with(content="lápida")
    assert [llamada.kwargs["asciicoins"] for llamada in render.call_args_list] == [
        None,
        None,
    ]


def test_actualizar_edita_la_ficha_viva_con_estado_y_controles_actuales(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
    db.crear("u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False)
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
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
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
        content=pantalla.render(guardada, ahora),
        attachments=[], embed=None, view=None,
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
        antigua = db.crear("u1", "g1", SIN_RETRATO, "Antigua", STATS, T0)
        reserva = db.crear(
            "u1", "g1", SIN_RETRATO, "Reserva", STATS, T0, activa=False
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
            "-# 🍖 Alimentar · comida 80 · ánimo 70 · salud +1 entrenamiento · "
            "+1 XP · 🪙 +1 asciicoins · cuidado 1/12 UTC",
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
            "-# 🏋️ Entrenar fuerza · fuerza +2 entrenamiento · +3 XP · "
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
        db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0), **estado
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
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
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
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
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


def test_el_eco_de_vetas_no_declara_quietud_si_cambio_ingenio():
    """La marca sale de comparar las tensiones **enumeradas** del dominio.

    Un esfuerzo que sólo toca el ingenio —lo único que emite el laberinto—
    tiene que contar como movimiento. Con una enumeración de tres canales la
    criatura se movería y las dos superficies dirían que está quieta.
    """
    antes = criatura(1, "Mia", True, "ficha")
    despues, rupturas = sim.aplicar_evento(
        antes, (sim.Esfuerzo("ingenio", 3.0, causa=sim.COMPETIR),), 0
    )
    marca = bool(rupturas or sim._tensiones(despues) != sim._tensiones(antes))
    assert despues.ten_ingenio > antes.ten_ingenio
    assert marca, "mover sólo el ingenio ya es mover las vetas"

    eco = vistas._eco_vetas_cuidado(economia.ResultadoCuidado(
        criatura=despues, mensaje="", rupturas=rupturas, marca=marca,
    ))
    assert eco == "-# Algo se pone en movimiento bajo sus vetas."
    assert "permanecen quietas" not in eco

    resumen = vistas._resumen_participante(sim.ResultadoAccion(
        criatura=despues, mensaje="", rupturas=rupturas, marca=marca,
    ))
    assert "vetas quietas" not in resumen


def test_cuidado_con_ruptura_deja_el_eco_al_anuncio_existente(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
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

    # La ruptura primero y la medalla de la alfa después, cada una en su
    # mensaje: el eco de las vetas no se mezcla con el anuncio del logro.
    mandados = [llamada.args[0] for llamada in canal.send.await_args_list]
    assert len(mandados) == 2
    assert "🪵" in mandados[0]
    assert "De la alfa" in mandados[1]
    llamada = publicar.await_args
    assert llamada is not None
    aviso = llamada.kwargs["aviso"]
    assert "movimiento bajo sus vetas" not in aviso
    assert "permanecen quietas" not in aviso


def test_cuidado_normal_congela_publica_y_replay_responde_privado(
    bd_temporal, monkeypatch
):
    criatura = db.crear("u1", "g1", SIN_RETRATO, "Mia", STATS, T0)
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
    # Lo único que se manda al canal aparte de la ficha es la medalla que se
    # lleva por haber nacido durante la alfa, y sale una sola vez.
    canal.send.assert_awaited_once()
    assert "De la alfa" in canal.send.await_args.args[0]

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

    # El 25 es el tope de opciones de un desplegable de Discord, y desde que
    # el plantel llegó a 25 este menú va **justo**, sin un hueco de margen:
    # subir `MAXIMO_PLANTEL` obliga antes a paginarlo. Va con literal para que
    # cambiar la constante no mueva también la portería.
    assert len(menu.options) == db.MAXIMO_PLANTEL
    assert db.MAXIMO_PLANTEL <= 25
    assert all(1 <= len(o.label) <= 100 for o in menu.options)
    assert all(len(o.description) <= 100 for o in menu.options)
    assert len(texto) < 2000, len(texto)
    # Y sale uno por gachamon, no uno de menos.
    assert texto.count("Gachamon ") == db.MAXIMO_PLANTEL
