"""Smoke test de la capa de Discord: los cogs cargan y los comandos existen.

No se conecta a ninguna parte. Sirve para cazar lo que los tests de lógica no
ven: un decorador mal puesto, dos comandos con el mismo nombre, un custom_id
repetido o un import roto en un cog.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import discord
import pytest
from discord.ext import commands

import bot as modulo_bot
import competir as comp
import db
import simulacion as sim
from cogs import competencias
from vistas import (
    MenuSeleccionRivales,
    NombrarView,
    PantallaAnteriorView,
    PantallaView,
)

COMANDOS_ESPERADOS = {
    "huevo", "mascota", "carrera", "sumo", "totem", "ranking", "cementerio",
    "ayuda",
    "jardin", "aventura", "mochila", "tienda", "plantel", "logros",
    "casa", "visitar", "buzon",
}


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    """Para los tests de este fichero que sí consultan enfriamientos. No es
    `autouse` porque el resto son smoke tests que no tocan la base de datos."""
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def _cargar_todo():
    async def arrancar():
        cliente = commands.Bot(
            command_prefix="!", intents=discord.Intents.none(), help_command=None
        )
        for extension in modulo_bot.EXTENSIONES:
            await cliente.load_extension(extension)
        cliente.add_view(PantallaView())
        cliente.add_view(PantallaAnteriorView())
        cliente.add_view(NombrarView())
        comandos = list(cliente.tree.get_commands())
        # Descargar para que el bucle de muerte no quede suelto.
        for extension in reversed(modulo_bot.EXTENSIONES):
            await cliente.unload_extension(extension)
        return comandos

    return asyncio.run(arrancar())


def test_todos_los_cogs_cargan_y_registran_sus_comandos():
    assert {c.name for c in _cargar_todo()} == COMANDOS_ESPERADOS


def test_los_comandos_directos_se_anuncian_como_toca():
    """`/mochila`, `/tienda` y `/plantel` abren lo que hasta ahora sólo estaba
    bajo los botones de la ficha. La descripción es lo único que se ve al
    escribir «/» en Discord, así que si miente el comando no se encuentra."""
    esperadas = {
        "mochila": "Abre tu mochila y usa lo que lleves",
        "tienda": "Compra objetos, cosméticos y casas",
        "casa": "Mira tu hogar y a todos los que viven en él",
        "plantel": "Mira tu plantel y cambia de gachamon activo",
    }
    directos = {c.name: c.description for c in _cargar_todo() if c.name in esperadas}

    assert directos == esperadas


def test_ningun_comando_se_sale_de_su_canal(monkeypatch):
    """Todos llevan `solo_en_el_canal`, y se comprueba ejecutando el check en un
    canal ajeno en vez de mirar el decorador: así vale igual si algún día se
    escribe de otra forma.

    Se recorre el árbol ENTERO y no sólo los tres nuevos, para que al próximo
    comando tampoco se le olvide."""
    from types import SimpleNamespace

    import comun
    import config

    async def pasar_los_checks(comando, interaccion):
        for check in comando.checks:
            await check(interaccion)

    monkeypatch.setattr(config, "CANALES", [111])
    interaccion = SimpleNamespace(channel_id=222)
    comandos = _cargar_todo()
    assert comandos, "sin comandos el barrido no comprueba nada"

    sueltos = []
    for comando in comandos:
        try:
            asyncio.run(pasar_los_checks(comando, interaccion))
        except comun.CanalEquivocado:
            continue
        sueltos.append(comando.name)

    assert not sueltos, f"contestan en cualquier canal: {sueltos}"


def test_la_pantalla_persistente_tiene_la_estructura_aprobada():
    """Cuatro cuidados directos y dos selectores de ancho completo."""
    vista = PantallaView()
    assert vista.timeout is None
    assert len(vista.children) == 6

    botones = vista.children[:4]
    assert all(isinstance(hijo, discord.ui.Button) for hijo in botones)
    assert [hijo.label for hijo in botones] == [
        "Alimentar", "Jugar", "Entrenar", "Limpiar"
    ]
    assert [str(hijo.emoji) for hijo in botones] == ["🍖", "🎮", "🏋️", "🧼"]
    assert [hijo.row for hijo in botones] == [0, 0, 0, 0]

    social, gestion = vista.children[4:]
    assert isinstance(social, discord.ui.Select)
    assert social.row == 1
    assert social.placeholder == "⚔️ Desafiar a otros…"
    assert social.custom_id == "tama:desafiar"
    assert [(op.label, op.value) for op in social.options] == [
        ("Carrera", comp.CARRERA),
        ("Sumo", comp.SUMO),
        ("Asalto al Tótem", comp.TOTEM),
        ("Entrenar juntos", "entrenar_juntos"),
    ]
    assert not any(op.default for op in social.options)

    assert isinstance(gestion, discord.ui.Select)
    assert gestion.row == 2
    assert gestion.placeholder == "🎒 Más acciones…"
    assert gestion.custom_id == "tama:mas_acciones"
    assert [(op.label, op.value) for op in gestion.options] == [
        ("Actualizar", sim.ACTUALIZAR),
        ("Mochila", "inventario"),
        ("Tienda", "tienda"),
        ("Cambiar", "plantel"),
        ("Personalizar", "personalizar"),
    ]
    assert not any(op.default for op in gestion.options)

    ids = [hijo.custom_id for hijo in vista.children]
    assert all(i and i.startswith("tama:") for i in ids)
    assert len(set(ids)) == len(ids)


def test_los_componentes_caben_en_tres_filas_de_discord():
    hijos = PantallaView().children
    assert [hijo.row for hijo in hijos] == [0, 0, 0, 0, 1, 2]


def test_no_se_procesan_comandos_de_texto():
    """Regresión: con la mención como prefijo, `@Gachamon cómo estás` se
    interpretaba también como el comando «cómo» y llenaba el registro de
    CommandNotFound. El bot sólo tiene slash commands."""
    import inspect

    fuente = inspect.getsource(modulo_bot.Tamagotchi.on_message)
    assert "process_commands" not in fuente


def test_la_charla_sigue_recibiendo_mensajes():
    """El listener del cog va por `extra_events`, no por `Bot.on_message`, así
    que anular el procesado de comandos no lo desactiva."""
    async def comprobar():
        cliente = commands.Bot(
            command_prefix="!", intents=discord.Intents.none(), help_command=None
        )
        await cliente.load_extension("cogs.charla")
        # Hay que contar ANTES de descargar: `extra_events` guarda la lista y
        # `unload_extension` la vacía en el sitio.
        cuantos = len(cliente.extra_events.get("on_message", []))
        await cliente.unload_extension("cogs.charla")
        return cuantos

    assert asyncio.run(comprobar()) == 1


def test_la_charla_no_necesita_el_intent_privilegiado():
    """Se va por menciones justamente para no tener que activar Message
    Content: Discord entrega el texto de los mensajes que mencionan al bot
    aunque ese intent esté apagado."""
    import discord

    intents = discord.Intents.default()
    assert not intents.message_content
    assert intents.guild_messages  # hace falta para recibir el evento


def test_no_queda_ningun_comando_de_depuracion():
    """`/debug_tiempo` se quitó a propósito: manipulaba el reloj de la criatura
    y no debe volver a colarse en producción."""
    assert not any("debug" in comando.name for comando in _cargar_todo())


def test_el_boton_de_nombrar_tambien_es_persistente():
    """Entre salir del huevo y bautizarla puede reiniciarse el bot: el botón
    tiene que seguir respondiendo."""
    vista = NombrarView()
    assert vista.timeout is None
    assert len(vista.children) == 1
    assert vista.children[0].custom_id == "tama:nombrar"


def test_los_custom_id_no_chocan_entre_vistas():
    todos = [h.custom_id for h in PantallaView().children]
    todos += [h.custom_id for h in PantallaAnteriorView().children]
    todos += [h.custom_id for h in NombrarView().children]
    todos += [
        MenuSeleccionRivales(tipo).custom_id
        for tipo in (comp.CARRERA, comp.SUMO, comp.TOTEM)
    ]
    assert len(set(todos)) == len(todos)


def test_las_fichas_anteriores_conservan_sus_acciones_persistentes():
    vista = PantallaAnteriorView()
    assert vista.timeout is None
    assert [hijo.custom_id for hijo in vista.children] == [
        "tama:actualizar",
        "tama:inventario",
        "tama:tienda",
        "tama:plantel",
        "tama:personalizar",
        "tama:entrenar_juntos",
    ]


def test_la_vista_congelada_no_acepta_clics():
    for hijo in PantallaView(congelada=True).children:
        assert hijo.disabled
    for hijo in PantallaView().children:
        assert not hijo.disabled


# --- Concordancia de los mensajes de los cogs ------------------------------

def criatura_de_prueba(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="chispa", nombre="Juan III",
        nacida_en=datetime(2026, 1, 1, tzinfo=timezone.utc),
        actualizada_en=datetime(2026, 1, 1, tzinfo=timezone.utc),
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def test_mascota_ajena_viva_muestra_las_seis_esperas(monkeypatch, bd_temporal):
    from types import SimpleNamespace
    from typing import Any, cast
    from unittest.mock import AsyncMock, Mock

    import economia
    import pantalla
    from cogs import mascota as cog_mascota

    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    criatura = criatura_de_prueba(usuario_id="2", actualizada_en=ahora)
    esperas = Mock(return_value={
        accion: timedelta(minutes=1) for accion in pantalla.ACCIONES_EN_FICHA
    })
    saldos = Mock(return_value=economia.Saldos(asciicoins=34, asciigems=0))
    render = Mock(wraps=pantalla.render)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    monkeypatch.setattr(db, "criatura_activa", Mock(return_value=criatura))
    monkeypatch.setattr(db, "esperas_de_ficha", esperas)
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(pantalla, "render", render)

    respuesta = AsyncMock()
    interaccion = cast(discord.Interaction, SimpleNamespace(
        user=SimpleNamespace(id=1),
        guild_id="g1",
        response=SimpleNamespace(send_message=respuesta),
    ))
    rival = cast(discord.User, UsuarioFalso(2))
    cog = cog_mascota.Mascota.__new__(cog_mascota.Mascota)

    callback = cast(Any, cog_mascota.Mascota.mascota.callback)
    asyncio.run(callback(cog, interaccion, rival))

    # Se le pasa la criatura entera y no su id: la espera de aventura es de la
    # persona, y hacen falta su `usuario_id` y su `guild_id` para encontrarla.
    esperas.assert_called_once_with(
        criatura, ahora,
        (
            sim.ALIMENTAR, sim.JUGAR, sim.ENTRENAR,
            sim.LIMPIAR, sim.COMPETIR, sim.AVENTURA,
        ),
    )
    saldos.assert_called_once_with("2", "g1")
    assert render.call_args.kwargs["esperas"] == esperas.return_value
    assert render.call_args.kwargs["asciicoins"] == 34
    llamada = respuesta.await_args
    assert llamada is not None
    contenido = llamada.args[0]
    assert all(
        icono in contenido for icono in ("🍖", "🎮", "🏋️", "🧼", "🏁", "🧭")
    )
    assert "🪙 34 asciicoins" in contenido
    assert "view" not in llamada.kwargs


def test_mascota_ajena_que_muere_no_consulta_ni_muestra_saldo(monkeypatch, bd_temporal):
    from types import SimpleNamespace
    from typing import Any, cast
    from unittest.mock import AsyncMock, Mock

    import economia
    import pantalla
    from cogs import mascota as cog_mascota

    ahora = datetime(2026, 1, 2, tzinfo=timezone.utc)
    criatura = criatura_de_prueba(
        usuario_id="2",
        actualizada_en=ahora - timedelta(days=1),
        hambre=1.0,
    )
    saldos = Mock(side_effect=AssertionError("una lápida no consulta saldo"))
    guardar = Mock()
    render = Mock(wraps=pantalla.render)
    monkeypatch.setattr(db, "ahora_utc", Mock(return_value=ahora))
    monkeypatch.setattr(db, "criatura_activa", Mock(return_value=criatura))
    monkeypatch.setattr(db, "guardar", guardar)
    monkeypatch.setattr(db, "esperas_de_ficha", Mock(return_value={}))
    monkeypatch.setattr(db, "efectos_activos", Mock(return_value={}))
    monkeypatch.setattr(economia, "saldos", saldos)
    monkeypatch.setattr(pantalla, "render", render)

    respuesta = AsyncMock()
    interaccion = cast(discord.Interaction, SimpleNamespace(
        user=SimpleNamespace(id=1),
        guild_id="g1",
        response=SimpleNamespace(send_message=respuesta),
    ))
    rival = cast(discord.User, UsuarioFalso(2))
    cog = cog_mascota.Mascota.__new__(cog_mascota.Mascota)

    callback = cast(Any, cog_mascota.Mascota.mascota.callback)
    asyncio.run(callback(cog, interaccion, rival))

    saldos.assert_not_called()
    lapida = guardar.call_args.args[0]
    assert not lapida.viva
    assert render.call_args.args[0] == lapida
    assert render.call_args.kwargs["asciicoins"] is None
    llamada = respuesta.await_args
    assert llamada is not None
    contenido = llamada.args[0]
    assert "asciicoins" not in contenido


def test_el_aviso_de_hambre_para_competir_concuerda():
    """Vive en un cog, fuera del alcance del constructor de `ResultadoAccion`,
    así que lleva su propia llamada a `concordar` y hay que vigilarla."""
    import especies as esp
    from cogs.competencias import _problema_para_competir

    # Sin enfriamiento pendiente: así queda fijado que el hambre se avisa antes,
    # que es lo accionable de las dos cosas.
    el = _problema_para_competir(
        criatura_de_prueba(hambre=5.0), "felipe", timedelta(0))
    ella = _problema_para_competir(
        criatura_de_prueba(hambre=5.0, genero=esp.HEMBRA), "felipe", timedelta(0))

    assert "hambriento" in el and "{" not in el
    assert "hambrienta" in ella and "{" not in ella


# --- Competir frena a los dos ----------------------------------------------

def test_el_aviso_de_recuperacion_dice_cuanto_falta():
    from cogs.competencias import _problema_para_competir

    aviso = _problema_para_competir(
        criatura_de_prueba(), "felipe", timedelta(minutes=2))

    assert aviso is not None
    assert "Juan III" in aviso and "2 min" in aviso and "{" not in aviso


def test_el_enfriamiento_de_competir_frena_a_todos(bd_temporal):
    """Regresión: el enfriamiento se guardaba para las dos criaturas, pero sólo
    se comprobaba el de quien retaba. Quien aceptaba podía pelear recién salido
    de otra pelea, y por fuera parecía que no tenía enfriamiento ninguno.

    Con carreras de hasta cinco esto cuenta más: basta con que **uno cualquiera**
    del grupo esté recuperándose para que la carrera no salga."""
    import db
    from cogs.competencias import _problema_del_grupo

    ahora = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    criaturas = [
        db.crear(f"u{i}", "g1", "pulpo", f"C{i}", (15, 15, 15), ahora)
        for i in range(3)
    ]
    grupo = tuple((c, f"dueño de {c.nombre}") for c in criaturas)

    assert _problema_del_grupo(grupo, ahora) is None

    # El del último invitado cuenta igual que el de quien reta.
    db.poner_cooldown(criaturas[-1].id, sim.COMPETIR, ahora)
    problema = _problema_del_grupo(grupo, ahora)
    assert problema is not None and "C2" in problema

    # Y cuando caduca, los tres vuelven a poder.
    assert _problema_del_grupo(
        grupo, ahora + sim.COOLDOWNS[sim.COMPETIR]) is None


class UsuarioFalso:
    """Lo justo que le pide el cog a un `discord.User`."""

    def __init__(self, id, bot=False):
        self.id = id
        self.bot = bot
        self.display_name = f"u{id}"
        self.mention = f"<@{id}>"


def test_no_se_puede_invitar_al_mismo_dos_veces():
    """Con cuatro huecos es fácil repetir sin darse cuenta, y una carrera con la
    misma criatura dos veces no tiene sentido."""
    from cogs.competencias import _invitados_validos

    yo, ana, luis = UsuarioFalso(1), UsuarioFalso(2), UsuarioFalso(3)

    invitados, problema = _invitados_validos(yo, (ana, luis, None, None))
    assert problema is None
    assert [u.id for u in invitados] == [2, 3]

    assert _invitados_validos(yo, (ana, ana, None, None))[1] is not None
    assert _invitados_validos(yo, (ana, yo, None, None))[1] is not None
    assert _invitados_validos(yo, (ana, UsuarioFalso(9, bot=True), None, None))[1]
    assert _invitados_validos(yo, (None, None, None, None))[1] is not None


@pytest.mark.parametrize("desde_selector", [False, True])
def test_retar_mantiene_el_slash_y_permite_publicar_desde_selector(
    bd_temporal, monkeypatch, desde_selector
):
    """El selector sólo cambia dónde se publica; la autoridad sigue en `_retar`."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    ahora = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.crear("1", "g1", "pulpo", "Mia", (15, 15, 15), ahora)
    db.crear("2", "g1", "michi", "Lúa", (15, 15, 15), ahora)
    retador, rival = UsuarioFalso(1), UsuarioFalso(2)
    mensaje = SimpleNamespace(id="reto")
    canal = SimpleNamespace(send=AsyncMock(return_value=mensaje))
    respuesta = SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock())
    interaccion = SimpleNamespace(
        user=retador,
        guild_id="g1",
        response=respuesta,
        original_response=AsyncMock(return_value=mensaje),
        edit_original_response=AsyncMock(),
    )
    cog = competencias.Competencias(cast(commands.Bot, None))
    llamada = cog._retar(
        cast(discord.Interaction, interaccion),
        cast(tuple[discord.User | None, ...], (rival,)),
        comp.CARRERA,
        canal_publico=(
            cast(discord.abc.Messageable, canal) if desde_selector else None
        ),
    )

    asyncio.run(llamada)

    if desde_selector:
        respuesta.edit_message.assert_awaited_once_with(
            content="Publicando el reto en el canal…", view=None
        )
        canal.send.assert_awaited_once()
        interaccion.edit_original_response.assert_awaited_once_with(
            content="Reto publicado en el canal."
        )
        respuesta.send_message.assert_not_awaited()
        interaccion.original_response.assert_not_awaited()
        vista = canal.send.await_args.kwargs["view"]
    else:
        respuesta.send_message.assert_awaited_once()
        canal.send.assert_not_awaited()
        respuesta.edit_message.assert_not_awaited()
        interaccion.edit_original_response.assert_not_awaited()
        interaccion.original_response.assert_awaited_once()
        vista = respuesta.send_message.await_args.kwargs["view"]
    assert isinstance(vista, competencias.RetoView)
    assert vista.tipo == comp.CARRERA
    assert [usuario.id for usuario in vista.invitados] == [2]
    assert vista.mensaje is mensaje


