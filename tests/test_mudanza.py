"""El bot de la mudanza: el juego de Discord está en pausa.

El bot queda encendido sólo para `/vincular` y para contestar a todo lo demás
que Gachamon se mudó a la página: los botones y menús de los mensajes viejos,
mencionarlo y los dos comandos que la gente escribe de memoria. Y el manual del
canal queda en una sola página.

Ningún test habla con Discord: las interacciones, los canales y los mensajes
son de mentira, y la base es temporal.
"""
import asyncio
import importlib.util
import inspect
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from discord.ext import commands

import bot
import comun
import config
import db
import economia
import personalidad as per
import simulacion as sim
from cogs import mudanza

RAIZ = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
CANAL_DE_JUEGO = 4141
CANAL_DE_INFO = 4242
# El usuario del bot, el que tienen que mencionar para que conteste.
YO = SimpleNamespace(id=1, bot=True, display_name="Gachamon")


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    """Una base temporal con un gachamon dentro: si algo escribiera, se vería."""
    monkeypatch.setattr(db, "RUTA", tmp_path / "mudanza.db")
    db.inicializar()
    db.crear("555", str(config.GUILD_WEB), "pulpo", "Mia", (15, 15, 15, 15), T0)


@pytest.fixture
def cog():
    return mudanza.Mudanza(SimpleNamespace(user=YO, get_channel=lambda _: None))


def correr(corrutina):
    return asyncio.run(corrutina)


def volcado():
    """La base entera, tabla por tabla: cualquier escritura la cambia."""
    with db.conectar() as con:
        return list(con.iterdump())


def interaccion_falsa(
    guild_id=None,
    tipo=discord.InteractionType.application_command,
    custom_id=None,
    contestada=False,
):
    """Lo que el cog mira de una interacción, con una respuesta que lo apunta."""
    return SimpleNamespace(
        type=tipo,
        guild_id=guild_id,
        channel_id=CANAL_DE_JUEGO,
        user=SimpleNamespace(id=555),
        data={"custom_id": custom_id} if custom_id else {},
        response=SimpleNamespace(
            is_done=Mock(return_value=contestada),
            send_message=AsyncMock(),
        ),
    )


def mensaje_falso(canal=CANAL_DE_JUEGO, menciona=True, de_un_bot=False):
    return SimpleNamespace(
        author=SimpleNamespace(id=555, bot=de_un_bot),
        guild=SimpleNamespace(id=config.GUILD_WEB),
        channel=SimpleNamespace(id=canal),
        mentions=[YO] if menciona else [],
        reply=AsyncMock(),
    )


class _RespuestaFalsa:
    """Lo mínimo que una excepción de discord.py mira de una respuesta HTTP."""

    status = 404
    reason = "Not Found"


class MensajeFalso:
    def __init__(self, canal, id_, contenido):
        self.canal = canal
        self.id = id_
        self.content = contenido
        self.fallo = None   # lo que levanta `delete()`, si algo

    async def edit(self, content):
        self.canal.editados.append((self.id, content))
        self.content = content

    async def delete(self):
        if self.fallo is not None:
            raise self.fallo
        self.canal.borrados.append(self.id)
        del self.canal.mensajes[self.id]


class CanalFalso:
    """Un canal de Discord de mentira, que apunta todo lo que le hacen.

    Vive en un servidor (`guild`), que por defecto es el de la página y sólo
    conoce los canales de `canales_del_servidor`.
    """

    # Compartido entre canales, como los ids de Discord.
    _siguiente = 1000

    def __init__(self, id_=CANAL_DE_INFO, fallo=None, guild_id=None,
                 canales_del_servidor=()):
        self.id = id_
        self.name = "gachamon-info"
        self.guild = SimpleNamespace(
            id=config.GUILD_WEB if guild_id is None else guild_id,
            get_channel=lambda cid: (
                SimpleNamespace(id=cid) if cid in canales_del_servidor else None
            ),
        )
        self.fallo = fallo
        self.mensajes: dict[int, MensajeFalso] = {}
        self.consultados: list[int] = []
        self.publicados: list[str] = []
        self.editados: list[tuple[int, str]] = []
        self.borrados: list[int] = []

    def ya_tenia(self, contenido):
        """Un mensaje que ya estaba en el canal, sin contarlo como publicado."""
        CanalFalso._siguiente += 1
        mensaje = MensajeFalso(self, CanalFalso._siguiente, contenido)
        self.mensajes[mensaje.id] = mensaje
        return mensaje

    async def send(self, contenido):
        if self.fallo is not None:
            raise self.fallo
        mensaje = self.ya_tenia(contenido)
        self.publicados.append(contenido)
        return mensaje

    async def fetch_message(self, id_):
        self.consultados.append(id_)
        if id_ not in self.mensajes:
            raise discord.NotFound(_RespuestaFalsa(), "no está")
        return self.mensajes[id_]


