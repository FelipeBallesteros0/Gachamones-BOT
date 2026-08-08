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

import json
import random
from dataclasses import dataclass, replace
from datetime import datetime

import especies as esp
import objetos as obj
import pantalla
import personalidad as per
import simulacion as sim

CARA_DADO = 20

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
    # Cómo se dice «sale ___ Bosque». Va escrito y no deducido por la misma
    # razón que el artículo de las especies: en castellano no hay regla que lo
    # saque del nombre, y «sale al Ruinas» canta mucho.
    articulo: str = "al"

    @property
    def adonde(self) -> str:
        return f"{self.articulo} {self.nombre}"

    @property
    def nombres_especies(self) -> tuple[str, ...]:
        """Quién vive aquí, con el nombre que se ve.

        Sale del catálogo y no escrito, que es lo que hace que un rebautizo de
        especie llegue solo hasta el prompt de las escenas.
        """
        return tuple(esp.ESPECIES[clave].nombre for clave in self.especies)


BIOMAS: dict[str, Bioma] = {}


def _registrar(bioma: Bioma) -> Bioma:
    BIOMAS[bioma.clave] = bioma
    return bioma


# Ordenados por dificultad. Los cinco nuevos se reparten DENTRO del rango que
# ya había (22-30) en vez de estirarlo: subir el techo cambiaría lo dura que es
# la aventura, que es otra decisión.
_registrar(Bioma(
    "planicie", "Planicie", "🌾", ("pollito", "pulpo", "michi"), 22,
    articulo="a la",
))
_registrar(Bioma(
    "cienaga", "Ciénaga", "🪷", ("slime", "swampdon", "canizo"), 23,
    articulo="a la",
))
_registrar(Bioma("bosque", "Bosque", "🌲", ("brote", "michi", "pollito"), 24))
_registrar(Bioma(
    "arrecife", "Arrecife", "🏝️",
    ("coralito", "nacar", "remolin", "pulpo"), 25,
))
_registrar(Bioma(
    "chatarral", "Chatarral", "⚙️",
    ("chatarra", "prinel", "bulb", "magnetron"), 26,
))
_registrar(Bioma("desierto", "Desierto", "🏜️",
                 ("pedrusco", "chatarra", "escorpgon"), 26))
_registrar(Bioma(
    "cumbre", "Cumbre", "🏔️", ("criold", "goot", "cefiro"), 28,
    articulo="a la",
))
_registrar(Bioma(
    "ruinas", "Ruinas", "🌑", ("fantasma", "chatarra", "lucierno"), 28,
    articulo="a las",
))
_registrar(Bioma(
    "cavernas", "Cavernas", "🕳️", ("noctule", "prismlon", "pedrusco"), 29,
    articulo="a las",
))
_registrar(Bioma("volcan", "Volcán", "🌋",
                 ("chispa", "dragoncito", "escorpgon"), 30))


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
    def holgura(self) -> int:
        return self.total - self.dificultad

    @property
    def superada(self) -> bool:
        return self.holgura >= 0


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
    """Sortea un percance sólo si hubo fallos: 25 % por fallo, hasta 50 %.

    Desde el árbol de decisiones **un viaje jugado trae un fallo como mucho**,
    porque fallar lo cierra ahí mismo: en la práctica el percance es un 25 % fijo
    y el tope del 50 % no llega a tocarse. La cuenta se deja como está porque
    sigue siendo la regla correcta para cualquier salida que se le pase.
    """
    fallos = len(salida.pruebas) - salida.superadas
    if not fallos:
        return None

    probabilidad = min(
        MAX_PROBABILIDAD_PERCANCE,
        fallos * PROBABILIDAD_PERCANCE_POR_FALLO,
    )
    return PERCANCE if (rng or random.Random()).randint(1, 100) <= probabilidad else None


# --- El árbol de decisiones ------------------------------------------------

# Cada escena ofrece dos stats activas y Volver. El terreno favorece una de las
# dos sin mirar a la criatura; la banda visible sale después de sus stats.
FUERZA, VELOCIDAD, SALUD, INGENIO = sim.ESTADISTICAS
VOLVER = "volver"
Pareja = tuple[str, str]
PAREJAS: tuple[Pareja, ...] = (
    (FUERZA, VELOCIDAD),
    (FUERZA, SALUD),
    (FUERZA, INGENIO),
    (VELOCIDAD, SALUD),
    (VELOCIDAD, INGENIO),
    (SALUD, INGENIO),
)
SESGO_TERRENO = 2


def complementaria(pareja: Pareja) -> Pareja:
    """Las dos stats restantes, en el orden canónico de la simulación."""
    if pareja not in PAREJAS:
        raise ValueError(f"pareja desconocida: {pareja!r}")
    restantes = tuple(stat for stat in sim.ESTADISTICAS if stat not in pareja)
    return restantes[0], restantes[1]


def tirar_pareja(rng: random.Random | None = None) -> Pareja:
    """Sortea uniformemente la pareja del primer nodo."""
    return PAREJAS[(rng or random.Random()).randint(0, len(PAREJAS) - 1)]


@dataclass(frozen=True)
class Terreno:
    pareja: Pareja
    exigencias: tuple[int, int]

    def __post_init__(self) -> None:
        if self.pareja not in PAREJAS:
            raise ValueError(f"pareja desconocida: {self.pareja!r}")
        if len(self.exigencias) != 2:
            raise ValueError("el terreno necesita dos exigencias")

    def exigencia(self, opcion: str) -> int:
        try:
            return self.exigencias[self.pareja.index(opcion)]
        except ValueError as exc:
            raise ValueError(f"opción sin exigencia: {opcion!r}") from exc

    @property
    def favorecida(self) -> str:
        return (
            self.pareja[0]
            if self.exigencias[0] < self.exigencias[1]
            else self.pareja[1]
        )


def tirar_terreno(
    bioma: Bioma, pareja: Pareja, rng: random.Random | None = None,
) -> Terreno:
    """Sortea el lado favorecido sin recibir ni mirar a la criatura."""
    bit = (rng or random.Random()).randint(0, 1)
    baja = bioma.dificultad - SESGO_TERRENO
    alta = bioma.dificultad + SESGO_TERRENO
    return Terreno(pareja, (baja, alta) if bit == 0 else (alta, baja))


def probabilidad_opcion(stat: int, exigencia: int) -> float:
    """Probabilidad exacta y clampada de `stat + 1d20 >= exigencia`."""
    return max(0, min(CARA_DADO, CARA_DADO + 1 + stat - exigencia)) / CARA_DADO


