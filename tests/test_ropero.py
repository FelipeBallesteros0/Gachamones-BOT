"""Poner y quitar cosméticos dicen por qué no, y a qué gachamon se aplican."""
from datetime import datetime, timezone

import pytest

import cosmeticos as cos
import db
import economia

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
STATS = (10, 10, 10, 10)
CORONA = cos.CATALOGO["corona"]
CHISTERA = cos.CATALOGO["chistera"]
TITULO = cos.del_tipo(cos.TITULO)[0]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "ropero.db")
    db.inicializar()


def dar(*piezas):
    with db.conectar() as con:
        for pieza in piezas:
            db.guardar_en_el_ropero_en(con, U, G, pieza.clave)


def dos_gachamones():
    """Pelusa activa y Nube en la incubadora."""
    pelusa = db.crear(U, G, "pulpo", "Pelusa", STATS, T0)
    nube = db.crear(U, G, "pulpo", "Nube", STATS, T0, activa=False)
    return pelusa, nube


def puestos():
    with db.conectar() as con:
        return [
            (f["nombre"], f["sombrero"], f["titulo"])
            for f in con.execute(
                "SELECT nombre, sombrero, titulo FROM criaturas ORDER BY id"
            )
        ]


def poner_a(criatura, pieza):
    with db.conectar() as con:
        con.execute(
            f"UPDATE criaturas SET {pieza.tipo} = ? WHERE id = ?",
            (pieza.clave, criatura.id),
        )


def test_cada_rechazo_de_poner_dice_su_motivo(base):
    pelusa, nube = dos_gachamones()
    dar(CORONA, CHISTERA)
    poner_a(pelusa, CORONA)
    poner_a(nube, CHISTERA)
    antes = puestos()

    ya = economia.equipar_cosmetico(U, G, CORONA)
    assert (ya.ok, ya.motivo) == (False, "ya_lo_lleva")

    otro = economia.equipar_cosmetico(U, G, CHISTERA)
    assert (otro.ok, otro.motivo, otro.lo_lleva) == (False, "lo_lleva_otro", "Nube")

    sin = economia.equipar_cosmetico(U, G, cos.CATALOGO["laurel"])
    assert (sin.ok, sin.motivo) == (False, "no_lo_tienes")

    assert puestos() == antes

    economia.equipar_cosmetico("otra", G, CORONA)
    nadie = economia.equipar_cosmetico("otra", G, CORONA)
    assert (nadie.ok, nadie.motivo) == (False, "sin_gachamon")


def test_quitar_sin_nada_puesto_dice_no_lleva_nada(base):
    dos_gachamones()
    r = economia.quitar_cosmetico(U, G, cos.SOMBRERO)
    assert (r.ok, r.motivo) == (False, "no_lleva_nada")
    r = economia.quitar_cosmetico("otra", G, cos.SOMBRERO)
    assert (r.ok, r.motivo) == (False, "sin_gachamon")


def test_con_otro_criatura_id_no_se_viste_ni_se_desviste(base):
    pelusa, nube = dos_gachamones()
    dar(CORONA, CHISTERA)
    poner_a(pelusa, CORONA)
    poner_a(nube, TITULO)
    antes = puestos()

    r = economia.equipar_cosmetico(U, G, CHISTERA, criatura_id=nube.id)
    assert (r.ok, r.motivo) == (False, "sin_gachamon")
    r = economia.quitar_cosmetico(U, G, cos.TITULO, criatura_id=nube.id)
    assert (r.ok, r.motivo) == (False, "sin_gachamon")
    assert puestos() == antes


def test_con_el_criatura_id_del_activo_se_viste_como_siempre(base):
    pelusa, _ = dos_gachamones()
    dar(CORONA)
    r = economia.equipar_cosmetico(U, G, CORONA, criatura_id=pelusa.id)
    assert r.ok and r.motivo is None and r.criatura.sombrero == "corona"
    r = economia.quitar_cosmetico(U, G, cos.SOMBRERO, criatura_id=pelusa.id)
    assert r.ok and r.criatura.sombrero is None


def test_las_frases_de_discord_no_cambian(base):
    pelusa, nube = dos_gachamones()
    dar(CORONA, CHISTERA)
    poner_a(pelusa, CHISTERA)
    poner_a(nube, CORONA)
    assert economia.equipar_cosmetico(U, G, CHISTERA).problema == (
        "Pelusa ya lo lleva puesto."
    )
    assert economia.equipar_cosmetico(U, G, CORONA).problema == (
        "**Corona** lo lleva **Nube**. Quítaselo primero."
    )
    assert economia.equipar_cosmetico(U, G, cos.CATALOGO["laurel"]).problema == (
        "No tienes **Laurel** en tu ropero."
    )
    assert economia.equipar_cosmetico(
        U, G, CORONA, criatura_id=nube.id
    ).problema == "No tienes ningún gachamon activo."
    assert economia.equipar_cosmetico("otra", G, CORONA).problema == (
        "No tienes ningún gachamon activo."
    )
    assert economia.quitar_cosmetico(U, G, cos.TITULO).problema == (
        "Pelusa no lleva nada de eso."
    )


def test_quien_lleva_cada(base):
    pelusa, nube = dos_gachamones()
    dar(CORONA, TITULO)
    poner_a(pelusa, CORONA)
    poner_a(nube, TITULO)
    assert db.quien_lleva_cada(U, G) == {"corona": "Pelusa", TITULO.clave: "Nube"}
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ? WHERE id = ?",
            (T0.isoformat(), nube.id),
        )
    assert db.quien_lleva_cada(U, G) == {"corona": "Pelusa"}
