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
    assert suyo.casa == MEDIANA and suyo.puestos == ("chimenea",)


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


def bancales(usuario="u1", clave="grande"):
    return db.huerto_de(usuario, "g1", hue.bancales_de(clave))


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

    assert not resultado.ok and "semilla" in resultado.problema
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
    """Y con varias semillas distintas, no con una sola tirada afortunada."""
    con_huerto(semillas=60)
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    minimo, maximo = hue.POROTOS_POR_COSECHA
    vistos = set()
    for semilla in range(40):
        economia.plantar("u1", "g1", 1, T0)
        cuantos = economia.cosechar(
            "u1", "g1", 1, listo, random.Random(semilla)
        ).cuantos
        assert minimo <= cuantos <= maximo, cuantos
        vistos.add(cuantos)
    # Y no siempre el mismo número, o el rango sería de adorno.
    assert len(vistos) > 1


def test_los_porotos_de_una_cosecha_son_todos_del_mismo_color():
    """Se tira el color una vez para la mata entera. Se comprueba mirando el
    inventario: si cada poroto tirara el suyo, habría varias claves."""
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)

    resultado = economia.cosechar("u1", "g1", 1, listo, random.Random(7))

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


def test_el_color_se_sortea_al_cosechar_y_no_al_sembrar():
    """Si saliera al sembrar se podría mirar y replantar hasta que tocara el
    color que interesa."""
    con_huerto()
    listo = T0 + timedelta(hours=hue.HORAS_DE_CULTIVO)
    salidos = set()
    for _ in range(40):
        economia.plantar("u1", "g1", 1, T0)
        with db.conectar() as con:      # más semillas, que se acaban
            db.guardar_en_la_mochila_en(con, "u1", "g1", "semilla", 1)
        salidos.add(economia.cosechar("u1", "g1", 1, listo).cosechado)
    assert len(salidos) > 1


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


def test_el_huerto_del_refugio_lo_dice_y_no_ofrece_menu():
    assert "El refugio no tiene huerto" in tienda.texto_del_huerto("u1", "g1", T0)


def test_el_menu_del_huerto_ofrece_lo_que_toca_en_cada_bancal():
    con_huerto()
    economia.plantar("u1", "g1", 1, T0)
    economia.plantar("u1", "g1", 2, T0)
    economia.regar("u1", "g1", 2, T0)

    a_las_seis = T0 + timedelta(hours=6)
    menu = tienda.MenuHuerto(bancales(), a_las_seis)

    assert {o.value for o in menu.options} == {
        "regar:1",        # plantado, sin regar, aún creciendo
        "cosechar:2",     # regado y listo a las 5 h
        "plantar:3",      # en barbecho
    }


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

def vender(usuario="u1", ahora=T0):
    return economia.vender_casa(usuario, "g1", ahora)


def test_solo_se_tiene_una_casa():
    """Lo impone la clave primaria de `hogar` con una sola columna `casa`, y
    hasta ahora no lo decía ningún test. Comprar tres deja una: la última."""
    con_monedas(9000)
    for clave in ("pequena", "mediana", "grande"):
        economia.comprar_casa("u1", "g1", cas.CATALOGO[clave], T0)

    assert hogar().casa == GRANDE
    with db.conectar() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM hogar WHERE usuario_id='u1' AND guild_id='g1'"
        ).fetchone()[0] == 1


def test_vender_devuelve_el_ochenta_por_ciento():
    con_casa("grande")
    saldo = monedas()

    resultado = vender()

    assert resultado.ok and resultado.casa == GRANDE
    assert resultado.cobrado == GRANDE.precio * cas.PORCENTAJE_DE_REVENTA // 100
    assert monedas() == saldo + resultado.cobrado
    assert hogar().casa is None


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


def test_vender_devuelve_al_refugio_con_la_semana_entera():
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
    """`puede_mudarse_a` sigue prohibiendo bajar de golpe; vendiendo primero se
    puede, y el 20 % perdido queda a la vista en vez de escondido en la compra."""
    con_casa("grande", monedas=5000)
    assert not economia.comprar_casa("u1", "g1", PEQUENA, T0).ok

    saldo = monedas()
    cobrado = vender().cobrado
    bajada = economia.comprar_casa("u1", "g1", PEQUENA, T0)

    assert bajada.ok and hogar().casa == PEQUENA
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
    assert tienda.VENDER not in {o.value for o in tienda.MenuCasas(hogar()).options}

    con_casa("mediana")
    opciones = tienda.MenuCasas(hogar()).options

    assert opciones[0].value == tienda.VENDER          # la primera, no perdida
    assert str(cas.lo_que_dan_por(MEDIANA)) in opciones[0].label


def test_el_aviso_de_la_venta_dice_lo_que_se_pierde():
    con_huerto("grande")
    comprar_m(CHIMENEA)

    texto = tienda.texto_de_la_venta(hogar(), db.mobiliario("u1", "g1"))

    assert str(cas.lo_que_dan_por(GRANDE)) in texto
    assert "se guardan" in texto
    assert "huerto se pierde" in texto