def test_fallo_al_publicar_reto_cierra_el_selector_con_error_claro(
    bd_temporal, monkeypatch
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    ahora = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "ahora_utc", lambda: ahora)
    db.crear("1", "g1", "pulpo", "Mia", (15, 15, 15), ahora)
    db.crear("2", "g1", "michi", "Lúa", (15, 15, 15), ahora)
    error = discord.HTTPException(
        cast(Any, SimpleNamespace(status=500, reason="prueba")), "Discord cayó"
    )
    canal = SimpleNamespace(send=AsyncMock(side_effect=error))
    respuesta = SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock())
    interaccion = SimpleNamespace(
        user=UsuarioFalso(1),
        guild_id="g1",
        response=respuesta,
        edit_original_response=AsyncMock(),
    )
    cog = competencias.Competencias(cast(commands.Bot, None))

    asyncio.run(cog._retar(
        cast(discord.Interaction, interaccion),
        cast(tuple[discord.User | None, ...], (UsuarioFalso(2),)),
        comp.CARRERA,
        canal_publico=cast(discord.abc.Messageable, canal),
    ))

    respuesta.edit_message.assert_awaited_once_with(
        content="Publicando el reto en el canal…", view=None
    )
    interaccion.edit_original_response.assert_awaited_once_with(
        content="No pude publicar el reto en el canal. Inténtalo de nuevo."
    )


