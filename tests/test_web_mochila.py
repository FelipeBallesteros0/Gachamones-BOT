import pytest

import db
import identidad
import objetos
import simulacion as sim
from ayudas_web import ESCRIBIR, PUEBLO, con_gachamon, entrar, poner_reloj
from test_web_tienda import LA_DE_DISCORD, con_vinculo

MOCHILA, USAR = "/gachamon/api/mochila", "/gachamon/api/mochila/usar"
ESTADO = "/gachamon/api/estado"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


def dar(usuario, clave, cantidad=1):
    for _ in range(cantidad):
        db.regalar(usuario, G, objetos.CATALOGO[clave])


def usar(cliente, clave, evento="evento-mochila-01", **mas):
    return cliente.post(USAR, json={"evento_id": evento, "clave": clave, **mas}, headers=ESCRIBIR)


def con_hambre(usuario, comida=50):
    """Con el reloj quieto no decae nada: la comida queda justo donde se deja.
    Con la barra llena, la comida ni se usaría (`no_hace_falta`)."""
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET hambre = ? WHERE usuario_id = ? AND guild_id = ?", (comida, usuario, G))


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
    dar(YO, "adorno"); dar(YO, "poroto_rojo")
    por_clave = {o["clave"]: o for o in cliente.get(MOCHILA).json()["objetos"]}
    assert por_clave["adorno"]["uso"] is None and por_clave["adorno"]["descripcion"] == "Algo bonito."
    assert por_clave["adorno"]["nota"] == "Eso no se usa desde la mochila."
    assert por_clave["poroto_rojo"]["uso"] is None and por_clave["poroto_rojo"]["nota"] == "Se usa en el huerto."


@pytest.mark.parametrize("vinculada", [False, True])
def test_el_ticket_del_refugio_ya_no_se_lista_ni_se_usa(cliente, monkeypatch, vinculada):
    # El refugio cerró: la mochila ya no trata su ticket, tampoco el de quien tenía plazo en él.
    poner_reloj(monkeypatch)
    (con_vinculo if vinculada else con_gachamon)(cliente)
    usuario = LA_DE_DISCORD if vinculada else YO
    dar(usuario, "ticket_refugio"); dar(usuario, "placa")
    assert [o["clave"] for o in cliente.get(MOCHILA).json()["objetos"]] == ["placa"]
    r = usar(cliente, "ticket_refugio")
    assert r.status_code == 422
    assert r.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert db.inventario(usuario, G) == {"ticket_refugio": 1, "placa": 1}


def test_usar_dos_veces_con_el_mismo_evento_gasta_una(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas", 2)
    con_hambre(YO)
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
    con_hambre(YO)
    r = usar(cliente, "pocion_comida")
    assert r.status_code == 200
    assert (r.json()["ok"], r.json()["clave"], r.json()["mensaje"]) == (
        False, "no_tienes", "Ya no te queda ninguno.")


def test_la_pocion_de_comida_con_la_barra_llena_no_se_gasta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)                     # recién nacido: la comida a 100
    dar(YO, "pocion_comida")
    r = usar(cliente, "pocion_comida")
    assert r.status_code == 200
    assert (r.json()["ok"], r.json()["clave"], r.json()["mensaje"]) == (
        False, "no_hace_falta", "Pelusa no tiene hambre: su comida ya está a 100. No se gastó nada.")
    assert db.inventario(YO, G) == {"pocion_comida": 1}
    assert [o["cantidad"] for o in r.json()["mochila"]["objetos"]] == [1]


def test_el_silbato_sin_espera_de_entrenar_no_se_gasta(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)                     # recién nacido: sin ninguna espera
    dar(YO, "silbato")
    r = usar(cliente, "silbato")
    assert r.status_code == 200
    assert (r.json()["ok"], r.json()["clave"], r.json()["mensaje"]) == (
        False, "no_hace_falta", "Pelusa ya puede entrenar: no hace falta. No se gastó nada.")
    assert db.inventario(YO, G) == {"silbato": 1}


def test_la_semilla_no_se_usa_desde_la_mochila(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "semilla")
    r = usar(cliente, "semilla").json()
    assert (r["ok"], r["clave"], r["mensaje"]) == (False, "no_se_usa", "Eso no se usa desde la mochila.")
    assert db.inventario(YO, G) == {"semilla": 1}


