from datetime import timedelta

import pytest

import db
import economia
import especies as esp
import identidad
from ayudas_web import CABECERA, PUEBLO, STATS, alta, con_carta, con_gachamon, entrar, poner_reloj
from test_web_tienda import LA_DE_DISCORD, con_vinculo
from web import carta

API = "/gachamon/api"

TODO = {"ancho": 4, "fondo": 3, "camas": 3, "vivos": 2, "casas": ["mediana", "grande"], "monedas_por_casas": 1700, "muebles": 2,
        "cosecha": {"poroto_rojo": 3}, "tickets": 1, "monedas_por_tickets": 40, "regalos": 1, "gemas_por_medallas": 70,
        "nombres": [{"especie": "pulpo", "nombre": "Brisa"}], "placas": 1}
MEDALLAS = "Tenías medallas ganadas y sin cobrar: te pagué 70 gemas."
UNA_PLACA = "Te dejé una placa con nombre en tu mochila, por si le quieres cambiar el nombre."


def test_la_carta_dice_todo_lo_que_toco_en_su_orden():
    assert carta.lineas_de(TODO) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 4 × 3 casillas, y lo puedes ampliar.",
        "Te dejé puestas 3 camas: una para ti y una para cada gachamon.",
        "Te devolví lo que costaron tus casas: 1700 monedas.",
        "Tus 2 muebles están en guardados: entra a «Construir» y ponlos donde quieras.",
        "Coseché lo que tenías plantado y lo dejé en tu mochila. El huerto vuelve más adelante.",
        "El refugio cerró. Te devolví 40 monedas por tu ticket.",
        "Lo que te esperaba en el buzón ya está en tu mochila.",
        "Tenías medallas ganadas y sin cobrar: te pagué 70 gemas.",
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo.",
        UNA_PLACA,
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]


def test_a_quien_no_le_toco_nada_la_carta_le_dice_lo_justo():
    nada = {**TODO, "ancho": 3, "camas": 1, "vivos": 0, "casas": [], "monedas_por_casas": 0, "muebles": 0, "cosecha": {}, "tickets": 0, "monedas_por_tickets": 0, "regalos": 0,
            "gemas_por_medallas": 0, "nombres": [], "placas": 0}
    assert carta.lineas_de(nada) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 3 × 3 casillas, y lo puedes ampliar.",
        "Te dejé tu cama puesta y otra guardada: ponla y ve a «Aventura», que ahí te espera un gachamon.",
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]


def test_una_casa_y_un_mueble_van_en_singular():
    lineas = carta.lineas_de({**TODO, "casas": ["pequena"], "monedas_por_casas": 200, "muebles": 1})
    assert "Te devolví lo que costó tu casa: 200 monedas." in lineas and "Tu mueble está en guardados: entra a «Construir» y ponlo donde quieras." in lineas


def test_con_tres_muebles_la_carta_nombra_el_boton():
    lineas = carta.lineas_de({**TODO, "muebles": 3})
    assert "Tus 3 muebles están en guardados: entra a «Construir» y ponlos donde quieras." in lineas


def test_una_moneda_va_en_singular():
    lineas = carta.lineas_de({**TODO, "tickets": 1, "monedas_por_tickets": 1})
    assert "El refugio cerró. Te devolví 1 moneda por tu ticket." in lineas


def test_un_recluta_de_una_especie_que_ya_no_existe_no_lleva_linea():
    lineas = carta.lineas_de({**TODO, "nombres": [{"especie": "ya_no_existe", "nombre": "Nube"}, {"especie": "pulpo", "nombre": "Brisa"}]})
    assert [l for l in lineas if "ahora se llama" in l] == [
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo."
    ]


def test_varios_reclutas_llevan_una_linea_cada_uno_en_su_orden():
    nombres = [{"especie": "pulpo", "nombre": "Brisa"}, {"especie": "ya_no_existe", "nombre": "Nube"},
               {"especie": "pollito", "nombre": "Copo"}, {"especie": "michi", "nombre": "Ámbar"}]
    lineas = carta.lineas_de({**TODO, "nombres": nombres})
    assert [l for l in lineas if "ahora se llama" in l] == [
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo.",
        "Tu Piollito ahora se llama Copo. Se puso el nombre solo.",
        "Tu Purreon ahora se llama Ámbar. Se puso el nombre solo.",
    ]
    assert lineas[-1].startswith("Y dos cosas más:")


def test_la_carta_se_ve_una_vez(cliente):
    con_gachamon(cliente)
    assert cliente.get(f"{API}/carta").json() == {"carta": None} and cliente.get(f"{API}/estado").json()["carta"] is False
    con_carta(cliente, TODO)                                    # la escribe en la base para esa cuenta
    vista = cliente.get(f"{API}/carta").json()["carta"]
    assert (vista["titulo"], vista["firma"], len(vista["lineas"])) == ("Carta del alcalde", "El alcalde", 12)
    assert cliente.get(f"{API}/estado").json()["carta"] is True
    assert cliente.post(f"{API}/carta/vista", headers=CABECERA).json() == {"carta": None}
    assert cliente.get(f"{API}/carta").json() == {"carta": None}
    assert cliente.get(f"{API}/estado").json()["carta"] is False


