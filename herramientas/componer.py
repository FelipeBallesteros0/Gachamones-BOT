"""Genera los retratos de `arte/` a partir de los originales de `fuentes/`.

    ./venv/bin/python herramientas/componer.py             # todas las especies
    ./venv/bin/python herramientas/componer.py chispa      # sólo una
    ./venv/bin/python herramientas/componer.py --comprobar # sin escribir nada

`--comprobar` regenera en memoria y compara con lo que hay en `arte/`: si algo
sale distinto es que los originales cambiaron y los retratos están viejos. Es
determinista, así que la comparación es byte a byte y no admite matices.

Por qué los retratos van compuestos de antemano y no al vuelo: la ficha se
reedita a cada botón, y apilar tres capas de 256×256 en Python puro tarda
segundos en la Raspberry. Se paga una vez aquí y no en cada pulsación.

Cómo se llaman los archivos
---------------------------
El cuerpo es `fuentes/cuerpos/<especie>_body_<forma>.png`, donde `<especie>` es
el **nombre** del bicho en minúsculas y sin tildes —«Swampdón» es `swampdon`—,
no su clave interna. Se dibuja mirando la hoja de producción, donde salen los
nombres, así que pedir la clave sería pedir que se acuerde de que Tsushimon es
`dragoncito`. La correspondencia se deduce de `especies.py` y no hay tabla que
mantener: una especie nueva sólo necesita su PNG bien llamado.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unicodedata

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
# Las dos rutas: la raíz para `especies` y `cosmeticos`, y esta carpeta para
# `png`. Explícitas para que valga igual ejecutándolo que importándolo.
sys.path[:0] = [str(RAIZ), str(AQUI)]

import cosmeticos as cos  # noqa: E402
import especies as esp  # noqa: E402
import png  # noqa: E402

FUENTES = RAIZ / "fuentes"
DESTINO = RAIZ / "arte"

SIN = "sin"
CARAS = {esp.FELIZ: "face_1.png", esp.NORMAL: "face_2.png", esp.MAL: "face_3.png"}

# Las formas se llamaron así al dibujarlas y el juego las llama de otra manera.
# Renombrar los 55 originales rompería la costumbre de quien dibuja, y esta es
# la única tabla que queda: la de especies se deduce sola.
FORMA_ARCHIVO: dict[str, str] = dict(zip(
    esp.ETAPAS, ("cria", "niño", "adolecente", "adulto", "adulto_grande")
))

# Un respiro alrededor del dibujo para que no quede pegado al borde del embed.
# Va antes de doblar, así que en la imagen final son cuatro píxeles.
MARGEN = 2


def sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def claves_por_nombre() -> dict[str, str]:
    """«swampdon» -> «swampdon», «tsushimon» -> «dragoncito»."""
    return {sin_tildes(d.nombre): clave for clave, d in esp.ESPECIES.items()}


def caja_con_tinta(imagen: png.Imagen) -> tuple[int, int, int, int]:
    puntos = [(x, y)
              for y in range(imagen.alto) for x in range(imagen.ancho)
              if imagen.pixel(x, y)[3] != 0]
    if not puntos:
        raise ValueError("la imagen está vacía")
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return min(xs), min(ys), max(xs), max(ys)


def unir(a, b):
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def recortar_y_doblar(imagen: png.Imagen, caja) -> png.Imagen:
    """Recorta a la caja —con margen— y amplía al doble por vecino más cercano.

    Duplicar así no inventa ni un color: el arte no tiene bordes suavizados, o
    sea que cada píxel es opaco del todo o transparente del todo, y un cuadrado
    de 2×2 del mismo color es exactamente lo que se quiere ver.
    """
    x0, y0, x1, y1 = caja
    x0 -= MARGEN
    y0 -= MARGEN
    x1 += MARGEN
    y1 += MARGEN
    ancho, alto = x1 - x0 + 1, y1 - y0 + 1

    salida = png.Imagen.vacia(ancho * 2, alto * 2)
    for y in range(alto):
        for x in range(ancho):
            # El margen puede caerse fuera del lienzo si el dibujo llega al
            # borde: ahí no hay píxel que copiar y se queda transparente.
            ox, oy = x0 + x, y0 + y
            if not (0 <= ox < imagen.ancho and 0 <= oy < imagen.alto):
                continue
            pixel = imagen.pixel(ox, oy)
            if pixel[3] == 0:
                continue
            for dy in (0, 1):
                for dx in (0, 1):
                    salida.poner(x * 2 + dx, y * 2 + dy, pixel)
    return salida


def ruta_del_cuerpo(nombre: str, etapa: str) -> pathlib.Path:
    return FUENTES / "cuerpos" / f"{nombre}_body_{FORMA_ARCHIVO[etapa]}.png"


def ruta_de_capa(carpeta: str, nombre: str, archivo: str) -> pathlib.Path:
    especifica = FUENTES / carpeta / nombre / archivo
    return especifica if especifica.is_file() else FUENTES / carpeta / archivo


def retratos(nombre: str):
    """Los 21 retratos de cada forma, ya recortados al mismo encuadre.

    Las 21 combinaciones comparten caja **a propósito**: si cada una se recortara
    a la suya, cambiar de humor o ponerse un sombrero movería al bicho dentro
    del embed y parecería que da saltos.
    """
    caras = {animo: png.leer(ruta_de_capa("caras", nombre, archivo))
             for animo, archivo in CARAS.items()}
    sombreros = {
        s.clave: png.leer(ruta_de_capa("sombreros", nombre, f"{s.clave}.png"))
        for s in cos.SOMBREROS
    }

    for etapa in esp.ETAPAS:
        cuerpo = png.leer(ruta_del_cuerpo(nombre, etapa))
        piezas: dict[tuple[str, str], png.Imagen] = {}
        comun = None
        for animo, cara in caras.items():
            for sombrero in (SIN, *sombreros):
                capas = [cuerpo, cara]
                if sombrero != SIN:
                    capas.append(sombreros[sombrero])
                imagen = png.apilar(capas)
                piezas[(animo, sombrero)] = imagen
                caja = caja_con_tinta(imagen)
                comun = caja if comun is None else unir(comun, caja)
        for (animo, sombrero), imagen in piezas.items():
            yield etapa, animo, sombrero, recortar_y_doblar(imagen, comun)


def nombres_disponibles() -> dict[str, str]:
    """Nombre de archivo -> clave, sólo para lo que tenga sus cinco formas."""
    por_nombre = claves_por_nombre()
    completos = {}
    for nombre, clave in por_nombre.items():
        if all(ruta_del_cuerpo(nombre, e).is_file() for e in esp.ETAPAS):
            completos[nombre] = clave
    return completos


def main() -> int:
    argumentos = sys.argv[1:]
    comprobar = "--comprobar" in argumentos
    pedidas = [a for a in argumentos if not a.startswith("--")]

    disponibles = nombres_disponibles()
    por_clave = {clave: nombre for nombre, clave in disponibles.items()}

    if pedidas:
        desconocidas = [p for p in pedidas if p not in por_clave]
        if desconocidas:
            print(f"no sé dibujar {', '.join(desconocidas)}; "
                  f"hay {', '.join(sorted(por_clave))}")
            return 2
        trabajo = {por_clave[p]: p for p in pedidas}
    else:
        trabajo = disponibles

    distintos = 0
    for nombre, clave in sorted(trabajo.items(), key=lambda kv: kv[1]):
        hechos = 0
        for etapa, animo, sombrero, imagen in retratos(nombre):
            destino = DESTINO / clave / etapa / f"{animo}_{sombrero}.png"
            if comprobar:
                # Fuera de `arte/`, para que comprobar no deje ni un archivo ni
                # una carpeta vacía donde todavía no hay retratos.
                antes = destino.read_bytes() if destino.is_file() else b""
                with tempfile.TemporaryDirectory() as tmp:
                    temporal = pathlib.Path(tmp) / "retrato.png"
                    png.escribir(imagen, temporal)
                    ahora = temporal.read_bytes()
                if antes != ahora:
                    distintos += 1
                    print(f"  DISTINTO {destino.relative_to(RAIZ)}")
            else:
                destino.parent.mkdir(parents=True, exist_ok=True)
                png.escribir(imagen, destino)
            hechos += 1
        print(f"  {clave:12} ({nombre}) {hechos} retratos")

    if comprobar:
        print("todo igual" if not distintos else f"{distintos} retratos distintos")
        return 1 if distintos else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
