"""El departamento: la vivienda por casillas de cada persona.

Módulo puro: catálogo y reglas, sin base de datos ni Discord. Sólo conoce a
`simulacion`, para entregarle el ritmo.

Un departamento es una cuadrícula de `ancho × fondo` casillas, de 3 × 3 a
8 × 8, más dos paredes al fondo: la fila `y = -1` y la columna `x = -1`. Cada
mueble ocupa su sitio en una de tres capas: lo de **suelo** se pisa (un felpudo,
una alfombra), un **bulto** ocupa su casilla y lo de **pared** cuelga de los
tramos de una de las dos paredes. Dos piezas chocan sólo si son de la misma
capa. Las camas son el límite de gachamones: una para ti y una por cada uno.
"""
from __future__ import annotations

from dataclasses import dataclass

import simulacion as sim

SUELO = "suelo"
BULTO = "bulto"
PARED = "pared"

NO_ES_TUYO = "no_es_tuyo"
NO_CABE = "no_cabe"
OCUPADO = "ocupado"

ANCHO = "ancho"
FONDO = "fondo"

LADO_INICIAL = 3
LADO_MAXIMO = 8
PRECIO_POR_CASILLA = 15
COMODIDAD_BASE = 80
# En 8 × 8 caben 32 camas, menos la tuya.
MAXIMO_DE_GACHAMONES = 31

# Los dos extremos del alivio del ánimo: sin comodidad de más (75) no alivia, y
# de 150 en adelante alivia lo más que se puede.
_COMODIDAD_SIN_ALIVIO = 75
_COMODIDAD_DE_TOPE = 150
_ALIVIO_MAXIMO = 0.25


@dataclass(frozen=True)
class Mueble:
    clave: str
    nombre: str
    emoji: str
    precio: int
    comodidad: int
    ancho: int = 1      # en lo de pared, son sus tramos
    fondo: int = 1
    capa: str = BULTO
    cama: bool = False


MUEBLES: dict[str, Mueble] = {
    mueble.clave: mueble
    for mueble in (
        Mueble("felpudo", "Felpudo", "🚪", 30, 2, capa=SUELO),
        Mueble("maceta", "Maceta", "🪴", 50, 3),
        Mueble("cuadro", "Cuadro", "🖼️", 50, 3, capa=PARED),
        Mueble("estanteria", "Estantería", "🗄️", 80, 4, ancho=2),
        Mueble("lampara", "Lámpara", "💡", 80, 4),
        Mueble("alfombra", "Alfombra", "🧶", 120, 5, ancho=2, fondo=2, capa=SUELO),
        Mueble("cortinas", "Cortinas", "🪟", 120, 5, ancho=2, capa=PARED),
        Mueble("cojines", "Cojines", "🛋️", 180, 6),
        Mueble("fuente", "Fuente", "⛲", 180, 6, ancho=2, fondo=2),
        Mueble("chimenea", "Chimenea", "🔥", 180, 6, ancho=2),
        Mueble("calefactor", "Calefactor", "🌡️", 280, 7),
        Mueble("cama", "Cama grande", "🛏️", 280, 7, ancho=2, cama=True),
        Mueble("ventanal", "Ventanal", "🏞️", 280, 7, ancho=2, capa=PARED),
        Mueble("biblioteca", "Biblioteca", "📚", 280, 7, ancho=2),
        Mueble("cama_sencilla", "Cama sencilla", "🛏️", 85, 2, ancho=2, cama=True),
    )
}


@dataclass(frozen=True)
class Pieza:
    id: int
    clave: str
    x: int | None = None
    y: int | None = None
    giro: int = 0

    @property
    def puesta(self) -> bool:
        return self.x is not None and self.y is not None


def tope_de_comodidad(casillas: int) -> int:
    """Hasta dónde llega la comodidad: sube con el tamaño del departamento."""
    return 100 + (casillas - 9) * 50 // 55


@dataclass(frozen=True)
class Departamento:
    ancho: int = LADO_INICIAL
    fondo: int = LADO_INICIAL
    piezas: tuple[Pieza, ...] = ()

    @property
    def casillas(self) -> int:
        return self.ancho * self.fondo

    @property
    def puestas(self) -> tuple[Pieza, ...]:
        return tuple(p for p in self.piezas if p.puesta)

    @property
    def guardadas(self) -> tuple[Pieza, ...]:
        return tuple(p for p in self.piezas if not p.puesta)

    @property
    def camas_puestas(self) -> int:
        return sum(1 for p in self.puestas if p.clave in MUEBLES and MUEBLES[p.clave].cama)

    @property
    def comodidad(self) -> int:
        """La base más la de cada tipo de mueble puesto, una vez, hasta el tope.

        Un tipo que ya no está en el catálogo no suma: nadie conserva una
        comodidad que ya no se puede volver a conseguir.
        """
        tipos = {p.clave for p in self.puestas if p.clave in MUEBLES}
        suma = sum(MUEBLES[c].comodidad for c in tipos)
        return min(tope_de_comodidad(self.casillas), COMODIDAD_BASE + suma)

    def pieza(self, pieza_id: int) -> Pieza | None:
        return next((p for p in self.piezas if p.id == pieza_id), None)


