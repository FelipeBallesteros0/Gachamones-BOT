"""Arranque del bot.

Uso:
    ./venv/bin/python bot.py

Necesita un .env con DISCORD_TOKEN y CANAL_ID (ver .env.ejemplo).
CANAL_ID admite varios canales separados por comas.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

import comun
import config
import db
from vistas import (
    NombrarReclutaView,
    NombrarView,
    PantallaAnteriorView,
    PantallaView,
)

log = logging.getLogger("gachamones")

EXTENSIONES = (
    "cogs.mascota", "cogs.competencias", "cogs.aventura", "cogs.social",
    "cogs.charla",
)


class Tamagotchi(commands.Bot):
    def __init__(self) -> None:
        # Intents por defecto: bastan para slash commands y botones. En concreto
        # NO hace falta «Message Content», así que puede quedar desactivado en el
        # portal de Discord.
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
            help_command=None,
        )

    async def setup_hook(self) -> None:
        db.inicializar()

        for extension in EXTENSIONES:
            await self.load_extension(extension)

        # Vistas persistentes: los botones siguen vivos tras un reinicio sin
        # tener que recordar en qué mensajes estaban.
        self.add_view(PantallaView())
        self.add_view(PantallaAnteriorView())
        self.add_view(NombrarView())
        self.add_view(NombrarReclutaView())

        self.tree.on_error = comun.manejar_error

        if config.GUILDS:
            await self._sincronizar_en_servidores()
        else:
            comandos = await self.tree.sync()
            log.info("%d comandos sincronizados globalmente (pueden tardar "
                     "hasta una hora en aparecer)", len(comandos))

    async def _sincronizar_en_servidores(self) -> None:
        """Registra los comandos en cada servidor configurado.

        Un servidor que falle no puede tumbar el bot: si te equivocas de ID o
        se te olvida invitarlo, Discord responde 403 y antes eso reventaba el
        arranque entero, dejando sin bot también a los servidores buenos.
        """
        for guild_id in config.GUILDS:
            servidor = discord.Object(id=guild_id)
            try:
                self.tree.copy_global_to(guild=servidor)
                comandos = await self.tree.sync(guild=servidor)
            except discord.Forbidden:
                log.warning(
                    "No puedo registrar comandos en el servidor %s. ¿Está el "
                    "bot invitado ahí, y con el scope applications.commands?",
                    guild_id,
                )
            except discord.HTTPException:
                log.warning("Fallo al sincronizar en el servidor %s",
                            guild_id, exc_info=True)
            else:
                log.info("%d comandos sincronizados en el servidor %s",
                         len(comandos), guild_id)

    async def on_message(self, mensaje: discord.Message) -> None:
        """Este bot no tiene comandos de texto, sólo slash commands y botones.

        Por defecto `commands.Bot` intentaría interpretar cada mensaje como un
        comando con prefijo. Como el prefijo es la propia mención, hablarle a
        la criatura con `@Gachamon cómo estás` se interpretaba además como el
        comando «cómo» y llenaba el registro de `CommandNotFound`.

        El listener de `cogs/charla.py` no se ve afectado: los listeners de los
        cogs se despachan aparte de este método.
        """

    async def on_ready(self) -> None:
        log.info("Conectado como %s (id %s)", self.user, self.user.id)
        log.info("Servidores: %s", ", ".join(
            f"{g.name} ({g.id})" for g in self.guilds) or "ninguno")
        vistos, perdidos = [], []
        for canal_id in config.CANALES:
            canal = self.get_channel(canal_id)
            (vistos if canal else perdidos).append(
                f"#{canal.name}" if canal else str(canal_id)
            )

        if vistos:
            log.info("Canales de juego: %s", ", ".join(vistos))
        if perdidos:
            log.warning(
                "No veo estos canales: %s. ¿Está el bot en ese servidor y "
                "tiene permiso para verlos?", ", ".join(perdidos)
            )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    config.verificar()
    Tamagotchi().run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
