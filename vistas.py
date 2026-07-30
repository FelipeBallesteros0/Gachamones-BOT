"""Los botones de la pantalla y el ciclo de publicación.

Cada acción publica una pantalla NUEVA al final del canal y congela la anterior
con los botones en gris, para que quede el registro de la vida de la criatura.

Los botones son *persistentes*: `timeout=None` y `custom_id` fijos. Registrados
con `bot.add_view()` al arrancar, siguen respondiendo aunque el bot se reinicie,
sin tener que recordar qué mensajes existían.

Congelar la pantalla vieja se hace editando un mensaje del propio bot, cosa que
Discord siempre permite: no hace falta el permiso «Gestionar mensajes».
"""
from __future__ import annotations

import logging
from dataclasses import replace

import discord

import db
import pantalla
import simulacion as sim

log = logging.getLogger(__name__)

ESTILOS = {
    sim.ALIMENTAR: discord.ButtonStyle.success,
    sim.JUGAR: discord.ButtonStyle.primary,
    sim.ENTRENAR: discord.ButtonStyle.primary,
    sim.LIMPIAR: discord.ButtonStyle.secondary,
    sim.ACTUALIZAR: discord.ButtonStyle.secondary,
}


class PantallaView(discord.ui.View):
    """Los cinco botones bajo la pantalla."""

    def __init__(self, congelada: bool = False):
        super().__init__(timeout=None)
        if congelada:
            for hijo in self.children:
                hijo.disabled = True

    @discord.ui.button(label="Alimentar", emoji="🍖",
                       style=discord.ButtonStyle.success, custom_id="tama:alimentar")
    async def alimentar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ALIMENTAR)

    @discord.ui.button(label="Jugar", emoji="🎮",
                       style=discord.ButtonStyle.primary, custom_id="tama:jugar")
    async def jugar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.JUGAR)

    @discord.ui.button(label="Entrenar", emoji="🏋️",
                       style=discord.ButtonStyle.primary, custom_id="tama:entrenar")
    async def entrenar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ENTRENAR)

    @discord.ui.button(label="Limpiar", emoji="🧼",
                       style=discord.ButtonStyle.secondary, custom_id="tama:limpiar")
    async def limpiar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.LIMPIAR)

    @discord.ui.button(label="Actualizar", emoji="🔄",
                       style=discord.ButtonStyle.secondary, custom_id="tama:actualizar")
    async def actualizar(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        await _ejecutar(interaccion, sim.ACTUALIZAR)


LARGO_MAXIMO_NOMBRE = 24


class NombreModal(discord.ui.Modal, title="Ponle nombre"):
    """Bautizo. La criatura ya existe: esto sólo le cambia el nombre."""

    def __init__(self, nombre_actual: str):
        super().__init__()
        self.nombre = discord.ui.TextInput(
            label="¿Cómo se va a llamar?",
            default=nombre_actual,
            placeholder="Pelusa",
            min_length=1,
            max_length=LARGO_MAXIMO_NOMBRE,
        )
        self.add_item(self.nombre)

    async def on_submit(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        nombre = str(self.nombre).strip()

        criatura = db.criatura_viva(str(interaccion.user.id), str(interaccion.guild_id))
        if criatura is None:
            await interaccion.response.send_message(
                "Ya no tienes ninguna criatura viva.", ephemeral=True
            )
            return
        if not nombre:
            await interaccion.response.send_message(
                "Ese nombre está vacío. Prueba otra vez.", ephemeral=True
            )
            return

        criatura = replace(sim.avanzar(criatura, ahora), nombre=nombre)
        db.guardar(criatura)

        # La revelación pierde el botón: ya está bautizada.
        await interaccion.response.edit_message(view=None)
        await interaccion.channel.send(
            f"✨ {interaccion.user.mention} la ha llamado **{nombre}**."
        )
        await publicar_pantalla(interaccion.channel, criatura, ahora)

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
        criatura = db.criatura_viva(str(interaccion.user.id), str(interaccion.guild_id))
        if criatura is None:
            await interaccion.response.send_message(
                "No tienes ninguna criatura viva. Empieza con `/huevo`.", ephemeral=True
            )
            return

        dueño = db.criatura_por_pantalla(str(interaccion.message.id))
        if dueño and dueño.usuario_id != str(interaccion.user.id):
            await interaccion.response.send_message(
                f"Esa criatura es de <@{dueño.usuario_id}>.", ephemeral=True
            )
            return

        await interaccion.response.send_modal(NombreModal(criatura.nombre))


async def _ejecutar(interaccion: discord.Interaction, accion: str) -> None:
    ahora = db.ahora_utc()
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)

    # Si la pantalla pulsada es de otra persona, no dejamos que actúe sobre la
    # suya por error: sería desconcertante ver aparecer otra criatura.
    dueño = db.criatura_por_pantalla(str(interaccion.message.id))
    if dueño and dueño.usuario_id != usuario_id:
        await interaccion.response.send_message(
            f"Esa es la mascota de <@{dueño.usuario_id}>. "
            "Saca la tuya con `/mascota` o `/huevo`.",
            ephemeral=True,
        )
        return

    criatura = db.criatura_viva(usuario_id, guild_id)
    if criatura is None:
        await interaccion.response.send_message(
            "No tienes ninguna criatura viva. Empieza con `/huevo`.", ephemeral=True
        )
        return

    criatura = sim.avanzar(criatura, ahora)
    if not criatura.viva:
        db.guardar(criatura)
        await _congelar_pulsada(interaccion)
        await interaccion.channel.send(pantalla.render(criatura, ahora))
        return

    espera = db.espera_de(criatura.id, accion, ahora)
    if espera.total_seconds() > 0 and not sim.puede_saltarse_espera(criatura, accion):
        await interaccion.response.send_message(
            f"Todavía no. Vuelve en {pantalla.formato_espera(espera)}.", ephemeral=True
        )
        return

    resultado = sim.aplicar_accion(criatura, accion, ahora)
    if not resultado.ok:
        await interaccion.response.send_message(resultado.mensaje, ephemeral=True)
        return

    db.guardar(resultado.criatura)
    db.poner_cooldown(resultado.criatura.id, accion, ahora)

    await _congelar_pulsada(interaccion)

    if resultado.evoluciono:
        await interaccion.channel.send(pantalla.render_evolucion(
            resultado.criatura, resultado.etapa_anterior, resultado.subidas
        ))

    await publicar_pantalla(
        interaccion.channel, resultado.criatura, ahora,
        aviso=resultado.mensaje, ya_congelada=str(interaccion.message.id),
    )


async def _congelar_pulsada(interaccion: discord.Interaction) -> None:
    """Apaga los botones del mensaje pulsado, como respuesta a la interacción."""
    try:
        await interaccion.response.edit_message(view=PantallaView(congelada=True))
    except discord.HTTPException:
        log.warning("No se pudo congelar la pantalla pulsada", exc_info=True)


async def congelar(canal: discord.abc.Messageable, mensaje_id: str | None) -> None:
    """Apaga los botones de una pantalla concreta por su ID."""
    if not mensaje_id:
        return
    try:
        mensaje = await canal.fetch_message(int(mensaje_id))
        await mensaje.edit(view=PantallaView(congelada=True))
    except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
        # Mensaje borrado o inalcanzable: no es motivo para romper el flujo.
        log.debug("No se pudo congelar la pantalla %s", mensaje_id, exc_info=True)


def _canal_anterior(canal: discord.abc.Messageable, criatura: sim.Criatura):
    """El canal donde quedó la pantalla anterior.

    Con el bot en varios canales, la pantalla vieja puede estar en otro sitio
    distinto de donde vamos a publicar la nueva. Si no la buscásemos ahí, se
    quedaría con los botones activos y habría dos pantallas vivas.
    """
    if not criatura.canal_id or str(getattr(canal, "id", "")) == criatura.canal_id:
        return canal
    guild = getattr(canal, "guild", None)
    if guild is None:
        return canal
    return guild.get_channel(int(criatura.canal_id)) or canal


async def responder_pantalla(
    interaccion: discord.Interaction, criatura: sim.Criatura, ahora
) -> None:
    """Publica la pantalla *como respuesta* a un comando.

    Se usa cuando la pantalla es lo que el comando devuelve, para no tener que
    acusar recibo con un mensaje privado vacío antes de enviarla.
    """
    if criatura.pantalla_msg_id:
        await congelar(_canal_anterior(interaccion.channel, criatura),
                       criatura.pantalla_msg_id)

    contenido = pantalla.render(
        criatura, ahora, esperas=db.esperas(criatura.id, ahora)
    )
    vista = PantallaView() if criatura.viva else None
    await interaccion.response.send_message(contenido, view=vista)
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

    contenido = pantalla.render(
        criatura, ahora, esperas=db.esperas(criatura.id, ahora), aviso=aviso
    )
    vista = PantallaView() if criatura.viva else None
    mensaje = await canal.send(contenido, view=vista)
    db.guardar_pantalla(criatura.id, str(mensaje.id), str(canal.id))
    return mensaje
