# pyright: reportMissingImports=false
"""`/aventura`: salir al campo, pasar pruebas y cruzarse con alguien.

El reparto es el mismo que en las competencias: `aventura.py` decide con los
dados y este cog sólo lo cuenta. La conversación con el salvaje vive **en
memoria**, como `RetoView`: si el bot se reinicia a media charla se pierde, y es
aceptable por lo mismo que allí.
"""
from __future__ import annotations

import asyncio
import logging
import random
import sqlite3
from dataclasses import replace
from datetime import timedelta
from typing import cast

import discord
from discord import HTTPException, app_commands
from discord.ext import commands

import aventura as av
import comun
import config
import db
import economia
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
        # El que descansa eres tú, no el gachamon: la espera es de la persona
        # desde que cambiar de activo dejó de saltársela. Nombrar aquí al
        # gachamon confundiría justo a quien acaba de cambiarlo.
        return (
            "Todavía estás descansando del último viaje "
            f"(te quedan {pantalla.formato_espera(espera)})."
        )
    return None


async def _narrar(
    criatura: sim.Criatura, bioma: av.Bioma, salida: av.Salida,
    hallazgo: str, percance: av.Percance | None, usuario_id: str, ahora,
    dueño: str,
) -> str:
    """La narración del viaje. Una sola llamada al modelo por aventura.

    Si no hay presupuesto de IA se cuenta con texto propio: la aventura no puede
    quedarse muda por eso, igual que las criaturas no se quedan sin frase.
    """
    respaldo = av.resumen_escrito(
        criatura, bioma, salida, hallazgo, percance, dueño=dueño
    )
    if db.uso_ia_ultima_hora(usuario_id, ahora) >= config.LIMITE_CHARLA_POR_HORA:
        return respaldo

    db.registrar_uso_ia(usuario_id, ahora)
    sistema, peticion = per.prompt_aventura(
        criatura, bioma.adonde, list(salida.pruebas), hallazgo, percance, dueño
    )
    # Con el tope de la charla se recortaban 7 de cada 10 narraciones, y lo que
    # se perdía era el final: justo donde se cuenta si encontraste algo.
    texto, _ = await ia.generar(
        sistema, peticion, respaldo, largo_maximo=ia.LARGO_MAXIMO_NARRACION
    )
    # El mismo guardia que el salvaje, y aquí hace más falta: desde que se narra
    # a los dos, el modelo tiene que conjugar en plural y ahí es donde se le
    # escapa el «cruzáis». Si pasa, se cuenta con el texto escrito.
    if per.usa_formas_de_vosotros(texto):
        return respaldo
    return texto


EMOJI_OPCION = {av.FUERZA: "💪", av.VELOCIDAD: "💨", av.VOLVER: "🚶"}
ESTILO_OPCION = {
    av.FUERZA: discord.ButtonStyle.danger,
    av.VELOCIDAD: discord.ButtonStyle.primary,
    av.VOLVER: discord.ButtonStyle.secondary,
}
LARGO_BOTON = 80  # lo que admite Discord en una etiqueta


async def _pedir_escena(
    bioma: av.Bioma, nivel: int, antes: str, usuario_id: str, ahora,
    rng: random.Random, evitar: av.Escena | None = None, *, favorecida: str,
) -> av.Escena:
    """La escena del nodo: la inventa el modelo y, si no puede, va una escrita.

    El respaldo se calcula siempre, antes de pedir nada: si el modelo devuelve
    algo que no cuadra, la aventura tiene que seguir igualmente. Un árbol que se
    queda sin escena deja a alguien con tres botones vacíos.
    """
    escrita = av.escena_escrita(bioma, favorecida, evitar, rng)
    if db.uso_ia_ultima_hora(usuario_id, ahora) >= config.LIMITE_CHARLA_POR_HORA:
        return escrita

    db.registrar_uso_ia(usuario_id, ahora)
    sistema, peticion = per.prompt_escena(
        bioma.adonde, nivel, antes, especies=bioma.nombres_especies,
        favorecida=favorecida,
    )
    crudo = await ia.generar_crudo(sistema, peticion)
    if not crudo:
        return escrita
    return av.escena_desde_json(crudo) or escrita


