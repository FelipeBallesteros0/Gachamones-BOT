"""El hogar: que nadie duerma en la calle de entrada y que la casa cuadre."""
import re
from datetime import datetime, timedelta, timezone

import pytest

import casas as cas
import cogs.social as social
import db
import economia
import jardin
import simulacion as sim
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
ANSI = re.compile(r"\x1b\[[0-9;]*m")
PEQUENA = cas.CATALOGO["pequena"]
MEDIANA = cas.CATALOGO["mediana"]
GRANDE = cas.CATALOGO["grande"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "casas.db")
    db.inicializar()


def nacer(nombre="Kuro", activa=True, usuario="u1", especie="pulpo"):
    return db.crear(usuario, "g1", especie, nombre, STATS, T0, activa=activa)


def con_monedas(cuantas, usuario="u1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? "
            "AND guild_id = 'g1'",
            (cuantas, usuario),
        )


def monedas(usuario="u1"):
    return economia.saldos(usuario, "g1").asciicoins


def hogar(usuario="u1", ahora=T0):
    return db.hogar_de(usuario, "g1", ahora)


def un_hogar(casa=None, ahora=T0, puestos=(), id_=1):
    """Un hogar con **una sola casa**, que es el caso de casi todos los tests.

    Desde que se pueden tener varias, `Hogar` lleva una tupla de `CasaPropia` y
    ya no una `Casa` suelta; esto evita repetir el envoltorio en cada test.
    `casa` a `None` es no tener ninguna: refugio o intemperie según `ahora`.
    """
    casas = () if casa is None else (cas.CasaPropia(id_, casa, tuple(puestos)),)
    return cas.Hogar(casas=casas, refugio_hasta=ahora)


def la_casa_de(usuario="u1", ahora=T0):
    """La primera casa de alguien, o `None`. Sustituye al viejo `hogar().casa`."""
    casas = db.hogar_de(usuario, "g1", ahora).casas
    return casas[0].casa if casas else None


# --- Nadie en la calle -----------------------------------------------------

def test_nadie_se_queda_sin_hogar():
    """Lo pedido: quien nunca ha mirado su casa no está en la calle, está en el
    refugio y con la semana entera por delante."""
    suyo = hogar()

    assert not suyo.casas
    assert suyo.estado(T0) == cas.REFUGIO
    assert suyo.refugio_hasta == T0 + timedelta(days=cas.DIAS_DE_REFUGIO)


def test_la_semana_empieza_al_mirar_y_no_al_desplegar():
    """Por eso la fila se crea perezosamente: quien aparezca dentro de un mes se
    encuentra su semana entera, no gastada esperándole."""
    tarde = T0 + timedelta(days=30)
    suyo = hogar(ahora=tarde)

    assert suyo.estado(tarde) == cas.REFUGIO
    assert suyo.refugio_hasta == tarde + timedelta(days=cas.DIAS_DE_REFUGIO)


def test_la_estancia_no_se_reinicia_al_volver_a_mirar():
    primero = hogar()
    despues = hogar(ahora=T0 + timedelta(days=3))

    assert despues.refugio_hasta == primero.refugio_hasta


def test_al_acabarse_la_estancia_se_queda_a_la_intemperie():
    suyo = hogar()
    assert suyo.estado(suyo.refugio_hasta + timedelta(seconds=1)) == cas.INTEMPERIE
    assert suyo.comodidad_de(1, suyo.refugio_hasta + timedelta(seconds=1)) == 0


def test_el_hogar_es_de_cada_persona_y_servidor():
    db.hogar_de("u1", "g1", T0)
    assert db.hogar_de("u2", "g1", T0).casas == ()
    assert db.hogar_de("u1", "g2", T0).casas == ()


# --- Comprar y mudarse -----------------------------------------------------

def test_comprar_cobra_y_te_muda():
    nacer()
    con_monedas(1000)

    resultado = economia.comprar_casa("u1", "g1", MEDIANA, T0)

    assert resultado.ok
    assert resultado.casa == MEDIANA
    assert resultado.desde is None            # venía del refugio
    assert monedas() == 1000 - MEDIANA.precio
    assert la_casa_de() == MEDIANA
    assert hogar().estado(T0) == cas.PROPIA


def test_mejorar_a_una_igual_o_peor_no_cobra_ni_cambia_nada():
    """El mismo cerrojo que el doble clic del ropero. Ahora se aplica a **una
    casa concreta**: comprar una pequeña teniendo una grande ya no es un error,
    es comprarse otra casa; lo que no se puede es *mejorar* hacia abajo."""
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", GRANDE, T0)
    suya = id_de_la_casa()
    saldo = monedas()

    for casa in (PEQUENA, MEDIANA, GRANDE):
        resultado = economia.comprar_casa("u1", "g1", casa, T0, mejorar=suya)
        assert not resultado.ok, casa.clave
        assert "no se puede empeorar" in resultado.problema

    assert monedas() == saldo
    assert la_casa_de() == GRANDE


def test_mejorar_dice_de_donde_vienes_y_cuesta_la_diferencia():
    """Mejorar cobra sólo lo que va de una a otra: al precio entero saldría más
    caro que vender y comprar, y no mejoraría nadie."""
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", PEQUENA, T0)
    suya = id_de_la_casa()

    resultado = economia.comprar_casa("u1", "g1", GRANDE, T0, mejorar=suya)

    assert resultado.ok and resultado.desde == PEQUENA
    assert resultado.casa_id == suya, "mejorar conserva la casa, no crea otra"
    cuesta = GRANDE.precio - cas.lo_que_dan_por(PEQUENA)
    assert monedas() == 3000 - PEQUENA.precio - cuesta


def test_sin_monedas_suficientes_no_se_muda_nadie():
    con_monedas(PEQUENA.precio - 1)

    resultado = economia.comprar_casa("u1", "g1", PEQUENA, T0)

    assert not resultado.ok
    assert "faltan 1 asciicoins" in resultado.problema
    assert monedas() == PEQUENA.precio - 1
    assert la_casa_de() is None


def test_el_saldo_nunca_se_queda_en_negativo():
    con_monedas(0)
    for _ in range(3):
        assert not economia.comprar_casa("u1", "g1", PEQUENA, T0).ok
    assert monedas() == 0


def test_una_casa_que_no_es_del_catalogo_no_se_cuela():
    con_monedas(3000)
    falsa = cas.Casa("pequena", "Chabola", 0, 999, 99, 999, 3, 9)

    with pytest.raises(ValueError):
        economia.comprar_casa("u1", "g1", falsa, T0)
    assert monedas() == 3000


def test_el_refugio_no_se_compra():
    """No está en el catálogo a propósito: es donde se empieza, no un producto."""
    assert cas.REFUGIO not in cas.CATALOGO
    assert cas.EL_REFUGIO.precio == 0


# --- Los números del catálogo ----------------------------------------------

def test_comprar_siempre_sube_de_comodidad():
    """Es lo que hace que valga la pena mudarse: la casa más humilde tiene que
    superar al refugio, o comprar sería un castigo."""
    for casa in cas.CATALOGO.values():
        assert casa.comodidad > cas.EL_REFUGIO.comodidad, casa.clave


def test_el_techo_sube_con_el_tamano():
    """Con un techo común, la casa grande desperdiciaría siete de sus diez
    huecos: comprarla sólo valdría para mirarla."""
    por_tamano = sorted(cas.CATALOGO.values(), key=lambda c: c.tamano)
    for menor, mayor in zip(por_tamano, por_tamano[1:]):
        assert mayor.techo > menor.techo
        assert mayor.huecos > menor.huecos
        assert mayor.precio > menor.precio
        assert mayor.comodidad > menor.comodidad


def test_el_techo_de_cada_casa_es_alcanzable_amueblandola_entera():
    """Un techo al que no se puede llegar es un número que miente.

    Ata el catálogo con el presupuesto de mobiliario de la entrega 2: si alguien
    sube un techo o baja los huecos sin tocar `MAX_COMODIDAD_POR_MUEBLE`, esto
    avisa. Y el margen tiene que existir: llegar al techo nada más comprar
    dejaría los huecos sin sentido.
    """
    for casa in cas.CATALOGO.values():
        margen = casa.techo - casa.comodidad
        assert margen > 0, casa.clave
        assert margen <= casa.huecos * cas.MAX_COMODIDAD_POR_MUEBLE, casa.clave


# --- El dibujo -------------------------------------------------------------

def _sin_color(texto):
    return [l for l in ANSI.sub("", texto).splitlines() if not l.startswith("```")]


# Aquí vivían los tests del tejado y del marco de la casa. Se fueron con el
# dibujo: `/casa` lista y ya no dibuja, porque con veinticinco gachamones
# repartidos en tres casas el cuadro medía 3847 caracteres y Discord admite
# 2000. El arte ASCII de la ficha, del jardín y de las competencias sigue con
# sus tests intactos, que es donde sigue habiendo arte.


def _criatura(i):
    especies = ("pulpo", "michi", "pollito", "brote", "slime",
                "pedrusco", "chispa", "fantasma", "chatarra", "dragoncito")
    return sim.Criatura(
        id=i + 1, usuario_id="u1", guild_id="g1", especie=especies[i % 10],
        nombre=f"Bicho{i}", nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )


def test_la_casa_cabe_en_un_mensaje_de_discord():
    """Con diez el jardín ya mide más de mil caracteres; el tejado y el suelo
    tienen que dejarlo por debajo del tope de Discord."""
    texto = social.texto_de_la_casa(
        un_hogar(GRANDE, T0), [_criatura(i) for i in range(10)], "Felipe", T0
    )
    assert len(texto) < 2000


# --- Lo que se ve ----------------------------------------------------------

def test_la_casa_dibuja_a_todos_los_vivos_y_no_solo_al_activo():
    """Lo pedido: `/casa` enseña el plantel entero, no la ficha del activo."""
    nacer("Activo")
    nacer("Reserva", activa=False)
    muerto = nacer("Muerto", activa=False)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET muerta_en = ?, causa_muerte = 'hambre' "
            "WHERE id = ?", (T0.isoformat(), muerto.id),
        )

    texto = social.texto_de_la_casa(hogar(), db.plantel("u1", "g1"), "Felipe", T0)

    assert "Activo" in texto and "Reserva" in texto
    assert "Muerto" not in texto


