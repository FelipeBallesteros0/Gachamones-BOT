"""Las camas puestas mandan: reclutar pide una cama libre y no hay tope de 25."""
import ast
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import pytest

import db
import departamento as dep
import especies as esp
import identidad
import nacer as nacer_
from ayudas_web import PUEBLO, con_gachamon, en_casa

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
USUARIO_WEB = identidad.de_cuenta_web(1)
# Con tu cama en (0, 0), en un 3 x 3 caben tres más.
SITIOS = ((0, 1, 0), (0, 2, 0), (2, 0, 1))


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "camas.db")
    db.inicializar()


def nacer(nombre, activa=True):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0, activa=activa)


def poner_camas(usuario, cuantas, guild="g1"):
    """Le añade `cuantas` camas sencillas puestas, creando su departamento si falta."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, guild, T0)
        for x, y, giro in SITIOS[:cuantas]:
            db.anadir_mueble_en(con, usuario, guild, "cama_sencilla", x, y, giro)


def guardado(usuario, clave, guild="g1"):
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, guild, T0)
        return db.anadir_mueble_en(con, usuario, guild, clave)


def filas(tabla):
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(f"SELECT * FROM {tabla}")]


def recluta(rng=1):
    return nacer_.unir_recluta(
        "u1", "g1", especie="pulpo", stats=STATS, genero=esp.MACHO,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(rng),
    )


def test_un_recluta_pide_una_cama_libre():
    nacer("Ana")                                   # tú y Ana, con una sola cama puesta: ninguna libre
    with pytest.raises(db.SinCamaLibre):
        recluta()
    poner_camas("u1", 2)                           # ya son tres: la tuya, la de Ana y una libre
    assert recluta().nombre
    with pytest.raises(db.SinCamaLibre):
        recluta(2)


def test_sin_cama_libre_no_nace_nadie_ni_cuenta_como_reclutado():
    nacer("Ana")
    antes = (filas("criaturas"), filas("marcador_persona"))
    with pytest.raises(db.SinCamaLibre):
        recluta()
    assert (filas("criaturas"), filas("marcador_persona")) == antes


def test_sin_cama_libre_es_un_value_error_para_quien_ya_trata_ese_caso():
    assert issubclass(db.SinCamaLibre, ValueError)


def test_las_camas_guardadas_no_cuentan():
    nacer("Ana")
    for _ in range(3):
        guardado("u1", "cama_sencilla")
    assert not db.hay_cama_libre("u1", "g1")


def test_la_cama_libre_es_por_persona_y_por_servidor():
    nacer("Ana")
    poner_camas("u1", 2)
    assert db.hay_cama_libre("u1", "g1")
    assert not db.hay_cama_libre("u1", "g2")       # sin departamento: sólo la tuya
    assert not db.hay_cama_libre("u2", "g1")
    nacer_.unir_recluta(
        "u1", "g1", especie="pulpo", stats=STATS, genero=esp.MACHO,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(1),
    )
    assert not db.hay_cama_libre("u1", "g1")


RAIZ = Path(__file__).resolve().parent.parent
# Lo que no es código del juego: las pruebas, el entorno, lo compilado y lo oculto.
_FUERA_DEL_JUEGO = {"tests", "venv", "__pycache__", "node_modules"}


def _modulos_que_no_son_de_pruebas():
    for carpeta, subcarpetas, archivos in os.walk(RAIZ):
        subcarpetas[:] = sorted(c for c in subcarpetas if c not in _FUERA_DEL_JUEGO and not c.startswith("."))
        yield from (Path(carpeta) / a for a in sorted(archivos) if a.endswith(".py"))


def _llamadas_a_crear(ruta):
    """Cada `db.crear(...)` escrito en ese archivo."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    return [
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "crear" and isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "db"
    ]


def _pide_cama(llamada):
    return any(
        k.arg == "pide_cama" and isinstance(k.value, ast.Constant) and k.value.value is True
        for k in llamada.keywords
    )


def test_todo_gachamon_pide_cama():
    """Ya no hay huevo: nada del juego crea un gachamon sin pedir cama. Todo
    `db.crear(...)` de un módulo que no es de pruebas la pide (`pide_cama=True`);
    `db.crear` no la pide por su cuenta porque es lo que usan las pruebas de
    reglas para crear criaturas a mano.

    Lo que hace cada camino lo fijan sus propias pruebas: que el huevo ya no
    existe, `test_web_nacer.py::test_el_huevo_ya_no_existe`; que sin cama libre
    no hay primero, `test_web_aventura.py::test_sin_la_segunda_cama_no_hay_encuentro`
    y `test_nacer.py::test_el_primero_sale_de_las_diez_del_huevo_y_pide_cama`; y
    que sin cama libre no se une un recluta, `test_un_recluta_pide_una_cama_libre`.
    """
    llamadas = {ruta.relative_to(RAIZ).as_posix(): _llamadas_a_crear(ruta) for ruta in _modulos_que_no_son_de_pruebas()}
    # La búsqueda llega a todas partes menos a las pruebas, y no vuelve vacía: `nacer` crea.
    assert {"nacer.py", "economia.py", "web/aventura.py", "cogs/mudanza.py", "herramientas/pieza.py"} <= set(llamadas)
    assert not any(ruta.startswith(("tests/", "venv/")) for ruta in llamadas)
    assert llamadas["nacer.py"]
    sin_pedirla = [f"{ruta}:{l.lineno}" for ruta, ls in llamadas.items() for l in ls if not _pide_cama(l)]
    assert sin_pedirla == []


def test_ya_no_hay_tope_de_25():
    for i in range(27):
        db.crear("u1", "g1", "pulpo", f"N{i}", STATS, T0, activa=(i == 0))
    assert len(db.plantel("u1", "g1")) == 27 and not hasattr(db, "MAXIMO_PLANTEL")


def test_hay_mas_nombres_que_gachamones_caben():
    assert dep.MAXIMO_DE_GACHAMONES == 31       # y en tests/test_nombres.py, la cuenta de nombres se compara con esto


def test_el_departamento_dice_cuantos_caben_por_las_camas(cliente):
    con_gachamon(cliente); en_casa(cliente)
    d = cliente.get("/gachamon/api/departamento").json()
    # Caben tantos como camas puestas menos la tuya: tu cama y la del primero son dos, y cabe uno.
    assert (d["camas"] - 1, d["gachamones"], d["cabe_otro"]) == (1, 1, False)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        for x, y, giro in SITIOS[1:]:                                        # en (0, 1) está la del primero
            db.anadir_mueble_en(con, USUARIO_WEB, str(PUEBLO), "cama_sencilla", x, y, giro)
    d = cliente.get("/gachamon/api/departamento").json()
    assert (d["camas"] - 1, d["gachamones"], d["cabe_otro"]) == (3, 1, True)  # ya son cuatro puestas
