"""Los botones de la pantalla y el ciclo de publicación.

Cada acción de cuidado publica una pantalla NUEVA al final del canal y congela
la anterior, salvo «Actualizar», que edita la pantalla actual en su sitio.

Los botones son *persistentes*: `timeout=None` y `custom_id` fijos. Registrados
con `bot.add_view()` al arrancar, siguen respondiendo aunque el bot se reinicie,
sin tener que recordar qué mensajes existían.

Congelar la pantalla vieja se hace editando un mensaje del propio bot, cosa que
Discord siempre permite: no hace falta el permiso «Gestionar mensajes».
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import cast

import discord
from discord import Forbidden, HTTPException, NotFound

import comun
import competir as comp
import db
import economia
import equipo
import especies as esp
import pantalla
import retrato
import simulacion as sim
import tienda

log = logging.getLogger(__name__)

ESTILOS = {
    sim.ALIMENTAR: discord.ButtonStyle.success,
    sim.JUGAR: discord.ButtonStyle.primary,
    sim.ENTRENAR: discord.ButtonStyle.primary,
    sim.LIMPIAR: discord.ButtonStyle.secondary,
    sim.ACTUALIZAR: discord.ButtonStyle.secondary,
}


def _mensaje_de(interaccion: discord.Interaction) -> discord.Message:
    if interaccion.message is None:
        raise RuntimeError("la interacción no pertenece a un mensaje")
    return interaccion.message


def _canal_de(interaccion: discord.Interaction) -> discord.abc.Messageable:
    return cast(discord.abc.Messageable, interaccion.channel)


async def _es_de_otro(interaccion: discord.Interaction) -> bool:
    """Si la ficha pulsada es de otra persona, avisa y devuelve True.

    Los botones abren o cambian **tus** cosas, así que dejarlos funcionar bajo
    la ficha de otro haría que actuaras sobre un gachamon distinto del que estás
    mirando. Vive suelta para que todos los botones usen la misma.
    """
    dueño = db.criatura_por_pantalla(str(_mensaje_de(interaccion).id))
    if dueño is None:
        await interaccion.response.send_message(
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
            ephemeral=True,
        )
        return True
    if dueño.usuario_id == str(interaccion.user.id):
        return False
    await interaccion.response.send_message(
        f"Ese es el gachamon de <@{dueño.usuario_id}>. "
        "Saca el tuyo con `/mascota`.",
        ephemeral=True,
    )
    return True


def _cog_competencias_de(interaccion: discord.Interaction) -> object | None:
    resolver = getattr(interaccion.client, "get_cog", None)
    return resolver("Competencias") if callable(resolver) else None


class MenuSocial(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="⚔️ Desafiar a otros…",
            custom_id="tama:desafiar",
            row=1,
            options=[
                discord.SelectOption(label="Carrera", value=comp.CARRERA),
                discord.SelectOption(label="Sumo", value=comp.SUMO),
                discord.SelectOption(label="Asalto al Tótem", value=comp.TOTEM),
                discord.SelectOption(
                    label="Laberinto de Ecos", value=comp.LABERINTO
                ),
                discord.SelectOption(
                    label="Entrenar fuerza juntos", value="entrenar_juntos"
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if await _es_de_otro(interaction):
            return
        tipo = self.values[0]
        if tipo == "entrenar_juntos":
            await abrir_entrenamiento_conjunto(interaction)
        elif tipo in comp.CUANTOS_CABEN:
            await abrir_seleccion_rivales(interaction, tipo)
        else:
            await interaction.response.send_message(
                "Esa competencia ya no está disponible.", ephemeral=True
            )
        if (
            interaction.response.type
            is not discord.InteractionResponseType.message_update
        ):
            await _mensaje_de(interaction).edit(view=self.view)


class MenuGestion(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="🎒 Más acciones…",
            custom_id="tama:mas_acciones",
            row=2,
            options=[
                discord.SelectOption(label="Actualizar", value=sim.ACTUALIZAR),
                discord.SelectOption(label="Mochila", value="inventario"),
                discord.SelectOption(label="Tienda", value="tienda"),
                discord.SelectOption(label="Cambiar", value="plantel"),
                discord.SelectOption(label="Personalizar", value="personalizar"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if await _es_de_otro(interaction):
            return
        accion = self.values[0]
        if accion == sim.ACTUALIZAR:
            await _ejecutar(interaction, sim.ACTUALIZAR)
        elif accion == "inventario":
            await tienda.abrir_inventario(interaction, congelar)
        elif accion == "tienda":
            await tienda.abrir_tienda(interaction)
        elif accion == "plantel":
            await equipo.abrir_plantel(
                interaction, congelar, bautizar, publicar_pantalla
            )
        elif accion == "personalizar":
            await tienda.abrir_personalizacion(interaction, republicar_ficha)
        else:
            await interaction.response.send_message(
                "Esa acción ya no está disponible.", ephemeral=True
            )
        if (
            interaction.response.type
            is not discord.InteractionResponseType.message_update
        ):
            await _mensaje_de(interaction).edit(view=self.view)


class MenuSeleccionRivales(discord.ui.UserSelect):
    def __init__(self, tipo: str) -> None:
        self.tipo = tipo
        self._usado = False
        super().__init__(
            placeholder="Elige rivales…",
            custom_id=f"tama:rivales:{tipo}",
            min_values=1,
            max_values=max(comp.CUANTOS_CABEN[tipo]) - 1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self._usado:
            await interaction.response.send_message(
                "Este selector ya se usó. Abre `/mascota` para elegir rivales "
                "de nuevo.",
                ephemeral=True,
            )
            return
        self._usado = True
        retar = getattr(_cog_competencias_de(interaction), "_retar", None)
        if retar is None:
            await interaction.response.edit_message(
                content="Las competencias no están disponibles en este momento.",
                view=None,
            )
            return
        await retar(
            interaction,
            tuple(self.values),
            self.tipo,
            canal_publico=_canal_de(interaction),
        )


class VistaSeleccionRivales(discord.ui.View):
    def __init__(self, propietario_id: str, tipo: str) -> None:
        super().__init__(timeout=180)
        self.propietario_id = propietario_id
        self.add_item(MenuSeleccionRivales(tipo))

    async def interaction_check(self, interaccion: discord.Interaction) -> bool:
        if str(interaccion.user.id) == self.propietario_id:
            return True
        await interaccion.response.send_message(
            "Este selector de rivales no es tuyo.", ephemeral=True
        )
        return False


async def abrir_seleccion_rivales(
    interaccion: discord.Interaction, tipo: str
) -> None:
    if getattr(_cog_competencias_de(interaccion), "_retar", None) is None:
        await interaccion.response.send_message(
            "Las competencias no están disponibles en este momento.", ephemeral=True
        )
        return
    cantidades = tuple(cantidad - 1 for cantidad in comp.CUANTOS_CABEN[tipo])
    copy = (
        f"entre {cantidades[0]} y {cantidades[-1]}"
        if len(cantidades) > 2
        else " o ".join(map(str, cantidades))
    )
    await interaccion.response.send_message(
        f"Elige {copy} rivales para {comp.NOMBRES[tipo].lower()}.",
        view=VistaSeleccionRivales(str(interaccion.user.id), tipo),
        ephemeral=True,
    )


class PantallaView(discord.ui.View):
    """Cuidados frecuentes, juego social y gestión secundaria de la ficha."""

    def __init__(self, congelada: bool = False):
        super().__init__(timeout=None)
        self.add_item(MenuSocial())
        self.add_item(MenuGestion())
        if congelada:
            for hijo in self.children:
                if isinstance(hijo, (discord.ui.Button, discord.ui.Select)):
                    hijo.disabled = True

    @discord.ui.button(
        label="Alimentar", emoji="🍖", row=0,
        style=discord.ButtonStyle.success, custom_id="tama:alimentar"
    )
    async def alimentar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ALIMENTAR)

    @discord.ui.button(
        label="Jugar", emoji="🎮", row=0,
        style=discord.ButtonStyle.primary, custom_id="tama:jugar"
    )
    async def jugar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.JUGAR)

    @discord.ui.button(
        label="Entrenar fuerza", emoji="🏋️", row=0,
        style=discord.ButtonStyle.primary, custom_id="tama:entrenar"
    )
    async def entrenar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ENTRENAR)

    @discord.ui.button(
        label="Limpiar", emoji="🧼", row=0,
        style=discord.ButtonStyle.secondary, custom_id="tama:limpiar"
    )
    async def limpiar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.LIMPIAR)


class PantallaAnteriorView(discord.ui.View):
    """Despacha los controles de fichas publicadas antes del rediseño."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Actualizar", emoji="🔄", row=0,
        style=discord.ButtonStyle.secondary, custom_id="tama:actualizar"
    )
    async def actualizar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ACTUALIZAR)

    @discord.ui.button(
        label="Mochila", emoji="🎒", row=0,
        style=discord.ButtonStyle.secondary, custom_id="tama:inventario"
    )
    async def abrir_mochila(
        self, interaccion: discord.Interaction, boton: discord.ui.Button
    ):
        if not await _es_de_otro(interaccion):
            await tienda.abrir_inventario(interaccion, congelar)

    @discord.ui.button(
        label="Tienda", emoji="🛒", row=0,
        style=discord.ButtonStyle.success, custom_id="tama:tienda"
    )
    async def abrir_tienda(
        self, interaccion: discord.Interaction, boton: discord.ui.Button
    ):
        if not await _es_de_otro(interaccion):
            await tienda.abrir_tienda(interaccion)

    @discord.ui.button(
        label="Cambiar", emoji="🧬", row=0,
        style=discord.ButtonStyle.primary, custom_id="tama:plantel"
    )
    async def cambiar_activo(
        self, interaccion: discord.Interaction, boton: discord.ui.Button
    ):
        if not await _es_de_otro(interaccion):
            await equipo.abrir_plantel(
                interaccion, congelar, bautizar, publicar_pantalla
            )

    @discord.ui.button(
        label="Personalizar", emoji="🎨", row=0,
        style=discord.ButtonStyle.secondary, custom_id="tama:personalizar"
    )
    async def personalizar(
        self, interaccion: discord.Interaction, boton: discord.ui.Button
    ):
        if not await _es_de_otro(interaccion):
            await tienda.abrir_personalizacion(interaccion, republicar_ficha)

    @discord.ui.button(
        label="Entrenar fuerza juntos", emoji="🤝", row=1,
        style=discord.ButtonStyle.primary, custom_id="tama:entrenar_juntos"
    )
    async def entrenar_juntos(
        self, interaccion: discord.Interaction, boton: discord.ui.Button
    ):
        await abrir_entrenamiento_conjunto(interaccion)


