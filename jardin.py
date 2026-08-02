"""La escena del jardín: varias criaturas dibujadas juntas.

Módulo puro. Todo el trabajo es de reparto: convertir una lista de criaturas en
un cuadro de texto donde caben varias, alineadas como si pisaran el mismo
suelo. No sabe nada de Discord ni de la base de datos, así que se puede probar
con cualquier combinación de tamaños.

El ancho es mayor que el de la pantalla individual (26) porque aquí caben
varias criaturas. En el móvil el bloque de código se desplaza en horizontal,
que es un precio razonable a cambio de verlas todas juntas.
"""
from __future__ import annotations

import textwrap

import cosmeticos as cos
import especies as esp
import pantalla
import simulacion as sim

ANCHO = 44
SEPARACION = 3      # espacios entre dos criaturas de la misma fila
SUELO = ","         # el carácter con el que se dibuja la tierra

# Discord corta un mensaje en 2000 caracteres, y el jardín es lo ÚNICO del juego
# que crece con la gente que juega: la ficha, la casa y la tienda tienen tamaño
# acotado, pero aquí cabe un bicho más por cada uno que nazca. Con 28 criaturas
# el cuadro pedía 7500 caracteres y el comando reventaba entero.
TOPE_MENSAJE = 2000

# Lo que la IA puede escribir aquí. Más corto que el tope general de `ia`, que
# son 600: el jardín es un cuadro con un pie, no una redacción, y cada carácter
# de narración es un carácter menos de dibujo. Se le pasa a `ia.generar`.
LARGO_NARRACION = 280

# Lo que se reserva para lo que va FUERA del cuadro: el título con la cuenta, la
# narración ya citada línea a línea con «> », y la coletilla de las que no caben.
# Un test lo ata a `LARGO_NARRACION`; si aquél crece y éste no, el mensaje se
# pasaría del tope y Discord lo rechazaría entero.
MARGEN_DEL_TEXTO = 400


class Bloque:
    """Una criatura lista para colocar: su dibujo y su nombre debajo."""

    def __init__(self, lineas: list[str], nombre: str, color: str):
        self.lineas = lineas
        self.nombre = nombre
        self.color = color
        self.ancho_arte = max([len(l) for l in lineas] + [0])
        self.ancho = max(self.ancho_arte, len(nombre))
        # Un único margen para TODO el dibujo. Centrar cada línea por separado
        # rompería el dibujo: la sangría propia de cada línea cuenta para su
        # longitud, así que las líneas más indentadas se desplazarían más que
        # las otras y el bicho saldría corrido.
        self._margen_arte = (self.ancho - self.ancho_arte) // 2

    @property
    def alto(self) -> int:
        return len(self.lineas) + 1  # +1 por la línea del nombre

    def linea(self, i: int) -> str:
        """La línea `i` del bloque, ya colocada dentro de su ancho."""
        if i == len(self.lineas):
            margen = (self.ancho - len(self.nombre)) // 2
            return (" " * margen + self.nombre).ljust(self.ancho)
        return (" " * self._margen_arte + self.lineas[i]).ljust(self.ancho)


def bloque_de(criatura: sim.Criatura) -> Bloque:
    definicion = criatura.def_especie
    arte = esp.arte_de(definicion, criatura.etapa, criatura.animo_visual)
    lineas = [l.rstrip() for l in textwrap.dedent(arte.strip("\n")).split("\n")]
    nombre = criatura.nombre[:ANCHO]
    return Bloque(
        lineas, nombre, cos.color_del_tinte(criatura.tinte, definicion.color)
    )


def repartir(bloques: list[Bloque], ancho: int = ANCHO) -> list[list[Bloque]]:
    """Empaqueta los bloques en filas que quepan en `ancho`.

    Con avaricia: se van añadiendo mientras quepan. Una criatura más ancha que
    la fila entera va sola en la suya en vez de romper el marco.
    """
    filas: list[list[Bloque]] = []
    actual: list[Bloque] = []
    usado = 0

    for bloque in bloques:
        necesario = bloque.ancho if not actual else usado + SEPARACION + bloque.ancho
        if actual and necesario > ancho:
            filas.append(actual)
            actual, usado = [bloque], bloque.ancho
        else:
            actual.append(bloque)
            usado = necesario

    if actual:
        filas.append(actual)
    return filas


