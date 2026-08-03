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


def _escena_fv(
    situacion: str, fuerza: str, velocidad: str, volver: str,
) -> Escena:
    """Adaptador transitorio del catálogo F/V; la fase 2 lo reemplazará."""
    return Escena(situacion, (FUERZA, VELOCIDAD), (fuerza, velocidad), volver)


# Las escenas escritas a mano. Aunque las invente el modelo, hacen falta: es lo
# que se juega cuando la IA no está o se agotó el límite, igual que las criaturas
# nunca se quedan sin frase. Una aventura muda no es una aventura.
#
# Van variadas a propósito, y no sólo puertas y muros: en cada bioma hay algo
# cerrado, alguien con quien cruzarse y algo que está pasando. Si todas fueran
# obstáculos, el respaldo cantaría al segundo viaje y el modelo tendería a
# copiar la única forma que ve.
ESCENAS_ESCRITAS: dict[str, dict[str, tuple[Escena, Escena]]] = {
    "bosque": {
        FUERZA: (
            _escena_fv("Una puerta hinchada cede hacia afuera y tiene un tronco firme donde apoyar el hombro.",
                   "Empujar la puerta", "Colarte por la ventana enredada",
                   "Seguir el sendero"),
            _escena_fv("El carro de un leñador está calzado, pero su eje quedó hundido en barro espeso.",
                   "Levantar el eje apoyándote", "Calzar la rueda entre raíces",
                   "Desearle suerte y seguir"),
        ),
        VELOCIDAD: (
            _escena_fv("Bajo un panal queda un tramo limpio; la rama que lo sostiene es gruesa y está muy alta.",
                   "Bajar la rama trabada", "Cruzar el tramo de un tirón",
                   "Dar un rodeo"),
            _escena_fv("Una rama enorme cruje lejos; el sendero queda recto, pero sujetarla exigiría arrancar raíces.",
                   "Aguantar la rama enraizada", "Cruzar antes de que caiga",
                   "Refugiarte y esperar"),
        ),
    },
    "planicie": {
        FUERZA: (
            _escena_fv("La losa de un pozo sobresale y deja hueco para meter ambas manos; la cuerda cuelga muy lejos.",
                   "Levantar la losa", "Alcanzar la cuerda de un salto",
                   "Dejarlo estar"),
            _escena_fv("Un rebaño entra por un paso angosto con una cerca firme a la espalda; el flanco está lleno de hoyos.",
                   "Plantarte contra la cerca", "Esquivarlo por los hoyos",
                   "Tumbarte en la hierba"),
        ),
        VELOCIDAD: (
            _escena_fv("Una pastora ve entre los fardos un pasillo despejado hacia su oveja; cada fardo está empapado y pesa demasiado.",
                   "Apartar los fardos mojados", "Recorrer el pasillo corriendo",
                   "Decir que no la viste"),
            _escena_fv("Una lona vuela baja sobre campo abierto; el poste que la sujetaba está clavado hasta la piedra.",
                   "Arrancar el poste clavado", "Atrapar la lona al vuelo",
                   "Dejar que se la lleve"),
        ),
    },
    "desierto": {
        FUERZA: (
            _escena_fv("Una columna sobresale con base redonda y sitio para hacer palanca; alrededor la arena se hunde al correr.",
                   "Volcar la columna con palanca", "Saltar sobre la arena suelta",
                   "Buscar sombra"),
            _escena_fv("La caravana apoya un fardo en una tarima firme; las huellas ya se borran entre dunas separadas.",
                   "Cargar el fardo apoyado", "Seguir las huellas lejanas",
                   "Seguir tu camino"),
        ),
        VELOCIDAD: (
            _escena_fv("Al ceder el suelo queda un borde corto y limpio; sostenerlo exigiría cargar una placa entera de roca.",
                   "Sostener la placa de roca", "Saltar el borde de un impulso",
                   "Retroceder sobre tus huellas"),
            _escena_fv("Un cubo cuelga a un salto dentro del brocal; la cadena está encajada bajo un bloque macizo.",
                   "Arrancar la cadena encajada", "Bajar y tomar el cubo",
                   "Seguir la duna"),
        ),
    },
    "ruinas": {
        FUERZA: (
            _escena_fv("El portón de bronce está entreabierto y tiene un puntal firme; la hiedra cuelga rota y lejos.",
                   "Empujar desde el puntal", "Trepar por la hiedra rota",
                   "Rodear la muralla"),
            _escena_fv("Alguien quedó bajo una viga apoyada sobre un bloque firme; el suelo alrededor está cubierto de cascotes.",
                   "Levantar la viga apoyada", "Sacar a alguien entre cascotes",
                   "Ir a buscar ayuda"),
        ),
        VELOCIDAD: (
            _escena_fv("Una bandada deja un hueco recto al girar; cerrarles el paso exigiría mover una estatua maciza.",
                   "Mover la estatua maciza", "Cruzar mientras dure el hueco",
                   "Esperar a que se calmen"),
            _escena_fv("Bajo una losa queda una rendija lisa y cercana; la argolla está fundida con toda la piedra.",
                   "Levantar la losa fundida", "Colarte por la rendija",
                   "Dejar la losa quieta"),
        ),
    },
    "cienaga": {
        FUERZA: (
            _escena_fv("La pasarela descansa junto a un tronco seco que encaja debajo; los tablones libres resbalan al pisarlos rápido.",
                   "Reforzarla con el tronco", "Cruzar los tablones mojados",
                   "Vadear por la orilla"),
            _escena_fv("La barca de un pescador tiene la popa contra suelo firme; el limo alrededor llega hasta las rodillas.",
                   "Empujar desde suelo firme", "Sacar el limo a zancadas",
                   "Desearle suerte y seguir"),
        ),
        VELOCIDAD: (
            _escena_fv("La niebla aún deja un corredor recto entre juncos; arrancarlos requeriría sacar sus raíces del fango.",
                   "Arrancar los juncos enraizados", "Cruzar antes de que cierre",
                   "Esperar que aclare"),
            _escena_fv("Algo se hunde y abre una franja de agua quieta; golpearlo exige levantar un tronco anegado.",
                   "Levantar el tronco anegado", "Pasar por la franja quieta",
                   "Rodear la charca entera"),
        ),
    },
    "arrecife": {
        FUERZA: (
            _escena_fv("Las rocas sueltas tienen cantos para agarrarlas y apoyo seco; la próxima ola ya rompe muy cerca.",
                   "Apartar las rocas apoyadas", "Cruzar antes de la ola",
                   "Esperar a que baje"),
            _escena_fv("Una red queda al alcance sobre coral firme; desenredarla obliga a nadar entre corrientes cruzadas.",
                   "Tirar de la red apoyándote", "Desenredarla entre corrientes",
                   "Dejarla donde está"),
        ),
        VELOCIDAD: (
            _escena_fv("Una corriente recta lleva hasta una buceadora; la piedra que la atrapa está encajada en todo el arrecife.",
                   "Levantar la piedra encajada", "Nadar con la corriente",
                   "Ir a buscar ayuda"),
            _escena_fv("Un banco de peces abre huecos amplios al girar; apartarlo exigiría empujar contra toda la corriente.",
                   "Empujar contra la corriente", "Colarte por un hueco",
                   "Bordear el arrecife"),
        ),
    },
    "chatarral": {
        FUERZA: (
            _escena_fv("Una plancha cierra el paso apoyada de canto y deja sitio para el hombro; arriba sólo hay chapa suelta.",
                   "Volcar la plancha apoyada", "Trepar por la chapa suelta",
                   "Dar un rodeo largo"),
            _escena_fv("La pieza que busca un chatarrero está bajo una tapa con asa; rebuscar obliga a cruzar cables tensos.",
                   "Levantar la tapa por el asa", "Rebuscar entre cables tensos",
                   "Decir que no la viste"),
        ),
        VELOCIDAD: (
            _escena_fv("El aceite arde en un extremo y deja una franja despejada; ahogarlo exigiría mover un depósito lleno.",
                   "Volcar el depósito lleno", "Apartar lo que arde rápido",
                   "Alejarte del humo"),
            _escena_fv("Un respiradero queda a un paso tras una cinta móvil; el portón está soldado a un marco macizo.",
                   "Reventar el marco soldado", "Colarte por el respiradero",
                   "Buscar otra entrada"),
        ),
    },
    "cumbre": {
        FUERZA: (
            _escena_fv("Una placa de hielo sobresale sobre roca firme y se puede golpear desde abajo; la cornisa exterior está pulida.",
                   "Romper el hielo apoyándote", "Cruzar la cornisa pulida",
                   "Bajar y rodear"),
            _escena_fv("Dos rocas dejan una cuña natural junto a una cabra; el otro acceso baja por nieve suelta.",
                   "Separar las rocas con cuña", "Bajar por la nieve suelta",
                   "Dejarla donde está"),
        ),
        VELOCIDAD: (
            _escena_fv("La ventisca deja visible una bajada recta al refugio; abrir camino exige mover nieve apelmazada.",
                   "Mover la nieve apelmazada", "Correr por la bajada visible",
                   "Refugiarte tras una roca"),
            _escena_fv("El puente queda recto entre dos anclajes; su cuerda helada está rígida como una barra de hierro.",
                   "Doblar la cuerda helada", "Cruzar de un tirón",
                   "Buscar el paso de abajo"),
        ),
    },
    "cavernas": {
        FUERZA: (
            _escena_fv("Los bloques del derrumbe descansan sobre una repisa firme; el hueco superior es estrecho y tiene grava suelta.",
                   "Apartar los bloques apoyados", "Colarte por el hueco suelto",
                   "Volver por donde entraste"),
            _escena_fv("El equipo de un espeleólogo tiene correas y apoyo para cargarlo; la salida queda tras cornisas mojadas.",
                   "Cargar el equipo con correas", "Guiarlo por cornisas mojadas",
                   "Marcar el sitio y avisar"),
        ),
        VELOCIDAD: (
            _escena_fv("Una corriente corta cruza el lago hasta la otra orilla; la roca para un puente está fundida al suelo.",
                   "Arrancar la roca del suelo", "Cruzar siguiendo la corriente",
                   "Bordearlo por la cornisa"),
            _escena_fv("Entre dos temblores queda un tramo despejado; las estalactitas forman una sola masa sobre la bóveda.",
                   "Partir la masa de piedra", "Pasar durante la pausa",
                   "Esperar a que pare"),
        ),
    },
    "volcan": {
        FUERZA: (
            _escena_fv("La costra de lava tiene una grieta y roca firme para la palanca; el tramo para correr se deshace bajo los pies.",
                   "Abrir la costra con palanca", "Cruzar la costra quebradiza",
                   "Bordear la colada"),
            _escena_fv("Un buscador descansa junto a una parihuela sólida; el agua está detrás de una ladera de ceniza suelta.",
                   "Cargarlo en la parihuela", "Correr por la ceniza suelta",
                   "Avisar en el poblado"),
        ),
        VELOCIDAD: (
            _escena_fv("La ceniza deja un corredor breve hacia el refugio; apartarla exige mover capas compactadas por el calor.",
                   "Mover la ceniza compactada", "Cruzar por el corredor",
                   "Buscar refugio"),
            _escena_fv("Una grieta recta atraviesa el marco de obsidiana; la puerta es una sola pieza encajada en basalto.",
                   "Arrancar la puerta encajada", "Colarte por la grieta",
                   "Alejarte del calor"),
        ),
    },
}