def _resumen_participante(resultado: sim.ResultadoAccion) -> str:
    partes = []
    if resultado.evoluciono:
        partes.append(
            "evolución a "
            f"{esp.nombre_etapa(resultado.criatura.etapa, resultado.criatura.genero)}"
        )
    if resultado.rupturas:
        partes.append(
            "vetas " + ", ".join(ruptura.stat for ruptura in resultado.rupturas)
        )
    elif resultado.marca:
        partes.append("vetas en movimiento")
    else:
        partes.append("vetas quietas")
    return " · ".join(partes)


def texto_resultado_entrenamiento_conjunto(
    resultado: economia.ResultadoEntrenamientoConjunto,
) -> str:
    if len(resultado.participantes) != 2:
        raise ValueError("el resultado conjunto no tiene dos participantes")
    activo, reserva = resultado.participantes
    cuidado = resultado.delta_asciicoins - resultado.delta_evolucion
    recompensa = 0 if resultado.topada else cuidado
    monedas = f"🪙 +{recompensa} asciicoins"
    if resultado.topada:
        monedas += " (tope diario)"
    recibo = [monedas, f"cuidado {resultado.usados}/{resultado.limite} UTC"]
    if activo.evoluciono or reserva.evoluciono:
        evolucion = (
            f"evolución +{resultado.delta_evolucion} · "
            f"{resultado.evolucion_usadas}/{economia.TOPE_EVOLUCIONES} UTC"
        )
        if (
            resultado.delta_evolucion == 0
            and resultado.evolucion_usadas >= economia.TOPE_EVOLUCIONES
        ):
            evolucion += " (tope)"
        recibo.append(evolucion)
    return "\n".join((
        "🏋️ Entrenamiento conjunto: "
        f"**{activo.criatura.nombre}** + **{reserva.criatura.nombre}**.",
        "-# Cada participante: +2 XP · fuerza +1 entrenamiento · "
        "-10 comida · -5 ánimo",
        f"-# {activo.criatura.nombre}: {_resumen_participante(activo)} · "
        f"{reserva.criatura.nombre}: {_resumen_participante(reserva)}",
        pantalla.recibo(*recibo),
    ))