def test_error_al_retar_desde_selector_sigue_siendo_privado():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    respuesta = SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock())
    canal = SimpleNamespace(send=AsyncMock())
    interaccion = SimpleNamespace(
        user=UsuarioFalso(1), guild_id="g1", response=respuesta
    )
    cog = competencias.Competencias(cast(commands.Bot, None))

    asyncio.run(cog._retar(
        cast(discord.Interaction, interaccion),
        (),
        comp.CARRERA,
        canal_publico=cast(discord.abc.Messageable, canal),
    ))

    respuesta.send_message.assert_awaited_once_with(
        "Tienes que invitar a alguien.", ephemeral=True
    )
    respuesta.edit_message.assert_not_awaited()
    canal.send.assert_not_awaited()


def test_solo_se_republica_la_ficha_de_quien_cambia():
    """Una carrera de cinco publicaba cinco pantallas y eso llenaba el canal.
    Competir siempre gasta hambre y ánimo, así que eso no puede contar: sólo
    cuenta lo que se nota en la ficha, subir de nivel o evolucionar."""
    from dataclasses import replace

    from cogs.competencias import _ha_cambiado_la_ficha

    antes = criatura_de_prueba(hambre=80.0, animo=80.0, nivel=2, xp=10)

    gastada = replace(antes, hambre=70.0, animo=75.0, xp=14)
    assert not _ha_cambiado_la_ficha(antes, gastada), "sólo ha competido"

    subida = replace(antes, nivel=3, xp=0)
    assert _ha_cambiado_la_ficha(antes, subida)

    # Cambiar de etapa sin cambiar de número de nivel no pasa hoy, pero la regla
    # no debería depender de eso.
    evolucionada = replace(antes, nivel=antes.nivel, base_salud=99)
    assert antes.etapa == evolucionada.etapa
    assert not _ha_cambiado_la_ficha(antes, evolucionada)


