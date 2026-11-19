"""Las reglas del departamento: comprar un mueble, ponerlo, guardarlo y ampliar."""
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import departamento as dep
import economia
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
FELPUDO = dep.MUEBLES["felpudo"]
MACETA = dep.MUEBLES["maceta"]


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "economia_departamento.db")
    db.inicializar()


def con_monedas(cuantas, usuario="u1"):
    with db.conectar() as con:
        economia._asegurar_monedero(con, usuario, "g1")
        con.execute(
            "UPDATE monederos SET asciicoins = ? WHERE usuario_id = ? AND guild_id = 'g1'",
            (cuantas, usuario),
        )


def nacer(nombre):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0)


def puesto(usuario, clave, x, y, giro=0):
    """Le añade un mueble ya puesto en (x, y), creando su departamento si falta."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, "g1", T0)
        return db.anadir_mueble_en(con, usuario, "g1", clave, x, y, giro)


def guardado(usuario, clave):
    """Le añade un mueble guardado, creando su departamento si falta."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        db._departamento_en(con, usuario, "g1", T0)
        return db.anadir_mueble_en(con, usuario, "g1", clave)


def filas(tabla):
    with db.conectar() as con:
        return [tuple(f) for f in con.execute(f"SELECT * FROM {tabla}")]


def rompe(cuando):
    """Un disparador que aborta, como los de las pruebas del libro de cuentas."""
    with db.conectar() as con:
        con.execute(f"CREATE TRIGGER rompe {cuando} BEGIN SELECT RAISE(ABORT, 'falla a medias'); END")


# --- Comprar un mueble -----------------------------------------------------

def test_comprar_un_mueble_cobra_y_lo_deja_guardado():
    con_monedas(100)
    hecho = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (hecho.ok, hecho.saldo, hecho.replay) == (True, 70, False)
    assert not hecho.departamento.pieza(hecho.mueble_id).puesta
    assert filas("operaciones_economia") == []


def test_se_puede_comprar_dos_veces_el_mismo():
    con_monedas(100)
    a = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    b = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e2")
    assert a.mueble_id != b.mueble_id and b.saldo == 40


def test_repetir_la_compra_con_el_mismo_evento_no_cobra_ni_entrega_otra_vez():
    con_monedas(100)
    a = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    b = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (b.ok, b.replay, b.mueble_id, b.saldo) == (True, True, a.mueble_id, 70)
    assert len(db.departamento_leido("u1", "g1").piezas) == 4      # dos camas, la puerta y un solo felpudo


def test_el_replay_de_la_compra_devuelve_lo_cobrado_aunque_el_catalogo_cambie(monkeypatch):
    con_monedas(100)
    a = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    with db.conectar() as con:
        assert db.accion_hecha_en(con, "e1", "u1", "g1", "mueble") == ("felpudo", {"mueble_id": a.mueble_id, "coste": 30})
    mas_caro = replace(FELPUDO, precio=45)
    monkeypatch.setitem(dep.MUEBLES, "felpudo", mas_caro)
    b = economia.comprar_mueble("u1", "g1", mas_caro, T0, evento_id="e1")
    assert (b.ok, b.replay, b.mueble_id, b.coste, b.saldo) == (True, True, a.mueble_id, 30, 70)


def test_un_evento_anotado_sin_lo_cobrado_sigue_valiendo():
    con_monedas(100)
    viejo = guardado("u1", "felpudo")
    with db.conectar() as con:      # como se anotaba antes: sólo el mueble
        db.anotar_accion_en(con, "e1", "u1", "g1", "mueble", "felpudo", {"mueble_id": viejo}, T0)
    b = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (b.ok, b.replay, b.mueble_id, b.coste, b.saldo) == (True, True, viejo, 30, 100)


def test_el_mismo_evento_para_otro_mueble_es_un_error():
    con_monedas(200)
    economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    with pytest.raises(RuntimeError):
        economia.comprar_mueble("u1", "g1", MACETA, T0, evento_id="e1")


def test_sin_monedas_no_se_compra_ni_se_gasta_el_evento():
    con_monedas(10)
    hecho = economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1")
    assert (hecho.ok, hecho.motivo, hecho.coste, hecho.saldo) == (False, "faltan_monedas", 30, 10)
    con_monedas(30)
    assert economia.comprar_mueble("u1", "g1", FELPUDO, T0, evento_id="e1").ok


