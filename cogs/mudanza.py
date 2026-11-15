"""El bot de la mudanza: el juego de Discord está en pausa.

Gachamon se juega en la página. El bot sigue encendido sólo para `/vincular`,
que es la única forma de llevar allí los gachamones de Discord, y para contestar
a todo lo demás que el juego se mudó: a los botones y menús de los mensajes
viejos, a quien lo menciona y a los dos comandos que la gente escribe de
memoria, `/mascota` y `/huevo`.

No ejecuta ninguna regla del juego: sólo escribe en la base al canjear un código
(`db.canjear_codigo_de_vinculo`) y al apuntar dónde quedó el manual.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

import comun
import config
import db
import vinculo

log = logging.getLogger(__name__)

AVISO = (
    "🏠 **Gachamon se mudó a la página.** Ahora se juega en "
    f"{config.URL_DE_LA_PAGINA}. Tus gachamones, tus monedas y tus cosas te "
    "esperan ahí: entra, elige «Ya jugaba en Discord» y escribe aquí "
    "`/vincular` con el código que te dé."
)

# La página es de un solo servidor de Discord. En los demás el juego también
# está en pausa, pero no hay página adonde mandar a nadie.
AVISO_SIN_PAGINA = (
    "🏠 **Gachamon está en pausa en este servidor.** Tus gachamones y tus cosas "
    "siguen guardados."
)

SERVIDOR_SIN_WEB = "Este servidor no está conectado con la web."

DESCRIPCION_DEL_AVISO = "Gachamon se mudó a la página"


def aviso_para(guild_id: int | None) -> str:
    """El aviso de la mudanza que toca en ese servidor."""
    return AVISO if guild_id == config.GUILD_WEB else AVISO_SIN_PAGINA


def pagina_del_manual() -> str:
    """Lo único que queda en el canal de info: adónde se fue el juego y cómo
    llevarse los gachamones."""
    return f"""\
## 🏠 Gachamon se mudó a la página
Desde ahora se juega en **{config.URL_DE_LA_PAGINA}**.

**Cómo llevar tus gachamones**
1. Entra a la página con tu cuenta de Rowino.
2. Elige **«Ya jugaba en Discord»** y pide tu código.
3. Escribe aquí `/vincular` y pega el código.