class ViajeView(discord.ui.View):
    """El árbol de decisiones: tres botones por escena, dos escenas por viaje.

    El estado va en memoria como en `EncuentroView`. Si el bot se reinicia a
    media aventura se pierde, y es aceptable por lo mismo que allí: el viaje no
    ha cobrado nada todavía salvo el enfriamiento, que se pone al empezar
    justamente para que nadie tenga diez árboles abiertos a la vez.
    """

    def __init__(self, cog: "Aventura", dueño: discord.User, guild_id: str,
                 criatura: sim.Criatura, viaje: av.Viaje):
        super().__init__(timeout=SEGUNDOS_PARA_DECIDIR)
        self.cog = cog
        self.dueño = dueño
        self.guild_id = guild_id
        self.criatura = criatura
        self.viaje = viaje
        self.mensaje: discord.Message | None = None
        self._resuelto = False
        self._resolucion = asyncio.Lock()
        self._poner_botones()

    def _poner_botones(self) -> None:
        """Las etiquetas cambian con cada escena, así que los botones se rehacen.

        Por eso no se declaran con `@discord.ui.button`: ese decorador fija la
        etiqueta al escribir la clase, y aquí la escribe el modelo en marcha.
        """
        self.clear_items()
        for opcion in av.OPCIONES_ESCENA:
            etiqueta = self.viaje.escena.etiqueta(opcion)
            if opcion != av.VOLVER:
                stat = (
                    self.criatura.fuerza if opcion == av.FUERZA
                    else self.criatura.velocidad
                )
                etiqueta += (
                    f" · {av.banda_opcion(stat, self.viaje.terreno.exigencia(opcion))}"
                )
            boton = discord.ui.Button(
                label=etiqueta[:LARGO_BOTON],
                emoji=EMOJI_OPCION[opcion],
                style=ESTILO_OPCION[opcion],
            )
            async def callback(interaction: discord.Interaction, opcion=opcion):
                await self._elegir(opcion, interaction)

            boton.callback = callback
            self.add_item(boton)

    def texto(self, beat: str = "") -> str:
        bioma = self.viaje.bioma
        van = av.quienes_van(self.criatura, self.dueño.display_name)
        cabecera = f"## {bioma.emoji} {van} salen {bioma.adonde}\n"
        if beat:
            cabecera += f"-# {beat}\n"
        if not self.viaje.sigue:
            cierre = (
                "El viaje se corta ahí."
                if self.viaje.fallo else "El viaje termina ahí."
            )
            return f"{cabecera}{cierre}"
        return (
            f"{cabecera}"
            f"-# decisión {self.viaje.nivel + 1} de {av.NIVELES_DE_AVENTURA}"
            f" · superadas {self.viaje.nodos_superados}\n"
            f"{self.viaje.escena.situacion}\n"
            f"{av.pista_marcas(self.criatura, self.viaje.terreno)}"
        )

    async def interaction_check(self, interaccion: discord.Interaction) -> bool:
        if interaccion.user.id != self.dueño.id:
            await interaccion.response.send_message(
                "Esa aventura no es tuya.", ephemeral=True
            )
            return False
        return True

    async def _elegir(self, opcion: str, interaccion: discord.Interaction) -> None:
        await interaccion.response.defer()
        async with self._resolucion:
            if self._resuelto:
                return
            rng = random.Random()
            anterior = self.viaje

            # Se tira PRIMERO y se pide la escena después. Al revés se gastaría una
            # llamada al modelo en la mitad de los viajes que terminan aquí mismo.
            self.viaje = av.avanzar(
                anterior, self.criatura, opcion, None, None, rng
            )
            prueba = (
                self.viaje.pruebas[-1]
                if len(self.viaje.pruebas) > len(anterior.pruebas)
                else None
            )
            beat = av.render_beat(prueba)

            if self.viaje.sigue:
                terreno = av.tirar_terreno(self.viaje.bioma, rng)
                escena = await _pedir_escena(
                    self.viaje.bioma, self.viaje.nivel + 1,
                    _continuacion(anterior.escena, opcion),
                    str(self.dueño.id), db.ahora_utc(), rng, anterior.escena,
                    favorecida=terreno.favorecida,
                )
                self.viaje = replace(
                    self.viaje, escena=escena, terreno=terreno
                )
                self._poner_botones()
                await self._editar(self.texto(beat), self)
                return

            self.stop()
            await self._editar(self.texto(beat), None)
            self._resuelto = True
            await self.cog.resolver(
                interaccion.channel, self.dueño, self.guild_id,
                self.criatura, self.viaje,
            )

    async def _editar(self, cuerpo: str, vista) -> None:
        if self.mensaje is None:
            return
        try:
            await self.mensaje.edit(content=cuerpo, view=vista)
        except HTTPException:
            log.warning("No se pudo actualizar la aventura", exc_info=True)

    async def on_timeout(self) -> None:
        """Dejarlo a medias cuenta como volverse: el viaje se cobra igual.

        Si no se resolviera, quien se distrae se quedaría con el enfriamiento
        puesto y sin nada a cambio, que es peor que volver con las manos vacías.
        """
        async with self._resolucion:
            if self._resuelto or self.mensaje is None:
                return
            await self._editar(f"{self.texto()}\n\n⌛ Se hizo tarde y volvió.", None)
            self._resuelto = True
            await self.cog.resolver(
                self.mensaje.channel, self.dueño, self.guild_id,
                self.criatura, self.viaje,
            )


