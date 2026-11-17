from dataclasses import replace

import db
import economia
import especies as esp
import identidad
import nombres
import retrato
from ayudas_web import ESCRIBIR, PUEBLO, T0, alta, entrar, ganar_el_primero, poner_la_segunda_cama, poner_reloj

ESTADO = "/gachamon/api/estado"
STATS = (10, 10, 10, 10)
G = str(PUEBLO)
YO = identidad.de_cuenta_web(1)
ANA_DISCORD = "222222222222222222"


def nace(usuario=YO, especie="pollito", nombre="Pelusa", ahora=T0, **mas):
    return db.crear(usuario, G, especie, nombre, STATS, ahora, **mas)


def test_sin_cuenta_no_hay_estado(cliente):
    assert cliente.get(ESTADO).status_code == 401
    entrar(cliente, 1)
    respuesta = cliente.get(ESTADO)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["clave"] == "sin_cuenta"


def sin_el_dia_del_cambio():
    """El servicio hace el día del cambio al arrancar: sin su marca, la base es
    una en la que todavía no ha ocurrido."""
    with db.conectar() as con:
        con.execute("DELETE FROM cambios_hechos WHERE clave = ?", (economia.CAMBIO_DE_LA_VIVIENDA,))


def test_recien_llegado_no_tiene_ni_avatar_ni_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    sin_el_dia_del_cambio()                     # antes del cambio, un monedero nace con 50 y 50
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"] is None and estado["gachamon"] is None
    assert estado["globos"] == []
    assert estado["saldos"] == {"monedas": 50, "gemas": 50}
    assert estado["persona"] == {"usuario": "felipe", "vinculada": False}
    assert estado["ahora"] == T0.isoformat()
    assert "hogar" not in estado and estado["lugar"]["clave"] == "casa"


