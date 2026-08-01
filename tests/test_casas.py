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
STATS = (15, 15, 15)
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


# --- Nadie en la calle -----------------------------------------------------

def test_nadie_se_queda_sin_hogar():
    """Lo pedido: quien nunca ha mirado su casa no está en la calle, está en el
    refugio y con la semana entera por delante."""
    suyo = hogar()

    assert suyo.casa is None
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
    assert suyo.comodidad(suyo.refugio_hasta + timedelta(seconds=1)) == 0


def test_el_hogar_es_de_cada_persona_y_servidor():
    db.hogar_de("u1", "g1", T0)
    assert db.hogar_de("u2", "g1", T0).casa is None
    assert db.hogar_de("u1", "g2", T0).casa is None


# --- Comprar y mudarse -----------------------------------------------------

def test_comprar_cobra_y_te_muda():
    nacer()
    con_monedas(1000)

    resultado = economia.comprar_casa("u1", "g1", MEDIANA, T0)

    assert resultado.ok
    assert resultado.casa == MEDIANA
    assert resultado.desde is None            # venía del refugio
    assert monedas() == 1000 - MEDIANA.precio
    assert hogar().casa == MEDIANA
    assert hogar().estado(T0) == cas.PROPIA


def test_comprar_una_casa_menor_no_cobra_ni_te_muda():
    """El mismo cerrojo que el doble clic del ropero: comprar lo que ya tienes,
    o algo peor, no puede cobrar."""
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", GRANDE, T0)
    saldo = monedas()

    for casa in (PEQUENA, MEDIANA, GRANDE):
        resultado = economia.comprar_casa("u1", "g1", casa, T0)
        assert not resultado.ok, casa.clave
        assert "Ya vives" in resultado.problema

    assert monedas() == saldo
    assert hogar().casa == GRANDE


def test_mudarse_a_una_mayor_dice_de_donde_vienes():
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", PEQUENA, T0)

    resultado = economia.comprar_casa("u1", "g1", GRANDE, T0)

    assert resultado.ok
    assert resultado.desde == PEQUENA
    assert monedas() == 3000 - PEQUENA.precio - GRANDE.precio


def test_sin_monedas_suficientes_no_se_muda_nadie():
    con_monedas(PEQUENA.precio - 1)

    resultado = economia.comprar_casa("u1", "g1", PEQUENA, T0)

    assert not resultado.ok
    assert "faltan 1 asciicoins" in resultado.problema
    assert monedas() == PEQUENA.precio - 1
    assert hogar().casa is None


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


def _eje(linea):
    marcas = [i for i, ch in enumerate(linea) if ch in "/\\╭╮╰╯│"]
    return (marcas[0] + marcas[-1]) / 2 if marcas else None


@pytest.mark.parametrize("cuantos", [0, 1, 3, 5, 6, 10])
def test_el_tejado_va_centrado_sobre_el_marco(cuantos):
    """Es de donde han salido todos los descuadres de este proyecto: centrar el
    adorno sobre su propio eje en vez de sobre el del dibujo. Se mide el ancho
    visible, sin los códigos de color."""
    vivos = [_criatura(i) for i in range(cuantos)]
    for casa in (cas.EL_REFUGIO, *cas.CATALOGO.values()):
        lineas = _sin_color(cas.render(vivos, casa))
        ejes = {_eje(l) for l in lineas if _eje(l) is not None}
        assert len(ejes) == 1, (casa.clave, cuantos, sorted(ejes))


def test_todas_las_lineas_del_marco_miden_lo_mismo():
    lineas = _sin_color(cas.render([_criatura(i) for i in range(4)], GRANDE))
    marco = [l for l in lineas if l.startswith(("╭", "│", "╰"))]
    assert {len(l) for l in marco} == {jardin.ANCHO + 2}


def test_el_tejado_crece_con_la_casa():
    altos = [len(cas.tejado(c)) for c in
             sorted(cas.CATALOGO.values(), key=lambda c: c.tamano)]
    assert altos == sorted(altos) and altos[0] < altos[-1]


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
        cas.Hogar(GRANDE, T0), [_criatura(i) for i in range(10)], "Felipe", T0
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
    texto = social.texto_de_la_casa(cas.Hogar(GRANDE, T0), [], "Felipe", T0)
    assert f"**{GRANDE.comodidad}**/{GRANDE.techo}" in texto
    assert "%" not in texto