def test_el_refugio_dice_cuanto_queda_y_la_intemperie_que_se_acabo():
    suyo = hogar()
    en_refugio = social.texto_de_la_casa(suyo, [], "Felipe", T0)
    fuera = social.texto_de_la_casa(
        suyo, [], "Felipe", suyo.refugio_hasta + timedelta(days=1)
    )

    assert "refugio" in en_refugio and "días de estancia" in en_refugio
    assert "intemperie" in fuera and "Se acabó" in fuera


def test_la_comodidad_se_enseña_sin_porcentaje():
    """Deja de ser un porcentaje al subir los techos por encima de 100: quien
    viera «118 %» pensaría que hay un fallo."""
    texto = social.texto_de_la_casa(un_hogar(GRANDE, T0), [], "Felipe", T0)
    assert f"**{GRANDE.comodidad}**/{GRANDE.techo}" in texto
    assert "%" not in texto


def test_la_mudanza_se_canta_diciendo_de_donde_vienes():
    con_monedas(3000)
    del_refugio = economia.comprar_casa("u1", "g1", PEQUENA, T0)
    subiendo = economia.comprar_casa(
        "u1", "g1", GRANDE, T0, mejorar=id_de_la_casa()
    )

    assert "se trasladó del refugio a su nueva **Casa pequeña**" in (
        tienda.texto_de_la_mudanza("Felipe", del_refugio)
    )
    assert "de Casa pequeña a su nueva **Casa grande**" in (
        tienda.texto_de_la_mudanza("Felipe", subiendo)
    )


# --- La tienda -------------------------------------------------------------

def test_la_tienda_sigue_cabiendo_en_los_limites_con_las_casas():
    """Tres desplegables, uno por fila: Discord admite cinco filas y cada lista
    no puede pasar de 25 opciones."""
    import cosmeticos as cos
    import objetos as obj

    menus = (tienda.MenuTienda(), tienda.MenuCosmeticos(), tienda.MenuCasas())
    vista = tienda.VistaConMenu(*menus)

    assert len(vista.children) == 3 <= 5
    for menu in menus:
        assert 1 <= len(menu.options) <= 25
    assert len(obj.CATALOGO) + len(cos.CATALOGO) + len(cas.CATALOGO) > 25


def test_el_desplegable_ofrece_mejorar_comprar_y_vender():
    """Las tres cosas que se pueden hacer con las casas, en un solo menú: son la
    misma decisión y separarlas obligaría a adivinar en cuál de tres está."""
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", MEDIANA, T0)
    suya = id_de_la_casa()

    opciones = tienda.MenuCasas(hogar()).options
    por_valor = {o.value: o.label for o in opciones}

    # Mejorar sólo a lo que es mayor, y diciendo lo que cuesta la diferencia.
    assert f"mejorar:{suya}:grande" in por_valor
    assert f"mejorar:{suya}:pequena" not in por_valor
    assert f"mejorar:{suya}:mediana" not in por_valor
    # Comprar otra sigue estando, porque aún no llega al tope.
    assert f"🪙 {GRANDE.precio}" in por_valor["comprar:grande"]
    assert f"vender:{suya}" in por_valor


# --- Los muebles -----------------------------------------------------------

FELPUDO = cas.MUEBLES["felpudo"]
CHIMENEA = cas.MUEBLES["chimenea"]
CAMA = cas.MUEBLES["cama"]


def con_casa(clave="grande", monedas=9000):
    con_monedas(monedas)
    economia.comprar_casa("u1", "g1", cas.CATALOGO[clave], T0)


def comprar_m(mueble=CHIMENEA):
    return economia.comprar_mueble("u1", "g1", mueble, T0)


def mejores(cuantos):
    return sorted(cas.MUEBLES.values(), key=lambda m: -m.comodidad)[:cuantos]


def test_cada_casa_alcanza_su_techo_amueblandola_con_lo_mejor():
    """El invariante de fondo del catálogo: un techo al que no se llega es un
    número que miente, y unos huecos que sobran son una casa que no compensa.

    Se calcula del catálogo de verdad y no de `MAX_COMODIDAD_POR_MUEBLE`, que es
    sólo la cota: si alguien abarata un mueble o sube un techo, esto avisa.
    """
    for casa in cas.CATALOGO.values():
        puestos = [m.clave for m in mejores(casa.huecos)]
        assert cas.comodidad_de(casa, puestos) == casa.techo, casa.clave


def test_ningun_mueble_pasa_del_tope():
    for mueble in cas.MUEBLES.values():
        assert 0 < mueble.comodidad <= cas.MAX_COMODIDAD_POR_MUEBLE, mueble.clave
        assert mueble.precio > 0, mueble.clave


def test_hay_muebles_de_sobra_para_la_casa_grande():
    """Uno de cada, así que el catálogo tiene que dar para llenar la mayor."""
    assert len(cas.MUEBLES) >= max(c.huecos for c in cas.CATALOGO.values())


def test_la_comodidad_nunca_pasa_del_techo():
    todos = [m.clave for m in cas.MUEBLES.values()]
    for casa in cas.CATALOGO.values():
        assert cas.comodidad_de(casa, todos) == casa.techo


def test_un_mueble_retirado_del_catalogo_no_sigue_sumando():
    """Si algún día se quita uno, quien lo tuviera puesto no puede quedarse con
    una comodidad que ya no se puede volver a conseguir."""
    assert cas.comodidad_de(PEQUENA, ["mueble_fantasma"]) == PEQUENA.comodidad


def test_comprar_un_mueble_cobra_y_lo_coloca_si_cabe():
    con_casa("pequena")
    saldo = monedas()

    resultado = comprar_m(CHIMENEA)

    assert resultado.ok
    assert monedas() == saldo - CHIMENEA.precio
    assert db.mobiliario("u1", "g1") == {"chimenea": True}
    assert resultado.comodidad == PEQUENA.comodidad + CHIMENEA.comodidad
    assert resultado.puestos == 1


def test_el_mueble_que_no_cabe_se_guarda_en_vez_de_perderse():
    con_casa("pequena")
    for mueble in mejores(PEQUENA.huecos):
        comprar_m(mueble)

    resultado = comprar_m(FELPUDO)

    assert resultado.ok
    assert db.mobiliario("u1", "g1")["felpudo"] is False
    assert resultado.puestos == PEQUENA.huecos


def test_comprar_el_mismo_mueble_dos_veces_no_cuesta_nada():
    """Uno de cada, como el ropero: repetir la chimenea no significaría nada, y
    llegar al techo comprando cuatro veces el mueble más caro dejaría el
    catálogo sin sentido."""
    con_casa()
    comprar_m(CHIMENEA)
    saldo = monedas()

    repetida = comprar_m(CHIMENEA)

    assert not repetida.ok
    assert "Ya tienes" in repetida.problema
    assert monedas() == saldo


def test_en_el_refugio_no_se_puede_amueblar():
    """Es común y no es tuyo. Y no cobra: comprar sin sitio sería una faena."""
    con_monedas(9000)

    resultado = comprar_m(CHIMENEA)

    assert not resultado.ok
    assert "refugio no se puede amueblar" in resultado.problema
    assert monedas() == 9000
    assert db.mobiliario("u1", "g1") == {}


def test_a_la_intemperie_tampoco():
    con_monedas(9000)
    fuera = hogar().refugio_hasta + timedelta(days=1)

    resultado = economia.comprar_mueble("u1", "g1", CHIMENEA, fuera)

    assert not resultado.ok
    assert "intemperie" in resultado.problema
    assert monedas() == 9000


def test_sin_monedas_no_se_compra_mueble():
    con_casa("pequena", monedas=PEQUENA.precio + CHIMENEA.precio - 1)

    resultado = comprar_m(CHIMENEA)

    assert not resultado.ok
    assert "faltan 1 asciicoins" in resultado.problema
    assert db.mobiliario("u1", "g1") == {}


def test_retirar_un_mueble_no_lo_pierde_y_baja_la_comodidad():
    """La misma regla que el ropero: lo que quitas se guarda."""
    con_casa("pequena")
    comprar_m(CHIMENEA)
    saldo = monedas()

    retirado = economia.retirar_mueble("u1", "g1", CHIMENEA, T0)

    assert retirado.ok
    assert retirado.comodidad == PEQUENA.comodidad
    assert db.mobiliario("u1", "g1") == {"chimenea": False}

    vuelta = economia.colocar_mueble("u1", "g1", CHIMENEA, T0)

    assert vuelta.ok
    assert vuelta.comodidad == PEQUENA.comodidad + CHIMENEA.comodidad
    assert monedas() == saldo          # volver a ponerlo es gratis


def test_no_se_puede_colocar_mas_de_lo_que_caben():
    con_casa("pequena")
    for mueble in mejores(PEQUENA.huecos):
        comprar_m(mueble)
    comprar_m(FELPUDO)                 # se guarda: no cabía

    resultado = economia.colocar_mueble("u1", "g1", FELPUDO, T0)

    assert not resultado.ok
    assert "No cabe" in resultado.problema and str(PEQUENA.huecos) in resultado.problema


def test_al_mejorar_a_una_mayor_caben_los_que_estaban_guardados():
    """Lo que hace que subir de casa valga para algo más que el número."""
    con_casa("pequena")
    for mueble in mejores(PEQUENA.huecos):
        comprar_m(mueble)
    comprar_m(FELPUDO)
    assert not economia.colocar_mueble("u1", "g1", FELPUDO, T0).ok

    economia.comprar_casa("u1", "g1", MEDIANA, T0, mejorar=id_de_la_casa())
    resultado = economia.colocar_mueble("u1", "g1", FELPUDO, T0)

    assert resultado.ok
    assert resultado.puestos == PEQUENA.huecos + 1


