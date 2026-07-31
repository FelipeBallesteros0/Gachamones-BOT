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

import db
import economia
import equipo
import pantalla
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
    if dueño is None or dueño.usuario_id == str(interaccion.user.id):
        return False
    await interaccion.response.send_message(
        f"Ese es el gachamon de <@{dueño.usuario_id}>. "
        "Saca el tuyo con `/mascota`.",
        ephemeral=True,
    )
    return True


class PantallaView(discord.ui.View):
    """Los botones bajo la pantalla.

    Cinco de cuidado arriba, y abajo mochila, tienda y cambio de gachamon. Son
    ocho y Discord admite cinco por fila, así que van en dos: los de cuidar
    actúan sobre la criatura, los de abajo abren menús y no la tocan.
    """

    def __init__(self, congelada: bool = False):
        super().__init__(timeout=None)
        if congelada:
            for hijo in self.children:
                if isinstance(hijo, discord.ui.Button):
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

    # Estos tres no gastan enfriamiento ni tocan a la criatura por sí solos:
    # abren un menú que sólo ve quien pulsa, así que ni congelan la pantalla ni
    # publican una nueva. Pero sí piden que la ficha sea tuya, como los demás:
    # abren tus cosas, y usarlas desde la ficha de otro te haría beberte una
    # poción o cambiar de plantel mirando a un gachamon que no es el tuyo.
    @discord.ui.button(label="Mochila", emoji="🎒", row=1,
                       style=discord.ButtonStyle.secondary, custom_id="tama:inventario")
    async def abrir_mochila(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        if await _es_de_otro(interaccion):
            return
        await tienda.abrir_inventario(interaccion, congelar)

    @discord.ui.button(label="Tienda", emoji="🛒", row=1,
                       style=discord.ButtonStyle.success, custom_id="tama:tienda")
    async def abrir_tienda(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        if await _es_de_otro(interaccion):
            return
        await tienda.abrir_tienda(interaccion)

    @discord.ui.button(label="Cambiar", emoji="🧬", row=1,
                       style=discord.ButtonStyle.primary, custom_id="tama:plantel")
    async def cambiar_activo(self, interaccion: discord.Interaction, boton: discord.ui.Button):
        if await _es_de_otro(interaccion):
            return
        await equipo.abrir_plantel(interaccion, congelar, bautizar)


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
            criatura = sim.avanzar(criatura, ahora)
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


async def _ejecutar(interaccion: discord.Interaction, accion: str) -> None:
    ahora = db.ahora_utc()
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)

    # Si la pantalla pulsada es de otra persona, no dejamos que actúe sobre la
    # suya por error: sería desconcertante ver aparecer otra criatura.
    dueño = db.criatura_por_pantalla(str(_mensaje_de(interaccion).id))
    if dueño and dueño.usuario_id != usuario_id:
        await interaccion.response.send_message(
            f"Ese es el gachamon de <@{dueño.usuario_id}>. "
            "Saca el tuyo con `/mascota` o `/huevo`.",
            ephemeral=True,
        )
        return
    if dueño and dueño.viva and not dueño.activa:
        await interaccion.response.send_message(
            "Ese gachamon está en la incubadora. Cambia el activo para cuidarlo.",
            ephemeral=True,
        )
        return
    if accion == sim.ACTUALIZAR and (
        dueño is None or not dueño.viva or not dueño.activa
    ):
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
        contenido = pantalla.render(
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
        await interaccion.response.edit_message(content=contenido, view=vista)
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
        if resultado.ok and not resultado.marca:
            mensaje += "\n-# No le deja marca."
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
    if not resultado.marca:
        aviso += "\n-# No le deja marca."
    if resultado.usados or resultado.topada or resultado.evoluciono:
        aviso += f"\n{texto_recibo_cuidado(resultado, accion)}"
    await publicar_pantalla(
        canal, resultado.criatura, ahora,
        aviso=aviso, ya_congelada=str(_mensaje_de(interaccion).id),
    )


def _efecto_recibo_cuidado(
    resultado: economia.ResultadoCuidado, accion: str,
) -> tuple[str, ...]:
    xp = f"+{sim.XP_POR_CUIDADO[accion]} XP"
    if accion == sim.ALIMENTAR:
        return (
            "🍖 Alimentar",
            f"comida {resultado.criatura.hambre:g}",
            f"ánimo {resultado.criatura.animo:g}",
            xp,
        )

    efecto = sim.EFECTOS_CUIDADO[accion]
    if accion == sim.JUGAR:
        return (
            "🪀 Jugar",
            f"ánimo {resultado.criatura.animo:g}",
            f"velocidad +{efecto['ent_velocidad']:g} entrenamiento",
            xp,
            f"coste base {efecto['hambre']:g} comida",
        )
    if accion == sim.ENTRENAR:
        return (
            "🏋️ Entrenar",
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
    cap = f"cuidado {resultado.usados}/{resultado.limite} UTC"
    if resultado.topada:
        cap += " (tope)"
    partes = [
        *_efecto_recibo_cuidado(resultado, accion),
        f"🪙 +{recompensa} asciicoins",
        cap,
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

    contenido = pantalla.render(
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
        await interaccion.response.send_message(contenido, view=PantallaView())
    else:
        await interaccion.response.send_message(contenido)
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
        mensaje = await canal.send(contenido, view=PantallaView())
    else:
        mensaje = await canal.send(contenido)
    db.guardar_pantalla(criatura.id, str(mensaje.id), str(getattr(canal, "id")))
    return mensaje