-# Tus gachamones, monedas, gemas, objetos y medallas siguen guardados: los \
verás en la página en cuanto vincules.
-# Competir, las aventuras, reclutar y conversar están en pausa. Volverán en \
la página."""


async def _mensaje_publicado(canal, canal_id: str, indice: int):
    """El mensaje donde vive esa página, o `None` si hay que publicarla.

    Devuelve `None` tanto si nunca se publicó como si el mensaje apuntado ya no
    está: borrar el canal a mano no es un error, es la forma de pedirle al bot
    que lo rehaga en el siguiente arranque.
    """
    guardado = db.publicacion_en(canal_id, indice)
    if not guardado:
        return None
    try:
        return await canal.fetch_message(int(guardado))
    except discord.NotFound:
        return None


async def publicar_la_pagina(canal, texto: str) -> None:
    """Deja el manual del canal en una sola página, **editando en el sitio**.

    La página 0 se publica si no está, se edita si su texto cambió y si no, no
    se toca: un arranque sin cambios no hace ninguna llamada que modifique el
    canal. Las demás páginas del manual de antes se borran del canal y se
    olvidan; la que ya no esté porque alguien la quitó a mano sólo se olvida.

    Recibe el canal como argumento —en vez de buscarlo— para poder probarla sin
    Discord.
    """
    canal_id = str(canal.id)
    mensaje = await _mensaje_publicado(canal, canal_id, 0)
    if mensaje is None:
        nuevo = await canal.send(texto)
        db.guardar_publicacion(canal_id, 0, str(nuevo.id))
    elif mensaje.content != texto:
        await mensaje.edit(content=texto)

    for indice, mensaje_id in db.publicaciones_de(canal_id).items():
        if indice == 0:
            continue
        try:
            viejo = await canal.fetch_message(int(mensaje_id))
            await viejo.delete()
        except discord.NotFound:
            pass
        db.borrar_publicacion(canal_id, indice)


class Mudanza(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Canales cuyo manual ya se ha dejado al día en este proceso.
        # `on_ready` se dispara también al reconectar, y el texto sólo cambia al
        # desplegar —que reinicia—, así que repasarlo una vez por arranque basta.
        # Se apunta el que sale bien: el que falle se reintenta al reconectar.
        self._manual_al_dia: set[int] = set()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Deja el manual al día en cada canal de info.

        Nada de esto puede tumbar el bot: un canal mal puesto, sin permisos o
        caído deja un aviso en el registro y el bot sigue funcionando. Es el
        mismo trato que `bot.py` le da a un servidor donde no puede registrar
        comandos.
        """
        for canal_id in config.CANALES_INFO:
            if canal_id in self._manual_al_dia:
                continue
            canal = self.bot.get_channel(canal_id)
            if canal is None:
                log.warning(
                    "No veo el canal de info %s. ¿Está el bot en ese servidor "
                    "y tiene permiso para verlo?", canal_id,
                )
                continue
            try:
                await publicar_la_pagina(canal, pagina_del_manual())
            except discord.Forbidden:
                log.warning(
                    "Sin permiso para mantener el manual en #%s. Le hace falta "
                    "Ver canal, Enviar mensajes y Leer el historial.",
                    getattr(canal, "name", canal_id),
                )
            except discord.HTTPException:
                log.warning("Fallo publicando el manual en el canal %s",
                            canal_id, exc_info=True)
            else:
                self._manual_al_dia.add(canal_id)
                log.info("Manual al día en #%s",
                         getattr(canal, "name", canal_id))

    @commands.Cog.listener()
    async def on_interaction(self, interaccion: discord.Interaction) -> None:
        """Los botones, menús y formularios de los mensajes viejos.

        El bot ya no registra ninguna vista, así que todo componente o
        formulario que llega viene de un mensaje del juego de antes: se le
        contesta el aviso en vez de dejar que Discord diga que falló. Los
        comandos de barra los atiende el árbol y aquí no se tocan.
        """
        if interaccion.type not in (
            discord.InteractionType.component,
            discord.InteractionType.modal_submit,
        ):
            return
        if interaccion.response.is_done():
            return
        try:
            await interaccion.response.send_message(
                aviso_para(interaccion.guild_id), ephemeral=True
            )
        except discord.HTTPException:
            # Un botón pulsado hace rato: la interacción caducó. No hay a quién
            # contestar y no puede tumbar nada.
            log.warning("No se pudo contestar el aviso de la mudanza",
                        exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, mensaje: discord.Message) -> None:
        """Quien menciona al bot en su canal recibe el aviso de la mudanza."""
        if not self._va_conmigo(mensaje):
            return
        await mensaje.reply(aviso_para(mensaje.guild.id), mention_author=False)

    def _va_conmigo(self, mensaje: discord.Message) -> bool:
        if mensaje.author.bot or mensaje.guild is None:
            return False
        if config.CANALES and mensaje.channel.id not in config.CANALES:
            return False
        # `mensaje.mentions` no incluye @everyone ni las menciones de rol, que
        # es justo lo que queremos: contestar a quien le habla al bot, no
        # reaccionar a un aviso general del servidor.
        return self.bot.user in mensaje.mentions

    @app_commands.command(name="mascota", description=DESCRIPCION_DEL_AVISO)
    @comun.solo_en_el_canal()
    async def mascota(self, interaccion: discord.Interaction) -> None:
        await interaccion.response.send_message(
            aviso_para(interaccion.guild_id), ephemeral=True
        )

    @app_commands.command(name="huevo", description=DESCRIPCION_DEL_AVISO)
    @comun.solo_en_el_canal()
    async def huevo(self, interaccion: discord.Interaction) -> None:
        await interaccion.response.send_message(
            aviso_para(interaccion.guild_id), ephemeral=True
        )

    @app_commands.command(
        name="vincular",
        description="Une tu cuenta de Rowino con tus gachamones de aquí",
    )
    @app_commands.describe(codigo="El código que te dio la web")
    @comun.solo_en_el_canal()
    async def vincular(self, interaccion: discord.Interaction, codigo: str) -> None:
        if interaccion.guild_id != config.GUILD_WEB:
            await interaccion.response.send_message(SERVIDOR_SIN_WEB, ephemeral=True)
            return
        resultado = db.canjear_codigo_de_vinculo(
            codigo,
            str(interaccion.user.id),
            str(interaccion.guild_id),
            db.ahora_utc(),
        )
        await interaccion.response.send_message(
            vinculo.MENSAJES[resultado], ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mudanza(bot))
