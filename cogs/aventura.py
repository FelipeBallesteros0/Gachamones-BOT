"""`/aventura`: salir al campo, pasar pruebas y cruzarse con alguien.

El reparto es el mismo que en las competencias: `aventura.py` decide con los
dados y este cog sólo lo cuenta. La conversación con el salvaje vive **en
memoria**, como `RetoView`: si el bot se reinicia a media charla se pierde, y es
aceptable por lo mismo que allí.
"""
from __future__ import annotations

import logging
import random
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import aventura as av
import comun
import config
import db
import especies as esp
import ia
import objetos as obj
import pantalla
import personalidad as per
import simulacion as sim
import vistas

log = logging.getLogger(__name__)

SEGUNDOS_PARA_DECIDIR = 180


def _problema_para_salir(criatura: sim.Criatura | None, espera) -> str | None:
    """El motivo por el que no se puede salir, o None.

    Tener el plantel lleno **no** es motivo: se sale igual y lo que se encuentra
    son objetos. Volver de vacío por tener equipo sería castigar por jugar.
    """
    if criatura is None:
        return "No tienes ningún gachamon. Empieza con `/huevo`."
    if criatura.hambre < sim.HAMBRE_MINIMA_AVENTURA:
        return esp.concordar(
            f"**{criatura.nombre}** está demasiado hambrient{{o/a}} para salir "
            f"(necesita más de {sim.HAMBRE_MINIMA_AVENTURA:.0f} de comida).",
            criatura.genero,
        )
    if espera.total_seconds() > 0:
        return (
            f"**{criatura.nombre}** todavía está descansando del último viaje "
            f"(le quedan {pantalla.formato_espera(espera)})."
        )
    return None


async def _narrar(
    criatura: sim.Criatura, bioma: av.Bioma, salida: av.Salida,
    hallazgo: str, usuario_id: str, ahora,
) -> str:
    """La narración del viaje. Una sola llamada al modelo por aventura.

    Si no hay presupuesto de IA se cuenta con texto propio: la aventura no puede
    quedarse muda por eso, igual que las criaturas no se quedan sin frase.
    """
    respaldo = av.resumen_escrito(criatura, bioma, salida, hallazgo)
    if db.uso_ia_ultima_hora(usuario_id, ahora) >= config.LIMITE_CHARLA_POR_HORA:
        return respaldo

    db.registrar_uso_ia(usuario_id, ahora)
    sistema, peticion = per.prompt_aventura(
        criatura, bioma.adonde, list(salida.pruebas), hallazgo
    )
    texto, _ = await ia.generar(sistema, peticion, respaldo)
    return texto