def con_el_manual_de_ocho_paginas(canal):
    """El canal de info de hoy: las ocho páginas del manual viejo, apuntadas."""
    ids = []
    for indice in range(8):
        mensaje = canal.ya_tenia(f"## Página {indice}\ntexto viejo")
        db.guardar_publicacion(str(canal.id), indice, str(mensaje.id))
        ids.append(mensaje.id)
    return ids


def cog_con_info(monkeypatch, *canales):
    """El cog con esos canales de información configurados y a la vista."""
    monkeypatch.setattr(config, "CANALES_INFO", tuple(c.id for c in canales))
    visibles = {c.id: c for c in canales}
    return mudanza.Mudanza(SimpleNamespace(user=YO, get_channel=visibles.get))


# --- Lo que queda del bot ---------------------------------------------------

def test_el_bot_solo_carga_la_mudanza():
    assert bot.EXTENSIONES == ("cogs.mudanza",)


def test_el_aviso_dice_donde_y_como():
    for texto in (mudanza.AVISO, mudanza.pagina_del_manual((CANAL_DE_JUEGO,))):
        assert config.URL_DE_LA_PAGINA in texto and "`/vincular`" in texto
        assert "«Ya jugaba en Discord»" in texto and len(texto) < 2000
    assert config.URL_DE_LA_PAGINA not in mudanza.AVISO_SIN_PAGINA


def arrancar_el_bot(monkeypatch, sync=None):
    """El `setup_hook` de verdad y sin red: las extensiones no se cargan y el
    árbol de comandos no habla con Discord."""
    async def arrancar():
        cliente = bot.Tamagotchi()
        monkeypatch.setattr(cliente, "load_extension", AsyncMock())
        monkeypatch.setattr(cliente.tree, "sync", sync or AsyncMock(return_value=[]))
        monkeypatch.setattr(cliente.tree, "copy_global_to", Mock())
        monkeypatch.setattr(cliente, "add_view", Mock())
        monkeypatch.setattr(cliente, "add_dynamic_items", Mock())
        await cliente.setup_hook()
        return cliente

    return correr(arrancar())


def test_el_arranque_no_registra_vistas_ni_botones_del_juego(monkeypatch):
    """Con el `setup_hook` de verdad y sin red: se pone al día la base, se carga
    sólo la mudanza y ningún botón ni menú del juego queda escuchando."""
    monkeypatch.setattr(config, "GUILDS", ())
    poner_al_dia = Mock(wraps=economia.poner_al_dia)
    monkeypatch.setattr(economia, "poner_al_dia", poner_al_dia)

    cliente = arrancar_el_bot(monkeypatch)

    poner_al_dia.assert_called_once()
    assert [c.args for c in cliente.load_extension.await_args_list] == [
        ("cogs.mudanza",)
    ]
    cliente.add_view.assert_not_called()
    cliente.add_dynamic_items.assert_not_called()
    assert cliente.tree.on_error is comun.manejar_error


def _servidores_sincronizados(cliente):
    return [c.kwargs["guild"].id for c in cliente.tree.sync.await_args_list]


def test_el_arranque_sincroniza_una_vez_en_cada_servidor(monkeypatch):
    monkeypatch.setattr(config, "GUILDS", (71, 72))

    cliente = arrancar_el_bot(monkeypatch)

    assert _servidores_sincronizados(cliente) == [71, 72]


