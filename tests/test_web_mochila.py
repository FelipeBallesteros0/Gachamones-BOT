import pytest

import db
import identidad
import objetos
from ayudas_web import ESCRIBIR, PUEBLO, con_gachamon, entrar, poner_reloj
from test_web_tienda import LA_DE_DISCORD, con_vinculo

MOCHILA, USAR = "/gachamon/api/mochila", "/gachamon/api/mochila/usar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def dar(usuario, clave, cantidad=1):
    for _ in range(cantidad):
        db.regalar(usuario, G, objetos.CATALOGO[clave])


def usar(cliente, clave, evento="evento-mochila-01", **mas):
    return cliente.post(USAR, json={"evento_id": evento, "clave": clave, **mas}, headers=ESCRIBIR)


def test_la_mochila_ensena_lo_que_llevas_y_como_se_usa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "pocion_comida", 2); dar(YO, "placa", 1); dar(YO, "semilla", 3)
    objetos_ = cliente.get(MOCHILA).json()["objetos"]
    assert [(o["clave"], o["cantidad"], o["uso"]) for o in objetos_] == [
        ("pocion_comida", 2, "al_momento"), ("placa", 1, "con_nombre"), ("semilla", 3, None),
    ]
    assert objetos_[2]["nota"] == "Se usa en el huerto." and objetos_[0]["nota"] is None
    assert objetos_[0]["icono"] == "iconos/objetos/pocion_comida.png"
    assert "**" not in objetos_[0]["descripcion"]


def test_lo_que_no_se_usa_desde_la_mochila_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    sin_uso = objetos.Objeto(clave="adorno", nombre="Adorno", emoji="x", descripcion="**Algo** bonito.", precio=1)
    monkeypatch.setitem(objetos.CATALOGO, "adorno", sin_uso)
    dar(YO, "adorno"); dar(YO, "ticket_refugio"); dar(YO, "poroto_rojo")
    por_clave = {o["clave"]: o for o in cliente.get(MOCHILA).json()["objetos"]}
    assert por_clave["adorno"]["uso"] is None and por_clave["adorno"]["descripcion"] == "Algo bonito."
    assert por_clave["adorno"]["nota"] == "Eso no se usa desde la mochila."
    assert por_clave["ticket_refugio"]["uso"] is None
    assert por_clave["ticket_refugio"]["nota"] == "No lo necesitas: tu estancia en el refugio no tiene plazo."
    assert por_clave["poroto_rojo"]["uso"] is None and por_clave["poroto_rojo"]["nota"] == "Se usa en el huerto."


def test_el_ticket_con_plazo_se_usa_al_momento(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_vinculo(cliente)
    dar(LA_DE_DISCORD, "ticket_refugio")
    ticket = cliente.get(MOCHILA).json()["objetos"][0]
    assert ticket["uso"] == "al_momento" and ticket["nota"] is None


def test_usar_dos_veces_con_el_mismo_evento_gasta_una(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas", 2)
    # Con el reloj quieto no decae nada: la comida queda justo donde se deja.
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET hambre = 50 WHERE usuario_id = ? AND guild_id = ?", (YO, G))
    cuerpo = {"evento_id": "evento-mochila-01", "clave": "golosinas"}
    primera = cliente.post(USAR, json=cuerpo, headers=ESCRIBIR).json()
    segunda = cliente.post(USAR, json=cuerpo, headers=ESCRIBIR).json()
    assert primera["ok"] and segunda["ok"] and primera["mensaje"] == segunda["mensaje"]
    assert primera["mensaje"] == segunda["mensaje"] == "Pelusa come. Comida +25 (ahora 75)."
    assert [o["cantidad"] for o in segunda["mochila"]["objetos"]] == [1]
    assert segunda["estado"]["gachamon"]["barras"]["comida"] == primera["estado"]["gachamon"]["barras"]["comida"]


def test_la_placa_con_un_nombre_que_vale_renombra(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "placa")
    r = usar(cliente, "placa", nombre="Nube").json()
    assert r["ok"] is True and r["clave"] is None and r["mensaje"] == "Pelusa pasa a llamarse Nube."
    assert r["estado"]["gachamon"]["nombre"] == "Nube" and r["mochila"]["objetos"] == []


def test_la_placa_con_un_nombre_que_no_vale_no_se_gasta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "placa")
    for cuerpo in ({"nombre": "   "}, {}):
        r = usar(cliente, "placa", evento="evento-placa-1", **cuerpo)
        assert r.status_code == 200
        assert r.json()["ok"] is False and r.json()["clave"] == "nombre"
        assert r.json()["mensaje"] and "**" not in r.json()["mensaje"]
    assert db.inventario(YO, G) == {"placa": 1}


def test_la_placa_con_el_mismo_nombre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "placa")
    r = usar(cliente, "placa", nombre="Pelusa").json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "mismo_nombre", "Ya se llama así.")
    assert db.inventario(YO, G) == {"placa": 1}


def test_usar_lo_que_no_llevas(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    r = usar(cliente, "pocion_comida")
    assert r.status_code == 200
    assert (r.json()["ok"], r.json()["clave"], r.json()["mensaje"]) == (
        False, "no_tienes", "Ya no te queda ninguno.")


def test_la_semilla_no_se_usa_desde_la_mochila(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "semilla")
    r = usar(cliente, "semilla").json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "no_se_usa", "Eso no se usa desde la mochila.")
    assert db.inventario(YO, G) == {"semilla": 1}


