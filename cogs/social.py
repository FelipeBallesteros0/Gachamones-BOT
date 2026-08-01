"""Ranking, cementerio, ayuda y utilidades de prueba."""
from __future__ import annotations

import random
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import aventura as av
import comun
import competir as comp
import config
import db
import economia as eco
import equipo
import objetos as obj
import especies as esp
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


def _tabla(lineas: list[str], vacia: str) -> str:
    if not lineas:
        return vacia
    return "```ansi\n" + "\n".join(lineas) + "\n```"


def panel_de_logros(
    criatura: sim.Criatura,
    hechos: dict[str, int],
    conseguidos: dict,
) -> str:
    """La lista de las dieciocho medallas, con cuáles lleva y cuánto le falta.

    En markdown y no dentro de un ```ansi``` como el ranking: aquí lo que manda
    es el texto de cada logro, que es largo y de ancho variable, y en un bloque
    de código no cabría sin recortarlo. Fuera del bloque, Discord lo parte solo.
    """
    lineas = []
    for logro in lgr.LOGROS:
        tiene = logro.clave in conseguidos
        linea = f"{'✅' if tiene else '⬜'} **{logro.nombre}** · {logro.como}"
        # El progreso sólo donde significa algo: en los de una sola vez, un
        # «0/1» no le dice nada a nadie.
        if not tiene and logro.meta > 1:
            linea += f" · `{min(hechos.get(logro.hecho, 0), logro.meta)}/{logro.meta}`"
        lineas.append(linea)

    return (
        f"## 🏅 Logros de {sim.nombre_visible(criatura)}\n"
        + "\n".join(lineas)
        + f"\n-# {len(conseguidos)} de {len(lgr.LOGROS)}. "
        "Son del gachamon: cada uno lleva los suyos."
    )


def _techo_diario() -> int:
    """Lo máximo que se puede ganar en un día, aprovechándolo entero.

    Se calcula de los premios y los topes en vez de escribirlo, para que la
    ayuda no se quede diciendo un número viejo si alguien los retoca.
    """
    return (
        eco.PREMIO_CUIDADO * eco.TOPE_CUIDADOS
        + eco.PREMIO_EVOLUCION * eco.TOPE_EVOLUCIONES
        + eco.PREMIO_GANADOR * eco.TOPE_COMPETENCIAS
    )