def reto_de(cuantos_invitados, tipo="carrera"):
    from cogs.competencias import RetoView

    yo = UsuarioFalso(1)
    invitados = [UsuarioFalso(2 + i) for i in range(cuantos_invitados)]
    vista = RetoView(None, yo, invitados, tipo, "g1", "cabecera")
    return vista, yo, invitados


def test_si_una_baja_deja_al_sumo_en_tres_no_se_juega():
    """El sumo es de 2 o de 4, así que en un torneo la regla de «quien rechaza se
    cae» choca con los números: quedarían tres y no hay forma de emparejar.

    Sin esto, `enfrentar` levantaba un ValueError dentro del botón y el torneo se
    moría con un traceback en el registro y ningún mensaje en el canal."""
    vista, _, (ana, luis, sara) = reto_de(3, tipo="sumo")

    vista.dentro += [ana, luis]
    vista.fuera.append(sara)

    assert vista.pendientes == []
    assert len(vista.dentro) == 3
    assert not vista.pueden_competir()
    assert "2 o 4" in vista._cierre()


def test_un_torneo_al_que_faltan_dos_se_juega_como_un_sumo_normal():
    """Quedarse en dos sí vale: es un sumo de los de siempre."""
    vista, _, (ana, luis, sara) = reto_de(3, tipo="sumo")

    vista.dentro.append(ana)
    vista.fuera += [luis, sara]

    assert len(vista.dentro) == 2
    assert vista.pueden_competir()
    assert "vs" in vista._cierre()


