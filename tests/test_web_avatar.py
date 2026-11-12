import db
import identidad
from ayudas_web import ESCRIBIR, PUEBLO, entrar

AVATAR = "/gachamon/api/avatar"
BUENO = {"nombre": "Feli", "genero": "macho", "piel": "media", "pelo": "corto",
         "color_de_pelo": "castano", "ropa": "poleron"}


def empezar(cliente, uid=1):
    entrar(cliente, uid)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)


def test_las_opciones_se_piden_con_sesion(cliente):
    assert cliente.get(f"{AVATAR}/opciones").status_code == 401
    entrar(cliente, 1)
    opciones = cliente.get(f"{AVATAR}/opciones").json()
    assert [o["clave"] for o in opciones["pieles"]] == ["clara", "media", "tostada", "oscura"]
    assert opciones["generos"][0] == {"clave": "macho", "nombre": "Masculino"}


def test_guardar_el_avatar(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json() == BUENO
    assert db.avatar_de(identidad.de_cuenta_web(1), str(PUEBLO)).nombre == "Feli"


def test_la_respuesta_trae_el_nombre_normalizado(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "nombre": "  Feli   Pe "}, headers=ESCRIBIR)
    assert respuesta.json()["nombre"] == "Feli Pe"


def test_sin_haber_empezado_no_hay_donde_guardarlo(cliente):
    entrar(cliente, 1)
    respuesta = cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"


def test_un_avatar_que_no_vale_vuelve_con_su_frase(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "nombre": "<script>"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"
    assert "letras" in respuesta.json()["detail"]["mensaje"]


def test_una_opcion_que_no_existe_nombra_el_campo_en_castellano(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "color_de_pelo": "verde"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["mensaje"] == "Ese color de pelo no existe."


def test_un_cuerpo_incompleto_tambien_vuelve_con_nuestra_forma_de_error(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={"nombre": "Feli"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"
    assert "genero" in respuesta.json()["detail"]["mensaje"]


def test_un_campo_que_no_es_texto_se_rechaza(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "piel": 3}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"
    assert "piel" in respuesta.json()["detail"]["mensaje"]


def test_un_cuerpo_que_no_es_un_objeto_se_rechaza(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json=["Feli"], headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "avatar"


def test_los_campos_de_mas_se_ignoran(cliente):
    empezar(cliente)
    respuesta = cliente.put(AVATAR, json={**BUENO, "usuario_id": "otro"}, headers=ESCRIBIR)
    assert respuesta.status_code == 200 and respuesta.json() == BUENO


def test_un_cuerpo_que_ni_es_json_sale_con_nuestra_forma(cliente):
    empezar(cliente)
    respuesta = cliente.put(
        AVATAR, content=b"{roto", headers={**ESCRIBIR, "Content-Type": "application/json"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["clave"] == "peticion"
    assert respuesta.json()["detail"]["mensaje"].strip()


def test_guardar_pide_la_cabecera(cliente):
    empezar(cliente)
    assert cliente.put(AVATAR, json=BUENO).status_code == 403


def test_el_avatar_es_de_cada_cual(cliente):
    empezar(cliente, 1)
    cliente.put(AVATAR, json=BUENO, headers=ESCRIBIR)
    empezar(cliente, 2)
    cliente.put(AVATAR, json={**BUENO, "nombre": "Ana"}, headers=ESCRIBIR)
    assert db.avatar_de(identidad.de_cuenta_web(1), str(PUEBLO)).nombre == "Feli"
    assert db.avatar_de(identidad.de_cuenta_web(2), str(PUEBLO)).nombre == "Ana"
