"""Carreras, sumo, asaltos al tótem y laberintos contra el eco del pasillo.

Módulo puro: el generador de números aleatorios se pasa como argumento, así que
los tests fijan los dados y comprueban el resultado exacto. Cada fase combina
las estadísticas que le corresponden y suma 1d20.

Las cuatro modalidades se diferencian por **cómo cuentan**, no por cuántas fases
tienen:

* la **carrera** acumula puntos crudos y los domina la velocidad;
* el **sumo** va a dos intercambios ganados y lo domina la fuerza;
* el **asalto al tótem** juega una fase entera con cada estadística y reparte
  puestos en cada una, así que lo gana quien es completo y no quien destaca en
  una sola cosa;
* el **laberinto de ecos** es el único donde el adversario es el terreno: cada
  fase se juega contra un eco común y se cuenta cuántas puertas abre cada uno,
  así que puede no cruzar nadie.

Una carrera, un asalto y un laberinto admiten de dos a cinco; el sumo, dos o un
torneo de cuatro. Todo se guarda en listas indexadas para conservar un solo
vocabulario y el orden original de dorsales.
"""
from __future__ import annotations

import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

import especies as esp
import pantalla
import simulacion as sim

CARRERA = "carrera"
SUMO = "sumo"
TOTEM = "totem"
LABERINTO = "laberinto"

SALIDA = "SALIDA"
TERRENO = "TERRENO"
FONDO = "FONDO"
POSICION = "POSICIÓN"
EMPUJE = "EMPUJE"
AGUANTE = "AGUANTE"
CENTRO = "AL CENTRO"
FORCEJEO = "FORCEJEO"
HUIDA = "HUIDA"
DESEMPATE = "DESEMPATE"
SENALES = "SEÑALES"
TRAZADO = "TRAZADO"
NO_PERDERSE = "NO PERDERSE"
FASES_CARRERA = (SALIDA, TERRENO, FONDO)
FASES_SUMO = (POSICION, EMPUJE, AGUANTE)
FASES_TOTEM = (CENTRO, FORCEJEO, HUIDA)
FASES_LABERINTO = (SENALES, TRAZADO, NO_PERDERSE)

CARA_DADO = 20
ANCHO_PISTA = 10
ANCHO_DOHYO = 19  # impar, para que haya casilla central exacta

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
    TOTEM: tuple(range(2, MAX_CORREDORES + 1)),
    LABERINTO: tuple(range(2, MAX_CORREDORES + 1)),
}
# Con cuatro, el sumo se juega a torneo: dos semifinales y una final.
CUANTOS_EN_TORNEO = 4

NOMBRES = {
    CARRERA: "CARRERA", SUMO: "SUMO", TOTEM: "TÓTEM", LABERINTO: "LABERINTO",
}
# Qué estadísticas pone a prueba de verdad cada modalidad, en el orden de sus
# fases. Van en tupla incluso cuando es una sola: el tótem juega las tres, y es
# esta lista la que hace que las vetas y el entrenamiento cuenten lo que pasó.
STATS = {
    CARRERA: ("velocidad",),
    SUMO: ("fuerza",),
    TOTEM: ("velocidad", "fuerza", "salud"),
    LABERINTO: ("ingenio",),
}
RONDAS_DEL_TORNEO = ("SEMIFINAL 1", "SEMIFINAL 2", "FINAL")

# Cómo se dice cada modalidad al anunciar el reto y con qué se cuenta su
# marcador. Van en tabla y no en condicionales porque son tres cosas paralelas.
ARTICULOS = {
    CARRERA: "una CARRERA",
    SUMO: "un SUMO",
    TOTEM: "un ASALTO AL TÓTEM",
    LABERINTO: "un LABERINTO DE ECOS",
}
REGLA_DEL_MARCADOR = {
    CARRERA: " puntos acumulados",
    SUMO: " en intercambios",
    TOTEM: " puntos de colocación",
    LABERINTO: " puertas abiertas",
}
# Cómo se resume la modalidad al lanzar el reto, para que quien acepte sepa a
# qué juega antes de pulsar.
REGLAS = {
    CARRERA: "SALIDA, TERRENO y FONDO suman puntos",
    SUMO: "POSICIÓN, EMPUJE y AGUANTE; gana quien logra 2 intercambios",
    TOTEM: (
        "AL CENTRO, FORCEJEO y HUIDA; cada fase reparte puestos "
        "y gana quien más sume"
    ),
    LABERINTO: (
        "SEÑALES, TRAZADO y NO PERDERSE contra el eco del laberinto; "
        "gana quien abre más puertas"
    ),
}