def test_no_se_coloca_ni_se_retira_lo_que_no_toca():
    con_casa()
    comprar_m(CHIMENEA)

    assert "No tienes" in economia.colocar_mueble("u1", "g1", CAMA, T0).problema
    assert "ya está puesto" in economia.colocar_mueble("u1", "g1", CHIMENEA, T0).problema
    assert "no está puesto" in economia.retirar_mueble("u1", "g1", CAMA, T0).problema


def test_un_mueble_que_no_es_del_catalogo_no_se_cuela():
    con_casa()
    falso = cas.Mueble("chimenea", "Chimenea de mentira", "🔥", 0, 99)

    for operacion in (
        economia.comprar_mueble, economia.colocar_mueble, economia.retirar_mueble
    ):
        with pytest.raises(ValueError):
            operacion("u1", "g1", falso, T0)


def test_el_mobiliario_es_de_cada_persona_y_servidor():
    con_casa()
    comprar_m(CHIMENEA)

    assert db.mobiliario("u2", "g1") == {}
    assert db.mobiliario("u1", "g2") == {}


# --- Lo que se ve de los muebles -------------------------------------------

def test_la_casa_enseña_la_comodidad_real_y_los_muebles():
    con_casa("pequena")
    comprar_m(CHIMENEA)

    texto = social.texto_de_la_casa(hogar(), [], "Felipe", T0)

    assert f"**{PEQUENA.comodidad + CHIMENEA.comodidad}**/{PEQUENA.techo}" in texto
    assert f"1/{PEQUENA.huecos} huecos" in texto
    assert CHIMENEA.emoji in texto


def test_la_casa_con_el_plantel_entero_cabe_en_discord():
    """El peor caso de verdad, y el motivo de que `/casa` deje de dibujar: con
    el plantel lleno el cuadro medía 3847 caracteres y Discord admite 2000."""
    todos = [_criatura(i) for i in range(db.MAXIMO_PLANTEL)]
    texto = social.texto_de_la_casa(
        un_hogar(GRANDE, T0, tuple(m.clave for m in mejores(GRANDE.huecos))),
        todos, "Felipe", T0,
    )
    assert len(texto) < 2000, len(texto)
    # Y con el plantel repartido en tres casas, que es cuando más cabeceras hay.
    hogar_lleno = cas.Hogar(
        casas=tuple(
            cas.CasaPropia(i + 1, GRANDE, tuple(m.clave for m in mejores(10)))
            for i in range(cas.MAXIMO_CASAS)
        ),
        refugio_hasta=T0,
    )
    from dataclasses import replace
    repartidos = [
        replace(c, casa_id=(i % (cas.MAXIMO_CASAS + 1)) or None)
        for i, c in enumerate(todos)
    ]
    texto = social.texto_de_la_casa(hogar_lleno, repartidos, "Felipe", T0)
    assert len(texto) < 2000, len(texto)


def test_amueblar_en_el_refugio_lo_dice_y_no_ofrece_menu():
    assert "refugio no se puede amueblar" in tienda.texto_de_amueblar(
        "u1", "g1", T0
    )


def test_amueblar_cuenta_lo_puesto_y_lo_guardado():
    con_casa("pequena")
    for mueble in mejores(PEQUENA.huecos):
        comprar_m(mueble)
    comprar_m(FELPUDO)

    texto = tienda.texto_de_amueblar("u1", "g1", T0)

    assert f"{PEQUENA.huecos}/{PEQUENA.huecos} huecos" in texto
    assert "Guardados: **1**" in texto
    assert "no se pierde" in texto


def test_los_menus_de_amueblar_separan_lo_puesto_de_lo_guardado():
    mobiliario = {"chimenea": True, "felpudo": False, "cama": False}

    colocar = tienda.MenuColocarMueble(mobiliario)
    retirar = tienda.MenuRetirarMueble(mobiliario)

    assert {o.value for o in colocar.options} == {"felpudo", "cama"}
    assert {o.value for o in retirar.options} == {"chimenea"}


def test_la_tienda_sigue_cabiendo_con_los_cuatro_desplegables():
    menus = (
        tienda.MenuTienda(), tienda.MenuCosmeticos(),
        tienda.MenuCasas(), tienda.MenuMuebles(),
    )
    vista = tienda.VistaConMenu(*menus)

    assert len(vista.children) == 4 <= 5
    for menu in menus:
        assert 1 <= len(menu.options) <= 25


# --- Lo que el hogar le hace al gachamon -----------------------------------

def _viva(hambre=100.0, animo=100.0, limpieza=100.0, activa=True):
    return sim.Criatura(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Kuro",
        nacida_en=T0, actualizada_en=T0, base_fuerza=15, base_velocidad=15,
        base_salud=15, hambre=hambre, animo=animo, limpieza=limpieza,
        activa=activa,
    )


def _tras(horas, ritmo=sim.RITMO_BAJO_TECHO, **estado):
    return sim.avanzar(_viva(**estado), T0 + timedelta(hours=horas), ritmo)


def test_bajo_techo_el_tiempo_pasa_como_siempre():
    """El ritmo por defecto **es** el de quien tiene techo: quien olvide pasarlo
    se queda con el comportamiento de antes y nunca con uno peor."""
    hogar = un_hogar(None, T0 + timedelta(days=1))       # refugio
    assert cas.ritmo_de(hogar, T0) == sim.Ritmo()
    assert _tras(10, cas.ritmo_de(hogar, T0)) == _tras(10)


def test_a_la_intemperie_todo_cae_un_cuarto_mas_rapido():
    fuera = cas.ritmo_de(un_hogar(None, T0), T0 + timedelta(days=1), 1)

    normal, crudo = _tras(10), _tras(10, fuera)

    for barra in ("hambre", "animo", "limpieza"):
        perdido_normal = 100.0 - getattr(normal, barra)
        perdido_fuera = 100.0 - getattr(crudo, barra)
        assert perdido_fuera == pytest.approx(perdido_normal * 1.25), barra


def test_la_intemperie_no_puede_matar():
    """Lo decidido: acelera, pero nadie pierde un gachamon para siempre por no
    haber comprado casa. Ni en un mes a la intemperie."""
    fuera = cas.ritmo_de(un_hogar(None, T0), T0 + timedelta(days=1), 1)

    tras_un_mes = _tras(24 * 30, fuera, hambre=30.0)

    assert tras_un_mes.viva
    assert tras_un_mes.hambre == cas.SUELO_DE_HAMBRE_A_LA_INTEMPERIE
    assert tras_un_mes.muerta_en is None


def test_el_suelo_deja_margen_para_mudarse_sin_morirse():
    """Quien por fin compre casa no puede encontrarse con que su gachamon se
    muere a los dos minutos: el suelo tiene que quedar por encima del aviso."""
    assert cas.SUELO_DE_HAMBRE_A_LA_INTEMPERIE > sim.UMBRAL_AVISO_HAMBRE


def test_bajo_techo_el_hambre_sigue_matando():
    """El suelo es sólo de la intemperie: la muerte por hambre sigue existiendo
    para quien tiene casa, que es como ha sido siempre."""
    muerta = _tras(24 * 5, hambre=10.0)
    assert not muerta.viva and muerta.causa_muerte == "hambre"


def test_la_comodidad_frena_el_animo_hasta_un_cuarto():
    """Simétrico al castigo de la intemperie, para poder contarlo en una frase."""
    assert cas.alivio_de_animo(cas.EL_REFUGIO.comodidad) == 1.0
    assert cas.alivio_de_animo(GRANDE.techo) == 1.0 - cas.ALIVIO_MAXIMO_DE_ANIMO
    # Y por debajo del refugio no premia, que sería al revés de lo que toca.
    assert cas.alivio_de_animo(0) == 1.0


def test_la_mejor_casa_conserva_mas_animo_que_el_refugio():
    mejor = un_hogar(GRANDE, T0, tuple(m.clave for m in mejores(GRANDE.huecos)))
    refugio = un_hogar(None, T0 + timedelta(days=1))

    en_casa = _tras(24, cas.ritmo_de(mejor, T0, 1))
    en_refugio = _tras(24, cas.ritmo_de(refugio, T0))

    assert en_casa.animo > en_refugio.animo
    # Y el hambre no la toca la comodidad: `muere_en` va precalculado en la base
    # y dejaría de ser cierto en cuanto alguien se mudara.
    assert en_casa.hambre == en_refugio.hambre


def test_los_muebles_cuentan_para_el_ritmo():
    vacia = un_hogar(GRANDE, T0)
    llena = un_hogar(GRANDE, T0, tuple(m.clave for m in mejores(GRANDE.huecos)))

    assert cas.ritmo_de(llena, T0, 1).animo < cas.ritmo_de(vacia, T0, 1).animo


def test_las_de_la_incubadora_siguen_congeladas_vivan_donde_vivan():
    """El invariante que no se toca: si las de reserva decayeran, con diez por
    persona se morirían hiciera lo que hiciera su dueño."""
    fuera = cas.ritmo_de(un_hogar(None, T0), T0 + timedelta(days=1), 1)
    guardada = _viva(activa=False)

    assert sim.avanzar(guardada, T0 + timedelta(days=30), fuera) == guardada


def test_avanzar_mira_el_hogar_de_quien_sea_la_criatura():
    """De punta a punta: nadie pasa el ritmo a mano, sale de la base."""
    from dataclasses import replace

    nacer()
    bicho = db.criatura_activa("u1", "g1")
    fin = db.hogar_de("u1", "g1", T0).refugio_hasta

    dentro = db.avanzar(bicho, T0 + timedelta(hours=1))
    # El mismo, con el reloj puesto justo cuando se le acaba el refugio: una
    # hora dentro contra una hora fuera, que es lo comparable. Medido sobre
    # varios días, el ánimo toca fondo en cero y la media miente.
    fuera = db.avanzar(
        replace(bicho, actualizada_en=fin), fin + timedelta(hours=1)
    )

    assert (100.0 - fuera.animo) == pytest.approx(
        (100.0 - dentro.animo) * cas.PENALIZACION_INTEMPERIE
    )


