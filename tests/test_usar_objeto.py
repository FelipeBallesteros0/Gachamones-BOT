"""Usar algo de la mochila es una regla del juego, y una sola operación.

Gastar la unidad, avanzar al gachamon y aplicar el efecto van en una única
transacción y con evento: un reintento no gasta dos veces, y ningún rechazo
cuesta el objeto. La usan Discord y la web.
"""
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import casas
import db
import economia
import huerto as hue
import identidad
import objetos as obj
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
U, G = "u1", "g1"
WEB = identidad.de_cuenta_web(12)
STATS = (15, 15, 15, 15)
PLACA = obj.CATALOGO["placa"]
TICKET = obj.CATALOGO["ticket_refugio"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "usar.db")
    db.inicializar()


def nace(nombre="Kuro", usuario=U):
    return db.crear(usuario, G, "pulpo", nombre, STATS, T0)


def dar(usuario, clave, cuantos):
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, usuario, G, clave, cuantos)


def hambrear(criatura, comida):
    db.guardar(replace(criatura, hambre=float(comida)))


def cuando_ya_murio_de_hambre(desde):
    """Un instante en que la activa ya murió de hambre sin que nadie lo apuntara.

    Cae dentro de su estancia en el refugio: a la intemperie el hambre tiene un
    suelo y no mata, y en el refugio a una identidad de Discord sí.
    """
    muerte = sim.momento_de_muerte(db.criatura_activa(U, G)) + timedelta(hours=1)
    assert muerte < desde + timedelta(days=casas.DIAS_DE_REFUGIO)
    return muerte


def efectos(criatura_id, ahora=T0):
    return {
        stat: bonus
        for stat, (bonus, _) in db.efectos_activos(criatura_id, ahora).items()
    }


# --- Una sola unidad, pase lo que pase ---------------------------------------

def test_usar_dos_veces_con_el_mismo_evento_gasta_una_sola_unidad(base):
    criatura = nace()
    dar(U, "pocion_comida", 2)
    hambrear(criatura, 40)
    primera = economia.usar_objeto("evento-uso-01", U, G, obj.CATALOGO["pocion_comida"], T0)
    segunda = economia.usar_objeto("evento-uso-01", U, G, obj.CATALOGO["pocion_comida"], T0)
    assert primera.ok and primera.efecto == "comida" and primera.comida == 60
    assert segunda.ok and segunda.replay and segunda.comida == 60
    assert db.inventario(U, G) == {"pocion_comida": 1}


def test_ningun_rechazo_gasta_el_objeto(base):
    dar(U, "pocion_comida", 1)
    dar(U, "semilla", 1)
    assert economia.usar_objeto("evento-uso-02", U, G, obj.CATALOGO["pocion_comida"], T0).motivo == "sin_gachamon"
    nace()
    assert economia.usar_objeto("evento-uso-03", U, G, obj.CATALOGO["semilla"], T0).motivo == "no_se_usa"
    assert economia.usar_objeto("evento-uso-04", U, G, obj.CATALOGO["silbato"], T0).motivo == "no_tienes"
    assert db.inventario(U, G) == {"pocion_comida": 1, "semilla": 1}


def test_a_un_gachamon_que_ya_murio_no_se_le_gasta_nada(base):
    nace()
    dar(U, "pocion_comida", 1)
    despues = cuando_ya_murio_de_hambre(T0)   # una identidad de Discord, sin casa
    assert economia.usar_objeto("evento-uso-05", U, G, obj.CATALOGO["pocion_comida"], despues).motivo == "sin_gachamon"
    assert db.inventario(U, G) == {"pocion_comida": 1}


def test_el_que_ya_murio_queda_guardado_muerto(base):
    """Se entera de la muerte al avanzarlo, y la guarda: no la deja sin apuntar."""
    nace()
    dar(U, "pocion_comida", 1)
    despues = cuando_ya_murio_de_hambre(T0)

    economia.usar_objeto("evento-uso-06", U, G, obj.CATALOGO["pocion_comida"], despues)

    assert db.criatura_activa(U, G) is None


