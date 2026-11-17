import random
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import logros as lgr
import nacer
import nombres
from test_camas import poner_camas

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
U, G = "u", "g"
STATS = (10, 10, 10, 10)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "nacer.db")
    db.inicializar()


def nace(nombre):
    return db.crear(U, G, "pulpo", nombre, STATS, T0)


def test_del_huevo_sale_una_de_las_diez_con_nombre_provisional():
    nacida = nacer.romper_el_huevo("u", "g", T0, random.Random(3))
    especie = esp.ESPECIES[nacida.especie]
    assert especie.peso > 0
    assert nacida.nombre == especie.nombre and nacer.espera_nombre(nacida)
    assert nacida.activa and nacida.viva and nacida.nivel == 1
    assert db.criatura_activa("u", "g").id == nacida.id


def test_el_mismo_azar_da_el_mismo_gachamon():
    a = nacer.romper_el_huevo("a", "g", T0, random.Random(5))
    b = nacer.romper_el_huevo("b", "g", T0, random.Random(5))
    assert (a.especie, a.genero, a.caracter, a.base_fuerza, a.base_ingenio) == (
        b.especie, b.genero, b.caracter, b.base_fuerza, b.base_ingenio)


def test_el_huevo_es_solo_el_de_partida():
    nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)
    assert len(db.plantel("u", "g")) == 1


def test_con_uno_en_la_incubadora_tampoco_hay_huevo():
    primero = nacer.romper_el_huevo("u", "g", T0)
    db.guardar(replace(primero, muerta_en=T0, causa_muerte="hambre"))
    db.crear("u", "g", "pulpo", "Tinta", (10, 10, 10, 10), T0, activa=False)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.romper_el_huevo("u", "g", T0)


def test_cuando_se_le_murio_el_unico_puede_sacar_otro():
    unico = nacer.romper_el_huevo("d", "g", T0)
    db.guardar(replace(unico, muerta_en=T0, causa_muerte="hambre"))
    otro = nacer.romper_el_huevo("d", "g", T0 + timedelta(days=5))
    assert otro.viva and len(db.plantel("d", "g")) == 1


def test_dos_huevos_a_la_vez_dejan_un_gachamon():
    def romper(_):
        try:
            return nacer.romper_el_huevo("u", "g", T0)
        except nacer.YaTieneGachamon:
            return None

    with ThreadPoolExecutor(max_workers=2) as hilos:
        nacidos = [n for n in hilos.map(romper, range(2)) if n]
    assert len(nacidos) == 1 and len(db.plantel("u", "g")) == 1


# --- El primero, en la primera aventura ---------------------------------------

def test_el_primero_sale_de_las_diez_del_huevo_y_pide_cama():
    # Sin la segunda cama puesta (la de partida es la tuya) no nace nadie.
    with pytest.raises(db.SinCamaLibre):
        nacer.encontrar_al_primero(U, G, T0, random.Random(3))
    assert db.plantel(U, G) == [] and not db.tiene_gachamones(U, G)

    poner_camas(U, 1, G)
    primero = nacer.encontrar_al_primero(U, G, T0, random.Random(3))
    especie = esp.elegir_del_huevo(random.Random(3))
    assert primero.especie == especie.clave and especie.clave in esp.DEL_HUEVO
    assert primero.nombre == especie.nombre and nacer.espera_nombre(primero)
    assert primero.activa and primero.viva and primero.nivel == 1
    assert primero.se_nombro_solo is False
    assert db.criatura_activa(U, G).id == primero.id
    assert [c.id for c in db.plantel(U, G)] == [primero.id]


def test_con_un_gachamon_vivo_no_hay_primero():
    poner_camas(U, 3, G)
    nace("Nube")
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.encontrar_al_primero(U, G, T0)
    # Tampoco con uno vivo que no es el activo: el remiendo lo hace activo.
    db.crear("v", G, "pulpo", "Tinta", STATS, T0, activa=False)
    poner_camas("v", 3, G)
    with pytest.raises(nacer.YaTieneGachamon):
        nacer.encontrar_al_primero("v", G, T0)
    assert len(db.plantel(U, G)) == 1 and len(db.plantel("v", G)) == 1