def test_mirar_la_ficha_de_otro_no_le_estrena_el_refugio():
    """`avanzar` es de sólo lectura: coger el cerrojo de escritura en cada ficha
    sería caro, y estrenarle la estancia a otro por mirarle el gachamon, injusto."""
    nacer(usuario="u2")
    ajena = db.criatura_activa("u2", "g1")

    db.avanzar(ajena, T0 + timedelta(hours=1))

    with db.conectar() as con:
        assert not db._hay_hogar(con, "u2", "g1")


# --- El ticket del refugio -------------------------------------------------

TICKET = __import__("objetos").CATALOGO["ticket_refugio"]


def test_el_ticket_devuelve_una_estancia_entera():
    nacer()
    bicho = db.criatura_activa("u1", "g1")
    fuera = hogar().refugio_hasta + timedelta(days=1)
    assert hogar().estado(fuera) == cas.INTEMPERIE

    aviso = tienda.usar(bicho, TICKET, fuera)

    assert "refugio" in aviso
    assert db.hogar_de("u1", "g1", fuera).estado(fuera) == cas.REFUGIO


def test_el_ticket_cuenta_desde_que_se_usa():
    """Y el aviso lo dice: usarlo con estancia de sobra es tirarlo."""
    nacer()
    bicho = db.criatura_activa("u1", "g1")
    db.hogar_de("u1", "g1", T0)

    aviso = tienda.usar(bicho, TICKET, T0 + timedelta(days=1))

    assert "lo has perdido" in aviso
    assert db.hogar_de("u1", "g1", T0).refugio_hasta == (
        T0 + timedelta(days=1 + TICKET.dias_de_refugio)
    )


def test_el_ticket_se_puede_usar_desde_la_mochila():
    """Si no, se gastaría la unidad sin hacer nada: es justo lo que comprueba el
    menú antes de gastarla."""
    assert TICKET.se_usa_en_mochila and TICKET.se_aplica_al_momento


def test_el_ticket_sale_mas_caro_que_comprar_casa_a_la_larga():
    """Es una red de seguridad, no una alternativa: quien lo use cada semana
    gasta más que la casa pequeña en dos meses y sigue sin poder amueblar."""
    ocho_semanas = TICKET.precio * 8
    assert ocho_semanas > PEQUENA.precio


# --- Visitar y el buzón ----------------------------------------------------

import objetos as objs   # noqa: E402  (al final, junto a lo que lo usa)

GOLOSINAS = objs.CATALOGO["golosinas"]
PLACA = objs.CATALOGO["placa"]


def test_la_casa_nace_abierta_a_visitas():
    """Como todo lo demás del bot: `/mascota @alguien` y `/jardin` ya enseñan lo
    de cualquiera sin preguntar."""
    assert hogar().publica


def test_se_puede_cerrar_y_volver_a_abrir():
    db.abrir_o_cerrar_la_casa("u1", "g1", False, T0)
    assert not hogar().publica

    db.abrir_o_cerrar_la_casa("u1", "g1", True, T0)
    assert hogar().publica


def test_cerrar_la_casa_no_la_toca_por_dentro():
    con_casa("mediana")
    comprar_m(CHIMENEA)
    db.abrir_o_cerrar_la_casa("u1", "g1", False, T0)

    suyo = hogar()
    assert [c.casa for c in suyo.casas] == [MEDIANA]
    assert suyo.casas[0].puestos == ("chimenea",)


def test_mirar_la_casa_de_otro_no_le_estrena_el_refugio():
    """`/visitar` sólo mira: no puede empezarle a nadie su semana."""
    db.hogar_leido("u2", "g1", T0)

    with db.conectar() as con:
        assert not db._hay_hogar(con, "u2", "g1")


def test_el_regalo_sale_de_tu_mochila_y_llega_a_su_buzon():
    db.regalar("u1", "g1", GOLOSINAS)

    assert db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "toma", T0
    )

    assert db.inventario("u1", "g1") == {}
    assert db.inventario("u2", "g1") == {}          # todavía en el buzón
    [regalo] = db.buzon_de("u2", "g1")
    assert regalo.objeto == GOLOSINAS.clave
    assert regalo.de_nombre == "Felipe" and regalo.nota == "toma"


def test_no_se_puede_regalar_lo_que_no_tienes():
    """Las dos mitades van juntas: un objeto que saliera de una mochila sin
    llegar a ningún buzón se habría perdido."""
    assert not db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0
    )
    assert db.buzon_de("u2", "g1") == []


def test_recoger_lo_pasa_a_la_mochila_y_vacia_el_buzon():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    recogido = db.recoger_del_buzon("u2", "g1", regalo.id)

    assert recogido is not None and recogido.objeto == GOLOSINAS.clave
    assert db.inventario("u2", "g1") == {GOLOSINAS.clave: 1}
    assert db.buzon_de("u2", "g1") == []


def test_el_mismo_regalo_no_se_recoge_dos_veces():
    """El doble clic: la condición viaja dentro del UPDATE, como en las compras."""
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    assert db.recoger_del_buzon("u2", "g1", regalo.id) is not None
    assert db.recoger_del_buzon("u2", "g1", regalo.id) is None
    assert db.inventario("u2", "g1") == {GOLOSINAS.clave: 1}


def test_no_se_recoge_el_regalo_de_otro():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)
    [regalo] = db.buzon_de("u2", "g1")

    assert db.recoger_del_buzon("u3", "g1", regalo.id) is None
    assert len(db.buzon_de("u2", "g1")) == 1


def test_la_nota_es_opcional_y_cabe_en_una_linea():
    """Una nota con saltos rompería el listado, que pinta un regalo por renglón."""
    assert db.limpiar_nota("") == ""
    assert db.limpiar_nota("dos\nlíneas   y   huecos") == "dos líneas y huecos"
    assert len(db.limpiar_nota("x" * 500)) == db.LARGO_MAXIMO_NOTA


def test_el_buzon_es_de_cada_persona_y_servidor():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)

    assert len(db.buzon_de("u2", "g1")) == 1
    assert db.buzon_de("u2", "g2") == []
    assert db.buzon_de("u1", "g1") == []


def test_el_buzon_los_lista_del_mas_viejo_al_mas_nuevo():
    for objeto in (GOLOSINAS, PLACA):
        db.regalar("u1", "g1", objeto)
    db.mandar_regalo("u1", "A", "u2", "g1", GOLOSINAS.clave, "", T0)
    db.mandar_regalo("u1", "B", "u2", "g1", PLACA.clave, "", T0 + timedelta(days=1))

    assert [r.de_nombre for r in db.buzon_de("u2", "g1")] == ["A", "B"]


def test_el_buzon_vacio_lo_dice_y_no_ofrece_menu():
    assert "No te espera nada" in tienda.texto_del_buzon("u1", "g1")


def test_el_buzon_enseña_de_quien_es_y_su_nota():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "para Pyro", T0)

    texto = tienda.texto_del_buzon("u2", "g1")

    assert GOLOSINAS.nombre in texto
    assert "de Felipe" in texto and "«para Pyro»" in texto


def test_un_regalo_sin_nota_no_deja_comillas_vacias():
    db.regalar("u1", "g1", GOLOSINAS)
    db.mandar_regalo("u1", "Felipe", "u2", "g1", GOLOSINAS.clave, "", T0)

    assert "«»" not in tienda.texto_del_buzon("u2", "g1")


def test_el_menu_del_buzon_cabe_en_discord():
    """Con más de veinticinco se recogen por tandas, que es mejor que un menú
    que Discord rechaza entero."""
    for i in range(30):
        db.regalar("u1", "g1", GOLOSINAS)
        db.mandar_regalo("u1", f"Vecino{i}", "u2", "g1", GOLOSINAS.clave, "", T0)

    menu = tienda.MenuBuzon(db.buzon_de("u2", "g1"))

    assert len(menu.options) == 25


# --- El huerto -------------------------------------------------------------

import huerto as hue        # noqa: E402
import random               # noqa: E402

SEMILLA = objs.CATALOGO["semilla"]


def con_huerto(clave="grande", semillas=10):
    con_casa(clave)
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", "semilla", semillas)


def id_de_la_casa(usuario="u1", ahora=T0):
    """El id de su primera casa. Con varias, cada bancal y cada mueble apuntan
    a una en concreto, así que hace falta para casi todo."""
    casas = db.hogar_de(usuario, "g1", ahora).casas
    return casas[0].id if casas else 0


def bancales(usuario="u1", clave="grande"):
    return db.huerto_de(
        usuario, "g1", id_de_la_casa(usuario), hue.bancales_de(clave)
    )


# --- La tabla de gustos ---

def test_cada_caracter_ordena_los_cinco_colores():
    """Es lo que hace que el color importe: sin una lista completa por carácter,
    `caras_de` reventaría con el que faltara."""
    import personalidad as per

    assert set(hue.AFINIDAD) == set(per.CARACTERES)
    for caracter, orden in hue.AFINIDAD.items():
        assert set(orden) == set(hue.COLORES), caracter
        assert len(orden) == len(set(orden)) == len(hue.COLORES), caracter


def test_los_cinco_dados_se_reparten_uno_por_puesto():
    assert len(hue.CARAS_POR_PUESTO) == len(hue.COLORES)
    assert list(hue.CARAS_POR_PUESTO) == sorted(hue.CARAS_POR_PUESTO, reverse=True)

    for caracter, orden in hue.AFINIDAD.items():
        caras = [hue.caras_de(caracter, color) for color in orden]
        assert caras == list(hue.CARAS_POR_PUESTO), caracter


def test_el_favorito_es_el_dado_mayor_y_el_peor_el_menor():
    for caracter, orden in hue.AFINIDAD.items():
        assert hue.caras_de(caracter, orden[0]) == 12, caracter
        assert hue.caras_de(caracter, orden[-1]) == 4, caracter
        assert "favorito" in hue.le_gusta(caracter, orden[0])
        assert "detesta" in hue.le_gusta(caracter, orden[-1])