def banda_opcion(stat: int, exigencia: int) -> str:
    probabilidad = probabilidad_opcion(stat, exigencia)
    if probabilidad >= 0.75:
        return "favorable"
    if probabilidad >= 0.50:
        return "pareja"
    if probabilidad >= 0.25:
        return "cuesta arriba"
    return "temeraria"


def deja_marca(holgura: int) -> bool:
    """Si el esfuerzo canónico de esta holgura supera el filtro de VETAS."""
    esfuerzo = sim.esfuerzo_de_aventura(FUERZA, holgura)
    return esfuerzo.profunda or esfuerzo.bruto >= sim.UMBRAL_ESFUERZO


def puede_dejar_marca(stat: int, exigencia: int) -> bool:
    """Si algún resultado posible del d20 emitiría tensión canónica."""
    return any(deja_marca(stat + dado - exigencia)
               for dado in range(1, CARA_DADO + 1))


EMOJI_STAT = {
    FUERZA: "💪",
    VELOCIDAD: "💨",
    SALUD: "🛡️",
    INGENIO: "🧠",
}


def pista_marcas(criatura: sim.Criatura, terreno: Terreno) -> str:
    posibles = [
        stat for stat in terreno.pareja
        if puede_dejar_marca(getattr(criatura, stat), terreno.exigencia(stat))
    ]
    if len(posibles) == 2:
        cuales = "cualquiera de las dos"
    elif posibles:
        cuales = f"sólo la {EMOJI_STAT[posibles[0]]}"
    else:
        cuales = "ninguna"
    return f"-# 🪵 pueden forjar marca: {cuales}"


def palabra_holgura(holgura: int) -> str:
    if holgura in (0, 1):
        return "al límite"
    if 2 <= holgura <= 5:
        return "justa"
    if holgura >= 6:
        return "sobrada"
    if holgura >= -5:
        return "por un pelo"
    return "de largo"


def render_beat(prueba: Prueba | None) -> str:
    if prueba is None:
        return "🚶 Prefirieron no meterse"
    emoji = EMOJI_STAT[prueba.stat]
    esfuerzo = sim.esfuerzo_de_aventura(prueba.stat, prueba.holgura)
    marca = esfuerzo.profunda or esfuerzo.bruto >= sim.UMBRAL_ESFUERZO
    huella = (
        "marca profunda" if esfuerzo.profunda
        else "deja marca" if marca
        else "sin marca"
    )
    resultado = "✓" if prueba.superada else "✗"
    return (
        f"{resultado} {prueba.obstaculo} — {emoji} {prueba.base} + "
        f"{prueba.dado} = {prueba.total} / {prueba.dificultad} · "
        f"{palabra_holgura(prueba.holgura)}, {huella}"
    )


# Cuántas decisiones dura una aventura. Volver también gasta una: es la salida
# sin riesgo, no una forma de seguir mirando escenas hasta que salga una fácil.
NIVELES_DE_AVENTURA = 2


@dataclass(frozen=True)
class Escena:
    """La ficción de un nodo, alineada con sus dos stats activas."""

    situacion: str
    pareja: Pareja
    etiquetas: tuple[str, str]
    volver: str

    def __post_init__(self) -> None:
        if self.pareja not in PAREJAS:
            raise ValueError(f"pareja desconocida: {self.pareja!r}")
        if len(self.etiquetas) != 2:
            raise ValueError("la escena necesita dos etiquetas")

    @property
    def opciones(self) -> tuple[str, str, str]:
        return self.pareja + (VOLVER,)

    def etiqueta(self, opcion: str) -> str:
        if opcion == VOLVER:
            return self.volver
        try:
            return self.etiquetas[self.pareja.index(opcion)]
        except ValueError as exc:
            raise ValueError(f"opción inactiva: {opcion!r}") from exc


# Lo que cabe. Discord corta las etiquetas de botón en 80 caracteres y no avisa;
# la situación va dentro del marco ASCII, que es más estrecho todavía.
LARGO_ETIQUETA = 60
LARGO_SITUACION = 160