DE_PARTIDA = Departamento(
    piezas=(
        Pieza(0, "cama_sencilla", 0, 0),
        Pieza(0, "cama_sencilla"),
    ),
)


def huella(mueble: Mueble, x: int, y: int, giro: int) -> frozenset[tuple[int, int]]:
    """Las casillas (o tramos) que ocupa el mueble puesto en (x, y).

    Lo de pared va en la fila `y = -1` o en la columna `x = -1`, y el giro no
    le cambia nada. Lo demás ocupa `ancho × fondo`, o `fondo × ancho` si el giro
    es 1 o 3.
    """
    if mueble.capa == PARED:
        if x == -1 and y != -1:
            return frozenset((x, y + i) for i in range(mueble.ancho))
        return frozenset((x + i, y) for i in range(mueble.ancho))
    largo, hondo = (mueble.ancho, mueble.fondo) if giro % 2 == 0 else (mueble.fondo, mueble.ancho)
    return frozenset((x + i, y + j) for i in range(largo) for j in range(hondo))


def _cabe(depto: Departamento, mueble: Mueble, casillas: frozenset[tuple[int, int]]) -> bool:
    if mueble.capa == PARED:
        return all(
            (cy == -1 and 0 <= cx < depto.ancho) or (cx == -1 and 0 <= cy < depto.fondo)
            for cx, cy in casillas
        )
    return all(0 <= cx < depto.ancho and 0 <= cy < depto.fondo for cx, cy in casillas)


def problema_al_poner(depto: Departamento, pieza_id: int, x: int, y: int, giro: int) -> str | None:
    """Por qué no se puede poner esa pieza ahí, o `None` si se puede."""
    pieza = depto.pieza(pieza_id)
    mueble = MUEBLES.get(pieza.clave) if pieza else None
    if mueble is None:
        return NO_ES_TUYO
    casillas = huella(mueble, x, y, giro)
    if not _cabe(depto, mueble, casillas):
        return NO_CABE
    for otra in depto.puestas:
        if otra.id == pieza_id:
            continue
        del_otro = MUEBLES.get(otra.clave)
        if del_otro is None or del_otro.capa != mueble.capa:
            continue
        if casillas & huella(del_otro, otra.x, otra.y, otra.giro):
            return OCUPADO
    return None


def cama_libre(depto: Departamento, vivos: int) -> bool:
    """Si sobra una cama puesta: la tuya y una por cada gachamon vivo ya están."""
    return depto.camas_puestas >= vivos + 2


def puede_guardarse(depto: Departamento, pieza_id: int, vivos: int) -> bool:
    pieza = depto.pieza(pieza_id)
    es_cama_puesta = (
        pieza is not None and pieza.puesta and pieza.clave in MUEBLES and MUEBLES[pieza.clave].cama
    )
    return not (es_cama_puesta and depto.camas_puestas - 1 < vivos + 1)


def alivio_de_animo(comodidad: int) -> float:
    """El multiplicador del ánimo: 1.0 en 75 y 0.75 de 150 en adelante."""
    de_mas = max(0, comodidad - _COMODIDAD_SIN_ALIVIO)
    margen = _COMODIDAD_DE_TOPE - _COMODIDAD_SIN_ALIVIO
    return 1.0 - _ALIVIO_MAXIMO * min(1.0, de_mas / margen)


def ritmo_de(depto: Departamento) -> sim.Ritmo:
    return sim.Ritmo(animo=alivio_de_animo(depto.comodidad))


def coste_de_ampliar(depto: Departamento, eje: str) -> int | None:
    """15 por casilla que suma; `None` si ese lado ya mide lo máximo."""
    if eje == ANCHO:
        return None if depto.ancho >= LADO_MAXIMO else PRECIO_POR_CASILLA * depto.fondo
    return None if depto.fondo >= LADO_MAXIMO else PRECIO_POR_CASILLA * depto.ancho


def tamano_para(camas: int) -> tuple[int, int]:
    """El primero de 3 × 3, 4 × 3, 4 × 4, 5 × 4… 8 × 8 con casillas para esas camas."""
    ancho = fondo = LADO_INICIAL
    while ancho * fondo < 2 * camas + 5 and (ancho, fondo) != (LADO_MAXIMO, LADO_MAXIMO):
        if ancho == fondo:
            ancho += 1
        else:
            fondo += 1
    return ancho, fondo


def acomodar_camas(ancho: int, fondo: int, cuantas: int) -> tuple[tuple[int, int, int], ...]:
    """Dónde deja el alcalde `cuantas` camas de 2 × 1 en un departamento vacío.

    Por filas, de a dos columnas. Si el ancho es impar, la última columna se
    llena con camas giradas, de a dos filas.
    """
    sitios = [(x, y, 0) for y in range(fondo) for x in range(0, ancho - 1, 2)]
    if ancho % 2:
        sitios += [(ancho - 1, y, 1) for y in range(0, fondo - 1, 2)]
    if cuantas > len(sitios):
        raise ValueError(f"en {ancho} × {fondo} no caben {cuantas} camas")
    return tuple(sitios[:cuantas])
