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

# Cada escena ofrece las tres, siempre. Fuerza y velocidad tiran contra la misma
# dificultad a propósito: si una fuera más barata, nadie elegiría la otra y la
# decisión sería un adorno.
FUERZA = "fuerza"
VELOCIDAD = "velocidad"
VOLVER = "volver"
OPCIONES_ESCENA = (FUERZA, VELOCIDAD, VOLVER)

# Cuántas decisiones dura una aventura. Volver también gasta una: es la salida
# sin riesgo, no una forma de seguir mirando escenas hasta que salga una fácil.
NIVELES_DE_AVENTURA = 2


@dataclass(frozen=True)
class Escena:
    """La ficción de un nodo: qué pasa y cómo se llaman las tres salidas.

    La escribe el modelo, pero **no decide nada**: quién pasa y quién no sale de
    `stat + 1d20` contra la dificultad del bioma, igual que antes. Por eso el
    texto puede venir de fuera sin que el juego deje de ser probable con dados
    fijos.
    """

    situacion: str
    fuerza: str
    velocidad: str
    volver: str

    def etiqueta(self, opcion: str) -> str:
        return getattr(self, opcion)


# Lo que cabe. Discord corta las etiquetas de botón en 80 caracteres y no avisa;
# la situación va dentro del marco ASCII, que es más estrecho todavía.
LARGO_ETIQUETA = 60
LARGO_SITUACION = 160


def escena_desde_json(crudo: str) -> Escena | None:
    """La escena que propuso el modelo, o `None` si no vale.

    Se valida entera antes de usarla porque el texto viene de fuera: si falta
    una opción, la escena tendría dos salidas en vez de tres, y si una etiqueta
    se pasa de largo, Discord rechaza el botón y la aventura se queda colgada.
    Devolver `None` es la señal para tirar de las escritas.
    """
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
    for clave, tope in (("situacion", LARGO_SITUACION), ("fuerza", LARGO_ETIQUETA),
                        ("velocidad", LARGO_ETIQUETA), ("volver", LARGO_ETIQUETA)):
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
    return Escena(**campos)