def test_en_la_carrera_cualquier_numero_entre_dos_y_cinco_vale():
    for bajas in range(0, 3):
        vista, _, invitados = reto_de(4)
        vista.dentro += invitados[bajas:]
        vista.fuera += invitados[:bajas]
        assert vista.pueden_competir(), (bajas, len(vista.dentro))


def test_quien_rechaza_se_cae_pero_la_carrera_sigue():
    """La decisión de diseño: con hasta cuatro invitados, exigir el sí de todos
    dejaría que uno solo bloqueara la carrera. Se corre con quien haya aceptado
    mientras queden dos."""
    vista, yo, (ana, luis) = reto_de(2)

    assert [u.id for u in vista.pendientes] == [ana.id, luis.id]
    assert vista.dentro == [yo], "quien reta corre de oficio"

    vista.fuera.append(ana)
    vista.dentro.append(luis)

    assert vista.pendientes == []
    assert [u.id for u in vista.dentro] == [yo.id, luis.id]
    marcador = vista.marcador()
    assert "❌ u2" in marcador and "✅ u3" in marcador
    assert "vs" in vista._cierre()


def test_si_no_llegan_a_dos_no_hay_carrera():
    vista, _, (ana,) = reto_de(1)
    vista.fuera.append(ana)

    assert vista.pendientes == []
    assert len(vista.dentro) < 2
    assert "rechazado" in vista._cierre()


