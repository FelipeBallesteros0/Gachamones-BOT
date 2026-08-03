"""Ranking, cementerio, ayuda y utilidades de prueba."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import aventura as av
import casas as cas
import comun
import competir as comp
import config
import cosmeticos as cosm
import db
import economia as eco
import equipo
import objetos as obj
import especies as esp
import huerto as hue
import ia
import jardin
import logros as lgr
import pantalla
import personalidad as per
import simulacion as sim
import tienda
import vistas

# Enfriamiento por servidor, para que el jardín no se pueda machacar. Se guarda
# en memoria: con dos minutos no merece la pena tocar la base de datos, y que
# se olvide al reiniciar el bot no tiene ninguna consecuencia.
SEGUNDOS_ENTRE_JARDINES = 120

# Lo que dura el botón de amueblar en el mensaje de `/casa`. No es persistente
# como los de la ficha: la casa se vuelve a pedir con el comando y no hay nada
# que se pierda si caduca.
SEGUNDOS_DE_CASA = 120


def _tabla(lineas: list[str], vacia: str) -> str:
    if not lineas:
        return vacia
    return "```ansi\n" + "\n".join(lineas) + "\n```"


def _lineas_de_logros(
    catalogo: tuple[lgr.Logro, ...], hechos: dict[str, int], conseguidos: dict
) -> list[str]:
    lineas = []
    for logro in catalogo:
        tiene = logro.clave in conseguidos
        linea = (
            f"{'✅' if tiene else '⬜'} **{logro.nombre}** · {logro.como} · "
            f"{obj.EMOJI_GEMA} {logro.gemas}"
        )
        # El progreso sólo donde significa algo: en los de una sola vez, un
        # «0/1» no le dice nada a nadie.
        if not tiene and logro.meta > 1:
            linea += f" · `{min(hechos.get(logro.hecho, 0), logro.meta)}/{logro.meta}`"
        lineas.append(linea)
    return lineas


def panel_de_logros(
    criatura: sim.Criatura,
    hechos: dict[str, int],
    conseguidos: dict,
    persona: str,
    hechos_persona: dict[str, int],
    conseguidos_persona: dict,
    reserva: int = 0,
) -> str:
    """Todas las medallas, en dos secciones: las suyas y las tuyas.

    En markdown y no dentro de un ```ansi``` como el ranking: aquí lo que manda
    es el texto de cada logro, que es largo y de ancho variable, y en un bloque
    de código no cabría sin recortarlo. Fuera del bloque, Discord lo parte solo.

    Van en el mismo mensaje y no en dos porque juntas caben de sobra, y porque
    lo que se quiere ver de un vistazo es cuánto queda en total.
    """
    todos = {**conseguidos, **conseguidos_persona}
    ganadas = sum(lgr.POR_CLAVE[c].gemas for c in todos if c in lgr.POR_CLAVE)
    por_ganar = sum(l.gemas for l in lgr.LOGROS) - ganadas
    return (
        f"## 🏅 Logros de {sim.nombre_visible(criatura)}\n"
        + "\n".join(_lineas_de_logros(lgr.del_gachamon(), hechos, conseguidos))
        + f"\n### 🏅 Tuyos, {persona}\n"
        + "\n".join(
            _lineas_de_logros(
                lgr.de_la_persona(), hechos_persona, conseguidos_persona
            )
        )
        + f"\n-# {len(todos)} de {len(lgr.LOGROS)} · "
        f"{obj.EMOJI_GEMA} **{reserva}** en reserva · "
        f"le quedan {por_ganar} por ganar.\n"
        "-# Las de arriba se van con el gachamon si se muere; las tuyas se "
        "quedan. Las gemas van a tu monedero en los dos casos."
    )


def texto_de_la_casa(
    hogar: cas.Hogar,
    vivos: list[sim.Criatura],
    persona: str,
    ahora: datetime,
    puestos: tuple[str, ...] = (),
) -> str:
    """El hogar con todos los vivos dentro, sea propio o el refugio."""
    estado = hogar.estado(ahora)
    donde = hogar.donde(ahora)
    if estado == cas.PROPIA:
        titulo = f"## 🏠 {donde.nombre} de {persona}"
        muebles = [cas.MUEBLES[c] for c in puestos if c in cas.MUEBLES]
        pie = (
            f"-# Comodidad **{cas.comodidad_de(donde, puestos)}**/{donde.techo} · "
            f"{len(muebles)}/{donde.huecos} huecos · "
            f"{len(vivos)} viviendo aquí."
        )
        if muebles:
            pie += "\n-# " + " ".join(m.emoji for m in muebles)
    elif estado == cas.REFUGIO:
        quedan = max(0, (hogar.refugio_hasta - ahora).days)
        titulo = f"## 🏚️ {persona}, en el refugio"
        pie = (
            f"-# Comodidad {donde.comodidad}, y no se puede decorar. "
            f"Quedan **{quedan}** días de estancia: cómprate una casa en "
            "🛒 **Tienda**."
        )
    else:
        titulo = f"## 🌧️ {persona}, a la intemperie"
        pie = (
            "-# Se acabó la estancia en el refugio. Cómprate una casa en "
            "🛒 **Tienda**."
        )
    return f"{titulo}\n{cas.render(vivos, donde)}\n{pie}"


class CasaView(discord.ui.View):
    """Los botones de tu propia casa, pegados al dibujo.

    El mensaje de `/casa` es público —es para enseñarlo—, así que cada botón
    comprueba de quién es antes de abrir nada: amueblar la casa de otro desde su
    propio mensaje sería lo primero que probaría cualquiera.
    """

    def __init__(self, dueño_id: int, publica: bool):
        super().__init__(timeout=SEGUNDOS_DE_CASA)
        self.dueño_id = dueño_id
        self.publica = publica
        self.visitas.label = "Abierta a visitas" if publica else "Cerrada"
        self.visitas.emoji = "🔓" if publica else "🔒"

    async def _es_tuya(self, interaccion: discord.Interaction) -> bool:
        if interaccion.user.id == self.dueño_id:
            return True
        await interaccion.response.send_message(
            "Esa casa no es tuya. Mira la tuya con `/casa`.", ephemeral=True
        )
        return False

    @discord.ui.button(label="Amueblar", emoji="🪑",
                       style=discord.ButtonStyle.secondary)
    async def amueblar(self, interaccion: discord.Interaction, boton) -> None:
        if await self._es_tuya(interaccion):
            await tienda.abrir_amueblar(interaccion)

    @discord.ui.button(label="Huerto", emoji="🌱",
                       style=discord.ButtonStyle.success)
    async def huerto(self, interaccion: discord.Interaction, boton) -> None:
        if await self._es_tuya(interaccion):
            await tienda.abrir_huerto(interaccion)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def visitas(self, interaccion: discord.Interaction, boton) -> None:
        if not await self._es_tuya(interaccion):
            return
        ahora_publica = not self.publica
        db.abrir_o_cerrar_la_casa(
            str(interaccion.user.id), str(interaccion.guild_id),
            ahora_publica, db.ahora_utc(),
        )
        await interaccion.response.send_message(
            "🔓 Tu casa queda **abierta**: cualquiera puede verla con `/visitar`."
            if ahora_publica else
            "🔒 Tu casa queda **cerrada**: sólo la ves tú.",
            ephemeral=True,
        )


class VisitaView(discord.ui.View):
    """Lo que puedes hacer en casa ajena: dejar algo en su buzón.

    Cualquiera que pase por el mensaje puede regalarle, y está bien: es el
    sentido de visitar. Lo que no puede es tocarle la casa, y por eso este botón
    es el único que hay.
    """

    def __init__(self, anfitrion_id: str, anfitrion: str):
        super().__init__(timeout=SEGUNDOS_DE_CASA)
        self.anfitrion_id = anfitrion_id
        self.anfitrion = anfitrion

    @discord.ui.button(label="Dejar un regalo", emoji="🎁",
                       style=discord.ButtonStyle.success)
    async def regalar(self, interaccion: discord.Interaction, boton) -> None:
        if str(interaccion.user.id) == self.anfitrion_id:
            await interaccion.response.send_message(
                "Regalarte a ti mismo no cuenta.", ephemeral=True
            )
            return
        await tienda.abrir_regalo(interaccion, self.anfitrion_id, self.anfitrion)


def paginas_de_ayuda(nombre_bot: str) -> tuple[str, ...]:
    """La ayuda repartida en mensajes, uno por página.

    Va partida porque no cabe en uno: Discord corta el `content` en 2000
    caracteres y la ayuda entera se pasaba, así que `/ayuda` fallaba con un 400
    sin que se notara. Partirla en vez de apretar el texto deja sitio para seguir
    explicando lo que haga falta, y por eso son seis y no dos: cada vez que una
    página se llena se abre otra. Los cortes van donde cambia el tema — la
    criatura, competir, la aventura, el plantel, la casa y el dinero.

    Es una función aparte y no el cuerpo del comando para poder medir cada página
    en un test sin conectarse a nada.
    """
    horas = int(sim.horas_de_vida(15))
    del_huevo_txt = " ".join(esp.ESPECIES[c].emoji for c in esp.DEL_HUEVO)
    del_campo_txt = " ".join(e.emoji for c, e in esp.ESPECIES.items()
                             if c not in esp.DEL_HUEVO)
    caracteres_txt = ", ".join(c.masculino for c in per.CARACTERES.values())
    limite = config.LIMITE_CHARLA_POR_HORA

    tu_criatura = f"""## 🥚 Gachamones BOT

