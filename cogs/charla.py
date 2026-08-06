"""Hablar con tu criatura mencionando al bot.

Va por menciones y no por chat libre a propósito: Discord entrega el contenido
de los mensajes que mencionan al bot **aunque el intent privilegiado Message
Content esté apagado**. Así el bot no lee todo lo que se escribe en el canal y
no hay que tocar nada en el portal de desarrolladores.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta

import discord
from discord.ext import commands

import config
import db
import economia
import ia
import simulacion as sim

log = logging.getLogger(__name__)

# El propio texto de la mención, para quitarlo del mensaje.
MENCION = re.compile(r"<@!?\d+>")

LARGO_MAXIMO_ENTRADA = 500


class Charla(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_unload(self) -> None:
        await ia.cerrar()

    @commands.Cog.listener()
    async def on_message(self, mensaje: discord.Message) -> None:
        if not self._va_conmigo(mensaje):
            return

        ahora = db.ahora_utc()
        texto = MENCION.sub("", mensaje.content).strip()[:LARGO_MAXIMO_ENTRADA]

        criatura = db.criatura_activa(str(mensaje.author.id), str(mensaje.guild.id))
        if criatura is None:
            await mensaje.reply(
                "No tienes ningún gachamon con quien hablar. Saca un huevo "
                "con `/huevo`.",
                mention_author=False,
            )
            return

        criatura = db.avanzar(criatura, ahora)
        if not criatura.viva:
            db.guardar(criatura)
            await mensaje.reply(
                f"**{criatura.nombre}** ya no puede contestarte. 🪦",
                mention_author=False,
            )
            return
        db.guardar(criatura)

        aviso = self._limite_alcanzado(str(mensaje.author.id), ahora)
        if aviso:
            await mensaje.reply(aviso, mention_author=False)
            return

        if not texto:
            texto = "*te mira sin decir nada*"

        db.registrar_uso_ia(str(mensaje.author.id), ahora)

        # Se carga antes de contestar y se reutiliza abajo: sirve de memoria
        # para el modelo y, de paso, para no premiar el mismo párrafo dos veces.
        historial = db.historial(criatura.id)

        async with mensaje.channel.typing():
            respuesta, de_la_ia = await ia.responder(
                criatura=criatura,
                ahora=ahora,
                dueño=mensaje.author.display_name,
                historial=historial,
                mensaje=texto,
                # La semilla tiene que AVANZAR con cada mensaje. Antes era
                # `victorias + derrotas + len(texto)`, que no avanza: a una
                # criatura sin competencias le salía la misma frase de respaldo
                # para dos mensajes distintos («hola» y «qué te gustaría
                # comer?» daban los dos el índice 1), y parecía que el bot
                # ignoraba a esa persona. El contador de uso sí sube.
                semilla=db.uso_ia_ultima_hora(str(mensaje.author.id), ahora),
            )

        # Las frases de respaldo no entran en la memoria: si entraran, el
        # modelo aprendería a repetirlas como si fueran suyas.
        if de_la_ia:
            db.guardar_turnos(criatura.id, texto, respuesta, ahora)
        else:
            # Sin esta línea, «el bot no me responde» era indistinguible desde
            # fuera de un bot roto: hubo que bajarse el canal por la API para
            # ver que sí contestaba, sólo que siempre lo mismo.
            log.info("Respaldo servido a %s (%s): la IA no contestó",
                     mensaje.author.display_name, criatura.nombre)

        premio = await self._premio_por_hablar_bien(
            criatura, texto, historial, ahora
        )
        await mensaje.reply(
            self._formatear(criatura, respuesta) + premio, mention_author=False
        )

    # -- ayudas -------------------------------------------------------------

    async def _premio_por_hablar_bien(
        self, criatura: sim.Criatura, texto: str, historial, ahora
    ) -> str:
        """Lo que se añade al pie si de esta conversación ha aprendido algo.

        El orden importa y es de más barato a más caro: primero las reglas —que
        no cuestan nada—, luego el enfriamiento —una lectura—, y **sólo al final
        se le pregunta al modelo**. Así la llamada extra ocurre como mucho una
        vez cada enfriamiento y no una por mensaje.
        """
        if not sim.merece_juicio(texto, historial):
            return ""
        if not economia.puede_aprender_hablando(criatura.id, ahora):
            return ""
        if not await ia.juzgar_elocuencia(texto):
            return ""

        premio = economia.aprender_hablando(
            criatura.usuario_id, criatura.guild_id, ahora
        )
        if not premio.ok:
            return ""

        # Se dice lo que de verdad ha pasado: el entrenamiento sube siempre,
        # pero `stat_final` le saca la raíz, así que la estadística sólo se
        # mueve de vez en cuando. Anunciar «+1 de ingenio» siempre sería mentir.
        subida = (
            f"Ingenio **+{premio.ingenio_ganado}**"
            if premio.ingenio_ganado
            else f"Entrenamiento de ingenio **+{premio.entrenamiento_ganado}**"
        )
        animo = f" · ánimo **+{premio.animo_ganado}**" if premio.animo_ganado else ""
        return f"\n-# ✨ Le has hecho pensar. {subida}{animo}"

    def _va_conmigo(self, mensaje: discord.Message) -> bool:
        if mensaje.author.bot or mensaje.guild is None:
            return False
        if config.CANALES and mensaje.channel.id not in config.CANALES:
            return False
        # `mensaje.mentions` no incluye @everyone ni las menciones de rol, que
        # es justo lo que queremos: hablarle a la criatura, no reaccionar a un
        # aviso general del servidor.
        return self.bot.user in mensaje.mentions

    def _limite_alcanzado(self, usuario_id: str, ahora) -> str | None:
        ultimo = db.ultimo_uso_ia(usuario_id)
        if ultimo:
            espera = timedelta(seconds=config.SEGUNDOS_ENTRE_MENSAJES) - (ahora - ultimo)
            if espera.total_seconds() > 0:
                return "Dale un segundo para pensar."

        if db.uso_ia_ultima_hora(usuario_id, ahora) >= config.LIMITE_CHARLA_POR_HORA:
            return (
                f"Tu gachamon está agotado de tanto hablar "
                f"({config.LIMITE_CHARLA_POR_HORA} mensajes por hora). "
                "Prueba dentro de un rato."
            )
        return None

    def _formatear(self, criatura: sim.Criatura, respuesta: str) -> str:
        definicion = criatura.def_especie
        citado = "\n".join(f"> {linea}" for linea in respuesta.split("\n"))
        return f"{definicion.emoji} **{criatura.nombre}**\n{citado}"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Charla(bot))