@pytest.mark.parametrize("camas", [1, 2], ids=["la_cama_justa", "con_cama_de_sobra"])
def test_dos_primeros_a_la_vez_dejan_uno(camas, monkeypatch):
    """Los dos miran el plantel vacío antes de que el otro cree nada: con la
    cama justa, el segundo ya no la encuentra; con una de sobra, lo para el
    índice de la activa. Los dos casos dicen que ya tienes uno."""
    poner_camas(U, camas, G)
    los_dos_miraron = threading.Barrier(2, timeout=10)
    elegir = esp.elegir_del_huevo

    def despues_de_mirar(rng):
        los_dos_miraron.wait()
        return elegir(rng)

    monkeypatch.setattr(nacer.esp, "elegir_del_huevo", despues_de_mirar)

    def encontrar(_):
        try:
            return nacer.encontrar_al_primero(U, G, T0)
        except nacer.YaTieneGachamon:
            return None

    with ThreadPoolExecutor(max_workers=2) as hilos:
        encontrados = [n for n in hilos.map(encontrar, range(2)) if n]
    assert len(encontrados) == 1 and len(db.plantel(U, G)) == 1


def test_el_primero_no_nace_si_la_cuenta_se_vinculo_mientras_tanto():
    web = db.crear_identidad_web(12, G, T0).usuario_id
    poner_camas(web, 1, G)
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, "111111111111111111", G, T0) == "ok"
    with pytest.raises(nacer.YaNoEsSuIdentidad):
        nacer.encontrar_al_primero(web, G, T0)
    assert not db.tiene_gachamones(web, G)


def test_quien_se_quedo_sin_ninguno_puede_encontrar_al_primero():
    viejo = nace("Viejo")
    db.guardar(replace(viejo, muerta_en=T0, causa_muerte="hambre"))
    poner_camas(U, 1, G)
    primero = nacer.encontrar_al_primero(U, G, T0 + timedelta(days=5))
    assert primero.viva and primero.activa
    assert [c.id for c in db.plantel(U, G)] == [primero.id]
    assert db.por_id(viejo.id).muerta_en == T0


def test_bautizar_le_pone_nombre_una_vez():
    nacer.romper_el_huevo("u", "g", T0)
    assert nacer.bautizar("u", "g", "  Pelusa  ", T0).nombre == "Pelusa"
    assert db.criatura_activa("u", "g").nombre == "Pelusa"
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("u", "g", "Otra", T0)


@pytest.mark.parametrize("malo", ["", "   ", "<b>x</b>", "x" * 25, "Pelu🙂"])
def test_un_nombre_que_no_vale_no_bautiza(malo):
    nacida = nacer.romper_el_huevo("u", "g", T0)
    with pytest.raises(ValueError):
        nacer.bautizar("u", "g", malo, T0)
    assert db.criatura_activa("u", "g").nombre == nacida.nombre


def test_sin_gachamon_no_hay_a_quien_bautizar():
    with pytest.raises(nacer.NoSePuedeBautizar):
        nacer.bautizar("nadie", "g", "Pelusa", T0)


def test_no_nace_un_huerfano_si_la_cuenta_se_vinculo_mientras_tanto():
    import identidad

    web = db.crear_identidad_web(12, "g", T0).usuario_id
    codigo = db.pedir_codigo_de_vinculo(12, T0)
    assert db.canjear_codigo_de_vinculo(codigo, "111111111111111111", "g", T0) == "ok"
    with pytest.raises(nacer.YaNoEsSuIdentidad):
        nacer.romper_el_huevo(web, "g", T0)
    assert not db.tiene_gachamones(web, "g")
    assert identidad.es_web(web)


def test_una_identidad_web_vigente_si_puede_nacer():
    web = db.crear_identidad_web(12, "g", T0).usuario_id
    assert nacer.romper_el_huevo(web, "g", T0).usuario_id == web


def test_cuenta_vigente_solo_va_por_nombre():
    with pytest.raises(TypeError):
        db.crear("u", "g", "pulpo", "Tinta", (10, 10, 10, 10), T0, esp.MACHO,
                 "sereno", None, True, False, True)