def test_el_id_del_mensaje_del_reto_es_la_clave_idempotente():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    vista, _, (ana,) = reto_de(1)
    vista.dentro.append(ana)
    vista.mensaje = SimpleNamespace(id=987654)
    vista.cog = SimpleNamespace(disputar=AsyncMock())

    asyncio.run(vista._arrancar(SimpleNamespace()))

    assert vista.cog.disputar.await_args.args[-1] == "987654"


# --- Lo que se manda tiene que caber ---------------------------------------

LARGO_MAXIMO_MENSAJE = 2000  # tope de `content` en la API de Discord


def test_cada_pagina_de_la_ayuda_cabe_en_un_mensaje():
    """Regresión: `/ayuda` había crecido hasta 2046 caracteres y Discord la
    rechazaba con un 400, así que el comando estaba roto sin que nadie lo notara.
    Por eso va repartida en páginas, y el tope aplica a **cada mensaje**.

    Se deja margen: los nombres de las personalidades y el del bot cambian, y
    apurar el tope hasta el último carácter lo volvería a romper al añadir algo.
    Si una página se queda sin sitio, la salida es partirla en otra más, no subir
    el margen.
    """
    from cogs.social import paginas_de_ayuda

    paginas = paginas_de_ayuda("Gachamon")
    assert len(paginas) >= 2
    for numero, pagina in enumerate(paginas, start=1):
        assert len(pagina) <= LARGO_MAXIMO_MENSAJE * 0.95, (
            f"la página {numero} mide {len(pagina)} caracteres y el tope de un "
            f"mensaje es {LARGO_MAXIMO_MENSAJE}"
        )


def test_la_ayuda_habla_de_lo_que_hay():
    """Que no se quede contando reglas viejas al repartirla en páginas.

    Se comprueban los números **sacados de las constantes**, no escritos aquí:
    si alguien cambia el tope del plantel o los premios, la ayuda tiene que
    seguirlos o este test lo caza. Ya pasó dos veces —la ayuda siguió diciendo
    «sólo puedes tener una viva a la vez» después del plantel de tres, y no
    mencionaba que las monedas se ganan jugando.
    """
    import competir as comp
    import economia as eco
    import objetos as obj
    from cogs.social import paginas_de_ayuda

    texto = "\n".join(paginas_de_ayuda("Gachamon"))
    esperados = (
        "/huevo", "/carrera", "/sumo", "/jardin", "/ranking", "/cementerio",
        "/aventura", "/mochila", "/tienda", "/plantel", "podio", "incubadora",
        *comp.FASES_CARRERA, *comp.FASES_SUMO,
        "puntos acumulados", "mejor de tres", "dos intercambios",
        str(comp.MAX_CORREDORES), str(db.MAXIMO_PLANTEL),
        obj.MONEDA_TIENDA, str(eco.TOPE_CUIDADOS), str(eco.PREMIO_EVOLUCION),
    )
    for esperado in esperados:
        assert esperado in texto, esperado
    assert "Se acuerda de la última conversación." in texto
    assert "hayáis" not in texto


def test_los_comandos_de_competencia_anuncian_sus_fases_y_regla():
    comandos = {
        c.name: c.description
        for c in _cargar_todo()
        if c.name in {"carrera", "sumo"}
    }
    assert "SALIDA, TERRENO y FONDO" in comandos["carrera"]
    assert "POSICIÓN, EMPUJE y AGUANTE" in comandos["sumo"]
    assert "mejor de tres" in comandos["sumo"]