def test_las_frases_de_cada_efecto(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_vinculo(cliente)
    reloj.pasar(hours=1)
    # Que los reinicios tengan una espera que borrar: si no, ni se usan.
    pelusa = db.criatura_activa(LA_DE_DISCORD, G)
    for accion in (sim.ENTRENAR, sim.COMPETIR):
        db.poner_cooldown(pelusa.id, accion, db.ahora_utc())
    for objeto in objetos.CATALOGO.values():
        dar(LA_DE_DISCORD, objeto.clave)
    # Cada uno de los que la mochila dice que se usan al momento.
    al_momento = [o["clave"] for o in cliente.get(MOCHILA).json()["objetos"] if o["uso"] == "al_momento"]
    assert al_momento
    ok = []
    for clave in al_momento:
        r = usar(cliente, clave, evento=f"evento-{clave}-x".replace("_", "-")).json()
        if r["ok"]:
            ok.append((clave, r["mensaje"]))
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
    con_hambre(YO)                # con la barra llena ni se usaría, ni se anotaría
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


# --- El gachamon que la pantalla enseñaba ------------------------------------------
#
# Si el cambio de gachamon quedó registrado antes de la petición (otro activado
# desde Discord), sólo se nota comparando con el que la pantalla tenía, que el
# cliente manda como `gachamon_id`.

def con_relevo(cliente):
    """La cuenta vinculada con Pelusa activa y Nube esperando en la incubadora."""
    con_vinculo(cliente)
    nube = db.crear(LA_DE_DISCORD, G, "pulpo", "Nube", (15, 15, 15, 15), db.ahora_utc(), activa=False)
    return db.criatura_activa(LA_DE_DISCORD, G), nube


def test_si_ya_se_activo_a_otro_no_se_le_aplica_el_objeto(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    pelusa, nube = con_relevo(cliente)
    dar(LA_DE_DISCORD, "golosinas")
    visto = cliente.get(ESTADO).json()["gachamon"]["id"]
    assert visto == pelusa.id
    assert [o["clave"] for o in cliente.get(MOCHILA).json()["objetos"]] == ["golosinas"]
    assert db.activar(nube.id, LA_DE_DISCORD, G)     # desde Discord
    antes = (db.por_id(pelusa.id), db.por_id(nube.id))
    r = usar(cliente, "golosinas", gachamon_id=visto)
    assert r.status_code == 409
    assert r.json()["detail"] == {"clave": "sin_gachamon", "mensaje": "Tu gachamon ya no es el mismo. Mira otra vez."}
    assert db.inventario(LA_DE_DISCORD, G) == {"golosinas": 1}
    assert (db.por_id(pelusa.id), db.por_id(nube.id)) == antes


def test_con_el_gachamon_que_se_ve_o_sin_decirlo_se_usa_como_siempre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas", 2)
    con_hambre(YO)
    visto = cliente.get(ESTADO).json()["gachamon"]["id"]
    # Sin `gachamon_id`, como mandan las páginas de antes durante el despliegue.
    sin_decirlo = usar(cliente, "golosinas", evento="evento-mochila-02").json()
    diciendolo = usar(cliente, "golosinas", evento="evento-mochila-03", gachamon_id=visto).json()
    assert sin_decirlo["mensaje"] == "Pelusa come. Comida +25 (ahora 75)."
    assert diciendolo["mensaje"] == "Pelusa come. Comida +25 (ahora 100)."
    assert db.inventario(YO, G) == {}


def test_un_gachamon_id_que_no_es_un_entero_es_un_422(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas")
    visto = cliente.get(ESTADO).json()["gachamon"]["id"]
    for raro in (str(visto), float(visto), True, None, [visto]):
        r = usar(cliente, "golosinas", gachamon_id=raro)
        assert r.status_code == 422 and r.json()["detail"]["clave"] == "peticion", raro
    assert db.inventario(YO, G) == {"golosinas": 1}


def test_un_gachamon_id_fuera_de_rango_es_un_422_y_no_gasta_nada(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    dar(YO, "golosinas")
    con_hambre(YO)
    antes = db.criatura_activa(YO, G)
    for n, raro in enumerate((2**70, 2**63, 0, -1)):
        r = usar(cliente, "golosinas", evento=f"evento-mochila-1{n}", gachamon_id=raro)
        assert r.status_code == 422, raro
        assert r.json()["detail"] == {"clave": "peticion", "mensaje": "La petición no se entiende."}
    assert db.inventario(YO, G) == {"golosinas": 1}
    assert db.criatura_activa(YO, G) == antes


def test_un_replay_sin_gachamon_activo_es_un_409_y_no_un_500(monkeypatch):
    import web.mochila as mochila
    from economia import ResultadoUso
    hecho = ResultadoUso(ok=True, efecto="comida", objeto="pocion_comida", comida=25, replay=True)
    with pytest.raises(Exception) as error:
        mochila.frase(objetos.CATALOGO["pocion_comida"], hecho)
    assert error.value.status_code == 409 and error.value.detail["clave"] == "sin_gachamon"


@pytest.mark.parametrize("motivo", [None, "no_hace_falta"], ids=["usado", "no_hace_falta"])
def test_un_efecto_sin_frase_es_un_fallo_nuestro_y_no_se_disfraza(motivo):
    # Como el del ticket del refugio, que ya no tiene frase porque la página no lo usa.
    import web.mochila as mochila
    from economia import ResultadoUso
    hecho = ResultadoUso(ok=motivo is None, motivo=motivo, objeto="pocion_comida", efecto="desconocido")
    with pytest.raises(RuntimeError, match="sin frase: 'desconocido'"):
        mochila.frase(objetos.CATALOGO["pocion_comida"], hecho)


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
    con_hambre(identidad.de_cuenta_web(2))
    assert cliente.get(MOCHILA).json()["objetos"] == []
    assert usar(cliente, "pocion_comida").json()["clave"] == "no_tienes"
    entrar(cliente, 1)
    assert [o["cantidad"] for o in cliente.get(MOCHILA).json()["objetos"]] == [2]
