import pytest

import casas
import db
import economia
from ayudas_web import AVATAR, ESCRIBIR, PUEBLO, con_gachamon, entrar, poner_reloj

ESTADO, LUGAR = "/gachamon/api/estado", "/gachamon/api/lugar"
LA_DE_DISCORD = "222222222222222222"
A_LA_INTEMPERIE_CON_CASA = (
    "Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. "
    "Puedes mudarlo a tu casa, por ahora desde Discord, o comprar una más grande en la tienda."
)
A_LA_INTEMPERIE_SIN_CASA = (
    "Se acabó tu estancia en el refugio y tu gachamon vive a la intemperie. Las casas se compran en la tienda."
)


def ir(cliente, lugar):
    return cliente.post(LUGAR, json={"lugar": lugar}, headers=ESCRIBIR)


def vinculada_con_gachamon(cliente) -> None:
    """La cuenta 1, ligada a una identidad de Discord sintética, con su gachamon; la estancia ya empezó."""
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, LA_DE_DISCORD, str(PUEBLO), db.ahora_utc()) == "ok"
    assert cliente.put("/gachamon/api/avatar", json=AVATAR, headers=ESCRIBIR).status_code == 200
    assert cliente.post("/gachamon/api/huevo", headers=ESCRIBIR).status_code == 201
    assert cliente.post("/gachamon/api/bautizar", json={"nombre": "Pelusa"}, headers=ESCRIBIR).status_code == 200
    cuenta = db.cuenta_web(1)
    db.hogar_de(cuenta.usuario_id, cuenta.guild_id, db.ahora_utc())   # empieza la estancia


def comprar_una_casa(reloj) -> None:
    cuenta = db.cuenta_web(1)
    with db.conectar() as con:
        economia._asegurar_monedero(con, cuenta.usuario_id, cuenta.guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = 9000 WHERE usuario_id = ? AND guild_id = ?",
            (cuenta.usuario_id, cuenta.guild_id),
        )
    assert economia.comprar_casa(cuenta.usuario_id, cuenta.guild_id, casas.CATALOGO["grande"], reloj()).ok


def test_en_el_refugio_se_ve_quien_vive_ahi(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    estado = con_gachamon(cliente)
    refugio = cliente.get(ESTADO).json()["lugar"]["refugio"]
    assert refugio["estancia"] == "Tu estancia aquí no tiene plazo."
    assert refugio["viven"] == [{
        "id": estado["gachamon"]["id"], "nombre": "Pelusa",
        "nombre_especie": estado["gachamon"]["nombre_especie"], "retrato": estado["gachamon"]["retrato"],
    }]


def test_con_casa_y_el_gachamon_dentro_no_vive_nadie_aqui(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    comprar_una_casa(reloj)
    assert ir(cliente, "refugio").json()["lugar"]["refugio"]["viven"] == []


@pytest.mark.parametrize("pasa, frase", [
    ({"hours": 22}, "Tu estancia en el refugio dura 6 días más."),
    ({"days": 6}, "Tu estancia en el refugio dura 1 día más."),
    ({"days": 6, "hours": 18, "minutes": 50}, "Tu estancia en el refugio se acaba en 6 horas."),
    ({"days": 6, "hours": 23}, "Tu estancia en el refugio se acaba en 1 hora."),
    ({"days": 6, "hours": 23, "minutes": 20}, "Tu estancia en el refugio se acaba en menos de una hora."),
    ({"days": casas.DIAS_DE_REFUGIO, "seconds": 1}, None),
])
def test_las_frases_de_la_estancia(cliente, monkeypatch, pasa, frase):
    reloj = poner_reloj(monkeypatch)
    vinculada_con_gachamon(cliente)
    reloj.pasar(**pasa)
    assert cliente.get(ESTADO).json()["lugar"]["refugio"]["estancia"] == frase


def test_fuera_del_refugio_no_viene(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert "refugio" not in ir(cliente, "tienda").json()["lugar"]


def test_a_la_intemperie_con_casa_lo_dice(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    vinculada_con_gachamon(cliente)
    comprar_una_casa(reloj)
    cuenta = db.cuenta_web(1)
    with db.conectar() as con:   # su gachamon sale de la casa y la estancia se vence
        con.execute("UPDATE criaturas SET casa_id = NULL WHERE usuario_id = ?", (cuenta.usuario_id,))
    reloj.pasar(days=casas.DIAS_DE_REFUGIO, seconds=1)
    estado = ir(cliente, "refugio").json()
    assert estado["hogar"] == "intemperie"
    assert estado["lugar"]["aviso"] == A_LA_INTEMPERIE_CON_CASA
    assert estado["lugar"]["refugio"]["estancia"] is None


def test_a_la_intemperie_sin_casa_dice_la_de_siempre(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    vinculada_con_gachamon(cliente)
    reloj.pasar(days=casas.DIAS_DE_REFUGIO, seconds=1)
    assert cliente.get(ESTADO).json()["lugar"]["aviso"] == A_LA_INTEMPERIE_SIN_CASA


def test_a_la_intemperie_no_vive_nadie_en_el_refugio(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    vinculada_con_gachamon(cliente)
    reloj.pasar(days=casas.DIAS_DE_REFUGIO, seconds=1)
    refugio = cliente.get(ESTADO).json()["lugar"]["refugio"]
    assert refugio == {"viven": [], "estancia": None}


def test_un_recluta_sin_nombre_se_llama_como_en_la_incubadora(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    cuenta = db.cuenta_web(1)
    recluta = db.crear(cuenta.usuario_id, cuenta.guild_id, "pollito", "", (10, 10, 10, 10), db.ahora_utc(), activa=False)
    viven = cliente.get(ESTADO).json()["lugar"]["refugio"]["viven"]
    assert {v["id"]: v["nombre"] for v in viven} == {viven[0]["id"]: "Pelusa", recluta.id: "Sin nombre"}