class MenuEntrenamientoConjunto(discord.ui.Select):
    def __init__(
        self,
        activo: sim.Criatura,
        reservas: list[sim.Criatura],
        pantalla_msg_id: str,
    ):
        super().__init__(
            placeholder="¿Con quién entrena?",
            custom_id="tama:entrenar_juntos:reserva",
            options=[
                discord.SelectOption(label=reserva.nombre[:100], value=str(reserva.id))
                for reserva in reservas
            ],
        )
        self.activo = (activo.id, activo.nombre)
        self.reservas = {
            str(reserva.id): (reserva.id, reserva.nombre) for reserva in reservas
        }
        self.pantalla_msg_id = pantalla_msg_id

    async def callback(self, interaction: discord.Interaction) -> None:
        reserva = self.reservas.get(self.values[0] if self.values else "")
        if reserva is None:
            await interaction.response.edit_message(
                content="Ese compañero ya no está disponible. "
                "Abre «Entrenar fuerza juntos» otra vez.",
                view=None,
            )
            return

        ahora = db.ahora_utc()
        resultado = economia.ejecutar_entrenamiento_conjunto(
            str(interaction.id),
            str(interaction.user.id),
            str(interaction.guild_id),
            economia.SeleccionEntrenamientoConjunto(
                self.activo[0], self.activo[1], reserva[0], reserva[1]
            ),
            ahora,
        )
        if resultado.replay:
            texto = "Esta interacción ya estaba procesada."
        elif resultado.problema == "activo_caduco":
            texto = "Esta ficha ya no está vigente. Abre la actual con `/mascota`."
        elif resultado.problema == "reserva_caduca":
            texto = (
                "Ese compañero ya no está disponible. "
                "Abre «Entrenar fuerza juntos» otra vez."
            )
        elif resultado.problema == "cooldown":
            if resultado.bloqueada is None or resultado.espera is None:
                raise RuntimeError("resultado de cooldown incompleto")
            texto = (
                f"Todavía no. {resultado.bloqueada.nombre} puede volver a "
                f"entrenar en {pantalla.formato_espera(resultado.espera)}."
            )
        elif resultado.problema == "activo_muerto":
            texto = "Tu gachamon ya no está entre nosotros."
        else:
            texto = ""

        if texto:
            await interaction.response.edit_message(content=texto, view=None)
            if resultado.problema == "activo_muerto" and resultado.bloqueada:
                canal = _canal_de(interaction)
                await congelar(
                    canal,
                    resultado.bloqueada.pantalla_msg_id or self.pantalla_msg_id,
                )
                await canal.send(pantalla.render(resultado.bloqueada, ahora))
            return

        if len(resultado.participantes) != 2:
            raise RuntimeError("resultado conjunto sin dos participantes")
        await interaction.response.edit_message(
            content="Entrenamiento conjunto completado.", view=None
        )
        canal = _canal_de(interaction)
        activo, reserva_resultado = resultado.participantes
        await publicar_pantalla(
            canal,
            activo.criatura,
            ahora,
            aviso=texto_resultado_entrenamiento_conjunto(resultado),
        )
        await comun.anunciar_logros(canal, activo.criatura, ahora)
        await comun.anunciar_logros(canal, reserva_resultado.criatura, ahora)


