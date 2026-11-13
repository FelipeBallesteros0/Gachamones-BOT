from dataclasses import replace
from datetime import timedelta

import pytest

import db
import economia
import identidad
import simulacion as sim
from ayudas_web import ESCRIBIR, PUEBLO, alta, con_gachamon, entrar, poner_reloj

CUIDAR, ACARICIAR = "/gachamon/api/cuidar", "/gachamon/api/acariciar"
YO, G = identidad.de_cuenta_web(1), str(PUEBLO)


@pytest.fixture(autouse=True)
def huevo_comun(monkeypatch):
    """El huevo da siempre una especie común: con una rara (una de cada
    veinticinco) nacer pagaría «Uno entre veinticinco» y las gemas variarían."""
    import especies as esp
    import nacer

    comun = esp.ESPECIES["pollito"]
    assert comun.rareza == esp.COMUN
    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", lambda rng: comun)


def cuidar(cliente, accion, evento="evento-0001"):
    return cliente.post(CUIDAR, json={"accion": accion, "evento_id": evento}, headers=ESCRIBIR)


def test_jugar_sube_el_animo_paga_una_moneda_y_devuelve_el_estado(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    respuesta = cuidar(cliente, "jugar")
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200 and cuerpo["ok"] is True
    assert cuerpo["monedas"] == 1 and cuerpo["mensaje"]
    assert cuerpo["estado"]["gachamon"]["barras"]["animo"] > antes
    assert cuerpo["estado"]["saldos"]["monedas"] == 51
    assert cuerpo["estado"]["gachamon"]["esperas"]["jugar"] == 29 * 60


def test_el_mismo_evento_repetido_no_premia_ni_aplica_dos_veces(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    primera = cuidar(cliente, "jugar", "evento-doble").json()
    repetida = cuidar(cliente, "jugar", "evento-doble").json()
    assert repetida["ok"] is True and repetida["monedas"] == primera["monedas"] == 1
    assert repetida["estado"]["saldos"]["monedas"] == 51
    assert repetida["estado"]["gachamon"]["barras"] == primera["estado"]["gachamon"]["barras"]
    assert db.criatura_activa(YO, G).xp == sim.XP_POR_CUIDADO[sim.JUGAR]


def test_el_mismo_evento_para_otra_accion_se_rechaza(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-mezcla")
    respuesta = cuidar(cliente, "limpiar", "evento-mezcla")
    assert respuesta.status_code == 409 and respuesta.json()["detail"]["clave"] == "evento"


def test_antes_de_tiempo_la_regla_dice_que_no_y_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-0001")
    reloj.pasar(minutes=9)
    cuerpo = cuidar(cliente, "jugar", "evento-0002").json()
    assert cuerpo["ok"] is False and cuerpo["monedas"] == 0
    assert cuerpo["espera"] == 20 * 60 and cuerpo["mensaje"]
    assert cuerpo["estado"]["saldos"]["monedas"] == 51


@pytest.mark.parametrize("cuerpo, clave", [
    ({"accion": "bailar", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "competir", "evento_id": "evento-0001"}, "accion"),
    ({"accion": "acariciar", "evento_id": "evento-0001"}, "accion"),
    ({"evento_id": "evento-0001"}, "accion"),
    ({"accion": "jugar"}, "evento"),
    ({"accion": "jugar", "evento_id": "corto"}, "evento"),
    ({"accion": "jugar", "evento_id": "x" * 65}, "evento"),
    ({"accion": "jugar", "evento_id": "con espacios 1"}, "evento"),
    ({"accion": "jugar", "evento_id": "ñandú-00001"}, "evento"),
    ({"accion": "jugar", "evento_id": 12345678}, "evento"),
])
def test_un_pedido_mal_hecho_no_toca_nada(cliente, monkeypatch, cuerpo, clave):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(CUIDAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == clave
    assert economia.saldos(YO, G).asciicoins == 50


def test_sin_gachamon_no_hay_a_quien_cuidar_ni_acariciar(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    for respuesta in (cuidar(cliente, "jugar"), cliente.post(ACARICIAR, headers=ESCRIBIR)):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"]["clave"] == "sin_gachamon"


def test_acariciar_cuenta_una_vez_y_despues_dice_cuanto_falta(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    antes = cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]["animo"]
    primera = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert primera["ok"] is True and primera["espera"] == 19 * 60
    assert primera["estado"]["gachamon"]["barras"]["animo"] == antes + 5
    reloj.pasar(minutes=4)
    segunda = cliente.post(ACARICIAR, headers=ESCRIBIR).json()
    assert segunda["ok"] is False and segunda["espera"] == 15 * 60
    assert segunda["estado"]["gachamon"]["barras"] == cliente.get("/gachamon/api/estado").json()["gachamon"]["barras"]
    assert segunda["estado"]["saldos"] == {"monedas": 50, "gemas": 50}


def test_nadie_cuida_ni_acaricia_al_gachamon_de_otro(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente, 1)
    mio = db.criatura_activa(YO, G)
    reloj.pasar(hours=6)
    alta(cliente, 2, nombre="Ana")
    assert cuidar(cliente, "jugar").status_code == 409
    assert cliente.post(ACARICIAR, headers=ESCRIBIR).status_code == 409
    intruso = cliente.post(
        CUIDAR, headers=ESCRIBIR,
        json={"accion": "jugar", "evento_id": "evento-0009", "usuario_id": YO,
              "guild_id": G, "criatura_id": mio.id},
    )
    assert intruso.status_code == 409
    assert db.por_id(mio.id).xp == 0 and economia.saldos(YO, G).asciicoins == 50


def test_las_dos_piden_la_cabecera(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    assert cliente.post(CUIDAR, json={"accion": "jugar", "evento_id": "evento-0001"}).status_code == 403
    assert cliente.post(ACARICIAR).status_code == 403


# --- Las medallas: las mismas reglas que en Discord ----------------------------

ALFA = {"nombre": "De la alfa", "gemas": 25}


def test_un_cuidado_que_desbloquea_una_medalla_la_trae_y_sube_las_gemas(cliente, monkeypatch):
    # «De la alfa» es la más barata de provocar: mientras la alfa siga abierta
    # la gana cualquiera, y se paga la primera vez que se miran sus medallas.
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuerpo = cuidar(cliente, "jugar", "evento-alfa").json()
    assert cuerpo["ok"] is True and cuerpo["logros"] == [ALFA]
    assert cuerpo["estado"]["saldos"] == {"monedas": 51, "gemas": 75}


def test_repetir_el_mismo_evento_no_paga_la_medalla_otra_vez(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    assert cuidar(cliente, "jugar", "evento-alfa").json()["logros"] == [ALFA]
    repetido = cuidar(cliente, "jugar", "evento-alfa").json()
    assert repetido["ok"] is True and repetido["logros"] == []
    assert repetido["estado"]["saldos"]["gemas"] == 75
    assert economia.saldos(YO, G).asciigems == 75


def test_un_cuidado_normal_no_trae_medallas(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-alfa")
    normal = cuidar(cliente, "limpiar", "evento-normal").json()
    assert normal["ok"] is True and normal["logros"] == []
    assert normal["estado"]["saldos"]["gemas"] == 75


def test_un_cuidado_que_no_sale_no_mira_las_medallas(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-0001")
    llamadas = []
    monkeypatch.setattr(economia, "pagar_logros", lambda *a: llamadas.append(a))
    reloj.pasar(minutes=9)
    cuerpo = cuidar(cliente, "jugar", "evento-0002").json()
    assert cuerpo["ok"] is False and cuerpo["logros"] == [] and llamadas == []


# --- Un cuidado o una caricia no le caen al relevo ---------------------------

ANA_DISCORD = "222222222222222222"
STATS = (10, 10, 10, 10)


def _vinculada_que_se_muere_con_relevo(cliente, reloj):
    """Ana, vinculada: su activa se muere de hambre y en la incubadora hay otro."""
    entrar(cliente, 2)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, reloj.ahora) == "ok"
    activa = db.crear(ANA_DISCORD, G, "pollito", "Viejo", STATS, reloj.ahora)
    relevo = db.crear(ANA_DISCORD, G, "pulpo", "Tinta", STATS, reloj.ahora, activa=False)
    reloj.pasar(days=5)
    return activa, relevo


@pytest.mark.parametrize("hacer", [
    lambda c: cuidar(c, "jugar", "evento-relevo"),
    lambda c: c.post(ACARICIAR, headers=ESCRIBIR),
], ids=["cuidar", "acariciar"])
def test_si_la_activa_muere_en_la_peticion_no_se_le_aplica_al_relevo(cliente, monkeypatch, hacer):
    reloj = poner_reloj(monkeypatch)
    activa, relevo = _vinculada_que_se_muere_con_relevo(cliente, reloj)

    respuesta = hacer(cliente)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "sin_gachamon", "mensaje": "Tu gachamon ya no es el mismo. Mira otra vez.",
    }
    # La muerte sí quedó registrada y el relevo salió, pero nadie lo tocó.
    assert db.por_id(activa.id).causa_muerte == "hambre"
    guardado = db.por_id(relevo.id)
    assert guardado.activa and guardado.xp == 0 and guardado.animo == relevo.animo
    assert all(s == timedelta(0) for s in db.esperas(
        relevo.id, reloj.ahora, (sim.JUGAR, sim.ACARICIAR)).values())
    assert economia.saldos(ANA_DISCORD, G) == economia.Saldos(50, 50)

    # Una vez visto, ya es el mismo: lo siguiente sí le llega.
    assert hacer(cliente).status_code == 200


def test_quien_nunca_tuvo_gachamon_oye_que_no_tiene(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    for respuesta, que in ((cuidar(cliente, "jugar"), "cuidar"),
                           (cliente.post(ACARICIAR, headers=ESCRIBIR), "acariciar")):
        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == {
            "clave": "sin_gachamon", "mensaje": f"No tienes un gachamon que {que}.",
        }


# --- Lo que faltaba de la ruta del cuidado ------------------------------------

@pytest.mark.parametrize("cuerpo", [[], "jugar", None, 7])
def test_un_cuerpo_que_no_es_un_objeto_da_422_accion(cliente, monkeypatch, cuerpo):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(CUIDAR, json=cuerpo, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == "accion"


@pytest.mark.parametrize("accion", [["jugar"], {"jugar": 1}, "actualizar"])
def test_una_accion_que_no_es_un_cuidado_da_422_y_no_500(cliente, monkeypatch, accion):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(
        CUIDAR, json={"accion": accion, "evento_id": "evento-0001"}, headers=ESCRIBIR)
    assert respuesta.status_code == 422 and respuesta.json()["detail"]["clave"] == "accion"


@pytest.mark.parametrize("evento", ["evento-0001\n", "corto", None, ["evento-0001"]])
def test_un_evento_que_no_vale_lo_dice(cliente, monkeypatch, evento):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    respuesta = cliente.post(CUIDAR, json={"accion": "jugar", "evento_id": evento}, headers=ESCRIBIR)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {
        "clave": "evento", "mensaje": "Ese identificador de evento no vale.",
    }


def test_el_409_del_evento_trae_su_frase_y_no_la_de_la_excepcion(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)

    def choca(*_):
        raise RuntimeError("texto interno de la excepción")

    monkeypatch.setattr(economia, "ejecutar_cuidado", choca)
    respuesta = cuidar(cliente, "jugar", "evento-mezcla")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {
        "clave": "evento", "mensaje": "Ese cuidado ya se usó para otra acción.",
    }
    assert "texto interno" not in respuesta.text


def test_una_evolucion_lo_dice_y_paga_su_premio(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)
    db.guardar(replace(db.criatura_activa(YO, G), xp=24, hambre=50.0))
    cuerpo = cuidar(cliente, "alimentar", "evento-evoluciona").json()
    assert cuerpo["ok"] is True and cuerpo["evoluciono"] is True
    # Una del cuidado y diez de la evolución.
    assert cuerpo["monedas"] == 11
    assert cuerpo["estado"]["gachamon"]["etapa"] != "bebe"
    assert cuerpo["estado"]["saldos"]["monedas"] == 61


def test_un_cuidado_sin_evolucion_dice_que_no(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    assert cuidar(cliente, "jugar").json()["evoluciono"] is False


def test_una_espera_con_fraccion_de_segundo_se_redondea_hacia_arriba(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    con_gachamon(cliente)
    reloj.pasar(hours=6)
    cuidar(cliente, "jugar", "evento-0001")
    reloj.pasar(seconds=1, milliseconds=500)
    cuerpo = cuidar(cliente, "jugar", "evento-0002").json()
    # Faltan 29 min menos 1,5 s: 1738,5 s, que se dicen 1739.
    assert cuerpo["ok"] is False and cuerpo["espera"] == 29 * 60 - 1
    assert cuerpo["estado"]["gachamon"]["esperas"]["jugar"] == 29 * 60 - 1