def test_a_dos_caracteres_no_les_gusta_lo_mismo_en_el_mismo_orden():
    """Si dos coincidieran, el carácter daría igual para media tabla."""
    ordenes = [tuple(o) for o in hue.AFINIDAD.values()]
    assert len(set(ordenes)) == len(ordenes)


# --- Plantar, regar, cosechar ---

def test_el_refugio_no_tiene_huerto():
    resultado = economia.plantar("u1", "g1", 1, T0)

    assert not resultado.ok
    assert "refugio no tiene huerto" in resultado.problema


def test_los_bancales_los_da_el_tamaño_de_la_casa():
    assert hue.bancales_de(None) == 0
    assert hue.bancales_de(cas.REFUGIO) == 0
    por_tamano = sorted(cas.CATALOGO.values(), key=lambda c: c.tamano)
    cuantos = [hue.bancales_de(c.clave) for c in por_tamano]
    assert cuantos == sorted(cuantos) and cuantos[0] >= 1


def test_plantar_gasta_una_semilla():
    con_huerto(semillas=2)

    resultado = economia.plantar("u1", "g1", 1, T0)

    assert resultado.ok
    assert db.inventario("u1", "g1")["semilla"] == 1
    assert bancales()[0].plantado


def test_sin_semillas_no_se_planta():
    con_huerto(semillas=0)

    resultado = economia.plantar("u1", "g1", 1, T0)

    assert not resultado.ok
    assert objs.CATALOGO[hue.SEMILLA].nombre in resultado.problema
    assert not bancales()[0].plantado


def test_no_se_planta_dos_veces_en_el_mismo_bancal():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    quedan = db.inventario("u1", "g1")["semilla"]

    repetida = economia.plantar("u1", "g1", 1, T0)

    assert not repetida.ok and "ya hay algo" in repetida.problema
    assert db.inventario("u1", "g1")["semilla"] == quedan


def test_no_se_planta_en_un_bancal_que_no_tienes():
    """La casa pequeña tiene uno: el segundo no es suyo aunque exista para otro."""
    con_huerto("pequena")

    resultado = economia.plantar("u1", "g1", 2, T0)

    assert not resultado.ok and "no es tuyo" in resultado.problema


def test_regar_adelanta_la_cosecha():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)

    resultado = economia.regar("u1", "g1", 1, T0 + timedelta(hours=1))

    assert resultado.ok
    listo = bancales()[0].listo_en()
    assert listo == T0 + timedelta(
        hours=hue.HORAS_DE_CULTIVO - hue.HORAS_QUE_AHORRA_REGAR
    )
    assert not bancales()[0].listo(T0 + timedelta(hours=4))
    assert bancales()[0].listo(T0 + timedelta(hours=5))


def test_no_se_riega_dos_veces_ni_lo_que_ya_esta_listo():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    economia.regar("u1", "g1", 1, T0)

    assert "Ya está regado" in economia.regar("u1", "g1", 1, T0).problema

    economia.plantar("u1", "g1", 2, T0)
    tarde = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    assert "Ya está listo" in economia.regar("u1", "g1", 2, tarde).problema


def test_no_se_riega_lo_que_no_esta_plantado():
    con_huerto()
    assert "no hay nada" in economia.regar("u1", "g1", 1, T0).problema


def test_cosechar_da_varios_porotos_y_deja_el_bancal_libre():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)

    resultado = economia.cosechar("u1", "g1", 1, listo, random.Random(1))

    assert resultado.ok
    assert resultado.cosechado in {
        hue.clave_de_poroto(c) for c in hue.COLORES
    }
    # En la mochila entran **exactamente** los que dice el resultado: ni uno
    # suelto, ni el doble por guardar dos veces.
    assert db.inventario("u1", "g1")[resultado.cosechado] == resultado.cuantos
    assert not bancales()[0].plantado


def test_la_cosecha_da_de_dos_a_cuatro():
    """Los números van clavados y no leídos de la constante.

    Deducirlos de `POROTOS_POR_COSECHA` haría el test circular: cambiar la
    constante movería a la vez lo que se comprueba, y nadie se enteraría de que
    el huerto pasó a dar uno o siete.
    """
    assert hue.POROTOS_POR_COSECHA == (2, 4)


def test_la_cosecha_siempre_cae_dentro_del_rango():
    """Y con varias semillas distintas, no con una sola tirada afortunada.

    Se cuenta el lote **entero**, arcoíris incluido: cuando sale uno sustituye a
    un poroto de color en vez de sumarse, así que una cosecha afortunada no
    rinde más que una normal.
    """
    con_huerto(semillas=60)
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    minimo, maximo = hue.POROTOS_POR_COSECHA
    vistos = set()
    for semilla in range(40):
        economia.plantar("u1", "g1", 1, T0)
        recogido = economia.cosechar("u1", "g1", 1, listo, random.Random(semilla))
        cuantos = recogido.cuantos + recogido.arcoiris
        assert minimo <= cuantos <= maximo, cuantos
        vistos.add(cuantos)
    # Y no siempre el mismo número, o el rango sería de adorno.
    assert len(vistos) > 1


def test_los_porotos_de_una_cosecha_son_todos_del_mismo_color():
    """Se tira el color una vez para la mata entera. Se comprueba mirando el
    inventario: si cada poroto tirara el suyo, habría varias claves.

    El arcoíris se apaga a mano en vez de confiar en que la semilla del RNG no
    lo saque: es la única clave más que puede aparecer aquí legítimamente, y
    dejarlo al azar volvería este test un misterio el día que salga.
    """
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)

    resultado = economia.cosechar(
        "u1", "g1", 1, listo, DadosDelHuerto(arcoiris=False, color="rosa")
    )

    porotos = {
        clave: cuantos
        for clave, cuantos in db.inventario("u1", "g1").items()
        if clave.startswith("poroto_")
    }
    assert porotos == {resultado.cosechado: resultado.cuantos}


def test_no_se_cosecha_antes_de_tiempo():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)

    resultado = economia.cosechar("u1", "g1", 1, T0 + timedelta(hours=1))

    assert not resultado.ok and "Todavía no" in resultado.problema
    assert bancales()[0].plantado


def test_el_mensaje_de_la_cosecha_cuenta_y_concuerda():
    """«2 porotos azules», no «2 porotos azuls» ni «2 Poroto azul».

    Los cinco colores no hacen el plural igual —«azul» hace «azules»— y el
    número va delante, así que aquí es donde se rompería sin que fallara nada.
    """
    import tienda

    for color in hue.COLORES:
        clave = hue.clave_de_poroto(color)
        varios = tienda.texto_resultado_huerto(
            economia.ResultadoHuerto(ok=True, bancal=1, cosechado=clave, cuantos=3),
            T0,
        )
        assert f"3 porotos {hue.PLURAL_COLOR[color]}" in varios, varios
        assert "están en tu" in varios

        uno = tienda.texto_resultado_huerto(
            economia.ResultadoHuerto(ok=True, bancal=1, cosechado=clave, cuantos=1),
            T0,
        )
        assert f"un **Poroto {color}**" in uno, uno
        assert "está en tu" in uno


def test_la_semilla_sortea_el_color_al_cosechar_y_no_al_sembrar():
    """La semilla es la única que sortea, y lo hace **al cosechar**: si saliera
    al sembrar se podría mirar y replantar hasta que tocara el color que
    interesa. Sembrar un poroto sí decide el color, pero porque ya lo traía."""
    con_huerto()
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    salidos = set()
    for _ in range(40):
        economia.plantar("u1", "g1", 1, T0)
        with db.conectar() as con:      # más semillas, que se acaban
            db.guardar_en_la_mochila_en(con, "u1", "g1", "semilla", 1)
        salidos.add(economia.cosechar("u1", "g1", 1, listo).cosechado)
    assert len(salidos) > 1


# --- Sembrar porotos, y el arcoíris ---

class DadosDelHuerto:
    """Un RNG de mentira: se le dice si sale arcoíris, cuántos y de qué color.

    Con `random.Random` haría falta buscar una semilla que diera cada caso, y
    eso ata el test a la implementación del generador: el día que cambie el
    orden de las tiradas, el test miente en vez de fallar.
    """

    def __init__(self, arcoiris: bool, cuantos: int = 3, color: str = "verde"):
        self.arcoiris = arcoiris
        self.cuantos = cuantos
        self.color = color

    def random(self) -> float:
        # `tirar_arcoiris` compara con `<`, así que 0.0 siempre sale y 1.0 nunca.
        return 0.0 if self.arcoiris else 1.0

    def randint(self, a: int, b: int) -> int:
        return self.cuantos

    def choice(self, opciones):
        return self.color


def sembrar_y_cosechar(que, rng=None, color_sembrado="rojo"):
    """Deja en la mochila lo que se va a sembrar, lo siembra y lo cosecha."""
    con_casa("grande")
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", que, 1)
    plantado = economia.plantar("u1", "g1", 1, T0, que)
    assert plantado.ok, plantado.problema
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    return economia.cosechar("u1", "g1", 1, listo, rng)


def test_sembrar_un_poroto_gasta_ese_poroto_y_la_cosecha_sale_de_su_color():
    """Lo que pedía el cambio: el color lo hereda lo sembrado."""
    rojo = hue.clave_de_poroto("rojo")
    con_casa("grande")
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", rojo, 2)

    plantado = economia.plantar("u1", "g1", 1, T0, rojo)

    assert plantado.ok and plantado.sembrado == rojo
    assert db.inventario("u1", "g1")[rojo] == 1     # se gastó uno de los dos

    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    # Con el color forzado a verde en el RNG: si se sorteara, saldría verde.
    recogido = economia.cosechar(
        "u1", "g1", 1, listo, DadosDelHuerto(arcoiris=False, color="verde")
    )
    assert recogido.cosechado == rojo