def test_un_mueble_que_no_es_del_catalogo_no_se_cuela():
    con_monedas(100)
    falso = dep.Mueble("felpudo", "Felpudo de mentira", "🚪", 0, 99)
    with pytest.raises(ValueError):
        economia.comprar_mueble("u1", "g1", falso, T0, evento_id="e1")
    assert economia.saldos("u1", "g1").asciicoins == 100 and filas("muebles") == []


# --- Poner y guardar -------------------------------------------------------

def test_poner_mover_y_girar():
    cama = db.departamento_de("u1", "g1", T0).guardadas[0].id
    assert economia.poner_mueble("u1", "g1", cama, 1, 1, 0, T0).ok
    hecho = economia.poner_mueble("u1", "g1", cama, 0, 1, 1, T0)       # la mueve y la gira
    assert hecho.ok and hecho.departamento.pieza(cama) == dep.Pieza(cama, "cama_sencilla", 0, 1, 1)
    assert economia.poner_mueble("u1", "g1", cama, 0, 1, 1, T0).departamento == hecho.departamento   # repetir deja lo mismo


@pytest.mark.parametrize("x, y, giro, motivo", [(2, 2, 0, dep.NO_CABE), (0, 0, 0, dep.OCUPADO), (-1, 0, 0, dep.NO_CABE)])
def test_no_se_pone_donde_no_cabe_ni_donde_hay_algo(x, y, giro, motivo):
    antes = db.departamento_de("u1", "g1", T0)
    hecho = economia.poner_mueble("u1", "g1", antes.guardadas[0].id, x, y, giro, T0)
    assert (hecho.ok, hecho.motivo) == (False, motivo)
    assert db.departamento_leido("u1", "g1") == antes


@pytest.mark.parametrize("x, y, giro", [(1, 1, 4), (1, 1, -1), (1, 1, True), (1.5, 1, 0), (1, "1", 0)])
def test_un_giro_o_un_sitio_que_no_existe_es_un_error(x, y, giro):
    antes = db.departamento_de("u1", "g1", T0)
    with pytest.raises(ValueError):
        economia.poner_mueble("u1", "g1", antes.guardadas[0].id, x, y, giro, T0)
    assert db.departamento_leido("u1", "g1") == antes


def test_el_mueble_de_otro_no_se_pone_ni_se_guarda():
    ajeno = db.departamento_de("u2", "g1", T0).guardadas[0].id
    assert economia.poner_mueble("u1", "g1", ajeno, 1, 1, 0, T0).motivo == dep.NO_ES_TUYO
    assert economia.guardar_mueble("u1", "g1", ajeno, T0).motivo == dep.NO_ES_TUYO
    assert not db.departamento_leido("u2", "g1").pieza(ajeno).puesta


def test_un_mueble_que_no_existe_tampoco_se_guarda():
    hecho = economia.guardar_mueble("u1", "g1", 9999, T0)
    assert (hecho.ok, hecho.motivo) == (False, dep.NO_ES_TUYO)


def test_guardar_no_destruye_y_repetirlo_no_cambia_nada():
    maceta = puesto("u1", "maceta", 2, 2)
    assert economia.guardar_mueble("u1", "g1", maceta, T0).ok
    hecho = economia.guardar_mueble("u1", "g1", maceta, T0)
    assert hecho.ok and hecho.departamento.pieza(maceta) == dep.Pieza(maceta, "maceta")


def test_la_cama_que_hace_falta_no_se_guarda():
    nacer("Ana")
    d = db.departamento_de("u1", "g1", T0)
    tuya, otra = d.puestas[0].id, d.guardadas[0].id
    economia.poner_mueble("u1", "g1", otra, 0, 1, 0, T0)               # ya son dos: tú y Ana
    assert economia.guardar_mueble("u1", "g1", tuya, T0).motivo == "hace_falta"
    tercera = puesto("u1", "cama", 0, 2)
    assert economia.guardar_mueble("u1", "g1", tuya, T0).ok            # ahora sobra una
    assert economia.guardar_mueble("u1", "g1", tercera, T0).motivo == "hace_falta"


# --- Ampliar ---------------------------------------------------------------

