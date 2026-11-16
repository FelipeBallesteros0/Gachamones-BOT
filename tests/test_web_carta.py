import db
import especies as esp
from ayudas_web import CABECERA, con_carta, con_gachamon, entrar
from web import carta

API = "/gachamon/api"

TODO = {"ancho": 4, "fondo": 3, "camas": 3, "vivos": 2, "casas": ["mediana", "grande"], "monedas_por_casas": 1700, "muebles": 2,
        "cosecha": {"poroto_rojo": 3}, "tickets": 1, "monedas_por_tickets": 40, "regalos": 1, "nombres": [{"especie": "pulpo", "nombre": "Brisa"}]}


def test_la_carta_dice_todo_lo_que_toco_en_su_orden():
    assert carta.lineas_de(TODO) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 4 × 3 casillas, y lo puedes ampliar.",
        "Te dejé puestas 3 camas: una para ti y una para cada gachamon.",
        "Te devolví lo que costaron tus casas: 1700 monedas.",
        "Tus 2 muebles están en guardados: ponlos donde quieras.",
        "Coseché lo que tenías plantado y lo dejé en tu mochila. El huerto vuelve más adelante.",
        "El refugio cerró. Te devolví 40 monedas por tu ticket.",
        "Lo que te esperaba en el buzón ya está en tu mochila.",
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez.",
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]


def test_a_quien_no_le_toco_nada_la_carta_le_dice_lo_justo():
    nada = {**TODO, "ancho": 3, "camas": 1, "vivos": 0, "casas": [], "monedas_por_casas": 0, "muebles": 0, "cosecha": {}, "tickets": 0, "monedas_por_tickets": 0, "regalos": 0, "nombres": []}
    assert carta.lineas_de(nada) == [
        "El pueblo cambió, y vengo a contarte qué te toca.",
        "Desde hoy todos vivimos en el mismo edificio. Tu departamento mide 3 × 3 casillas, y lo puedes ampliar.",
        "Te dejé tu cama puesta y otra guardada, para cuando llegue un gachamon.",
        "Y dos cosas más: ya ningún gachamon muere, y a todos les pasa el tiempo, no sólo al que sale contigo.",
    ]


def test_una_casa_y_un_mueble_van_en_singular():
    lineas = carta.lineas_de({**TODO, "casas": ["pequena"], "monedas_por_casas": 200, "muebles": 1})
    assert "Te devolví lo que costó tu casa: 200 monedas." in lineas and "Tu mueble está en guardados: ponlo donde quieras." in lineas


def test_una_moneda_va_en_singular():
    lineas = carta.lineas_de({**TODO, "tickets": 1, "monedas_por_tickets": 1})
    assert "El refugio cerró. Te devolví 1 moneda por tu ticket." in lineas


def test_un_recluta_de_una_especie_que_ya_no_existe_no_lleva_linea():
    lineas = carta.lineas_de({**TODO, "nombres": [{"especie": "ya_no_existe", "nombre": "Nube"}, {"especie": "pulpo", "nombre": "Brisa"}]})
    assert [l for l in lineas if "ahora se llama" in l] == [
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez."
    ]


def test_varios_reclutas_llevan_una_linea_cada_uno_en_su_orden():
    nombres = [{"especie": "pulpo", "nombre": "Brisa"}, {"especie": "ya_no_existe", "nombre": "Nube"},
               {"especie": "pollito", "nombre": "Copo"}, {"especie": "michi", "nombre": "Ámbar"}]
    lineas = carta.lineas_de({**TODO, "nombres": nombres})
    assert [l for l in lineas if "ahora se llama" in l] == [
        "Tu Octopul ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez.",
        "Tu Piollito ahora se llama Copo. Se puso el nombre solo, y se lo puedes cambiar una vez.",
        "Tu Purreon ahora se llama Ámbar. Se puso el nombre solo, y se lo puedes cambiar una vez.",
    ]
    assert lineas[-1].startswith("Y dos cosas más:")


def test_la_carta_se_ve_una_vez(cliente):
    con_gachamon(cliente)
    assert cliente.get(f"{API}/carta").json() == {"carta": None} and cliente.get(f"{API}/estado").json()["carta"] is False
    con_carta(cliente, TODO)                                    # la escribe en la base para esa cuenta
    vista = cliente.get(f"{API}/carta").json()["carta"]
    assert (vista["titulo"], vista["firma"], len(vista["lineas"])) == ("Carta del alcalde", "El alcalde", 10)
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


def test_la_especie_del_recluta_va_con_su_mayuscula():
    nombre = esp.ESPECIES["pulpo"].nombre
    assert nombre[0].isupper()
    assert f"Tu {nombre} ahora se llama Brisa. Se puso el nombre solo, y se lo puedes cambiar una vez." in carta.lineas_de(TODO)