def escena_escrita(
    bioma: Bioma, pareja: Pareja, favorecida: str,
    evitar: Escena | None = None, rng: random.Random | None = None,
) -> Escena:
    """Respaldo F/V transitorio, ya devuelto con la forma de escena nueva."""
    if pareja != (FUERZA, VELOCIDAD):
        raise ValueError("el catálogo de cuatro stats se completa en la fase 2")
    if favorecida not in pareja:
        raise ValueError(f"lado desconocido: {favorecida!r}")
    posibles = [
        escena for escena in ESCENAS_ESCRITAS[bioma.clave][favorecida]
        if escena != evitar
    ]
    return (rng or random.Random()).choice(posibles)


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

# Cuánta confianza hay que reunir para que se una. Bajó de 100 a 90 el
# 2026-07-31 porque costaba demasiado: a ciegas se reclutaba un 27 % de los
# encuentros y ahora un 42 %. Es la palanca de dificultad del reclutamiento, y
# la única que hace falta tocar para apretarlo o aflojarlo.
#
# Tiene un coste asumido: con 90, quien se sabe la tabla de caracteres recluta
# el 100 % de las veces. Antes el tope estaba puesto justamente para que no
# fuera seguro; se soltó a conciencia. Ver
# `test_leerle_el_caracter_sigue_notandose`.
CONFIANZA_PARA_UNIRSE = 90
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
    """Da una pista fija del cambio real, sin revelar carácter ni delta crudo."""
    emoji, etiqueta = ETIQUETAS[opcion]
    if despues.se_larga and not antes.se_larga:
        pista = "Su paciencia se agota."
    elif (
        despues.confianza < antes.confianza
        or despues.paciencia < antes.paciencia - 1
    ):
        pista = "Se pone a la defensiva."
    elif despues.confianza > antes.confianza:
        pista = "Ahora confía más."
    else:
        pista = "No termina de decidirse."
    return f"-# {emoji} {etiqueta} · {pista}"


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
