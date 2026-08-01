"""Carreras y peleas de sumo.

Módulo puro: el generador de números aleatorios se pasa como argumento, así que
los tests fijan los dados y comprueban el resultado exacto.

La tirada es la pedida: `estadística + 1d20`. Lo que se hace es repetirla en
tres tramos y sumar. Con una sola tirada el ganador estaría decidido antes del
primer fotograma y la animación sería decorado; con tres hay remontadas y el
resultado se construye delante de quien mira.

Una carrera admite de dos a cinco corredores; el sumo, dos y sólo dos, porque es
un forcejeo y el dohyō tiene dos lados. De ahí que todo se guarde en listas
indexadas y no en un `a` y un `b`: un solo vocabulario para los dos casos.
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

import especies as esp
import pantalla
import simulacion as sim

CARRERA = "carrera"
SUMO = "sumo"

TRAMOS = 3
CARA_DADO = 20
ANCHO_PISTA = 10
ANCHO_DOHYO = 19  # impar, para que haya casilla central exacta
PUNTOS_POR_CASILLA = 5  # cuánta ventaja hace falta para empujar una casilla

# Tope de desempates: con 1d20 la probabilidad de encadenar empates es ínfima,
# pero un bucle sin salida en producción no es aceptable.
MAX_DESEMPATES = 20

MAX_CORREDORES = 5
# Cuántos caben en cada modalidad. Es la lista de números válidos y no un rango
# porque el sumo admite dos o cuatro pero **no tres**: con tres no hay forma de
# emparejar sin que alguien pelee solo o dos veces.
CUANTOS_CABEN = {
    CARRERA: tuple(range(2, MAX_CORREDORES + 1)),
    SUMO: (2, 4),
}
# Con cuatro, el sumo se juega a torneo: dos semifinales y una final.
CUANTOS_EN_TORNEO = 4

NOMBRES = {CARRERA: "CARRERA", SUMO: "SUMO"}
STATS = {CARRERA: "velocidad", SUMO: "fuerza"}
RONDAS_DEL_TORNEO = ("SEMIFINAL 1", "SEMIFINAL 2", "FINAL")


@dataclass(frozen=True)
class Competidor:
    nombre: str
    especie: str
    stat: int
    modificador: int = 0
    # La cara que tiene puesta al competir. Se trae hecha desde la criatura para
    # que el podio pueda dibujarla sin que este módulo deje de ser puro.
    animo: str = esp.NORMAL

    @property
    def color(self) -> str:
        return esp.ESPECIES[self.especie].color

    @property
    def cara(self) -> str:
        return esp.ESPECIES[self.especie].caras[self.animo]

    @property
    def base(self) -> int:
        """Lo que aporta sin contar el dado. Nunca baja de 1."""
        return max(1, self.stat + self.modificador)


@dataclass(frozen=True)
class Ronda:
    """Un tramo: el dado de cada competidor y lo que sumó, en el mismo orden."""

    dados: tuple[int, ...]
    totales: tuple[int, ...]


@dataclass(frozen=True)
class Resultado:
    tipo: str
    competidores: tuple[Competidor, ...]
    rondas: list[Ronda]
    orden: tuple[int, ...]  # índices de `competidores`, del 1.º al último
    desempates: int = 0

    @property
    def totales(self) -> tuple[int, ...]:
        """Lo que suma cada competidor al final, en orden de dorsal."""
        return tuple(
            sum(r.totales[i] for r in self.rondas)
            for i in range(len(self.competidores))
        )

    @property
    def clasificacion(self) -> tuple[tuple[Competidor, int], ...]:
        """`(competidor, total)` del primero al último."""
        totales = self.totales
        return tuple((self.competidores[i], totales[i]) for i in self.orden)

    @property
    def competidor_ganador(self) -> Competidor:
        return self.competidores[self.orden[0]]

    @property
    def competidor_perdedor(self) -> Competidor:
        return self.competidores[self.orden[-1]]


@dataclass(frozen=True)
class Encuentro:
    """Lo que pasa cuando un grupo compite: uno o varios combates y el orden final.

    Una carrera y un sumo de dos tienen un combate; un torneo de cuatro, tres.
    Quien narra no necesita distinguirlos: anima `combates` en orden, publica
    `resumen(...)` y reparte la experiencia con `orden`, donde cada dorsal
    aparece **una sola vez** aunque haya peleado dos.
    """

    tipo: str
    competidores: tuple[Competidor, ...]  # en el orden en que se invitó
    combates: tuple[Resultado, ...]
    orden: tuple[int, ...]  # dorsales, del 1.º al último
    # El marcador que se le apunta a cada dorsal: lo que sumó en su última pelea.
    marcadores: tuple[int, ...]

    @property
    def clasificacion(self) -> tuple[tuple[Competidor, int], ...]:
        """`(competidor, marcador)` del primero al último."""
        return tuple(
            (self.competidores[dorsal], self.marcadores[dorsal])
            for dorsal in self.orden
        )

    @property
    def campeon(self) -> Competidor:
        return self.competidores[self.orden[0]]

    @property
    def es_torneo(self) -> bool:
        return len(self.combates) > 1


def margen_de(encuentro: Encuentro, dorsal: int) -> int:
    """Margen del último combate real de un participante.

    En un torneo los derrotados sólo aparecen en una semifinal y los finalistas
    en la final; recorrer de atrás hacia delante conserva exactamente ese último
    resultado sin inventar un margen a partir del orden global.
    """
    objetivo = encuentro.competidores[dorsal]
    for combate in reversed(encuentro.combates):
        indices = [
            indice for indice, competidor in enumerate(combate.competidores)
            if competidor is objetivo
        ]
        if not indices:
            continue
        indice = indices[0]
        totales = combate.totales
        ganador = combate.orden[0]
        if indice != ganador:
            return abs(totales[indice] - totales[ganador])
        subcampeon = combate.orden[1]
        return abs(totales[indice] - totales[subcampeon])
    raise ValueError(f"dorsal sin combate: {dorsal}")


def modificador_por_estado(hambre: float, animo: float) -> int:
    """Cuidar a la criatura se nota, pero poco: el 1d20 sigue mandando."""
    modificador = 0
    if animo > 70:
        modificador += 2
    elif animo < 30:
        modificador -= 2
    if hambre < 25:
        modificador -= 3
    return modificador


def competidor_de(
    criatura: sim.Criatura, tipo: str, bonus_objetos: int = 0
) -> Competidor:
    """La criatura vista como competidor.

    El bonus de las pociones entra como argumento y no se consulta aquí porque
    este módulo es puro a propósito —el generador de dados se pasa por fuera por
    lo mismo—, y buscarlo dentro obligaría a montar una base de datos para cada
    test de dados. Va al modificador y no a la estadística: así una poción se
    suma donde ya se suman el hambre y el ánimo, y sigue mandando el 1d20.
    """
    stat = criatura.velocidad if tipo == CARRERA else criatura.fuerza
    return Competidor(
        nombre=criatura.nombre,
        especie=criatura.especie,
        stat=stat,
        modificador=(
            modificador_por_estado(criatura.hambre, criatura.animo) + bonus_objetos
        ),
        animo=criatura.animo_visual,
    )


def resolver(
    competidores: Sequence[Competidor],
    tipo: str,
    rng: random.Random | None = None,
) -> Resultado:
    """Un combate: todos contra todos a la vez, tres tramos y el que más sume.

    No valida cuántos son: eso lo hace `enfrentar`, que es quien sabe si el grupo
    pelea de una vez o repartido en un torneo.
    """
    competidores = tuple(competidores)
    rng = rng or random.Random()
    rondas: list[Ronda] = []

    def tirar() -> Ronda:
        # Un dado por competidor, en orden de dorsal: así los tests de dados
        # fijos pueden guionizar la tirada entera.
        dados = tuple(rng.randint(1, CARA_DADO) for _ in competidores)
        return Ronda(
            dados, tuple(c.base + d for c, d in zip(competidores, dados))
        )

    def acumulados() -> tuple[int, ...]:
        return tuple(
            sum(r.totales[i] for r in rondas) for i in range(len(competidores))
        )

    for _ in range(TRAMOS):
        rondas.append(tirar())

    # Mientras haya DOS totales iguales cualesquiera se tira otro tramo para
    # todos. Con cinco corredores los empates son bastante más probables que con
    # dos, pero cada tramo extra añade un d20 independiente a cada uno, así que
    # se rompen enseguida.
    desempates = 0
    totales = acumulados()
    while len(set(totales)) != len(totales) and desempates < MAX_DESEMPATES:
        rondas.append(tirar())
        totales = acumulados()
        desempates += 1

    # Al agotar los desempates puede quedar algún empate: lo deshace el dorsal,
    # que es el equivalente al «gana `a` los empates» de cuando esto era de dos.
    orden = tuple(
        sorted(range(len(competidores)), key=lambda i: (-totales[i], i))
    )
    return Resultado(
        tipo=tipo,
        competidores=competidores,
        rondas=rondas,
        orden=orden,
        desempates=desempates,
    )


def enfrentar(
    competidores: Sequence[Competidor],
    tipo: str,
    rng: random.Random | None = None,
) -> Encuentro:
    """La única puerta de entrada: un combate, o un torneo si toca.

    Valida cuántos caben y decide la forma. Con cuatro al sumo monta el torneo;
    con todo lo demás, un solo combate.
    """
    competidores = tuple(competidores)
    if len(competidores) not in CUANTOS_CABEN[tipo]:
        caben = " o ".join(str(n) for n in CUANTOS_CABEN[tipo])
        raise ValueError(
            f"{NOMBRES[tipo]} es de {caben} competidores, "
            f"y han venido {len(competidores)}"
        )

    rng = rng or random.Random()
    if tipo == SUMO and len(competidores) == CUANTOS_EN_TORNEO:
        return _torneo(competidores, tipo, rng)

    combate = resolver(competidores, tipo, rng)
    return Encuentro(
        tipo=tipo,
        competidores=competidores,
        combates=(combate,),
        orden=combate.orden,
        marcadores=combate.totales,
    )


def _torneo(
    competidores: tuple[Competidor, ...], tipo: str, rng: random.Random
) -> Encuentro:
    """Dos semifinales sorteadas y una final entre los que pasan.

    Se trabaja con **dorsales** y no con competidores porque `orden` tiene que
    indexar `competidores` en el orden en que se invitó: es el que usa el cog para
    darle la experiencia a la criatura correcta, y el sorteo lo desordena.
    """
    dorsales = list(range(len(competidores)))
    rng.shuffle(dorsales)
    parejas = (tuple(dorsales[:2]), tuple(dorsales[2:]))

    combates: list[Resultado] = []
    finalistas: list[int] = []
    caidos: list[tuple[int, int]] = []  # (dorsal, lo que sumó en su semifinal)

    for pareja in parejas:
        semifinal = resolver([competidores[d] for d in pareja], tipo, rng)
        combates.append(semifinal)
        finalistas.append(pareja[semifinal.orden[0]])
        perdedor = pareja[semifinal.orden[-1]]
        caidos.append((perdedor, semifinal.totales[semifinal.orden[-1]]))

    final = resolver([competidores[d] for d in finalistas], tipo, rng)
    combates.append(final)

    campeon = finalistas[final.orden[0]]
    subcampeon = finalistas[final.orden[1]]
    # Los dos de semifinales no pelean por el bronce, así que se ordenan entre sí
    # por lo que sumaron: mejor marcador, mejor puesto. Así el orden es completo
    # y determinista en vez de arbitrario.
    caidos.sort(key=lambda caido: -caido[1])

    marcadores = [0] * len(competidores)
    marcadores[campeon] = final.totales[final.orden[0]]
    marcadores[subcampeon] = final.totales[final.orden[1]]
    for dorsal, total in caidos:
        marcadores[dorsal] = total

    return Encuentro(
        tipo=tipo,
        competidores=competidores,
        combates=tuple(combates),
        orden=(campeon, subcampeon, *(dorsal for dorsal, _ in caidos)),
        marcadores=tuple(marcadores),
    )


# --- Narración -------------------------------------------------------------

def _cabecera(resultado: Resultado, paso: int, titulo: str) -> list[str]:
    """El marco de arriba. `titulo` cabe en 14: el más largo, «SEMIFINAL 1», mide 11."""
    total = len(resultado.rondas)
    etiqueta = f"tramo {paso}/{total}" if paso <= total else "final"
    if paso > TRAMOS and paso <= total:
        etiqueta = "desempate"
    return [
        "╭" + "─" * pantalla.ANCHO + "╮",
        pantalla.fila(f" {titulo:<14}{etiqueta:>10} "),
        "├" + "─" * pantalla.ANCHO + "┤",
    ]


def _acumulados(resultado: Resultado, paso: int) -> tuple[int, ...]:
    """Lo que lleva sumado cada competidor tras `paso` tramos."""
    return tuple(
        sum(r.totales[i] for r in resultado.rondas[:paso])
        for i in range(len(resultado.competidores))
    )


def _pista(avance: int) -> str:
    avance = max(0, min(ANCHO_PISTA, avance))
    return "=" * avance + ">" + "." * (ANCHO_PISTA - avance)


# Lo que queda del ancho interior para el nombre y el marcador, una vez
# descontados la pista, su punta y los cuatro espacios de separación.
ANCHO_NOMBRE_Y_MARCADOR = pantalla.ANCHO - (ANCHO_PISTA + 1) - 4


def _fila_corredor(c: Competidor, acumulado: int, meta: int) -> str:
    """Nombre, pista y marcador. Esta fila se monta a mano, sin pasar por
    `pantalla.fila()`, porque lleva color en medio: si se pasa de ancho no se
    recorta, rompe el marco. Por eso el marcador se mide y el nombre —que ya
    venía truncado— le cede el sitio que necesite."""
    avance = 0 if meta <= 0 else round(acumulado / meta * ANCHO_PISTA)
    ancho_marcador = max(3, len(str(meta)))
    ancho_nombre = ANCHO_NOMBRE_Y_MARCADOR - ancho_marcador
    izq = f" {c.nombre[:ancho_nombre]:<{ancho_nombre}} "
    der = f" {acumulado:>{ancho_marcador}} "
    return f"│{izq}{pantalla.pintar(_pista(avance), c.color)}{der}│"


def _anchos_del_dado(resultado: Resultado) -> tuple[int, int]:
    """Ancho de las columnas `base` y `total`, medido sobre TODO el combate.

    Se calcula una vez sobre todos los competidores y todos los tramos, y no fila
    a fila: si cada una midiera lo suyo, con un competidor a 9 y otro a 240 las
    columnas bailarían de una fila a la siguiente. Los mínimos (2 y 3) son los
    anchos de siempre, así que un combate normal sale exactamente igual que
    antes.
    """
    ancho_base = max([2] + [len(str(c.base)) for c in resultado.competidores])
    ancho_total = max(
        [3] + [len(str(t)) for r in resultado.rondas for t in r.totales]
    )
    return ancho_base, ancho_total


def _fila_dado(
    c: Competidor, dado: int, total: int, ancho_base: int, ancho_total: int
) -> str:
    """`nombre  stat+d20 tirada = total`, en 25 caracteres justos.

    Sin etiqueta de estadística: el encabezado ya dice si es CARRERA (velocidad)
    o SUMO (fuerza), y con ella la fila se pasaba de ancho y `fila()` recortaba
    justo el total, que es el dato que importa. Por lo mismo, los números mandan
    sobre el nombre: cuando crecen de cifras, es el nombre el que se acorta.
    """
    # 1 + nombre + 1 + base + len("+d20") + 1 + 2 + len(" = ") + total + 1
    ancho_nombre = max(1, pantalla.ANCHO - 1 - ancho_base - ancho_total - 13)
    return pantalla.fila(
        f" {c.nombre[:ancho_nombre]:<{ancho_nombre}} "
        f"{c.base:>{ancho_base}}+d20 {dado:>2} = {total:>{ancho_total}} "
    )


def fotogramas_carrera(resultado: Resultado, titulo: str) -> list[str]:
    """Un mensaje por tramo. El cog los va editando para animar la carrera.

    Con cinco corredores son quince líneas y unos 500 caracteres contando los
    códigos de color: muy por debajo del tope de 2000 de un mensaje de Discord.
    """
    meta = max(resultado.totales)
    ancho_base, ancho_total = _anchos_del_dado(resultado)
    fotogramas = []

    for paso in range(1, len(resultado.rondas) + 1):
        acumulados = _acumulados(resultado, paso)
        ronda = resultado.rondas[paso - 1]

        cuerpo = _cabecera(resultado, paso, titulo)
        for competidor, acumulado in zip(resultado.competidores, acumulados):
            cuerpo.append(_fila_corredor(competidor, acumulado, meta))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        for competidor, dado, total in zip(
            resultado.competidores, ronda.dados, ronda.totales
        ):
            cuerpo.append(
                _fila_dado(competidor, dado, total, ancho_base, ancho_total)
            )
        cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")
        fotogramas.append("```ansi\n" + "\n".join(cuerpo) + "\n```")

    return fotogramas


def _dohyo(desplazamiento: int) -> str:
    """La marca se aleja del centro hacia el lado del que va perdiendo."""
    centro = ANCHO_DOHYO // 2
    posicion = max(0, min(ANCHO_DOHYO - 1, centro + desplazamiento))
    return "(" + "=" * posicion + "O" + "=" * (ANCHO_DOHYO - 1 - posicion) + ")"


def fotogramas_sumo(resultado: Resultado, titulo: str) -> list[str]:
    total_rondas = len(resultado.rondas)
    ancho_base, ancho_total = _anchos_del_dado(resultado)
    a, b = resultado.competidores  # el sumo es de dos: lo garantiza `resolver`
    fotogramas = []

    for paso in range(1, total_rondas + 1):
        acum_a, acum_b = _acumulados(resultado, paso)
        ronda = resultado.rondas[paso - 1]

        # Cuanto más domina A, más lejos empuja la marca hacia el lado de B.
        # La escala es fija (tantos puntos de ventaja = una casilla) en vez de
        # relativa al marcador final: si se normalizase contra la diferencia
        # final, la marca saltaría al extremo en cuanto alguien se pusiera por
        # delante y se quedaría ahí clavada el resto del combate.
        ventaja = acum_a - acum_b
        desplazamiento = round(ventaja / PUNTOS_POR_CASILLA)

        cuerpo = _cabecera(resultado, paso, titulo)
        cuerpo.append(pantalla.fila(
            f" {a.nombre[:11]:<11}{b.nombre[:11]:>13} "
        ))
        cuerpo.append(pantalla.fila(f" {_dohyo(desplazamiento)} "))
        cuerpo.append(pantalla.fila(f" {acum_a:<11}{acum_b:>13} "))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        cuerpo.append(_fila_dado(a, ronda.dados[0], ronda.totales[0],
                                 ancho_base, ancho_total))
        cuerpo.append(_fila_dado(b, ronda.dados[1], ronda.totales[1],
                                 ancho_base, ancho_total))
        cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")
        fotogramas.append("```ansi\n" + "\n".join(cuerpo) + "\n```")

    return fotogramas


def como_se_llama(tipo: str, cuantos: int) -> str:
    """«una CARRERA», «un SUMO» o «un TORNEO DE SUMO», para anunciar el reto."""
    if tipo == SUMO and cuantos == CUANTOS_EN_TORNEO:
        return "un TORNEO DE SUMO"
    return "una CARRERA" if tipo == CARRERA else "un SUMO"


def _titulos(encuentro: Encuentro) -> tuple[str, ...]:
    """El rótulo de cada combate: la ronda del torneo, o la modalidad si es uno."""
    if encuentro.es_torneo:
        return RONDAS_DEL_TORNEO
    return (NOMBRES[encuentro.tipo],)


def fotogramas_de(encuentro: Encuentro) -> list[list[str]]:
    """Los fotogramas de cada combate, en orden y con el título de su ronda.

    Una lista por combate: el cog manda un mensaje por cada una y la va editando
    para animarla. Un torneo son tres tandas; todo lo demás, una.
    """
    dibujar = (
        fotogramas_carrera if encuentro.tipo == CARRERA else fotogramas_sumo
    )
    return [
        dibujar(combate, titulo)
        for combate, titulo in zip(encuentro.combates, _titulos(encuentro))
    ]


# --- El podio --------------------------------------------------------------

MEDALLAS = ("🥇", "🥈", "🥉")
PUESTOS_EN_EL_PODIO = 3

# Cada cajón mide lo mismo que el token de un gachamón, `(` + cara + `)`, porque
# las diez especies tienen la cara de tres caracteres exactos. Eso es lo que hace
# que la cara caiga siempre justo encima de su cajón sin medir nada.
ANCHO_CAJON = 5

# Dónde empieza el cajón de cada puesto, en columnas del interior del marco.
# Orden clásico: el 2.º a la izquierda, el 1.º en medio y el 3.º a la derecha.
COLUMNAS_PODIO = {2: 3, 1: 10, 3: 17}
ALTO_PODIO = 5


def _pieza_del_podio(puesto: int, competidor: Competidor, fila: int) -> str | None:
    """Qué le toca a un puesto en una fila del dibujo, o None si nada.

    El puesto marca la altura: el 1.º empieza arriba del todo y cada siguiente
    baja una fila, así que los cajones salen escalonados sin más aritmética.

        fila = puesto - 1   la cara
        fila = puesto       el techo del cajón
        fila = puesto + 1   el número
        más abajo           el cuerpo del cajón
    """
    if fila == puesto - 1:
        return f"({competidor.cara})"
    if fila == puesto:
        return "┌───┐"
    if fila == puesto + 1:
        return f"│ {puesto} │"
    if fila > puesto + 1:
        return "│···│"
    return None


def _fila_del_podio(piezas: list[tuple[int, str, str]]) -> str:
    """Monta una fila colocando cada pieza en su columna.

    Se monta a mano y no con `pantalla.fila()` porque lleva color en medio: los
    códigos ANSI son invisibles pero cuentan como caracteres, y recortar al ancho
    rompería el marco en vez de acortar el texto. Aquí no hay nada que medir:
    todas las piezas miden `ANCHO_CAJON` y las columnas son constantes.
    """
    trozos = []
    cursor = 0
    for columna, pieza, color in sorted(piezas):
        trozos.append(" " * (columna - cursor))
        trozos.append(pantalla.pintar(pieza, color))
        cursor = columna + ANCHO_CAJON
    trozos.append(" " * (pantalla.ANCHO - cursor))
    return "│" + "".join(trozos) + "│"


def _dibujo_del_podio(clasificacion) -> list[str]:
    """Los tres cajones con su gachamón encima, cada uno en su color."""
    filas = []
    for fila in range(ALTO_PODIO):
        piezas = []
        for puesto, (competidor, _) in enumerate(
            clasificacion[:PUESTOS_EN_EL_PODIO], start=1
        ):
            pieza = _pieza_del_podio(puesto, competidor, fila)
            if pieza is not None:
                piezas.append((COLUMNAS_PODIO[puesto], pieza, competidor.color))
        filas.append(_fila_del_podio(piezas))
    return filas


def _fila_puesto(
    puesto: int, competidor: Competidor, total: int, ancho_total: int
) -> str:
    """`  2  Nombre        61 `, con el nombre en el color de su especie.

    Como la del corredor: lleva color, así que se mide en piezas de largo fijo y
    son los números los que mandan sobre el nombre cuando crecen de cifras.
    """
    # 1 + 2 + 2 + nombre + 1 + total + 1 == ANCHO
    ancho_nombre = max(1, pantalla.ANCHO - 7 - ancho_total)
    nombre = f"{competidor.nombre[:ancho_nombre]:<{ancho_nombre}}"
    return (
        f"│ {puesto:>2}  {pantalla.pintar(nombre, competidor.color)}"
        f" {total:>{ancho_total}} │"
    )


def podio(encuentro: Encuentro) -> str:
    """El podio de una carrera: medallas fuera del bloque y dibujo dentro.

    Las medallas van fuera a propósito: dentro de un bloque ```ansi Discord
    sustituye cada emoji por una imagen de ancho variable y descuadra el marco.
    """
    clasificacion = encuentro.clasificacion
    ancho_total = max([3] + [len(str(total)) for _, total in clasificacion])

    cuerpo = [
        "╭" + "─" * pantalla.ANCHO + "╮",
        pantalla.fila(f" {'PODIO':<14}{NOMBRES[encuentro.tipo]:>10} "),
        "├" + "─" * pantalla.ANCHO + "┤",
    ]
    cuerpo += _dibujo_del_podio(clasificacion)
    cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
    for puesto, (competidor, total) in enumerate(clasificacion, start=1):
        cuerpo.append(_fila_puesto(puesto, competidor, total, ancho_total))
    cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")

    medallas = " · ".join(
        f"{MEDALLAS[i]} **{competidor.nombre}**"
        for i, (competidor, _) in enumerate(clasificacion[:PUESTOS_EN_EL_PODIO])
    )
    return (
        f"## 🏁 Podio\n{medallas}\n"
        "```ansi\n" + "\n".join(cuerpo) + "\n```"
        + _nota_de_desempates(encuentro)
    )


def _nota_de_desempates(encuentro: Encuentro) -> str:
    """Cuántos tramos extra hicieron falta, sumando todos los combates."""
    desempates = sum(combate.desempates for combate in encuentro.combates)
    if not desempates:
        return ""
    return f"\n-# Hizo falta desempatar {desempates} vez/veces."


# --- El cuadro del torneo --------------------------------------------------

# El hueco del nombre en las dos columnas del cuadro. Es una constante y no una
# medida: con 26 columnas de marco es lo que queda tras las líneas del cruce, y
# ser constante es lo que impide que el color rompa el marco.
ANCHO_NOMBRE_CUADRO = 10


def _fila_del_cuadro(
    prefijo: str, competidor: Competidor, paso: bool, sufijo: str = ""
) -> str:
    """Una fila del cuadro: prefijo, el nombre en color, y sufijo.

    Se monta a mano y no con `pantalla.fila()` porque los códigos ANSI cuentan
    como caracteres y el recorte se los comería, rompiendo el marco en vez de
    acortar el nombre. Nada que medir: el hueco del nombre es la constante
    `ANCHO_NOMBRE_CUADRO`.

    Quien pasa va del color de su especie y quien cae, en gris — el mismo con el
    que `/cementerio` pinta a las que ya no están, y por lo mismo: para ver de un
    golpe quién sigue en pie sin tener que seguir las líneas.
    """
    nombre = f"{competidor.nombre[:ANCHO_NOMBRE_CUADRO]:<{ANCHO_NOMBRE_CUADRO}}"
    visible = len(prefijo) + ANCHO_NOMBRE_CUADRO + len(sufijo)
    relleno = " " * max(0, pantalla.ANCHO - visible)
    color = competidor.color if paso else esp.GRIS
    return f"│{prefijo}{pantalla.pintar(nombre, color)}{sufijo}{relleno}│"


def _renglones_del_cruce(resultado: Resultado) -> list[str]:
    """Los tres renglones de un cruce: los dos que pelean y quién pasa.

        Juan III   ─┐
                     ├─ Juan III
        Michi      ─┘

    Las tres esquinas caen en la misma columna por construcción: la sangría del
    cruce es exactamente lo que ocupan el margen, el nombre y las dos rayas.
    """
    arriba, abajo = resultado.competidores
    ganador = resultado.competidor_ganador
    sangria = " " * (1 + ANCHO_NOMBRE_CUADRO + 2)
    return [
        _fila_del_cuadro(" ", arriba, arriba is ganador, " ─┐"),
        _fila_del_cuadro(f"{sangria}├─ ", ganador, True),
        _fila_del_cuadro(" ", abajo, abajo is ganador, " ─┘"),
    ]


def cuadro(encuentro: Encuentro) -> str:
    """El cuadro del torneo: dos semifinales y la final, con sus llaves.

    Las tres rondas van apiladas como tres cuadros pequeños en vez de encadenadas
    en uno solo. Encadenado, un cuadro de tres rondas no cabe en 26 columnas y los
    nombres se quedarían en cuatro letras; apilado caben diez.
    """
    campeon = encuentro.campeon
    cuerpo = [
        "╭" + "─" * pantalla.ANCHO + "╮",
        pantalla.fila(f" {'TORNEO':<14}{NOMBRES[encuentro.tipo]:>10} "),
        "├" + "─" * pantalla.ANCHO + "┤",
        pantalla.fila(" SEMIS "),
    ]
    semifinales = encuentro.combates[:-1]
    for numero, semifinal in enumerate(semifinales):
        if numero:
            cuerpo.append(pantalla.fila(""))
        cuerpo += _renglones_del_cruce(semifinal)

    cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
    cuerpo.append(pantalla.fila(" FINAL "))
    cuerpo += _renglones_del_cruce(encuentro.combates[-1])
    cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")

    marcadores = " · ".join(
        f"{c.competidor_ganador.nombre} {max(c.totales)}-{min(c.totales)} "
        f"{c.competidor_perdedor.nombre}"
        for c in encuentro.combates
    )
    return (
        f"## 🏆 Campeón de {NOMBRES[encuentro.tipo]}\n"
        f"{MEDALLAS[0]} **{campeon.nombre}**\n"
        "```ansi\n" + "\n".join(cuerpo) + "\n```"
        f"\n-# {marcadores}"
        + _nota_de_desempates(encuentro)
    )


def resumen(encuentro: Encuentro) -> str:
    """Cómo acabó: el cuadro si fue torneo, el podio si corrieron tres o más, y
    la línea de siempre si sólo eran dos.

    Con dos no hay tres mejores: hay quien gana y quien pierde, y eso se cuenta
    mejor en una línea que dibujando cajones vacíos.
    """
    if encuentro.es_torneo:
        return cuadro(encuentro)
    if len(encuentro.competidores) >= PUESTOS_EN_EL_PODIO:
        return podio(encuentro)

    combate = encuentro.combates[0]
    ganador = combate.competidor_ganador
    perdedor = combate.competidor_perdedor
    totales = combate.totales
    marcador = f"{max(totales)} a {min(totales)}"
    return (
        f"🏆 **{ganador.nombre}** gana a **{perdedor.nombre}** por {marcador}."
        + _nota_de_desempates(encuentro)
    )
