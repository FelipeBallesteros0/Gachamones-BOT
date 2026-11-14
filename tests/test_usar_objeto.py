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
    kuro = nace()
    db.poner_cooldown(kuro.id, sim.ENTRENAR, T0)   # con espera: si no, ni haría falta
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
    hambrear(nace(), 40)          # con la barra llena ni se usaría, ni se anotaría
    dar(U, "pocion_comida", 1)
    dar(U, "silbato", 1)
    economia.usar_objeto("evento-uso-08", U, G, obj.CATALOGO["pocion_comida"], T0)

    with pytest.raises(RuntimeError):
        economia.usar_objeto("evento-uso-08", U, G, obj.CATALOGO["silbato"], T0)
    assert db.inventario(U, G) == {"silbato": 1}


def test_si_el_efecto_falla_despues_de_gastar_el_objeto_vuelve_a_la_mochila(base, monkeypatch):
    kuro = nace()
    db.poner_cooldown(kuro.id, sim.ENTRENAR, T0)   # sin espera no llegaría a gastarlo
    dar(U, "silbato", 1)

    def revienta(*_args, **_kwargs):
        raise RuntimeError("el efecto no se pudo aplicar")

    monkeypatch.setattr(db, "quitar_cooldown_en", revienta)
    with pytest.raises(RuntimeError):
        economia.usar_objeto("evento-uso-40", U, G, obj.CATALOGO["silbato"], T0)
    assert db.inventario(U, G) == {"silbato": 1}


def test_un_objeto_sin_efecto_conocido_es_un_error_y_no_se_gasta(base, monkeypatch):
    """La guarda no es un `assert`, que con `python -O` desaparece."""
    nace()
    adorno = obj.Objeto(clave="adorno", nombre="Adorno", emoji="x", descripcion="Algo bonito.", precio=1)
    monkeypatch.setitem(obj.CATALOGO, "adorno", adorno)
    monkeypatch.setattr(obj.Objeto, "se_aplica_al_momento", property(lambda objeto: True))
    dar(U, "adorno", 1)
    with pytest.raises(ValueError):
        economia.usar_objeto("evento-uso-41", U, G, adorno, T0)
    assert db.inventario(U, G) == {"adorno": 1}


def test_un_rechazo_no_se_anota_y_repetirlo_vuelve_a_decidir(base):
    """Entre un intento y el reintento puede haber llegado el objeto."""
    kuro = nace()
    db.poner_cooldown(kuro.id, sim.ENTRENAR, T0)
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
    """Una identidad de Discord con la estancia empezada ayer: el ticket se la
    escribe desde ahora, no desde que acababa. (Quien nunca había mirado su casa
    ya tiene la semana entera que se le supone: ése no lo gasta.)"""
    nace()
    db.hogar_de(U, G, T0)
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
    db.hogar_de(U, G, T0)
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


# --- Lo que no haría nada no se gasta ----------------------------------------------
#
# Tres casos, ni uno más: comida que no sumaría nada, un reinicio sin espera que
# borrar y un ticket que no alargaría la estancia. Se mira con el gachamon ya
# puesto al día y antes de gastar, y no se anota: es un rechazo como los demás.

POCION_COMIDA = obj.CATALOGO["pocion_comida"]
SILBATO = obj.CATALOGO["silbato"]


def test_la_comida_con_la_barra_llena_no_se_gasta(base):
    kuro = nace()                                   # recién nacido: la comida a 100
    dar(U, "pocion_comida", 1)

    llena = economia.usar_objeto("evento-uso-50", U, G, POCION_COMIDA, T0)

    assert llena.ok is False and llena.motivo == "no_hace_falta"
    assert llena.efecto == "comida" and llena.criatura.id == kuro.id
    assert db.inventario(U, G) == {"pocion_comida": 1}
    # No quedó anotado: el mismo evento, con la barra ya baja, sí la usa.
    hambrear(db.criatura_activa(U, G), 40)
    baja = economia.usar_objeto("evento-uso-50", U, G, POCION_COMIDA, T0)
    assert baja.ok and not baja.replay and baja.comida == 60
    assert db.inventario(U, G) == {}


