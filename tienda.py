"""La mochila y la tienda: comprar consumibles y usarlos.

Vive en la raíz y no en `cogs/` porque no aporta ningún comando de barra: son
vistas, como `vistas.py`, y desde allí se abren con los dos botones nuevos.

Todo va en respuestas efímeras —sólo las ve quien pulsa— para no llenar el canal
de menús. Las vistas de aquí, al contrario que `PantallaView`, no son
persistentes: se abren desde un botón, se usan y se van, así que no tienen que
sobrevivir a un reinicio.
"""
from __future__ import annotations

import logging
import random
from dataclasses import replace

import discord

import db
import economia
import objetos as obj
import simulacion as sim

log = logging.getLogger(__name__)

SEGUNDOS_DE_MENU = 120


def _saldos(usuario_id: str, guild_id: str) -> str:
    saldos = economia.saldos(usuario_id, guild_id)
    return (
        f"🪙 asciicoins para comprar: **{saldos.asciicoins}**\n"
        f"💎 asciigems en reserva: **{saldos.asciigems}**"
    )


def _saldo_de_compra(saldos: economia.Saldos) -> str:
    return f"🪙 **{saldos.asciicoins}** asciicoins"


def texto_de_la_tienda(usuario_id: str, guild_id: str) -> str:
    return (
        f"## {obj.EMOJI_MONEDA_TIENDA} Tienda\n"
        f"{_saldos(usuario_id, guild_id)}\n"
        "-# Elige abajo lo que quieras comprar."
    )


def lo_que_tiene(usuario_id: str, guild_id: str) -> dict[str, int]:
    """La mochila, sin lo que ya no esté en el catálogo.

    El filtro no es paranoia: si algún día se retira un objeto, quien lo tuviera
    guardado se quedaría con un menú que Discord rechaza por citar una opción
    que no existe.
    """
    return {
        clave: cuantos
        for clave, cuantos in db.inventario(usuario_id, guild_id).items()
        if clave in obj.CATALOGO
    }


def texto_del_inventario(usuario_id: str, guild_id: str) -> str:
    tengo = lo_que_tiene(usuario_id, guild_id)
    if not tengo:
        return (
            "## 🎒 Mochila\n"
            "No tienes nada todavía. Pulsa 🛒 **Tienda** para comprar.\n"
            f"-# {_saldos(usuario_id, guild_id)}"
        )
    lineas = "\n".join(
        f"{obj.CATALOGO[clave].emoji} **{obj.CATALOGO[clave].nombre}** ×{cuantos}"
        for clave, cuantos in sorted(tengo.items())
    )
    return (
        f"## 🎒 Mochila\n{lineas}\n"
        f"-# {_saldos(usuario_id, guild_id)}\n-# Elige abajo para usar."
    )


def texto_resultado_compra(
    resultado: economia.ResultadoCompra, objeto: obj.Objeto
) -> str:
    if resultado.replay:
        estado = "comprada" if resultado.comprada else "rechazada por saldo insuficiente"
        return f"{objeto.emoji} Compra ya procesada: **{objeto.nombre}** ({estado})."
    if not resultado:
        return (
            f"No te llega: **{objeto.nombre}** cuesta 🪙 {objeto.precio} "
            f"asciicoins y tienes {_saldo_de_compra(resultado.saldos)}."
        )
    return (
        f"{objeto.emoji} Comprado: **{objeto.nombre}**.\n"
        f"-# Te quedan {_saldo_de_compra(resultado.saldos)}. "
        "Úsalo desde 🎒 Mochila."
    )


# --- Usar un objeto --------------------------------------------------------

def usar(
    criatura: sim.Criatura,
    objeto: obj.Objeto,
    ahora,
    rng: random.Random | None = None,
) -> str:
    """Aplica el objeto y devuelve qué contar. La criatura ya se guarda aquí.

    Vive fuera de la vista para poder probarlo sin montar media API de Discord:
    es donde están las reglas de verdad de qué hace cada cosa.
    """
    if objeto.reinicia:
        db.quitar_cooldown(criatura.id, objeto.reinicia)
        return f"{objeto.emoji} **{criatura.nombre}** ya puede {objeto.reinicia}."

    if objeto.stat:
        bonus = obj.tirar_bonus(objeto, rng)
        db.poner_efecto(criatura.id, objeto.stat, bonus, ahora)
        return (
            f"{objeto.emoji} **{criatura.nombre}** gana **+{bonus} de "
            f"{objeto.stat}** durante {obj.MINUTOS_DE_EFECTO} minutos."
        )

    nueva = obj.aplicar_a_la_criatura(objeto, criatura)
    db.guardar(nueva)
    return f"{objeto.emoji} **{criatura.nombre}** se lo bebe de un trago. Hambre al 100."