def test_un_servidor_que_no_deja_sincronizar_no_frena_a_los_demas(monkeypatch, caplog):
    """Un id equivocado o un servidor sin invitar dan 403: el siguiente se
    sincroniza igual y el registro dice cuál falló."""
    monkeypatch.setattr(config, "GUILDS", (71, 72))
    sync = AsyncMock(side_effect=[discord.Forbidden(_RespuestaFalsa(), "sin permiso"), []])

    with caplog.at_level(logging.WARNING):
        cliente = arrancar_el_bot(monkeypatch, sync=sync)   # no lanza

    assert _servidores_sincronizados(cliente) == [71, 72]
    assert any(
        r.name == "gachamones" and r.levelno == logging.WARNING and "71" in r.getMessage()
        for r in caplog.records
    )


# La descripción es lo único que se ve al escribir «/» en Discord, así que
# también se fija.
COMANDOS_ESPERADOS = {
    "vincular": "Une tu cuenta de Rowino con tus gachamones de aquí",
    "mascota": "Gachamon se mudó a la página",
    "huevo": "Gachamon se mudó a la página",
}


def _cargar_todo():
    """Las extensiones del bot, cargadas de verdad por discord.py y sin red."""
    async def arrancar():
        cliente = commands.Bot(
            command_prefix="!", intents=discord.Intents.none(), help_command=None
        )
        for extension in bot.EXTENSIONES:
            await cliente.load_extension(extension)
        comandos = list(cliente.tree.get_commands())
        # Descargar, como al apagar el bot, para que no quede nada suelto.
        for extension in reversed(bot.EXTENSIONES):
            await cliente.unload_extension(extension)
        return comandos

    return correr(arrancar())


def test_el_unico_cog_carga_y_registra_sus_tres_comandos():
    comandos = _cargar_todo()
    assert len(comandos) == len(COMANDOS_ESPERADOS) == 3
    assert {c.name: c.description for c in comandos} == COMANDOS_ESPERADOS


def test_ningun_comando_se_sale_de_su_canal(monkeypatch):
    """Todos llevan `solo_en_el_canal`, y se comprueba ejecutando el check en un
    canal ajeno en vez de mirar el decorador: así vale igual si algún día se
    escribe de otra forma.

    Se recorre el árbol ENTERO, para que al próximo comando tampoco se le
    olvide. Y se comprueba también la otra mitad: en su propio canal el check
    deja pasar, o el bot rechazaría hasta `/vincular` donde toca."""
    async def pasar_los_checks(comando, interaccion):
        return [await check(interaccion) for check in comando.checks]

    monkeypatch.setattr(config, "CANALES", [111])
    ajeno = SimpleNamespace(channel_id=222)
    suyo = SimpleNamespace(channel_id=111)
    comandos = _cargar_todo()
    assert comandos, "sin comandos el barrido no comprueba nada"

    sueltos = []
    for comando in comandos:
        try:
            correr(pasar_los_checks(comando, ajeno))
        except comun.CanalEquivocado:
            continue
        sueltos.append(comando.name)

    assert not sueltos, f"contestan en cualquier canal: {sueltos}"

    for comando in comandos:
        resultados = correr(pasar_los_checks(comando, suyo))   # no lanza
        assert resultados and all(r is True for r in resultados), comando.name


def test_no_se_procesan_comandos_de_texto():
    """Regresión: con la mención como prefijo, `@Gachamon cómo estás` se
    interpretaba también como el comando «cómo» y llenaba el registro de
    CommandNotFound. El bot sólo tiene slash commands."""
    fuente = inspect.getsource(bot.Tamagotchi.on_message)
    assert "process_commands" not in fuente


def test_la_mudanza_sigue_recibiendo_mensajes():
    """El listener del cog va por `extra_events`, no por `Bot.on_message`, así
    que anular el procesado de comandos no le quita las menciones."""
    async def comprobar():
        cliente = commands.Bot(
            command_prefix="!", intents=discord.Intents.none(), help_command=None
        )
        await cliente.load_extension("cogs.mudanza")
        # Hay que contar ANTES de descargar: `extra_events` guarda la lista y
        # `unload_extension` la vacía en el sitio.
        cuantos = len(cliente.extra_events.get("on_message", []))
        await cliente.unload_extension("cogs.mudanza")
        return cuantos

    assert correr(comprobar()) == 1


