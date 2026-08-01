"""Utilidades compartidas por los cogs."""
from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands

import config
import db
import economia
import objetos as obj
import simulacion as sim


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


def texto_del_anuncio(
    criatura: sim.Criatura, recibo: economia.ReciboLogros
) -> str:
    """Cómo se canta una medalla. Aparte del envío, para poder probarlo."""
    nombre = sim.nombre_visible(criatura)
    cobro = f"{obj.EMOJI_GEMA} +{recibo.asciigems}"
    if len(recibo.nuevos) == 1:
        logro = recibo.nuevos[0]
        return (
            f"🏅 **{nombre}** consigue **{logro.nombre}** — {logro.como}. "
            f"{cobro}"
        )
    lineas = "\n".join(
        f"🏅 **{l.nombre}** — {l.como}. {obj.EMOJI_GEMA} +{l.gemas}"
        for l in recibo.nuevos
    )
    return (
        f"**{nombre}** consigue {len(recibo.nuevos)} logros. {cobro}\n{lineas}"
    )


async def anunciar_logros(
    canal: discord.abc.Messageable,
    criatura: sim.Criatura,
    ahora: datetime | None = None,
) -> None:
    """Canta lo que el gachamon acaba de conseguir, si es que hay algo.

    Va después de que cierre la transacción, como todo lo que se publica: una
    medalla anunciada que luego no estuviera sería peor que una que tarda un
    segundo en salir.

    `economia.pagar_logros` devuelve **sólo lo nuevo**, así que llamar de más no
    repite nada. Por eso esto se puede poner en cualquier sitio donde algo
    pueda desbloquearse sin tener que pensar cuál de los dieciocho era.
    """
    recibo = economia.pagar_logros(criatura, ahora or db.ahora_utc())
    if not recibo.nuevos:
        return
    await canal.send(
        f"{texto_del_anuncio(criatura, recibo)}\n"
        f"-# {obj.EMOJI_GEMA} {recibo.saldo} asciigems en reserva."
    )


async def manejar_error(
    interaccion: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, CanalEquivocado):
        canales = ", ".join(f"<#{c}>" for c in config.CANALES)
        mensaje = f"Los gachamones viven en {canales}. Escríbeme allí."
    elif isinstance(error, app_commands.CommandOnCooldown):
        mensaje = f"Demasiado rápido. Prueba en {error.retry_after:.0f} s."
    else:
        raise error

    if interaccion.response.is_done():
        await interaccion.followup.send(mensaje, ephemeral=True)
    else:
        await interaccion.response.send_message(mensaje, ephemeral=True)