**Empezar**
`/huevo` — te da un huevo. Al romperlo ves cuál de los {len(esp.DEL_HUEVO)} \
gachamones de partida te ha tocado y con qué estadísticas; después lo bautizas.
-# {del_huevo_txt}
-# Los otros **{len(esp.ESPECIES) - len(esp.DEL_HUEVO)}** no salen del huevo: \
sólo te los encuentras en `/aventura`.
-# {del_campo_txt}

**Cuidarlo**
Los botones bajo la pantalla: 🍖 alimentar, 🎮 jugar, 🏋️ entrenar fuerza, \
🧼 limpiar, 🔄 actualizar. Cada acción publica una pantalla nueva abajo y deja \
la anterior apagada.
-# Si la comida llega a 0, **se muere**. Aguanta unas {horas} h sin comer; \
la estadística de salud alarga ese margen.

**Crecer**
Cuidarlo da experiencia: alimentar +1, jugar +2, entrenar fuerza +3. Ganar una \
competencia da +10. Cada nivel es una **evolución** y le cambia el dibujo:
-# cría → niño → adolescente → adulto → adulto grande
El primer salto cae en un día; llegar a la forma final cuesta cerca de un mes. \
Cada evolución reparte estadísticas y, al subir salud, aguanta más sin comer.