# --- Todo lo demás contesta que el juego se mudó ----------------------------

@pytest.mark.parametrize("comando", ["mascota", "huevo"])
def test_los_comandos_de_memoria_avisan_y_no_tocan_nada(cog, comando):
    antes = volcado()
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB)
    asyncio.run(getattr(cog, comando).callback(cog, interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO, ephemeral=True)
    assert volcado() == antes


@pytest.mark.parametrize("custom_id", [
    "tama:alimentar", "tama:plantel", "tama:nombrar", "tama:nombrar_recluta",
    "tama:nombrar_recluta:7", "tama:entrenar_juntos:reserva", "otra-cosa",
])
@pytest.mark.parametrize("tipo", [discord.InteractionType.component, discord.InteractionType.modal_submit])
def test_lo_viejo_contesta_el_aviso_y_no_toca_nada(cog, custom_id, tipo):
    antes = volcado()
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB, tipo=tipo, custom_id=custom_id)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO, ephemeral=True)
    assert volcado() == antes


def test_un_comando_de_barra_no_pasa_por_el_aviso(cog):
    interaccion = interaccion_falsa(tipo=discord.InteractionType.application_command)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_not_awaited()


def test_lo_ya_contestado_no_se_contesta_otra_vez(cog):
    interaccion = interaccion_falsa(tipo=discord.InteractionType.component, contestada=True)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_not_awaited()


def test_en_otro_servidor_el_aviso_no_promete_pagina(cog):
    interaccion = interaccion_falsa(guild_id=config.GUILD_WEB + 1, tipo=discord.InteractionType.component)
    asyncio.run(cog.on_interaction(interaccion))
    interaccion.response.send_message.assert_awaited_once_with(mudanza.AVISO_SIN_PAGINA, ephemeral=True)


def test_un_aviso_que_ya_no_se_puede_mandar_no_revienta(cog, caplog):
    """Un botón pulsado hace rato: la interacción caducó y Discord rechaza la
    respuesta. Eso no puede tumbar nada; queda en el registro y ya."""
    interaccion = interaccion_falsa(
        guild_id=config.GUILD_WEB, tipo=discord.InteractionType.component
    )
    interaccion.response.send_message.side_effect = discord.HTTPException(
        _RespuestaFalsa(), "caducada"
    )

    with caplog.at_level("WARNING"):
        correr(cog.on_interaction(interaccion))   # no lanza

    assert any(r.name == "cogs.mudanza" for r in caplog.records)


def test_mencionar_al_bot_en_su_canal_contesta_el_aviso(cog, monkeypatch):
    monkeypatch.setattr(config, "CANALES", (CANAL_DE_JUEGO,))
    antes = volcado()
    mensaje = mensaje_falso()

    correr(cog.on_message(mensaje))

    mensaje.reply.assert_awaited_once_with(mudanza.AVISO, mention_author=False)
    assert volcado() == antes


@pytest.mark.parametrize("mensaje", [
    mensaje_falso(canal=CANAL_DE_JUEGO + 1),
    mensaje_falso(menciona=False),
    mensaje_falso(de_un_bot=True),
], ids=["fuera-de-su-canal", "sin-mencion", "de-un-bot"])
def test_fuera_de_su_canal_o_sin_mencion_o_un_bot_no_contesta(cog, monkeypatch, mensaje):
    monkeypatch.setattr(config, "CANALES", (CANAL_DE_JUEGO,))

    correr(cog.on_message(mensaje))

    mensaje.reply.assert_not_awaited()


def test_si_no_puede_contestar_una_mencion_no_revienta(cog, monkeypatch, caplog):
    """Sin permiso para escribir en ese canal, por ejemplo: queda en el
    registro y ya, como con los botones."""
    monkeypatch.setattr(config, "CANALES", (CANAL_DE_JUEGO,))
    mensaje = mensaje_falso()
    mensaje.reply.side_effect = discord.HTTPException(_RespuestaFalsa(), "sin permiso")

    with caplog.at_level("WARNING"):
        correr(cog.on_message(mensaje))   # no lanza

    assert any(r.name == "cogs.mudanza" for r in caplog.records)