class VistaEntrenamientoConjunto(discord.ui.View):
    def __init__(
        self,
        activo: sim.Criatura,
        reservas: list[sim.Criatura],
        pantalla_msg_id: str,
    ):
        super().__init__(timeout=120)
        self.add_item(
            MenuEntrenamientoConjunto(activo, reservas, pantalla_msg_id)
        )


async def abrir_entrenamiento_conjunto(
    interaccion: discord.Interaction,
) -> None:
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)
    mensaje_id = str(_mensaje_de(interaccion).id)
    ficha = db.criatura_por_pantalla(mensaje_id)
    if ficha is not None and ficha.usuario_id != usuario_id:
        await interaccion.response.send_message(
            f"Ese es el gachamon de <@{ficha.usuario_id}>. "
            "Saca el tuyo con `/mascota` o `/huevo`.",
            ephemeral=True,
        )
        return
    activo = db.criatura_activa(usuario_id, guild_id)
    if (
        ficha is None
        or activo is None
        or ficha.id != activo.id
        or not ficha.viva
        or not ficha.activa
    ):
        await interaccion.response.send_message(
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
            ephemeral=True,
        )
        return

    reservas = [
        criatura
        for criatura in db.plantel(usuario_id, guild_id)
        if (
            criatura.id != activo.id
            and criatura.viva
            and not criatura.activa
            and not sim.esta_sin_nombrar(criatura)
        )
    ]
    if not reservas:
        await interaccion.response.send_message(
            "No tienes ninguna reserva viva y con nombre para entrenar.",
            ephemeral=True,
        )
        return
    await interaccion.response.send_message(
        "Elige una reserva para entrenar con tu gachamon activo.",
        view=VistaEntrenamientoConjunto(activo, reservas, mensaje_id),
        ephemeral=True,
    )