@dataclass(frozen=True)
class Competidor:
    nombre: str
    especie: str
    fuerza: int
    velocidad: int
    salud: int
    modificador: int = 0
    # Lo que suman las pociones y las sopaipillas en curso. Están las cuatro
    # porque el tótem se juega con salud y el laberinto con ingenio: sin ellas,
    # un efecto que las tocara se vería en la ficha y no haría nada en la pista.
    bonus_fuerza: int = 0
    bonus_velocidad: int = 0
    bonus_salud: int = 0
    bonus_ingenio: int = 0
    # La cara que tiene puesta al competir. Se trae hecha desde la criatura para
    # que el podio pueda dibujarla sin que este módulo deje de ser puro.
    animo: str = esp.NORMAL
    ingenio: int = 0

    @property
    def color(self) -> str:
        return esp.ESPECIES[self.especie].color

    @property
    def cara(self) -> str:
        return esp.ESPECIES[self.especie].caras[self.animo]

    def base_en(self, fase: str) -> int:
        """Aporte de la fase sin dado, con el estado aplicado una sola vez."""
        fuerza = self.fuerza + self.bonus_fuerza
        velocidad = self.velocidad + self.bonus_velocidad
        salud = self.salud + self.bonus_salud
        ingenio = self.ingenio + self.bonus_ingenio
        if fase == SALIDA:
            base = velocidad
        elif fase == TERRENO:
            base = round((7 * velocidad + 3 * fuerza) / 10)
        elif fase == FONDO:
            base = round((7 * velocidad + 3 * salud) / 10)
        elif fase == POSICION:
            base = round((7 * fuerza + 3 * velocidad) / 10)
        elif fase == EMPUJE:
            base = fuerza
        elif fase == AGUANTE:
            base = round((7 * fuerza + 3 * salud) / 10)
        elif fase == CENTRO:
            # El tótem no mezcla: cada asalto pone a prueba una estadística
            # entera, y es el reparto de puestos el que premia ser completo.
            base = velocidad
        elif fase == FORCEJEO:
            base = fuerza
        elif fase == HUIDA:
            base = salud
        elif fase == SENALES:
            base = ingenio
        elif fase == TRAZADO:
            base = round((7 * ingenio + 3 * velocidad) / 10)
        elif fase == NO_PERDERSE:
            base = round((7 * ingenio + 3 * salud) / 10)
        else:
            raise ValueError(f"fase desconocida: {fase}")
        return max(1, base + self.modificador)


@dataclass(frozen=True)
class Ronda:
    """Una fase visible, con posibles reintentos de empate ocultos."""

    dados: tuple[int, ...]
    totales: tuple[int, ...]
    fase: str = ""
    ganador: int | None = None
    desempates: int = 0
    # Quiénes tiraron de verdad. Vacío quiere decir «todos», que es lo normal:
    # sólo un forcejeo de desempate del tótem lo rellena, porque allí tira nada
    # más quien sigue empatado. `dados` y `totales` se quedan a lo largo del
    # campo entero, con un cero en quien no tiró, para que todo lo que indexa
    # por dorsal —Carrera, Sumo y las sumas— siga funcionando igual.
    dorsales: tuple[int, ...] = ()
    eco: int = 0


def _crudos(rondas: Sequence[Ronda], cuantos: int) -> tuple[int, ...]:
    """Puntos crudos acumulados por cada dorsal a lo largo de esas rondas."""
    return tuple(
        sum(ronda.totales[i] for ronda in rondas) for i in range(cuantos)
    )