def test_la_mudanza_se_canta_diciendo_de_donde_vienes():
    con_monedas(3000)
    del_refugio = economia.comprar_casa("u1", "g1", PEQUENA, T0)
    subiendo = economia.comprar_casa("u1", "g1", GRANDE, T0)

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


def test_el_desplegable_marca_donde_vives_y_lo_que_se_te_quedo_pequeño():
    con_monedas(3000)
    economia.comprar_casa("u1", "g1", MEDIANA, T0)

    por_valor = {
        o.value: o.label for o in tienda.MenuCasas(hogar()).options
    }

    assert "se te quedó pequeña" in por_valor["pequena"]
    assert "aquí vives" in por_valor["mediana"]
    assert f"🪙 {GRANDE.precio}" in por_valor["grande"]


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


def test_al_mudarte_a_una_mayor_caben_los_que_estaban_guardados():
    """Lo que hace que subir de casa valga para algo más que el número."""
    con_casa("pequena")
    for mueble in mejores(PEQUENA.huecos):
        comprar_m(mueble)
    comprar_m(FELPUDO)
    assert not economia.colocar_mueble("u1", "g1", FELPUDO, T0).ok

    economia.comprar_casa("u1", "g1", MEDIANA, T0)
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

    texto = social.texto_de_la_casa(
        hogar(), [], "Felipe", T0, db.puestos("u1", "g1")
    )

    assert f"**{PEQUENA.comodidad + CHIMENEA.comodidad}**/{PEQUENA.techo}" in texto
    assert f"1/{PEQUENA.huecos} huecos" in texto
    assert CHIMENEA.emoji in texto


def test_la_casa_con_diez_gachamones_y_diez_muebles_cabe_en_discord():
    """El peor caso: la casa grande llena de bichos y de muebles."""
    texto = social.texto_de_la_casa(
        cas.Hogar(GRANDE, T0), [_criatura(i) for i in range(10)], "Felipe", T0,
        tuple(m.clave for m in mejores(GRANDE.huecos)),
    )
    assert len(texto) < 2000


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
    hogar = cas.Hogar(None, T0 + timedelta(days=1))       # refugio
    assert cas.ritmo_de(hogar, T0) == sim.Ritmo()
    assert _tras(10, cas.ritmo_de(hogar, T0)) == _tras(10)


def test_a_la_intemperie_todo_cae_un_cuarto_mas_rapido():
    fuera = cas.ritmo_de(cas.Hogar(None, T0), T0 + timedelta(days=1))

    normal, crudo = _tras(10), _tras(10, fuera)

    for barra in ("hambre", "animo", "limpieza"):
        perdido_normal = 100.0 - getattr(normal, barra)
        perdido_fuera = 100.0 - getattr(crudo, barra)
        assert perdido_fuera == pytest.approx(perdido_normal * 1.25), barra


def test_la_intemperie_no_puede_matar():
    """Lo decidido: acelera, pero nadie pierde un gachamon para siempre por no
    haber comprado casa. Ni en un mes a la intemperie."""
    fuera = cas.ritmo_de(cas.Hogar(None, T0), T0 + timedelta(days=1))

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
    mejor = cas.Hogar(GRANDE, T0, tuple(m.clave for m in mejores(GRANDE.huecos)))
    refugio = cas.Hogar(None, T0 + timedelta(days=1))

    en_casa = _tras(24, cas.ritmo_de(mejor, T0))
    en_refugio = _tras(24, cas.ritmo_de(refugio, T0))

    assert en_casa.animo > en_refugio.animo
    # Y el hambre no la toca la comodidad: `muere_en` va precalculado en la base
    # y dejaría de ser cierto en cuanto alguien se mudara.
    assert en_casa.hambre == en_refugio.hambre


def test_los_muebles_cuentan_para_el_ritmo():
    vacia = cas.Hogar(GRANDE, T0)
    llena = cas.Hogar(GRANDE, T0, tuple(m.clave for m in mejores(GRANDE.huecos)))

    assert cas.ritmo_de(llena, T0).animo < cas.ritmo_de(vacia, T0).animo


def test_las_de_la_incubadora_siguen_congeladas_vivan_donde_vivan():
    """El invariante que no se toca: si las de reserva decayeran, con diez por
    persona se morirían hiciera lo que hiciera su dueño."""
    fuera = cas.ritmo_de(cas.Hogar(None, T0), T0 + timedelta(days=1))
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
