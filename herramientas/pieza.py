"""Reduce los originales de la pieza del departamento a lo que sirve la página.

Se corre con `./venv/bin/python -m herramientas.pieza`. El dibujante deja sus
originales en `fuentes/pieza/…` (el doble de lo servido, con el mismo nombre que
dice `docs/arte/contrato.md`) y esta herramienta escribe la copia reducida en
`web/static/arte/pieza/…`. Un original que no mide lo que dice el contrato se
avisa y no se escribe nada.
"""

from pathlib import Path

from PIL import Image

from web import arte

FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
SERVIDO = arte.RAIZ


def reducida(ruta: Path) -> Image.Image:
    """El original abierto, en RGBA, reducido a la mitad con `LANCZOS`: lo que se guarda."""
    with Image.open(ruta) as abierta:
        imagen = abierta.convert("RGBA")
    return imagen.resize((imagen.width // arte.REDUCCION, imagen.height // arte.REDUCCION), Image.LANCZOS)


def reducir() -> list[str]:
    """Escribe la copia reducida de cada original que exista y devuelve las rutas escritas.

    Primero comprueba todos: si uno no mide lo que dice el contrato, no escribe ninguno.
    """
    presentes = []
    for esperado in arte.originales_de_la_pieza():
        origen = FUENTES / esperado.ruta
        if not origen.exists():
            continue
        with Image.open(origen) as imagen:
            tamano = imagen.size
        if tamano != (esperado.ancho, esperado.alto):
            raise ValueError(f"{esperado.ruta} mide {tamano[0]} × {tamano[1]} y el contrato pide "
                             f"{esperado.ancho} × {esperado.alto}")
        presentes.append(esperado.ruta)
    for ruta in presentes:
        destino = SERVIDO / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        reducida(FUENTES / ruta).save(destino, "PNG", optimize=True)
    return presentes


if __name__ == "__main__":
    for escrita in reducir():
        print(escrita)