class NombreModal(discord.ui.Modal, title="Ponle nombre"):
    """Bautizo. La criatura ya existe: esto sólo le cambia el nombre.

    Con `criatura_id` bautiza a esa criatura concreta; sin él, a la activa. La
    diferencia la trajo el reclutamiento: quien se une en una `/aventura` entra
    en la incubadora y **no puede activarse hasta tener nombre**, así que buscar
    «la activa» le habría cambiado el nombre a la mascota equivocada.
    """

    def __init__(self, nombre_actual: str, criatura_id: int | None = None):
        super().__init__()
        self.criatura_id = criatura_id
        self.nombre = discord.ui.TextInput(
            label="¿Cómo se va a llamar?",
            default=nombre_actual,
            placeholder="Pelusa",
            min_length=1,
        )
        self.add_item(self.nombre)

    async def on_submit(self, interaccion: discord.Interaction) -> None:
        try:
            nombre = sim.normalizar_nombre(str(self.nombre))
        except ValueError as error:
            await interaccion.response.send_message(
                f"Nombre no válido. {error}", ephemeral=True
            )
            return

        ahora = db.ahora_utc()

        if self.criatura_id is None:
            criatura = db.criatura_activa(
                str(interaccion.user.id), str(interaccion.guild_id)
            )
        else:
            criatura = db.por_id(self.criatura_id)
            if criatura is not None and (
                criatura.usuario_id != str(interaccion.user.id)
                or criatura.guild_id != str(interaccion.guild_id)
            ):
                criatura = None
        if criatura is None:
            await interaccion.response.send_message(
                "Ya no tienes ningún gachamon vivo.", ephemeral=True
            )
            return

        # A la que duerme en la incubadora no se le adelanta el reloj: sólo la
        # activa decae, y `avanzar` le comería el hambre por estar guardada.
        if criatura.activa:
            criatura = db.avanzar(criatura, ahora)
        criatura = replace(criatura, nombre=nombre)
        db.guardar(criatura)

        # La revelación pierde el botón: ya está bautizada.
        await interaccion.response.edit_message(view=None)
        canal = _canal_de(interaccion)
        await canal.send(
            f"✨ {interaccion.user.mention} la ha llamado **{nombre}**."
        )
        if criatura.activa:
            await publicar_pantalla(canal, criatura, ahora)

    async def on_error(self, interaccion: discord.Interaction, error: Exception) -> None:
        log.exception("Fallo al poner nombre", exc_info=error)
        mensaje = "No he podido guardar el nombre. Inténtalo otra vez."
        if interaccion.response.is_done():
            await interaccion.followup.send(mensaje, ephemeral=True)
        else:
            await interaccion.response.send_message(mensaje, ephemeral=True)


class NombrarView(discord.ui.View):
    """Botón de bautizo bajo la revelación.

    Es persistente, como los de la pantalla: si el bot se reinicia entre que
    sale del huevo y le pones nombre, el botón sigue funcionando. No necesita
    recordar nada del mensaje porque busca la criatura viva de quien pulsa.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ponerle nombre", emoji="✏️",
                       style=discord.ButtonStyle.primary, custom_id="tama:nombrar")
    async def nombrar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        criatura = db.criatura_activa(str(interaccion.user.id), str(interaccion.guild_id))
        if criatura is None:
            await interaccion.response.send_message(
                "No tienes ningún gachamon vivo. Empieza con `/huevo`.", ephemeral=True
            )
            return

        dueño = db.criatura_por_pantalla(str(_mensaje_de(interaccion).id))
        if dueño and dueño.usuario_id != str(interaccion.user.id):
            await interaccion.response.send_message(
                f"Ese gachamon es de <@{dueño.usuario_id}>.", ephemeral=True
            )
            return

        await interaccion.response.send_modal(NombreModal(criatura.nombre))


def sin_nombrar_de(usuario_id: str, guild_id: str) -> sim.Criatura | None:
    """El recluta que espera nombre, el más antiguo si hay más de uno."""
    for criatura in db.plantel(usuario_id, guild_id):
        if sim.esta_sin_nombrar(criatura):
            return criatura
    return None


class NombrarReclutaView(discord.ui.View):
    """Botón de bautizo bajo el gachamon que se acaba de unir.

    Persistente como el del huevo, y por el mismo motivo elevado a necesidad:
    hasta que no tenga nombre no puede salir de la incubadora, así que si un
    reinicio dejara el botón muerto te quedarías con un gachamon inservible.
    Por eso busca al que espera nombre en vez de llevar su identificador dentro:
    un `custom_id` con el id de la criatura no puede ser persistente.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ponerle nombre", emoji="✏️",
                       style=discord.ButtonStyle.success,
                       custom_id="tama:nombrar_recluta")
    async def nombrar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        recluta = sin_nombrar_de(str(interaccion.user.id), str(interaccion.guild_id))
        if recluta is None:
            await interaccion.response.send_message(
                "No tienes ningún gachamon esperando nombre.", ephemeral=True
            )
            return
        await interaccion.response.send_modal(NombreModal("", recluta.id))


async def bautizar(interaccion: discord.Interaction, criatura: sim.Criatura) -> None:
    """Abre el bautizo de una criatura concreta.

    Se le pasa a `equipo.abrir_plantel` igual que `congelar`, para que el menú
    del plantel pueda mandar a poner nombre sin que `equipo` importe este módulo
    —que ya lo importa a él— y sin que el bautizo dependa de que siga existiendo
    el mensaje de la aventura.
    """
    await interaccion.response.send_modal(NombreModal("", criatura.id))


def _eco_vetas_cuidado(resultado: economia.ResultadoCuidado) -> str:
    if resultado.rupturas:
        return ""
    if resultado.marca:
        return "-# Algo se pone en movimiento bajo sus vetas."
    return "-# Sus vetas permanecen quietas."


