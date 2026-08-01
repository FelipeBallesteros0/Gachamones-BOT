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

import cosmeticos as cos
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
        "-# Los consumibles se usan desde 🎒 **Mochila**; los cosméticos se "
        "ponen desde 🎨 **Personalizar**."
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

    if objeto.alimenta:
        nueva = obj.aplicar_a_la_criatura(objeto, criatura)
        db.guardar(nueva)
        ganado = round(nueva.hambre - criatura.hambre)
        return (
            f"{objeto.emoji} **{criatura.nombre}** se come {objeto.nombre}. "
            f"Comida +{ganado} (ahora {round(nueva.hambre)})."
        )

    # Sin caso por descarte. Antes, todo lo que no era poción ni reinicio caía en
    # la rama de la comida y devolvía su mensaje escrito a mano: las golosinas se
    # gastaban, no hacían nada y decían «Hambre al 100». El próximo objeto que no
    # encajara heredaría la misma mentira, así que aquí se revienta en vez de
    # inventar. `MenuInventario` lo comprueba antes para no gastar la unidad.
    raise ValueError(f"{objeto.clave} no se aplica al momento desde la mochila")


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
    def __init__(self, objeto: obj.Objeto, nombre_actual: str, congelar=None):
        super().__init__()
        self.objeto = objeto
        self.congelar = congelar
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
        criatura = db.criatura_activa(
            str(interaccion.user.id), str(interaccion.guild_id)
        )
        mensaje_id = criatura.pantalla_msg_id if criatura is not None else None
        if self.congelar is not None:
            await self.congelar(interaccion.channel, mensaje_id)
        await interaccion.response.send_message(aviso, ephemeral=True)


# --- Los desplegables ------------------------------------------------------

