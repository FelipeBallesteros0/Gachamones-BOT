"""Los datos del pueblo: qué lugares hay, de dónde se parte y qué avisa cada pantalla.

Sólo biblioteca estándar y `casas`: lo importan pruebas de módulos puros.
El archivo se lee una vez al importar; no se valida aquí (lo vigila la prueba).
"""

import json
from dataclasses import dataclass
from pathlib import Path

import casas

RUTA = Path(__file__).parent / "static" / "datos" / "pueblo.json"
DATOS: dict = json.loads(RUTA.read_text(encoding="utf-8"))

YA = "ya"
PRONTO = "pronto"
DESPUES = "despues"
_ABRE = (YA, PRONTO, DESPUES)
_PARTES = ("A", "B")


@dataclass(frozen=True)
class Lugar:
    clave: str
    nombre: str
    parte: str
    abre: str


LUGARES: dict[str, Lugar] = {
    clave: Lugar(clave, d["nombre"], d["parte"], d["abre"]) for clave, d in DATOS["lugares"].items()
}


# Lo que se puede hacer en cada lugar, por nombre. Sólo cuenta si el lugar ya abrió.
OFRECE: dict[str, tuple[str, ...]] = {"tienda": ("tienda",), "incubadora": ("incubadora",)}


def ofrece(clave: str) -> tuple[str, ...]:
    """Lo que se puede hacer en ese lugar; vacío si no abre `ya` o no ofrece nada."""
    lugar = LUGARES.get(clave)
    if lugar is None or lugar.abre != YA:
        return ()
    return OFRECE.get(clave, ())


def existe(clave: object) -> bool:
    return isinstance(clave, str) and clave in LUGARES


def de_partida(hogar: str) -> str:
    return "casa" if hogar == casas.PROPIA else "refugio"


def sin_casa(clave: str, hogar: str) -> bool:
    """Está en «Tu casa» sin tener una propia.

    `hogar` es la situación de la persona (`Hogar.estado`), no la de su
    gachamon: quien tiene casa la tiene aunque su gachamon viva en el refugio.
    """
    return clave == "casa" and hogar != casas.PROPIA


def a_la_intemperie(clave: str, hogar_del_gachamon: str) -> bool:
    """Está en el Refugio, pero su gachamon ya no vive en él: se le acabó la estancia.

    `hogar_del_gachamon` es la situación del gachamon activo (`Hogar.estado_de`),
    no la de la persona.
    """
    return clave == "refugio" and hogar_del_gachamon == casas.INTEMPERIE


def aviso(clave: str, vinculada: bool, hogar: str, hogar_del_gachamon: str | None) -> str | None:
    """Lo que la pantalla del lugar avisa, o `None` si no hay nada que avisar.

    `hogar` es la situación de la persona (`Hogar.estado`), como en `sin_casa`;
    `hogar_del_gachamon`, la de su gachamon activo, como en `a_la_intemperie`,
    o `None` si no lo tiene: sin gachamon no hay a quién avisarle que vive a la
    intemperie.
    """
    abre = LUGARES[clave].abre
    if abre == DESPUES:
        if vinculada:
            return "Esto se abre más adelante. Por ahora se juega en Discord."
        return "Esto se abre más adelante."
    if abre == PRONTO:
        return "Aquí todavía no hay nada que hacer. Abre pronto."
    if sin_casa(clave, hogar):
        return "Todavía no tienes casa. Se compran en la tienda."
    if hogar_del_gachamon is not None and a_la_intemperie(clave, hogar_del_gachamon):
        if hogar == casas.PROPIA:
            return (
                "Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. "
                "Puedes mudarlo a tu casa, por ahora desde Discord, o comprar una más grande en la tienda."
            )
        return (
            "Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. "
            "Las casas se compran en la tienda."
        )
    return None


def _numero_positivo(valor: object) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor > 0


def problemas(datos: dict) -> list[str]:
    """Lo que está mal en unos datos de pueblo, en frases; vacía si todo está bien."""
    malos: list[str] = []
    for clave in ("ancho", "alto", "velocidad", "hueco"):
        if not _numero_positivo(datos.get(clave)):
            malos.append(f"«{clave}» tiene que ser un número positivo.")
    lugares = datos.get("lugares")
    nodos = datos.get("nodos")
    aristas = datos.get("aristas")
    if not isinstance(lugares, dict) or not lugares:
        malos.append("Faltan los lugares.")
        lugares = {}
    if not isinstance(nodos, dict) or not nodos:
        malos.append("Faltan los nodos.")
        nodos = {}
    if not isinstance(aristas, list):
        malos.append("Faltan los caminos.")
        aristas = []

    for clave, lugar in lugares.items():
        if not isinstance(lugar, dict):
            malos.append(f"El lugar «{clave}» está mal escrito.")
            continue
        if lugar.get("abre") not in _ABRE:
            malos.append(f"El lugar «{clave}» abre «{lugar.get('abre')}», que no es válido.")
        if lugar.get("parte") not in _PARTES:
            malos.append(f"El lugar «{clave}» es de la parte «{lugar.get('parte')}», que no es válida.")
        hacia = lugar.get("hacia")
        if not (isinstance(hacia, str) and hacia.strip()):
            malos.append(f"El lugar «{clave}» no dice cómo se va hacia él («hacia»).")
        if clave not in nodos:
            malos.append(f"El lugar «{clave}» no tiene nodo.")

    ancho, alto = datos.get("ancho"), datos.get("alto")
    for clave, punto in nodos.items():
        if not (isinstance(punto, (list, tuple)) and len(punto) == 2
                and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in punto)):
            malos.append(f"El nodo «{clave}» no tiene coordenadas válidas.")
        elif _numero_positivo(ancho) and _numero_positivo(alto) and not (
            0 <= punto[0] <= ancho and 0 <= punto[1] <= alto
        ):
            malos.append(f"El nodo «{clave}» cae fuera del pueblo.")

    vecinos: dict[str, set[str]] = {}
    for arista in aristas:
        if not (isinstance(arista, (list, tuple)) and len(arista) == 2):
            malos.append(f"El camino {arista!r} está mal escrito.")
            continue
        a, b = arista
        faltan = [n for n in (a, b) if not isinstance(n, str) or n not in nodos]
        for n in faltan:
            malos.append(f"Un camino nombra el nodo «{n}», que no existe.")
        if not faltan:
            vecinos.setdefault(a, set()).add(b)
            vecinos.setdefault(b, set()).add(a)

    existentes = [c for c in lugares if c in nodos]
    if existentes:
        vistos = {existentes[0]}
        pendientes = [existentes[0]]
        while pendientes:
            for v in vecinos.get(pendientes.pop(), ()):
                if v not in vistos:
                    vistos.add(v)
                    pendientes.append(v)
        for clave in existentes:
            if clave not in vistos:
                malos.append(f"No se puede llegar al lugar «{clave}» por los caminos.")
    return malos
