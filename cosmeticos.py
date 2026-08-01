"""Lo que se le puede poner encima a un gachamon.

Módulo puro, como `logros.py`: el catálogo y cómo se ve cada cosa, sin base ni
Discord. Quién lo lleva puesto vive en la criatura, y pintarlo es de `pantalla`.

Cuatro tipos y **uno activo de cada** por gachamon. Se compran con las gemas que
pagan los logros —es lo que cierra el círculo— y se quedan con el gachamon: son
suyos, como sus medallas, y se van con él cuando se muere.

Comprar otro del mismo tipo **sustituye** al anterior, que se pierde. Es la
misma regla que las pociones y se impone igual, guardando uno solo: una lista
permitiría llevar dos coronas y habría que prohibirlo con código.
"""
from __future__ import annotations

from dataclasses import dataclass

import especies as esp

# Los cuatro tipos. Van como claves y no como cuatro listas sueltas para que la
# tienda, el guardado y el render los recorran igual sin repetir el nombre.
TINTE, SOMBRERO, MARCO, TITULO = "tinte", "sombrero", "marco", "titulo"
TIPOS = (TINTE, SOMBRERO, MARCO, TITULO)

PRECIOS = {TINTE: 20, SOMBRERO: 60, MARCO: 50, TITULO: 30}


@dataclass(frozen=True)
class Cosmetico:
    clave: str
    tipo: str
    nombre: str
    # Qué hace cada uno con esto depende del tipo: el color ANSI del tinte, el
    # dibujo del sombrero, las piezas del marco o el texto del título.
    valor: str

    @property
    def precio(self) -> int:
        return PRECIOS[self.tipo]


# --- Tintes -----------------------------------------------------------------
#
# Los ocho que admite Discord en un bloque ```ansi```. Pintan al gachamon entero
# y sustituyen al color de su especie: un Pyro azul deja de parecer un Pyro, y
# ese es justo el sentido de comprarlo.

TINTES = (
    Cosmetico("tinte_rojo", TINTE, "Rojo", esp.ROJO),
    Cosmetico("tinte_verde", TINTE, "Verde", esp.VERDE),
    Cosmetico("tinte_amarillo", TINTE, "Amarillo", esp.AMARILLO),
    Cosmetico("tinte_azul", TINTE, "Azul", esp.AZUL),
    Cosmetico("tinte_rosa", TINTE, "Rosa", esp.ROSA),
    Cosmetico("tinte_cian", TINTE, "Cian", esp.CIAN),
    Cosmetico("tinte_blanco", TINTE, "Blanco", esp.BLANCO),
    Cosmetico("tinte_gris", TINTE, "Gris", esp.GRIS),
)

# --- Sombreros --------------------------------------------------------------
#
# Una fila de dibujo por encima del gachamon, centrada sobre él. Cabe porque el
# marco reserva siete filas y **ningún dibujo pasa de seis**; hay un test que lo
# vigila, porque el día que alguien dibuje uno de siete el sombrero se comería
# la última fila sin avisar.

SOMBREROS = (
    Cosmetico("corona", SOMBRERO, "Corona", r"\_Y_/"),
    Cosmetico("chistera", SOMBRERO, "Chistera", "[===]"),
    Cosmetico("laurel", SOMBRERO, "Laurel", "(\\|/)"),
    Cosmetico("cuernos", SOMBRERO, "Cuernos", r"\\ //"),
    Cosmetico("aureola", SOMBRERO, "Aureola", "(___)"),
    Cosmetico("cinta", SOMBRERO, "Cinta", "~~~~~"),
)

# --- Marcos -----------------------------------------------------------------
#
# El borde de la caja. El valor son las nueve piezas en el orden en que se leen
# dibujando: arriba (izquierda, medio, derecha), el separador (izquierda,
# derecha) y abajo (izquierda, medio, derecha). El vertical va el último.
#
# Se guardan como una cadena de nueve caracteres y no como nueve campos porque
# así el catálogo se lee como lo que es —un dibujo— y añadir un marco es escribir
# una línea.

PIEZAS = ("sup_izq", "horizontal", "sup_der", "med_izq", "med_der",
          "inf_izq", "inf_der", "vertical")

REDONDO = "╭─╮├┤╰╯│"     # el de siempre, y el que lleva quien no compra nada