# Las escenas escritas a mano. Aunque las invente el modelo, hacen falta: es lo
# que se juega cuando la IA no está o se agotó el límite, igual que las criaturas
# nunca se quedan sin frase. Una aventura muda no es una aventura.
#
# Van variadas a propósito, y no sólo puertas y muros: en cada bioma hay algo
# cerrado, alguien con quien cruzarse y algo que está pasando. Si todas fueran
# obstáculos, el respaldo cantaría al segundo viaje y el modelo tendería a
# copiar la única forma que ve.
ESCENAS_ESCRITAS: dict[str, tuple[Escena, ...]] = {
    "bosque": (
        Escena("Una cabaña con la puerta hinchada por la humedad.",
               "Empujar la puerta", "Colarte por la ventana rota",
               "Seguir el sendero"),
        Escena("Un leñador forcejea con su carro atascado en el barro.",
               "Levantarlo por detrás", "Calzar la rueda antes de que se hunda",
               "Desearle suerte y seguir"),
        Escena("Un panal zumbando justo encima del camino.",
               "Bajar la rama despacio", "Pasar por debajo de un tirón",
               "Dar un rodeo"),
        Escena("Cruje arriba: una rama enorme viene abajo sobre el sendero.",
               "Aguantarla mientras pasas", "Cruzar antes de que caiga",
               "Refugiarte y esperar"),
    ),
    "planicie": (
        Escena("Un pozo de piedra tapado con una losa.",
               "Levantar la losa", "Descolgarte por la cuerda",
               "Dejarlo estar"),
        Escena("Un rebaño se ha asustado y viene de frente.",
               "Plantarte y aguantar", "Esquivarlo por el flanco",
               "Tumbarte en la hierba"),
        Escena("Una pastora lleva media tarde buscando una oveja perdida.",
               "Apartar los fardos del corral", "Batir el campo a la carrera",
               "Decirle que no la has visto"),
        Escena("El viento arranca la lona de un puesto de feria.",
               "Sujetar el poste a pulso", "Atrapar la lona antes de que vuele",
               "Dejar que se la lleve"),
    ),
    "desierto": (
        Escena("Media columna asoma de la arena, y algo brilla debajo.",
               "Empujar la columna", "Escarbar antes de que se hunda",
               "Buscar sombra"),
        Escena("Una caravana ha perdido un fardo y lo busca antes del viento.",
               "Cargar tú con el resto", "Rastrear las huellas que quedan",
               "Seguir tu camino"),
        Escena("El suelo cede: debajo se abre una galería antigua.",
               "Aguantar el borde que se desmorona", "Saltar al otro lado",
               "Retroceder sobre tus huellas"),
        Escena("Un pozo seco con un cubo atascado en el brocal.",
               "Tirar de la cadena", "Bajar por el brocal",
               "Seguir la duna"),
    ),
    "ruinas": (
        Escena("Un portón de bronce, cerrado desde dentro.",
               "Reventar el portón", "Trepar por la hiedra",
               "Rodear la muralla"),
        Escena("Alguien pide ayuda debajo de una viga caída.",
               "Levantar la viga", "Sacarlo a rastras antes de que ceda",
               "Ir a buscar ayuda"),
        Escena("Una bandada sale en tromba y tapa el pasillo entero.",
               "Abrirte paso a manotazos", "Cruzar mientras dure el hueco",
               "Esperar a que se calmen"),
        Escena("Una losa con una argolla, en mitad de la sala.",
               "Levantar la losa", "Colarte por la rendija",
               "Dejar la losa quieta"),
    ),
    "cienaga": (
        Escena("Una pasarela de tablones podridos sobre el agua negra.",
               "Reforzarla con un tronco", "Cruzarla de tres zancadas",
               "Vadear por la orilla"),
        Escena("Un pescador con la barca encallada en el limo.",
               "Empujar la barca", "Sacar el limo antes de que agarre",
               "Desearle suerte y seguir"),
        Escena("Sube una niebla espesa y el camino desaparece.",
               "Apartar los juncos a manotazos", "Cruzar antes de que cierre",
               "Sentarte a esperar que aclare"),
        Escena("Algo grande se mueve bajo el agua, muy despacio.",
               "Golpear el agua para asustarlo", "Pasar de puntillas",
               "Rodear la charca entera"),
    ),
    "arrecife": (
        Escena("La marea sube y tapa el paso entre las rocas.",
               "Apartar las rocas sueltas", "Cruzar antes de la próxima ola",
               "Esperar a que baje"),
        Escena("Una red vieja enredada en el coral, con algo dentro.",
               "Tirar de la red", "Desenredarla antes de que se hunda",
               "Dejarla donde está"),
        Escena("Una buceadora se ha quedado sin aire y golpea las rocas.",
               "Levantar la piedra que la atrapa", "Nadar a por ella",
               "Ir a buscar ayuda"),
        Escena("Un banco de peces cierra el paso como una pared.",
               "Abrirte camino a brazadas", "Colarte por un hueco",
               "Bordear el arrecife"),
    ),
    "chatarral": (
        Escena("Una torre de chatarra se tambalea encima del sendero.",
               "Sujetar la torre", "Cruzar antes de que caiga",
               "Dar un rodeo largo"),
        Escena("Un chatarrero busca una pieza y ya no ve bien.",
               "Levantar la plancha que la tapa", "Rebuscar tú, que eres rápido",
               "Decirle que no la has visto"),
        Escena("Salta una chispa y un montón de aceite empieza a arder.",
               "Ahogar el fuego con arena", "Apartar lo que arde de un tirón",
               "Alejarte del humo"),
        Escena("Un portón de acero, soldado por el óxido.",
               "Reventar la soldadura", "Colarte por el respiradero",
               "Buscar otra entrada"),
    ),
    "cumbre": (
        Escena("Una cornisa estrecha, con el hielo justo encima.",
               "Romper el hielo a golpes", "Cruzar antes de que resbale",
               "Bajar y rodear"),
        Escena("Una cabra se ha quedado atascada entre dos rocas.",
               "Separar las rocas", "Sacarla antes de que se agote",
               "Dejarla, que se apañe"),
        Escena("Empieza la ventisca y el sendero se borra en un minuto.",
               "Abrir camino a paladas", "Correr al refugio de abajo",
               "Refugiarte tras una roca"),
        Escena("Un puente de cuerda tieso de escarcha.",
               "Tensar la cuerda helada", "Cruzarlo sin mirar",
               "Buscar el paso de abajo"),
    ),
    "cavernas": (
        Escena("Un derrumbe tapa la galería, pero queda un hueco arriba.",
               "Apartar los bloques", "Colarte por el hueco",
               "Volver por donde entraste"),
        Escena("Un espeleólogo se ha quedado sin luz y no se atreve a moverse.",
               "Cargar con su equipo", "Guiarlo hasta la salida",
               "Marcar el sitio y avisar fuera"),
        Escena("Un lago subterráneo corta el paso, y está muy frío.",
               "Empujar una roca para hacer puente", "Cruzarlo a nado",
               "Bordearlo por la cornisa"),
        Escena("Cuelgan estalactitas justo encima, y el suelo tiembla.",
               "Partir las que estorban", "Pasar corriendo por debajo",
               "Esperar a que pare el temblor"),
    ),
    "volcan": (
        Escena("Una colada de lava con costra encima.",
               "Romper la costra y saltar", "Cruzar corriendo por encima",
               "Bordear la colada"),
        Escena("Un buscador de obsidiana se ha quedado sin agua y no se levanta.",
               "Cargarlo hasta la sombra", "Correr a por agua fría",
               "Avisar en el poblado"),
        Escena("Empieza a caer ceniza y el sendero desaparece a ojos vistas.",
               "Apartarla a paladas", "Cruzar antes de que lo cubra",
               "Buscar refugio"),
        Escena("Una puerta de obsidiana, tibia al tacto.",
               "Forzar la obsidiana", "Colarte por la grieta del marco",
               "Alejarte del calor"),
    ),
}