def escena_desde_json(crudo: str, pareja: Pareja) -> Escena | None:
    """La escena que propuso el modelo, o `None` si no vale.

    Se valida entera antes de usarla porque el texto viene de fuera: si falta
    una opción, la escena tendría dos salidas en vez de tres, y si una etiqueta
    se pasa de largo, Discord rechaza el botón y la aventura se queda colgada.
    Devolver `None` es la señal para tirar de las escritas.
    """
    if pareja not in PAREJAS:
        raise ValueError(f"pareja desconocida: {pareja!r}")
    # Se busca el objeto en vez de exigir que la respuesta sea JSON a secas: el
    # modelo lo envuelve en un bloque de código o le pone una frase delante más
    # veces de las que uno querría, y eso no es motivo para quedarse sin escena.
    abre, cierra = crudo.find("{"), crudo.rfind("}")
    if abre < 0 or cierra < abre:
        return None

    try:
        datos = json.loads(crudo[abre:cierra + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(datos, dict):
        return None

    campos = {}
    for clave, tope in (
        ("situacion", LARGO_SITUACION),
        (pareja[0], LARGO_ETIQUETA),
        (pareja[1], LARGO_ETIQUETA),
        ("volver", LARGO_ETIQUETA),
    ):
        valor = datos.get(clave)
        if not isinstance(valor, str):
            return None
        valor = " ".join(valor.split())
        if not valor or len(valor) > tope:
            return None
        # La mayúscula inicial se pone aquí y no se le pide al modelo, que la
        # cumple una vez de cada dos: al lado de las escritas cantaba un botón
        # en minúscula junto a otros dos en mayúscula.
        campos[clave] = valor[0].upper() + valor[1:]
    return Escena(
        campos["situacion"], pareja,
        (campos[pareja[0]], campos[pareja[1]]), campos["volver"],
    )


@dataclass(frozen=True)
class EscenaBase:
    """Una situación del respaldo, con etiqueta para las cuatro estadísticas.

    Se escribe **una por (bioma, estadística favorecida)** y se proyecta sobre
    la pareja que salga: la etiqueta del acompañante ya está escrita para esa
    misma situación, sea cual sea. Así el catálogo cubre las 6 parejas × 2 lados
    sin escribir ninguna combinación a mano.
    """

    situacion: str
    etiquetas: tuple[str, str, str, str]   # en el orden de sim.ESTADISTICAS
    volver: str

    def etiqueta(self, stat: str) -> str:
        try:
            return self.etiquetas[sim.ESTADISTICAS.index(stat)]
        except ValueError as exc:
            raise ValueError(f"estadística desconocida: {stat!r}") from exc


# Las escenas escritas a mano. Aunque las invente el modelo, hacen falta: es lo
# que se juega cuando la IA no está o se agotó el límite, igual que las criaturas
# nunca se quedan sin frase. Una aventura muda no es una aventura.
#
# Van variadas a propósito, y no sólo puertas y muros: en cada bioma hay algo
# cerrado, alguien con quien cruzarse y algo que está pasando. Si todas fueran
# obstáculos, el respaldo cantaría al segundo viaje y el modelo tendería a
# copiar la única forma que ve.
ESCENAS_ESCRITAS: dict[str, dict[str, EscenaBase]] = {
    "bosque": {
        FUERZA: EscenaBase(
            "Una puerta hinchada cede hacia afuera y tiene un tronco firme donde apoyar el hombro.",
            ("Empujar la puerta desde el tronco",
             "Colarte por la ventana enredada",
             "Avanzar entre las zarzas mojadas sin parar",
             "Leer por dónde se ha hinchado la madera"),
            "Seguir el sendero",
        ),
        VELOCIDAD: EscenaBase(
            "Bajo un panal de avispas queda un tramo limpio y recto que se cruza de una vez.",
            ("Bajar la rama gruesa que sostiene el panal",
             "Cruzar el tramo limpio de un tirón",
             "Cruzar despacio y aguantar las picaduras",
             "Leer el vaivén de las avispas antes de pasar"),
            "Dar un rodeo",
        ),
        SALUD: EscenaBase(
            "Un leñador se ha quedado sin fuerzas bajo el aguacero y aún le falta medio camino con la carga.",
            ("Cargar tú el haz de leña entero",
             "Correr al pueblo a buscarle ayuda",
             "Acompañarlo bajo el aguacero hasta el final",
             "Repartir la carga con dos varas cruzadas"),
            "Desearle suerte y seguir",
        ),
        INGENIO: EscenaBase(
            "Los senderos se bifurcan una y otra vez, y en los troncos hay marcas viejas que se repiten.",
            ("Abrirte paso recto rompiendo la maleza",
             "Recorrer las bifurcaciones a la carrera",
             "Caminar sin descanso hasta salir del bosque",
             "Seguir las marcas repetidas de los troncos"),
            "Volver por donde entraste",
        ),
    },
    "planicie": {
        FUERZA: EscenaBase(
            "La losa de un pozo sobresale y deja hueco para meter ambas manos.",
            ("Levantar la losa con las dos manos",
             "Alcanzar la cuerda de un salto",
             "Bajar por el brocal y aguantar el agua fría",
             "Buscar el contrapeso que abre la losa"),
            "Dejarlo estar",
        ),
        VELOCIDAD: EscenaBase(
            "Una lona vuela baja sobre campo abierto y hay sitio de sobra para correr tras ella.",
            ("Arrancar el poste clavado que la sujetaba",
             "Atrapar la lona al vuelo",
             "Perseguirla contra el viento sin aflojar",
             "Leer el viento y cortarle el paso a la lona"),
            "Dejar que se la lleve",
        ),
        SALUD: EscenaBase(
            "Un rebaño entra por un paso angosto y levanta una polvareda que tarda en asentarse.",
            ("Plantarte contra la cerca y frenar el rebaño",
             "Esquivarlo por el flanco lleno de hoyos",
             "Aguantar la polvareda hasta que pase entero",
             "Abrir un hueco con dos varas y un trapo"),
            "Tumbarte en la hierba",
        ),
        INGENIO: EscenaBase(
            "Una pastora ha perdido una oveja entre los fardos y quedan huellas y lana enganchada.",
            ("Apartar los fardos mojados uno a uno",
             "Recorrer el pasillo entre fardos corriendo",
             "Batir el campo entero sin parar a descansar",
             "Seguir la lana enganchada hasta la oveja"),
            "Decir que no la viste",
        ),
    },
    "desierto": {
        FUERZA: EscenaBase(
            "Una columna caída tiene la base redonda y una piedra justo donde hacer palanca.",
            ("Volcar la columna con la palanca",
             "Saltar sobre la arena suelta",
             "Empujarla a pleno sol hasta moverla",
             "Calzar cuñas de piedra para que ruede sola"),
            "Buscar sombra",
        ),
        VELOCIDAD: EscenaBase(
            "El suelo cede y deja un borde corto y limpio que se salta de un impulso.",
            ("Sostener la placa de roca que se hunde",
             "Saltar el borde de un impulso",
             "Rodear el socavón por la arena ardiente",
             "Leer las grietas para pisar donde aguanta"),
            "Retroceder sobre tus huellas",
        ),
        SALUD: EscenaBase(
            "La caravana avanza en la hora peor y todavía queda un buen trecho de duna hasta el pozo.",
            ("Cargar tú el fardo más pesado",
             "Adelantarte al pozo y traer agua",
             "Aguantar el trecho de duna a pleno sol",
             "Marcar el rumbo por la sombra de las dunas"),
            "Seguir tu camino",
        ),
        INGENIO: EscenaBase(
            "Un pozo tapiado tiene tres tapas iguales y la arena de alrededor está pisada de idas y venidas.",
            ("Reventar las tres tapas de una vez",
             "Bajar y subir el cubo antes del anochecer",
             "Cavar junto al pozo hasta encontrar agua",
             "Leer las pisadas y ver a qué tapa vuelven"),
            "Seguir la duna",
        ),
    },
    "ruinas": {
        FUERZA: EscenaBase(
            "El portón de bronce está entreabierto y hay un puntal firme donde apoyarse.",
            ("Empujar el portón desde el puntal",
             "Trepar por la hiedra rota",
             "Cruzar el sótano inundado y helado",
             "Buscar el gozne por donde el portón cede"),
            "Rodear la muralla",
        ),
        VELOCIDAD: EscenaBase(
            "Una bandada gira sobre el patio y al hacerlo deja un hueco recto que dura poco.",
            ("Mover la estatua maciza y taparles el paso",
             "Cruzar mientras dure el hueco",
             "Cruzar el patio aguantando los picotazos",
             "Contar sus giros y salir en el momento justo"),
            "Esperar a que se calmen",
        ),
        SALUD: EscenaBase(
            "Alguien lleva horas bajo una viga y sacarlo pide sostenerla un buen rato más.",
            ("Levantar la viga de golpe",
             "Sacarlo de un tirón entre los cascotes",
             "Sostener la viga el rato que haga falta",
             "Apuntalar la viga con cascotes apilados"),
            "Ir a buscar ayuda",
        ),
        INGENIO: EscenaBase(
            "En el muro hay tres marcas repetidas y una losa del suelo suena distinta al pisarla.",
            ("Levantar la losa hueca a pulso",
             "Recorrer el muro y probar cada marca",
             "Rebuscar entre el polvo hasta que anochezca",
             "Leer las marcas que llevan hasta la losa"),
            "Dejar la losa quieta",
        ),
    },
    "cienaga": {
        FUERZA: EscenaBase(
            "La pasarela rota descansa junto a un tronco seco que encaja justo debajo.",
            ("Reforzar la pasarela con el tronco",
             "Cruzar los tablones mojados de un tirón",
             "Vadear el tramo con el agua por el pecho",
             "Probar los tablones y pisar los que aguantan"),
            "Bordear por la orilla firme",
        ),
        VELOCIDAD: EscenaBase(
            "La niebla se abre un momento y deja un corredor recto entre los juncos.",
            ("Arrancar los juncos de raíz",
             "Cruzar antes de que la niebla cierre",
             "Avanzar en el fango sin parar a descansar",
             "Fijarte en un árbol y no perder el rumbo"),
            "Esperar que aclare",
        ),
        SALUD: EscenaBase(
            "A un pescador se le encalló la barca en el limo, y el agua de la ciénaga está helada y el limo no suelta a la primera.",
            ("Empujar la barca desde suelo firme",
             "Entrar y sacar la barca antes de que cale el frío",
             "Meterte en el agua fría hasta sacarla",
             "Hacer palanca con dos remos cruzados"),
            "Desearle suerte y seguir",
        ),
        INGENIO: EscenaBase(
            "Las burbujas del fango salen siempre por los mismos sitios y dibujan un camino de suelo firme.",
            ("Levantar el tronco anegado y hacer puente",
             "Pasar por la franja de agua quieta",
             "Cruzar el fango pese al frío y al hedor",
             "Pisar por donde las burbujas no salen"),
            "Rodear la charca entera",
        ),
    },
    "arrecife": {
        FUERZA: EscenaBase(
            "Las rocas sueltas tienen cantos donde agarrarlas y hay apoyo seco para tirar de ellas.",
            ("Apartar las rocas por los cantos",
             "Cruzar antes de que rompa la ola",
             "Aguantar el golpe de las olas mientras cruzas",
             "Mirar qué roca sostiene a todas las demás"),
            "Esperar a que baje",
        ),
        VELOCIDAD: EscenaBase(
            "Un banco de peces gira sin parar y al girar abre huecos amplios que duran un instante.",
            ("Empujar contra la corriente y abrir paso",
             "Colarte por un hueco del banco",
             "Nadar el rodeo entero sin salir a respirar",
             "Leer el giro del banco y entrar a tiempo"),
            "Bordear el arrecife",
        ),
        SALUD: EscenaBase(
            "Una buceadora lleva demasiado rato abajo, y el agua de aquí enfría a cualquiera en poco tiempo.",
            ("Levantar la piedra que la tiene atrapada",
             "Bajar hasta ella y subir de una apnea",
             "Aguantar el agua helada las veces que haga falta",
             "Izarla con la boya y el cabo de su red"),
            "Ir a buscar ayuda",
        ),
        INGENIO: EscenaBase(
            "Una red vieja se ha enganchado en el coral y sus nudos se repiten con el mismo orden.",
            ("Tirar de la red hasta arrancarla",
             "Desenredarla entre corrientes cruzadas",
             "Aguantar la corriente mientras la sueltas",
             "Deshacer los nudos en el orden que repiten"),
            "Dejarla donde está",
        ),
    },
    "chatarral": {
        FUERZA: EscenaBase(
            "Una plancha apoyada de canto cierra el paso y deja justo sitio para meter el hombro.",
            ("Volcar la plancha desde el canto",
             "Trepar por la chapa suelta",
             "Meterte por el conducto y aguantar el encierro",
             "Buscar el punto donde la plancha bascula"),
            "Dar un rodeo largo",
        ),
        VELOCIDAD: EscenaBase(
            "Un respiradero abierto queda a un paso, al otro lado de una cinta que no para de moverse.",
            ("Reventar el marco soldado del portón",
             "Colarte por el respiradero de un salto",
             "Aguantar el aire viciado del conducto largo",
             "Parar la cinta desde su propio motor"),
            "Buscar otra entrada",
        ),
        SALUD: EscenaBase(
            "El aceite arde en un extremo y el humo tarda en irse, pero en el camino no queda llama.",
            ("Volcar el depósito lleno sobre el fuego",
             "Cruzar el tramo antes de que prenda",
             "Cruzar el humo sin dejar de avanzar",
             "Cortarle el aire al fuego con una chapa"),
            "Alejarte del humo",
        ),
        INGENIO: EscenaBase(
            "Un chatarrero busca una pieza y las etiquetas de los montones siguen un orden que aún se lee.",
            ("Levantar la tapa del montón por el asa",
             "Rebuscar entre los cables tensos a toda prisa",
             "Rebuscar en el óxido hasta que se haga tarde",
             "Leer las etiquetas y dar con el montón"),
            "Decir que no la viste",
        ),
    },
    "cumbre": {
        FUERZA: EscenaBase(
            "Una placa de hielo cierra el paso sobre roca firme y se puede golpear de lleno desde abajo.",
            ("Romper el hielo golpeando desde abajo",
             "Cruzar por la cornisa pulida",
             "Abrirte paso a golpes con las manos heladas",
             "Golpear por donde el hielo ya está agrietado"),
            "Bajar y rodear",
        ),
        VELOCIDAD: EscenaBase(
            "La ventisca abre un claro y deja ver una bajada recta hasta el refugio.",
            ("Mover la nieve apelmazada del camino",
             "Correr por la bajada mientras se vea",
             "Bajar despacio aguantando la ventisca",
             "Fijar el rumbo por las estacas del refugio"),
            "Refugiarte tras una roca",
        ),
        SALUD: EscenaBase(
            "El paso al otro lado es largo y descubierto, y el frío de aquí arriba no da tregua en todo el trayecto.",
            ("Doblar la cuerda helada del puente",
             "Cruzar el puente de un tirón",
             "Cruzar el paso descubierto sin pararte",
             "Encordarte con lo que llevas antes de cruzar"),
            "Buscar el paso de abajo",
        ),
        INGENIO: EscenaBase(
            "Una cabra perdida ha dejado huellas en la nieve, y las mismas huellas se repiten en dos sitios.",
            ("Separar las rocas donde quedó encajada",
             "Subir por la nieve suelta a toda prisa",
             "Rastrear la ladera entera sin descanso",
             "Leer cuáles de las huellas son las de hoy"),
            "Dejarla donde está",
        ),
    },
    "cavernas": {
        FUERZA: EscenaBase(
            "Los bloques del derrumbe descansan sobre una repisa firme, con hueco para hacer fuerza.",
            ("Apartar los bloques desde la repisa",
             "Colarte por el hueco de grava suelta",
             "Cavar en la grava hasta abrir el paso",
             "Quitar el bloque que sostiene a los demás"),
            "Volver por donde entraste",
        ),
        VELOCIDAD: EscenaBase(
            "Entre dos temblores queda un tramo despejado, y la pausa dura lo justo para cruzarlo.",
            ("Partir la masa de estalactitas",
             "Pasar durante la pausa",
             "Aguantar el polvo y los golpes hasta salir",
             "Contar los temblores y salir en la pausa"),
            "Esperar a que pare",
        ),
        SALUD: EscenaBase(
            "Un espeleólogo no puede con su equipo y hasta la salida quedan horas de cornisas mojadas.",
            ("Cargar el equipo con las correas",
             "Adelantarte por las cornisas a buscar salida",
             "Guiarlo las horas que haga falta",
             "Repartir el equipo y dejar señales al pasar"),
            "Marcar el sitio y avisar",
        ),
        INGENIO: EscenaBase(
            "Las galerías se repiten iguales, pero las paredes tienen marcas de agua a distintas alturas.",
            ("Abrir un paso recto rompiendo la pared fina",
             "Recorrer las galerías hasta dar con la salida",
             "Andar la galería entera sin luz ni descanso",
             "Seguir la marca de agua que va subiendo"),
            "Volver sobre tus pasos",
        ),
    },
    "volcan": {
        FUERZA: EscenaBase(
            "La costra de lava tiene una grieta y roca firme donde apoyar la palanca.",
            ("Abrir la costra con la palanca",
             "Cruzar la costra quebradiza de un tirón",
             "Cruzar la costra aguantando el calor",
             "Golpear por donde la costra ya está partida"),
            "Bordear la colada",
        ),
        VELOCIDAD: EscenaBase(
            "La ceniza deja un corredor breve y despejado hasta el refugio.",
            ("Mover las capas de ceniza compactada",
             "Cruzar el corredor antes de que cierre",
             "Avanzar por la ceniza sin quedarte parado",
             "Leer el viento y salir cuando abra el paso"),
            "Buscar refugio",
        ),
        SALUD: EscenaBase(
            "Un buscador se ha quedado sin agua y el trecho hasta la fuente es largo y va todo a pleno calor.",
            ("Cargarlo tú en la parihuela",
             "Correr a la fuente y volver con agua",
             "Llevarlo el trecho entero bajo el calor",
             "Sacar agua condensándola con una lona"),
            "Avisar en el poblado",
        ),
        INGENIO: EscenaBase(
            "La obsidiana del marco está partida en vetas y sólo una recorre la puerta de lado a lado.",
            ("Arrancar la puerta encajada en el basalto",
             "Colarte por la grieta antes de que llegue el humo",
             "Aguantar el calor del marco mientras lo abres",
             "Partir la obsidiana siguiendo su veta"),
            "Alejarte del calor",
        ),
    },
}


def escena_escrita(bioma: Bioma, pareja: Pareja, favorecida: str) -> Escena:
    """El respaldo del bioma, proyectado sobre la pareja que salió.

    Es **determinista**, sin `rng` ni escena que evitar: dentro de un viaje las
    dos parejas son complementarias, así que los dos nodos nunca comparten la
    estadística favorecida y no hay forma de repetir situación.
    """
    if pareja not in PAREJAS:
        raise ValueError(f"pareja desconocida: {pareja!r}")
    if favorecida not in pareja:
        raise ValueError(f"lado desconocido: {favorecida!r}")
    base = ESCENAS_ESCRITAS[bioma.clave][favorecida]
    return Escena(
        base.situacion, pareja,
        (base.etiqueta(pareja[0]), base.etiqueta(pareja[1])),
        base.volver,
    )


def resolver_opcion(
    criatura: sim.Criatura,
    terreno: Terreno,
    opcion: str,
    rng: random.Random | None = None,
    obstaculo: str = "",
) -> Prueba | None:
    """La tirada de una opción, o `None` si es la de volver, que nunca falla."""
    if opcion == VOLVER:
        return None
    dificultad = terreno.exigencia(opcion)
    base = getattr(criatura, opcion)
    return Prueba(
        obstaculo=obstaculo,
        stat=opcion,
        base=base,
        dado=(rng or random.Random()).randint(1, CARA_DADO),
        dificultad=dificultad,
    )


@dataclass(frozen=True)
class Viaje:
    """El estado del árbol entre pulsación y pulsación.

    Es inmutable y no guarda nada de Discord, así que el cog puede sostenerlo en
    la vista y los tests recorrer el árbol entero con dados fijos.
    """

    bioma: Bioma
    escena: Escena
    terreno: Terreno
    pruebas: tuple[Prueba, ...] = ()
    nivel: int = 0
    fallo: bool = False

    def __post_init__(self) -> None:
        if self.escena.pareja != self.terreno.pareja:
            raise ValueError("la escena y el terreno deben usar la misma pareja")

    @property
    def nodos_superados(self) -> int:
        return sum(1 for p in self.pruebas if p.superada)

    @property
    def sigue(self) -> bool:
        return not self.fallo and self.nivel < NIVELES_DE_AVENTURA

    @property
    def salida(self) -> Salida:
        """El viaje visto como lo ve el resto del módulo.

        El coste de hambre, el percance y la XP siguen calculándose sobre las
        pruebas, que es lo que ya existía; el árbol sólo cambia quién las elige.
        """
        return Salida(self.pruebas)

    @property
    def coste_hambre(self) -> float:
        return self.salida.coste_hambre


def avanzar(
    viaje: Viaje,
    criatura: sim.Criatura,
    opcion: str,
    siguiente: Escena | None,
    siguiente_terreno: Terreno | None,
    rng: random.Random | None = None,
) -> Viaje:
    """Aplica una decisión y cambia escena y terreno juntos o ninguno."""
    if (siguiente is None) != (siguiente_terreno is None):
        raise ValueError("escena y terreno siguientes deben cambiar juntos")
    prueba = resolver_opcion(
        criatura, viaje.terreno, opcion, rng, viaje.escena.etiqueta(opcion)
    )
    fallo = prueba is not None and not prueba.superada
    return Viaje(
        bioma=viaje.bioma,
        escena=siguiente or viaje.escena,
        terreno=siguiente_terreno or viaje.terreno,
        pruebas=viaje.pruebas + ((prueba,) if prueba else ()),
        nivel=viaje.nivel + 1,
        fallo=fallo,
    )


# --- Qué te encuentras -----------------------------------------------------

NADA = "nada"
OBJETO = "objeto"
SALVAJE = "salvaje"

# Probabilidad de cada final según cuántos nodos del árbol se superaron.
#
# El salvaje sólo aparece llegando al fondo: es el gachamon dormido dentro del
# cofre, y quedarse a medias no puede pagar lo mismo que llegar. El 55 no es un
# número redondo por casualidad: midiendo 40 000 aventuras con criaturas recién
# nacidas, el árbol termina con los dos nodos el 46 % de las veces, y 55 deja el
# reclutamiento en el 25 % de las aventuras, exactamente donde estaba antes del
# árbol. Concentrar el premio al fondo no podía salir por la puerta de atrás
# como una subida de dificultad.
HALLAZGOS = {
    2: {SALVAJE: 55, OBJETO: 25, NADA: 20},
    1: {SALVAJE: 0, OBJETO: 55, NADA: 45},
    0: {SALVAJE: 0, OBJETO: 30, NADA: 70},
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


# Lo que te puedes encontrar por el camino además de lo de siempre. Se tira
# **aparte** del hallazgo de objeto/salvaje/nada, no como una rama más: así
# aparecen encima de lo que ya haya y no tocan las probabilidades de aquéllos,
# que están calibradas.
#
# Los números salen de que la aventura tiene 37 min de espera: hasta 38 al día.
# Al 4 % con 1-10, eso son ~8 asciicoins diarios, que dejan sitio en el bote de
# 20 para lo que se gana cuidando y compitiendo. Las gemas, al 0,5 % con 1-5,
# salen a una cada dos días largos: son un golpe de suerte, no una renta.
# Van **por mil** y no por ciento porque las gemas caen al 0,5 % y con enteros no
# hay forma de escribir medio punto. Se tira con `randint` como el resto del
# módulo, y no con `uniform`, para que los dados fijos de los tests sigan
# valiendo: aquí todo se prueba con tiradas puestas a mano.
POR_MIL = 1000
PROBABILIDAD_MONEDAS = 40       # 4 %
MONEDAS_ENCONTRADAS = (1, 10)
PROBABILIDAD_GEMAS = 5          # 0,5 %
GEMAS_ENCONTRADAS = (1, 5)


def tirar_monedas(rng: random.Random | None = None) -> int:
    """Cuántos asciicoins te encuentras, o 0. Se cobran dentro del bote."""
    rng = rng or random.Random()
    if rng.randint(1, POR_MIL) > PROBABILIDAD_MONEDAS:
        return 0
    return rng.randint(*MONEDAS_ENCONTRADAS)


def tirar_gemas(rng: random.Random | None = None) -> int:
    """Cuántos asciigems te encuentras, o 0. Éstos no tienen tope."""
    rng = rng or random.Random()
    if rng.randint(1, POR_MIL) > PROBABILIDAD_GEMAS:
        return 0
    return rng.randint(*GEMAS_ENCONTRADAS)


def tirar_objeto(rng: random.Random | None = None) -> obj.Objeto:
    """Un objeto del catálogo, **sorteado a la inversa del precio**.

    Las golosinas y las pociones pequeñas son corrientes; una de 1d12 es un
    hallazgo. Se apoya en los precios que ya existen en vez de mantener una
    segunda tabla que se desincronizaría al tocar la tienda.

    Sólo se encuentra lo que está a la venta. Lo demás —porotos y sopaipillas—
    se cosecha y se cocina, y además vale 0: repartir por el precio daría una
    división por cero, que es exactamente cómo se descubrió.
    """
    rng = rng or random.Random()
    objetos = [o for o in obj.CATALOGO.values() if o.se_vende]
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
    stats: tuple[int, int, int, int]

    @property
    def def_especie(self) -> esp.Especie:
        return esp.ESPECIES[self.especie]


def tirar_salvaje(bioma: Bioma, rng: random.Random | None = None) -> Salvaje:
    """Con quién te cruzas, **pesado por la rareza**.

    Antes era uniforme y una rara salía tanto como sus vecinas comunes: su
    rareza sólo se notaba en las estadísticas y en la etiqueta de la ficha. El
    peso sale de `esp.PESO_EN_EL_CAMPO`, el mismo reparto que usa el huevo.
    """
    rng = rng or random.Random()
    pesos = [esp.PESO_EN_EL_CAMPO[esp.ESPECIES[e].rareza] for e in bioma.especies]
    definicion = esp.ESPECIES[
        rng.choices(list(bioma.especies), weights=pesos, k=1)[0]
    ]
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

# Cuánta confianza hay que reunir para que se una. Es la palanca de dificultad
# del reclutamiento, y la única que hace falta tocar para apretarlo o aflojarlo.
#
# Ha ido y vuelto, y las dos veces por una razón medida:
#
# * **100 → 90** el 2026-07-31, porque costaba demasiado: a ciegas se reclutaba
#   el 22 % de los encuentros.
# * **90 → 100** al subir el plantel a 25. Con 90, quien se sabía la tabla de
#   caracteres reclutaba el **100 %** de las veces y el encuentro dejaba de
#   tener riesgo; con veinticinco huecos que llenar, eso convertía la fase de
#   reclutar en un trámite largo en vez de en una apuesta.
#
# Medido ahora: jugando bien sale el **93 %** y a ciegas el **22 %**. Volver a
# tocarlo es legítimo, pero hazlo con los números delante y no a ojo — ver
# `test_leerle_el_caracter_sigue_notandose`, que vigila que leerle el carácter
# se siga notando pase lo que pase con este número.
CONFIANZA_PARA_UNIRSE = 100

# Si el recelo llega aquí, se larga. Es el segundo eje, y existe porque con uno
# solo el encuentro se resolvía con un `argmax`: probabas una opción, la pista
# te decía si le gustaba, y repetías esa misma hasta ganar. **Medido, repetir la
# mejor reclutaba en 9 de los 10 caracteres.**
#
# Con dos ejes en tensión hay que llenar la confianza SIN llenar el recelo, y
# como lo que más confianza da es lo que más recelo levanta, machacar la mejor
# opción te delata. El bucle que funciona es empujar y dejar respirar.
RECELO_QUE_ESPANTA = 100

# Turnos que dura el encuentro. Subió de 4 a 6 con el recelo: con dos barras que
# gestionar, cuatro jugadas no daban para alternar ni una vez.
PACIENCIA_INICIAL = 6
CARA_DADO_CONFIANZA = 6

# Cuánto suma cada opción antes del carácter y del dado.
#
# Los números están medidos, no puestos a ojo: se recorrió una rejilla de 2673
# combinaciones simulando 1200 encuentros cada una, con el reparto real de
# confianza inicial. Sobre 6000 encuentros, el punto elegido da:
#
#     empujando y dejando respirar .... 87 %
#     pulsando al azar ................ 34 %
#     repitiendo la mejor opción ...... 31 %
#
# **La tercera línea es la que importa**: antes repetir la mejor reclutaba en 9
# de los 10 caracteres, y ahora sale peor que pulsar al azar. Ninguna
# combinación de la rejilla lograba a la vez que jugar bien pasara del 85 % y
# que el azar bajara del 30 %: para que lo primero salga hay que ser generoso, y
# entonces al azar también le toca de vez en cuando. Se eligió proteger a quien
# juega bien.
BASE = {HABLAR: 4, GOLOSINAS: 5, PRESUMIR: 4, ESPERAR: 9}

# Lo que cada opción levanta de recelo antes del carácter. **Aquí está el juego
# nuevo**: el riesgo es de la opción y no sólo del bicho, así que las que más
# confianza dan son las que más desconfianza siembran.
#
#   🎭 presumir  — el empujón caro: mucha confianza, mucho recelo.
#   🍬 golosinas — empujón, y además gasta una golosina de tu mochila.
#   💬 hablar    — el relleno seguro: poco de lo uno y poco de lo otro.
#   🧘 esperar   — el respiro: casi no convence, pero LO BAJA.
RECELO = {HABLAR: 6, GOLOSINAS: 34, PRESUMIR: 36, ESPERAR: -34}

# **El carácter manda en un eje por opción, y ésa es la regla que sostiene todo
# el sistema.**
#
#   * En los empujones manda sobre la **confianza**: acertar convence más, pero
#     el recelo cuesta lo mismo pase lo que pase. Si acertar además abaratara el
#     recelo, repetir la favorita volvería a ser la jugada óptima y no habríamos
#     arreglado nada, sólo movido el problema de sitio.
#   * En esperar manda sobre el **recelo**: a un miedoso quedarse quieto le
#     tranquiliza mucho más que a un travieso, pero la confianza que da es la
#     misma para todos. Con el carácter puesto también aquí, a un miedoso se le
#     ganaba repitiendo esperar —su favorita, sin recelo y sin nada que
#     gestionar—, que era el mismo agujero por otra puerta.

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
    recelo: int = 0
    paciencia: int = PACIENCIA_INICIAL
    # Lo que acaba de pasar, para narrarlo.
    ultimo_cambio: int = 0
    ultimo_recelo: int = 0

    @property
    def se_une(self) -> bool:
        return self.confianza >= CONFIANZA_PARA_UNIRSE

    @property
    def se_asusta(self) -> bool:
        """Se le llenó el recelo. Es perder por empujar demasiado."""
        return self.recelo >= RECELO_QUE_ESPANTA and not self.se_une

    @property
    def se_aburre(self) -> bool:
        """Se acabaron los turnos. Es perder por no arriesgar lo suficiente."""
        return self.paciencia <= 0 and not self.se_une and not self.se_asusta

    @property
    def se_larga(self) -> bool:
        """Se fue sin unirse, por el motivo que sea.

        Las dos causas se distinguen aparte porque la narración las cuenta
        distinto: no es lo mismo espantarlo que aburrirlo, y quien juega necesita
        saber cuál de las dos cosas hizo para corregir.
        """
        return self.se_asusta or self.se_aburre

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
    cambio = confianza_de(opcion, reaccion) + rng.randint(1, CARA_DADO_CONFIANZA)
    recelo = recelo_de(opcion, reaccion)

    # Un turno es un turno, le guste o no. El gasto doble por elegir mal era el
    # parche anti-repetición de cuando sólo había un eje; ahora ese trabajo lo
    # hace el recelo, y cobrarlo dos veces castigaría dos veces lo mismo.
    return replace(
        encuentro,
        confianza=max(0, min(100, encuentro.confianza + cambio)),
        recelo=max(0, min(RECELO_QUE_ESPANTA, encuentro.recelo + recelo)),
        paciencia=encuentro.paciencia - 1,
        ultimo_cambio=cambio,
        ultimo_recelo=recelo,
    )


def confianza_de(opcion: str, reaccion: int) -> int:
    """Cuánta confianza da esa opción, antes del dado.

    **Esperar no lleva el carácter**, y ésa es la pieza que hace que el sistema
    funcione. Con él puesto, a un miedoso —que adora que lo dejen en paz— le
    ganabas repitiendo esperar: su mejor opción era el respiro, no levantaba
    recelo y no había nada que gestionar. Quedarse quieto **calma** mucho a
    quien es asustadizo, pero no se gana su confianza sin hacer nada, así que su
    carácter influye en el otro eje y no en éste.
    """
    if RECELO[opcion] <= 0:
        return BASE[opcion]
    return BASE[opcion] + reaccion


def recelo_de(opcion: str, reaccion: int) -> int:
    """Cuánto recelo levanta esa opción con esa reacción.

    Lo que le gusta le baja la guardia, pero **un empujón nunca sale gratis**:
    por mucho que acierte, sigue costando `RECELO_MINIMO_AL_EMPUJAR`. Sin ese
    suelo, el carácter podría dejar en cero el recelo de su opción favorita y
    repetirla volvería a ser la jugada óptima.

    Esperar es la excepción y por eso el suelo no le aplica: su trabajo es
    justamente bajar el recelo, y acertar con él tiene que bajarlo más.
    """
    base = RECELO[opcion]
    if base > 0:
        # Un empujón cuesta lo que cuesta: acertar con el carácter da más
        # confianza, no menos guardia. Si además lo abaratara, repetir la
        # favorita volvería a ser la jugada óptima y no habríamos arreglado
        # nada — sólo movido el problema de sitio.
        return base
    # Calmarse sí depende del carácter, y es donde vive su mitad del juego: a
    # un miedoso quedarse quieto le tranquiliza mucho más que a un travieso.
    return base - reaccion


def le_gusta(salvaje: Salvaje, opcion: str) -> bool:
    return REACCIONES[salvaje.caracter][opcion] >= 0


def narrar_opcion(antes: Encuentro, opcion: str, despues: Encuentro) -> str:
    """Lo que movió la jugada, con los dos números.

    Se enseñan crudos y no en palabras: con dos barras que gestionar hay que
    poder echar la cuenta de cuántos empujones caben antes de espantarlo, y
    «se pone a la defensiva» no da para eso. El carácter sigue oculto — lo que
    se ve es el efecto, no la tabla.
    """
    emoji, etiqueta = ETIQUETAS[opcion]
    if despues.se_asusta and not antes.se_asusta:
        return f"-# {emoji} {etiqueta} · **Lo has espantado.**"
    if despues.se_aburre and not antes.se_aburre:
        return f"-# {emoji} {etiqueta} · **Se cansa de esperar y se va.**"
    partes = [f"confianza {despues.confianza - antes.confianza:+d}"]
    recelo = despues.recelo - antes.recelo
    if recelo:
        partes.append(f"recelo {recelo:+d}")
    return f"-# {emoji} {etiqueta} · " + " · ".join(partes)


MAX_HISTORIAL_ENCUENTRO = 4
LARGO_CONTESTO_HISTORIAL = 160


@dataclass(frozen=True)
class TurnoHablar:
    dicho: str
    contesto: str


@dataclass(frozen=True)
class TurnoGesto:
    accion: str
    reaccion: str


EventoEncuentro = TurnoHablar | TurnoGesto


_FRASES_GESTO = {
    (GOLOSINAS, True): "te ofrecieron golosinas y las devoraste",
    (GOLOSINAS, False): "te ofrecieron golosinas y las apartaste de un manotazo",
    (PRESUMIR, True): "su gachamon presumió delante de ti y te picó la curiosidad",
    (PRESUMIR, False): "su gachamon presumió delante de ti y no te hizo ninguna gracia",
    (ESPERAR, True): "se quedaron quietos, sin agobiarte, y lo agradeciste",
    (ESPERAR, False): "se quedaron quietos un buen rato y te aburriste",
}


def frase_gesto(accion: str, gusto: bool) -> str:
    try:
        return _FRASES_GESTO[(accion, gusto)]
    except KeyError as exc:
        raise ValueError(f"gesto desconocido: {accion!r}") from exc


def recordar(
    historial: tuple[EventoEncuentro, ...], evento: EventoEncuentro,
) -> tuple[EventoEncuentro, ...]:
    if isinstance(evento, TurnoHablar):
        evento = replace(
            evento, contesto=evento.contesto[:LARGO_CONTESTO_HISTORIAL]
        )
    return (historial + (evento,))[-MAX_HISTORIAL_ENCUENTRO:]


def fase_de(confianza: int) -> str:
    if confianza < 40:
        return "arisco"
    if confianza < 70:
        return "receloso"
    return "cercano"


def tendencia_de(antes: Encuentro, despues: Encuentro) -> str:
    if despues.paciencia < antes.paciencia - 1:
        return "recela"
    if despues.confianza > antes.confianza:
        return "mejora"
    return "estancada"


@dataclass(frozen=True)
class ContextoSalvaje:
    salvaje: Salvaje
    acompañante: sim.Criatura
    fase: str
    fase_ahora: str
    tendencia: str
    paciencia: int
    dicho: str
    historial: tuple[EventoEncuentro, ...] = ()


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


def esfuerzos_de_viaje(salida: Salida) -> tuple[sim.Esfuerzo, ...]:
    """Convierte las pruebas ya resueltas en emisiones, en orden real."""
    esfuerzos: list[sim.Esfuerzo] = []
    for prueba in salida.pruebas:
        esfuerzos.append(sim.esfuerzo_de_aventura(
            prueba.stat, prueba.holgura
        ))
        if not prueba.superada:
            # El fallo añade SAL 1.0, que por sí solo no supera el filtro.
            esfuerzos.append(sim.Esfuerzo(
                "salud", 1.0, causa=sim.AVENTURA
            ))
    return tuple(esfuerzos)


def aplicar_viaje(
    criatura: sim.Criatura, salida: Salida, ahora: datetime,
    percance: Percance | None = None, rng: random.Random | None = None,
) -> tuple[sim.Criatura, list[sim.Ruptura]]:
    """Cobra el viaje, emite sus pruebas y da XP sólo si vuelve con vida."""
    cansada = aplicar_desgaste(criatura, salida, ahora, percance)
    if not cansada.viva:
        return cansada, []
    estado, rupturas = sim.aplicar_evento(
        cansada, esfuerzos_de_viaje(salida), sim.XP_AVENTURA, rng
    )
    return estado, list(rupturas)


def render_percance(percance: Percance | None) -> str:
    """Efecto mecánico visible, independiente de lo que escriba el modelo."""
    if percance is None:
        return ""
    return f"⚠️ Percance: -{percance.hambre} comida y -{percance.animo} ánimo."


def quienes_van(criatura: sim.Criatura, dueño: str) -> str:
    """«Felipe y Pelusa». A la aventura van los dos, y así se cuenta.

    En plural de **ustedes**, nunca de vosotros: «Felipe y Pelusa salen», que es
    lo que manda `REGLA_ESPANOL_NEUTRO` en todo el bot.
    """
    return f"{dueño} y {criatura.nombre}"


def resumen_escrito(
    criatura: sim.Criatura, bioma: Bioma, salida: Salida, hallazgo: str,
    percance: Percance | None = None, *, dueño: str,
) -> str:
    """La narración cuando no hay presupuesto de IA.

    La aventura no puede quedarse muda porque se haya agotado el límite, igual
    que las criaturas nunca se quedan sin frase.
    """
    van = quienes_van(criatura, dueño)
    if not salida.pruebas:
        # Con el árbol se puede volver de todo sin haber tirado un solo dado, y
        # decir entonces que «no se le resiste nada» sería contar otro viaje.
        viaje = f"{van} salen {bioma.adonde} y no se meten en nada."
    elif salida.superadas == len(salida.pruebas):
        viaje = f"{van} salen {bioma.adonde} y no se les resiste nada."
    elif salida.superadas:
        viaje = f"{van} salen {bioma.adonde} y tienen problemas en un tramo."
    else:
        viaje = f"{van} salen {bioma.adonde} y vuelven en muy mal estado."

    if percance is not None:
        viaje += " Sufren un percance durante el trayecto."

    finales = {
        SALVAJE: "Algo se mueve ahí al lado.",
        OBJETO: "Y algo brilla entre las piedras.",
        NADA: "No hay nadie más por aquí.",
    }
    return f"{viaje} {finales[hallazgo]}"


# --- El marco de las pruebas ------------------------------------------------


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
    percance: Percance | None = None, *, dueño: str,
) -> str:
    """El marco del viaje. El emoji del bioma va FUERA, como siempre.

    La cabecera nombra a los dos y también va fuera del bloque, así que un
    nombre largo no descuadra nada: dentro del marco no entra ninguno.
    """
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
            f" {marca} {pantalla.ETIQUETAS_STAT[prueba.stat]} "
            f"{prueba.base:>{ancho_base}}+d20 {prueba.dado:>2} = "
            f"{prueba.total:>{ancho_total}}/{prueba.dificultad} "
        ))
    cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")

    texto = (
        f"## {bioma.emoji} {quienes_van(criatura, dueño)} salen {bioma.adonde}\n"
        "```ansi\n" + "\n".join(cuerpo) + "\n```"
    )
    hambre, animo = coste_desgaste(salida, percance)
    desgaste = pantalla.recibo(
        f"🥾 Desgaste total: -{hambre:g} comida", f"-{animo:g} ánimo"
    )
    efecto = render_percance(percance)
    return "\n".join(parte for parte in (texto, desgaste, efecto) if parte)