def _pintar_fila(fila: list[Bloque], ancho: int) -> list[str]:
    """Dibuja una fila alineando los bloques por abajo.

    Alinear por abajo es lo que hace que todas parezcan estar de pie sobre el
    mismo suelo, en vez de flotando a alturas distintas.
    """
    alto = max(b.alto for b in fila)
    juntos = SEPARACION * (len(fila) - 1) + sum(b.ancho for b in fila)
    margen = max(0, (ancho - juntos) // 2)

    salida = []
    for i in range(alto):
        trozos = []
        for bloque in fila:
            desfase = alto - bloque.alto
            if i < desfase:
                trozos.append(" " * bloque.ancho)
            else:
                trozos.append(pantalla.pintar(bloque.linea(i - desfase), bloque.color))
        # El ancho visible se calcula con las piezas sin color, que son de
        # tamaño fijo por construcción.
        cuerpo = " " * margen + (" " * SEPARACION).join(trozos)
        relleno = ancho - margen - juntos
        salida.append(f"│{cuerpo}{' ' * max(0, relleno)}│")
    return salida


def cuerpo_de(
    criaturas: list[sim.Criatura],
    ancho: int,
    suelo: str = SUELO,
    vacio: str = "El jardín está vacío.",
) -> list[str]:
    """Las filas de criaturas ya pintadas, cada una sobre su suelo.

    Sin el marco de fuera: es lo que comparten el jardín y la casa, que sólo se
    diferencian en qué llevan alrededor y en de qué está hecho el suelo.
    """
    if not criaturas:
        # Nada de pantalla.fila() aquí: está fijada al ancho de la pantalla
        # individual (26) y dejaría el marco descuadrado.
        return [_centrado("", ancho), _centrado(vacio, ancho), _centrado("", ancho)]

    cuerpo: list[str] = []
    for fila in repartir([bloque_de(c) for c in criaturas], ancho):
        cuerpo += _pintar_fila(fila, ancho)
        cuerpo.append("│" + suelo * ancho + "│")
    return cuerpo


def render(criaturas: list[sim.Criatura], ancho: int = ANCHO) -> str:
    """El cuadro del jardín con todas las criaturas."""
    cuerpo = ["╭" + "─" * ancho + "╮"]
    cuerpo += cuerpo_de(criaturas, ancho)
    cuerpo.append("╰" + "─" * ancho + "╯")
    return "```ansi\n" + "\n".join(cuerpo) + "\n```"


def cuantas_caben(
    criaturas: list[sim.Criatura],
    presupuesto: int = TOPE_MENSAJE - MARGEN_DEL_TEXTO,
) -> int:
    """Cuántas de las primeras caben en un cuadro de ese tamaño.

    No vale con dividir por un tamaño medio: los bichos miden cosas distintas
    —de un Nacar de dos filas a un Magnetrón de veintitrés columnas— y el
    reparto los empaqueta de a dos o de a tres según lo anchos que sean. Así que
    se mide dibujando.

    Se busca por bisección porque el tamaño **crece** con cada criatura que se
    añade: si `n` no cabe, `n + 1` tampoco.
    """
    if not criaturas or len(render(criaturas)) <= presupuesto:
        return len(criaturas)

    bajo, alto = 1, len(criaturas)
    while bajo < alto:
        medio = (bajo + alto + 1) // 2
        if len(render(criaturas[:medio])) <= presupuesto:
            bajo = medio
        else:
            alto = medio - 1
    # Nunca cero: un jardín que dijera «está vacío» habiendo criaturas estaría
    # mintiendo. Si ni una cupiera, es preferible pasarse y que Discord se
    # queje —eso sale en el registro— a enseñar algo falso.
    return bajo


def _centrado(texto: str, ancho: int) -> str:
    margen = max(0, (ancho - len(texto)) // 2)
    return "│" + (" " * margen + texto).ljust(ancho)[:ancho] + "│"


FRASES_VACIO = "-# Nadie vive aquí todavía. Saca un huevo con `/huevo`."

# Cuando la IA no está disponible el jardín tampoco puede quedarse en blanco.
RESPALDO = (
    "Todas se miran de reojo. No pasa nada más, de momento.",
    "Hay un silencio raro en el jardín. Alguien ha debido de decir algo.",
    "Se están ignorando con mucha dedicación.",
    "Reina una calma sospechosa.",
)


def frase_de_respaldo(semilla: int = 0) -> str:
    return RESPALDO[semilla % len(RESPALDO)]
