from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATS = (10, 10, 10, 10)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "devolucion.db")
    db.inicializar()


def con_piezas(usuario: str, *claves: str) -> None:
    with db.conectar() as con:
        for clave in claves:
            db.guardar_en_el_ropero_en(con, usuario, "g", clave)


def vestir(criatura_id: int, **piezas: str) -> None:
    asignaciones = ", ".join(f"{columna} = ?" for columna in piezas)
    with db.conectar() as con:
        con.execute(
            f"UPDATE criaturas SET {asignaciones} WHERE id = ?",
            (*piezas.values(), criatura_id),
        )


def gemas_de(usuario: str) -> int:
    return economia.saldos(usuario, "g").asciigems


def cuantas(tabla: str) -> int:
    with db.conectar() as con:
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_devuelve_veinte_por_tinte_y_cincuenta_por_marco():
    con_piezas("u", "tinte_rojo", "marco_doble", "corona")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (1, 2, 70)
    assert gemas_de("u") == 50 + 70
    assert db.ropero("u", "g") == {"corona"}


def test_cada_persona_recibe_lo_suyo():
    con_piezas("a", "tinte_rojo", "tinte_azul")
    con_piezas("b", "marco_fino")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (2, 3, 90)
    assert (gemas_de("a"), gemas_de("b")) == (90, 100)


def test_repetirla_no_paga_dos_veces():
    con_piezas("u", "tinte_rojo")
    economia.devolver_cosmeticos_retirados(T0)
    segunda = economia.devolver_cosmeticos_retirados(T0 + timedelta(days=1))
    assert (segunda.personas, segunda.piezas, segunda.gemas) == (0, 0, 0)
    assert gemas_de("u") == 70


def test_ni_aunque_la_pieza_reaparezca_en_el_ropero():
    con_piezas("u", "tinte_rojo")
    economia.devolver_cosmeticos_retirados(T0)
    con_piezas("u", "tinte_rojo")   # una base restaurada a medias, por ejemplo
    economia.devolver_cosmeticos_retirados(T0)
    assert gemas_de("u") == 70
    assert db.ropero("u", "g") == frozenset()


def test_se_la_quita_a_quien_la_lleva_y_le_deja_lo_demas():
    viva = db.crear("u", "g", "pollito", "Viva", STATS, T0)
    con_piezas("u", "tinte_rojo", "marco_doble", "corona")
    vestir(viva.id, tinte="tinte_rojo", marco="marco_doble", sombrero="corona")
    economia.devolver_cosmeticos_retirados(T0)
    despues = db.por_id(viva.id)
    assert (despues.tinte, despues.marco, despues.sombrero) == (None, None, "corona")


def test_tambien_se_la_quita_a_un_gachamon_muerto():
    muerta = db.crear("u", "g", "pollito", "Ida", STATS, T0)
    con_piezas("u", "tinte_rojo")
    vestir(muerta.id, tinte="tinte_rojo", muerta_en=T0.isoformat())
    economia.devolver_cosmeticos_retirados(T0)
    assert db.por_id(muerta.id).tinte is None
    assert gemas_de("u") == 70


def test_una_pieza_puesta_que_no_estaba_en_el_ropero_tambien_se_devuelve():
    viva = db.crear("u", "g", "pollito", "Viva", STATS, T0)
    vestir(viva.id, marco="marco_grueso")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert resumen.piezas == 1 and gemas_de("u") == 100
    assert db.por_id(viva.id).marco is None


def test_queda_anotada_y_no_pasa_por_el_libro_de_las_monedas():
    con_piezas("u", "marco_doble")
    economia.devolver_cosmeticos_retirados(T0)
    with db.conectar() as con:
        fila = con.execute("SELECT * FROM devoluciones").fetchone()
    assert (fila["usuario_id"], fila["cosmetico"], fila["gemas"]) == (
        "u", "marco_doble", 50,
    )
    assert fila["devuelta_en"] == T0.isoformat()
    assert cuantas("operaciones_economia") == 0


def test_quien_no_tenia_nada_retirado_no_recibe_nada():
    con_piezas("u", "corona", "titulo_veloz")
    resumen = economia.devolver_cosmeticos_retirados(T0)
    assert (resumen.personas, resumen.piezas, resumen.gemas) == (0, 0, 0)
    assert gemas_de("u") == 50
    assert db.ropero("u", "g") == {"corona", "titulo_veloz"}
    assert cuantas("devoluciones") == 0


def test_dos_arranques_a_la_vez_pagan_una_sola_vez():
    con_piezas("u", "tinte_rojo", "marco_doble")
    with ThreadPoolExecutor(max_workers=2) as hilos:
        resumenes = list(hilos.map(
            lambda _: economia.devolver_cosmeticos_retirados(T0), range(2)
        ))
    assert sorted(r.piezas for r in resumenes) == [0, 2]
    assert gemas_de("u") == 50 + 70