def test_el_ticket_sin_plazo_no_hace_falta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "ticket_refugio")
    r = usar(cliente, "ticket_refugio").json()
    assert (r["clave"], r["mensaje"]) == (
        "sin_plazo", "No lo necesitas: tu estancia en el refugio no tiene plazo.")
    assert db.inventario(YO, G) == {"ticket_refugio": 1}


def test_el_ticket_con_plazo_da_otra_estancia(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_vinculo(cliente)
    dar(LA_DE_DISCORD, "ticket_refugio")
    r = usar(cliente, "ticket_refugio").json()
    assert r["ok"] is True
    assert r["mensaje"].startswith("Tienes otra estancia en el refugio, hasta el ")
    assert len(r["mensaje"].rsplit(" ", 1)[1].rstrip(".")) == 5


def test_las_frases_de_cada_efecto(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    reloj.pasar(hours=1)
    ok = []
    for objeto in objetos.CATALOGO.values():
        if not objeto.se_aplica_al_momento or objeto.dias_de_refugio:
            continue
        dar(LA_DE_DISCORD, objeto.clave)
        r = usar(cliente, objeto.clave, evento=f"evento-{objeto.clave}-x".replace("_", "-")).json()
        if r["ok"]:
            ok.append((objeto, r["mensaje"]))
            assert "**" not in r["mensaje"] and "{" not in r["mensaje"] and "None" not in r["mensaje"]
    mensajes = [m for _, m in ok]
    assert any(m.endswith(" otra vez.") for m in mensajes)
    assert any("durante 5 minutos." in m and " gana +" in m for m in mensajes)
    assert any("se come una" in m and "de fuerza y de velocidad durante 5 minutos." in m for m in mensajes)
    assert any("en las cuatro estadísticas durante 5 minutos." in m for m in mensajes)


def test_una_clave_que_no_existe_es_un_422(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    for cuerpo in ({"clave": "no_existe"}, {"clave": 3}, {}):
        r = cliente.post(USAR, json={"evento_id": "evento-raro-01", **cuerpo}, headers=ESCRIBIR)
        assert r.status_code == 422 and r.json()["detail"]["clave"] == "peticion"
    for cuerpo in ({"clave": "placa"}, {"clave": "placa", "evento_id": "x"}, [1]):
        r = cliente.post(USAR, json=cuerpo, headers=ESCRIBIR)
        assert r.status_code == 422 and r.json()["detail"]["clave"] == "evento"


def test_un_evento_para_otra_cosa_es_un_409(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "pocion_comida"); dar(YO, "placa")
    assert usar(cliente, "pocion_comida", evento="evento-doble-01").status_code == 200
    r = usar(cliente, "placa", evento="evento-doble-01", nombre="Nube")
    assert r.status_code == 409
    assert r.json()["detail"] == {"clave": "evento", "mensaje": "Ese evento ya se usó para otra cosa."}


def test_lo_que_ya_no_esta_en_el_catalogo_no_aparece_ni_rompe(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "pocion_comida")
    with db.conectar() as con:
        con.execute("INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) VALUES (?, ?, 'fantasma', 4)",
                    (YO, G))
    r = cliente.get(MOCHILA)
    assert r.status_code == 200 and [o["clave"] for o in r.json()["objetos"]] == ["pocion_comida"]


def test_sin_gachamon_se_ve_la_mochila_pero_no_se_usa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    from ayudas_web import alta
    alta(cliente)
    dar(YO, "pocion_comida")
    assert [o["clave"] for o in cliente.get(MOCHILA).json()["objetos"]] == ["pocion_comida"]
    r = usar(cliente, "pocion_comida")
    assert r.status_code == 409 and r.json()["detail"]["clave"] == "sin_gachamon"
    assert db.inventario(YO, G) == {"pocion_comida": 1}


def test_si_el_gachamon_murio_entre_medias_no_se_gasta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    dar(LA_DE_DISCORD, "pocion_comida")
    reloj.pasar(days=5)
    r = usar(cliente, "pocion_comida")
    assert r.status_code == 409 and r.json()["detail"]["clave"] == "sin_gachamon"
    assert db.inventario(LA_DE_DISCORD, G) == {"pocion_comida": 1}
    assert db.criatura_activa(LA_DE_DISCORD, G) is None   # de verdad murió


def test_un_replay_sin_gachamon_activo_es_un_409_y_no_un_500(monkeypatch):
    import web.mochila as mochila
    from economia import ResultadoUso
    hecho = ResultadoUso(ok=True, efecto="comida", objeto="pocion_comida", comida=25, replay=True)
    with pytest.raises(Exception) as error:
        mochila.frase(objetos.CATALOGO["pocion_comida"], hecho)
    assert error.value.status_code == 409 and error.value.detail["clave"] == "sin_gachamon"


def test_sin_la_cabecera_no_pasa(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "pocion_comida")
    r = cliente.post(USAR, json={"evento_id": "evento-mochila-01", "clave": "pocion_comida"})
    assert r.status_code == 403 and r.json()["detail"]["clave"] == "sin_cabecera"
    assert db.inventario(YO, G) == {"pocion_comida": 1}


def test_cada_cuenta_ve_y_usa_su_mochila(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    dar(YO, "pocion_comida", 2)
    entrar(cliente, 2)
    con_gachamon(cliente, 2, "Nube")
    assert cliente.get(MOCHILA).json()["objetos"] == []
    assert usar(cliente, "pocion_comida").json()["clave"] == "no_tienes"
    entrar(cliente, 1)
    assert [o["cantidad"] for o in cliente.get(MOCHILA).json()["objetos"]] == [2]