async def _ejecutar(interaccion: discord.Interaction, accion: str) -> None:
    ahora = db.ahora_utc()
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)

    # Si la pantalla pulsada es de otra persona, no dejamos que actúe sobre la
    # suya por error: sería desconcertante ver aparecer otra criatura.
    dueño = db.criatura_por_pantalla(str(_mensaje_de(interaccion).id))
    if dueño is None:
        await interaccion.response.send_message(
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
            ephemeral=True,
        )
        return
    if dueño.usuario_id != usuario_id:
        await interaccion.response.send_message(
            f"Ese es el gachamon de <@{dueño.usuario_id}>. "
            "Saca el tuyo con `/mascota` o `/huevo`.",
            ephemeral=True,
        )
        return
    if dueño.viva and not dueño.activa:
        await interaccion.response.send_message(
            "Ese gachamon está en la incubadora. Cambia el activo para cuidarlo.",
            ephemeral=True,
        )
        return
    if accion == sim.ACTUALIZAR and (not dueño.viva or not dueño.activa):
        await interaccion.response.send_message(
            "Esta ficha ya no está vigente. Abre la actual con `/mascota`.",
            ephemeral=True,
        )
        return

    # Esta llamada síncrona es la frontera autoritativa: lee el estado vivo,
    # avanza el tiempo, decide el cooldown y guarda efecto + cooldown en una sola
    # transacción. No se hace ningún await hasta que SQLite ha terminado.
    resultado = economia.ejecutar_cuidado(
        str(interaccion.id), usuario_id, guild_id, accion, ahora
    )
    if resultado is None:
        await interaccion.response.send_message(
            "No tienes ningún gachamon vivo. Empieza con `/huevo`.", ephemeral=True
        )
        return

    if resultado.replay:
        await interaccion.response.send_message(
            "Esta interacción ya estaba procesada.", ephemeral=True
        )
        return

    if accion == sim.ACTUALIZAR:
        ficha = _ficha(
            resultado.criatura, ahora,
            esperas=db.esperas_de_ficha(
                resultado.criatura, ahora, pantalla.ACCIONES_EN_FICHA
            ),
            efectos=db.efectos_activos(resultado.criatura.id, ahora),
            en_la_incubadora=max(
                0,
                len(db.plantel(
                    resultado.criatura.usuario_id, resultado.criatura.guild_id
                )) - 1,
            ),
            asciicoins=(
                economia.saldos(
                    resultado.criatura.usuario_id, resultado.criatura.guild_id
                ).asciicoins
                if resultado.criatura.viva else None
            ),
        )
        vista = PantallaView() if resultado.criatura.viva else None
        await interaccion.response.edit_message(**_como_edicion(ficha), view=vista)
        return

    if not resultado.criatura.viva:
        await _congelar_pulsada(interaccion)
        await _canal_de(interaccion).send(pantalla.render(resultado.criatura, ahora))
        return

    if resultado.espera:
        await interaccion.response.send_message(
            f"Todavía no. Vuelve en {pantalla.formato_espera(resultado.espera)}.",
            ephemeral=True,
        )
        return

    # `sin_efecto` es un cuidado válido que no cambió nada —limpiar a quien ya
    # está limpia—: publicar otra ficha idéntica y congelar la pulsada sería un
    # recibo falso. Se cuenta en privado y no se toca la ficha viva.
    if not resultado.ok or resultado.sin_efecto:
        mensaje = resultado.mensaje
        if resultado.ok:
            mensaje += f"\n{_eco_vetas_cuidado(resultado)}"
        await interaccion.response.send_message(mensaje, ephemeral=True)
        return

    await _congelar_pulsada(interaccion)

    canal = _canal_de(interaccion)
    if resultado.evoluciono:
        etapa_anterior = resultado.etapa_anterior
        assert etapa_anterior is not None
        await canal.send(pantalla.render_evolucion(
            resultado.criatura, etapa_anterior
        ))
    if resultado.rupturas:
        await canal.send(
            pantalla.render_rupturas(resultado.criatura, resultado.rupturas)
        )

    aviso = resultado.mensaje
    eco_vetas = _eco_vetas_cuidado(resultado)
    if eco_vetas:
        aviso += f"\n{eco_vetas}"
    if resultado.usados or resultado.topada or resultado.evoluciono:
        aviso += f"\n{texto_recibo_cuidado(resultado, accion)}"
    await publicar_pantalla(
        canal, resultado.criatura, ahora,
        aviso=aviso, ya_congelada=str(_mensaje_de(interaccion).id),
    )
    await comun.anunciar_logros(canal, resultado.criatura, ahora)