def _continuacion(escena: av.Escena, opcion: str) -> str:
    """Qué contarle al modelo de lo que acaba de pasar, para que encadene."""
    if opcion == av.VOLVER:
        return f"Ante «{escena.situacion}» prefirió no meterse y siguió camino."
    return f"Ante «{escena.situacion}» eligió {escena.etiqueta(opcion).lower()}, y lo logró."


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
        self.historial: tuple[av.EventoEncuentro, ...] = ()
        self.mensaje: discord.Message | None = None
        self._cerrado = False
        self._refrescar_botones()

    # -- estado -------------------------------------------------------------

    def _refrescar_botones(self) -> None:
        """Las golosinas sólo salen si te queda alguna."""
        tiene = db.inventario(str(self.dueño.id), self.guild_id).get("golosinas", 0)
        for hijo in self.children:
            if isinstance(hijo, discord.ui.Button) and hijo.custom_id == "av:golosinas":
                hijo.disabled = tiene <= 0
                hijo.label = f"Golosinas ({tiene})"

    def texto(self, ultimo: str = "") -> str:
        salvaje = self.encuentro.salvaje
        definicion = salvaje.def_especie
        # Lo que se enseña es el camino hasta unirse, no la confianza cruda:
        # con el umbral en 90, un encuentro ya ganado se veía al 90 %. Se
        # redondea con `round()` y se recorta a 0..100 porque la confianza
        # cruda sí llega a 100.
        porcentaje = max(
            0,
            min(
                100,
                round(self.encuentro.confianza * 100 / av.CONFIANZA_PARA_UNIRSE),
            ),
        )
        cabecera = (
            f"## {definicion.emoji} Un {definicion.nombre} salvaje "
            f"{pantalla.EMOJI_GENERO[salvaje.genero]}\n"
            f"-# carácter por descubrir · confianza {porcentaje}% · "
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
                f"Dejas {esp.concordar('{al /a la }', self.encuentro.salvaje.genero)}"
                f"{self.encuentro.salvaje.def_especie.nombre} donde estaba."
            ),
            view=None,
        )

    async def _jugar(
        self, interaccion: discord.Interaction, opcion: str, dicho: str = ""
    ) -> None:
        """Una vuelta: el desenlace bifurca antes de cualquier texto libre."""
        antes = self.encuentro
        self.encuentro = av.aplicar_opcion(antes, opcion, random.Random())
        reaccion_mecanica = av.narrar_opcion(antes, opcion, self.encuentro)
        if not interaccion.response.is_done():
            await interaccion.response.defer()

        if not self.encuentro.sigue:
            desenlace = "se_une" if self.encuentro.se_une else "se_va"
            semilla = self.encuentro.confianza + self.encuentro.paciencia
            voz = per.linea_desenlace(
                self.encuentro.salvaje, desenlace, semilla
            )
            reaccion = f"> {voz}\n{reaccion_mecanica}"
            if self.encuentro.se_une:
                await self._unirse(interaccion, reaccion)
            else:
                self._cerrado = True
                self.stop()
                await self._editar(
                    interaccion, f"{reaccion}\n\n🚪 Se ha ido.", None
                )
            return

        if opcion == av.HABLAR:
            contexto = av.ContextoSalvaje(
                salvaje=self.encuentro.salvaje,
                acompañante=self.criatura,
                fase=av.fase_de(antes.confianza),
                fase_ahora=av.fase_de(self.encuentro.confianza),
                tendencia=av.tendencia_de(antes, self.encuentro),
                paciencia=self.encuentro.paciencia,
                dicho=dicho,
                historial=self.historial,
            )
            respuesta = await self.cog.contestar(
                contexto, str(self.dueño.id)
            )
            self.historial = av.recordar(
                self.historial, av.TurnoHablar(dicho, respuesta)
            )
            reaccion = f"> {respuesta}\n{reaccion_mecanica}"
        else:
            gesto = av.frase_gesto(
                opcion, av.le_gusta(self.encuentro.salvaje, opcion)
            )
            self.historial = av.recordar(
                self.historial, av.TurnoGesto(opcion, gesto)
            )
            reaccion = reaccion_mecanica

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
                especie=salvaje.especie,
                # Sin nombre a propósito: se guarda ya, para que no se pierda si
                # se cierra el formulario o se cae la conexión, pero no sale de
                # la incubadora hasta que lo bauticen.
                nombre=sim.NOMBRE_PENDIENTE,
                stats=salvaje.stats, ahora=ahora,
                genero=salvaje.genero, caracter=salvaje.caracter,
                canal_id=str(interaccion.channel_id),
                activa=False,  # a la incubadora: no te cambia el activo sin avisar
                # El reclutamiento se le apunta a la persona, no a ningún
                # gachamon: a la aventura vas tú y es tuyo el mérito.
                reclutada=True,
            )
        except (ValueError, sqlite3.IntegrityError) as error:
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
                f"{reaccion}\n\n🧬 **¡Se une a tu equipo!** Todavía no tiene "
                "nombre, y hasta que se lo pongas no sale de la incubadora.",
                nuevo.genero,
            ),
            vistas.NombrarReclutaView(),
        )
        # Domador y Flautista son tuyos, y también «Uno entre veinticinco» si el
        # que se acaba de unir era raro. Los del gachamon que iba se revisan
        # igual: la aventura le ha subido sus propios contadores.
        if interaccion.channel is not None:
            canal = cast(discord.abc.Messageable, interaccion.channel)
            await comun.anunciar_logros(canal, self.criatura, ahora)
            await comun.anunciar_logros_de_persona(
                canal, str(self.dueño.id), self.guild_id,
                self.dueño.display_name, ahora,
            )

    async def _editar(self, interaccion, cuerpo: str, vista) -> None:
        try:
            await interaccion.edit_original_response(
                content=self.texto(cuerpo), view=vista
            )
        except HTTPException:
            log.warning("No se pudo actualizar el encuentro", exc_info=True)

    async def on_timeout(self) -> None:
        if self._cerrado or self.mensaje is None:
            return
        try:
            await self.mensaje.edit(
                content=self.texto("⌛ Se cansó de esperar y se fue."), view=None
            )
        except HTTPException:
            log.debug("No se pudo cerrar el encuentro caducado", exc_info=True)