def test_el_replay_no_vuelve_a_tirar_el_dado(base):
    """Lo que salió la primera vez es lo que se cuenta: ni otro bonus ni otro
    efecto puesto encima."""
    criatura = nace()
    dar(U, "fuerza_1d12", 2)
    pocion = obj.CATALOGO["fuerza_1d12"]
    primera = economia.usar_objeto("evento-uso-07", U, G, pocion, T0, random.Random(7))
    otro_dado = random.Random(primera.bonus)          # cualquiera que no sea el 7
    segunda = economia.usar_objeto("evento-uso-07", U, G, pocion, T0, otro_dado)

    assert segunda.replay and (segunda.bonus, segunda.caras, segunda.stats) == (
        primera.bonus, primera.caras, primera.stats
    )
    assert efectos(criatura.id) == {"fuerza": primera.bonus}
    assert db.inventario(U, G) == {"fuerza_1d12": 1}


def test_un_evento_no_sirve_para_usar_otra_cosa(base):
    nace()
    dar(U, "pocion_comida", 1)
    dar(U, "silbato", 1)
    economia.usar_objeto("evento-uso-08", U, G, obj.CATALOGO["pocion_comida"], T0)

    with pytest.raises(RuntimeError):
        economia.usar_objeto("evento-uso-08", U, G, obj.CATALOGO["silbato"], T0)
    assert db.inventario(U, G) == {"silbato": 1}


def test_un_rechazo_no_se_anota_y_repetirlo_vuelve_a_decidir(base):
    """Entre un intento y el reintento puede haber llegado el objeto."""
    nace()
    assert economia.usar_objeto("evento-uso-09", U, G, obj.CATALOGO["silbato"], T0).motivo == "no_tienes"
    dar(U, "silbato", 1)

    otra_vez = economia.usar_objeto("evento-uso-09", U, G, obj.CATALOGO["silbato"], T0)

    assert otra_vez.ok and not otra_vez.replay
    assert db.inventario(U, G) == {}


# --- Lo que hace cada cosa ---------------------------------------------------

def test_el_silbato_deja_entrenar_ya(base):
    criatura = nace()
    dar(U, "silbato", 1)
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)

    resultado = economia.usar_objeto("evento-uso-10", U, G, obj.CATALOGO["silbato"], T0)

    assert resultado.ok and resultado.efecto == "reinicia"
    assert resultado.accion == sim.ENTRENAR
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.inventario(U, G) == {}


def test_la_pocion_tira_su_dado_y_queda_puesta(base):
    criatura = nace()
    dar(U, "fuerza_1d8", 1)

    resultado = economia.usar_objeto(
        "evento-uso-11", U, G, obj.CATALOGO["fuerza_1d8"], T0, random.Random(7)
    )

    assert resultado.ok and resultado.efecto == "estadistica"
    assert resultado.stats == ("fuerza",) and resultado.caras == 8
    assert 1 <= resultado.bonus <= resultado.caras
    assert efectos(criatura.id) == {"fuerza": resultado.bonus}
    assert db.inventario(U, G) == {}


def test_la_sopaipilla_de_color_tira_un_dado_para_las_dos(base):
    criatura = nace()
    clave = hue.clave_de_sopaipilla("rojo")
    dar(U, clave, 1)

    resultado = economia.usar_objeto(
        "evento-uso-12", U, G, obj.CATALOGO[clave], T0, random.Random(7)
    )

    assert resultado.ok and resultado.efecto == "sopaipilla"
    assert resultado.stats == ("fuerza", "velocidad")
    assert resultado.caras == hue.caras_de(criatura.caracter, "rojo")
    assert 1 <= resultado.bonus <= resultado.caras
    assert resultado.gusto == hue.le_gusta(criatura.caracter, "rojo") != ""
    assert efectos(criatura.id) == {
        "fuerza": resultado.bonus, "velocidad": resultado.bonus,
    }
    assert db.inventario(U, G) == {}


def test_la_sopaipilla_arcoiris_va_a_las_cuatro_con_su_dado(base):
    criatura = nace()
    clave = hue.clave_de_sopaipilla(hue.ARCOIRIS, 10)
    dar(U, clave, 1)

    resultado = economia.usar_objeto(
        "evento-uso-13", U, G, obj.CATALOGO[clave], T0, random.Random(7)
    )

    assert resultado.ok and resultado.efecto == "sopaipilla"
    assert resultado.stats == sim.ESTADISTICAS
    assert resultado.caras == 10 and 1 <= resultado.bonus <= 10
    assert resultado.gusto is None
    assert efectos(criatura.id) == {stat: resultado.bonus for stat in sim.ESTADISTICAS}