def escena_escrita(
    bioma: Bioma, evitar: Escena | None = None, rng: random.Random | None = None
) -> Escena:
    """Una escena de las escritas, saltándose la que ya se enseñó.

    `evitar` está para que el segundo nodo no repita el primero, que es lo que
    delataría el respaldo en cuanto la IA se cae dos veces seguidas.
    """
    posibles = [e for e in ESCENAS_ESCRITAS[bioma.clave] if e != evitar]
    return (rng or random.Random()).choice(posibles)


def resolver_opcion(
    criatura: sim.Criatura,
    bioma: Bioma,
    opcion: str,
    rng: random.Random | None = None,
    obstaculo: str = "",
) -> Prueba | None:
    """La tirada de una opción, o `None` si es la de volver, que nunca falla."""
    if opcion == VOLVER:
        return None
    if opcion not in (FUERZA, VELOCIDAD):
        raise ValueError(f"opción desconocida: {opcion!r}")

    base = criatura.fuerza if opcion == FUERZA else criatura.velocidad
    return Prueba(
        obstaculo=obstaculo,
        stat=opcion,
        base=base,
        dado=(rng or random.Random()).randint(1, CARA_DADO),
        dificultad=bioma.dificultad,
    )


@dataclass(frozen=True)
class Viaje:
    """El estado del árbol entre pulsación y pulsación.

    Es inmutable y no guarda nada de Discord, así que el cog puede sostenerlo en
    la vista y los tests recorrer el árbol entero con dados fijos.
    """

    bioma: Bioma
    escena: Escena
    pruebas: tuple[Prueba, ...] = ()
    nivel: int = 0
    fallo: bool = False

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
    rng: random.Random | None = None,
) -> Viaje:
    """Aplica una decisión y devuelve el viaje resultante.

    Acertar y volver llevan a `siguiente`; fallar cierra la aventura ahí mismo,
    y por eso `siguiente` puede venir vacío.
    """
    prueba = resolver_opcion(
        criatura, viaje.bioma, opcion, rng, viaje.escena.etiqueta(opcion)
    )
    fallo = prueba is not None and not prueba.superada
    return Viaje(
        bioma=viaje.bioma,
        escena=siguiente or viaje.escena,
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
            f" {marca} {ETIQUETA_STAT[prueba.stat]} "
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
