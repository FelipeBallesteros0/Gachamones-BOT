import pytest

import cosmeticos as cos
import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, T0, alta, con_gachamon, poner_reloj

ROPERO = "/gachamon/api/ropero"
PONER, QUITAR = f"{ROPERO}/poner", f"{ROPERO}/quitar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)
STATS = (10, 10, 10, 10)
TITULO = cos.del_tipo(cos.TITULO)[0]


def activa():
    return db.criatura_activa(YO, G)


def dar(*claves):
    with db.conectar() as con:
        for clave in claves:
            db.guardar_en_el_ropero_en(con, YO, G, clave)


def poner_a(criatura_id, clave, tipo):
    with db.conectar() as con:
        con.execute(f"UPDATE criaturas SET {tipo} = ? WHERE id = ?", (clave, criatura_id))


def con_nube():
    """Pelusa activa y Nube en la incubadora."""
    return db.crear(YO, G, "pulpo", "Nube", STATS, T0, activa=False)


def poner(cliente, clave, gachamon_id=None, **mas):
    cuerpo = {"clave": clave, "gachamon_id": activa().id if gachamon_id is None else gachamon_id}
    return cliente.post(PONER, json={**cuerpo, **mas}, headers=ESCRIBIR)


def quitar(cliente, tipo, gachamon_id=None):
    cuerpo = {"tipo": tipo, "gachamon_id": activa().id if gachamon_id is None else gachamon_id}
    return cliente.post(QUITAR, json=cuerpo, headers=ESCRIBIR)


def puestos():
    with db.conectar() as con:
        return [tuple(f) for f in con.execute("SELECT nombre, sombrero, titulo FROM criaturas ORDER BY id")]