def test_no_se_siembra_lo_que_no_tienes_y_no_se_gasta_nada():
    con_huerto(semillas=3)
    azul = hue.clave_de_poroto("azul")

    resultado = economia.plantar("u1", "g1", 1, T0, azul)

    assert not resultado.ok
    assert objs.CATALOGO[azul].nombre in resultado.problema
    # Ni se plantó ni se tocó la semilla, que sí tenía.
    assert not bancales()[0].plantado
    assert db.inventario("u1", "g1")[hue.SEMILLA] == 3


def test_lo_que_no_es_sembrable_no_se_siembra():
    """Sin esto, una clave inventada acabaría en la columna `sembrado` y la
    cosecha caería en el sorteo sin que nadie supiera por qué."""
    con_huerto()

    resultado = economia.plantar("u1", "g1", 1, T0, "piedra")

    assert not resultado.ok and not bancales()[0].plantado


def test_de_la_cosecha_sale_un_solo_arcoiris_y_el_resto_del_color():
    """Uno, y **sustituyendo** a un poroto del lote: una cosecha con suerte no
    rinde más que una normal, sólo mejor."""
    recogido = sembrar_y_cosechar(
        hue.clave_de_poroto("rojo"), DadosDelHuerto(arcoiris=True, cuantos=3)
    )

    assert recogido.arcoiris
    assert recogido.cuantos == 2                    # 3 del lote, uno cambiado
    mochila = db.inventario("u1", "g1")
    assert mochila[hue.clave_de_poroto("rojo")] == 2
    assert mochila[hue.clave_de_poroto(hue.ARCOIRIS)] == 1


def test_sin_suerte_no_sale_ningun_arcoiris():
    recogido = sembrar_y_cosechar(
        hue.clave_de_poroto("rojo"), DadosDelHuerto(arcoiris=False, cuantos=3)
    )

    assert not recogido.arcoiris and recogido.cuantos == 3
    assert hue.clave_de_poroto(hue.ARCOIRIS) not in db.inventario("u1", "g1")


def test_la_probabilidad_del_arcoiris_esta_clavada():
    """Con literales y no leyendo la constante: deducir de ella lo que se espera
    haría que cambiarla moviera también la portería, y el test no protegería
    nada. Si esto falla es que alguien tocó el equilibrio a propósito.
    """
    assert hue.PROBABILIDAD_ARCOIRIS == 0.05
    assert sorted(hue.CARAS_DE_ARCOIRIS) == [4, 6, 8, 10, 12]
    assert hue.tirar_arcoiris(DadosDelHuerto(arcoiris=True))
    assert not hue.tirar_arcoiris(DadosDelHuerto(arcoiris=False))


def test_el_arcoiris_se_siembra_pero_da_un_color_al_azar():
    """Se puede plantar —es un poroto— pero no tiene color que heredar, así que
    cae en el sorteo igual que la semilla."""
    recogido = sembrar_y_cosechar(
        hue.clave_de_poroto(hue.ARCOIRIS),
        DadosDelHuerto(arcoiris=False, cuantos=2, color="amarillo"),
    )

    assert recogido.cosechado == hue.clave_de_poroto("amarillo")


def test_el_arcoiris_no_es_un_color():
    """Está fuera de `COLORES` a propósito: si entrara, se sortearía como uno
    más y habría que darle sitio en la tabla de gustos de cada carácter."""
    assert hue.ARCOIRIS not in hue.COLORES
    assert hue.ARCOIRIS in hue.COCINABLES
    assert hue.color_sembrado(hue.clave_de_poroto(hue.ARCOIRIS)) is None
    assert hue.color_sembrado(hue.SEMILLA) is None
    assert hue.color_sembrado(hue.clave_de_poroto("rojo")) == "rojo"
    for _ in range(50):
        assert hue.tirar_color() != hue.ARCOIRIS


def test_lo_sembrado_sobrevive_a_una_base_de_antes_del_cambio():
    """El caso que puede romper un huerto que esté creciendo ahora mismo: esos
    bancales se plantaron cuando la columna no existía, y tienen que seguir
    comportándose como se plantaron —semilla, y color al azar al cosechar—.
    """
    con_casa("grande")
    casa = id_de_la_casa()
    with db.conectar() as con:
        # Sin `sembrado`, como estaba antes; `casa_id` sí, que es de la
        # migración de las casas múltiples y ya la cubre `test_migracion_casas`.
        con.execute("DROP TABLE huerto")
        con.execute(
            "CREATE TABLE huerto ("
            "usuario_id TEXT NOT NULL, guild_id TEXT NOT NULL, "
            "casa_id INTEGER NOT NULL, bancal INTEGER NOT NULL, "
            "plantado_en TEXT NOT NULL, regado INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (usuario_id, guild_id, casa_id, bancal))"
        )
        con.execute(
            "INSERT INTO huerto VALUES ('u1', 'g1', ?, 1, ?, 0)",
            (casa, T0.isoformat()),
        )
        con.commit()
        db._migrar(con)

    bancal = bancales()[0]
    assert bancal.plantado and bancal.sembrado == hue.SEMILLA

    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    recogido = economia.cosechar(
        "u1", "g1", 1, listo, DadosDelHuerto(arcoiris=False, color="verde")
    )
    assert recogido.ok
    assert recogido.cosechado == hue.clave_de_poroto("verde")


def test_el_mensaje_de_la_cosecha_canta_el_arcoiris():
    recogido = sembrar_y_cosechar(
        hue.clave_de_poroto("rojo"), DadosDelHuerto(arcoiris=True, cuantos=3)
    )

    texto = tienda.texto_resultado_huerto(recogido, T0)

    assert hue.NOMBRE_ARCOIRIS in texto and "2 porotos rojos" in texto


def test_el_menu_ofrece_sembrar_lo_que_llevas_y_nada_mas():
    mochila = {
        hue.SEMILLA: 2,
        hue.clave_de_poroto("rojo"): 5,
        hue.clave_de_poroto(hue.ARCOIRIS): 1,
        "golosinas": 9,                     # no se siembra
    }

    assert hue.plantables(mochila) == [
        hue.SEMILLA,
        hue.clave_de_poroto("rojo"),
        hue.clave_de_poroto(hue.ARCOIRIS),
    ]
    assert hue.plantables({"golosinas": 9}) == []
    # Cero en la mochila es no tenerlo: se queda una fila a 0 al gastar el último.
    assert hue.plantables({hue.SEMILLA: 0}) == []


# --- Cocinar ---

def test_cocinar_gasta_los_porotos_y_da_la_sopaipilla():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto("rojo"),
            hue.POROTOS_POR_SOPAIPILLA + 1,
        )

    resultado = economia.cocinar("u1", "g1", "rojo")

    assert resultado.ok
    mochila = db.inventario("u1", "g1")
    assert mochila[hue.clave_de_poroto("rojo")] == 1
    assert mochila[hue.clave_de_sopaipilla("rojo")] == 1


def test_sin_porotos_suficientes_no_se_cocina_ni_se_gasta_nada():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("rojo"), 2)

    resultado = economia.cocinar("u1", "g1", "rojo")

    assert not resultado.ok and "y tienes 2" in resultado.problema
    assert db.inventario("u1", "g1")[hue.clave_de_poroto("rojo")] == 2


def test_no_se_cocina_un_color_que_no_existe():
    with pytest.raises(ValueError):
        economia.cocinar("u1", "g1", "morado")


# --- Comerse la sopaipilla ---

def test_la_sopaipilla_sube_fuerza_y_velocidad_a_la_vez():
    """Un plato, no dos pociones: el mismo número en las dos."""
    bicho = nacer(especie="chispa")

    aviso = tienda.usar(
        bicho, objs.CATALOGO[hue.clave_de_sopaipilla("rojo")], T0,
        random.Random(3),
    )

    # `efectos_activos` devuelve (bonus, lo que queda), no sólo el número.
    efectos = {
        stat: bonus for stat, (bonus, _) in
        db.efectos_activos(bicho.id, T0).items()
    }
    assert set(efectos) == {"fuerza", "velocidad"}
    assert efectos["fuerza"] == efectos["velocidad"]
    assert f"+{efectos['fuerza']}" in aviso


@pytest.mark.parametrize("caras", hue.CARAS_DE_ARCOIRIS)
def test_la_sopaipilla_arcoiris_sube_las_cuatro_con_su_dado(caras):
    """Lo mismo que la de color —un plato, un solo dado— pero en las cuatro, y
    con el dado que le tocó al cocinarla en vez de con el del carácter."""
    bicho = nacer(especie="chispa")

    aviso = tienda.usar(
        bicho, objs.CATALOGO[hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)], T0,
        random.Random(3),
    )

    efectos = {
        stat: bonus for stat, (bonus, _) in
        db.efectos_activos(bicho.id, T0).items()
    }
    assert set(efectos) == set(sim.ESTADISTICAS)
    assert len(set(efectos.values())) == 1      # el mismo número en las cuatro
    assert 1 <= efectos["salud"] <= caras
    assert f"+{efectos['salud']}" in aviso and f"1d{caras}" in aviso


def test_el_dado_del_arcoiris_es_el_suyo_y_no_el_del_caracter():
    """No tiene color, así que no hay tabla de gustos que consultar: se come con
    el dado que traiga escrito, le toque el carácter que le toque."""
    from dataclasses import replace

    import personalidad as per

    class DadoEspia:
        def __init__(self):
            self.caras = None

        def randint(self, a, b):
            self.caras = b
            return b

    # Una criatura sola, cambiándole el carácter: sólo hay una activa por
    # persona y servidor, y lo que se mira aquí es el dado, no la criatura.
    bicho = nacer()
    for caracter in per.CARACTERES:
        for caras in hue.CARAS_DE_ARCOIRIS:
            espia = DadoEspia()
            tienda.usar(
                replace(bicho, caracter=caracter),
                objs.CATALOGO[hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)],
                T0, espia,
            )
            assert espia.caras == caras, (caracter, caras)