def test_bautizar_no_toca_al_recluta():
    nacida = nacer.romper_el_huevo("u", "g", T0)
    nacer.bautizar("u", "g", "Pelusa", T0)
    recluta = db.crear("u", "g", "pulpo", "Brote", (10, 10, 10, 10), T0, activa=False)
    with pytest.raises(nacer.NoSePuedeBautizar) as caido:
        nacer.bautizar("u", "g", "Otra", T0)
    assert caido.value.motivo == "ya_bautizado"
    assert db.por_id(recluta.id).nombre == "Brote"
    assert db.por_id(nacida.id).nombre == "Pelusa"


def test_bautizar_no_toca_al_de_otra_persona():
    nacer.romper_el_huevo("a", "g", T0)
    ajena = nacer.romper_el_huevo("b", "g", T0)
    nacer.bautizar("a", "g", "Pelusa", T0)
    assert db.criatura_activa("b", "g").nombre == ajena.nombre


@pytest.mark.parametrize("como", [
    lambda n: n, str.upper, str.lower, lambda n: f"  {n}  ",
], ids=["igual", "mayusculas", "minusculas", "con_espacios"])
def test_el_nombre_de_su_especie_no_es_un_nombre_propio(como):
    nacida = nacer.romper_el_huevo("u", "g", T0, random.Random(3))
    especie = esp.ESPECIES[nacida.especie].nombre
    with pytest.raises(nacer.NombreNoVale) as caido:
        nacer.bautizar("u", "g", como(especie), T0)
    assert str(caido.value) == "Ese es el nombre de su especie. Ponle uno propio."
    assert nacer.espera_nombre(db.criatura_activa("u", "g"))
    # La transacción se deshizo sin dejar nada tomado: uno propio sí vale.
    assert nacer.bautizar("u", "g", "Pelusa", T0).nombre == "Pelusa"


def test_el_nombre_de_otra_especie_si_vale():
    nacida = nacer.romper_el_huevo("u", "g", T0, random.Random(3))
    otra = next(e.nombre for e in esp.ESPECIES.values() if e.clave != nacida.especie)
    assert nacer.bautizar("u", "g", otra, T0).nombre == otra


# --- El recluta llega con nombre ---------------------------------------------

def test_el_recluta_llega_con_el_nombre_que_se_puso_solo():
    activa = nace("Nube")                                  # ya hay una Nube
    poner_camas(U, 2, G)
    recluta = nacer.unir_recluta(
        U, G, especie="pollito", stats=STATS, genero=esp.HEMBRA, caracter=esp.CARACTER_POR_DEFECTO,
        ahora=T0, rng=random.Random(3),
    )
    assert recluta.nombre in nombres.NOMBRES and recluta.nombre != "Nube"
    assert recluta.se_nombro_solo and recluta.activa is False
    assert db.por_id(recluta.id) == recluta
    assert db.criatura_activa(U, G).id == activa.id
    assert db.marcador_de_persona(U, G)[lgr.RECLUTADOS] == 1


def test_el_nombre_de_un_recluta_se_elige_tambien_sin_ningun_gachamon():
    assert nacer.nombre_de_recluta(U, G, "pollito", random.Random(1)) in nombres.NOMBRES


def test_al_activo_que_se_nombro_solo_se_le_puede_bautizar_una_vez():
    """Un recluta que se queda solo en el plantel pasa a ser el activo con el
    nombre que se puso; el bautizo del activo también se lo deja cambiar, una
    vez."""
    poner_camas(U, 1, G)
    recluta = nacer.unir_recluta(
        U, G, especie="pollito", stats=STATS, genero=esp.HEMBRA,
        caracter=esp.CARACTER_POR_DEFECTO, ahora=T0, rng=random.Random(3),
    )
    assert db.activa_al_dia(U, G, T0).id == recluta.id

    bautizada = nacer.bautizar(U, G, "Rayo", T0)

    assert bautizada.nombre == "Rayo" and bautizada.se_nombro_solo is False
    assert db.por_id(recluta.id) == bautizada
    with pytest.raises(nacer.NoSePuedeBautizar) as caido:
        nacer.bautizar(U, G, "Otra", T0)
    assert caido.value.motivo == nacer.YA_BAUTIZADO
