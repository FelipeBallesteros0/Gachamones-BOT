"""Cambiar de gachamon activo.

Vive en la raíz por lo mismo que `tienda.py`: son vistas, no comandos de barra,
y desde `vistas.py` se abren con un botón. La respuesta es efímera —sólo la ve
quien pulsa— para no llenar el canal de menús.
"""
from __future__ import annotations

import logging

import discord

import db
import especies as esp
import pantalla
import simulacion as sim

log = logging.getLogger(__name__)

SEGUNDOS_DE_MENU = 120
EMOJI_INCUBADORA = "🥚"


def _como_esta(criatura: sim.Criatura) -> str:
    if criatura.activa:
        return "activo ahora"
    if sim.esta_sin_nombrar(criatura):
        return "esperando nombre"
    return "en la incubadora"


def _resumen(criatura: sim.Criatura) -> str:
    """`Pollito · adulto · nivel 3 · en la incubadora`, para la lista."""
    definicion = criatura.def_especie
    etapa = esp.nombre_etapa(criatura.etapa, criatura.genero)
    return (
        f"{definicion.nombre} · {etapa} · nivel {criatura.nivel} "
        f"· {_como_esta(criatura)}"
    )


def texto_del_plantel(plantel: list[sim.Criatura]) -> str:
    if not plantel:
        return "No tienes ningún gachamon. Empieza con `/huevo`."

    lineas = "\n".join(
        f"{'▶️' if c.activa else EMOJI_INCUBADORA} **{sim.nombre_visible(c)}** "
        f"{pantalla.EMOJI_GENERO[c.genero]} — {_resumen(c)}"
        for c in plantel
    )
    if len(plantel) == 1:
        cola = (
            "-# Es el único que tienes. Los demás se consiguen reclutándolos "
            "por ahí, no con `/huevo`."
        )
    else:
        cola = (
            "-# En la incubadora no les pasa el tiempo: ni comida, ni ánimo, "
            "ni aseo. Elige abajo cuál sacas."
        )
    return f"## 🧬 Tu plantel\n{lineas}\n{cola}"


class MenuPlantel(discord.ui.Select):
    def __init__(self, plantel: list[sim.Criatura], congelar=None, bautizar=None):
        opciones = [
            discord.SelectOption(
                label=sim.nombre_visible(criatura)[:100],
                value=str(criatura.id),
                description=_resumen(criatura)[:100],
                emoji=criatura.def_especie.emoji,
                default=criatura.activa,
            )
            for criatura in plantel
        ]
        super().__init__(placeholder="¿A cuál sacas?", options=opciones)
        self.congelar = congelar
        self.bautizar = bautizar
        self.plantel = plantel

    async def callback(self, interaccion: discord.Interaction) -> None:
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)
        elegido = int(self.values[0])
        ahora = db.ahora_utc()

        actual = db.criatura_activa(usuario_id, guild_id)
        if actual is not None and actual.id == elegido:
            await interaccion.response.edit_message(
                content=f"**{actual.nombre}** ya era el activo.", view=None
            )
            return

        # Elegir a un recluta sin bautizar no es un error del que quejarse: es
        # justo el momento de ponerle nombre. El formulario tiene que salir como
        # respuesta inmediata, así que va antes de cualquier otra respuesta.
        pendiente = next(
            (c for c in self.plantel
             if c.id == elegido and sim.esta_sin_nombrar(c)),
            None,
        )
        if pendiente is not None:
            if self.bautizar is not None:
                await self.bautizar(interaccion, pendiente)
            else:
                await interaccion.response.edit_message(
                    content="Ese gachamon no sale de la incubadora hasta que "
                            "le pongas nombre.",
                    view=None,
                )
            return

        # `activar` comprueba que sea tuyo: un identificador copiado de otro
        # mensaje no puede sacar la mascota de otra persona.
        if not db.activar(elegido, usuario_id, guild_id, ahora):
            await interaccion.response.edit_message(
                content="Ese gachamon no es tuyo o ya no está.", view=None
            )
            return

        nueva = db.criatura_activa(usuario_id, guild_id)
        if self.congelar is not None and actual is not None:
            await self.congelar(interaccion.channel, actual.pantalla_msg_id)
        await interaccion.response.edit_message(
            content=esp.concordar(
                f"🧬 Sale de la incubadora **{nueva.nombre}**. "
                "Mír{alo/ala} con `/mascota`.",
                nueva.genero,
            ),
            view=None,
        )


class VistaPlantel(discord.ui.View):
    def __init__(self, plantel: list[sim.Criatura], congelar=None, bautizar=None):
        super().__init__(timeout=SEGUNDOS_DE_MENU)
        self.add_item(MenuPlantel(plantel, congelar, bautizar))


async def abrir_plantel(
    interaccion: discord.Interaction, congelar=None, bautizar=None
) -> None:
    plantel = db.plantel(str(interaccion.user.id), str(interaccion.guild_id))
    # Con uno solo no hay nada que elegir: se enseña la lista y ya.
    hay_donde_elegir = len(plantel) > 1
    await interaccion.response.send_message(
        texto_del_plantel(plantel),
        view=VistaPlantel(plantel, congelar, bautizar) if hay_donde_elegir else None,
        ephemeral=True,
    )