def test_ampliar_cobra_15_por_casilla_y_no_mueve_lo_puesto():
    con_monedas(200)
    antes = db.departamento_de("u1", "g1", T0)
    hecho = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert (hecho.ok, hecho.coste, hecho.saldo) == (True, 45, 155)
    assert (hecho.departamento.ancho, hecho.departamento.fondo, hecho.departamento.piezas) == (4, 3, antes.piezas)
    assert economia.ampliar_departamento("u1", "g1", dep.FONDO, T0, evento_id="e2").coste == 60


def test_repetir_ampliar_con_el_mismo_evento_no_cobra_dos_veces():
    con_monedas(200)
    economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    otra = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert (otra.ok, otra.replay, otra.saldo, otra.departamento.ancho) == (True, True, 155, 4)
    assert otra.coste == 45


def test_ampliar_sin_monedas_o_ya_en_8_no_cambia_nada():
    con_monedas(44)
    assert economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1").motivo == "faltan_monedas"
    con_monedas(9999)
    for i in range(5):
        assert economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id=f"a{i}").ok
    tope = economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="a9")
    assert (tope.ok, tope.motivo, tope.departamento.ancho) == (False, "ya_es_el_maximo", 8)
    assert economia.saldos("u1", "g1").asciicoins == 9999 - 5 * 45


def test_el_mismo_evento_para_ampliar_por_el_otro_lado_es_un_error():
    con_monedas(200)
    economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    with pytest.raises(RuntimeError):
        economia.ampliar_departamento("u1", "g1", dep.FONDO, T0, evento_id="e1")
    assert economia.saldos("u1", "g1").asciicoins == 155 and db.departamento_leido("u1", "g1").fondo == 3


def test_ampliar_por_un_lado_que_no_existe_es_un_error():
    con_monedas(200)
    with pytest.raises(ValueError):
        economia.ampliar_departamento("u1", "g1", "alto", T0, evento_id="e1")
    assert economia.saldos("u1", "g1").asciicoins == 200 and filas("departamentos") == []


def test_si_falla_a_medias_ampliar_no_cobra():
    con_monedas(200)
    db.departamento_de("u1", "g1", T0)
    rompe("BEFORE UPDATE ON departamentos")
    with pytest.raises(sqlite3.DatabaseError):
        economia.ampliar_departamento("u1", "g1", dep.ANCHO, T0, evento_id="e1")
    assert economia.saldos("u1", "g1").asciicoins == 200 and filas("acciones_unicas") == []


# --- Antes de cambiar el ritmo, el plantel se asienta ----------------------

def test_poner_un_mueble_no_cambia_el_animo_del_tiempo_ya_pasado():
    c = nacer("Ana")
    chimenea = guardado("u1", "chimenea")
    tarde = T0 + timedelta(hours=10)
    esperado = sim.avanzar(c, tarde, dep.ritmo_de(db.departamento_leido("u1", "g1")))   # con la comodidad de antes
    economia.poner_mueble("u1", "g1", chimenea, 1, 1, 0, tarde)
    ahora_es = db.por_id(c.id)
    assert ahora_es.actualizada_en == tarde and ahora_es.animo == pytest.approx(esperado.animo)


def test_guardar_un_mueble_no_cambia_el_animo_del_tiempo_ya_pasado():
    c = nacer("Ana")
    chimenea = puesto("u1", "chimenea", 0, 1)
    antes = db.departamento_leido("u1", "g1")
    tarde = T0 + timedelta(hours=10)
    esperado = sim.avanzar(c, tarde, dep.ritmo_de(antes))                 # con la comodidad de antes, la alta
    assert economia.guardar_mueble("u1", "g1", chimenea, tarde).ok
    assert db.departamento_leido("u1", "g1").comodidad < antes.comodidad
    ahora_es = db.por_id(c.id)
    assert ahora_es.actualizada_en == tarde and ahora_es.animo == pytest.approx(esperado.animo)


def test_ampliar_no_cambia_el_animo_del_tiempo_ya_pasado():
    c = nacer("Ana"); con_monedas(100)
    for clave, x, y in (("chimenea", 0, 1), ("biblioteca", 0, 2), ("calefactor", 2, 0), ("ventanal", 0, -1)):
        puesto("u1", clave, x, y)
    antes = db.departamento_leido("u1", "g1")
    assert antes.comodidad == dep.tope_de_comodidad(9) == 100                # 80 + 2 + 6 + 7 + 7 + 7 = 109, topada
    tarde = T0 + timedelta(hours=10)
    esperado = sim.avanzar(c, tarde, dep.ritmo_de(antes))                 # con el tope de antes
    assert economia.ampliar_departamento("u1", "g1", dep.ANCHO, tarde, evento_id="e1").ok
    assert db.departamento_leido("u1", "g1").comodidad == 102
    ahora_es = db.por_id(c.id)
    assert ahora_es.actualizada_en == tarde and ahora_es.animo == pytest.approx(esperado.animo)