# --- El manual, en una sola página ------------------------------------------

def test_la_pagina_nombra_el_canal_del_juego():
    """`/vincular` sólo se acepta en los canales del juego, así que la página
    dice cuáles son en vez de mandar a escribirlo «aquí»."""
    uno = mudanza.pagina_del_manual((111,))
    dos = mudanza.pagina_del_manual((111, 222))
    ninguno = mudanza.pagina_del_manual(())

    assert "3. Escribe `/vincular` en <#111> y pega el código." in uno
    assert "3. Escribe `/vincular` en <#111> o <#222> y pega el código." in dos
    assert "3. Escribe `/vincular` y pega el código." in ninguno
    for pagina in (uno, dos, ninguno):
        assert "Escribe aquí" not in pagina
        assert config.URL_DE_LA_PAGINA in pagina
        assert "«Ya jugaba en Discord»" in pagina and len(pagina) < 2000

def test_el_manual_queda_en_una_sola_pagina():
    canal = CanalFalso()
    ids = con_el_manual_de_ocho_paginas(canal)
    pagina = mudanza.pagina_del_manual()

    correr(mudanza.publicar_la_pagina(canal, pagina))

    assert canal.editados == [(ids[0], pagina)]
    assert sorted(canal.borrados) == ids[1:]
    assert canal.publicados == []
    assert db.publicaciones_de(str(canal.id)) == {0: str(ids[0])}


def test_un_segundo_arranque_no_toca_el_canal():
    canal = CanalFalso()
    con_el_manual_de_ocho_paginas(canal)
    pagina = mudanza.pagina_del_manual()
    correr(mudanza.publicar_la_pagina(canal, pagina))
    canal.publicados.clear()
    canal.editados.clear()
    canal.borrados.clear()

    correr(mudanza.publicar_la_pagina(canal, pagina))

    assert (canal.publicados, canal.editados, canal.borrados) == ([], [], [])


def test_una_pagina_vieja_borrada_a_mano_no_revienta():
    canal = CanalFalso()
    ids = con_el_manual_de_ocho_paginas(canal)
    del canal.mensajes[ids[3]]   # alguien la borró a mano: `fetch_message` da NotFound

    correr(mudanza.publicar_la_pagina(canal, mudanza.pagina_del_manual()))

    assert sorted(canal.borrados) == ids[1:3] + ids[4:]
    assert db.publicacion_en(str(canal.id), 3) is None
    assert db.publicaciones_de(str(canal.id)) == {0: str(ids[0])}


def test_un_canal_sin_manual_publica_la_pagina():
    canal = CanalFalso()
    pagina = mudanza.pagina_del_manual()

    correr(mudanza.publicar_la_pagina(canal, pagina))

    assert canal.publicados == [pagina]
    (unico,) = canal.mensajes
    assert db.publicaciones_de(str(canal.id)) == {0: str(unico)}


def test_al_arrancar_deja_la_pagina_y_al_reconectar_no_la_repasa(monkeypatch):
    """`on_ready` se dispara también al reconectar; el texto sólo cambia al
    desplegar, que reinicia, así que basta con repasar el canal una vez."""
    monkeypatch.setattr(config, "CANALES", (CANAL_DE_JUEGO,))
    canal = CanalFalso(canales_del_servidor=(CANAL_DE_JUEGO,))
    con_el_manual_de_ocho_paginas(canal)
    cog = cog_con_info(monkeypatch, canal)

    correr(cog.on_ready())
    assert [m.content for m in canal.mensajes.values()] == [
        mudanza.pagina_del_manual((CANAL_DE_JUEGO,))
    ]

    canal.consultados.clear()
    correr(cog.on_ready())
    assert canal.consultados == []