class MenuInventario(discord.ui.Select):
    def __init__(self, tengo: dict[str, int], congelar=None):
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
        self.congelar = congelar

    async def callback(self, interaccion: discord.Interaction) -> None:
        usuario_id = str(interaccion.user.id)
        guild_id = str(interaccion.guild_id)
        objeto = obj.CATALOGO[self.values[0]]

        criatura = db.criatura_activa(usuario_id, guild_id)
        if criatura is None:
            await interaccion.response.edit_message(
                content="No tienes ningún gachamon vivo. Empieza con `/huevo`.",
                view=None,
            )
            return

        if objeto.renombra:
            # La placa se gasta al CONFIRMAR el nombre, no aquí: cerrar el
            # formulario sin escribir nada no puede costarte el objeto.
            await interaccion.response.send_modal(
                RenombrarModal(objeto, criatura.nombre, self.congelar)
            )
            return

        if not objeto.se_usa_en_mochila:
            # Antes de gastar nada: si no hace nada aquí, elegirlo no puede
            # costarte la unidad. Es lo que pasaba con las golosinas.
            await interaccion.response.edit_message(
                content=(
                    f"{objeto.emoji} **{objeto.nombre}** no se usa desde aquí. "
                    "Llévalas a una `/aventura`."
                ),
                view=None,
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

        if self.congelar is not None:
            await self.congelar(interaccion.channel, criatura.pantalla_msg_id)
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
        # Etiqueta y no pregunta, y con la moneda delante: comparte mensaje con
        # el de cosméticos, así que lo que hace falta es poder distinguirlos de
        # un vistazo. Los que van solos en su mensaje sí preguntan.
        super().__init__(placeholder="🪙 Consumibles", options=opciones)

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


# --- Los cosméticos ---------------------------------------------------------
#
# Se compran en la misma tienda que lo demás, pero en su propio desplegable: son
# 15 objetos y 23 cosméticos, y en una lista de Discord caben 25. Lo que se
# compra va a tu **ropero**, y ponérselo o quitárselo a un gachamon es otra
# pantalla, la de 🎨 Personalizar.

EMOJI_TIPO = {
    cos.TINTE: "🎨", cos.SOMBRERO: "👑", cos.MARCO: "🖼️", cos.TITULO: "📜",
}
NOMBRE_TIPO = {
    cos.TINTE: "Tinte", cos.SOMBRERO: "Sombrero",
    cos.MARCO: "Marco", cos.TITULO: "Título",
}


def _lo_que_lleva(criatura: sim.Criatura | None) -> str:
    if criatura is None:
        return "-# No tienes ningún gachamon activo."
    puestos = []
    for tipo in cos.TIPOS:
        cosmetico = cos.buscar(getattr(criatura, tipo))
        if cosmetico:
            puestos.append(f"{EMOJI_TIPO[tipo]} {cosmetico.nombre}")
    if not puestos:
        return f"-# **{sim.nombre_visible(criatura)}** no lleva nada puesto."
    return (
        f"-# **{sim.nombre_visible(criatura)}** lleva: " + " · ".join(puestos)
    )


def texto_de_personalizacion(usuario_id: str, guild_id: str) -> str:
    criatura = db.criatura_activa(usuario_id, guild_id)
    tengo = len(db.ropero(usuario_id, guild_id))
    if criatura is None:
        return "## 🎨 Personalizar\n-# No tienes ningún gachamon activo."
    if not tengo:
        return (
            f"## 🎨 Personalizar a {sim.nombre_visible(criatura)}\n"
            "Tu ropero está vacío. Cómprale algo en 🛒 **Tienda**.\n"
            f"-# {obj.EMOJI_GEMA} asciigems: "
            f"**{economia.saldos(usuario_id, guild_id).asciigems}**"
        )
    return (
        f"## 🎨 Personalizar a {sim.nombre_visible(criatura)}\n"
        f"{_lo_que_lleva(criatura)}\n"
        f"-# En tu ropero: **{tengo}** "
        f"{'pieza' if tengo == 1 else 'piezas'}. Lo que le quites vuelve ahí."
    )


def texto_resultado_compra_cosmetico(
    resultado: economia.ResultadoCosmetico, cosmetico: cos.Cosmetico
) -> str:
    if not resultado.ok:
        return f"❌ {resultado.problema}"

    linea = f"{EMOJI_TIPO[cosmetico.tipo]} Comprado: **{cosmetico.nombre}**."
    if resultado.criatura is not None:
        linea += (
            f" Se lo estrena **{sim.nombre_visible(resultado.criatura)}**."
        )
    else:
        linea += " Está en tu ropero."
    if resultado.sustituido is not None:
        linea += (
            f"\n-# Se le quita **{resultado.sustituido.nombre}**, que vuelve a "
            "tu ropero."
        )
    return (
        f"{linea}\n-# {obj.EMOJI_GEMA} -{cosmetico.precio} · "
        f"te quedan **{resultado.saldo}**."
    )


def texto_resultado_equipar(
    resultado: economia.ResultadoCosmetico, cosmetico: cos.Cosmetico
) -> str:
    if not resultado.ok:
        return f"❌ {resultado.problema}"
    linea = (
        f"{EMOJI_TIPO[cosmetico.tipo]} **{sim.nombre_visible(resultado.criatura)}** "
        f"lleva ahora **{cosmetico.nombre}**."
    )
    if resultado.sustituido is not None:
        linea += (
            f"\n-# **{resultado.sustituido.nombre}** vuelve a tu ropero."
        )
    return linea


def texto_resultado_quitar(resultado: economia.ResultadoCosmetico) -> str:
    if not resultado.ok:
        return f"❌ {resultado.problema}"
    return (
        f"🧺 **{sim.nombre_visible(resultado.criatura)}** se queda sin "
        f"**{resultado.sustituido.nombre}**.\n"
        "-# Sigue en tu ropero: se lo puedes volver a poner cuando quieras."
    )


class MenuCosmeticos(discord.ui.Select):
    """Los cosméticos de la tienda, en su propio desplegable.

    Caben los veintitrés en las 25 opciones que admite Discord, y por eso van
    aparte de los objetos: juntos serían 38 y no habría lista que los aguantara.
    Un test vigila el tope: el día que no quepan, hay que partirlo por tipos.
    """

    def __init__(self, tengo: frozenset[str] = frozenset()):
        opciones = [
            discord.SelectOption(
                label=(
                    f"{cosmetico.nombre} — ya lo tienes" if clave in tengo
                    else f"{cosmetico.nombre} — 💎 {cosmetico.precio}"
                ),
                value=clave,
                description=NOMBRE_TIPO[cosmetico.tipo],
                emoji=EMOJI_TIPO[cosmetico.tipo],
            )
            for clave, cosmetico in cos.CATALOGO.items()
        ]
        super().__init__(placeholder="💎 Cosméticos", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        cosmetico = cos.CATALOGO[self.values[0]]
        resultado = economia.comprar_cosmetico(
            str(interaccion.user.id), str(interaccion.guild_id), cosmetico
        )
        await interaccion.response.edit_message(
            content=texto_resultado_compra_cosmetico(resultado, cosmetico),
            view=None,
        )


class MenuPonerCosmetico(discord.ui.Select):
    """Lo que tienes en el ropero, para ponérselo al activo."""

    def __init__(self, tengo: frozenset[str], refrescar=None):
        self.refrescar = refrescar
        opciones = [
            discord.SelectOption(
                label=cosmetico.nombre,
                value=clave,
                description=NOMBRE_TIPO[cosmetico.tipo],
                emoji=EMOJI_TIPO[cosmetico.tipo],
            )
            for clave, cosmetico in cos.CATALOGO.items()
            if clave in tengo
        ]
        super().__init__(placeholder="Ponerle…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        cosmetico = cos.CATALOGO[self.values[0]]
        resultado = economia.equipar_cosmetico(
            str(interaccion.user.id), str(interaccion.guild_id), cosmetico
        )
        await _contestar(
            interaccion, texto_resultado_equipar(resultado, cosmetico),
            resultado, self.refrescar,
        )


class MenuQuitarCosmetico(discord.ui.Select):
    """Sólo lo que lleva puesto, que no pueden ser más de cuatro cosas.

    Van en su propio desplegable y no mezclados con los de poner justamente por
    eso: así ninguna de las dos listas depende de lo grande que sea el catálogo.
    """

    def __init__(self, criatura: sim.Criatura, refrescar=None):
        self.refrescar = refrescar
        opciones = []
        for tipo in cos.TIPOS:
            cosmetico = cos.buscar(getattr(criatura, tipo))
            if cosmetico is not None:
                opciones.append(discord.SelectOption(
                    label=f"Quitar {cosmetico.nombre}",
                    value=tipo,
                    description=NOMBRE_TIPO[tipo],
                    emoji=EMOJI_TIPO[tipo],
                ))
        super().__init__(placeholder="Quitarle…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        resultado = economia.quitar_cosmetico(
            str(interaccion.user.id), str(interaccion.guild_id), self.values[0]
        )
        await _contestar(
            interaccion, texto_resultado_quitar(resultado), resultado,
            self.refrescar,
        )


async def _contestar(
    interaccion: discord.Interaction,
    aviso: str,
    resultado: economia.ResultadoCosmetico,
    refrescar,
) -> None:
    """Contesta y, si el gachamon ha cambiado de aspecto, republica su ficha."""
    await interaccion.response.edit_message(content=aviso, view=None)
    if resultado.ok and refrescar is not None:
        await refrescar(interaccion, resultado.criatura)


class VistaConMenu(discord.ui.View):
    """Uno o varios desplegables sueltos. Caduca solo: no sobrevive a nada.

    Discord admite cinco filas por mensaje y un desplegable ocupa una entera, así
    que aquí caben cinco. La tienda usa dos y la personalización otros dos.
    """

    def __init__(self, *menus: discord.ui.Select):
        super().__init__(timeout=SEGUNDOS_DE_MENU)
        for menu in menus:
            self.add_item(menu)


async def abrir_inventario(interaccion: discord.Interaction, congelar=None) -> None:
    usuario_id = str(interaccion.user.id)
    guild_id = str(interaccion.guild_id)
    tengo = lo_que_tiene(usuario_id, guild_id)

    await interaccion.response.send_message(
        texto_del_inventario(usuario_id, guild_id),
        view=VistaConMenu(MenuInventario(tengo, congelar)) if tengo else None,
        ephemeral=True,
    )


async def abrir_tienda(interaccion: discord.Interaction) -> None:
    """Todo lo que se compra, en un solo sitio y con sus dos monedas."""
    usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
    await interaccion.response.send_message(
        texto_de_la_tienda(usuario_id, guild_id),
        view=VistaConMenu(
            MenuTienda(), MenuCosmeticos(db.ropero(usuario_id, guild_id))
        ),
        ephemeral=True,
    )


async def abrir_personalizacion(
    interaccion: discord.Interaction, refrescar=None
) -> None:
    """Poner y quitar lo que ya tienes. Aquí no se cobra nada."""
    usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
    criatura = db.criatura_activa(usuario_id, guild_id)
    tengo = db.ropero(usuario_id, guild_id)

    menus: list[discord.ui.Select] = []
    if criatura is not None:
        if tengo:
            menus.append(MenuPonerCosmetico(tengo, refrescar))
        if any(getattr(criatura, tipo) for tipo in cos.TIPOS):
            menus.append(MenuQuitarCosmetico(criatura, refrescar))

    await interaccion.response.send_message(
        texto_de_personalizacion(usuario_id, guild_id),
        view=VistaConMenu(*menus) if menus else None,
        ephemeral=True,
    )
