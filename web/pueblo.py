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


def existe(clave: object) -> bool:
    return isinstance(clave, str) and clave in LUGARES


def de_partida(hogar: str) -> str:
    return "casa" if hogar == casas.PROPIA else "refugio"


def sin_casa(clave: str, hogar: str) -> bool:
    """Está en «Tu casa» sin tener una propia."""
    return clave == "casa" and hogar != casas.PROPIA


def aviso(clave: str, vinculada: bool, hogar: str) -> str | None:
    abre = LUGARES[clave].abre
    if abre == DESPUES:
        if vinculada:
            return "Esto se abre más adelante. Por ahora se juega en Discord."
        return "Esto se abre más adelante."
    if abre == PRONTO:
        return "Aquí todavía no hay nada que hacer. Abre pronto."
    if sin_casa(clave, hogar):
        return "Todavía no tienes casa. Se compran en la tienda."
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