def paginas_de_ayuda(nombre_bot: str) -> tuple[str, ...]:
    """La ayuda repartida en mensajes, uno por página.

    Va en dos porque no cabe en uno: Discord corta el `content` en 2000
    caracteres y la ayuda entera se pasaba, así que `/ayuda` fallaba con un 400
    sin que se notara. Partirla en vez de apretar el texto deja sitio para seguir
    explicando lo que haga falta. El corte va donde cambia el tema: primero la
    criatura, después qué hacer con ella.

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
Los botones bajo la pantalla: 🍖 alimentar, 🎮 jugar, 🏋️ entrenar, 🧼 limpiar, \
🔄 actualizar. Cada acción publica una pantalla nueva abajo y deja la anterior \
apagada.
-# Si la comida llega a 0, **se muere**. Aguanta unas {horas} h sin comer; \
la estadística de salud alarga ese margen.

**Crecer**
Cuidarlo da experiencia: alimentar +1, jugar +2, entrenar +3. Ganar una \
competencia da +10. Cada nivel es una **evolución** y le cambia el dibujo:
-# cría → niño → adolescente → adulto → adulto grande
El primer salto cae en un día; llegar a la forma final cuesta cerca de un mes. \
Cada evolución reparte estadísticas y, al subir salud, aguanta más sin comer.

**Estadísticas**
Al nacer: base de la especie + 2d6 en cada una. Jugar sube velocidad, entrenar \
sube fuerza, comer sube salud — con rendimientos decrecientes.

**Quién le ha tocado ser**
Al salir del huevo se sortean también su **género** (♂️ o ♀️, mitad y mitad) y \
su **personalidad**, una de diez: {caracteres_txt}.
-# Las dos salen en la ficha y no cambian nunca. No tocan ninguna estadística: \
sólo cómo te habla y cómo se porta en el jardín. Ninguna es mejor que otra."""

    que_hacer = f"""## 🏁 Y qué hacer con él

**Competir**
`/carrera @alguien` — decide la velocidad + 1d20. Puedes invitar a **tres más** \
en los huecos opcionales y correr hasta {comp.MAX_CORREDORES}: con tres o más, \
la carrera acaba en **podio**, con los tres primeros subidos a su cajón.
`/sumo @alguien` — decide la fuerza + 1d20, cuerpo a cuerpo.
`/sumo @a @b @c` — **torneo de cuatro**: se sortean dos semifinales y los que \
pasan juegan la final. De dos o de cuatro; con tres no hay forma de emparejar.
-# {comp.TRAMOS} tramos por pelea, gana quien sume más. El buen ánimo suma un \
poco; tener poca comida resta. Sólo el primero suma victoria, y el torneo cuenta como \
una sola competencia aunque los finalistas peleen dos veces. Quien rechaza el \
reto se cae, no lo cancela, y al agotarse el plazo se juega con quien aceptó.

**Aventura**
`/aventura` te lleva **a ti y a tu gachamon** a un bioma al azar, ante una escena \
con **tres salidas**: 💪 fuerza, 💨 velocidad o 🚶 seguir camino. Las dos \
primeras tiran `estadística + 1d20`; seguir camino no arriesga, pero tampoco \
cuenta.
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

**Mochila y tienda**
Los dos botones de abajo, o `/mochila` y `/tienda`. En la **tienda** se compra con \
{obj.EMOJI_MONEDA_TIENDA} {obj.MONEDA_TIENDA}; en la **mochila** eliges qué usar. \
Empiezas con **{obj.ASCIICOINS_INICIALES} asciicoins** para gastar y \
**{obj.ASCIIGEMS_INICIALES} asciigems** en reserva.
Hay pociones de fuerza y de velocidad de 1d4 a 1d12 que duran \
{obj.MINUTOS_DE_EFECTO} minutos, una que llena la comida de golpe, dos que \
borran un enfriamiento y una placa para cambiarle el nombre.
-# 🍬 Las **golosinas** ({obj.CATALOGO['golosinas'].precio} \
{obj.MONEDA_TIENDA}) valen para dos cosas: dan \
+{obj.CATALOGO['golosinas'].alimenta} de comida desde la mochila, y sirven de \
cebo con un salvaje en `/aventura`.
-# Sólo una poción activa por estadística: la nueva sustituye a la anterior. \
El bonus sale en la ficha mientras dure.

**Ganar {obj.MONEDA_TIENDA}**
Jugando, con tope diario para que no se pueda machacar:
-# 🍖 cuidarlo **+{eco.PREMIO_CUIDADO}**, hasta {eco.TOPE_CUIDADOS} al día \
· ✨ evolucionar **+{eco.PREMIO_EVOLUCION}**, {eco.TOPE_EVOLUCIONES} al día \
· 🏁 competir **+{eco.PREMIO_COMPETENCIA}** y **+{eco.PREMIO_GANADOR}** si ganas, \
hasta {eco.TOPE_COMPETENCIAS} al día
Son unos **{_techo_diario()} al día** si lo aprovechas entero. Y en `/aventura` \
se encuentran objetos por el camino, que salen gratis.

**Otros**
`/jardin` todos juntos · `/mascota` el tuyo · `/mascota @alguien` el de otro
`/ranking` · `/cementerio` · `/logros` las medallas del tuyo"""

    return (tu_criatura, que_hacer, tus_cosas)


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
            avanzada = sim.avanzar(viva, ahora)
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

        escena = jardin.render(criaturas)
        protagonistas = random.sample(criaturas, min(2, len(criaturas)))
        narracion = await self._narrar(interaccion, protagonistas, ahora)

        citado = "\n".join(f"> {l}" for l in narracion.split("\n"))
        await interaccion.followup.send(
            f"## 🌳 El jardín · {len(criaturas)} gachamones\n{escena}\n{citado}"
        )

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
            sistema, peticion, jardin.frase_de_respaldo(semilla)
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
            nombre = pantalla.pintar(f"{criatura.nombre[:13]:<13}", definicion.color)
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

        # Se revisa antes de pintar, y no sólo por cortesía: «Veterano» y «Bien
        # criado» dependen del tiempo y del nivel, así que se cumplen sin que
        # nadie haga nada. Si no se apuntaran aquí, el panel diría que los tiene
        # y la tabla de logros no se habría enterado.
        nuevos = db.revisar_logros(criatura, ahora)
        hechos = lgr.hechos_de(criatura, db.marcador(criatura.id), ahora)
        panel = panel_de_logros(criatura, hechos, db.logros_de(criatura.id))
        if nuevos:
            panel += f"\n{comun.texto_del_anuncio(criatura, nuevos)}"

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

    @app_commands.command(name="tienda", description=f"Compra objetos con {obj.MONEDA_TIENDA}")
    @comun.solo_en_el_canal()
    async def tienda_cmd(self, interaccion: discord.Interaction) -> None:
        await tienda.abrir_tienda(interaccion)

    @app_commands.command(name="plantel", description="Mira tu plantel y cambia de gachamon activo")
    @comun.solo_en_el_canal()
    async def plantel(self, interaccion: discord.Interaction) -> None:
        await equipo.abrir_plantel(interaccion, vistas.congelar, vistas.bautizar)

    @app_commands.command(name="ayuda", description="Cómo funciona el bot")
    @comun.solo_en_el_canal()
    async def ayuda(self, interaccion: discord.Interaction) -> None:
        primera, *resto = paginas_de_ayuda(interaccion.client.user.display_name)
        await interaccion.response.send_message(primera, ephemeral=True)
        for pagina in resto:
            await interaccion.followup.send(pagina, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Social(bot))
