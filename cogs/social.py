"""Ranking, cementerio, ayuda y utilidades de prueba."""
from __future__ import annotations

import random
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import comun
import competir as comp
import config
import db
import objetos as obj
import especies as esp
import ia
import jardin
import pantalla
import personalidad as per
import simulacion as sim

# Enfriamiento por servidor, para que el jardín no se pueda machacar. Se guarda
# en memoria: con dos minutos no merece la pena tocar la base de datos, y que
# se olvide al reiniciar el bot no tiene ninguna consecuencia.
SEGUNDOS_ENTRE_JARDINES = 120


def _tabla(lineas: list[str], vacia: str) -> str:
    if not lineas:
        return vacia
    return "```ansi\n" + "\n".join(lineas) + "\n```"


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
    especies_txt = " ".join(e.emoji for e in esp.ESPECIES.values())
    caracteres_txt = ", ".join(c.masculino for c in per.CARACTERES.values())
    limite = config.LIMITE_CHARLA_POR_HORA

    tu_criatura = f"""## 🥚 Gachamones BOT

**Empezar**
`/huevo` — te da un huevo. Al romperlo ves cuál de las {len(esp.ESPECIES)} \
criaturas te ha tocado y con qué estadísticas; después la bautizas. Sólo puedes \
tener una viva a la vez.
-# {especies_txt}

**Cuidarla**
Los botones bajo la pantalla: 🍖 alimentar, 🎮 jugar, 🏋️ entrenar, 🧼 limpiar, \
🔄 actualizar. Cada acción publica una pantalla nueva abajo y deja la anterior \
apagada.
-# Si la comida llega a 0, **se muere**. Aguanta unas {horas} h sin comer; \
la estadística de salud alarga ese margen.

**Crecer**
Cuidarla da experiencia: alimentar +1, jugar +2, entrenar +3. Ganar una \
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

    que_hacer = f"""## 🏁 Y qué hacer con ella

**Competir**
`/carrera @alguien` — decide la velocidad + 1d20. Puedes invitar a **tres más** \
en los huecos opcionales y correr hasta {comp.MAX_CORREDORES}: con tres o más, \
la carrera acaba en **podio**, con los tres primeros subidos a su cajón.
`/sumo @alguien` — decide la fuerza + 1d20, cuerpo a cuerpo.
`/sumo @a @b @c` — **torneo de cuatro**: se sortean dos semifinales y los que \
pasan juegan la final. De dos o de cuatro; con tres no hay forma de emparejar.
-# {comp.TRAMOS} tramos por pelea, gana quien sume más. El buen ánimo suma un \
poco; el hambre resta. Sólo el primero suma victoria, y el torneo cuenta como \
una sola competencia aunque los finalistas peleen dos veces. Quien rechaza el \
reto se cae, no lo cancela, y al agotarse el plazo se juega con quien aceptó.

**Aventura**
`/aventura` saca a tu gachamon activo a un bioma al azar. Dos pruebas de fuerza \
o velocidad, y según cómo salgan puedes volver de vacío, con un **objeto** o \
cruzándote con un **gachamon salvaje**.
Convencerlo va por turnos: hablarle, darle **golosinas** (de la tienda), \
presumir o esperar quieto. **Cada carácter reacciona distinto**, y lo que le \
molesta le gasta el doble de paciencia; si se le acaba, se larga.
-# Es la única forma de tener un segundo o un tercer gachamon. Se puede salir \
con el equipo lleno: entonces sólo se encuentran objetos.

**Hablarle**
Menciona al bot y tu criatura te contesta: `@{nombre_bot} te acaricio`.
Cada especie tiene su carácter, y el tono cambia según cómo la tengas: una \
criatura hambrienta contesta de mal humor. Se acuerda de lo último que hayáis \
hablado.
-# Hasta {limite} mensajes por hora. Hablar no gasta comida ni da experiencia."""

    tus_cosas = f"""## 🧬 Tu plantel y tus cosas

**El plantel**
Puedes tener hasta **{db.MAXIMO_PLANTEL}** gachamones, pero sólo **uno activo**: \
es el que recibe los botones y los comandos. Los demás esperan en la \
**incubadora**, donde no les pasa el tiempo —ni hambre, ni ánimo, ni aseo—, así \
que no se te mueren mientras juegas con otro.
-# Se cambia con 🧬 **Cambiar**. `/huevo` sólo da el de partida: los demás hay \
que ganárselos por ahí.

**Mochila y tienda**
Los dos botones de abajo. En la **tienda** se compra con {obj.EMOJI_MONEDA} \
{obj.MONEDA}; en la **mochila** eliges qué usar. Empiezas con \
**{obj.GEMAS_DE_BIENVENIDA}** de regalo.
Hay pociones de fuerza y de velocidad de 1d4 a 1d12 que duran \
{obj.MINUTOS_DE_EFECTO} minutos, una que llena el hambre de golpe, dos que \
borran un enfriamiento y una placa para cambiarle el nombre.
-# Sólo una poción activa por estadística: la nueva sustituye a la anterior. \
El bonus sale en la ficha mientras dure.

**Otros**
`/jardin` todas juntas · `/mascota` la tuya · `/mascota @alguien` la de otro
`/ranking` · `/cementerio`"""

    return (tu_criatura, que_hacer, tus_cosas)


class Social(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ultimo_jardin: dict[str, object] = {}

    @app_commands.command(name="jardin", description="Mira a todas las criaturas del servidor juntas")
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
            f"## 🌳 El jardín · {len(criaturas)} criaturas\n{escena}\n{citado}"
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

    @app_commands.command(name="ranking", description="Las criaturas vivas con más victorias")
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
            + _tabla(lineas, "-# Todavía no hay ninguna criatura viva. Usa `/huevo`.")
        )

    @app_commands.command(name="cementerio", description="Las criaturas que ya no están")
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

    @app_commands.command(name="ayuda", description="Cómo funciona el bot")
    @comun.solo_en_el_canal()
    async def ayuda(self, interaccion: discord.Interaction) -> None:
        primera, *resto = paginas_de_ayuda(interaccion.client.user.display_name)
        await interaccion.response.send_message(primera, ephemeral=True)
        for pagina in resto:
            await interaccion.followup.send(pagina, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Social(bot))