def test_la_carta_de_otro_no_es_la_tuya(cliente):
    con_gachamon(cliente, uid=1)
    con_gachamon(cliente, uid=2, nombre="Brisa")
    con_carta(cliente, TODO, uid=1)
    entrar(cliente, 2)
    assert cliente.get(f"{API}/carta").json() == {"carta": None}
    assert cliente.get(f"{API}/estado").json()["carta"] is False
    assert cliente.post(f"{API}/carta/vista", headers=CABECERA).json() == {"carta": None}
    entrar(cliente, 1)
    assert cliente.get(f"{API}/carta").json()["carta"] is not None
    assert cliente.get(f"{API}/estado").json()["carta"] is True


def test_marcar_vista_pide_la_cabecera_y_la_sesion(cliente):
    con_gachamon(cliente)
    con_carta(cliente, TODO)
    assert cliente.post(f"{API}/carta/vista").status_code == 403
    assert cliente.get(f"{API}/carta").json()["carta"] is not None
    cliente.cookies.clear()
    assert cliente.get(f"{API}/carta").status_code == 401


def test_con_un_solo_ticket_la_carta_lo_dice_en_singular():
    lineas = carta.lineas_de({**TODO, "tickets": 1, "monedas_por_tickets": 40})
    assert "El refugio cerró. Te devolví 40 monedas por tu ticket." in lineas
    assert "El refugio cerró. Te devolví 80 monedas por tus tickets." in carta.lineas_de(
        {**TODO, "tickets": 2, "monedas_por_tickets": 80})


def test_las_medallas_cobradas_van_tras_las_devoluciones_y_antes_de_los_nombres():
    lineas = carta.lineas_de(TODO)
    medallas = lineas.index(MEDALLAS)
    assert lineas[medallas - 1] == "Lo que te esperaba en el buzón ya está en tu mochila."
    assert lineas[medallas + 1].startswith("Tu Octopul ahora se llama")
    solas = carta.lineas_de({**TODO, "casas": [], "muebles": 0, "cosecha": {}, "tickets": 0, "regalos": 0})
    assert solas[3:] == [MEDALLAS, *lineas[medallas + 1:]]


def test_una_gema_va_en_singular():
    lineas = carta.lineas_de({**TODO, "gemas_por_medallas": 1})
    assert "Tenías medallas ganadas y sin cobrar: te pagué 1 gema." in lineas


def test_sin_medallas_cobradas_la_carta_no_las_nombra_y_una_carta_de_antes_tampoco():
    de_antes = {clave: valor for clave, valor in TODO.items() if clave != "gemas_por_medallas"}
    for contenido in ({**TODO, "gemas_por_medallas": 0}, de_antes):
        lineas = carta.lineas_de(contenido)
        assert not [l for l in lineas if "medallas" in l]
        assert lineas == [l for l in carta.lineas_de(TODO) if l != MEDALLAS]


def test_la_especie_del_recluta_va_con_su_mayuscula():
    nombre = esp.ESPECIES["pulpo"].nombre
    assert nombre[0].isupper()
    assert f"Tu {nombre} ahora se llama Brisa. Se puso el nombre solo." in carta.lineas_de(TODO)


# --- Las placas con nombre ------------------------------------------------------------

Y_DOS_COSAS_MAS = ("Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, "
                   "no sólo al que sale contigo.")


def test_un_recluta_que_se_nombro_solo_y_su_placa_van_antes_de_las_dos_cosas_mas():
    lineas = carta.lineas_de({**TODO, "nombres": [{"especie": "pulpo", "nombre": "Rulo"}], "placas": 1})
    assert lineas[-3:] == [
        "Tu Octopul ahora se llama Rulo. Se puso el nombre solo.",
        "Te dejé una placa con nombre en tu mochila, por si le quieres cambiar el nombre.",
        Y_DOS_COSAS_MAS,
    ]


def test_con_tres_reclutas_las_tres_lineas_y_las_placas_en_plural():
    nombres = [{"especie": "pulpo", "nombre": "Rulo"}, {"especie": "pollito", "nombre": "Copo"},
               {"especie": "michi", "nombre": "Ámbar"}]
    lineas = carta.lineas_de({**TODO, "nombres": nombres, "placas": 3})
    assert lineas[-5:] == [
        "Tu Octopul ahora se llama Rulo. Se puso el nombre solo.",
        "Tu Piollito ahora se llama Copo. Se puso el nombre solo.",
        "Tu Purreon ahora se llama Ámbar. Se puso el nombre solo.",
        "Te dejé 3 placas con nombre en tu mochila, por si les quieres cambiar el nombre.",
        Y_DOS_COSAS_MAS,
    ]
    assert lineas[-6] == MEDALLAS                       # y las de los reclutas, tras las medallas