def test_el_ticket_da_otra_semana_desde_ahora(base):
    """Una identidad de Discord que nunca había mirado su casa: el ticket le
    escribe la estancia y no se queda en la que se le supone al leerla."""
    nace()
    dar(U, "ticket_refugio", 1)
    ahora = T0 + timedelta(days=1)

    resultado = economia.usar_objeto("evento-uso-14", U, G, TICKET, ahora)

    assert resultado.ok and resultado.efecto == "refugio"
    assert resultado.refugio_hasta == ahora + timedelta(days=7)
    luego = ahora + timedelta(days=3)
    assert db.hogar_leido(U, G, luego).refugio_hasta == ahora + timedelta(days=7)
    assert db.inventario(U, G) == {}


def test_el_replay_del_ticket_devuelve_la_misma_fecha(base):
    nace()
    dar(U, "ticket_refugio", 2)
    ahora = T0 + timedelta(days=1)
    primera = economia.usar_objeto("evento-uso-15", U, G, TICKET, ahora)

    segunda = economia.usar_objeto("evento-uso-15", U, G, TICKET, ahora + timedelta(hours=2))

    assert segunda.replay and segunda.refugio_hasta == primera.refugio_hasta
    assert db.inventario(U, G) == {"ticket_refugio": 1}


def test_quien_juega_en_la_web_no_gasta_el_ticket(base):
    nace(usuario=WEB)
    dar(WEB, "ticket_refugio", 1)

    resultado = economia.usar_objeto("evento-uso-16", WEB, G, TICKET, T0)

    assert not resultado.ok and resultado.motivo == "sin_plazo"
    assert db.inventario(WEB, G) == {"ticket_refugio": 1}


def test_la_comida_no_pasa_de_cien(base):
    criatura = nace()
    dar(U, "golosinas", 1)
    hambrear(criatura, 90)

    resultado = economia.usar_objeto("evento-uso-17", U, G, obj.CATALOGO["golosinas"], T0)

    assert resultado.ok and resultado.efecto == "comida" and resultado.comida == 10
    assert resultado.criatura.hambre == 100.0 == db.criatura_activa(U, G).hambre


# --- La placa ------------------------------------------------------------------

def test_la_placa_le_cambia_el_nombre(base):
    nace("Kuro")
    dar(U, "placa", 1)

    resultado = economia.renombrar_con_placa("evento-uso-20", U, G, PLACA, "  Pelusa  ", T0)

    assert resultado.ok and resultado.efecto == "nombre"
    assert resultado.nombre_anterior == "Kuro"
    assert resultado.criatura.nombre == "Pelusa" == db.criatura_activa(U, G).nombre
    assert db.inventario(U, G) == {}


def test_un_nombre_que_no_vale_no_gasta_la_placa(base):
    nace("Kuro")
    dar(U, "placa", 1)
    with pytest.raises(ValueError) as validador:
        sim.normalizar_nombre("Pelusa <@everyone>")

    resultado = economia.renombrar_con_placa(
        "evento-uso-21", U, G, PLACA, "Pelusa <@everyone>", T0
    )

    assert not resultado.ok and resultado.motivo == "nombre"
    assert resultado.problema == str(validador.value)
    assert db.inventario(U, G) == {"placa": 1}
    assert db.criatura_activa(U, G).nombre == "Kuro"


def test_el_mismo_nombre_no_gasta_la_placa(base):
    nace("Kuro")
    dar(U, "placa", 1)

    resultado = economia.renombrar_con_placa("evento-uso-22", U, G, PLACA, " Kuro ", T0)

    assert not resultado.ok and resultado.motivo == "mismo_nombre"
    assert db.inventario(U, G) == {"placa": 1}


def test_repetir_la_placa_con_el_mismo_evento_no_gasta_otra(base):
    nace("Kuro")
    dar(U, "placa", 2)
    primera = economia.renombrar_con_placa("evento-uso-23", U, G, PLACA, "Pelusa", T0)

    segunda = economia.renombrar_con_placa("evento-uso-23", U, G, PLACA, "Pelusa", T0)

    assert primera.ok and segunda.ok and segunda.replay
    assert segunda.nombre_anterior == "Kuro" and segunda.criatura.nombre == "Pelusa"
    assert db.inventario(U, G) == {"placa": 1}