**Estadísticas**
Al nacer se tiran **las cuatro**: base de la especie + 2d6 en fuerza, \
velocidad, salud e ingenio. Las acciones dan puntos de entrenamiento:
-# **Alimentar** → Salud +1 entrenamiento si no hay empacho. **Jugar** → \
Velocidad +1 entrenamiento. **Entrenar fuerza** → Fuerza +2 entrenamiento.
-# **Laberinto completado** → Ingenio +1 entrenamiento por participante. La \
estadística visible usa raíz cuadrada: hay rendimientos decrecientes y una \
acción no siempre cambia el número visible.

**Quién le ha tocado ser**
Al salir del huevo se sortean también su **género** (♂️ o ♀️, mitad y mitad) y \
su **personalidad**, una de diez: {caracteres_txt}.
-# Las dos salen en la ficha y no cambian nunca. No tocan ninguna estadística: \
sólo cómo te habla y cómo se porta en el jardín. Ninguna es mejor que otra."""

    que_hacer = f"""## 🏁 Y qué hacer con él

**Competir**
`/carrera @alguien` — **puntos acumulados**: **SALIDA** (velocidad + 1d20), \
**TERRENO** (70 % velocidad + 30 % fuerza + 1d20) y **FONDO** (70 % velocidad \
+ 30 % salud + 1d20). Corren hasta {comp.MAX_CORREDORES}; con tres o más hay podio.
`/sumo @alguien` — **mejor de tres**: **POSICIÓN** (70 % fuerza + 30 % \
velocidad + 1d20), **EMPUJE** (fuerza + 1d20) y **AGUANTE** (70 % fuerza + \
30 % salud + 1d20). Gana **dos intercambios**; con 2–0 no juega AGUANTE.
`/sumo @a @b @c` — torneo de cuatro: dos semis y final, cada cruce al mejor de \
tres. De dos o cuatro; con tres no se puede emparejar.
`/totem @alguien` — **Asalto al Tótem**, no basta con llegar: hay que tomarlo y \
conservarlo. **AL CENTRO** (velocidad + 1d20), **FORCEJEO** (fuerza + 1d20) y \
**HUIDA** (salud + 1d20). Cada fase reparte **puntos de colocación** —tantos \
como asaltantes al primero y uno al último— y gana quien más sume de las tres, \
así que premia al gachamon completo. Asaltan hasta {comp.MAX_CORREDORES}; con \
tres o más hay podio.
-# Las tres dejan **veta**, pero el entrenamiento es **un punto** como en las \
otras dos, y se lo lleva la estadística más atrasada.
`/laberinto @alguien` — **puertas abiertas contra el eco**: **SEÑALES** \
(ingenio + 1d20), **TRAZADO** (70 % ingenio + 30 % velocidad + 1d20) y \
**NO PERDERSE** (70 % ingenio + 30 % salud + 1d20). El eco tira la base del \
participante del medio + 1d20 y abre la puerta quien **lo supera**: igualarlo \
no basta, así que puede no cruzar nadie. Entran hasta {comp.MAX_CORREDORES}; \
con tres o más hay podio.
-# El adversario es el pasillo, no el rival: gana quien más puertas abre.
-# El buen ánimo suma un poco; tener poca comida resta. Sólo el primero suma \
victoria; el \
torneo cuenta una competencia. Quien rechaza se cae del reto."""

    # La aventura se mudó a su propia página al entrar el tótem: con las tres
    # modalidades explicadas, «qué hacer con él» se pasaba del tope de Discord.
    salir_al_campo = f"""## 🧭 Salir de aventura