def test_el_dado_del_arcoiris_se_sortea_al_cocinarlo():
    """Es lo que se pidió: cocinarlo también se juega. Salen los cinco tamaños,
    y con el mismo reparto que las de color —ninguno cargado hacia el 12—.
    """
    salidos = []
    for vuelta in range(60):
        with db.conectar() as con:
            db.guardar_en_la_mochila_en(
                con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS),
                hue.POROTOS_POR_SOPAIPILLA,
            )
        cocinada = economia.cocinar(
            "u1", "g1", hue.ARCOIRIS, T0, random.Random(vuelta)
        )
        assert cocinada.ok
        salidos.append(cocinada.sopaipilla.caras)

    assert set(salidos) == set(hue.CARAS_DE_ARCOIRIS)
    # Cada sopaipilla guarda su dado: si la clave no lo llevara, todas las de la
    # mochila serían la misma y el sorteo no habría servido de nada.
    mochila = db.inventario("u1", "g1")
    for caras in hue.CARAS_DE_ARCOIRIS:
        clave = hue.clave_de_sopaipilla(hue.ARCOIRIS, caras)
        assert mochila[clave] == salidos.count(caras), caras


def test_una_cocina_que_falla_no_gasta_una_tirada_de_dado():
    """El dado se tira con los porotos ya gastados. Si se tirara antes, quien no
    llegara a tres porotos iría corriendo el sorteo sin cocinar nada."""
    class DadoQueChilla:
        def choice(self, opciones):
            raise AssertionError("no debería tirarse el dado sin cocinar")

    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS), 2
        )

    fallida = economia.cocinar("u1", "g1", hue.ARCOIRIS, T0, DadoQueChilla())

    assert not fallida.ok and "y tienes 2" in fallida.problema


def test_el_dado_de_la_sopaipilla_sale_del_caracter():
    bicho = nacer()
    favorito = hue.AFINIDAD[bicho.caracter][0]
    peor = hue.AFINIDAD[bicho.caracter][-1]

    bueno = tienda.usar(
        bicho, objs.CATALOGO[hue.clave_de_sopaipilla(favorito)], T0
    )
    malo = tienda.usar(
        bicho, objs.CATALOGO[hue.clave_de_sopaipilla(peor)], T0
    )

    assert "1d12" in bueno and "es su favorito" in bueno
    assert "1d4" in malo and "lo detesta" in malo


def test_la_sopaipilla_no_se_acumula():
    """Como las pociones: la nueva sustituye a la anterior."""
    bicho = nacer()
    for _ in range(3):
        tienda.usar(bicho, objs.CATALOGO[hue.clave_de_sopaipilla("rojo")], T0)

    efectos = db.efectos_activos(bicho.id, T0)
    assert len(efectos) == 2                 # fuerza y velocidad, una de cada


# --- Lo que no se vende ---

def test_los_porotos_y_las_sopaipillas_no_se_compran():
    for color in hue.COLORES:
        for clave in (hue.clave_de_poroto(color), hue.clave_de_sopaipilla(color)):
            assert not objs.CATALOGO[clave].se_vende, clave
    assert objs.CATALOGO["semilla"].se_vende


def test_el_poroto_se_puede_regalar_por_el_buzon():
    """Media gracia de que haya colores: te sobran unos y te faltan otros."""
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("rojo"))

    assert db.mandar_regalo(
        "u1", "Felipe", "u2", "g1", hue.clave_de_poroto("rojo"), "te sobran", T0
    )
    assert "Poroto rojo" in tienda.texto_del_buzon("u2", "g1")


# --- Lo que se ve ---

def test_el_huerto_dice_lo_que_le_falta_a_cada_bancal():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    economia.plantar("u1", "g1", 2, T0)
    economia.regar("u1", "g1", 2, T0)

    texto = tienda.texto_del_huerto("u1", "g1", T0 + timedelta(hours=6))

    assert "barbecho" in texto                     # el tercero
    assert "listo para cosechar" in texto          # el regado, a las 5 h
    assert "le faltan 2 h" in texto                # el otro


def test_el_mensaje_de_plantar_dice_las_horas_de_verdad():
    """Regresión: se deducía si estaba regado comparando el `listo_en` contra el
    de un `Bancal` sin `plantado_en`, cuyo `listo_en()` es **siempre `None`**.
    Todo salía distinto, todo se daba por regado y plantar anunciaba las horas
    del bancal regado —5— cuando faltaban las 8 enteras.
    """
    con_huerto()

    plantado = economia.plantar("u1", "g1", 1, T0)
    assert f"le faltan {hue.HORAS_DE_CULTIVO} h" in tienda.texto_resultado_huerto(
        plantado, T0
    )

    # Y regar sí adelanta: desde el momento de regar quedan las que ahorra.
    regado = economia.regar("u1", "g1", 1, T0)
    quedan = hue.HORAS_DE_CULTIVO - hue.HORAS_QUE_AHORRA_REGAR
    assert f"le faltan {quedan} h" in tienda.texto_resultado_huerto(regado, T0)


def test_el_huerto_del_refugio_lo_dice_y_no_ofrece_menu():
    assert "El refugio no tiene huerto" in tienda.texto_del_huerto("u1", "g1", T0)


def test_el_menu_del_huerto_ofrece_lo_que_toca_en_cada_bancal():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    economia.plantar("u1", "g1", 2, T0)
    economia.regar("u1", "g1", 2, T0)

    a_las_seis = T0 + timedelta(hours=6)
    casa = id_de_la_casa()
    menu = tienda.MenuHuerto(bancales(), a_las_seis)

    # El valor lleva la casa además del número: con varias, los números se
    # repiten y regar «el bancal 1» sería ambiguo.
    esperado = {f"regar:{casa}:1", f"cosechar:{casa}:2"}
    esperado |= {
        f"plantar:{casa}:{n}"
        for n in range(3, hue.bancales_de("grande") + 1)
    }
    assert {o.value for o in menu.options} == esperado


def test_el_menu_de_siembra_empieza_en_la_semilla_y_recuerda_lo_elegido():
    """Va aparte del de bancales para no escribir tres bancales por siete cosas
    sembrables. El precio de separarlo es que hay que acordarse de la elección
    entre un desplegable y el otro, y eso es lo que se comprueba aquí."""
    con_huerto(semillas=2)
    rojo = hue.clave_de_poroto("rojo")
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", rojo, 4)
    mochila = db.inventario("u1", "g1")

    de_partida = tienda.MenuQueSembrar(mochila)
    assert de_partida.elegido == hue.SEMILLA
    assert [o.value for o in de_partida.options] == [hue.SEMILLA, rojo]
    assert [o.default for o in de_partida.options] == [True, False]

    elegido = tienda.MenuQueSembrar(mochila, rojo)
    assert elegido.elegido == rojo
    assert [o.default for o in elegido.options] == [False, True]

    # Si se acabó lo que estaba elegido, no se queda apuntando a lo que no está.
    assert tienda.MenuQueSembrar({hue.SEMILLA: 1}, rojo).elegido == hue.SEMILLA
    assert tienda.MenuQueSembrar({}).elegido is None


def test_el_menu_del_huerto_siembra_lo_que_diga_el_de_siembra():
    """El cable entre los dos desplegables: sin él, elegir un poroto no haría
    nada y se seguiría plantando la semilla sin decírselo a nadie."""
    con_huerto(semillas=1)
    rojo = hue.clave_de_poroto("rojo")
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", rojo, 1)

    menus = tienda.menus_del_huerto("u1", "g1", T0, sembrar=rojo)

    del_huerto = next(m for m in menus if isinstance(m, tienda.MenuHuerto))
    assert del_huerto.sembrar == rojo
    # Y sin decir nada, la semilla: es lo que se plantaba antes de todo esto.
    por_defecto = tienda.menus_del_huerto("u1", "g1", T0)
    assert next(
        m for m in por_defecto if isinstance(m, tienda.MenuHuerto)
    ).sembrar == hue.SEMILLA


def test_la_cocina_ofrece_el_arcoiris_cuando_te_llegan():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto(hue.ARCOIRIS),
            hue.POROTOS_POR_SOPAIPILLA,
        )

    menu = tienda.MenuCocina(db.inventario("u1", "g1"))
    assert {o.value for o in menu.options} == {hue.ARCOIRIS}

    resultado = economia.cocinar("u1", "g1", hue.ARCOIRIS, T0, random.Random(1))
    assert resultado.ok
    mochila = db.inventario("u1", "g1")
    assert mochila[resultado.sopaipilla.clave] == 1
    assert resultado.sopaipilla.caras in hue.CARAS_DE_ARCOIRIS
    assert mochila.get(hue.clave_de_poroto(hue.ARCOIRIS), 0) == 0


def test_la_cocina_solo_ofrece_los_colores_que_te_llegan():
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(
            con, "u1", "g1", hue.clave_de_poroto("rojo"),
            hue.POROTOS_POR_SOPAIPILLA,
        )
        db.guardar_en_la_mochila_en(con, "u1", "g1", hue.clave_de_poroto("azul"), 1)

    menu = tienda.MenuCocina(db.inventario("u1", "g1"))

    assert {o.value for o in menu.options} == {"rojo"}


def test_todo_lo_que_hace_pasar_el_tiempo_mira_el_hogar():
    """Ningún sitio puede llamar a `sim.avanzar` a secas.

    El valor por defecto es el de quien tiene techo, así que olvidarlo no rompe
    nada visible: simplemente el hogar deja de contar, en silencio. Pasó en
    cuanto entró una función nueva escrita en paralelo, así que lo vigila un
    barrido del fuente en vez de la buena voluntad.
    """
    import pathlib

    raiz = pathlib.Path(__file__).parent.parent
    permitidos = {"simulacion.py", "db.py"}
    sueltos = []
    for ruta in raiz.glob("**/*.py"):
        if "tests" in ruta.parts or "venv" in ruta.parts:
            continue
        if ruta.name in permitidos:
            continue
        if "sim.avanzar(" in ruta.read_text():
            sueltos.append(ruta.name)

    assert not sueltos, (
        f"llaman a sim.avanzar sin mirar el hogar: {sueltos}. Usa db.avanzar "
        "o db._avanzar_en si ya hay una transacción abierta."
    )


# --- Vender la casa --------------------------------------------------------

