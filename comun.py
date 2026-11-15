"""Lo que comparte el bot: el canal de los comandos y el aviso de un error."""
from __future__ import annotations

import logging

import discord
from discord import app_commands

import config

log = logging.getLogger(__name__)


class CanalEquivocado(app_commands.CheckFailure):
    pass


def solo_en_el_canal():
    """Restringe un comando al canal configurado.

    Se responde en privado en vez de callar: si alguien escribe el comando en
    otro canal y no pasa nada, pensará que el bot está caído.
    """
    async def predicado(interaccion: discord.Interaction) -> bool:
        if config.CANALES and interaccion.channel_id not in config.CANALES:
            raise CanalEquivocado()
        return True

    return app_commands.check(predicado)


async def manejar_error(
    interaccion: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    inesperado = False
    if isinstance(error, app_commands.CommandNotFound):
        # Uno de los comandos del juego de antes, que siguen registrados en un
        # servidor donde la sincronización falló al arrancar.
        # Import tardío: `cogs.mudanza` importa este módulo.
        from cogs import mudanza
        log.warning(
            "Llegó /%s, que ya no existe. Mira si falló la sincronización de "
            "comandos en el servidor %s.", error.name, interaccion.guild_id,
        )
        mensaje = mudanza.aviso_para(interaccion.guild_id)
    elif isinstance(error, CanalEquivocado):
        # Sólo los canales que se ven desde este servidor: los de otro serían
        # enlaces a ninguna parte. Si no ve ninguno, todos, como antes.
        servidor = interaccion.guild
        suyos = [
            c for c in config.CANALES
            if servidor is not None and servidor.get_channel(c) is not None
        ]
        canales = ", ".join(f"<#{c}>" for c in suyos or config.CANALES)
        mensaje = f"Escríbeme en {canales}."
    elif isinstance(error, app_commands.CommandOnCooldown):
        mensaje = f"Demasiado rápido. Prueba en {error.retry_after:.0f} s."
    else:
        # Antes esto era un `raise` a secas, y por eso un comando que reventaba
        # después de `defer()` dejaba el «pensando…» girando para siempre: nadie
        # contestaba la interacción. Ahora se contesta SIEMPRE, y el error se
        # vuelve a lanzar después para que salga en el registro igual que antes.
        inesperado = True
        mensaje = "Algo se ha roto por dentro. Vuelve a intentarlo."

    try:
        if interaccion.response.is_done():
            await interaccion.followup.send(mensaje, ephemeral=True)
        else:
            await interaccion.response.send_message(mensaje, ephemeral=True)
    except discord.HTTPException:
        # Si ni el aviso se puede enviar —interacción caducada, por ejemplo—, lo
        # que no puede es tragarse el error de origen, que es el que importa.
        log.warning("No se pudo avisar del error al usuario", exc_info=True)

    if inesperado:
        raise error