**Aventura**
`/aventura` te lleva **a ti y a tu gachamon** a un bioma al azar, ante una escena \
con **tres salidas**: 🚶 seguir camino y **dos de las cuatro sendas** —💪 fuerza, \
💨 velocidad, 🛡️ salud o 🧠 ingenio—, sorteadas para esa escena. Las dos sendas \
tiran `estadística + 1d20`; seguir camino no arriesga, pero tampoco cuenta.
La segunda escena trae **las otras dos**, así que en un viaje entero aparecen las \
cuatro, cada una una sola vez.
Son **{av.NIVELES_DE_AVENTURA} decisiones**: acertar te mete más adentro y \
fallar cierra el viaje. Cuanto más hondo llegues, mejor lo que encuentras, y \
sólo al fondo puede aparecer un **gachamon salvaje**. Si vuelve con vida gana \
**+{sim.XP_AVENTURA} XP**; si muere por el desgaste, no.
Convencerlo va por turnos: hablarle, **golosinas**, presumir o esperar quieto. \
**Cada carácter reacciona distinto**, y lo que le molesta le gasta el doble de \
paciencia. Al unirse **no trae nombre**: se lo pones tú, y hasta entonces no \
sale de la incubadora.
-# Es la única forma de tener un segundo o un tercer gachamon. Con el equipo \
lleno se sale igual, pero sólo se encuentran objetos.
-# 🧭 El descanso entre viajes es **tuyo**, no del gachamon: cambiar de activo \
no te lo salta, porque el que sale al campo eres tú."""

    # «Hablarle» se mudó aquí al crecer la aventura con el árbol de decisiones:
    # la página de qué hacer se pasaba del tope de un mensaje de Discord.
    tus_cosas = f"""## 🧬 Tu plantel y tus cosas

**Hablarle**
Menciona al bot y tu gachamon te contesta: `@{nombre_bot} te acaricio`.
Cada especie tiene su carácter, y el tono cambia según cómo lo tengas: un \
gachamon hambriento contesta de mal humor. Se acuerda de la última conversación.
-# Hasta {limite} mensajes por hora. Hablar no gasta comida ni da experiencia.

**El plantel**
Puedes tener hasta **{db.MAXIMO_PLANTEL}** gachamones, pero sólo **uno activo**: \
es el que recibe los botones y los comandos. Los demás esperan en la \
**incubadora**, donde no les pasa el tiempo —ni comida, ni ánimo, ni aseo—, así \
que no se te mueren mientras juegas con otro.
-# Se cambia con 🧬 **Cambiar** o con `/plantel`. `/huevo` sólo da el de \
partida: los demás hay que ganárselos por ahí.