def test_la_placa_no_se_usa_sin_formulario_ni_otra_cosa_con_el(base):
    """Cada una con lo suyo: la placa necesita un nombre, y un nombre no le
    sirve a nada que no sea la placa."""
    nace()
    dar(U, "placa", 1)
    dar(U, "silbato", 1)

    assert economia.usar_objeto("evento-uso-24", U, G, PLACA, T0).motivo == "no_se_usa"
    assert economia.renombrar_con_placa(
        "evento-uso-25", U, G, obj.CATALOGO["silbato"], "Pelusa", T0
    ).motivo == "no_se_usa"
    assert db.inventario(U, G) == {"placa": 1, "silbato": 1}


# --- El gachamon a quien se le daba ---------------------------------------------
#
# La web dice a qué gachamon se lo da (el que enseñaba la pantalla): si el activo
# ya es otro, no se le da a nadie. Discord no lo dice, y para Discord no cambia nada.

GOLOSINAS = obj.CATALOGO["golosinas"]


def en_la_incubadora(nombre="Nube"):
    return db.crear(U, G, "pulpo", nombre, STATS, T0, activa=False)


def test_a_otro_gachamon_no_se_le_usa_nada_ni_se_gasta(base):
    kuro = nace("Kuro")
    nube = en_la_incubadora()
    assert db.activar(nube.id, U, G, T0)
    dar(U, "golosinas", 1)
    dar(U, "placa", 1)
    antes = (db.por_id(kuro.id), db.por_id(nube.id))

    uso = economia.usar_objeto("evento-uso-30", U, G, GOLOSINAS, T0, criatura_id=kuro.id)
    placa = economia.renombrar_con_placa(
        "evento-uso-31", U, G, PLACA, "Pelusa", T0, criatura_id=kuro.id
    )

    assert (uso.ok, uso.motivo) == (placa.ok, placa.motivo) == (False, "sin_gachamon")
    assert db.inventario(U, G) == {"golosinas": 1, "placa": 1}
    assert (db.por_id(kuro.id), db.por_id(nube.id)) == antes


def test_al_gachamon_activo_se_le_usa_como_siempre(base):
    kuro = nace("Kuro")
    dar(U, "golosinas", 1)
    dar(U, "placa", 1)
    hambrear(kuro, 50)

    uso = economia.usar_objeto("evento-uso-32", U, G, GOLOSINAS, T0, criatura_id=kuro.id)
    placa = economia.renombrar_con_placa(
        "evento-uso-33", U, G, PLACA, "Pelusa", T0, criatura_id=kuro.id
    )

    assert uso.ok and uso.efecto == "comida" and uso.comida == 25
    assert placa.ok and placa.nombre_anterior == "Kuro"
    assert db.criatura_activa(U, G).nombre == "Pelusa"
    assert db.inventario(U, G) == {}


def test_el_replay_contesta_lo_de_la_primera_vez_aunque_el_activo_ya_sea_otro(base):
    kuro = nace("Kuro")
    nube = en_la_incubadora()
    dar(U, "golosinas", 2)
    dar(U, "placa", 2)
    hambrear(kuro, 50)
    uso = economia.usar_objeto("evento-uso-34", U, G, GOLOSINAS, T0, criatura_id=kuro.id)
    placa = economia.renombrar_con_placa(
        "evento-uso-35", U, G, PLACA, "Pelusa", T0, criatura_id=kuro.id
    )
    assert db.activar(nube.id, U, G, T0)

    otro_uso = economia.usar_objeto(
        "evento-uso-34", U, G, GOLOSINAS, T0, criatura_id=kuro.id
    )
    otra_placa = economia.renombrar_con_placa(
        "evento-uso-35", U, G, PLACA, "Pelusa", T0, criatura_id=kuro.id
    )

    assert uso.ok and placa.ok
    assert otro_uso.ok and otro_uso.replay and otro_uso.comida == uso.comida == 25
    assert otra_placa.ok and otra_placa.replay and otra_placa.nombre_anterior == "Kuro"
    assert db.inventario(U, G) == {"golosinas": 1, "placa": 1}