def vender(usuario="u1", ahora=T0, casa_id=None):
    return economia.vender_casa(
        usuario, "g1", id_de_la_casa(usuario) if casa_id is None else casa_id,
        ahora,
    )


def test_se_pueden_tener_hasta_tres_casas():
    """Y ni una más: tres grandes son 21 bancales y el menú del huerto lleva una
    fila por bancal, con las 25 opciones que admite un desplegable de Discord."""
    con_monedas(9000)
    for clave in ("pequena", "mediana", "grande"):
        assert economia.comprar_casa("u1", "g1", cas.CATALOGO[clave], T0).ok

    suyas = db.hogar_de("u1", "g1", T0).casas
    assert [c.casa.clave for c in suyas] == ["pequena", "mediana", "grande"]

    cuarta = economia.comprar_casa("u1", "g1", PEQUENA, T0)
    assert not cuarta.ok and str(cas.MAXIMO_CASAS) in cuarta.problema
    assert len(db.hogar_de("u1", "g1", T0).casas) == cas.MAXIMO_CASAS


def test_vender_devuelve_el_ochenta_por_ciento():
    con_casa("grande")
    saldo = monedas()

    resultado = vender()

    assert resultado.ok and resultado.casa == GRANDE
    assert resultado.cobrado == GRANDE.precio * cas.PORCENTAJE_DE_REVENTA // 100
    assert monedas() == saldo + resultado.cobrado
    assert la_casa_de() is None


def test_la_venta_no_pasa_por_el_bote_diario():
    """Lo que más caro saldría equivocado: el bote son 20 al día y la casa
    grande devuelve 960. Si contara como ganancia se perderían 940.

    Una venta es una devolución, no una ganancia.
    """
    con_casa("grande")
    # Se llena el bote del día antes de vender.
    ganado = 0
    i = 0
    while ganado < economia.TOPE_DIARIO_ASCIICOINS:
        ganado += economia.otorgar_hallazgo(f"h{i}", "u1", "g1", 10, 0, T0).monedas
        i += 1
    saldo = monedas()

    resultado = vender()

    assert resultado.cobrado == cas.lo_que_dan_por(GRANDE)      # los 960 enteros
    assert monedas() == saldo + cas.lo_que_dan_por(GRANDE)
    # Y no deja rastro en el ledger, que envenenaría el bote del día.
    with db.conectar() as con:
        assert economia._ganado_hoy(con, "u1", "g1", "2026-01-01") == (
            economia.TOPE_DIARIO_ASCIICOINS
        )


def test_vender_dos_veces_no_paga_dos_veces():
    """El doble clic. Lo para el propio estado: con la casa ya a NULL no hay
    nada que vender."""
    con_casa("mediana")
    primera = vender()
    saldo = monedas()

    segunda = vender()

    assert primera.ok and not segunda.ok
    assert "No tienes casa que vender" in segunda.problema
    assert monedas() == saldo


def test_en_el_refugio_no_hay_nada_que_vender():
    con_monedas(500)
    resultado = vender()

    assert not resultado.ok and "vives en el refugio" in resultado.problema
    assert monedas() == 500


def test_vender_la_ultima_devuelve_al_refugio_con_la_semana_entera():
    """Sólo la última: quien se queda sin nada no puede acabar en la calle de
    golpe. Vendiendo una de varias sigue teniendo techo y el reloj no se toca,
    que es lo que impide refrescarlo comprando y vendiendo una barata en bucle.
    """
    con_casa("pequena")
    mas_tarde = T0 + timedelta(days=30)

    vender(ahora=mas_tarde)

    suyo = db.hogar_de("u1", "g1", mas_tarde)
    assert suyo.estado(mas_tarde) == cas.REFUGIO
    assert suyo.refugio_hasta == mas_tarde + timedelta(days=cas.DIAS_DE_REFUGIO)


def test_al_vender_los_muebles_se_guardan_y_el_huerto_se_pierde():
    """Retirar un mueble nunca lo destruye, tampoco al vender la casa. Lo
    plantado sí: la tierra era de la casa."""
    con_huerto("grande")
    for mueble in mejores(3):
        comprar_m(mueble)
    economia.plantar("u1", "g1", 1, T0)
    assert bancales()[0].plantado

    resultado = vender()

    assert resultado.guardados == 3
    assert set(db.mobiliario("u1", "g1")) == {m.clave for m in mejores(3)}
    assert not any(db.mobiliario("u1", "g1").values())    # ninguno colocado
    with db.conectar() as con:
        assert con.execute("SELECT COUNT(*) FROM huerto").fetchone()[0] == 0


def test_los_muebles_guardados_se_vuelven_a_poner_en_la_casa_nueva():
    """Es lo que hace que vender no sea tirar el dinero del mobiliario."""
    con_huerto("grande")
    for mueble in mejores(3):
        comprar_m(mueble)
    vender()
    con_monedas(monedas() + PEQUENA.precio)
    economia.comprar_casa("u1", "g1", PEQUENA, T0)

    puesto = economia.colocar_mueble("u1", "g1", mejores(1)[0], T0)

    assert puesto.ok and puesto.puestos == 1


def test_vender_es_el_camino_para_bajar_de_casa():
    """`puede_mejorarse_a` sigue prohibiendo bajar de golpe; vendiendo primero se
    puede, y el 20 % perdido queda a la vista en vez de escondido en la compra."""
    con_casa("grande", monedas=5000)
    suya = id_de_la_casa()
    assert not economia.comprar_casa("u1", "g1", PEQUENA, T0, mejorar=suya).ok

    saldo = monedas()
    cobrado = vender().cobrado
    bajada = economia.comprar_casa("u1", "g1", PEQUENA, T0)

    assert bajada.ok and la_casa_de() == PEQUENA
    assert monedas() == saldo + cobrado - PEQUENA.precio


def test_vender_cuesta_lo_mismo_que_el_ticket_del_refugio():
    """Ata las dos cifras: es lo que impide que comprar y vender salga más
    barato que el ticket y se convierta en el atajo para tener techo gratis."""
    perdido = PEQUENA.precio - cas.lo_que_dan_por(PEQUENA)

    assert perdido == objs.CATALOGO["ticket_refugio"].precio
    assert objs.CATALOGO["ticket_refugio"].dias_de_refugio == cas.DIAS_DE_REFUGIO


def test_lo_que_dan_es_entero_por_todas_las_casas():
    for casa in cas.CATALOGO.values():
        dan = cas.lo_que_dan_por(casa)
        assert isinstance(dan, int)
        assert 0 < dan < casa.precio, casa.clave


# --- Lo que se ve al vender ------------------------------------------------

def test_el_menu_ofrece_vender_solo_si_tienes_casa():
    sin_casa = {o.value for o in tienda.MenuCasas(hogar()).options}
    assert not any(v.startswith("vender:") for v in sin_casa)

    con_casa("mediana")
    opciones = tienda.MenuCasas(hogar()).options
    vender = [o for o in opciones if o.value.startswith("vender:")]

    assert len(vender) == 1, "una opción por casa tuya"
    assert str(cas.lo_que_dan_por(MEDIANA)) in vender[0].label


def test_el_aviso_de_la_venta_dice_lo_que_se_pierde():
    con_huerto("grande")
    nacer("Kuro")
    comprar_m(CHIMENEA)
    propia = db.hogar_de("u1", "g1", T0).casas[0]

    texto = tienda.texto_de_la_venta(propia, inquilinos=1)

    assert str(cas.lo_que_dan_por(GRANDE)) in texto
    assert "se guardan" in texto
    assert "se pierde" in texto
    assert "al refugio" in texto, "hay que avisar de que echa a quien vive ahí"


# --- La casa se lista, no se dibuja ----------------------------------------

def test_la_casa_dice_quien_vive_en_cada_una():
    """Lo único que esta pantalla tiene que contestar: quién está dónde."""
    from dataclasses import replace

    hogar_dos = cas.Hogar(
        casas=(cas.CasaPropia(1, PEQUENA), cas.CasaPropia(2, GRANDE)),
        refugio_hasta=T0 + timedelta(days=7),
    )
    dentro = replace(_criatura(0), nombre="Granito", casa_id=1)
    otra = replace(_criatura(1), nombre="Kuro", casa_id=2)
    sin_sitio = replace(_criatura(2), nombre="Perdido", casa_id=None)

    texto = social.texto_de_la_casa(
        hogar_dos, [dentro, otra, sin_sitio], "Felipe", T0
    )

    pequena, grande, refugio = texto.split("### ")[1:]
    assert "Granito" in pequena and "Kuro" not in pequena
    assert "Kuro" in grande and "Granito" not in grande
    assert "Perdido" in refugio
    assert f"**1/{PEQUENA.aforo}**" in pequena, "la ocupación, a la vista"


def test_la_casa_ya_no_dibuja_nada():
    """Se quitó a propósito: con el plantel lleno el cuadro medía 3847
    caracteres. El arte ASCII sigue en la ficha, el jardín y las competencias.
    """
    texto = social.texto_de_la_casa(
        un_hogar(GRANDE, T0), [_criatura(0)], "Felipe", T0
    )

    assert "```" not in texto, "sin bloque de código no hay dibujo"
    assert not hasattr(cas, "render") and not hasattr(cas, "tejado")


def test_el_refugio_solo_sale_si_hay_alguien_fuera():
    """A quien tenga a todos alojados no hace falta recordarle que existe."""
    from dataclasses import replace

    hogar_uno = cas.Hogar(
        casas=(cas.CasaPropia(1, GRANDE),), refugio_hasta=T0 + timedelta(days=7)
    )
    dentro = replace(_criatura(0), casa_id=1)

    con_todos = social.texto_de_la_casa(hogar_uno, [dentro], "Felipe", T0)
    con_uno_fuera = social.texto_de_la_casa(
        hogar_uno, [dentro, replace(_criatura(1), casa_id=None)], "Felipe", T0
    )

    assert "refugio" not in con_todos.lower()
    assert "refugio" in con_uno_fuera.lower()