def test_el_manual_nombra_solo_los_canales_del_juego_de_ese_servidor(monkeypatch):
    """Un canal del juego de otro servidor no se ve desde éste: nombrarlo
    dejaría un enlace que no lleva a ninguna parte."""
    monkeypatch.setattr(config, "CANALES", [111, 999])
    canal = CanalFalso(canales_del_servidor=(111,))
    cog = cog_con_info(monkeypatch, canal)

    correr(cog.on_ready())

    (pagina,) = canal.publicados
    assert pagina == mudanza.pagina_del_manual((111,))
    assert "<#111>" in pagina and "<#999>" not in pagina


def test_los_canales_del_juego_van_en_el_orden_de_la_configuracion(monkeypatch):
    monkeypatch.setattr(config, "CANALES", [222, 999, 111])
    canal = CanalFalso(canales_del_servidor=(111, 222))
    cog = cog_con_info(monkeypatch, canal)

    correr(cog.on_ready())

    assert canal.publicados == [mudanza.pagina_del_manual((222, 111))]


def test_en_un_servidor_sin_pagina_el_manual_dice_que_esta_en_pausa(monkeypatch):
    """La página es de un solo servidor: en los demás, el manual no puede
    mandar a nadie a ella ni a `/vincular`, que allí no canjea nada."""
    monkeypatch.setattr(config, "CANALES", (CANAL_DE_JUEGO, CANAL_DE_JUEGO + 1))
    del_pueblo = CanalFalso(CANAL_DE_INFO, canales_del_servidor=(CANAL_DE_JUEGO,))
    de_otro = CanalFalso(
        CANAL_DE_INFO + 1, guild_id=config.GUILD_WEB + 1,
        canales_del_servidor=(CANAL_DE_JUEGO + 1,),
    )
    con_el_manual_de_ocho_paginas(del_pueblo)
    viejas = con_el_manual_de_ocho_paginas(de_otro)
    cog = cog_con_info(monkeypatch, del_pueblo, de_otro)

    correr(cog.on_ready())

    assert [m.content for m in de_otro.mensajes.values()] == [mudanza.AVISO_SIN_PAGINA]
    assert sorted(de_otro.borrados) == viejas[1:]
    assert db.publicaciones_de(str(de_otro.id)) == {0: str(viejas[0])}
    assert [m.content for m in del_pueblo.mensajes.values()] == [
        mudanza.pagina_del_manual((CANAL_DE_JUEGO,))
    ]


@pytest.mark.parametrize("fallo", [
    discord.Forbidden(_RespuestaFalsa(), "sin permiso"),
    discord.HTTPException(_RespuestaFalsa(), "la nube"),
])
def test_un_fallo_de_discord_con_el_manual_avisa_y_se_reintenta(fallo, monkeypatch, caplog):
    canal = CanalFalso(fallo=fallo)
    cog = cog_con_info(monkeypatch, canal)

    with caplog.at_level("WARNING"):
        correr(cog.on_ready())   # no lanza

    assert any(r.name == "cogs.mudanza" for r in caplog.records)
    assert canal.publicados == []

    canal.fallo = None
    correr(cog.on_ready())       # al reconectar
    assert canal.publicados == [mudanza.pagina_del_manual()]


def test_un_canal_de_info_que_no_ve_no_frena_a_los_demas(monkeypatch, caplog):
    """Un canal mal puesto o de un servidor del que echaron al bot: aviso en el
    registro, y los que vienen detrás se repasan igual."""
    visible = CanalFalso(CANAL_DE_INFO + 1)
    cog = cog_con_info(monkeypatch, visible)
    monkeypatch.setattr(config, "CANALES_INFO", (CANAL_DE_INFO, visible.id))

    with caplog.at_level(logging.WARNING):
        correr(cog.on_ready())   # no lanza

    assert visible.publicados == [mudanza.pagina_del_manual()]
    assert any(
        r.name == "cogs.mudanza" and str(CANAL_DE_INFO) in r.getMessage()
        for r in caplog.records
    )


