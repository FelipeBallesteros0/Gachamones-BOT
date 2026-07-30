"""Utilidades compartidas por los cogs."""
from __future__ import annotations

import discord
from discord import app_commands

import config


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
    if isinstance(error, CanalEquivocado):
        canales = ", ".join(f"<#{c}>" for c in config.CANALES)
        mensaje = f"Las mascotas viven en {canales}. Escríbeme allí."
    elif isinstance(error, app_commands.CommandOnCooldown):
        mensaje = f"Demasiado rápido. Prueba en {error.retry_after:.0f} s."
    else:
        raise error

    if interaccion.response.is_done():
        await interaccion.followup.send(mensaje, ephemeral=True)
    else:
        await interaccion.response.send_message(mensaje, ephemeral=True)
