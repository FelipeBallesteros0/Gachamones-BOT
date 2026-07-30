"""Carreras y peleas de sumo entre criaturas de distintas personas."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import comun
import competir as comp
import db
import economia
import especies as esp
import pantalla
import simulacion as sim
import vistas

log = logging.getLogger(__name__)

SEGUNDOS_ENTRE_TRAMOS = 1.6
SEGUNDOS_PARA_ACEPTAR = 120


def _problema_para_competir(
    criatura: sim.Criatura | None, quien: str, espera: timedelta
) -> str | None:
    """Devuelve el motivo por el que no puede competir, o None si puede.

    El enfriamiento entra como parámetro y no se consulta aquí, para que la
    función siga siendo comprobable sin base de datos.
    """
    if criatura is None:
        return f"{quien} no tiene ninguna criatura viva."
    if not criatura.viva:
        return f"La criatura de {quien} ha muerto."
    if criatura.hambre < sim.HAMBRE_MINIMA_COMPETIR:
        # El hambre va antes que el enfriamiento: de las dos cosas, es la única
        # que quien lea el aviso puede arreglar.
        return esp.concordar(
            f"**{criatura.nombre}** está demasiado hambrient{{o/a}} para competir "
            f"(necesita más de {sim.HAMBRE_MINIMA_COMPETIR:.0f} de comida).",
            criatura.genero,
        )
    if espera.total_seconds() > 0:
        return (
            f"**{criatura.nombre}** todavía está recuperándose de la última "
            f"competencia (le quedan {pantalla.formato_espera(espera)})."
        )
    return None


def _problema_del_grupo(
    quienes: tuple[tuple[sim.Criatura | None, str], ...], ahora: datetime
) -> str | None:
    """El primer motivo por el que este grupo no puede competir, o None.

    Se miran **todos**, y en las dos puertas: al retar y al aceptar. Antes el
    enfriamiento se guardaba para las dos criaturas pero sólo se comprobaba el de
    quien retaba, así que quien aceptaba peleaba recién salido de otra pelea.
    """
    for criatura, quien in quienes:
        espera = (
            db.espera_de(criatura.id, sim.COMPETIR, ahora)
            if criatura is not None else timedelta(0)
        )
        problema = _problema_para_competir(criatura, quien, espera)
        if problema:
            return problema
    return None


def _ha_cambiado_la_ficha(antes: sim.Criatura, despues: sim.Criatura) -> bool:
    """Si merece la pena publicar una pantalla nueva tras competir.

    Se mira el nivel y la etapa, y no la lista de subidas, porque así se lee sin
    tener que saber qué mete `aplicar_xp` ahí dentro. Competir siempre gasta
    hambre y ánimo, así que si eso contara habría que republicar a todos, que es
    justo lo que llenaba el canal.
    """
    return antes.nivel != despues.nivel or antes.etapa != despues.etapa


def texto_recibo_competencia(
    recibo: economia.ReciboCompetencia, mencion: str
) -> str:
    cap = f"competencia {recibo.usados}/{recibo.limite} UTC"
    if recibo.topada:
        cap += " (tope)"
    texto = f"-# 🪙 {mencion} +{recibo.delta_competencia} asciicoins · {cap}"
    if recibo.evoluciono:
        evo_cap = f"{recibo.evolucion_usadas}/{economia.TOPE_EVOLUCIONES} UTC"
        if recibo.evolucion_topada:
            evo_cap += ", tope"
        texto += f" · evolución +{recibo.delta_evolucion} ({evo_cap})"
    return texto


def _invitados_validos(
    retador: discord.User, propuestos: tuple[discord.User | None, ...]
) -> tuple[list[discord.User], str | None]:
    """Los invitados de verdad, o el motivo por el que el reto no vale.

    Los huecos vacíos se ignoran: en una carrera de tres, `usuario3` y `usuario4`
    llegan como None.
    """
    invitados: list[discord.User] = []
    for usuario in propuestos:
        if usuario is None:
            continue
        if usuario.id == retador.id:
            return [], "No puedes competir contra ti mismo."
        if usuario.bot:
            return [], "Los bots no tienen mascota."
        if any(u.id == usuario.id for u in invitados):
            return [], f"Has invitado a **{usuario.display_name}** dos veces."
        invitados.append(usuario)
    if not invitados:
        return [], "Tienes que invitar a alguien."
    return invitados, None


class RetoView(discord.ui.View):
    """Un reto a una o varias personas. Arranca cuando todas han contestado.

    Quien rechaza **se cae de la competencia, no la cancela**, y al caducar el
    plazo se corre con quien haya aceptado. Con hasta cinco invitados eso importa:
    si hiciera falta el sí de todos, uno que pase de largo dejaría a los demás
    esperando dos minutos para nada. Sólo se cancela si no llegan a dos.
    """

    def __init__(self, cog: "Competencias", retador: discord.User,
                 invitados: list[discord.User], tipo: str, guild_id: str,
                 cabecera: str):
        super().__init__(timeout=SEGUNDOS_PARA_ACEPTAR)
        self.cog = cog
        self.retador = retador
        self.invitados = list(invitados)
        self.tipo = tipo
        self.guild_id = guild_id
        self.cabecera = cabecera
        self.mensaje: discord.Message | None = None
        self.dentro = [retador]          # quien reta corre de oficio
        self.fuera: list[discord.User] = []
        self._arrancado = False

    # -- estado -------------------------------------------------------------

    @property
    def pendientes(self) -> list[discord.User]:
        decididos = {u.id for u in self.dentro} | {u.id for u in self.fuera}
        return [u for u in self.invitados if u.id not in decididos]

    def marcador(self) -> str:
        """`✅ ana · ⌛ luis · ❌ sara`, para saber a quién se espera."""
        marcas = [f"✅ {self.retador.display_name}"]
        dentro = {u.id for u in self.dentro}
        fuera = {u.id for u in self.fuera}
        for usuario in self.invitados:
            if usuario.id in dentro:
                marcas.append(f"✅ {usuario.display_name}")
            elif usuario.id in fuera:
                marcas.append(f"❌ {usuario.display_name}")
            else:
                marcas.append(f"⌛ {usuario.display_name}")
        return " · ".join(marcas)

    # -- pulsaciones --------------------------------------------------------

    async def interaction_check(self, interaccion: discord.Interaction) -> bool:
        if not any(u.id == interaccion.user.id for u in self.pendientes):
            await interaccion.response.send_message(
                "Ese reto no va contigo, o ya has contestado.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Aceptar", emoji="✅", style=discord.ButtonStyle.success)
    async def aceptar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        self.dentro.append(interaccion.user)
        await self._contestado(interaccion)

    @discord.ui.button(label="Rechazar", emoji="❌", style=discord.ButtonStyle.secondary)
    async def rechazar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        self.fuera.append(interaccion.user)
        await self._contestado(interaccion)

    async def _contestado(self, interaccion: discord.Interaction) -> None:
        if self.mensaje is None:
            self.mensaje = interaccion.message
        if self.pendientes:
            # Todavía falta gente: se actualiza el marcador y se sigue esperando.
            await interaccion.response.edit_message(
                content=f"{self.cabecera}\n{self.marcador()}", view=self
            )
            return
        await interaccion.response.edit_message(content=self._cierre(), view=None)
        await self._arrancar(interaccion.channel)

    async def on_timeout(self) -> None:
        if self.mensaje is None or self._arrancado:
            return
        try:
            await self.mensaje.edit(content=self._cierre(), view=None)
        except discord.HTTPException:
            log.debug("No se pudo cerrar el reto caducado", exc_info=True)
        await self._arrancar(self.mensaje.channel)

    def pueden_competir(self) -> bool:
        """Si los que quedan son un número válido para la modalidad.

        No basta con que sean dos o más: el sumo es de 2 o de 4, así que si de un
        torneo se cae uno quedan tres y no hay forma de emparejarlos.
        """
        return len(self.dentro) in comp.CUANTOS_CABEN[self.tipo]

    def _cierre(self) -> str:
        """Con qué se queda el mensaje del reto cuando ya no hay nada que esperar."""
        if self.pueden_competir():
            return "⚔️ " + " vs ".join(u.mention for u in self.dentro)

        if self.fuera:
            quienes = ", ".join(u.mention for u in self.fuera)
            verbo = "ha" if len(self.fuera) == 1 else "han"
            rechazo = f"🚫 {quienes} {verbo} rechazado el reto"
            if len(self.dentro) >= 2:
                caben = " o ".join(map(str, comp.CUANTOS_CABEN[self.tipo]))
                return (
                    f"{rechazo}, y así no salen los números: "
                    f"{comp.NOMBRES[self.tipo]} es de {caben}."
                )
            return f"{rechazo}."

        return f"⌛ Nadie ha contestado al reto de {self.retador.mention}."

    async def _arrancar(self, canal: discord.abc.Messageable) -> None:
        if self._arrancado:
            return
        self._arrancado = True
        self.stop()
        if not self.pueden_competir():
            return
        if self.mensaje is None:
            return
        await self.cog.disputar(
            canal, self.dentro, self.tipo, self.guild_id, str(self.mensaje.id)
        )


class Competencias(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # -- comandos -----------------------------------------------------------

    @app_commands.command(
        name="carrera",
        description="Reta a hasta cuatro personas a una carrera (velocidad + 1d20)",
    )
    @app_commands.describe(
        usuario="A quién quieres retar",
        usuario2="Otro más (opcional)",
        usuario3="Otro más (opcional)",
        usuario4="Otro más (opcional)",
    )
    @comun.solo_en_el_canal()
    async def carrera(
        self,
        interaccion: discord.Interaction,
        usuario: discord.User,
        usuario2: discord.User | None = None,
        usuario3: discord.User | None = None,
        usuario4: discord.User | None = None,
    ):
        await self._retar(
            interaccion, (usuario, usuario2, usuario3, usuario4), comp.CARRERA
        )

    @app_commands.command(
        name="sumo",
        description="Reta a un sumo, o monta un torneo de cuatro (fuerza + 1d20)",
    )
    @app_commands.describe(
        usuario="A quién quieres retar",
        usuario2="Para torneo de cuatro: hay que invitar a los dos",
        usuario3="Para torneo de cuatro: hay que invitar a los dos",
    )
    @comun.solo_en_el_canal()
    async def sumo(
        self,
        interaccion: discord.Interaction,
        usuario: discord.User,
        usuario2: discord.User | None = None,
        usuario3: discord.User | None = None,
    ):
        await self._retar(interaccion, (usuario, usuario2, usuario3), comp.SUMO)

    async def _retar(
        self,
        interaccion: discord.Interaction,
        propuestos: tuple[discord.User | None, ...],
        tipo: str,
    ) -> None:
        ahora = db.ahora_utc()
        retador = interaccion.user
        guild_id = str(interaccion.guild_id)

        invitados, problema = _invitados_validos(retador, propuestos)
        if problema:
            await interaccion.response.send_message(problema, ephemeral=True)
            return

        caben = comp.CUANTOS_CABEN[tipo]
        if len(invitados) + 1 not in caben:
            await interaccion.response.send_message(
                f"{comp.NOMBRES[tipo]} es de {' o '.join(map(str, caben))}, "
                f"y sois {len(invitados) + 1}.",
                ephemeral=True,
            )
            return

        # Todos los participantes, empezando por quien reta.
        criaturas = []
        for usuario in (retador, *invitados):
            criatura = db.criatura_activa(str(usuario.id), guild_id)
            if criatura is not None:
                criatura = sim.avanzar(criatura, ahora)
                db.guardar(criatura)
            criaturas.append(criatura)

        problema = _problema_del_grupo(
            tuple(zip(criaturas, [u.display_name for u in (retador, *invitados)])),
            ahora,
        )
        if problema:
            await interaccion.response.send_message(problema, ephemeral=True)
            return

        a_quien = ", ".join(u.mention for u in invitados)
        nombres = ", ".join(c.nombre for c in criaturas)
        cabecera = (
            f"⚡ {retador.mention} reta a {a_quien} a "
            f"**{comp.como_se_llama(tipo, len(criaturas))}**.\n"
            f"-# {nombres} · decide la {comp.STATS[tipo]} + 1d20 "
            f"en {comp.TRAMOS} tramos."
        )
        vista = RetoView(self, retador, invitados, tipo, guild_id, cabecera)
        await interaccion.response.send_message(
            f"{cabecera}\n{vista.marcador()}", view=vista
        )
        vista.mensaje = await interaccion.original_response()

    # -- disputa ------------------------------------------------------------

    async def disputar(
        self,
        canal: discord.abc.Messageable,
        participantes: list[discord.User],
        tipo: str,
        guild_id: str,
        evento_id: str,
    ) -> None:
        """Confirma el encuentro completo y sólo entonces lo narra."""
        ahora = db.ahora_utc()
        resultado = economia.ejecutar_competencia(
            evento_id,
            [str(usuario.id) for usuario in participantes],
            guild_id,
            tipo,
            ahora,
        )
        if resultado.replay:
            return
        if resultado.problema:
            detalle = resultado.problema
            if resultado.problema_usuario_id is not None:
                usuario = next(
                    (
                        participante for participante in participantes
                        if str(participante.id) == resultado.problema_usuario_id
                    ),
                    None,
                )
                if usuario is not None:
                    detalle = _problema_para_competir(
                        resultado.problema_criatura,
                        usuario.display_name,
                        resultado.espera or timedelta(0),
                    ) or detalle
            await canal.send(f"❌ Se cancela: {detalle}")
            return

        encuentro = resultado.encuentro
        assert encuentro is not None
        # La transacción ya confirmó efectos, cooldowns, premios y operaciones.
        # Ningún fallo de Discord desde aquí puede volver a ejecutar el encuentro.
        for fotogramas in comp.fotogramas_de(encuentro):
            await self._animar(canal, fotogramas)

        recibos = "\n".join(
            texto_recibo_competencia(recibo, usuario.mention)
            for recibo, usuario in zip(resultado.recibos, participantes)
        )
        await canal.send(f"{comp.resumen(encuentro)}\n{recibos}")

        for antes, nueva, subidas, usuario in zip(
            resultado.antes, resultado.despues, resultado.subidas, participantes
        ):
            if antes.etapa != nueva.etapa:
                await canal.send(f"{usuario.mention}")
                await canal.send(pantalla.render_evolucion(
                    nueva, antes.etapa, subidas
                ))
            elif subidas:
                await canal.send(
                    f"✨ **{nueva.nombre}** sube a nivel {nueva.nivel}, "
                    f"{usuario.mention}."
                )

            if _ha_cambiado_la_ficha(antes, nueva):
                await vistas.publicar_pantalla(canal, nueva, ahora)

    async def _animar(
        self, canal: discord.abc.Messageable, fotogramas: list[str]
    ) -> None:
        """Manda el primer fotograma y edita ese mismo mensaje con los demás."""
        mensaje = await canal.send(fotogramas[0])
        for fotograma in fotogramas[1:]:
            await asyncio.sleep(SEGUNDOS_ENTRE_TRAMOS)
            try:
                await mensaje.edit(content=fotograma)
            except discord.HTTPException:
                log.warning("No se pudo animar la competencia", exc_info=True)
                break
        await asyncio.sleep(SEGUNDOS_ENTRE_TRAMOS)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Competencias(bot))