def test_quien_llega_despues_del_cambio_parte_en_cero(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    with db.conectar() as con:                  # el servicio hizo el día del cambio al arrancar
        assert con.execute(
            "SELECT 1 FROM cambios_hechos WHERE clave = ?", (economia.CAMBIO_DE_LA_VIVIENDA,)
        ).fetchone()
    entrar(cliente, 1)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    estado = cliente.get(ESTADO).json()
    assert estado["saldos"] == {"monedas": 0, "gemas": 0}


def test_el_estado_completo_de_un_gachamon_recien_nacido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace(genero="hembra")
    estado = cliente.get(ESTADO).json()
    assert estado["avatar"]["nombre"] == "Feli"
    assert estado["gachamon"] == {
        "id": creado.id, "nombre": "Pelusa", "espera_nombre": False,
        "se_nombro_solo": False, "especie": "pollito", "nombre_especie": esp.ESPECIES["pollito"].nombre,
        "emoji": esp.ESPECIES["pollito"].emoji,
        "etapa": "bebe", "nombre_etapa": esp.nombre_etapa("bebe", "hembra"),
        "nivel": 1, "genero": "hembra",
        "barras": {"comida": 100, "animo": 100, "aseo": 100},
        "cara": "feliz", "desfallecido": False,
        "retrato": f"/gachamon/retrato/pollito/bebe/feliz/sin.png?v={retrato.version()}",
        "esperas": {"alimentar": 0, "jugar": 0, "entrenar": 0, "limpiar": 0, "acariciar": 0},
        "titulo": None, "sugerido": None,
    }
    assert estado["globos"] and all(g["tipo"] in ("lugar", "suelta") for g in estado["globos"])
    assert estado["carta"] is False and estado["guia"] is None
    assert set(estado) == {
        "ahora", "persona", "avatar", "saldos", "gachamon", "globos", "lugar", "carta", "guia",
    }


def test_el_estado_ya_no_habla_de_reclutas_sin_nombre(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    assert "sin_nombre" not in cliente.get(ESTADO).json()
    nace()
    assert "sin_nombre" not in cliente.get(ESTADO).json()


def test_las_barras_bajan_con_el_reloj_y_leer_no_guarda(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    reloj.pasar(hours=10)
    barras = cliente.get(ESTADO).json()["gachamon"]["barras"]
    assert barras["comida"] < 100 and barras["animo"] < 100 and barras["aseo"] < 100
    assert all(isinstance(v, int) for v in barras.values())
    assert db.por_id(creado.id).actualizada_en == T0


def test_el_que_espera_nombre_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    nace(nombre="Piollito")
    assert cliente.get(ESTADO).json()["gachamon"]["espera_nombre"] is True


def test_el_primero_no_se_nombro_solo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    ganar_el_primero(cliente)
    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"]["se_nombro_solo"] is False


def test_el_que_se_nombro_solo_lo_dice(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    nace(nombre="Miga", se_nombro_solo=True)
    assert cliente.get(ESTADO).json()["gachamon"]["se_nombro_solo"] is True


def test_las_esperas_salen_en_segundos_y_la_de_alimentar_cede_con_hambre(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    for accion in ("alimentar", "jugar", "acariciar"):
        db.poner_cooldown(creado.id, accion, T0)
    reloj.pasar(minutes=4, seconds=30)
    esperas = cliente.get(ESTADO).json()["gachamon"]["esperas"]
    assert esperas == {"alimentar": 18 * 60 + 30, "jugar": 24 * 60 + 30,
                       "entrenar": 0, "limpiar": 0, "acariciar": 14 * 60 + 30}
    db.guardar(replace(db.por_id(creado.id), hambre=30.0, actualizada_en=reloj.ahora))
    assert cliente.get(ESTADO).json()["gachamon"]["esperas"]["alimentar"] == 0


def test_con_necesidades_los_globos_piden_primero(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace()
    db.guardar(replace(creado, limpieza=10.0))
    tipos = [g["tipo"] for g in cliente.get(ESTADO).json()["globos"]]
    assert tipos[0] == "necesidad" and "suelta" in tipos


def test_el_de_una_cuenta_web_se_queda_desfallecido_y_vivo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    nace()
    reloj.pasar(days=5)
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["barras"]["comida"] == 0 and gachamon["desfallecido"] is True
    assert gachamon["cara"] == "mal"


def test_cada_cual_ve_su_estado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente, 1)
    nace(usuario=YO, nombre="Mío")
    alta(cliente, 2, nombre="Ana")
    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"] is None and estado["avatar"]["nombre"] == "Ana"


def morir_de_antes(criatura, cuando):
    """Una muerte de antes del cambio, que la cuenta nunca vio: `muerta_en` a mano."""
    db.guardar(replace(db.por_id(criatura.id), hambre=0.0, muerta_en=cuando, causa_muerte="hambre"))


def test_el_estado_ya_no_habla_de_difuntos(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    viejo = nace(nombre="Viejo")
    vivo = nace(nombre="Pelusa", activa=False)
    reloj.pasar(days=3)
    morir_de_antes(viejo, reloj.ahora)
    estado = cliente.get(ESTADO).json()
    assert "difunto" not in estado
    assert estado["gachamon"]["id"] == vivo.id and estado["gachamon"]["nombre"] == "Pelusa"


def test_una_muerte_de_antes_sin_ver_no_rompe_nada(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    viejo = nace(nombre="Viejo")
    reloj.pasar(days=3)
    morir_de_antes(viejo, reloj.ahora)
    estado = cliente.get(ESTADO).json()
    assert estado["gachamon"] is None and "difunto" not in estado
    assert "sin_nombre" not in estado and estado["globos"] == []
    assert db.por_id(viejo.id).muerta_en == reloj.ahora


def test_difunto_visto_ya_no_existe(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    viejo = nace(nombre="Viejo")
    morir_de_antes(viejo, reloj.ahora)
    respuesta = cliente.post("/gachamon/api/difunto/visto", headers=ESCRIBIR)
    # Lo mismo que cualquier dirección que no existe.
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": {"clave": "no_existe", "mensaje": "Eso no existe."}}


def test_cualquiera_con_la_comida_en_cero_esta_desfallecido(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    entrar(cliente, 2)
    cliente.post("/gachamon/api/cuenta/empezar", headers=ESCRIBIR)
    codigo = cliente.post("/gachamon/api/cuenta/codigo", headers=ESCRIBIR).json()["codigo"]
    assert db.canjear_codigo_de_vinculo(codigo, ANA_DISCORD, G, T0) == "ok"
    creado = nace(usuario=ANA_DISCORD)
    db.guardar(replace(creado, hambre=0.0))
    estado = cliente.get(ESTADO).json()
    assert estado["persona"]["vinculada"] is True
    assert estado["gachamon"]["barras"]["comida"] == 0
    assert estado["gachamon"]["desfallecido"] is True


def test_el_lugar_dice_lo_que_ofrece_y_el_gachamon_su_titulo(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    nace(genero="hembra")
    estado = cliente.get(ESTADO).json()
    assert estado["lugar"]["ofrece"] == ["departamento"] and estado["gachamon"]["titulo"] is None
    cliente.post("/gachamon/api/lugar", json={"lugar": "tienda"}, headers=ESCRIBIR)
    assert cliente.get(ESTADO).json()["lugar"]["ofrece"] == ["tienda"]


def test_el_titulo_sale_ya_concordado(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)
    creado = nace(genero="hembra")
    with db.conectar() as con:
        con.execute("UPDATE criaturas SET titulo = 'titulo_invicto' WHERE id = ?", (creado.id,))
    assert cliente.get(ESTADO).json()["gachamon"]["titulo"] == "la Invicta"


# --- Sin gachamon: la guía y la primera aventura -------------------------------

GUIA_CAMA = "Pon tu segunda cama: entra a «Construir», tócala en los guardados y después toca una casilla."
GUIA_AVENTURA = "Ya hay cama para un gachamon. Sal al pueblo y ve a «Aventura»."
SIN_CAMA = "Antes pon tu segunda cama en tu departamento: sin cama, nadie se queda contigo."


def test_la_guia_dice_el_paso_que_toca(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    assert cliente.get(ESTADO).json()["guia"] == {"clave": "cama", "texto": GUIA_CAMA}
    poner_la_segunda_cama(cliente)
    assert cliente.get(ESTADO).json()["guia"] == {"clave": "aventura", "texto": GUIA_AVENTURA}
    creado = nace()
    assert cliente.get(ESTADO).json()["guia"] is None
    # Quien se quedó sin ninguno antes del cambio vuelve a tener la guía.
    morir_de_antes(creado, reloj.ahora)
    assert cliente.get(ESTADO).json()["guia"] == {"clave": "aventura", "texto": GUIA_AVENTURA}


def test_el_que_espera_nombre_trae_uno_sugerido_y_es_siempre_el_mismo(cliente, monkeypatch):
    reloj = poner_reloj(monkeypatch)
    alta(cliente)
    especie = esp.ESPECIES["pollito"].nombre
    creado = nace(nombre=especie)                      # espera nombre
    sugerido = cliente.get(ESTADO).json()["gachamon"]["sugerido"]
    assert sugerido in nombres.NOMBRES
    reloj.pasar(hours=3)
    assert all(cliente.get(ESTADO).json()["gachamon"]["sugerido"] == sugerido for _ in range(5))

    # Ni el de otro de su plantel ni el de su especie: aquí sólo queda «Miga».
    monkeypatch.setattr(nombres, "NOMBRES", ("Nube", especie, "Miga"))
    nace(nombre="Nube", activa=False)
    assert cliente.get(ESTADO).json()["gachamon"]["sugerido"] == "Miga"

    # Con un nombre propio ya no se sugiere ninguno.
    db.guardar(replace(db.por_id(creado.id), nombre="Pelusa"))
    gachamon = cliente.get(ESTADO).json()["gachamon"]
    assert gachamon["espera_nombre"] is False and gachamon["sugerido"] is None


def test_aventura_se_ofrece_solo_a_quien_no_tiene_gachamon(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    alta(cliente)

    def el_lugar(clave):
        cliente.post("/gachamon/api/lugar", json={"lugar": clave}, headers=ESCRIBIR)
        lugar = cliente.get(ESTADO).json()["lugar"]
        assert lugar["clave"] == clave
        return lugar["abre"], lugar["ofrece"], lugar["aviso"]

    assert el_lugar("aventura") == ("despues", ["aventura"], SIN_CAMA)
    poner_la_segunda_cama(cliente)
    assert el_lugar("aventura") == ("despues", ["aventura"], None)
    # Los demás lugares, sin gachamon, como siempre.
    assert el_lugar("plaza") == ("despues", [], "Esto se abre más adelante.")
    assert el_lugar("tienda") == ("ya", ["tienda"], None)
    assert el_lugar("casa") == ("ya", ["departamento"], None)
    nace()
    assert el_lugar("aventura") == ("despues", [], "Esto se abre más adelante.")