def test_el_ropero_ensena_lo_que_tienes_y_quien_lo_lleva(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    nube = con_nube()
    dar("laurel", "chistera", "corona", TITULO.clave, "marco_doble")
    poner_a(activa().id, "corona", "sombrero")
    poner_a(nube.id, TITULO.clave, "titulo")
    cuerpo = cliente.get(ROPERO).json()
    assert cuerpo["gachamon"] == {"id": activa().id, "nombre": "Pelusa"}
    # En el orden del catálogo; "marco_doble" está retirado y no sale.
    assert cuerpo["piezas"] == [
        {"clave": "corona", "nombre": "Corona", "tipo": "sombrero", "puesta": True, "lo_lleva": None},
        {"clave": "chistera", "nombre": "Chistera", "tipo": "sombrero", "puesta": False, "lo_lleva": None},
        {"clave": "laurel", "nombre": "Laurel", "tipo": "sombrero", "puesta": False, "lo_lleva": None},
        {"clave": TITULO.clave, "nombre": TITULO.nombre, "tipo": "titulo", "puesta": False, "lo_lleva": "Nube"},
    ]
    assert set(cuerpo["saldos"]) == {"monedas", "gemas"}


def test_poner_un_sombrero(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar("corona")
    hecho = poner(cliente, "corona")
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert cuerpo["ok"] is True and cuerpo["clave"] is None
    assert cuerpo["mensaje"] == "Pelusa ya lleva Corona."
    assert "corona" in cuerpo["estado"]["gachamon"]["retrato"]
    assert cuerpo["ropero"]["piezas"][0]["puesta"] is True
    assert puestos() == [("Pelusa", "corona", None)]


def test_poner_un_titulo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(TITULO.clave)
    cuerpo = poner(cliente, TITULO.clave).json()
    titulo = cos.texto_del_titulo(TITULO.clave, activa().genero)
    assert cuerpo["ok"] is True and cuerpo["mensaje"] == f"Ahora es Pelusa {titulo}."
    assert puestos() == [("Pelusa", None, TITULO.clave)]


def test_poner_en_lugar_de_otro(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar("corona", "chistera")
    poner_a(activa().id, "corona", "sombrero")
    cuerpo = poner(cliente, "chistera").json()
    assert cuerpo["ok"] is True
    assert cuerpo["mensaje"] == "Pelusa ya lleva Chistera. Corona vuelve a tu ropero."
    assert puestos() == [("Pelusa", "chistera", None)]


def test_poner_lo_que_ya_lleva_es_un_si(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar("corona")
    poner_a(activa().id, "corona", "sombrero")
    hecho = poner(cliente, "corona")
    assert hecho.status_code == 200
    assert hecho.json()["ok"] is True and hecho.json()["mensaje"] == "Pelusa ya lleva Corona."
    assert puestos() == [("Pelusa", "corona", None)]


def test_quitar_sin_nada_es_un_si(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    sombrero = quitar(cliente, "sombrero").json()
    titulo = quitar(cliente, "titulo").json()
    assert (sombrero["ok"], sombrero["mensaje"]) == (True, "Pelusa no lleva ningún sombrero.")
    assert (titulo["ok"], titulo["mensaje"]) == (True, "Pelusa no lleva ningún título.")


def test_quitar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar("corona")
    poner_a(activa().id, "corona", "sombrero")
    cuerpo = quitar(cliente, "sombrero").json()
    assert cuerpo["ok"] is True and cuerpo["mensaje"] == "Pelusa ya no lleva Corona. Está en tu ropero."
    assert puestos() == [("Pelusa", None, None)]
    assert cuerpo["ropero"]["piezas"][0] == {
        "clave": "corona", "nombre": "Corona", "tipo": "sombrero", "puesta": False, "lo_lleva": None,
    }
    assert "corona" not in cuerpo["estado"]["gachamon"]["retrato"]


def test_lo_que_lleva_otro(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    nube = con_nube()
    dar("corona")
    poner_a(nube.id, "corona", "sombrero")
    hecho = poner(cliente, "corona")
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert (cuerpo["ok"], cuerpo["clave"]) == (False, "lo_lleva_otro")
    assert cuerpo["mensaje"] == "Corona: lo lleva Nube. Quítaselo primero."
    assert puestos() == [("Pelusa", None, None), ("Nube", "corona", None)]


def test_lo_que_ya_no_tienes(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    hecho = poner(cliente, "laurel")
    assert hecho.status_code == 200
    cuerpo = hecho.json()
    assert (cuerpo["ok"], cuerpo["clave"], cuerpo["mensaje"]) == (False, "no_lo_tienes", "Ya no tienes Laurel.")
    assert puestos() == [("Pelusa", None, None)]


def test_si_la_pantalla_ensena_otro_gachamon_es_un_409_y_no_cambia_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    nube = con_nube()
    dar("corona", "chistera")
    poner_a(activa().id, "chistera", "sombrero")
    antes = puestos()
    for hecho in (poner(cliente, "corona", gachamon_id=nube.id), quitar(cliente, "sombrero", gachamon_id=nube.id)):
        assert hecho.status_code == 409
        assert hecho.json()["detail"] == {
            "clave": "sin_gachamon", "mensaje": "Tu gachamon ya no es el mismo. Mira otra vez.",
        }
    assert puestos() == antes


def test_peticiones_mal_hechas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar("corona")
    yo = activa().id
    malas = [
        (PONER, {"clave": "corona"}),
        (PONER, {"clave": "corona", "gachamon_id": str(yo)}),
        (PONER, {"clave": "corona", "gachamon_id": None}),
        (PONER, {"clave": "corona", "gachamon_id": True}),
        (PONER, {"clave": "sombrero_que_no_existe", "gachamon_id": yo}),
        (PONER, {"clave": "marco_doble", "gachamon_id": yo}),
        (PONER, {"clave": 3, "gachamon_id": yo}),
        (QUITAR, {"tipo": "sombrero"}),
        (QUITAR, {"tipo": "sombrero", "gachamon_id": str(yo)}),
        (QUITAR, {"tipo": "marco", "gachamon_id": yo}),
        (QUITAR, {"tipo": "zapatos", "gachamon_id": yo}),
        (QUITAR, {"tipo": None, "gachamon_id": yo}),
    ]
    for ruta, cuerpo in malas:
        hecho = cliente.post(ruta, json=cuerpo, headers=ESCRIBIR)
        assert hecho.status_code == 422, (ruta, cuerpo)
        assert hecho.json()["detail"]["clave"] == "peticion", (ruta, cuerpo)
    assert cliente.post(PONER, json={"clave": "corona", "gachamon_id": yo}).status_code == 403
    assert cliente.post(QUITAR, json={"tipo": "sombrero", "gachamon_id": yo}).status_code == 403
    assert puestos() == [("Pelusa", None, None)]


def test_un_gachamon_id_fuera_de_rango_es_un_422_y_no_cambia_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    con_nube()
    dar("corona", "chistera")
    poner_a(activa().id, "chistera", "sombrero")
    antes = puestos()
    for gachamon_id in (2**70, 2**63, 0, -1):
        for hecho in (poner(cliente, "corona", gachamon_id=gachamon_id),
                      quitar(cliente, "sombrero", gachamon_id=gachamon_id)):
            assert hecho.status_code == 422, gachamon_id
            assert hecho.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert puestos() == antes


def test_sin_gachamon_o_sin_sesion(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    assert cliente.get(ROPERO).status_code == 401
    alta(cliente)
    hecho = cliente.get(ROPERO)
    assert hecho.status_code == 409 and hecho.json()["detail"]["clave"] == "sin_gachamon"
    hecho = cliente.post(PONER, json={"clave": "corona", "gachamon_id": 1}, headers=ESCRIBIR)
    assert hecho.status_code == 409 and hecho.json()["detail"]["clave"] == "sin_gachamon"