def _puntos_de_colocacion(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    """N puntos al mejor de cada fase, N-1 al siguiente y así hasta 1.

    Quien empata dentro de una fase se lleva el puesto de arriba —los dos
    terceros de cinco cobran 3— y el de abajo se salta. Repartir por orden de
    dorsal sería más simple, pero le daría el punto extra al que se apuntó
    antes, que es justo lo que un empate dice que no ha pasado.
    """
    return tuple(
        sum(
            cuantos - sum(otro > ronda.totales[i] for otro in ronda.totales)
            for ronda in rondas
        )
        for i in range(cuantos)
    )


def _oficiales(rondas: Sequence[Ronda]) -> list[Ronda]:
    """Las fases de verdad del tótem: un desempate **no** es una cuarta fase."""
    return [ronda for ronda in rondas if ronda.fase != DESEMPATE]


def _de_desempate(rondas: Sequence[Ronda]) -> list[Ronda]:
    return [ronda for ronda in rondas if ronda.fase == DESEMPATE]


def senda_de_desempate(
    rondas: Sequence[Ronda], dorsal: int
) -> tuple[int, ...]:
    """Lo que sacó un dorsal en cada forcejeo de desempate que jugó, en orden.

    Es una **senda** y no una suma porque los desempates se ramifican: la
    primera ronda parte a los empatados en subgrupos y las siguientes sólo
    ordenan dentro del subgrupo que sigue empatado. Comparadas por orden y de
    mayor a menor, la primera componente decide entre quien salió de ramas
    distintas y las de después sólo desempatan dentro de la misma rama.

    Sumarlas sería otra cosa: quien siguió tirando acumularía puntos que quien
    ya se había resuelto no tiene forma de igualar, y acabaría adelantándolo.
    """
    return tuple(
        ronda.totales[dorsal]
        for ronda in _de_desempate(rondas)
        if not ronda.dorsales or dorsal in ronda.dorsales
    )


def _claves_del_totem(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[tuple[int, int, tuple[int, ...]], ...]:
    """Por dorsal: `(puestos oficiales, bruto oficial, senda de desempate)`.

    Los dos primeros salen **sólo** de las tres fases y no se mueven nunca más.
    La senda va la última, así que sólo ordena a quien ya venía empatado en los
    dos anteriores: si contara para los puestos, un forcejeo entre dos coronaría
    a un tercero que no estaba empatado con nadie.
    """
    oficiales = _oficiales(rondas)
    puestos = _puntos_de_colocacion(oficiales, cuantos)
    brutos = _crudos(oficiales, cuantos)
    sendas = [senda_de_desempate(rondas, i) for i in range(cuantos)]
    return tuple(zip(puestos, brutos, sendas))


def _empatados_del_totem(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    """Quiénes siguen exactamente empatados con alguien, en orden de dorsal.

    Un empate exacto se deshace **entre los suyos**: si a la vez hay dos grupos
    empatados y uno se resuelve antes, la ronda que le hace falta al otro no
    puede volver a tirar por los ya resueltos, porque les cambiaría un orden
    que ya estaba decidido.
    """
    claves = _claves_del_totem(rondas, cuantos)
    return tuple(i for i in range(cuantos) if claves.count(claves[i]) > 1)


def _orden_del_totem(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    """Del 1.º al último por `(puestos, bruto, senda, dorsal)`.

    Todo se compara de mayor a menor, y para eso se le da la vuelta al signo:
    ordenar ascendente por la senda negada es ordenar descendente por la senda,
    componente a componente. Dos sendas con el mismo principio y distinto largo
    no se dan entre empatados, porque quien comparte prefijo comparte también
    grupo y vuelve a tirar con él.
    """
    claves = _claves_del_totem(rondas, cuantos)
    return tuple(sorted(
        range(cuantos),
        key=lambda i: (
            -claves[i][0],
            -claves[i][1],
            tuple(-total for total in claves[i][2]),
            i,
        ),
    ))


def _puertas_del_laberinto(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    oficiales = _oficiales(rondas)
    return tuple(
        sum(ronda.totales[i] > ronda.eco for ronda in oficiales)
        for i in range(cuantos)
    )


def _claves_del_laberinto(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[tuple[int, int, tuple[int, ...]], ...]:
    puertas = _puertas_del_laberinto(rondas, cuantos)
    brutos = _crudos(_oficiales(rondas), cuantos)
    sendas = [senda_de_desempate(rondas, i) for i in range(cuantos)]
    return tuple(zip(puertas, brutos, sendas))


def _empatados_del_laberinto(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    claves = _claves_del_laberinto(rondas, cuantos)
    return tuple(i for i in range(cuantos) if claves.count(claves[i]) > 1)


def _orden_del_laberinto(
    rondas: Sequence[Ronda], cuantos: int
) -> tuple[int, ...]:
    claves = _claves_del_laberinto(rondas, cuantos)
    return tuple(sorted(
        range(cuantos),
        key=lambda i: (
            -claves[i][0],
            -claves[i][1],
            tuple(-total for total in claves[i][2]),
            i,
        ),
    ))


@dataclass(frozen=True)
class Resultado:
    tipo: str
    competidores: tuple[Competidor, ...]
    rondas: list[Ronda]
    orden: tuple[int, ...]  # índices de `competidores`, del 1.º al último

    @property
    def desempates(self) -> int:
        return sum(
            ronda.desempates + (ronda.fase == DESEMPATE)
            for ronda in self.rondas
        )

    @property
    def totales(self) -> tuple[int, ...]:
        """Puntos crudos acumulados, en orden de dorsal.

        En Carrera los desempates son tramos de verdad y suman; en Tótem y
        Laberinto no lo son, así que el bruto oficial se queda en sus fases.
        """
        rondas = (
            _oficiales(self.rondas)
            if self.tipo in (TOTEM, LABERINTO)
            else self.rondas
        )
        return _crudos(rondas, len(self.competidores))

    @property
    def marcadores(self) -> tuple[int, ...]:
        """Puntos acumulados en Carrera, puestos en Tótem, intercambios en Sumo."""
        if self.tipo == CARRERA:
            return self.totales
        if self.tipo == TOTEM:
            return _puntos_de_colocacion(
                _oficiales(self.rondas), len(self.competidores)
            )
        if self.tipo == LABERINTO:
            return _puertas_del_laberinto(self.rondas, len(self.competidores))
        return tuple(
            sum(ronda.ganador == i for ronda in self.rondas)
            for i in range(len(self.competidores))
        )

    @property
    def clasificacion(self) -> tuple[tuple[Competidor, int], ...]:
        """`(competidor, marcador)` del primero al último."""
        marcadores = self.marcadores
        return tuple((self.competidores[i], marcadores[i]) for i in self.orden)

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
    # Marcador del último combate: puntos de Carrera o intercambios de Sumo.
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
        ganador = combate.orden[0]
        if combate.tipo == SUMO:
            ganados = 0
            for ronda in combate.rondas:
                if ronda.ganador == ganador:
                    ganados += 1
                if ganados == 2:
                    rival = 1 - ganador
                    return abs(ronda.totales[ganador] - ronda.totales[rival])
            raise ValueError("sumo sin intercambio decisivo")

        totales = combate.totales
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
    criatura: sim.Criatura,
    *,
    bonus_fuerza: int = 0,
    bonus_velocidad: int = 0,
    bonus_salud: int = 0,
    bonus_ingenio: int = 0,
) -> Competidor:
    """La criatura vista como competidor, sin consultar persistencia."""
    return Competidor(
        nombre=criatura.nombre,
        especie=criatura.especie,
        fuerza=criatura.fuerza,
        velocidad=criatura.velocidad,
        salud=criatura.salud,
        modificador=modificador_por_estado(criatura.hambre, criatura.animo),
        bonus_fuerza=bonus_fuerza,
        bonus_velocidad=bonus_velocidad,
        bonus_salud=bonus_salud,
        bonus_ingenio=bonus_ingenio,
        animo=criatura.animo_visual,
        ingenio=criatura.ingenio,
    )


def _base_del_eco(competidores: Sequence[Competidor], fase: str) -> int:
    return round(statistics.median(c.base_en(fase) for c in competidores))


def resolver(
    competidores: Sequence[Competidor],
    tipo: str,
    rng: random.Random | None = None,
) -> Resultado:
    """Resuelve una Carrera acumulativa o un Sumo al mejor de tres."""
    competidores = tuple(competidores)
    rng = rng or random.Random()
    rondas: list[Ronda] = []

    def tirar(fase: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
        dados = tuple(rng.randint(1, CARA_DADO) for _ in competidores)
        totales = tuple(
            c.base_en(fase) + dado
            for c, dado in zip(competidores, dados)
        )
        return dados, totales

    if tipo == CARRERA:
        for fase in FASES_CARRERA:
            dados, totales = tirar(fase)
            rondas.append(Ronda(dados, totales, fase))

        totales = tuple(
            sum(r.totales[i] for r in rondas)
            for i in range(len(competidores))
        )
        desempates = 0
        while len(set(totales)) != len(totales) and desempates < MAX_DESEMPATES:
            dados, puntos = tirar(SALIDA)
            rondas.append(Ronda(dados, puntos, DESEMPATE))
            totales = tuple(
                sum(r.totales[i] for r in rondas)
                for i in range(len(competidores))
            )
            desempates += 1
        orden = tuple(
            sorted(range(len(competidores)), key=lambda i: (-totales[i], i))
        )
        return Resultado(tipo, competidores, rondas, orden)

    if tipo == TOTEM:
        cuantos = len(competidores)
        for fase in FASES_TOTEM:
            dados, totales = tirar(fase)
            rondas.append(Ronda(dados, totales, fase))

        def forcejear(quienes: tuple[int, ...]) -> Ronda:
            """Un forcejeo de desempate en el que sólo tiran `quienes`.

            Quien no tira se queda a cero en esa ronda, así que su tercer
            criterio no se mueve y su sitio tampoco.
            """
            dados = [0] * cuantos
            totales = [0] * cuantos
            for dorsal in quienes:
                dado = rng.randint(1, CARA_DADO)
                dados[dorsal] = dado
                totales[dorsal] = competidores[dorsal].base_en(FORCEJEO) + dado
            return Ronda(
                tuple(dados), tuple(totales), DESEMPATE, dorsales=quienes
            )

        desempates = 0
        # El tótem se decide agarrándolo, así que el desempate es otro forcejeo.
        # Cada ronda añade una componente a la senda de quien tira, que es el
        # tercer criterio y el último antes del dorsal; las componentes de antes
        # no se tocan, así que el orden que ya abrió una ronda anterior se
        # mantiene. Sólo tira quien sigue empatado: dos grupos pueden compartir
        # una ronda, y el que se resuelva primero se queda fuera de las
        # siguientes.
        while desempates < MAX_DESEMPATES:
            pendientes = _empatados_del_totem(rondas, cuantos)
            if not pendientes:
                break
            rondas.append(forcejear(pendientes))
            desempates += 1

        return Resultado(
            tipo, competidores, rondas, _orden_del_totem(rondas, cuantos)
        )

    if tipo == LABERINTO:
        cuantos = len(competidores)
        for fase in FASES_LABERINTO:
            eco = _base_del_eco(competidores, fase) + rng.randint(1, CARA_DADO)
            dados, totales = tirar(fase)
            rondas.append(Ronda(dados, totales, fase, eco=eco))

        def recorrer(quienes: tuple[int, ...]) -> Ronda:
            dados = [0] * cuantos
            totales = [0] * cuantos
            for dorsal in quienes:
                dado = rng.randint(1, CARA_DADO)
                dados[dorsal] = dado
                totales[dorsal] = competidores[dorsal].base_en(SENALES) + dado
            return Ronda(
                tuple(dados), tuple(totales), DESEMPATE, dorsales=quienes
            )

        desempates = 0
        while desempates < MAX_DESEMPATES:
            pendientes = _empatados_del_laberinto(rondas, cuantos)
            if not pendientes:
                break
            rondas.append(recorrer(pendientes))
            desempates += 1

        return Resultado(
            tipo, competidores, rondas, _orden_del_laberinto(rondas, cuantos)
        )

    marcadores = [0, 0]
    for fase in FASES_SUMO:
        dados, totales = tirar(fase)
        desempates = 0
        while totales[0] == totales[1] and desempates < MAX_DESEMPATES:
            desempates += 1
            dados, totales = tirar(fase)
        ganador = 0 if totales[0] >= totales[1] else 1
        rondas.append(Ronda(dados, totales, fase, ganador, desempates))
        marcadores[ganador] += 1
        if marcadores[ganador] == 2:
            break

    orden = tuple(sorted((0, 1), key=lambda i: (-marcadores[i], i)))
    return Resultado(tipo, competidores, rondas, orden)


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
        marcadores=combate.marcadores,
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
    # (dorsal, intercambios ganados, puntos crudos en su semifinal)
    caidos: list[tuple[int, int, int]] = []

    for pareja in parejas:
        semifinal = resolver([competidores[d] for d in pareja], tipo, rng)
        combates.append(semifinal)
        finalistas.append(pareja[semifinal.orden[0]])
        indice_perdedor = semifinal.orden[-1]
        caidos.append((
            pareja[indice_perdedor],
            semifinal.marcadores[indice_perdedor],
            semifinal.totales[indice_perdedor],
        ))

    final = resolver([competidores[d] for d in finalistas], tipo, rng)
    combates.append(final)

    campeon = finalistas[final.orden[0]]
    subcampeon = finalistas[final.orden[1]]
    # Los dos de semifinales no pelean por el bronce: primero manda cuántos
    # intercambios ganaron, después sus puntos crudos y por último el dorsal.
    caidos.sort(key=lambda caido: (-caido[1], -caido[2], caido[0]))

    marcadores = [0] * len(competidores)
    marcadores[campeon] = final.marcadores[final.orden[0]]
    marcadores[subcampeon] = final.marcadores[final.orden[1]]
    for dorsal, marcador, _ in caidos:
        marcadores[dorsal] = marcador

    return Encuentro(
        tipo=tipo,
        competidores=competidores,
        combates=tuple(combates),
        orden=(campeon, subcampeon, *(dorsal for dorsal, _, _ in caidos)),
        marcadores=tuple(marcadores),
    )


# --- Narración -------------------------------------------------------------

def _cabecera(resultado: Resultado, paso: int, titulo: str) -> list[str]:
    """El título del combate y la fase real que se está mostrando."""
    ronda = resultado.rondas[paso - 1]
    etiqueta = ronda.fase + ("*" if ronda.desempates else "")
    return [
        "╭" + "─" * pantalla.ANCHO + "╮",
        pantalla.fila(f" {titulo[:12]:<12}{etiqueta:>12} "),
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
    ancho_base = max(
        [2]
        + [
            len(str(total - dado))
            for ronda in resultado.rondas
            for dado, total in zip(ronda.dados, ronda.totales)
        ]
    )
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
    base = total - dado
    return pantalla.fila(
        f" {c.nombre[:ancho_nombre]:<{ancho_nombre}} "
        f"{base:>{ancho_base}}+d20 {dado:>2} = {total:>{ancho_total}} "
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
        marcadores = tuple(
            sum(ronda.ganador == i for ronda in resultado.rondas[:paso])
            for i in (0, 1)
        )
        ronda = resultado.rondas[paso - 1]
        desplazamiento = 3 * (marcadores[0] - marcadores[1])

        cuerpo = _cabecera(resultado, paso, titulo)
        cuerpo.append(pantalla.fila(
            f" {a.nombre[:11]:<11}{b.nombre[:11]:>13} "
        ))
        cuerpo.append(pantalla.fila(f" {_dohyo(desplazamiento)} "))
        cuerpo.append(pantalla.fila(
            f" {marcadores[0]:<11}{marcadores[1]:>13} "
        ))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        cuerpo.append(_fila_dado(a, ronda.dados[0], ronda.totales[0],
                                 ancho_base, ancho_total))
        cuerpo.append(_fila_dado(b, ronda.dados[1], ronda.totales[1],
                                 ancho_base, ancho_total))
        cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")
        fotogramas.append("```ansi\n" + "\n".join(cuerpo) + "\n```")

    return fotogramas


# El tótem se dibuja en un campo de ancho fijo para que se vea que cambia de
# sitio: en las dos primeras fases está en el centro y en la HUIDA, desplazado
# hacia la derecha porque se lo están llevando.
ANCHO_ESCENA = 15
ALTO_ESCENA = 3

ESCENAS_TOTEM = {
    CENTRO: (
        "      ┌─┐      ",
        ">>>>  │#│  <<<<",
        "      └─┘      ",
    ),
    FORCEJEO: (
        "     \\┌─┐/     ",
        "  >>>-│#│-<<<  ",
        "     /└─┘\\     ",
    ),
    HUIDA: (
        "          ┌─┐  ",
        " >>>  >>  │#│>>",
        "          └─┘  ",
    ),
}


def _narracion_del_totem(resultado: Resultado, paso: int) -> str:
    """Cuenta el resultado ya resuelto de una fase o forcejeo extra."""
    ronda = resultado.rondas[paso - 1]

    def nombres(dorsales: Sequence[int]) -> str:
        ns = [resultado.competidores[dorsal].nombre for dorsal in dorsales]
        return ns[0] if len(ns) == 1 else ", ".join(ns[:-1]) + " y " + ns[-1]

    if ronda.fase != DESEMPATE:
        mejor = max(ronda.totales)
        mejores = tuple(
            dorsal for dorsal, total in enumerate(ronda.totales)
            if total == mejor
        )
        quienes = nombres(mejores)
        if ronda.fase == CENTRO:
            return (
                f"{quienes} llega primero al tótem."
                if len(mejores) == 1 else
                f"{quienes} llegan juntos al tótem."
            )
        if ronda.fase == FORCEJEO:
            return (
                f"{quienes} gana el forcejeo y toma el control del tótem."
                if len(mejores) == 1 else
                f"{quienes} forcejean sin ceder el control del tótem."
            )
        return (
            f"{quienes} escapa con el tótem y resiste la persecución."
            if len(mejores) == 1 else
            f"{quienes} resisten juntos la huida con el tótem."
        )

    claves_antes = _claves_del_totem(resultado.rondas[:paso - 1],
                                     len(resultado.competidores))
    grupos: dict[tuple[int, int, tuple[int, ...]], list[int]] = {}
    for dorsal in ronda.dorsales:
        grupos.setdefault(claves_antes[dorsal], []).append(dorsal)

    frases = []
    for grupo in grupos.values():
        por_total: dict[int, list[int]] = {}
        for dorsal in grupo:
            por_total.setdefault(ronda.totales[dorsal], []).append(dorsal)
        empatados = [dorsales for dorsales in por_total.values()
                     if len(dorsales) > 1]
        if not empatados:
            ganador = max(grupo, key=lambda dorsal: ronda.totales[dorsal])
            frases.append(
                f"{nombres((ganador,))} rompe el empate en el forcejeo."
            )
            continue
        ganador = max(grupo, key=lambda dorsal: ronda.totales[dorsal])
        if len(por_total[ronda.totales[ganador]]) == 1:
            frases.append(
                f"{nombres((ganador,))} toma ventaja en el forcejeo."
            )
        frases.extend(
            f"{nombres(dorsales)} siguen empatados en el forcejeo."
            for dorsales in empatados
        )
    return " ".join(frases)


def fotogramas_totem(resultado: Resultado, titulo: str) -> list[str]:
    """Un mensaje por fase: la escena, los dados y cómo va el reparto de puestos.

    Los puestos se pintan con la fila del podio —la misma de `resumen()`—
    porque es justo lo que se está disputando: el marcador del tótem no es lo
    que se saca, sino en qué lugar se queda uno fase tras fase.

    En un fotograma de desempate los puntos ya no se mueven —el desempate no es
    una fase—, pero las filas sí se reordenan: se ordenan con la misma clave con
    la que se reparte el premio, así que el último fotograma enseña exactamente
    el orden del resultado.
    """
    cuantos = len(resultado.competidores)
    ancho_base, ancho_total = _anchos_del_dado(resultado)
    fotogramas = []

    for paso in range(1, len(resultado.rondas) + 1):
        ronda = resultado.rondas[paso - 1]
        hasta_aqui = resultado.rondas[:paso]
        puntos = _puntos_de_colocacion(_oficiales(hasta_aqui), cuantos)
        ancho_puntos = max([3] + [len(str(punto)) for punto in puntos])

        cuerpo = _cabecera(resultado, paso, titulo)
        # Un desempate es otro forcejeo, así que se dibuja como tal.
        for linea in ESCENAS_TOTEM.get(ronda.fase, ESCENAS_TOTEM[FORCEJEO]):
            cuerpo.append(pantalla.fila(f"{linea:^{pantalla.ANCHO}}"))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        # En un desempate sólo tiran los que siguen empatados, así que sólo
        # ellos salen aquí; la clasificación de abajo sigue siendo del campo
        # entero.
        for dorsal in ronda.dorsales or range(cuantos):
            cuerpo.append(_fila_dado(
                resultado.competidores[dorsal],
                ronda.dados[dorsal], ronda.totales[dorsal],
                ancho_base, ancho_total,
            ))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        for puesto, dorsal in enumerate(
            _orden_del_totem(hasta_aqui, cuantos), start=1
        ):
            cuerpo.append(_fila_puesto(
                puesto, resultado.competidores[dorsal],
                puntos[dorsal], ancho_puntos,
            ))
        cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")
        fotogramas.append(
            "```ansi\n" + "\n".join(cuerpo) + "\n```\n"
            + _narracion_del_totem(resultado, paso)
        )

    return fotogramas


# El laberinto se dibuja en el mismo campo de ancho fijo que el tótem. Las tres
# escenas cuentan la fase sin una palabra: puertas con señales que leer, un
# trazado de pasillos que recorrer y la salida al final de los repetidos.
ESCENAS_LABERINTO = {
    SENALES: (
        " ╔═╗  ╔═╗  ╔═╗ ",
        " ║?║  ║!║  ║?║ ",
        " ╚═╝  ╚═╝  ╚═╝ ",
    ),
    TRAZADO: (
        "═╗ ╔═══╗ ╔═══╗ ",
        ">>>>╝ ╚>>>╝ ╚>>",
        "══╗ ╔═══╗ ╔═══ ",
    ),
    NO_PERDERSE: (
        " ╔═╗ ╔═╗  ┌─┐  ",
        " ║#║ ║#║  │ │>>",
        " ╚═╝ ╚═╝  └─┘  ",
    ),
}

# Por fase: cruza uno, cruzan varios, no cruza nadie. El tercer caso no es un
# empate ni un fallo del motor: contra el eco puede no pasar nadie, y contarlo
# es parte de lo que distingue al laberinto de las otras tres modalidades.
NARRACIONES_LABERINTO = {
    SENALES: (
        "{quienes} descifra las señales.",
        "{quienes} descifran las señales a la vez.",
        "El eco confunde las señales: nadie cruza.",
    ),
    TRAZADO: (
        "{quienes} traza la ruta sin dudar.",
        "{quienes} trazan rutas parejas.",
        "Los pasillos se repiten: nadie avanza.",
    ),
    NO_PERDERSE: (
        "{quienes} sale del laberinto y su eco se apaga.",
        "{quienes} salen a la vez.",
        "El laberinto retiene a todos una vuelta más.",
    ),
}


def _narracion_del_laberinto(
    ronda: Ronda, competidores: Sequence[Competidor]
) -> str:
    """Quién abrió la puerta de esta fase, o que no la abrió nadie.

    Un desempate se queda sin línea: no tiene eco, así que no hay puerta que
    contar y cualquier frase sobre cruzar sería inventada.
    """
    plantillas = NARRACIONES_LABERINTO.get(ronda.fase)
    if plantillas is None:
        return ""
    cruzan = [
        competidores[dorsal].nombre
        for dorsal, total in enumerate(ronda.totales)
        if total > ronda.eco
    ]
    una, varias, ninguna = plantillas
    if not cruzan:
        return ninguna
    if len(cruzan) == 1:
        return una.format(quienes=cruzan[0])
    return varias.format(
        quienes=", ".join(cruzan[:-1]) + " y " + cruzan[-1]
    )


def _fila_de_puertas(puesto: int, competidor: Competidor, puertas: int) -> str:
    """`1. Pelusa     2 puertas`, la clasificación parcial de una fase."""
    return pantalla.fila(
        f" {puesto}. {competidor.nombre[:10]:<10} "
        f"{puertas} puerta{'s' if puertas != 1 else ''} "
    )


def fotogramas_laberinto(resultado: Resultado, titulo: str) -> list[str]:
    """Un mensaje por fase: la escena, el eco, quién lo supera y las puertas.

    La marca ✓/✗ ocupa el espacio con el que empieza la fila del dado, así que
    el presupuesto de esa fila no cambia y los nombres siguen teniendo el mismo
    sitio que en las otras modalidades.

    En un desempate no hay eco —no es una fase oficial— y el reparto de puertas
    ya no se mueve, pero las filas sí se reordenan con la clave definitiva, así
    que el último fotograma enseña el orden con el que se cierra.
    """
    cuantos = len(resultado.competidores)
    ancho_base, ancho_total = _anchos_del_dado(resultado)
    fotogramas = []

    for paso in range(1, len(resultado.rondas) + 1):
        ronda = resultado.rondas[paso - 1]
        hasta_aqui = resultado.rondas[:paso]
        puertas = _puertas_del_laberinto(hasta_aqui, cuantos)
        oficial = ronda.fase in ESCENAS_LABERINTO

        cuerpo = _cabecera(resultado, paso, titulo)
        # El desempate vuelve a la base de SEÑALES, así que se dibuja como tal.
        for linea in ESCENAS_LABERINTO.get(ronda.fase, ESCENAS_LABERINTO[SENALES]):
            cuerpo.append(pantalla.fila(f"{linea:^{pantalla.ANCHO}}"))
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        if oficial:
            cuerpo.append(pantalla.fila(f" eco del pasillo {ronda.eco:>7} "))
        for dorsal in ronda.dorsales or range(cuantos):
            fila = _fila_dado(
                resultado.competidores[dorsal],
                ronda.dados[dorsal], ronda.totales[dorsal],
                ancho_base, ancho_total,
            )
            if oficial:
                marca = "✓" if ronda.totales[dorsal] > ronda.eco else "✗"
                fila = fila[0] + marca + fila[2:]
            cuerpo.append(fila)
        cuerpo.append("├" + "─" * pantalla.ANCHO + "┤")
        for puesto, dorsal in enumerate(
            _orden_del_laberinto(hasta_aqui, cuantos), start=1
        ):
            cuerpo.append(_fila_de_puertas(
                puesto, resultado.competidores[dorsal], puertas[dorsal]
            ))
        cuerpo.append("╰" + "─" * pantalla.ANCHO + "╯")

        narracion = _narracion_del_laberinto(ronda, resultado.competidores)
        fotogramas.append(
            "```ansi\n" + "\n".join(cuerpo) + "\n```"
            + (f"\n{narracion}" if narracion else "")
        )

    return fotogramas


def como_se_llama(tipo: str, cuantos: int) -> str:
    """«una CARRERA», «un SUMO», «un TORNEO DE SUMO» o «un ASALTO AL TÓTEM»."""
    if tipo == SUMO and cuantos == CUANTOS_EN_TORNEO:
        return "un TORNEO DE SUMO"
    return ARTICULOS[tipo]


def _titulos(encuentro: Encuentro) -> tuple[str, ...]:
    """El rótulo de cada combate: la ronda del torneo, o la modalidad si es uno."""
    if encuentro.es_torneo:
        return RONDAS_DEL_TORNEO
    return (NOMBRES[encuentro.tipo],)


DIBUJANTES = {
    CARRERA: fotogramas_carrera,
    SUMO: fotogramas_sumo,
    TOTEM: fotogramas_totem,
    LABERINTO: fotogramas_laberinto,
}


def fotogramas_de(encuentro: Encuentro) -> list[list[str]]:
    """Los fotogramas de cada combate, en orden y con el título de su ronda.

    Una lista por combate: el cog manda un mensaje por cada una y la va editando
    para animarla. Un torneo son tres tandas; todo lo demás, una.
    """
    dibujar = DIBUJANTES[encuentro.tipo]
    return [
        dibujar(combate, titulo)
        for combate, titulo in zip(encuentro.combates, _titulos(encuentro))
    ]


# --- El podio --------------------------------------------------------------

MEDALLAS = ("🥇", "🥈", "🥉")
PUESTOS_EN_EL_PODIO = 3

# Cada cajón mide lo mismo que el token de un gachamón, `(` + cara + `)`, porque
# las veinticinco especies tienen la cara de tres caracteres exactos. Eso es lo
# que hace que la cara caiga siempre justo encima de su cajón sin medir nada.
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
    """Reintentos ocultos de Sumo y rondas visibles de Carrera."""
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
        Purreon    ─┘

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
        f"{c.competidor_ganador.nombre} "
        f"{c.marcadores[c.orden[0]]}–{c.marcadores[c.orden[1]]} "
        f"{c.competidor_perdedor.nombre}"
        for c in encuentro.combates
    )
    return (
        f"## 🏆 Campeón de {NOMBRES[encuentro.tipo]}\n"
        f"{MEDALLAS[0]} **{campeon.nombre}**\n"
        "```ansi\n" + "\n".join(cuerpo) + "\n```"
        f"\n-# Intercambios: {marcadores}"
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
    marcador = (
        f"{combate.marcadores[combate.orden[0]]}–"
        f"{combate.marcadores[combate.orden[1]]}"
    )
    regla = REGLA_DEL_MARCADOR[encuentro.tipo]
    return (
        f"🏆 **{ganador.nombre}** gana a **{perdedor.nombre}** por "
        f"{marcador}{regla}."
        + _nota_de_desempates(encuentro)
    )