def test_con_la_comida_casi_llena_tambien_es_no_hace_falta_si_sumaria_cero(base):
    """Se cuenta redondeado, como en la frase: «Comida +0» no se le dice a nadie."""
    nace()
    dar(U, "golosinas", 2)

    hambrear(db.criatura_activa(U, G), 99.6)
    casi = economia.usar_objeto("evento-uso-51", U, G, GOLOSINAS, T0)
    assert (casi.ok, casi.motivo, casi.efecto) == (False, "no_hace_falta", "comida")
    assert db.inventario(U, G) == {"golosinas": 2}

    hambrear(db.criatura_activa(U, G), 99.4)
    usada = economia.usar_objeto("evento-uso-52", U, G, GOLOSINAS, T0)
    assert usada.ok and usada.comida == 1
    assert db.inventario(U, G) == {"golosinas": 1}


def test_un_reinicio_sin_espera_no_se_gasta(base):
    kuro = nace()
    dar(U, "silbato", 1)

    sin_espera = economia.usar_objeto("evento-uso-53", U, G, SILBATO, T0)
    assert (sin_espera.ok, sin_espera.motivo) == (False, "no_hace_falta")
    assert sin_espera.efecto == "reinicia" and sin_espera.accion == sim.ENTRENAR
    # Una espera que ya pasó tampoco es nada que borrar.
    db.poner_cooldown(kuro.id, sim.ENTRENAR, T0 - sim.COOLDOWNS[sim.ENTRENAR])
    assert economia.usar_objeto("evento-uso-54", U, G, SILBATO, T0).motivo == "no_hace_falta"
    assert db.inventario(U, G) == {"silbato": 1}

    db.poner_cooldown(kuro.id, sim.ENTRENAR, T0)
    con_espera = economia.usar_objeto("evento-uso-55", U, G, SILBATO, T0)
    assert con_espera.ok and con_espera.efecto == "reinicia"
    assert db.espera_de(kuro.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.inventario(U, G) == {}


def test_un_ticket_que_no_alargaria_no_se_gasta(base):
    nace()
    dar(U, "ticket_refugio", 1)
    # Sin estancia empezada, la que se le supone ya llega a ahora + 7 días; y
    # mirarla para decir que no tampoco se la empieza.
    sin_empezar = economia.usar_objeto("evento-uso-56", U, G, TICKET, T0)
    assert (sin_empezar.motivo, sin_empezar.efecto) == ("no_hace_falta", "refugio")
    with db.conectar() as con:
        assert not db._hay_hogar(con, U, G)

    db.hogar_de(U, G, T0)                           # recién empezada: hasta T0 + 7 días
    recien = economia.usar_objeto("evento-uso-57", U, G, TICKET, T0)
    assert (recien.ok, recien.motivo, recien.efecto) == (False, "no_hace_falta", "refugio")
    assert db.inventario(U, G) == {"ticket_refugio": 1}

    a_la_mitad = T0 + timedelta(days=3, hours=12)
    # Sin comer no llegaría vivo a la mitad de la estancia: come a los dos días.
    hambrear(db.avanzar(db.criatura_activa(U, G), T0 + timedelta(days=2)), 100)
    usado = economia.usar_objeto("evento-uso-58", U, G, TICKET, a_la_mitad)
    assert usado.ok and usado.refugio_hasta == a_la_mitad + timedelta(days=7)
    assert db.hogar_leido(U, G, a_la_mitad).refugio_hasta == a_la_mitad + timedelta(days=7)
    assert db.inventario(U, G) == {}


def test_las_pociones_y_las_sopaipillas_siempre_se_usan(base):
    """Ponen su efecto o lo renuevan: con todo lleno y sin esperas, también."""
    nace()
    pocion = obj.CATALOGO["fuerza_1d4"]
    sopaipilla = obj.CATALOGO[hue.clave_de_sopaipilla("rojo")]
    dar(U, pocion.clave, 2)
    dar(U, sopaipilla.clave, 2)

    for vez in (1, 2):                              # la segunda, renovando
        assert economia.usar_objeto(
            f"evento-uso-6{vez}", U, G, pocion, T0, random.Random(7)
        ).ok
        assert economia.usar_objeto(
            f"evento-uso-7{vez}", U, G, sopaipilla, T0, random.Random(7)
        ).ok
    assert db.inventario(U, G) == {}