class HablarModal(discord.ui.Modal):
    def __init__(self, vista: EncuentroView):
        super().__init__(title="¿Qué le dices?")
        self.vista = vista
        self.dicho = discord.ui.TextInput(
            label="¿Qué le dices?",
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
        self, contexto: av.ContextoSalvaje, usuario_id: str,
    ) -> str:
        """Una respuesta no terminal; mecánica e historial ya están decididos."""
        ahora = db.ahora_utc()
        semilla = db.uso_ia_ultima_hora(usuario_id, ahora)
        respaldo = per.respaldo_salvaje(contexto, semilla)

        if semilla >= config.LIMITE_CHARLA_POR_HORA:
            return respaldo

        db.registrar_uso_ia(usuario_id, ahora)
        sistema, peticion = per.prompt_salvaje(contexto)
        texto, _ = await ia.generar(sistema, peticion, respaldo)
        if per.usa_formas_de_vosotros(texto) or per.menciona_nombre_caracter(
            texto, contexto.salvaje.caracter
        ):
            texto = respaldo
        return texto

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

        # La espera es tuya, no del gachamon, así que se mira antes incluso de
        # saber si tienes alguno: cambiar de activo no puede saltársela.
        espera = db.espera_de_persona(usuario_id, guild_id, sim.AVENTURA, ahora)
        problema = _problema_para_salir(criatura, espera)
        if problema:
            await interaccion.response.send_message(problema, ephemeral=True)
            return
        # La función de validación sólo deja pasar a una activa viva.
        assert criatura is not None

        rng = random.Random()
        bioma = av.elegir_bioma(rng)

        # El enfriamiento se pone al SALIR, no al volver: el árbol dura varios
        # minutos y sin esto se podrían abrir diez aventuras a la vez.
        db.poner_cooldown_persona(usuario_id, guild_id, sim.AVENTURA, ahora)

        canal = cast(discord.abc.Messageable, interaccion.channel)
        canal_anterior = vistas._canal_anterior(canal, criatura)
        await vistas.congelar(canal_anterior, criatura.pantalla_msg_id)
        await interaccion.response.defer()

        terreno = av.tirar_terreno(bioma, rng)
        escena = await _pedir_escena(
            bioma, 1, "", usuario_id, ahora, rng,
            favorecida=terreno.favorecida,
        )
        viaje = av.Viaje(bioma=bioma, escena=escena, terreno=terreno)
        vista = ViajeView(
            self, cast(discord.User, interaccion.user), guild_id, criatura, viaje
        )
        vista.mensaje = await interaccion.followup.send(
            vista.texto(), view=vista, wait=True
        )

    async def resolver(
        self, canal, dueño: discord.User, guild_id: str,
        criatura: sim.Criatura, viaje: av.Viaje,
    ) -> None:
        """Lo que cuesta y lo que da el viaje, una vez cerrado el árbol.

        Vive aparte del comando porque hay dos formas de terminar —decidiendo o
        dejándolo caducar— y las dos tienen que cobrar y premiar igual.
        """
        ahora = db.ahora_utc()
        usuario_id = str(dueño.id)
        rng = random.Random()
        salida = viaje.salida

        hueco = len(db.plantel(usuario_id, guild_id)) < db.MAXIMO_PLANTEL
        hallazgo = av.tirar_hallazgo(viaje.nodos_superados, hueco, rng)
        percance = av.tirar_percance(salida, rng)

        # La aventura no tiene ledger de replay, pero sí una frontera
        # autoritativa: recarga el activo, valida que siga siendo el mismo y
        # confirma desgaste + VETAS antes de publicar cualquier resultado.
        confirmado = economia.ejecutar_viaje(
            usuario_id, guild_id, criatura.id, salida, ahora, percance,
            viaje=viaje,
        )
        if confirmado.problema or confirmado.criatura is None:
            await canal.send(f"❌ Se cancela: {confirmado.problema or 'No hay un gachamon activo.'}")
            return
        cansada = confirmado.criatura
        criatura_avanzada = confirmado.antes or criatura
        rupturas = confirmado.rupturas

        pruebas = av.render_pruebas(
            criatura_avanzada, viaje.bioma, salida, percance,
            dueño=dueño.display_name,
        )
        if cansada.viva:
            pruebas += f"\n✨ +{sim.XP_AVENTURA} XP por el viaje."
        await canal.send(pruebas)

        if not cansada.viva:
            await canal.send(f"💀 **{cansada.nombre}** no sobrevivió al viaje.")
            return

        if criatura_avanzada.etapa != cansada.etapa:
            await canal.send(pantalla.render_evolucion(
                cansada, criatura_avanzada.etapa
            ))
        elif criatura_avanzada.nivel != cansada.nivel:
            await canal.send(
                f"✨ **{cansada.nombre}** sube a nivel {cansada.nivel}, "
                f"{dueño.mention}."
            )
        if rupturas:
            await canal.send(pantalla.render_rupturas(cansada, rupturas))

        narracion = await _narrar(
            criatura_avanzada, viaje.bioma, salida, hallazgo, percance, usuario_id, ahora,
            dueño.display_name,
        )
        await canal.send(narracion)

        # Después de contar el viaje y antes de lo que se encuentre: la medalla
        # es por lo andado, no por el premio. Va aquí y no en cada uno de los
        # tres finales porque los tres pasan por este punto.
        await comun.anunciar_logros(canal, cansada, ahora)

        if hallazgo == av.OBJETO:
            encontrado = av.tirar_objeto(rng)
            db.regalar(usuario_id, guild_id, encontrado)
            await canal.send(
                f"{encontrado.emoji} Encuentras **{encontrado.nombre}** por el "
                "camino. Está en tu 🎒 Mochila."
            )
            return

        if hallazgo == av.NADA:
            return

        salvaje = av.tirar_salvaje(viaje.bioma, rng)
        encuentro = av.Encuentro(
            salvaje=salvaje, confianza=av.confianza_inicial(viaje.nodos_superados)
        )
        vista = EncuentroView(self, dueño, guild_id, cansada, encuentro)
        vista.mensaje = await canal.send(vista.texto(), view=vista)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Aventura(bot))
