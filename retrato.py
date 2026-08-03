"""Qué criaturas tienen retrato dibujado y cuál les toca.

**Esto es una prueba acotada.** Sólo Pyro, sólo en adulto grande y sólo sin
teñir: todo lo demás sigue con el arte ASCII de siempre. El cerrojo vive aquí y
en un solo sitio, así que ampliar o retirar la prueba es tocar este módulo.

No sabe de imágenes ni de Discord: mira una criatura y devuelve una ruta. Los
retratos vienen **ya compuestos** —cuerpo, cara y sombrero apilados de
antemano—, así que a la hora de enseñarlos no hay nada que calcular. Componer al
vuelo pedía o una dependencia nueva o segundos de CPU en la Raspberry, y en una
ficha que se reedita a cada botón eso se nota.

El nombre del archivo es `{animo}_{sombrero}.png`, con las mismas claves que ya
usan `especies` y `cosmeticos`. No hay tabla de equivalencias que mantener: si
mañana se añade un sombrero, el archivo se llama como su clave y ya está.
"""
from __future__ import annotations

from pathlib import Path

import especies as esp
import simulacion as sim

ARTE = Path(__file__).parent / "arte"

# El borde del embed va del color de la especie, que es lo que ata el retrato a
# la ficha. Son los mismos ocho colores del arte ANSI traducidos a RGB; se
# devuelve el número y no un objeto de Discord para no arrastrar la librería a
# un módulo que no la necesita.
COLORES = {
    esp.GRIS: 0x8A8A8A, esp.ROJO: 0xC0392B, esp.VERDE: 0x4CAF50,
    esp.AMARILLO: 0xD9A400, esp.AZUL: 0x3F7FD0, esp.ROSA: 0xD268A8,
    esp.CIAN: 0x3FB6C4, esp.BLANCO: 0xD8D8D8,
}
COLOR_POR_DEFECTO = 0x8A8A8A

# Lo que entra en la prueba: las parejas de especie y etapa que tienen dibujo.
# Se escriben a mano en vez de mirar qué carpetas hay porque es el cerrojo de
# que esto siga acotado; una carpeta a medio llenar dejaría fichas sin imagen.
CON_RETRATO = frozenset({
    ("chispa", "adulto_grande"),        # Pyro
    ("pedrusco", "adulto"),             # Geo
    ("pedrusco", "adulto_grande"),
    ("pollito", "adulto_grande"),       # Piollito
    ("slime", "adulto"),                # Gelatín
    ("slime", "adulto_grande"),
})

SIN_SOMBRERO = "sin"


def ruta_de(criatura: sim.Criatura) -> Path | None:
    """El retrato de esta criatura, o `None` si le toca seguir en ASCII.

    Devuelve `None` para las criaturas **teñidas** a propósito. El tinte se
    resolverá dibujando una imagen por color, y hasta entonces enseñar el
    retrato sin teñir sería peor que no enseñarlo: alguien pagó por tener su
    Pyro azul y lo vería rojo.
    """
    if (criatura.especie, criatura.etapa) not in CON_RETRATO or criatura.tinte:
        return None

    sombrero = criatura.sombrero or SIN_SOMBRERO
    ruta = (ARTE / criatura.especie / criatura.etapa
            / f"{criatura.animo_visual}_{sombrero}.png")
    # Un sombrero sin dibujo no puede dejar la ficha sin imagen a medias: es
    # preferible caer al arte ASCII, que siempre está.
    return ruta if ruta.is_file() else None


def nombre_del_adjunto(ruta: Path) -> str:
    """Cómo se llama el fichero al subirlo.

    Discord ata la miniatura de un embed a un adjunto por su nombre, con
    `attachment://<nombre>`. Que los dos salgan de aquí es lo que evita el fallo
    clásico: si no coinciden, la miniatura sale vacía y no hay error en ninguna
    parte.
    """
    return ruta.name


def color_de(criatura: sim.Criatura) -> int:
    """El color del borde de la ficha: el de su especie.

    No mira el tinte porque una criatura teñida no llega hasta aquí: `ruta_de`
    la devuelve a ASCII antes.
    """
    return COLORES.get(criatura.def_especie.color, COLOR_POR_DEFECTO)