def test_guardar_y_ampliar_tambien_asientan_antes():
    c = nacer("Ana"); con_monedas(100)
    maceta = puesto("u1", "maceta", 2, 2)
    economia.guardar_mueble("u1", "g1", maceta, T0 + timedelta(hours=1))
    assert db.por_id(c.id).actualizada_en == T0 + timedelta(hours=1)
    economia.ampliar_departamento("u1", "g1", dep.FONDO, T0 + timedelta(hours=2), evento_id="e1")
    assert db.por_id(c.id).actualizada_en == T0 + timedelta(hours=2)


def test_si_poner_o_guardar_falla_a_medias_el_plantel_tampoco_se_asienta():
    c = nacer("Ana")
    maceta = puesto("u1", "maceta", 2, 2)
    antes = db.departamento_leido("u1", "g1")
    rompe("BEFORE UPDATE ON muebles")
    luego = T0 + timedelta(hours=3)
    with pytest.raises(sqlite3.DatabaseError):
        economia.poner_mueble("u1", "g1", maceta, 1, 1, 0, luego)
    with pytest.raises(sqlite3.DatabaseError):
        economia.guardar_mueble("u1", "g1", maceta, luego)
    assert db.por_id(c.id).actualizada_en == T0 and db.departamento_leido("u1", "g1") == antes


def test_lo_que_no_cambia_nada_no_asienta():
    c = nacer("Ana"); con_monedas(10)
    maceta = puesto("u1", "maceta", 2, 2)
    guardada = guardado("u1", "felpudo")
    luego = T0 + timedelta(hours=3)
    economia.poner_mueble("u1", "g1", maceta, 2, 2, 0, luego)                  # ya estaba ahí
    economia.poner_mueble("u1", "g1", guardada, 5, 5, 0, luego)                # no cabe
    economia.guardar_mueble("u1", "g1", guardada, luego)                       # ya estaba guardado
    economia.ampliar_departamento("u1", "g1", dep.ANCHO, luego, evento_id="e1")   # no alcanza
    assert db.por_id(c.id).actualizada_en == T0


def test_la_puerta_no_se_guarda_ni_se_compra():
    nacer("Ana"); depto_ = db.departamento_de("u1", "g1", T0)
    puerta = next(p for p in depto_.puestas if p.clave == dep.PUERTA)
    hecho = economia.guardar_mueble("u1", "g1", puerta.id, T0)
    assert (hecho.ok, hecho.motivo) == (False, "no_se_guarda")
    assert db.departamento_leido("u1", "g1").pieza(puerta.id).puesta
    with pytest.raises(ValueError):
        economia.comprar_mueble("u1", "g1", dep.MUEBLES[dep.PUERTA], T0, "evento-puerta-1")


def test_la_puerta_se_mueve_como_cualquier_cosa_de_pared():
    nacer("Ana"); puerta = next(p for p in db.departamento_de("u1", "g1", T0).puestas if p.clave == dep.PUERTA)
    hecho = economia.poner_mueble("u1", "g1", puerta.id, 1, -1, 0, T0)
    assert hecho.ok and (hecho.departamento.pieza(puerta.id).x, hecho.departamento.pieza(puerta.id).y) == (1, -1)


# --- Los muebles que se usan solos -----------------------------------------
#
# Con el refrigerador, la consola o la ducha puestos, su barra no baja de 40 y,
# si estaba más abajo, sube a 40 al ponerlo; con unas pesas puestas, cada
# medianoche UTC suma un punto de fuerza. Todo sale del ritmo del departamento
# al leer: aquí se lee como la página, con `db.plantel_al_dia`.

def con_barras(criatura, **barras):
    """Le guarda esas barras sin mover cuándo se puso al día, y la devuelve como quedó."""
    db.guardar(replace(criatura, **barras))
    return db.por_id(criatura.id)


def al_dia(ahora):
    return db.plantel_al_dia("u1", "g1", ahora)