def test_la_ayuda_condiciona_la_xp_de_aventura_a_volver_con_vida():
    from cogs.social import paginas_de_ayuda

    texto = "\n".join(paginas_de_ayuda("Gachamon"))
    assert f"+{sim.XP_AVENTURA} XP" in texto
    assert "si vuelve con vida" in texto.lower()


def test_la_ayuda_no_dice_que_solo_cabe_una():
    """Regresión concreta: al pasar al plantel de tres, la sección «Empezar» se
    quedó diciendo «Sólo puedes tener una viva a la vez». El código estaba bien
    y el texto mentía, que es el fallo que nadie ve hasta que alguien lo lee."""
    from cogs.social import paginas_de_ayuda

    texto = "\n".join(paginas_de_ayuda("Gachamon")).lower()
    for mentira in ("una viva a la vez", "una sola criatura", "sólo una criatura"):
        assert mentira not in texto, mentira


def test_la_ayuda_se_manda_en_varios_mensajes():
    """La primera va en la respuesta a la interacción y el resto de seguimiento:
    si alguien vuelve a juntarlas en una sola, Discord la rechazaría."""
    import cogs.social as social

    enviados = []

    class Respuesta:
        async def send_message(self, contenido, **kw):
            enviados.append(("respuesta", contenido, kw))

    class Seguimiento:
        async def send(self, contenido, **kw):
            enviados.append(("seguimiento", contenido, kw))

    class Interaccion:
        response = Respuesta()
        followup = Seguimiento()

        class client:
            class user:
                display_name = "Gachamon"

    cog = social.Social.__new__(social.Social)
    asyncio.run(social.Social.ayuda.callback(cog, Interaccion()))

    destinos = [d for d, _, _ in enviados]
    assert destinos[0] == "respuesta", "la primera va como respuesta a la interacción"
    assert set(destinos[1:]) == {"seguimiento"}, destinos
    assert len(destinos) == len(social.paginas_de_ayuda("Gachamon"))
    # Las dos en privado: si la segunda se colara pública, la ayuda de uno
    # aparecería en el canal de todos.
    assert all(kw.get("ephemeral") for _, _, kw in enviados), enviados
    assert [c for _, c, _ in enviados] == list(
        social.paginas_de_ayuda("Gachamon")
    )