def test_con_diez_placas_el_plural_lleva_el_numero():
    lineas = carta.lineas_de({**TODO, "placas": 10})
    assert lineas[-2:] == ["Te dejé 10 placas con nombre en tu mochila, por si les quieres cambiar el nombre.", Y_DOS_COSAS_MAS]


def test_sin_reclutas_ni_lineas_de_nombre_ni_de_placas():
    lineas = carta.lineas_de({**TODO, "nombres": [], "placas": 0})
    assert not [l for l in lineas if "ahora se llama" in l or "placa" in l]
    assert lineas[-2:] == [MEDALLAS, Y_DOS_COSAS_MAS]


def test_las_placas_las_cuenta_la_carta_y_no_las_lineas_que_salieron():
    # Un recluta de una especie que ya no está en el catálogo no lleva línea, pero su placa sí se le dejó.
    nombres = [{"especie": "ya_no_existe", "nombre": "Nube"}, {"especie": "pulpo", "nombre": "Rulo"}]
    lineas = carta.lineas_de({**TODO, "nombres": nombres, "placas": 2})
    assert lineas[-3:] == [
        "Tu Octopul ahora se llama Rulo. Se puso el nombre solo.",
        "Te dejé 2 placas con nombre en tu mochila, por si les quieres cambiar el nombre.",
        Y_DOS_COSAS_MAS,
    ]
    # Y con todas sus especies fuera del catálogo, la de las placas sale igual.
    solas = carta.lineas_de({**TODO, "nombres": [{"especie": "ya_no_existe", "nombre": "Nube"}], "placas": 1})
    assert solas[-2:] == [UNA_PLACA, Y_DOS_COSAS_MAS]


def test_una_carta_sin_placas_no_las_nombra():
    sin_la_clave = {clave: valor for clave, valor in TODO.items() if clave != "placas"}
    for contenido in (sin_la_clave, {**TODO, "placas": 0}):
        lineas = carta.lineas_de(contenido)
        assert not [l for l in lineas if "placa" in l]
        assert lineas == [l for l in carta.lineas_de(TODO) if l != UNA_PLACA]


def de_antes_del_cambio_con_un_recluta(cliente, reloj):
    """La cuenta 1, de antes del día del cambio, con un único gachamon: un recluta
    que se puso el nombre solo. Devuelve al recluta."""
    with db.conectar() as con:                  # el servicio hizo el cambio al arrancar: se deshace la marca
        con.execute("DELETE FROM cambios_hechos WHERE clave = ?", (db.CAMBIO_DE_LA_VIVIENDA,))
    alta(cliente)
    yo = identidad.de_cuenta_web(1)
    return db.crear(yo, str(PUEBLO), "pulpo", "Rulo", STATS, reloj.ahora - timedelta(days=30), se_nombro_solo=True)


def test_de_punta_a_punta_la_placa_del_cambio_se_ve_en_la_mochila_y_renombra_como_una_comprada(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    rulo = de_antes_del_cambio_con_un_recluta(cliente, reloj)
    yo, g = rulo.usuario_id, rulo.guild_id
    economia.poner_al_dia(reloj.ahora)          # el arranque que hace el día del cambio
    saldos = economia.saldos(yo, g)
    lineas = cliente.get(f"{API}/carta").json()["carta"]["lineas"]
    assert lineas[-3:-1] == ["Tu Octopul ahora se llama Rulo. Se puso el nombre solo.", UNA_PLACA]

    objetos = cliente.get(f"{API}/mochila").json()["objetos"]
    assert [(o["clave"], o["nombre"], o["cantidad"], o["uso"]) for o in objetos] == [
        ("placa", "Placa con nombre", 1, "con_nombre")]
    cuerpo = {"evento_id": "evento-placa-del-cambio", "clave": "placa", "nombre": "Nube", "gachamon_id": rulo.id}
    r = cliente.post(f"{API}/mochila/usar", json=cuerpo, headers=CABECERA).json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (True, None, "Rulo pasa a llamarse Nube.")
    assert r["estado"]["gachamon"]["nombre"] == "Nube" and r["mochila"]["objetos"] == []
    # Se gastó, y el nombre ya es suyo: no se lo puso solo.
    assert db.inventario(yo, g) == {} and db.por_id(rulo.id).se_nombro_solo is False
    assert economia.saldos(yo, g) == saldos     # usarla no cobra nada


@pytest.mark.parametrize("vinculada", [False, True], ids=["cuenta_nueva", "de_discord"])
def test_quien_llega_despues_del_cambio_no_recibe_placas(cliente, monkeypatch, vinculada):
    poner_reloj(monkeypatch)
    (con_vinculo if vinculada else con_gachamon)(cliente)
    usuario = LA_DE_DISCORD if vinculada else identidad.de_cuenta_web(1)
    db.crear(usuario, str(PUEBLO), "pollito", "Brote", STATS, db.ahora_utc(), activa=False, se_nombro_solo=True)
    economia.poner_al_dia(db.ahora_utc())       # otro arranque, ya con el cambio hecho
    assert cliente.get(f"{API}/mochila").json() == {"objetos": []}
    assert cliente.get(f"{API}/carta").json() == {"carta": None}