def test_al_poner_el_refrigerador_la_comida_sube_al_minimo():
    con_barras(nacer("Ana"), hambre=10.0)
    refrigerador = guardado("u1", "refrigerador")
    luego = T0 + timedelta(hours=1)
    [sin_mueble] = al_dia(luego)
    assert sin_mueble.hambre < 10.0 and sin_mueble.animo < 100.0 and sin_mueble.limpieza < 100.0
    assert economia.poner_mueble("u1", "g1", refrigerador, 2, 2, 0, luego).ok
    [con_mueble] = al_dia(luego)                                              # el mismo instante
    assert con_mueble.hambre == 40.0
    assert (con_mueble.animo, con_mueble.limpieza) == (sin_mueble.animo, sin_mueble.limpieza)


def test_al_guardarlo_la_barra_vuelve_a_bajar_desde_el_minimo():
    ana = nacer("Ana")
    refrigerador = puesto("u1", "refrigerador", 2, 2)
    cien = T0 + timedelta(hours=100)
    assert [c.hambre for c in al_dia(cien)] == [40.0]
    assert economia.guardar_mueble("u1", "g1", refrigerador, cien).ok
    [luego] = al_dia(cien + timedelta(hours=10))
    assert luego.hambre < 40.0
    assert luego.hambre == pytest.approx(40.0 - 10 * sim.tasa_hambre_por_hora(ana.salud))


def test_con_dos_refrigeradores_guardar_uno_no_quita_el_minimo():
    nacer("Ana")
    uno = puesto("u1", "refrigerador", 2, 2)
    puesto("u1", "refrigerador", 2, 1)
    cien = T0 + timedelta(hours=100)
    assert economia.guardar_mueble("u1", "g1", uno, cien).ok
    assert [c.hambre for c in al_dia(cien + timedelta(hours=100))] == [40.0]


def fuerza_a_las(ahora):
    return [c.ent_fuerza for c in al_dia(ahora)]


def test_las_pesas_entrenan_a_todos_un_punto_por_dia():
    assert (T0.hour, T0.minute) == (12, 0)
    ana = nacer("Ana")
    beto = db.crear("u1", "g1", "pulpo", "Beto", STATS, T0, activa=False)
    pesas = guardado("u1", "pesas")
    assert economia.poner_mueble("u1", "g1", pesas, 2, 2, 0, T0).ok
    antes = [ana.ent_fuerza, beto.ent_fuerza]
    assert fuerza_a_las(T0 + timedelta(hours=11, minutes=59)) == antes                # todavía es el mismo día
    assert fuerza_a_las(T0 + timedelta(hours=12)) == [f + 1 for f in antes]           # la primera medianoche
    assert fuerza_a_las(T0 + timedelta(days=3)) == [f + 3 for f in antes]


def test_guardar_y_volver_a_poner_las_pesas_el_mismo_dia_no_da_puntos():
    ana = nacer("Ana")
    pesas = puesto("u1", "pesas", 2, 2)
    for hora in range(1, 6):                                                    # de las 13:00 a las 17:30
        assert economia.guardar_mueble("u1", "g1", pesas, T0 + timedelta(hours=hora)).ok
        assert economia.poner_mueble("u1", "g1", pesas, 2, 2, 0, T0 + timedelta(hours=hora, minutes=30)).ok
    assert db.por_id(ana.id).ent_fuerza == ana.ent_fuerza
    assert fuerza_a_las(T0 + timedelta(hours=11, minutes=59)) == [ana.ent_fuerza]
    assert fuerza_a_las(T0 + timedelta(hours=12)) == [ana.ent_fuerza + 1]       # y la medianoche cuenta una vez


def test_la_medianoche_con_las_pesas_guardadas_no_cuenta():
    ana = nacer("Ana")
    pesas = puesto("u1", "pesas", 2, 2)
    assert economia.guardar_mueble("u1", "g1", pesas, T0 + timedelta(hours=11)).ok          # a las 23:00
    assert economia.poner_mueble("u1", "g1", pesas, 2, 2, 0, T0 + timedelta(hours=13)).ok    # a la 1:00 del otro día
    assert db.por_id(ana.id).ent_fuerza == ana.ent_fuerza
    assert fuerza_a_las(T0 + timedelta(hours=35)) == [ana.ent_fuerza]
    assert fuerza_a_las(T0 + timedelta(hours=36)) == [ana.ent_fuerza + 1]       # la medianoche siguiente, sí