class EncuentroView(discord.ui.View):
    """El menú de convencer a un salvaje. Estado en memoria, como `RetoView`."""

    def __init__(self, cog: "Aventura", dueño: discord.User, guild_id: str,
                 criatura: sim.Criatura, encuentro: av.Encuentro):
        super().__init__(timeout=SEGUNDOS_PARA_DECIDIR)
        self.cog = cog
        self.dueño = dueño
        self.guild_id = guild_id
        self.criatura = criatura
        self.encuentro = encuentro
        self.mensaje: discord.Message | None = None
        self._cerrado = False
        self._refrescar_botones()

    # -- estado -------------------------------------------------------------

    def _refrescar_botones(self) -> None:
        """Las golosinas sólo salen si te queda alguna."""
        tiene = db.inventario(str(self.dueño.id), self.guild_id).get("golosinas", 0)
        for hijo in self.children:
            if getattr(hijo, "custom_id", None) == "av:golosinas":
                hijo.disabled = tiene <= 0
                hijo.label = f"Golosinas ({tiene})"

    def texto(self, ultimo: str = "") -> str:
        salvaje = self.encuentro.salvaje
        definicion = salvaje.def_especie
        caracter = per.CARACTERES[salvaje.caracter]
        cabecera = (
            f"## {definicion.emoji} Un {definicion.nombre} salvaje "
            f"{pantalla.EMOJI_GENERO[salvaje.genero]}\n"
            f"-# {caracter.nombre(salvaje.genero)} · "
            f"confianza {self.encuentro.confianza}/100 · "
            f"paciencia {'●' * max(0, self.encuentro.paciencia)}"
            f"{'○' * max(0, av.PACIENCIA_INICIAL - self.encuentro.paciencia)}"
        )
        return f"{cabecera}\n{ultimo}" if ultimo else cabecera

    async def interaction_check(self, interaccion: discord.Interaction) -> bool:
        if interaccion.user.id != self.dueño.id:
            await interaccion.response.send_message(
                "Ese encuentro no es tuyo.", ephemeral=True
            )
            return False
        return True

    # -- pulsaciones --------------------------------------------------------

    @discord.ui.button(label="Hablar", emoji="💬", style=discord.ButtonStyle.primary)
    async def hablar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await interaccion.response.send_modal(HablarModal(self))

    @discord.ui.button(label="Golosinas", emoji="🍬",
                       style=discord.ButtonStyle.success, custom_id="av:golosinas")
    async def golosinas(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        if not db.gastar(str(self.dueño.id), self.guild_id, "golosinas"):
            await interaccion.response.send_message(
                "Ya no te quedan golosinas.", ephemeral=True
            )
            return
        await self._jugar(interaccion, av.GOLOSINAS)

    @discord.ui.button(label="Presumir", emoji="🎭", style=discord.ButtonStyle.secondary)
    async def presumir(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await self._jugar(interaccion, av.PRESUMIR)

    @discord.ui.button(label="Esperar quieto", emoji="🧘",
                       style=discord.ButtonStyle.secondary)
    async def esperar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await self._jugar(interaccion, av.ESPERAR)

    @discord.ui.button(label="Marcharse", emoji="🚪", style=discord.ButtonStyle.danger)
    async def marcharse(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        self._cerrado = True
        self.stop()
        await interaccion.response.edit_message(
            content=self.texto(
                f"Dejáis {esp.concordar('al {/la }', self.encuentro.salvaje.genero)}"
                f"{self.encuentro.salvaje.def_especie.nombre} donde estaba."
            ),
            view=None,
        )

    async def _jugar(
        self, interaccion: discord.Interaction, opcion: str, dicho: str = ""
    ) -> None:
        """Una vuelta: los dados deciden y, si toca, el modelo pone las palabras."""
        antes = self.encuentro
        self.encuentro = av.aplicar_opcion(antes, opcion, random.Random())

        reaccion = av.narrar_opcion(antes, opcion, self.encuentro)
        if not interaccion.response.is_done():
            await interaccion.response.defer()

        if opcion == av.HABLAR:
            reaccion = await self.cog.contestar(
                self.encuentro.salvaje, self.criatura, dicho,
                str(self.dueño.id), reaccion,
            )

        if self.encuentro.se_une:
            await self._unirse(interaccion, reaccion)
            return
        if self.encuentro.se_larga:
            self._cerrado = True
            self.stop()
            await self._editar(interaccion, f"{reaccion}\n\n🚪 Se ha ido.", None)
            return

        self._refrescar_botones()
        await self._editar(interaccion, reaccion, self)

    async def _unirse(self, interaccion: discord.Interaction, reaccion: str) -> None:
        self._cerrado = True
        self.stop()
        salvaje = self.encuentro.salvaje
        ahora = db.ahora_utc()

        try:
            nuevo = db.crear(
                usuario_id=str(self.dueño.id), guild_id=self.guild_id,
                especie=salvaje.especie, nombre=salvaje.nombre,
                stats=salvaje.stats, ahora=ahora,
                genero=salvaje.genero, caracter=salvaje.caracter,
                canal_id=str(interaccion.channel_id),
                activa=False,  # a la incubadora: no te cambia el activo sin avisar
            )
        except Exception as error:
            # Tope de plantel (`ValueError`) o el índice único si alguien metió
            # otro por medio. De cara a quien juega significan lo mismo.
            log.warning("No se pudo reclutar: %s", error)
            await self._editar(
                interaccion,
                f"{reaccion}\n\n😕 Se acercaba, pero tu plantel ya está lleno.",
                None,
            )
            return

        await self._editar(
            interaccion,
            esp.concordar(
                f"{reaccion}\n\n🧬 **¡Se une a tu equipo!** Espera en la "
                "incubadora; sácal{o/a} con 🧬 **Cambiar** y ponle nombre con "
                "una placa de la tienda.",
                nuevo.genero,
            ),
            None,
        )

    async def _editar(self, interaccion, cuerpo: str, vista) -> None:
        try:
            await interaccion.edit_original_response(
                content=self.texto(cuerpo), view=vista
            )
        except discord.HTTPException:
            log.warning("No se pudo actualizar el encuentro", exc_info=True)

    async def on_timeout(self) -> None:
        if self._cerrado or self.mensaje is None:
            return
        try:
            await self.mensaje.edit(
                content=self.texto("⌛ Se cansó de esperar y se fue."), view=None
            )
        except discord.HTTPException:
            log.debug("No se pudo cerrar el encuentro caducado", exc_info=True)


class HablarModal(discord.ui.Modal, title="¿Qué le dices?"):
    def __init__(self, vista: EncuentroView):
        super().__init__()
        self.vista = vista
        self.dicho = discord.ui.TextInput(
            label="Habláis con él",
            placeholder="Tranquilo, no te vamos a hacer nada...",
            max_length=200,
        )
        self.add_item(self.dicho)

    async def on_submit(self, interaccion: discord.Interaction) -> None:
        await interaccion.response.defer()
        await self.vista._jugar(interaccion, av.HABLAR, str(self.dicho))


class Aventura(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def contestar(
        self, salvaje: av.Salvaje, criatura: sim.Criatura, dicho: str,
        usuario_id: str, reaccion: str,
    ) -> str:
        """Lo que dice el salvaje. El modelo pone las palabras, no el resultado."""
        ahora = db.ahora_utc()
        semilla = db.uso_ia_ultima_hora(usuario_id, ahora)
        respaldo = per.respaldo_salvaje(semilla)

        if semilla >= config.LIMITE_CHARLA_POR_HORA:
            return f"{respaldo}\n{reaccion}"

        db.registrar_uso_ia(usuario_id, ahora)
        sistema, peticion = per.prompt_salvaje(salvaje, criatura, dicho)
        texto, _ = await ia.generar(sistema, peticion, respaldo)
        return f"> {texto}\n{reaccion}"

    @app_commands.command(
        name="aventura",
        description="Sal al campo con tu gachamon activo, a ver qué encuentras",
    )
    @comun.solo_en_el_canal()
    async def aventura(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)

        criatura = db.criatura_activa(usuario_id, guild_id)
        if criatura is not None:
            criatura = sim.avanzar(criatura, ahora)
            db.guardar(criatura)

        espera = (
            db.espera_de(criatura.id, sim.AVENTURA, ahora)
            if criatura is not None else timedelta(0)
        )
        problema = _problema_para_salir(criatura, espera)
        if problema:
            await interaccion.response.send_message(problema, ephemeral=True)
            return

        rng = random.Random()
        bioma = av.elegir_bioma(rng)
        salida = av.explorar(criatura, bioma, rng)

        hueco = len(db.plantel(usuario_id, guild_id)) < db.MAXIMO_PLANTEL
        hallazgo = av.tirar_hallazgo(salida.superadas, hueco, rng)

        # El desgaste y el enfriamiento se aplican pase lo que pase: el viaje ya
        # se ha hecho.
        cansada = av.aplicar_desgaste(criatura, salida)
        db.guardar(cansada)
        db.poner_cooldown(criatura.id, sim.AVENTURA, ahora)

        await interaccion.response.send_message(
            av.render_pruebas(criatura, bioma, salida)
        )
        canal = interaccion.channel

        narracion = await _narrar(
            criatura, bioma, salida, hallazgo, usuario_id, ahora
        )
        await canal.send(narracion)

        if hallazgo == av.OBJETO:
            encontrado = av.tirar_objeto(rng)
            db.regalar(usuario_id, guild_id, encontrado)
            await canal.send(
                f"{encontrado.emoji} Encontráis **{encontrado.nombre}** por el "
                "camino. Está en tu 🎒 Mochila."
            )
            return

        if hallazgo == av.NADA:
            return

        salvaje = av.tirar_salvaje(bioma, rng)
        encuentro = av.Encuentro(
            salvaje=salvaje, confianza=av.confianza_inicial(salida.superadas)
        )
        vista = EncuentroView(self, interaccion.user, guild_id, cansada, encuentro)
        vista.mensaje = await canal.send(vista.texto(), view=vista)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Aventura(bot))
