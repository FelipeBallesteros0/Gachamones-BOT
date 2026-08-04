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

import casas as cas
import cosmeticos as cos
import db
import economia
import huerto as hue
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
        "-# Los consumibles se usan desde 🎒 **Mochila** y los cosméticos se "
        "ponen desde 🎨 **Personalizar**. La casa y los muebles, con `/casa`."
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

    if objeto.es_sopaipilla:
        caras = hue.caras_de(criatura.caracter, objeto.color)
        gusto = hue.le_gusta(criatura.caracter, objeto.color)
        # Un solo dado para las dos estadísticas: es un plato, no dos pociones.
        bonus = (rng or random.Random()).randint(1, caras)
        for stat in ("fuerza", "velocidad"):
            db.poner_efecto(criatura.id, stat, bonus, ahora)
        return (
            f"{objeto.emoji} **{criatura.nombre}** se come una sopaipilla "
            f"{objeto.color} — {gusto}.\n"
            f"-# **+{bonus}** de fuerza y de velocidad (1d{caras}) durante "
            f"{obj.MINUTOS_DE_EFECTO} minutos."
        )

    if objeto.dias_de_refugio:
        hasta = db.alargar_el_refugio(
            criatura.usuario_id, criatura.guild_id, objeto.dias_de_refugio, ahora
        )
        return (
            f"{objeto.emoji} Otra estancia en el refugio, hasta el "
            f"**{hasta:%d/%m}**.\n-# Cuenta desde ahora: si te sobraba tiempo, "
            "lo has perdido."
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
        criatura = db.avanzar(criatura, ahora)
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
            # Sólo lo que está a la venta: los porotos y las sopaipillas viven
            # en el catálogo porque van a la mochila y se regalan, pero no se
            # compran, y además no cabrían en las 25 opciones de un desplegable.
            for clave, objeto in obj.CATALOGO.items() if objeto.se_vende
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
    estilo = (
        "Imagen"
        if db.estilo_de_ficha(usuario_id, guild_id) == "imagen"
        else "ASCII clásico"
    )
    if not tengo:
        return (
            f"## 🎨 Personalizar a {sim.nombre_visible(criatura)}\n"
            f"Estilo de ficha: **{estilo}**\n"
            "Tu ropero está vacío. Cómprale algo en 🛒 **Tienda**.\n"
            f"-# {obj.EMOJI_GEMA} asciigems: "
            f"**{economia.saldos(usuario_id, guild_id).asciigems}**"
        )
    return (
        f"## 🎨 Personalizar a {sim.nombre_visible(criatura)}\n"
        f"Estilo de ficha: **{estilo}**\n"
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


# --- Las casas --------------------------------------------------------------

def texto_de_la_mudanza(nombre: str, resultado: economia.ResultadoMudanza) -> str:
    """Lo que se canta en el canal al mudarse. Público a propósito: es la clase
    de cosa que se presume."""
    desde = resultado.desde.nombre if resultado.desde else "del refugio"
    de_donde = f"de {desde}" if resultado.desde else desde
    return (
        f"🏠 **{nombre}** se trasladó {de_donde} a su nueva "
        f"**{resultado.casa.nombre}**.\n"
        f"-# Comodidad {resultado.casa.comodidad} · "
        f"{resultado.casa.huecos} huecos de mobiliario · "
        f"🪙 -{resultado.casa.precio}, le quedan **{resultado.saldo}**."
    )


VENDER = "vender"


def texto_de_la_venta(hogar: cas.Hogar, mobiliario: dict[str, bool]) -> str:
    """Lo que te darían y lo que pierdes, antes de confirmar."""
    casa = hogar.casa
    puestos = sum(1 for dentro in mobiliario.values() if dentro)
    aviso = (
        f"## 🏷️ ¿Vender {casa.nombre}?\n"
        f"Te dan **{cas.lo_que_dan_por(casa)}** 🪙 — el "
        f"{cas.PORCENTAJE_DE_REVENTA} % de los {casa.precio} que costó.\n"
        f"-# Vuelves al refugio con los {cas.DIAS_DE_REFUGIO} días enteros."
    )
    if puestos:
        aviso += (
            f"\n-# Tus **{puestos}** muebles se guardan: no se pierde ninguno."
        )
    aviso += "\n-# ⚠️ **Lo que tengas plantado en el huerto se pierde.**"
    return aviso


class ConfirmarVenta(discord.ui.View):
    """El segundo clic. Se pierde el 20 % y el huerto, así que no puede pasar
    por un resbalón sobre un desplegable."""

    def __init__(self):
        super().__init__(timeout=SEGUNDOS_DE_MENU)

    @discord.ui.button(label="Vender", emoji="🏷️",
                       style=discord.ButtonStyle.danger)
    async def vender(self, interaccion: discord.Interaction, boton) -> None:
        resultado = economia.vender_casa(
            str(interaccion.user.id), str(interaccion.guild_id)
        )
        if not resultado.ok:
            await interaccion.response.edit_message(
                content=f"❌ {resultado.problema}", view=None
            )
            return

        aviso = (
            f"🏷️ Vendida **{resultado.casa.nombre}** por "
            f"**{resultado.cobrado}** 🪙. Te quedan **{resultado.saldo}**.\n"
            f"-# De vuelta al refugio. Cómprate otra cuando quieras: con la casa "
            "vendida puedes elegir cualquier tamaño."
        )
        if resultado.guardados:
            aviso += f"\n-# **{resultado.guardados}** muebles esperando en tu armario."
        await interaccion.response.edit_message(content=aviso, view=None)


class MenuCasas(discord.ui.Select):
    """Las tres casas. Marca la tuya y las que se te han quedado pequeñas."""

    def __init__(self, hogar: cas.Hogar | None = None):
        tuya = hogar.casa if hogar else None
        opciones = []
        if tuya is not None:
            # Primera, y no perdida entre las tres: es lo único distinto que
            # puede hacer aquí quien ya tiene casa.
            opciones.append(discord.SelectOption(
                label=f"Vender {tuya.nombre} — 🪙 +{cas.lo_que_dan_por(tuya)}",
                value=VENDER,
                description=f"El {cas.PORCENTAJE_DE_REVENTA} % de lo que costó",
                emoji="🏷️",
            ))
        for clave, casa in cas.CATALOGO.items():
            if tuya is not None and casa.tamano < tuya.tamano:
                etiqueta = f"{casa.nombre} — se te quedó pequeña"
            elif tuya is not None and casa.tamano == tuya.tamano:
                etiqueta = f"{casa.nombre} — aquí vives"
            else:
                etiqueta = f"{casa.nombre} — 🪙 {casa.precio}"
            opciones.append(discord.SelectOption(
                label=etiqueta,
                value=clave,
                description=(
                    f"Comodidad {casa.comodidad}, hasta {casa.techo} · "
                    f"{casa.huecos} muebles"
                ),
                emoji="🏠",
            ))
        super().__init__(placeholder="🏠 Casas", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
        if self.values[0] == VENDER:
            # Elegir vender **no vende**: enseña la cuenta y pide el segundo
            # clic. Lo que se pierde no se recupera comprando otra vez.
            ahora = db.ahora_utc()
            await interaccion.response.edit_message(
                content=texto_de_la_venta(
                    db.hogar_leido(usuario_id, guild_id, ahora),
                    db.mobiliario(usuario_id, guild_id),
                ),
                view=ConfirmarVenta(),
            )
            return

        casa = cas.CATALOGO[self.values[0]]
        resultado = economia.comprar_casa(usuario_id, guild_id, casa)
        if not resultado.ok:
            await interaccion.response.edit_message(
                content=f"❌ {resultado.problema}", view=None
            )
            return

        await interaccion.response.edit_message(
            content=f"🏠 Te has mudado a **{casa.nombre}**. Míralo con `/casa`.",
            view=None,
        )
        # El anuncio va al canal y después de que cierre la transacción: mudarse
        # se presume, y una mudanza cantada que luego no estuviera sería peor
        # que una que tarda un segundo en salir.
        if interaccion.channel is not None:
            await interaccion.channel.send(
                texto_de_la_mudanza(interaccion.user.display_name, resultado)
            )


# --- El mobiliario ----------------------------------------------------------

def texto_resultado_mueble(resultado: economia.ResultadoMueble) -> str:
    if not resultado.ok:
        return f"❌ {resultado.problema}"
    mueble, casa = resultado.mueble, resultado.casa
    return (
        f"{mueble.emoji} **{mueble.nombre}** · "
        f"comodidad **{resultado.comodidad}**/{casa.techo} · "
        f"{resultado.puestos}/{casa.huecos} huecos"
    )


def _lo_que_hay_dentro(mobiliario: dict[str, bool]) -> str:
    dentro = [cas.MUEBLES[c] for c, puesto in mobiliario.items()
              if puesto and c in cas.MUEBLES]
    if not dentro:
        return "-# La casa está vacía."
    return "-# Dentro: " + " · ".join(
        f"{m.emoji} {m.nombre} +{m.comodidad}" for m in dentro
    )


class MenuMuebles(discord.ui.Select):
    """Los muebles de la tienda. Marca los que ya tienes."""

    def __init__(self, mobiliario: dict[str, bool] | None = None):
        tengo = mobiliario or {}
        opciones = [
            discord.SelectOption(
                label=(
                    f"{mueble.nombre} — ya lo tienes" if clave in tengo
                    else f"{mueble.nombre} — 🪙 {mueble.precio}"
                ),
                value=clave,
                description=f"Comodidad +{mueble.comodidad}",
                emoji=mueble.emoji,
            )
            for clave, mueble in cas.MUEBLES.items()
        ]
        super().__init__(placeholder="🪑 Mobiliario", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        mueble = cas.MUEBLES[self.values[0]]
        resultado = economia.comprar_mueble(
            str(interaccion.user.id), str(interaccion.guild_id), mueble
        )
        aviso = texto_resultado_mueble(resultado)
        if resultado.ok:
            sitio = "Puesto ya" if resultado.puestos else "Guardado"
            aviso = (
                f"🪙 Comprado. {aviso}\n"
                f"-# {sitio}. Se coloca y se retira desde 🪑 **Amueblar**, "
                "en `/casa`."
            )
        await interaccion.response.edit_message(content=aviso, view=None)


class MenuColocarMueble(discord.ui.Select):
    """Lo que tienes guardado, para meterlo en la casa."""

    def __init__(self, mobiliario: dict[str, bool]):
        opciones = [
            discord.SelectOption(
                label=f"{cas.MUEBLES[clave].nombre} +{cas.MUEBLES[clave].comodidad}",
                value=clave,
                emoji=cas.MUEBLES[clave].emoji,
            )
            for clave, puesto in mobiliario.items()
            if not puesto and clave in cas.MUEBLES
        ]
        super().__init__(placeholder="Colocar…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        mueble = cas.MUEBLES[self.values[0]]
        resultado = economia.colocar_mueble(
            str(interaccion.user.id), str(interaccion.guild_id), mueble
        )
        await interaccion.response.edit_message(
            content=texto_resultado_mueble(resultado), view=None
        )


class MenuRetirarMueble(discord.ui.Select):
    """Lo que está puesto, para sacarlo. Se guarda, no se pierde."""

    def __init__(self, mobiliario: dict[str, bool]):
        opciones = [
            discord.SelectOption(
                label=f"Retirar {cas.MUEBLES[clave].nombre}",
                value=clave,
                emoji=cas.MUEBLES[clave].emoji,
            )
            for clave, puesto in mobiliario.items()
            if puesto and clave in cas.MUEBLES
        ]
        super().__init__(placeholder="Retirar…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        mueble = cas.MUEBLES[self.values[0]]
        resultado = economia.retirar_mueble(
            str(interaccion.user.id), str(interaccion.guild_id), mueble
        )
        await interaccion.response.edit_message(
            content=texto_resultado_mueble(resultado), view=None
        )


def texto_de_amueblar(usuario_id: str, guild_id: str, ahora) -> str:
    hogar = db.hogar_de(usuario_id, guild_id, ahora)
    mobiliario = db.mobiliario(usuario_id, guild_id)
    if hogar.casa is None:
        return (
            "## 🪑 Amueblar\n-# El refugio no se puede amueblar: es de todos. "
            "Cómprate una casa en 🛒 **Tienda**."
        )
    dentro = [c for c, puesto in mobiliario.items() if puesto]
    guardados = len(mobiliario) - len(dentro)
    return (
        f"## 🪑 Amueblar {hogar.casa.nombre}\n"
        f"Comodidad **{cas.comodidad_de(hogar.casa, dentro)}**"
        f"/{hogar.casa.techo} · {len(dentro)}/{hogar.casa.huecos} huecos\n"
        f"{_lo_que_hay_dentro(mobiliario)}\n"
        f"-# Guardados: **{guardados}**. Lo que retires se guarda, no se pierde."
    )


async def abrir_amueblar(interaccion: discord.Interaction) -> None:
    usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
    ahora = db.ahora_utc()
    mobiliario = db.mobiliario(usuario_id, guild_id)
    hay_casa = db.hogar_de(usuario_id, guild_id, ahora).casa is not None

    menus: list[discord.ui.Select] = []
    if hay_casa:
        if any(not puesto for puesto in mobiliario.values()):
            menus.append(MenuColocarMueble(mobiliario))
        if any(mobiliario.values()):
            menus.append(MenuRetirarMueble(mobiliario))

    await interaccion.response.send_message(
        texto_de_amueblar(usuario_id, guild_id, ahora),
        view=VistaConMenu(*menus) if menus else None,
        ephemeral=True,
    )


# --- El buzón ---------------------------------------------------------------

def texto_del_buzon(usuario_id: str, guild_id: str) -> str:
    regalos = db.buzon_de(usuario_id, guild_id)
    if not regalos:
        return (
            "## 📬 Buzón\nNo te espera nada.\n"
            "-# Los regalos llegan cuando alguien te visita con `/visitar`."
        )
    lineas = "\n".join(_linea_de_regalo(r) for r in regalos)
    return (
        f"## 📬 Buzón\n{lineas}\n"
        f"-# **{len(regalos)}** sin recoger. Elige abajo para quedártelo."
    )


def _linea_de_regalo(regalo: db.Regalo) -> str:
    objeto = obj.CATALOGO.get(regalo.objeto)
    nombre = objeto.nombre if objeto else regalo.objeto
    emoji = objeto.emoji if objeto else "🎁"
    linea = f"{emoji} **{nombre}** — de {regalo.de_nombre}"
    if regalo.nota:
        linea += f"\n-# ✉️ «{regalo.nota}»"
    return linea


class MenuBuzon(discord.ui.Select):
    def __init__(self, regalos: list[db.Regalo]):
        opciones = [
            discord.SelectOption(
                label=(
                    obj.CATALOGO[r.objeto].nombre if r.objeto in obj.CATALOGO
                    else r.objeto
                )[:100],
                value=str(r.id),
                description=f"de {r.de_nombre}"[:100],
                emoji=obj.CATALOGO[r.objeto].emoji if r.objeto in obj.CATALOGO else "🎁",
            )
            # Veinticinco es el tope de Discord; con más, se recogen por tandas.
            for r in regalos[:25]
        ]
        super().__init__(placeholder="Recoger…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        regalo = db.recoger_del_buzon(
            str(interaccion.user.id), str(interaccion.guild_id),
            int(self.values[0]),
        )
        if regalo is None:
            aviso = "❌ Ese regalo ya no está en el buzón."
        else:
            aviso = (
                f"🎁 Recogido: {_linea_de_regalo(regalo)}\n"
                "-# Ya está en tu 🎒 **Mochila**."
            )
        await interaccion.response.edit_message(content=aviso, view=None)


async def abrir_buzon(interaccion: discord.Interaction) -> None:
    usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
    regalos = db.buzon_de(usuario_id, guild_id)
    await interaccion.response.send_message(
        texto_del_buzon(usuario_id, guild_id),
        view=VistaConMenu(MenuBuzon(regalos)) if regalos else None,
        ephemeral=True,
    )


class NotaModal(discord.ui.Modal, title="Deja una nota"):
    """La nota es opcional: se puede mandar el regalo dejándola en blanco."""

    def __init__(self, para_id: str, para_nombre: str, objeto: obj.Objeto):
        super().__init__()
        self.para_id = para_id
        self.para_nombre = para_nombre
        self.objeto = objeto
        self.nota = discord.ui.TextInput(
            label="Nota (opcional)",
            placeholder="Para que se lo des a tu Pyro.",
            required=False,
            max_length=db.LARGO_MAXIMO_NOTA,
        )
        self.add_item(self.nota)

    async def on_submit(self, interaccion: discord.Interaction) -> None:
        mandado = db.mandar_regalo(
            str(interaccion.user.id), interaccion.user.display_name,
            self.para_id, str(interaccion.guild_id), self.objeto.clave,
            str(self.nota), db.ahora_utc(),
        )
        if not mandado:
            await interaccion.response.send_message(
                f"❌ Ya no te queda ningún **{self.objeto.nombre}**.",
                ephemeral=True,
            )
            return
        await interaccion.response.send_message(
            f"🎁 {self.objeto.emoji} **{self.objeto.nombre}** va camino del "
            f"buzón de **{self.para_nombre}**.",
            ephemeral=True,
        )


class MenuRegalar(discord.ui.Select):
    """Lo que llevas en la mochila, para dejarlo en el buzón de quien visitas."""

    def __init__(self, tengo: dict[str, int], para_id: str, para_nombre: str):
        self.para_id = para_id
        self.para_nombre = para_nombre
        opciones = [
            discord.SelectOption(
                label=f"{obj.CATALOGO[clave].nombre} ×{cuantos}",
                value=clave,
                emoji=obj.CATALOGO[clave].emoji,
            )
            for clave, cuantos in sorted(tengo.items())
        ][:25]
        super().__init__(placeholder="¿Qué le dejas?", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        await interaccion.response.send_modal(
            NotaModal(self.para_id, self.para_nombre, obj.CATALOGO[self.values[0]])
        )


async def abrir_regalo(
    interaccion: discord.Interaction, para_id: str, para_nombre: str
) -> None:
    tengo = lo_que_tiene(str(interaccion.user.id), str(interaccion.guild_id))
    if not tengo:
        await interaccion.response.send_message(
            "No llevas nada que regalar. Compra algo en 🛒 **Tienda**.",
            ephemeral=True,
        )
        return
    await interaccion.response.send_message(
        f"## 🎁 Un regalo para {para_nombre}\n"
        "-# Sale de tu mochila y le espera en su buzón. Puedes dejarle una nota.",
        view=VistaConMenu(MenuRegalar(tengo, para_id, para_nombre)),
        ephemeral=True,
    )


# --- El huerto --------------------------------------------------------------

def _cuando(bancal: hue.Bancal, ahora) -> str:
    faltan = bancal.listo_en() - ahora
    horas = faltan.total_seconds() / 3600
    if horas <= 0:
        return "listo para cosechar"
    if horas < 1:
        return f"le faltan {int(faltan.total_seconds() // 60)} min"
    return f"le faltan {horas:.0f} h"


def texto_del_huerto(usuario_id: str, guild_id: str, ahora) -> str:
    hogar = db.hogar_leido(usuario_id, guild_id, ahora)
    cuantos = hue.bancales_de(hogar.casa.clave if hogar.casa else None)
    if not cuantos:
        return (
            "## 🌱 Huerto\n-# El refugio no tiene huerto. Cómprate una casa en "
            "🛒 **Tienda**."
        )

    lineas = []
    for bancal in db.huerto_de(usuario_id, guild_id, cuantos):
        if not bancal.plantado:
            lineas.append(f"`{bancal.numero}` 🟫 en barbecho")
        elif bancal.listo(ahora):
            lineas.append(f"`{bancal.numero}` 🌾 **listo para cosechar**")
        else:
            regado = " · regado" if bancal.regado else ""
            lineas.append(f"`{bancal.numero}` 🌱 {_cuando(bancal, ahora)}{regado}")

    semillas = db.inventario(usuario_id, guild_id).get("semilla", 0)
    return (
        f"## 🌱 Huerto de {hogar.casa.nombre}\n" + "\n".join(lineas) +
        f"\n-# Semillas: **{semillas}** · tarda {hue.HORAS_DE_CULTIVO} h, "
        f"o {hue.HORAS_DE_CULTIVO - hue.HORAS_QUE_AHORRA_REGAR} h si lo riegas.\n"
        f"-# Sale un poroto de color al azar. Con "
        f"{hue.POROTOS_POR_SOPAIPILLA} del mismo color se cocina una sopaipilla."
    )


def texto_resultado_huerto(resultado: economia.ResultadoHuerto, ahora) -> str:
    if not resultado.ok:
        return f"❌ {resultado.problema}"
    if resultado.cosechado:
        poroto = obj.CATALOGO[resultado.cosechado]
        return (
            f"{poroto.emoji} Ha salido un **{poroto.nombre}**.\n"
            "-# Ya está en tu 🎒 **Mochila**. El bancal queda libre."
        )
    faltan = hue.Bancal(resultado.bancal)
    espera = _cuando(
        hue.Bancal(resultado.bancal, ahora,
                   regado=resultado.listo_en != faltan.listo_en()),
        ahora,
    )
    return f"🌱 Bancal `{resultado.bancal}`: {espera}."


class MenuHuerto(discord.ui.Select):
    """Un solo desplegable: cada bancal ofrece lo que toca ahora mismo.

    Plantar, regar y cosechar en tres menús sería el mismo bancal escrito tres
    veces; así cada renglón dice lo único que se puede hacer con él.
    """

    def __init__(self, bancales: list[hue.Bancal], ahora):
        self.ahora = ahora
        opciones = []
        for bancal in bancales:
            if not bancal.plantado:
                accion, etiqueta, emoji = "plantar", "Plantar", "🌱"
            elif bancal.listo(ahora):
                accion, etiqueta, emoji = "cosechar", "Cosechar", "🌾"
            elif bancal.puede_regarse(ahora):
                accion, etiqueta, emoji = "regar", "Regar", "💧"
            else:
                continue                    # regado y creciendo: nada que hacer
            opciones.append(discord.SelectOption(
                label=f"{etiqueta} el bancal {bancal.numero}",
                value=f"{accion}:{bancal.numero}",
                emoji=emoji,
            ))
        super().__init__(placeholder="El huerto…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        accion, numero = self.values[0].split(":")
        usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
        ahora = db.ahora_utc()
        hacer = {
            "plantar": economia.plantar,
            "regar": economia.regar,
            "cosechar": economia.cosechar,
        }[accion]
        resultado = hacer(usuario_id, guild_id, int(numero), ahora)
        await interaccion.response.edit_message(
            content=texto_resultado_huerto(resultado, ahora), view=None
        )


class MenuCocina(discord.ui.Select):
    """Los colores de los que te llegan porotos para cocinar."""

    def __init__(self, mochila: dict[str, int]):
        opciones = []
        for color in hue.COLORES:
            cuantos = mochila.get(hue.clave_de_poroto(color), 0)
            if cuantos < hue.POROTOS_POR_SOPAIPILLA:
                continue
            opciones.append(discord.SelectOption(
                label=f"Sopaipilla {color}",
                value=color,
                description=f"gasta {hue.POROTOS_POR_SOPAIPILLA} de {cuantos}",
                emoji=hue.EMOJI_COLOR[color],
            ))
        super().__init__(placeholder="Cocinar…", options=opciones)

    async def callback(self, interaccion: discord.Interaction) -> None:
        resultado = economia.cocinar(
            str(interaccion.user.id), str(interaccion.guild_id), self.values[0]
        )
        if not resultado.ok:
            aviso = f"❌ {resultado.problema}"
        else:
            aviso = (
                f"{resultado.sopaipilla.emoji} Cocinada una "
                f"**{resultado.sopaipilla.nombre}**.\n"
                "-# Dásela desde 🎒 **Mochila**: cuánto suba depende de si a tu "
                "gachamon le gusta el color."
            )
        await interaccion.response.edit_message(content=aviso, view=None)


async def abrir_huerto(interaccion: discord.Interaction) -> None:
    usuario_id, guild_id = str(interaccion.user.id), str(interaccion.guild_id)
    ahora = db.ahora_utc()
    hogar = db.hogar_leido(usuario_id, guild_id, ahora)
    cuantos = hue.bancales_de(hogar.casa.clave if hogar.casa else None)
    mochila = db.inventario(usuario_id, guild_id)

    menus: list[discord.ui.Select] = []
    if cuantos:
        del_huerto = MenuHuerto(db.huerto_de(usuario_id, guild_id, cuantos), ahora)
        if del_huerto.options:
            menus.append(del_huerto)
        cocina = MenuCocina(mochila)
        if cocina.options:
            menus.append(cocina)

    await interaccion.response.send_message(
        texto_del_huerto(usuario_id, guild_id, ahora),
        view=VistaConMenu(*menus) if menus else None,
        ephemeral=True,
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


class MenuEstiloFicha(discord.ui.Select):
    """Cómo verá todo el servidor las fichas de la persona."""

    def __init__(self, actual: str, refrescar=None):
        self.refrescar = refrescar
        super().__init__(
            placeholder="Estilo de ficha…",
            options=[
                discord.SelectOption(
                    label="Imagen",
                    value="imagen",
                    description="Usa el retrato cuando esté disponible.",
                    emoji="🖼️",
                    default=actual == "imagen",
                ),
                discord.SelectOption(
                    label="ASCII clásico",
                    value="ascii",
                    description="Siempre muestra el arte ASCII clásico.",
                    emoji="⌨️",
                    default=actual == "ascii",
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        usuario_id, guild_id = str(interaction.user.id), str(interaction.guild_id)
        estilo = self.values[0]
        db.guardar_estilo_de_ficha(usuario_id, guild_id, estilo)
        criatura = db.criatura_activa(usuario_id, guild_id)
        nombre = "Imagen" if estilo == "imagen" else "ASCII clásico"
        await interaction.response.edit_message(
            content=f"✅ Estilo público de ficha: **{nombre}**.",
            view=None,
        )
        if criatura is not None and self.refrescar is not None:
            await self.refrescar(interaction, criatura)


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
    que aquí caben cinco. La tienda usa dos y la personalización hasta tres.
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
            MenuTienda(),
            MenuCosmeticos(db.ropero(usuario_id, guild_id)),
            MenuCasas(db.hogar_de(usuario_id, guild_id, db.ahora_utc())),
            MenuMuebles(db.mobiliario(usuario_id, guild_id)),
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
        menus.append(MenuEstiloFicha(
            db.estilo_de_ficha(usuario_id, guild_id), refrescar
        ))
        if tengo:
            menus.append(MenuPonerCosmetico(tengo, refrescar))
        if any(getattr(criatura, tipo) for tipo in cos.TIPOS):
            menus.append(MenuQuitarCosmetico(criatura, refrescar))

    await interaccion.response.send_message(
        texto_de_personalizacion(usuario_id, guild_id),
        view=VistaConMenu(*menus) if menus else None,
        ephemeral=True,
    )