def _efecto_recibo_cuidado(
    resultado: economia.ResultadoCuidado, accion: str,
) -> tuple[str, ...]:
    xp = f"+{sim.XP_POR_CUIDADO[accion]} XP"
    if accion == sim.ALIMENTAR:
        partes = [
            "🍖 Alimentar",
            f"comida {round(resultado.criatura.hambre)}",
            f"ánimo {round(resultado.criatura.animo)}",
        ]
        if resultado.ent_salud_ganada:
            partes.append(
                f"salud +{resultado.ent_salud_ganada:g} entrenamiento"
            )
        return *partes, xp

    efecto = sim.EFECTOS_CUIDADO[accion]
    if accion == sim.JUGAR:
        return (
            "🪀 Jugar",
            f"ánimo {round(resultado.criatura.animo)}",
            f"velocidad +{efecto['ent_velocidad']:g} entrenamiento",
            xp,
            f"coste base {efecto['hambre']:g} comida",
        )
    if accion == sim.ENTRENAR:
        return (
            "🏋️ Entrenar fuerza",
            f"fuerza +{efecto['ent_fuerza']:g} entrenamiento",
            xp,
            f"coste base {efecto['hambre']:g} comida",
            f"coste base {efecto['animo']:g} ánimo",
        )
    if accion == sim.LIMPIAR:
        return "🧼 Limpiar", f"aseo {efecto['limpieza']:g}", xp
    raise ValueError(f"acción de cuidado desconocida: {accion}")


def texto_recibo_cuidado(
    resultado: economia.ResultadoCuidado, accion: str,
) -> str:
    cuidado = resultado.delta_asciicoins - resultado.delta_evolucion
    recompensa = 0 if resultado.topada else cuidado
    monedas = f"🪙 +{recompensa} asciicoins"
    if resultado.topada:
        monedas += " (tope diario)"
    partes = [
        *_efecto_recibo_cuidado(resultado, accion),
        monedas,
        f"cuidado {resultado.usados}/{resultado.limite} UTC",
    ]
    if resultado.evoluciono:
        partes.extend((
            f"evolución +{resultado.delta_evolucion}",
            f"{resultado.evolucion_usadas}/{economia.TOPE_EVOLUCIONES} UTC",
        ))
    return pantalla.recibo(*partes)


async def _congelar_pulsada(interaccion: discord.Interaction) -> None:
    """Apaga los botones del mensaje pulsado, como respuesta a la interacción."""
    try:
        await interaccion.response.edit_message(view=PantallaView(congelada=True))
    except HTTPException:
        log.warning("No se pudo congelar la pantalla pulsada", exc_info=True)


async def congelar(canal: discord.abc.Messageable, mensaje_id: str | None) -> None:
    """Apaga los botones de una pantalla concreta por su ID.

    El canal que llega es sólo una pista: los menús y los comandos directos
    únicamente saben desde dónde se les ha abierto, y la ficha puede estar en
    otro canal del servidor. Manda el canal guardado con la propia pantalla; si
    no se sabe de quién es, o no se llega a él, se usa el que venga.
    """
    if not mensaje_id:
        return
    dueño = db.criatura_por_pantalla(mensaje_id)
    if dueño is not None:
        canal = _canal_anterior(canal, dueño)
    try:
        mensaje = await canal.fetch_message(int(mensaje_id))
        await mensaje.edit(view=PantallaView(congelada=True))
    except (NotFound, Forbidden, HTTPException, ValueError):
        # Mensaje borrado o inalcanzable: no es motivo para romper el flujo.
        log.debug("No se pudo congelar la pantalla %s", mensaje_id, exc_info=True)


def _canal_anterior(canal: discord.abc.Messageable, criatura: sim.Criatura):
    """El canal donde quedó la pantalla anterior.

    Con el bot en varios canales, la pantalla vieja puede estar en otro sitio
    distinto de donde vamos a publicar la nueva. Si no la buscásemos ahí, se
    quedaría con los botones activos y habría dos pantallas vivas. Un hilo
    también cuenta: hay que buscar por canales *y* hilos, porque `get_channel`
    no mira dentro de ellos. Si el canal apuntado no vale o no se llega a él,
    se sigue con el que venga.
    """
    if not criatura.canal_id or str(getattr(canal, "id", "")) == criatura.canal_id:
        return canal
    guild = getattr(canal, "guild", None)
    if guild is None:
        return canal
    try:
        guardado = int(criatura.canal_id)
    except ValueError:
        # Fichas antiguas guardaron ahí cosas que no son un identificador.
        return canal
    return guild.get_channel_or_thread(guardado) or canal