-# `/jardin` todos juntos · `/mascota` el tuyo · `/mascota @alguien` el de otro
-# `/ranking` · `/cementerio` · `/logros` las medallas del tuyo"""

    tu_casa = f"""## 🏠 Tu casa

**El hogar**
Todo tu plantel vive junto, y `/casa` te lo enseña dentro. Se empieza en el \
**refugio**, que es de todos y dura **{cas.DIAS_DE_REFUGIO} días**; después te \
quedas a la intemperie hasta que compres casa en 🛒 **Tienda**.
-# 🏠 {" · ".join(f"**{c.nombre}** 🪙 {c.precio}, comodidad {c.comodidad} y \
{c.huecos} huecos" for c in cas.CATALOGO.values())}
-# Se sube de tamaño, y para bajar se **vende** primero: te dan el \
{cas.PORCENTAJE_DE_REVENTA} % de lo que costó y vuelves al refugio con la semana \
entera. Tienes una casa, no varias. Los **{len(cas.MUEBLES)} muebles** \
(🪙 {min(m.precio for m in cas.MUEBLES.values())}–\
{max(m.precio for m in cas.MUEBLES.values())}) suman comodidad hasta el techo de \
tu casa; se ponen y se quitan con 🪑 **Amueblar**, y lo que retires se guarda.
-# Cuanta más **comodidad**, más despacio le baja el ánimo a tu activo — hasta \
un {int(cas.ALIVIO_MAXIMO_DE_ANIMO * 100)} % menos en la mejor casa. **A la \
intemperie** todo le baja un {int((cas.PENALIZACION_INTEMPERIE - 1) * 100)} % \
más rápido, pero **no puede matarlo**: la comida se queda en \
{int(cas.SUELO_DE_HAMBRE_A_LA_INTEMPERIE)}. El 🎟️ **ticket del refugio** \
(🪙 {obj.CATALOGO["ticket_refugio"].precio}) te devuelve una semana bajo techo.

**El huerto**
Tu casa trae bancales —{" · ".join(f"**{cas.CATALOGO[c].nombre}** {n}" for c, n in hue.BANCALES.items())}— y con 🌱 **Huerto** en `/casa` se siembra. \
Cada semilla (🪙 {obj.CATALOGO["semilla"].precio}) tarda **{hue.HORAS_DE_CULTIVO} h**, o {hue.HORAS_DE_CULTIVO - hue.HORAS_QUE_AHORRA_REGAR} si la riegas, y sale un **poroto de color al azar**.
-# Con **{hue.POROTOS_POR_SOPAIPILLA} porotos del mismo color** cocinas una sopaipilla. Al comérsela, tu gachamon gana el **mismo bonus de fuerza y de velocidad** durante {obj.MINUTOS_DE_EFECTO} min — y el dado sale de si le gusta ese color: **1d12** el favorito de su carácter, **1d4** el que detesta.
-# Por eso te sobrarán colores y te faltarán otros: se regalan por el buzón.

**Vecinos**
`/visitar @alguien` — su casa y sus gachamones, y el botón 🎁 para dejarle algo \
de tu mochila en el buzón, con una nota si quieres. `/buzon` recoge lo tuyo.
-# Tu casa nace abierta; con 🔓 en `/casa` la cierras a visitas.
"""

    # Se partió al entrar los logros: el dinero y las gemas necesitan su propia
    # página, y así queda sitio para explicar en qué se gasta cada moneda.
    tu_dinero = f"""## {obj.EMOJI_MONEDA_TIENDA} Tu dinero

**Mochila y tienda**
Los dos botones de abajo, o `/mochila` y `/tienda`. En la **tienda** se compra con \
{obj.EMOJI_MONEDA_TIENDA} {obj.MONEDA_TIENDA}; en la **mochila** eliges qué usar. \
Empiezas con **{obj.ASCIICOINS_INICIALES} asciicoins** para gastar y \
**{obj.ASCIIGEMS_INICIALES} asciigems** en reserva.
-# **{len([o for o in obj.CATALOGO.values() if o.se_vende])} cosas a la \
venta**: pociones de 1d4 a 1d12 que duran {obj.MINUTOS_DE_EFECTO} min, comida, \
dos que borran un enfriamiento, la placa del nombre, semillas y el ticket del \
refugio.
-# 🍬 Las **golosinas** ({obj.CATALOGO['golosinas'].precio} \
{obj.MONEDA_TIENDA}) valen para dos cosas: dan \
+{obj.CATALOGO['golosinas'].alimenta} de comida desde la mochila, y sirven de \
cebo con un salvaje en `/aventura`.

**Ganar {obj.MONEDA_TIENDA}**
Hasta **{eco.TOPE_DIARIO_ASCIICOINS} al día**, un solo bote para todo. Se \
renueva a medianoche UTC.
-# 🍖 cuidarlo **+{eco.PREMIO_CUIDADO}**, hasta {eco.TOPE_CUIDADOS} al día \
· ✨ evolucionar **+{eco.PREMIO_EVOLUCION}**, {eco.TOPE_EVOLUCIONES} al día \
· 🏁 competir **+{eco.PREMIO_COMPETENCIA}** y **+{eco.PREMIO_GANADOR}** si ganas, \
hasta {eco.TOPE_COMPETENCIAS} al día
-# En `/aventura` te encuentras objetos gratis, a veces \
**{av.MONEDAS_ENCONTRADAS[0]}–{av.MONEDAS_ENCONTRADAS[1]}** asciicoins —del \
bote— y muy raramente **{av.GEMAS_ENCONTRADAS[0]}–{av.GEMAS_ENCONTRADAS[1]}** \
{obj.EMOJI_GEMA}, que no tienen tope.

-# Sólo una poción activa por estadística: la nueva sustituye a la anterior. \
El bonus sale en la ficha mientras dure."""

    tus_gemas = f"""## {obj.EMOJI_GEMA} Tus asciigems

**Ganar {obj.EMOJI_GEMA} asciigems**
Sobre todo con los **logros**: `/logros` te enseña los {len(lgr.LOGROS)} y \
cuánto te falta para cada uno. Van desde ganar tu primera competencia hasta pisar los \
diez biomas o llegar a los 30 días de vida, y se pagan **una sola vez**.
-# **{len(lgr.del_gachamon())}** son de cada gachamon \
({sum(l.gemas for l in lgr.del_gachamon())} {obj.EMOJI_GEMA}) y se van con él; \
los otros **{len(lgr.de_la_persona())}** son tuyos \
({sum(l.gemas for l in lgr.de_la_persona())} {obj.EMOJI_GEMA}) y se quedan. Las \
gemas caen siempre en tu monedero: las de uno sirven para todo tu plantel.

**Gastar {obj.EMOJI_GEMA} asciigems**
En la misma 🛒 **Tienda**, abajo. Lo comprado va a tu **ropero** y se lo pones \
a quien quieras con 🎨 **Personalizar**.
-# 🎨 **tinte** ({cosm.PRECIOS[cosm.TINTE]}) le cambia el color · \
👑 **sombrero** ({cosm.PRECIOS[cosm.SOMBRERO]}) le pone algo en la cabeza · \
🖼️ **marco** ({cosm.PRECIOS[cosm.MARCO]}) cambia el borde de la ficha · \
📜 **título** ({cosm.PRECIOS[cosm.TITULO]}) le añade un mote
-# Uno de cada tipo a la vez, y lo que le quites vuelve al ropero y sirve para \
otro. No tocan ninguna estadística — son sólo para presumir."""

    return (
        tu_criatura, que_hacer, salir_al_campo, tus_cosas, tu_casa, tu_dinero,
        tus_gemas,
    )


