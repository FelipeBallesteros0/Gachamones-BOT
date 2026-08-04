"""Nacimiento, pantalla y muerte de las mascotas."""
from __future__ import annotations

import logging
import random
import sqlite3
from dataclasses import replace

import discord
from discord import app_commands
from discord.ext import commands, tasks

import comun
import config
import db
import economia
import especies as esp
import pantalla
import personalidad as per
import simulacion as sim
import vistas

log = logging.getLogger(__name__)


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
        rng = random.Random()
        especie = esp.elegir_del_huevo(rng)

        try:
            criatura = db.crear(
                usuario_id=str(interaccion.user.id),
                guild_id=str(interaccion.guild_id),
                especie=especie.clave,
                nombre=especie.nombre,  # provisional hasta que la bautice
                stats=esp.tirar_stats_iniciales(especie, rng),
                genero=esp.tirar_genero(rng),
                caracter=per.tirar_caracter(rng),
                ahora=ahora,
                canal_id=str(interaccion.channel_id),
            )
        except (sqlite3.IntegrityError, ValueError):
            # `IntegrityError`: el índice único ha hecho su trabajo, dos huevos a
            # la vez. `ValueError`: el plantel está lleno. Los dos significan lo
            # mismo de cara a quien pulsa.
            await interaccion.response.send_message(
                "Ya tienes un gachamon. El huevo es sólo el de partida: los "
                "demás hay que ganárselos por ahí.",
                ephemeral=True,
            )
            return

        await interaccion.response.edit_message(
            content=pantalla.render_revelacion(criatura, ahora),
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
        self.revisar_muertes.start()

    async def cog_unload(self) -> None:
        self.revisar_muertes.cancel()

    # -- comandos -----------------------------------------------------------

    @app_commands.command(name="huevo", description="Consigue un huevo y haz nacer tu gachamon")
    @comun.solo_en_el_canal()
    async def huevo(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)

        # Se mira el plantel entero y no sólo la activa: el huevo es el de
        # partida y sólo sale si no tienes ninguno, esté donde esté. El segundo y
        # el tercero se ganan reclutándolos.
        actual = db.criatura_activa(usuario_id, guild_id)
        if actual is not None:
            actual = db.avanzar(actual, ahora)
            if not actual.viva:
                # Se murió mientras nadie miraba: se registra y, si queda alguna
                # en la incubadora, sale ella en vez de un huevo nuevo.
                db.guardar(actual)
                await vistas.congelar(interaccion.channel, actual.pantalla_msg_id)
                db.ascender_de_la_incubadora(usuario_id, guild_id, ahora)

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
        if not criatura.viva:
            db.guardar(criatura)

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

    # -- bucle de muerte ----------------------------------------------------

    @tasks.loop(minutes=config.MINUTOS_ENTRE_REVISIONES)
    async def revisar_muertes(self) -> None:
        """Avisa a quien tenga la criatura en las últimas y mata a las que ya
        llegaron a cero.

        Son dos consultas contra `avisa_en` y `muere_en`: nada de recorrer y
        simular todas las filas cada cuarto de hora.
        """
        ahora = db.ahora_utc()

        # Aprovechamos el paso para tirar los registros de uso de la IA que ya
        # no cuentan para el límite por hora.
        db.limpiar_uso_ia(ahora)

        await self._avisar_hambrientas(ahora)

        for pendiente in db.pendientes_de_morir(ahora):
            muerta = db.avanzar(pendiente, ahora)
            if muerta.viva:  # la alimentaron entre medias
                continue

            db.guardar(muerta)
            # Si tenía compañeros esperando, sale uno: quedarse sin activo
            # teniendo dos en la incubadora sería desconcertante.
            releva = db.ascender_de_la_incubadora(
                muerta.usuario_id, muerta.guild_id, ahora
            )
            canal = self._canal_de(muerta)
            if canal is None:
                continue

            await vistas.congelar(canal, muerta.pantalla_msg_id)
            try:
                await canal.send(
                    f"💀 <@{muerta.usuario_id}>, **{muerta.nombre}** ha muerto "
                    "de hambre."
                )
                await canal.send(pantalla.render(muerta, ahora))
                if releva is not None:
                    await canal.send(esp.concordar(
                        f"🧬 Sale de la incubadora **{releva.nombre}**, que "
                        "pasa a ser tu gachamon activ{o/a}.",
                        releva.genero,
                    ))
                    await vistas.publicar_pantalla(canal, releva, ahora)
            except discord.HTTPException:
                log.warning("No se pudo anunciar la muerte de %s", muerta.id,
                            exc_info=True)

    def _canal_de(self, criatura: sim.Criatura):
        """Dónde avisar: el canal donde se atendió por última vez.

        Si esa criatura es anterior a los canales múltiples, o el canal ya no
        existe, se cae al principal en vez de quedarse callado.
        """
        if criatura.canal_id:
            canal = self.bot.get_channel(int(criatura.canal_id))
            if canal is not None:
                return canal
        return self.bot.get_channel(config.CANAL_PRINCIPAL)

    async def _avisar_hambrientas(self, ahora) -> None:
        """Un aviso por criatura y por bajada. Se rearma al alimentarla."""
        for pendiente in db.pendientes_de_aviso(ahora):
            criatura = db.avanzar(pendiente, ahora)
            if not criatura.viva:
                continue  # ya no es un aviso, es un funeral: lo hace el bucle
            if criatura.hambre > sim.UMBRAL_AVISO_HAMBRE:
                continue  # la alimentaron justo antes de la revisión

            canal = self._canal_de(criatura)
            if canal is None:
                continue

            marcada = replace(criatura, avisada=True)
            db.guardar(marcada)

            restante = sim.momento_de_muerte(marcada) - ahora
            try:
                await canal.send(
                    f"⚠️ <@{marcada.usuario_id}>, **{marcada.nombre}** se está "
                    f"muriendo de hambre.\n-# Le quedan unas "
                    f"{pantalla.formato_espera(restante)}. Dale de comer."
                )
                # Con botones, para poder alimentarla desde el propio aviso.
                await vistas.publicar_pantalla(canal, marcada, ahora)
            except discord.HTTPException:
                log.warning("No se pudo avisar del hambre de %s", marcada.id,
                            exc_info=True)

    @revisar_muertes.before_loop
    async def esperar_conexion(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mascota(bot))