def test_los_comandos_directos_abren_lo_mismo_que_los_botones(monkeypatch):
    """Cada uno delega en su adaptador de siempre, con los mismos ganchos que le
    pasa `vistas`: si `/mochila` se quedara sin `congelar`, beberse una poción
    dejaría viva la ficha anterior, y si `/plantel` se quedara sin `bautizar`,
    elegir a un recluta recién llegado no abriría el modal del nombre.

    Se comprueba la delegación y no lo que sale por pantalla: el texto, la vista
    y el efímero ya son cosa de `tienda` y `equipo`, y copiarlos aquí sólo sería
    una segunda versión que se queda vieja.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import cogs.social as social

    abrir_inventario = AsyncMock()
    abrir_tienda = AsyncMock()
    abrir_plantel = AsyncMock()
    monkeypatch.setattr(social.tienda, "abrir_inventario", abrir_inventario)
    monkeypatch.setattr(social.tienda, "abrir_tienda", abrir_tienda)
    monkeypatch.setattr(social.equipo, "abrir_plantel", abrir_plantel)

    cog = social.Social.__new__(social.Social)
    respuesta = AsyncMock()
    interaccion = SimpleNamespace(response=respuesta, followup=respuesta)

    asyncio.run(social.Social.mochila.callback(cog, interaccion))
    asyncio.run(social.Social.tienda_cmd.callback(cog, interaccion))
    asyncio.run(social.Social.plantel.callback(cog, interaccion))

    abrir_inventario.assert_awaited_once_with(interaccion, social.vistas.congelar)
    abrir_tienda.assert_awaited_once_with(interaccion)
    abrir_plantel.assert_awaited_once_with(
        interaccion,
        social.vistas.congelar,
        social.vistas.bautizar,
        social.vistas.publicar_pantalla,
    )
    # Quien contesta es el adaptador. Si además respondiera el comando, Discord
    # rechazaría la segunda respuesta de la misma interacción.
    assert respuesta.mock_calls == [], respuesta.mock_calls


@pytest.mark.parametrize(
    ("tipo", "espera"),
    ((comp.CARRERA, 1.6), (comp.SUMO, 1.6), (comp.TOTEM, 5.0)),
)
def test_cada_modalidad_mantiene_su_ritmo_de_animacion(
    monkeypatch, tipo, espera
):
    pausas = []

    class Mensaje:
        async def edit(self, **_):
            pass

    class Canal:
        async def send(self, _):
            return Mensaje()

    async def dormir(segundos):
        pausas.append(segundos)

    monkeypatch.setattr(competencias.asyncio, "sleep", dormir)
    cog = object.__new__(competencias.Competencias)
    canal = cast(discord.abc.Messageable, Canal())
    asyncio.run(cog._animar(canal, ["primero", "último"], tipo))

    # Una pausa antes de reemplazar el primero y otra antes del resumen.
    assert pausas == [espera, espera]


def test_mientras_falte_gente_se_sigue_esperando():
    vista, _, (ana, luis, sara) = reto_de(3)
    vista.dentro.append(ana)

    assert [u.id for u in vista.pendientes] == [luis.id, sara.id]
    marcador = vista.marcador()
    assert marcador.count("⌛") == 2 and marcador.count("✅") == 2


def literales_de(ruta) -> list[str]:
    """Las cadenas del fichero que son texto de verdad, sin docstrings.

    Se mira el árbol y no el fuente en crudo porque los comentarios y las
    docstrings citan a propósito las frases mal escritas, como ejemplo de lo que
    no debe volver a pasar. Un `in texto` daría falsos positivos justo ahí.
    """
    import ast
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docstrings = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = getattr(nodo, "body", None)
            if cuerpo and isinstance(cuerpo[0], ast.Expr) \
                    and isinstance(cuerpo[0].value, ast.Constant) \
                    and isinstance(cuerpo[0].value.value, str):
                docstrings.add(id(cuerpo[0].value))
    return [n.value for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def test_ningun_texto_lleva_ya_el_femenino_fijo():
    """Barrido del fuente. El constructor de `ResultadoAccion` cubre los avisos
    de las acciones, pero los cogs escriben texto a mano y ahí no hay nada que
    los cubra: esto vigila que no reaparezca un adjetivo clavado en femenino
    hablando de una criatura concreta."""
    import pathlib
    # Sólo frases sin sustantivo al lado. «una criatura hambrienta» no entra en
    # la lista: ahí el femenino concuerda con «criatura» y es correcto.
    sospechosas = ("encantada", "molida", "Como nueva", "mírala")
    raiz = pathlib.Path(__file__).parent.parent
    for ruta in raiz.glob("**/*.py"):
        if "tests" in ruta.parts or "venv" in ruta.parts:
            continue
        for literal in literales_de(ruta):
            for palabra in sospechosas:
                assert palabra not in literal, (ruta.name, palabra, literal)


# --- Ningún botón actúa sobre la ficha de otro -----------------------------

class RespuestaFalsa:
    """Anota lo que el botón habría contestado, sin hablar con Discord."""

    def __init__(self):
        self.avisos = []

    def is_done(self):
        return bool(self.avisos)

    async def send_message(self, contenido="", **kw):
        self.avisos.append(str(contenido))

    async def edit_message(self, content="", **kw):
        self.avisos.append(str(content))

    async def send_modal(self, modal):
        self.avisos.append(f"MODAL {type(modal).__name__}")


def interaccion_falsa(usuario_id: int, mensaje_id: int, guild_id: str):
    respuesta = RespuestaFalsa()
    return type("Interaccion", (), {
        "response": respuesta,
        "message": type("M", (), {"id": mensaje_id})(),
        "user": type("U", (), {"id": usuario_id, "mention": f"<@{usuario_id}>"})(),
        "guild_id": guild_id,
        "channel": None,
    })(), respuesta


def test_ningun_boton_actua_sobre_la_pantalla_de_otro(bd_temporal):
    """Regresión: Mochila, Tienda y Cambiar se añadieron sin la comprobación
    que sí tenían los cinco de cuidado, así que pulsarlos bajo la ficha de otra
    persona abría tus menús igual. No se filtraba nada —abren lo tuyo— pero
    actuabas sobre un gachamon que no era el que estabas viendo.

    Se recorre la vista ENTERA y no los tres de entonces, para que el próximo
    botón que se añada tampoco pueda olvidarse.
    """
    from vistas import PantallaView

    ahora = db.ahora_utc()
    db.crear("1", "g1", "pulpo", "Mia", (15, 15, 15), ahora)
    suya = db.crear("2", "g1", "pulpo", "Suya", (15, 15, 15), ahora)
    db.guardar_pantalla(suya.id, "555", "999")  # la ficha publicada es de «2»

    componentes = PantallaView().children + PantallaAnteriorView().children
    for componente in componentes:
        interaccion, respuesta = interaccion_falsa(1, 555, "g1")
        asyncio.run(componente.callback(interaccion))

        assert respuesta.avisos, f"{componente.custom_id} no contestó nada"
        assert any("<@2>" in aviso for aviso in respuesta.avisos), (
            f"{componente.custom_id} deja actuar sobre la ficha de otra persona: "
            f"contestó {respuesta.avisos}"
        )