class Social(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ultimo_jardin: dict[str, object] = {}

    @app_commands.command(name="jardin", description="Mira a todos los gachamones del servidor juntos")
    @comun.solo_en_el_canal()
    async def jardin_cmd(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        guild_id = str(interaccion.guild_id)

        espera = self._espera_del_jardin(guild_id, ahora)
        if espera:
            await interaccion.response.send_message(
                f"El jardín acaba de moverse. Vuelve en {espera}.", ephemeral=True
            )
            return

        criaturas = []
        for viva in db.vivas_del_servidor(guild_id):
            avanzada = db.avanzar(viva, ahora)
            db.guardar(avanzada)
            if avanzada.viva:
                criaturas.append(avanzada)

        if not criaturas:
            await interaccion.response.send_message(
                f"## 🌳 El jardín\n{jardin.render([])}\n{jardin.FRASES_VACIO}"
            )
            return

        self._ultimo_jardin[guild_id] = ahora
        await interaccion.response.defer()

        # El jardín crece con el servidor, y Discord corta en 2000 caracteres.
        # Se baraja PRIMERO y se mide después sobre lo que va a salir: medir una
        # lista y dibujar otra dejaría pasar un jardín de bichos anchos, que es
        # justo el caso que se pasa. Y barajar hace que el jardín cambie entre
        # visitas en vez de enseñar siempre a las mismas.
        barajadas = random.sample(criaturas, len(criaturas))
        asomadas = barajadas[:jardin.cuantas_caben(barajadas)]

        # Los protagonistas salen de las que SE VEN: narrar a un bicho que no
        # está en el cuadro deja la escena hablando de un fantasma.
        protagonistas = random.sample(asomadas, min(2, len(asomadas)))
        narracion = await self._narrar(interaccion, protagonistas, ahora)
        citado = "\n".join(f"> {l}" for l in narracion.split("\n"))
        titulo = f"## 🌳 El jardín · {len(criaturas)} gachamones\n"

        mensaje, asomadas = self._recortar(titulo, citado, asomadas, criaturas)
        await interaccion.followup.send(mensaje)

    @staticmethod
    def _recortar(titulo, citado, asomadas, todas) -> tuple[str, list]:
        """Arma el mensaje y le quita criaturas hasta que quepa.

        `jardin.cuantas_caben` sólo mide el cuadro, y el mensaje lleva además
        título, narración y coletilla. La narración la escribe la IA, así que su
        tamaño no se puede predecir: si devuelve muchas líneas cortas, el citado
        —que añade «> » a cada una— se dispara. Por eso se **mide lo que se va a
        enviar** en vez de estimarlo; el reparto de arriba deja el mensaje casi
        siempre a la primera y esto no suele dar ni una vuelta.
        """
        mensaje = ""
        recortadas = asomadas
        # De más a menos y acotado por construcción: un `while` aquí podría
        # colgarse si la narración creciera hasta no dejar sitio ni a un bicho,
        # y un bucle sin fin dentro de un comando bloquea el bot entero.
        for cuantas in range(len(asomadas), 0, -1):
            recortadas = asomadas[:cuantas]
            fuera = len(todas) - cuantas
            resto = f"\n-# Y {fuera} más, que hoy no han salido." if fuera else ""
            mensaje = f"{titulo}{jardin.render(recortadas)}\n{citado}{resto}"
            if len(mensaje) <= jardin.TOPE_MENSAJE:
                break
        # Si ni con una cabe, se manda igual: que Discord se queje y salga en el
        # registro es mejor que enseñar un jardín vacío teniendo criaturas.
        return mensaje, recortadas

    def _espera_del_jardin(self, guild_id: str, ahora) -> str | None:
        ultimo = self._ultimo_jardin.get(guild_id)
        if ultimo is None:
            return None
        restante = timedelta(seconds=SEGUNDOS_ENTRE_JARDINES) - (ahora - ultimo)
        if restante.total_seconds() <= 0:
            return None
        return pantalla.formato_espera(restante)

    async def _narrar(self, interaccion, protagonistas, ahora) -> str:
        """La escena la escribe la IA; si falla, una frase genérica.

        Consume del mismo límite horario de IA que la charla, así que el jardín
        no puede usarse para saltárselo.
        """
        usuario_id = str(interaccion.user.id)
        semilla = sum(c.id for c in protagonistas)

        if db.uso_ia_ultima_hora(usuario_id, ahora) >= config.LIMITE_CHARLA_POR_HORA:
            return jardin.frase_de_respaldo(semilla)

        db.registrar_uso_ia(usuario_id, ahora)
        sistema, peticion = per.prompt_jardin(protagonistas, ahora)
        texto, _ = await ia.generar(
            sistema, peticion, jardin.frase_de_respaldo(semilla),
            largo_maximo=jardin.LARGO_NARRACION,
        )
        return texto

    @app_commands.command(name="ranking", description="Los gachamones vivos con más victorias")
    @comun.solo_en_el_canal()
    async def ranking(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        criaturas = db.ranking(str(interaccion.guild_id))

        lineas = []
        for puesto, criatura in enumerate(criaturas, start=1):
            definicion = criatura.def_especie
            nombre = pantalla.pintar(
                f"{criatura.nombre[:13]:<13}",
                cosm.color_del_tinte(criatura.tinte, definicion.color),
            )
            lineas.append(
                f" {puesto:>2}  {nombre} {definicion.nombre[:11]:<11}"
                f" {criatura.victorias:>2}V-{criatura.derrotas:<2}D  Nv{criatura.nivel}"
            )

        await interaccion.response.send_message(
            "## 🏆 Ranking\n"
            + _tabla(lineas, "-# Todavía no hay ningún gachamon vivo. Usa `/huevo`.")
        )

    @app_commands.command(name="logros", description="Las medallas de tu gachamon activo")
    @comun.solo_en_el_canal()
    async def logros_cmd(self, interaccion: discord.Interaction) -> None:
        ahora = db.ahora_utc()
        criatura = db.criatura_activa(
            str(interaccion.user.id), str(interaccion.guild_id)
        )
        if criatura is None:
            await interaccion.response.send_message(
                "No tienes ningún gachamon activo. Empieza con `/huevo`.",
                ephemeral=True,
            )
            return

        # Se paga antes de pintar, y no sólo por cortesía: «Veterano» y «Bien
        # criado» dependen del tiempo y del nivel, así que se cumplen sin que
        # nadie haga nada. Si no se apuntaran aquí, el panel diría que los tiene
        # y la tabla de logros no se habría enterado, y no se cobrarían nunca.
        recibo = eco.pagar_logros(criatura, ahora)
        # Y las tuyas, que es lo que repesca a quien ya cumplía: la rara que te
        # salió hace días no la vas a volver a sacar.
        recibo_persona = eco.pagar_logros_de_persona(
            criatura.usuario_id, criatura.guild_id, ahora
        )
        persona = interaccion.user.display_name
        hechos = lgr.hechos_de(criatura, db.marcador(criatura.id), ahora)
        hechos_persona = lgr.hechos_de_la_persona(
            db.marcador_de_persona(criatura.usuario_id, criatura.guild_id),
            db.especies_de(criatura.usuario_id, criatura.guild_id),
        )
        reserva = eco.saldos(
            criatura.usuario_id, criatura.guild_id
        ).asciigems
        panel = panel_de_logros(
            criatura, hechos, db.logros_de(criatura.id),
            persona, hechos_persona,
            db.logros_de_persona(criatura.usuario_id, criatura.guild_id),
            reserva,
        )
        if recibo.nuevos:
            panel += (
                f"\n{comun.texto_del_anuncio(sim.nombre_visible(criatura), recibo)}"
            )
        if recibo_persona.nuevos:
            panel += f"\n{comun.texto_del_anuncio(persona, recibo_persona)}"

        await interaccion.response.send_message(panel)

    @app_commands.command(name="cementerio", description="Los gachamones que ya no están")
    @comun.solo_en_el_canal()
    async def cementerio(self, interaccion: discord.Interaction) -> None:
        criaturas = db.cementerio(str(interaccion.guild_id))

        lineas = []
        for criatura in criaturas:
            definicion = criatura.def_especie
            vivio = (criatura.muerta_en - criatura.nacida_en).total_seconds() / 3600
            nombre = pantalla.pintar(f"{criatura.nombre[:13]:<13}", esp.GRIS)
            lineas.append(
                f" {nombre} {definicion.nombre[:11]:<11}"
                f" {int(vivio):>3} h  {criatura.victorias:>2}V"
            )

        await interaccion.response.send_message(
            "## 🪦 Cementerio\n"
            + _tabla(lineas, "-# Todavía no ha muerto nadie. Que siga así.")
        )

    # Los mismos menús que abren los botones de abajo de la ficha, para poder
    # llegar a ellos sin buscarla: la ficha se va canal arriba en cuanto habla
    # alguien. Abren lo de quien escribe el comando, así que no hace falta la
    # comprobación de dueño que sí necesitan los botones.
    #
    # Se delega en los mismos adaptadores, con los mismos ganchos que les pasa
    # `vistas`: sin `congelar`, usar un objeto o cambiar de activo dejaría viva
    # una ficha que ya miente, y sin `bautizar` el plantel no sabría mandar a
    # poner nombre a un recluta recién llegado de una aventura.
    @app_commands.command(name="mochila", description="Abre tu mochila y usa lo que lleves")
    @comun.solo_en_el_canal()
    async def mochila(self, interaccion: discord.Interaction) -> None:
        await tienda.abrir_inventario(interaccion, vistas.congelar)

    @app_commands.command(name="tienda", description="Compra objetos, cosméticos y casas")
    @comun.solo_en_el_canal()
    async def tienda_cmd(self, interaccion: discord.Interaction) -> None:
        await tienda.abrir_tienda(interaccion)

    @app_commands.command(name="casa", description="Mira tu hogar y a todos los que viven en él")
    @comun.solo_en_el_canal()
    async def casa(self, interaccion: discord.Interaction) -> None:
        usuario_id, guild_id = (
            str(interaccion.user.id), str(interaccion.guild_id)
        )
        ahora = db.ahora_utc()
        hogar = db.hogar_de(usuario_id, guild_id, ahora)
        await interaccion.response.send_message(
            texto_de_la_casa(
                hogar,
                db.plantel(usuario_id, guild_id),
                interaccion.user.display_name,
                ahora,
                db.puestos(usuario_id, guild_id),
            ),
            view=CasaView(interaccion.user.id, hogar.publica),
        )

    @app_commands.command(name="visitar", description="Mira la casa de otra persona")
    @app_commands.describe(usuario="A quién quieres visitar")
    @comun.solo_en_el_canal()
    async def visitar(
        self, interaccion: discord.Interaction, usuario: discord.Member
    ) -> None:
        ahora = db.ahora_utc()
        suyo, suyo_id = str(usuario.id), str(interaccion.guild_id)
        hogar = db.hogar_leido(suyo, suyo_id, ahora)

        if usuario.id == interaccion.user.id:
            await interaccion.response.send_message(
                "Ésa es tu casa. Para verla, usa `/casa`.", ephemeral=True
            )
            return
        if not hogar.publica:
            await interaccion.response.send_message(
                f"🔒 {usuario.display_name} tiene la casa cerrada a visitas.",
                ephemeral=True,
            )
            return

        await interaccion.response.send_message(
            texto_de_la_casa(
                hogar, db.plantel(suyo, suyo_id), usuario.display_name, ahora,
                hogar.puestos,
            ),
            view=VisitaView(suyo, usuario.display_name),
        )

    @app_commands.command(name="buzon", description="Mira los regalos que te han dejado")
    @comun.solo_en_el_canal()
    async def buzon(self, interaccion: discord.Interaction) -> None:
        await tienda.abrir_buzon(interaccion)

    @app_commands.command(name="plantel", description="Mira tu plantel y cambia de gachamon activo")
    @comun.solo_en_el_canal()
    async def plantel(self, interaccion: discord.Interaction) -> None:
        await equipo.abrir_plantel(
            interaccion, vistas.congelar, vistas.bautizar, vistas.publicar_pantalla
        )

    @app_commands.command(name="ayuda", description="Cómo funciona el bot")
    @comun.solo_en_el_canal()
    async def ayuda(self, interaccion: discord.Interaction) -> None:
        primera, *resto = paginas_de_ayuda(interaccion.client.user.display_name)
        await interaccion.response.send_message(primera, ephemeral=True)
        for pagina in resto:
            await interaccion.followup.send(pagina, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Social(bot))