MARCOS = (
    Cosmetico("marco_doble", MARCO, "Doble", "╔═╗╠╣╚╝║"),
    Cosmetico("marco_grueso", MARCO, "Grueso", "┏━┓┣┫┗┛┃"),
    Cosmetico("marco_fino", MARCO, "Fino", "┌─┐├┤└┘│"),
)

# --- Títulos ----------------------------------------------------------------
#
# Una palabra que se cuela en el subtexto de la ficha, entre el nombre de la
# especie y el carácter. Llevan las marcas «{o/a}» de `especies.concordar`
# porque concuerdan con el género del gachamon, como todo lo demás.

TITULOS = (
    Cosmetico("titulo_invicto", TITULO, "El Invicto", "{el/la} Invict{o/a}"),
    Cosmetico("titulo_veloz", TITULO, "El Veloz", "{el/la} Veloz"),
    Cosmetico("titulo_terco", TITULO, "El Terco", "{el/la} Terc{o/a}"),
    Cosmetico("titulo_errante", TITULO, "El Errante", "{el/la} Errante"),
    Cosmetico("titulo_viejo", TITULO, "El Viejo", "{el/la} Viej{o/a}"),
    Cosmetico("titulo_sin_igual", TITULO, "Sin Igual", "sin igual"),
)


CATALOGO: dict[str, Cosmetico] = {
    c.clave: c for c in (*TINTES, *SOMBREROS, *MARCOS, *TITULOS)
}


def del_tipo(tipo: str) -> tuple[Cosmetico, ...]:
    return tuple(c for c in CATALOGO.values() if c.tipo == tipo)


def buscar(clave: str | None) -> Cosmetico | None:
    """El cosmético de esa clave, o nada.

    Devuelve `None` en vez de reventar cuando la clave no existe: una fila vieja
    con un cosmético que se retiró del catálogo tiene que seguir pintando la
    ficha, sin corona pero sin romperse.
    """
    return CATALOGO.get(clave) if clave else None


def color_del_tinte(clave: str | None, por_defecto: str) -> str:
    """El color con el que se pinta al gachamon.

    Va aquí y no repetido en cada vista porque al gachamon lo dibujan tres
    sitios —la ficha, `/jardin` y `/ranking`—, y un tinte que sólo se viera en
    uno se leería como un fallo.
    """
    cosmetico = buscar(clave)
    return cosmetico.valor if cosmetico and cosmetico.tipo == TINTE else por_defecto


def marco_de(clave: str | None) -> str:
    """Las nueve piezas del marco. El redondo si no lleva ninguno."""
    cosmetico = buscar(clave)
    return cosmetico.valor if cosmetico and cosmetico.tipo == MARCO else REDONDO


def texto_del_titulo(clave: str | None, genero: str) -> str:
    """El título ya concordado, o cadena vacía si no lleva."""
    cosmetico = buscar(clave)
    if not cosmetico or cosmetico.tipo != TITULO:
        return ""
    return esp.concordar(cosmetico.valor, genero)


def dibujo_del_sombrero(clave: str | None) -> str:
    cosmetico = buscar(clave)
    return cosmetico.valor if cosmetico and cosmetico.tipo == SOMBRERO else ""


def poner_sombrero(lineas: list[str], sombrero: str) -> list[str]:
    """Añade la fila del sombrero encima del dibujo, sobre su mismo eje.

    Centrar una cosa sobre otra es de donde han salido todos los descuadres de
    este proyecto, y siempre por el mismo motivo: centrar la grande sobre la
    pequeña. Aquí manda el eje del **dibujo**, y si el sombrero es más ancho es
    el dibujo el que se corre, no al revés.

    No comprueba si cabe: eso lo garantiza que ningún dibujo pase de seis filas
    de las siete del marco, y lo vigila un test aparte.
    """
    if not sombrero:
        return lineas
    ancho = max((len(linea) for linea in lineas), default=0)
    if len(sombrero) <= ancho:
        return [" " * ((ancho - len(sombrero)) // 2) + sombrero, *lineas]
    corrimiento = " " * ((len(sombrero) - ancho) // 2)
    return [sombrero, *(corrimiento + linea if linea else "" for linea in lineas)]