def _ficha(criatura: sim.Criatura, ahora, **kw) -> dict:
    """Los argumentos con los que se pinta una ficha.

    Casi siempre es el texto de siempre. Para las criaturas que tienen retrato
    dibujado —qué especies, en `retrato.py`— es un embed con la imagen y el
    marco sin el dibujo, que ya se ve en la foto.

    El PNG se manda tal cual está en `arte/`: aquí no se compone ni se escribe
    nada. `discord.File` lo abre, lo sube y lo cierra.

    Devuelve un diccionario porque `send` y `edit_message` no piden el adjunto
    con el mismo nombre; de eso se encarga `_como_edicion`.
    """
    ruta = retrato.ruta_de(criatura) if criatura.viva else None
    if ruta is None:
        return {"content": pantalla.render(criatura, ahora, **kw)}

    nombre = retrato.nombre_del_adjunto(ruta)
    embed = discord.Embed(
        description=pantalla.render(criatura, ahora, sin_arte=True, **kw),
        colour=retrato.color_de(criatura),
    )
    # Imagen y no miniatura: Discord topa las miniaturas en 80×80 y el bicho se
    # veía diminuto. La imagen se pinta a tamaño real —302×374— a cambio de ir
    # debajo del marco, porque en un embed la imagen siempre es lo último.
    #
    # El nombre sale de `retrato` en los dos sitios a propósito: si la URL y el
    # adjunto no coinciden, la imagen sale vacía y no falla nada en ningún
    # registro, así que no hay forma de enterarse salvo mirándolo.
    embed.set_image(url=f"attachment://{nombre}")
    return {"content": None, "embed": embed,
            "file": discord.File(ruta, filename=nombre)}


def _como_edicion(ficha: dict) -> dict:
    """Lo mismo, pero para `edit_message`, que llama `attachments` al adjunto.

    Y hay que pasarlo SIEMPRE, aunque sea vacío: si no se menciona, Discord
    conserva el adjunto anterior, y una ficha que vuelve a ASCII se quedaría con
    el retrato viejo pegado debajo.
    """
    editable = {k: v for k, v in ficha.items() if k != "file"}
    editable["attachments"] = [ficha["file"]] if "file" in ficha else []
    editable.setdefault("content", None)
    editable.setdefault("embed", None)
    return editable


async def responder_pantalla(
    interaccion: discord.Interaction, criatura: sim.Criatura, ahora
) -> None:
    """Publica la pantalla *como respuesta* a un comando.

    Se usa cuando la pantalla es lo que el comando devuelve, para no tener que
    acusar recibo con un mensaje privado vacío antes de enviarla.
    """
    if criatura.pantalla_msg_id:
        await congelar(_canal_anterior(_canal_de(interaccion), criatura),
                       criatura.pantalla_msg_id)

    ficha = _ficha(
        criatura, ahora,
        esperas=db.esperas_de_ficha(criatura, ahora, pantalla.ACCIONES_EN_FICHA),
        efectos=db.efectos_activos(criatura.id, ahora),
        en_la_incubadora=max(
            0, len(db.plantel(criatura.usuario_id, criatura.guild_id)) - 1
        ),
        asciicoins=(
            economia.saldos(criatura.usuario_id, criatura.guild_id).asciicoins
            if criatura.viva else None
        ),
    )
    if criatura.viva:
        await interaccion.response.send_message(**ficha, view=PantallaView())
    else:
        await interaccion.response.send_message(**ficha)
    mensaje = await interaccion.original_response()
    db.guardar_pantalla(criatura.id, str(mensaje.id), str(interaccion.channel_id))


async def publicar_pantalla(
    canal: discord.abc.Messageable,
    criatura: sim.Criatura,
    ahora,
    aviso: str = "",
    ya_congelada: str | None = None,
) -> discord.Message:
    """Congela la pantalla viva anterior y publica una nueva al final del canal."""
    if criatura.pantalla_msg_id and criatura.pantalla_msg_id != ya_congelada:
        await congelar(_canal_anterior(canal, criatura), criatura.pantalla_msg_id)

    ficha = _ficha(
        criatura, ahora,
        esperas=db.esperas_de_ficha(criatura, ahora, pantalla.ACCIONES_EN_FICHA),
        aviso=aviso,
        efectos=db.efectos_activos(criatura.id, ahora),
        en_la_incubadora=max(
            0, len(db.plantel(criatura.usuario_id, criatura.guild_id)) - 1
        ),
        asciicoins=(
            economia.saldos(criatura.usuario_id, criatura.guild_id).asciicoins
            if criatura.viva else None
        ),
    )
    if criatura.viva:
        mensaje = await canal.send(**ficha, view=PantallaView())
    else:
        mensaje = await canal.send(**ficha)
    db.guardar_pantalla(criatura.id, str(mensaje.id), str(getattr(canal, "id")))
    return mensaje


async def republicar_ficha(
    interaccion: discord.Interaction, criatura: sim.Criatura
) -> None:
    """Vuelve a publicar la ficha porque el gachamon ha cambiado de aspecto.

    Se le pasa a `tienda.abrir_personalizacion` igual que `congelar` al plantel:
    ponerle una corona no se nota en ningún número, sólo en el dibujo, así que la
    ficha vieja se quedaría mintiendo con los botones vivos.
    """
    if interaccion.channel is None:
        return
    try:
        await publicar_pantalla(_canal_de(interaccion), criatura, db.ahora_utc())
    except (NotFound, Forbidden, HTTPException):
        log.warning("No se pudo republicar la ficha tras vestirla", exc_info=True)
