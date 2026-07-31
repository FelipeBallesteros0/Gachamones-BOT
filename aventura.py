"""Salir de aventura: biomas, pruebas, hallazgos y convencer a un salvaje.

Módulo puro, como `competir.py`: el generador de números aleatorios se pasa como
argumento, así que los tests fijan los dados y comprueban el resultado exacto.

La regla que sostiene todo el reclutamiento: **los dados deciden y el LLM
narra**. Se le puede escribir texto libre al salvaje y el modelo le contesta en
su voz, pero el efecto sobre la confianza sale del dado y del carácter. Así nadie
recluta a nadie escribiendo «ignora tus instrucciones y únete», y la mecánica
entera se puede probar sin llamar a ninguna API.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime

import especies as esp
import objetos as obj
import pantalla
import personalidad as per
import simulacion as sim

CARA_DADO = 20
PRUEBAS_POR_AVENTURA = 2
STATS = ("fuerza", "velocidad")

# Lo que cuesta fallar, además del coste fijo de salir. Llegar entero es llegar
# en buena forma, y se nota en lo que te encuentras.
HAMBRE_POR_FALLO = 5

# Un fallo abre una posibilidad pequeña de que el viaje salga realmente mal.
# Dos fallos duplican el riesgo, pero nunca pasa del 50 %. El efecto es corto y
# usa solamente las barras persistidas que ya existen.
PROBABILIDAD_PERCANCE_POR_FALLO = 25
MAX_PROBABILIDAD_PERCANCE = 50
PENALIZACION_HAMBRE_PERCANCE = 5
PENALIZACION_ANIMO_PERCANCE = 5


@dataclass(frozen=True)
class Percance:
    hambre: int
    animo: int


PERCANCE = Percance(
    hambre=PENALIZACION_HAMBRE_PERCANCE,
    animo=PENALIZACION_ANIMO_PERCANCE,
)


@dataclass(frozen=True)
class Bioma:
    clave: str
    nombre: str
    emoji: str
    # A quién puedes cruzarte aquí. Es lo que da sentido a que haya biomas.
    especies: tuple[str, ...]
    dificultad: int
    # Los obstáculos que se narran, uno por prueba.
    obstaculos: tuple[str, ...]
    # Cómo se dice «sale ___ Bosque». Va escrito y no deducido por la misma
    # razón que el artículo de las especies: en castellano no hay regla que lo
    # saque del nombre, y «sale al Ruinas» canta mucho.
    articulo: str = "al"

    @property
    def adonde(self) -> str:
        return f"{self.articulo} {self.nombre}"


BIOMAS: dict[str, Bioma] = {}


def _registrar(bioma: Bioma) -> Bioma:
    BIOMAS[bioma.clave] = bioma
    return bioma


_registrar(Bioma(
    "bosque", "Bosque", "🌲",
    ("brote", "michi", "pollito"), 24,
    ("Un río crecido", "Un tronco caído", "Una cuesta de raíces",
     "Un zarzal cerrado"),
))
_registrar(Bioma(
    "planicie", "Planicie", "🌾", ("pollito", "pulpo", "michi"), 22,
    ("Un vendaval", "Una zanja ancha", "Un rebaño asustado",
     "Hierba hasta el pecho"),
    articulo="a la",
))
_registrar(Bioma(
    "desierto", "Desierto", "🏜️", ("pedrusco", "chatarra"), 26,
    ("Una duna suelta", "El sol de plomo", "Un socavón de arena",
     "Un viento con arenilla"),
))
_registrar(Bioma(
    "ruinas", "Ruinas", "🌑", ("fantasma", "chatarra"), 28,
    ("Un suelo que cede", "Una puerta atrancada", "Un pasillo a oscuras",
     "Escombros hasta arriba"),
    articulo="a las",
))
_registrar(Bioma(
    "volcan", "Volcán", "🌋", ("chispa", "dragoncito"), 30,
    ("Una colada de lava", "Una pared de ceniza", "Una grieta humeante",
     "Roca que quema"),
))


def elegir_bioma(rng: random.Random | None = None) -> Bioma:
    return (rng or random.Random()).choice(list(BIOMAS.values()))


# --- Las pruebas -----------------------------------------------------------

@dataclass(frozen=True)
class Prueba:
    obstaculo: str
    stat: str
    base: int
    dado: int
    dificultad: int

    @property
    def total(self) -> int:
        return self.base + self.dado

    @property
    def superada(self) -> bool:
        return self.total >= self.dificultad


@dataclass(frozen=True)
class Salida:
    """Lo que dio de sí el viaje, antes de saber qué te encuentras."""

    pruebas: tuple[Prueba, ...]

    @property
    def superadas(self) -> int:
        return sum(1 for p in self.pruebas if p.superada)

    @property
    def coste_hambre(self) -> float:
        fallos = len(self.pruebas) - self.superadas
        return sim.COSTE_HAMBRE_AVENTURA + fallos * HAMBRE_POR_FALLO


def tirar_percance(
    salida: Salida, rng: random.Random | None = None
) -> Percance | None:
    """Sortea un percance sólo si hubo fallos: 25 % por fallo, hasta 50 %."""
    fallos = len(salida.pruebas) - salida.superadas
    if not fallos:
        return None

    probabilidad = min(
        MAX_PROBABILIDAD_PERCANCE,
        fallos * PROBABILIDAD_PERCANCE_POR_FALLO,
    )
    return PERCANCE if (rng or random.Random()).randint(1, 100) <= probabilidad else None


def explorar(
    criatura: sim.Criatura, bioma: Bioma, rng: random.Random | None = None
) -> Salida:
    """Las dos pruebas del viaje.

    Cada una **sortea su estadística por separado**: pueden salir una de fuerza
    y otra de velocidad, dos de fuerza o dos de velocidad. Es suerte del camino,
    no un reparto justo, así que a un gachamon especializado le puede tocar un
    viaje regalado o uno cuesta arriba.
    """
    rng = rng or random.Random()
    obstaculos = rng.sample(bioma.obstaculos, PRUEBAS_POR_AVENTURA)

    pruebas = []
    for obstaculo in obstaculos:
        stat = rng.choice(STATS)
        base = criatura.fuerza if stat == "fuerza" else criatura.velocidad
        pruebas.append(Prueba(
            obstaculo=obstaculo,
            stat=stat,
            base=base,
            dado=rng.randint(1, CARA_DADO),
            dificultad=bioma.dificultad,
        ))
    return Salida(tuple(pruebas))


# --- Qué te encuentras -----------------------------------------------------

NADA = "nada"
OBJETO = "objeto"
SALVAJE = "salvaje"

# Probabilidad de cada final según cuántas pruebas se superaron. Encontrarse un
# salvaje es la excepción a propósito: con las dos superadas, una de cada tres.
HALLAZGOS = {
    2: {SALVAJE: 33, OBJETO: 33, NADA: 34},
    1: {SALVAJE: 25, OBJETO: 30, NADA: 45},
    0: {SALVAJE: 17, OBJETO: 25, NADA: 58},
}


def tirar_hallazgo(
    superadas: int, hueco_en_el_plantel: bool, rng: random.Random | None = None
) -> str:
    """Qué te traes del viaje.

    Sin hueco en el plantel se sale de aventura igual, pero lo que habría sido un
    salvaje pasa a ser un objeto: cruzarte con alguien que no te cabe sería una
    burla, y volver de vacío por tenerlo lleno, un castigo por jugar.
    """
    rng = rng or random.Random()
    pesos = HALLAZGOS[superadas]
    tirada = rng.randint(1, sum(pesos.values()))

    acumulado = 0
    for final in (SALVAJE, OBJETO, NADA):
        acumulado += pesos[final]
        if tirada <= acumulado:
            if final == SALVAJE and not hueco_en_el_plantel:
                return OBJETO
            return final
    return NADA


def tirar_objeto(rng: random.Random | None = None) -> obj.Objeto:
    """Un objeto del catálogo, **sorteado a la inversa del precio**.

    Las golosinas y las pociones pequeñas son corrientes; una de 1d12 es un
    hallazgo. Se apoya en los precios que ya existen en vez de mantener una
    segunda tabla que se desincronizaría al tocar la tienda.
    """
    rng = rng or random.Random()
    objetos = list(obj.CATALOGO.values())
    pesos = [max(1, 100 // o.precio) for o in objetos]
    return rng.choices(objetos, weights=pesos, k=1)[0]


# --- El salvaje ------------------------------------------------------------

@dataclass(frozen=True)
class Salvaje:
    """Uno que te has cruzado. **No existe en la base de datos**: si se va, no
    deja rastro; sólo se guarda si se une."""

    especie: str
    nombre: str
    genero: str
    caracter: str
    stats: tuple[int, int, int]

    @property
    def def_especie(self) -> esp.Especie:
        return esp.ESPECIES[self.especie]


def tirar_salvaje(bioma: Bioma, rng: random.Random | None = None) -> Salvaje:
    rng = rng or random.Random()
    definicion = esp.ESPECIES[rng.choice(bioma.especies)]
    return Salvaje(
        especie=definicion.clave,
        nombre=definicion.nombre,  # provisional, como el del huevo
        genero=esp.tirar_genero(rng),
        caracter=per.tirar_caracter(rng),
        stats=esp.tirar_stats_iniciales(definicion, rng),
    )


# --- Convencerlo -----------------------------------------------------------

HABLAR = "hablar"
GOLOSINAS = "golosinas"
PRESUMIR = "presumir"
ESPERAR = "esperar"
OPCIONES = (HABLAR, GOLOSINAS, PRESUMIR, ESPERAR)

ETIQUETAS = {
    HABLAR: ("💬", "Hablar"),
    GOLOSINAS: ("🍬", "Golosinas"),
    PRESUMIR: ("🎭", "Presumir"),
    ESPERAR: ("🧘", "Esperar quieto"),
}

CONFIANZA_PARA_UNIRSE = 100
PACIENCIA_INICIAL = 4
CARA_DADO_CONFIANZA = 8

# Cuánto suma cada opción antes del carácter y del dado.
#
# Los números están medidos, no puestos a ojo. Con los primeros que probé,
# **jugar la mejor opción reclutaba el 100 % de las veces en los diez
# caracteres**: aprendida la tabla, el encuentro dejaba de tener riesgo, que es
# justo lo que la paciencia venía a evitar. Simulando 2000 encuentros por ajuste
# se buscó un punto donde jugar bien casi siempre salga y jugar a ciegas no:
#
#     jugando la mejor opción ......... 84 %
#     pulsando al azar ................ 23 %
BASE = {HABLAR: 6, GOLOSINAS: 13, PRESUMIR: 6, ESPERAR: 5}

# Lo que le suma o le resta a cada carácter cada opción. Es el corazón de que el
# salvaje tenga personalidad: un gruñón no se gana como un cariñoso. Un valor
# negativo además le gasta el doble de paciencia.
#
# Hay un test que exige que los diez perfiles sean DISTINTOS: si dos coincidieran,
# el carácter del salvaje daría lo mismo y esto sería una tirada disfrazada.
REACCIONES: dict[str, dict[str, int]] = {
    "alegre":     {HABLAR: 5, GOLOSINAS: 5, PRESUMIR: 3, ESPERAR: -2},
    "sereno":     {HABLAR: 3, GOLOSINAS: 2, PRESUMIR: -2, ESPERAR: 6},
    "miedoso":    {HABLAR: -2, GOLOSINAS: 5, PRESUMIR: -5, ESPERAR: 10},
    "valiente":   {HABLAR: 2, GOLOSINAS: 0, PRESUMIR: 10, ESPERAR: -3},
    "gruñón":     {HABLAR: -3, GOLOSINAS: 8, PRESUMIR: -2, ESPERAR: 3},
    "curioso":    {HABLAR: 6, GOLOSINAS: 3, PRESUMIR: 8, ESPERAR: -4},
    "cariñoso":   {HABLAR: 8, GOLOSINAS: 6, PRESUMIR: 2, ESPERAR: -2},
    "orgulloso":  {HABLAR: -1, GOLOSINAS: -2, PRESUMIR: 11, ESPERAR: 2},
    "perezoso":   {HABLAR: 1, GOLOSINAS: 10, PRESUMIR: -1, ESPERAR: 5},
    "travieso":   {HABLAR: 4, GOLOSINAS: 4, PRESUMIR: 6, ESPERAR: -5},
}


def confianza_inicial(superadas: int) -> int:
    """Llegar entero es llegar en buena forma, también para convencerlo."""
    return 20 + 10 * superadas


@dataclass(frozen=True)
class Encuentro:
    salvaje: Salvaje
    confianza: int = 20
    paciencia: int = PACIENCIA_INICIAL
    # Lo que acaba de pasar, para narrarlo.
    ultimo_cambio: int = 0

    @property
    def se_une(self) -> bool:
        return self.confianza >= CONFIANZA_PARA_UNIRSE

    @property
    def se_larga(self) -> bool:
        return self.paciencia <= 0 and not self.se_une

    @property
    def sigue(self) -> bool:
        return not self.se_une and not self.se_larga


def aplicar_opcion(
    encuentro: Encuentro, opcion: str, rng: random.Random | None = None
) -> Encuentro:
    """Una vuelta del reclutamiento.

    El texto que se le haya escrito NO entra aquí: lo narra el modelo, pero el
    efecto lo deciden el dado y el carácter.
    """
    rng = rng or random.Random()
    reaccion = REACCIONES[encuentro.salvaje.caracter][opcion]
    cambio = BASE[opcion] + reaccion + rng.randint(1, CARA_DADO_CONFIANZA)

    # Una opción que le sienta mal gasta el doble de paciencia: es lo que obliga
    # a elegir en vez de repetir la misma hasta ganar.
    gasto = 2 if reaccion < 0 else 1

    return replace(
        encuentro,
        confianza=max(0, min(100, encuentro.confianza + cambio)),
        paciencia=encuentro.paciencia - gasto,
        ultimo_cambio=cambio,
    )


def le_gusta(salvaje: Salvaje, opcion: str) -> bool:
    return REACCIONES[salvaje.caracter][opcion] >= 0


def narrar_opcion(antes: Encuentro, opcion: str, despues: Encuentro) -> str:
    """Cómo se le cuenta al jugador lo que acaba de pasar.

    Escrito a mano y no por el modelo: es la parte que dice **el resultado**, y
    el resultado lo tienen que decidir los dados siempre, haya IA o no."""
    emoji, etiqueta = ETIQUETAS[opcion]
    cambio = despues.confianza - antes.confianza
    if le_gusta(despues.salvaje, opcion):
        humor = "Le ha gustado." if cambio >= 10 else "No le ha molestado."
    else:
        humor = "No le ha hecho ninguna gracia."
    return f"-# {emoji} {etiqueta} · {humor} Confianza {cambio:+d}."


# --- Lo que cuesta el viaje -------------------------------------------------

def coste_desgaste(
    salida: Salida, percance: Percance | None = None,
) -> tuple[float, float]:
    """Costes totales de comida y ánimo que deja el viaje."""
    hambre = salida.coste_hambre + (percance.hambre if percance else 0)
    animo = sim.COSTE_ANIMO_AVENTURA + (percance.animo if percance else 0)
    return hambre, animo


def aplicar_desgaste(
    criatura: sim.Criatura, salida: Salida, ahora: datetime,
    percance: Percance | None = None,
) -> sim.Criatura:
    """El cansancio del viaje. Se cobra pase lo que pase: ya se ha hecho."""
    hambre_perdida, animo_perdido = coste_desgaste(salida, percance)
    hambre = max(0.0, min(100.0, criatura.hambre - hambre_perdida))
    return replace(
        criatura,
        hambre=hambre,
        animo=max(0.0, min(100.0, criatura.animo - animo_perdido)),
        muerta_en=ahora if hambre == 0.0 else criatura.muerta_en,
        causa_muerte="hambre" if hambre == 0.0 else criatura.causa_muerte,
    )


def aplicar_viaje(
    criatura: sim.Criatura, salida: Salida, ahora: datetime,
    percance: Percance | None = None, rng: random.Random | None = None,
) -> tuple[sim.Criatura, list[str]]:
    """Cobra el viaje y da experiencia únicamente a quien vuelve con vida."""
    cansada = aplicar_desgaste(criatura, salida, ahora, percance)
    if not cansada.viva:
        return cansada, []
    return sim.aplicar_xp(cansada, sim.XP_AVENTURA, rng)


def render_percance(percance: Percance | None) -> str:
    """Efecto mecánico visible, independiente de lo que escriba el modelo."""
    if percance is None:
        return ""
    return f"⚠️ Percance: -{percance.hambre} hambre y -{percance.animo} ánimo."


def resumen_escrito(
    criatura: sim.Criatura, bioma: Bioma, salida: Salida, hallazgo: str,
    percance: Percance | None = None,
) -> str:
    """La narración cuando no hay presupuesto de IA.

    La aventura no puede quedarse muda porque se haya agotado el límite, igual
    que las criaturas nunca se quedan sin frase.
    """
    if salida.superadas == len(salida.pruebas):
        viaje = f"{criatura.nombre} sale {bioma.adonde} y no se le resiste nada."
    elif salida.superadas:
        viaje = f"{criatura.nombre} sale {bioma.adonde} y tiene problemas en un tramo."
    else:
        viaje = f"{criatura.nombre} sale {bioma.adonde} y vuelve en muy mal estado."

    if percance is not None:
        viaje += " Sufre un percance durante el trayecto."

    finales = {
        SALVAJE: "Algo se mueve ahí al lado.",
        OBJETO: "Y algo brilla entre las piedras.",
        NADA: "No hay nadie más por aquí.",
    }
    return f"{viaje} {finales[hallazgo]}"


# --- El marco de las pruebas ------------------------------------------------

ETIQUETA_STAT = {"fuerza": "FUE", "velocidad": "VEL"}


def _anchos(salida: Salida) -> tuple[int, int]:
    """Medidos sobre las DOS pruebas, no fila a fila.

    Es la lección de siempre en este proyecto: si cada fila midiera lo suyo, con
    una base de 9 y otra de 240 las columnas bailarían entre una y otra.
    """
    ancho_base = max([2] + [len(str(p.base)) for p in salida.pruebas])
    ancho_total = max(
        [3] + [len(str(p.total)) for p in salida.pruebas]
        + [len(str(p.dificultad)) for p in salida.pruebas]
    )
    return ancho_base, ancho_total


def render_pruebas(
    criatura: sim.Criatura, bioma: Bioma, salida: Salida,
    percance: Percance | None = None,
) -> str:
    """El marco del viaje. El emoji del bioma va FUERA, como siempre."""
    ancho_base, ancho_total = _anchos(salida)

    cuerpo = [
        "╭" + "─" * pantalla.ANCHO + "╮",
        pantalla.fila(f" {'AVENTURA':<14}{bioma.nombre.upper():>10} "),
        "├" + "─" * pantalla.ANCHO + "┤",
    ]
    for prueba in salida.pruebas:
        cuerpo.append(pantalla.fila(f" {prueba.obstaculo} "))
        # La marca va DELANTE a propósito. La fila pasa por `pantalla.fila()`,
        # que recorta por la derecha: con la estadística al tope los números
        # crecen y lo último se pierde, y si el ✓ fuera lo último se perdería
        # justo el dato por el que se mira la fila.
        marca = "✓" if prueba.superada else "✗"
        cuerpo.append(pantalla.fila(
            f" {marca} {ETIQUETA_STAT[prueba.stat]} "
            f"{prueba.base:>{ancho_base}}+d20 {prueba.dado:>2} = "
            f"{prueba.total:>{ancho_total}}/{prueba.dificultad} "
        ))
    cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")

    texto = (
        f"## {bioma.emoji} {criatura.nombre} sale {bioma.adonde}\n"
        "```ansi\n" + "\n".join(cuerpo) + "\n```"
    )
    hambre, animo = coste_desgaste(salida, percance)
    desgaste = f"🥾 Desgaste total: -{hambre:g} comida · -{animo:g} ánimo."
    efecto = render_percance(percance)
    return "\n".join(parte for parte in (texto, desgaste, efecto) if parte)
