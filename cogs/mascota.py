"""Nacimiento y pantalla de las mascotas."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

import comun
import config
import db
import economia
import nacer
import pantalla
import vistas


class HuevoView(discord.ui.View):
    """Botón para romper el cascarón. Sólo lo puede pulsar quien sacó el huevo.

    Al romperlo la criatura nace ya en la base de datos, con el nombre de su
    especie como provisional. Así puedes verla antes de bautizarla, y si te vas
    sin ponerle nombre no se pierde: sigue siendo tuya y el botón de nombrar
    aguanta reinicios del bot.
    """

    def __init__(self, dueño_id: int):
        super().__init__(timeout=600)
        self.dueño_id = dueño_id

    async def interaction_check(self, interaccion: discord.Interaction) -> bool:
        if interaccion.user.id != self.dueño_id:
            await interaccion.response.send_message(
                "Ese huevo no es tuyo. Saca el tuyo con `/huevo`.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Romper el cascarón", emoji="🥚",
                       style=discord.ButtonStyle.success)
    async def romper(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        self.stop()
        ahora = db.ahora_utc()

        try:
            criatura = nacer.romper_el_huevo(
                str(interaccion.user.id),
                str(interaccion.guild_id),
                ahora,
                canal_id=str(interaccion.channel_id),
            )
        except nacer.YaTieneGachamon:
            # Dos huevos a la vez o plantel lleno: de cara a quien pulsa es lo
            # mismo.
            await interaccion.response.send_message(
                "Ya tienes un gachamon. El huevo es sólo el de partida: los "
                "demás hay que ganárselos por ahí.",
                ephemeral=True,
            )
            return

        await interaccion.response.edit_message(
            **vistas._como_edicion(vistas.presentacion(
                criatura, pantalla.render_revelacion, ahora
            )),
            view=vistas.NombrarView(),
        )
        # Marcar el mensaje como suyo, para que nadie más pulse «Ponerle nombre».
        mensaje = await interaccion.original_response()
        db.guardar_pantalla(criatura.id, str(mensaje.id), str(interaccion.channel_id))

        # Si le ha salido un raro, «Uno entre veinticinco» es suyo y no del
        # bicho: la suerte fue de quien rompió el cascarón.
        if interaccion.channel is not None:
            await comun.anunciar_logros_de_persona(
                interaccion.channel, str(interaccion.user.id),
                str(interaccion.guild_id), interaccion.user.display_name, ahora,
            )


class Mascota(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.mantenimiento.start()

    async def cog_unload(self) -> None:
        self.mantenimiento.cancel()

    # -- comandos -----------------------------------------------------------

    @app_commands.command(name="huevo", description="Consigue un huevo y haz nacer tu gachamon")
    @comun.solo_en_el_canal()
    async def huevo(self, interaccion: discord.Interaction) -> None:
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)

        # Se mira el plantel entero y no sólo la activa: el huevo es el de
        # partida y sólo sale si no tienes ninguno, esté donde esté. El segundo y
        # el tercero se ganan reclutándolos.
        vivos = db.plantel(usuario_id, guild_id)
        if vivos:
            nombres = ", ".join(f"**{c.nombre}**" for c in vivos)
            await interaccion.response.send_message(
                f"Ya tienes a {nombres}. El huevo es sólo el de partida: los "
                "demás hay que ganárselos por ahí.",
                ephemeral=True,
            )
            return

        await interaccion.response.send_message(
            pantalla.render_huevo(), view=HuevoView(interaccion.user.id)
        )

    @app_commands.command(name="mascota", description="Enseña tu gachamon (o el de otra persona)")
    @app_commands.describe(usuario="De quién quieres ver el gachamon")
    @comun.solo_en_el_canal()
    async def mascota(
        self, interaccion: discord.Interaction, usuario: discord.User | None = None
    ) -> None:
        ahora = db.ahora_utc()
        objetivo = usuario or interaccion.user
        propia = objetivo.id == interaccion.user.id

        criatura = db.criatura_activa(str(objetivo.id), str(interaccion.guild_id))
        if criatura is None:
            texto = (
                "No tienes ningún gachamon vivo. Empieza con `/huevo`."
                if propia
                else f"{objetivo.display_name} no tiene ningún gachamon vivo."
            )
            await interaccion.response.send_message(texto, ephemeral=True)
            return

        criatura = db.avanzar(criatura, ahora)

        if not propia:
            # Sin botones: no es tuya, no la puedes cuidar. Los efectos sí se
            # ven: saber que el rival va dopado es parte de la gracia.
            await interaccion.response.send_message(**vistas._ficha(
                criatura, ahora,
                esperas=db.esperas_de_ficha(
                    criatura, ahora, pantalla.ACCIONES_EN_FICHA
                ),
                efectos=db.efectos_activos(criatura.id, ahora),
                asciicoins=(
                    economia.saldos(criatura.usuario_id, criatura.guild_id).asciicoins
                    if criatura.viva else None
                ),
            ))
            return

        await vistas.responder_pantalla(interaccion, criatura, ahora)

    # -- mantenimiento ------------------------------------------------------

    @tasks.loop(minutes=config.MINUTOS_ENTRE_REVISIONES)
    async def mantenimiento(self) -> None:
        """Tira los registros de uso de la IA que ya no cuentan para el límite
        por hora."""
        db.limpiar_uso_ia(db.ahora_utc())

    @mantenimiento.before_loop
    async def esperar_conexion(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mascota(bot))