def test_un_canal_de_info_sin_servidor_no_corta_el_repaso(monkeypatch, caplog):
    """Un canal de info que no es de ningún servidor —un mensaje directo, por
    ejemplo— no tiene manual que le toque; no puede dejar sin repasar a los que
    vienen detrás."""
    sin_servidor = CanalFalso(CANAL_DE_INFO)
    sin_servidor.guild = None
    bueno = CanalFalso(CANAL_DE_INFO + 1)
    cog = cog_con_info(monkeypatch, sin_servidor, bueno)

    with caplog.at_level(logging.WARNING):
        correr(cog.on_ready())   # no lanza

    assert bueno.publicados == [mudanza.pagina_del_manual()]
    assert sin_servidor.publicados == []
    assert any(
        r.name == "cogs.mudanza" and r.levelno == logging.WARNING
        and str(CANAL_DE_INFO) in r.getMessage()
        for r in caplog.records
    )


def test_un_borrado_que_falla_se_reintenta_al_reconectar(monkeypatch, caplog):
    """Las páginas viejas se olvidan de una en una según se borran, así que el
    reintento sigue donde se quedó y no vuelve a tocar las que ya no están."""
    canal = CanalFalso()
    ids = con_el_manual_de_ocho_paginas(canal)
    canal.mensajes[ids[3]].fallo = discord.HTTPException(_RespuestaFalsa(), "la nube")
    cog = cog_con_info(monkeypatch, canal)

    with caplog.at_level("WARNING"):
        correr(cog.on_ready())   # no lanza

    assert any(r.name == "cogs.mudanza" for r in caplog.records)
    assert set(db.publicaciones_de(str(canal.id))) == {0, 3, 4, 5, 6, 7}

    canal.mensajes[ids[3]].fallo = None
    canal.borrados.clear()
    correr(cog.on_ready())       # al reconectar: el canal no quedó «al día»

    assert sorted(canal.borrados) == ids[3:]
    assert db.publicaciones_de(str(canal.id)) == {0: str(ids[0])}


# --- Del juego de Discord no queda nada -------------------------------------

BORRADOS = ("vistas", "tienda", "equipo", "jardin", "cogs.mascota", "cogs.competencias",
            "cogs.aventura", "cogs.social", "cogs.charla")


@pytest.mark.parametrize("modulo", BORRADOS)
def test_el_juego_de_discord_ya_no_esta(modulo):
    assert importlib.util.find_spec(modulo) is None


def test_solo_el_bot_habla_con_discord():
    seguidos = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.split()
    con_discord = {
        ruta for ruta in seguidos
        if not ruta.startswith("tests/")
        and re.search(r"^\s*(import|from) discord\b", (RAIZ / ruta).read_text(), re.M)
    }
    assert con_discord == {"bot.py", "comun.py", "cogs/mudanza.py"}


def test_lo_comun_es_solo_el_canal_y_el_error():
    assert {n for n in vars(comun) if not n.startswith("_") and inspect.getmodule(getattr(comun, n)) is comun} \
        == {"CanalEquivocado", "solo_en_el_canal", "manejar_error"}


@pytest.mark.parametrize("modulo, nombre", [
    (economia, "ejecutar_entrenamiento_conjunto"), (economia, "SeleccionEntrenamientoConjunto"),
    (economia, "ResultadoEntrenamientoConjunto"), (economia, "freno_de"),
    (sim, "aplicar_entrenamiento_conjunto"), (sim, "EFECTO_ENTRENAMIENTO_CONJUNTO"),
    (db, "criatura_por_pantalla"), (db, "guardar_pantalla"), (db, "esperas_de_ficha"),
    (db, "estilo_de_ficha"), (db, "guardar_estilo_de_ficha"), (db, "vivas_del_servidor"),
    (per, "prompt_jardin"),
])
def test_lo_que_era_solo_de_discord_ya_no_esta(modulo, nombre):
    assert not hasattr(modulo, nombre)


@pytest.mark.parametrize("nombre", [
    "ejecutar_viaje", "otorgar_hallazgo", "ejecutar_competencia", "puede_aprender_hablando", "aprender_hablando",
])
def test_lo_que_vuelve_en_la_pagina_se_queda(nombre):
    assert callable(getattr(economia, nombre))


def test_no_se_fue_ninguna_tabla_ni_columna():
    with db.conectar() as con:
        tablas = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert {"estilos_ficha", "conversaciones", "uso_ia", "buzon", "publicaciones", "cooldowns_persona"} <= tablas
    assert {"pantalla_msg_id", "canal_id"} <= columnas