def test_quien_nace_con_las_pesas_ya_puestas_no_gana_nada_hasta_su_primera_medianoche():
    pesas = guardado("u1", "pesas")
    assert economia.poner_mueble("u1", "g1", pesas, 2, 2, 0, T0 - timedelta(days=3)).ok
    ana = db.crear("u1", "g1", "pulpo", "Ana", STATS, T0)                       # nace a las 12:00 UTC
    assert fuerza_a_las(T0) == [ana.ent_fuerza]
    assert fuerza_a_las(T0 + timedelta(hours=11, minutes=59)) == [ana.ent_fuerza]
    assert fuerza_a_las(T0 + timedelta(hours=12)) == [ana.ent_fuerza + 1]


def test_mover_o_girar_el_refrigerador_no_cambia_la_comida_ni_da_puntos():
    ana = nacer("Ana"); con_monedas(100)
    refrigerador = puesto("u1", "refrigerador", 2, 2)
    puesto("u1", "pesas", 2, 1)
    tarde = T0 + timedelta(hours=100)                                           # el 5 de enero a las 16:00
    [antes] = al_dia(tarde)
    assert (antes.hambre, antes.ent_fuerza) == (40.0, ana.ent_fuerza + 4)
    for minutos, (x, y, giro) in enumerate(((1, 2, 0), (1, 2, 1), (2, 2, 3)), 1):   # lo mueve, lo gira, lo devuelve
        assert economia.poner_mueble("u1", "g1", refrigerador, x, y, giro, tarde + timedelta(minutes=minutos)).ok
    [despues] = al_dia(tarde + timedelta(minutes=3))
    assert (despues.hambre, despues.ent_fuerza, despues.xp, despues.nivel) == (40.0, antes.ent_fuerza, antes.xp, antes.nivel)
    assert economia.saldos("u1", "g1").asciicoins == 100 and filas("operaciones_economia") == []


def lo_del_dinero():
    """Todo lo que ni los mínimos ni las pesas pueden tocar: el dinero, su libro, los marcadores y las medallas."""
    return {tabla: filas(tabla) for tabla in (
        "monederos", "operaciones_economia", "marcador", "logros", "marcador_persona", "logros_persona")}


def lo_que_no_es_de_las_pesas(c):
    """Experiencia, nivel y crecimiento: lo que sólo dan los cuidados, competir y las aventuras."""
    return (c.xp, c.nivel, c.niv_fuerza, c.niv_velocidad, c.niv_salud, c.niv_ingenio,
            c.ent_velocidad, c.ent_salud, c.ent_ingenio,
            c.ten_fuerza, c.ten_velocidad, c.ten_salud, c.ten_ingenio, c.historial_vetas)


def test_los_muebles_que_se_usan_solos_no_mueven_el_dinero():
    con_monedas(1500)
    ana = con_barras(nacer("Ana"), hambre=5.0, animo=5.0, limpieza=5.0)
    beto = db.crear("u1", "g1", "pulpo", "Beto", STATS, T0, activa=False)
    cuatro = [economia.comprar_mueble("u1", "g1", dep.MUEBLES[clave], T0, evento_id=f"compra-{clave}").mueble_id
              for clave in ("refrigerador", "consola", "ducha", "pesas")]
    antes = lo_del_dinero()
    assert economia.saldos("u1", "g1").asciicoins == 300
    for mueble_id, (x, y) in zip(cuatro, ((2, 0), (2, 1), (2, 2), (1, 1))):
        assert economia.poner_mueble("u1", "g1", mueble_id, x, y, 0, T0).ok
    # Treinta días, y cada uno asentado y guardado: mover las pesas pone al día a todos.
    for dia in range(1, 31):
        x = 0 if dia % 2 else 1
        assert economia.poner_mueble("u1", "g1", cuatro[3], x, 1, 0, T0 + timedelta(days=dia)).ok
    final = al_dia(T0 + timedelta(days=30))
    assert [(c.hambre, c.animo, c.limpieza) for c in final] == [(40.0, 40.0, 40.0)] * 2   # los mínimos, puestos
    assert [c.ent_fuerza for c in final] == [ana.ent_fuerza + 30, beto.ent_fuerza + 30]   # y las pesas, también
    assert lo_del_dinero() == antes
    assert [lo_que_no_es_de_las_pesas(c) for c in final] == [lo_que_no_es_de_las_pesas(c) for c in (ana, beto)]