def renombrar(
    usuario_id: str, guild_id: str, objeto: obj.Objeto, propuesto: str
) -> str:
    """Valida el nombre, gasta la placa y renombra. Devuelve qué contar.

    El orden importa y es el único que no deja agujeros: primero se valida, y
    sólo si el nombre vale se gasta el objeto. Al revés, un nombre con caracteres
    raros te costaría la placa sin cambiar nada.

    Levanta `ValueError` si el nombre no vale o si ya no queda ninguna placa.
    """
    nombre = sim.normalizar_nombre(propuesto)  # levanta ValueError si no vale

    criatura = db.criatura_activa(usuario_id, guild_id)
    if criatura is None:
        raise ValueError("Ya no tienes ningún gachamon activo.")
    if nombre == criatura.nombre:
        raise ValueError(f"Ya se llama **{nombre}**.")
    if not db.gastar(usuario_id, guild_id, objeto.clave):
        raise ValueError("Ya no te queda ninguna placa.")

    antes = criatura.nombre
    db.guardar(replace(criatura, nombre=nombre))
    return f"{objeto.emoji} **{antes}** pasa a llamarse **{nombre}**."


class RenombrarModal(discord.ui.Modal, title="Ponle otro nombre"):
    def __init__(self, objeto: obj.Objeto, nombre_actual: str):
        super().__init__()
        self.objeto = objeto
        self.nombre = discord.ui.TextInput(
            label="¿Cómo se va a llamar?",
            default=nombre_actual,
            placeholder="Pelusa",
            min_length=1,
        )
        self.add_item(self.nombre)

    async def on_submit(self, interaccion: discord.Interaction) -> None:
        try:
            aviso = renombrar(
                str(interaccion.user.id), str(interaccion.guild_id),
                self.objeto, str(self.nombre),
            )
        except ValueError as error:
            await interaccion.response.send_message(
                f"No se ha podido. {error}", ephemeral=True
            )
            return
        await interaccion.response.send_message(aviso, ephemeral=True)


# --- Los desplegables ------------------------------------------------------

class MenuInventario(discord.ui.Select):
    def __init__(self, tengo: dict[str, int]):
        opciones = [
            discord.SelectOption(
                label=f"{obj.CATALOGO[clave].nombre} ×{cuantos}",
                value=clave,
                description=obj.CATALOGO[clave].descripcion[:100],
                emoji=obj.CATALOGO[clave].emoji,
            )
            for clave, cuantos in sorted(tengo.items())
            if clave in obj.CATALOGO
        ]
        super().__init__(placeholder="¿Qué usas?", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)
        objeto = obj.CATALOGO[self.values[0]]

        criatura = db.criatura_activa(usuario_id, guild_id)
        if criatura is None:
            await interaccion.response.edit_message(
                content="No tienes ninguna criatura viva. Empieza con `/huevo`.",
                view=None,
            )
            return

        if objeto.renombra:
            # La placa se gasta al CONFIRMAR el nombre, no aquí: cerrar el
            # formulario sin escribir nada no puede costarte el objeto.
            await interaccion.response.send_modal(
                RenombrarModal(objeto, criatura.nombre)
            )
            return

        # Se gasta ANTES de aplicar: si fallara después, es preferible perder un
        # objeto que dejar que dos clics seguidos usen la misma unidad dos veces.
        if not db.gastar(usuario_id, guild_id, objeto.clave):
            await interaccion.response.edit_message(
                content="Ya no te queda ninguno.", view=None
            )
            return

        ahora = db.ahora_utc()
        criatura = sim.avanzar(criatura, ahora)
        db.guardar(criatura)
        aviso = usar(criatura, objeto, ahora)

        await interaccion.response.edit_message(content=aviso, view=None)


class MenuTienda(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(
                label=f"{objeto.nombre} — 🪙 {objeto.precio}",
                value=clave,
                description=objeto.descripcion[:100],
                emoji=objeto.emoji,
            )
            for clave, objeto in obj.CATALOGO.items()
        ]
        super().__init__(placeholder="¿Qué compras?", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)
        objeto = obj.CATALOGO[self.values[0]]

        resultado = economia.comprar(
            str(interaccion.id), usuario_id, guild_id, objeto
        )
        await interaccion.response.edit_message(
            content=texto_resultado_compra(resultado, objeto),
            view=None,
        )


class VistaConMenu(discord.ui.View):
    """Un desplegable suelto. Caduca solo: no tiene que sobrevivir a nada."""

    def __init__(self, menu: discord.ui.Select):
        super().__init__(timeout=SEGUNDOS_DE_MENU)
        self.add_item(menu)


async def abrir_inventario(interaccion: discord.Interaction) -> None:
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)
    tengo = lo_que_tiene(usuario_id, guild_id)

    await interaccion.response.send_message(
        texto_del_inventario(usuario_id, guild_id),
        view=VistaConMenu(MenuInventario(tengo)) if tengo else None,
        ephemeral=True,
    )


async def abrir_tienda(interaccion: discord.Interaction) -> None:
    await interaccion.response.send_message(
        texto_de_la_tienda(str(interaccion.user.id), str(interaccion.guild_id)),
        view=VistaConMenu(MenuTienda()),
        ephemeral=True,
    )
