"""El camino completo de un consumible: comprarlo, usarlo y notarlo peleando."""
import random
from datetime import datetime, timedelta, timezone

import pytest

import competir as comp
import db
import economia
import objetos as obj
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1"):
    return db.crear(usuario, "g1", "pulpo", "Prueba", STATS, T0)


_evento = 0


def comprar(objeto):
    global _evento
    _evento += 1
    return economia.comprar(f"tienda-{_evento}", "u1", "g1", objeto, T0)


class DadoFijo(random.Random):
    def __init__(self, valor):
        super().__init__()
        self.valor = valor

    def randint(self, a, b):
        return min(self.valor, b)


def usar(objeto, rng=None, ahora=T0):
    """Usar una unidad de la mochila, con un evento nuevo cada vez."""
    global _evento
    _evento += 1
    return economia.usar_objeto(f"uso-{_evento}", "u1", "g1", objeto, ahora, rng)


def renombrar(propuesto):
    """Cambiar el nombre con la placa, con un evento nuevo cada vez."""
    global _evento
    _evento += 1
    placa = obj.CATALOGO["placa"]
    return economia.renombrar_con_placa(
        f"placa-{_evento}", "u1", "g1", placa, propuesto, T0
    )


def dar(objeto, cuantos=1):
    with db.conectar() as con:
        db.guardar_en_la_mochila_en(con, "u1", "g1", objeto.clave, cuantos)


# --- De la tienda a la pelea ------------------------------------------------

def test_comprar_beber_y_que_se_note_en_la_carrera():
    """El recorrido entero: es lo que no se puede probar por partes."""
    criatura = nacer()
    pocion = obj.CATALOGO["velocidad_1d10"]

    assert comprar(pocion)
    resultado = usar(pocion, DadoFijo(6))
    assert resultado.ok and db.inventario("u1", "g1") == {}
    assert resultado.bonus == 6 and resultado.stats == ("velocidad",)

    bonus = db.efecto_activo(criatura.id, "velocidad", T0)
    competidor = comp.competidor_de(criatura, bonus_velocidad=bonus)
    normal = comp.competidor_de(criatura)

    assert competidor.base_en(comp.SALIDA) == normal.base_en(comp.SALIDA) + 6
    assert competidor.base_en(comp.TERRENO) == normal.base_en(comp.TERRENO) + 4


def test_la_pocion_de_fuerza_ayuda_en_terreno_sin_volverse_de_velocidad():
    criatura = nacer()
    dar(obj.CATALOGO["fuerza_1d12"])
    usar(obj.CATALOGO["fuerza_1d12"], DadoFijo(12))

    bonus = db.efecto_activo(criatura.id, "fuerza", T0)
    normal = comp.competidor_de(criatura)
    con_fuerza = comp.competidor_de(criatura, bonus_fuerza=bonus)

    assert bonus == 12
    assert db.efecto_activo(criatura.id, "velocidad", T0) == 0
    assert con_fuerza.base_en(comp.TERRENO) == normal.base_en(comp.TERRENO) + 4


def test_al_caducar_deja_de_ayudar():
    criatura = nacer()
    dar(obj.CATALOGO["fuerza_1d8"])
    usar(obj.CATALOGO["fuerza_1d8"], DadoFijo(8))
    tarde = T0 + timedelta(minutes=obj.MINUTOS_DE_EFECTO + 1)

    assert db.efecto_activo(criatura.id, "fuerza", tarde) == 0
    assert comp.competidor_de(
        criatura, bonus_fuerza=0
    ).base_en(comp.EMPUJE) == comp.competidor_de(criatura).base_en(comp.EMPUJE)


# --- Los otros objetos -----------------------------------------------------

def test_la_pocion_de_comida_llena_y_se_guarda():
    criatura = db.guardar(sim.avanzar(nacer(), T0))
    from dataclasses import replace
    db.guardar(replace(db.criatura_activa("u1", "g1"), hambre=12.0))
    hambrienta = db.criatura_activa("u1", "g1")
    assert hambrienta.hambre == 12.0
    dar(obj.CATALOGO["pocion_comida"])

    usar(obj.CATALOGO["pocion_comida"])

    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_el_silbato_deja_entrenar_otra_vez():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0
    dar(obj.CATALOGO["silbato"])

    usar(obj.CATALOGO["silbato"])

    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)


def test_el_descanso_solo_toca_el_de_competir():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    dar(obj.CATALOGO["descanso_rapido"])

    usar(obj.CATALOGO["descanso_rapido"])

    assert db.espera_de(criatura.id, sim.COMPETIR, T0) == timedelta(0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0


# --- La placa con nombre ---------------------------------------------------

def test_renombrar_gasta_la_placa_y_cambia_el_nombre():
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    resultado = renombrar("  Pelusa  ")

    assert resultado.ok and resultado.criatura.nombre == "Pelusa"
    assert db.criatura_activa("u1", "g1").nombre == "Pelusa"
    assert db.inventario("u1", "g1") == {}


def test_un_nombre_invalido_no_gasta_la_placa():
    """Si se gastara antes de validar, escribir un nombre con caracteres raros
    te costaría el objeto sin cambiar nada."""
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    for malo in ("", "   ", "a" * 40, "Pelusa <@everyone>", "```ansi"):
        resultado = renombrar(malo)
        assert not resultado.ok and resultado.motivo == "nombre", (
            f"«{malo}» no debería valer"
        )

    assert db.inventario("u1", "g1") == {"placa": 1}, "la placa sigue ahí"
    assert db.criatura_activa("u1", "g1").nombre == "Prueba"


def test_sin_placa_no_se_renombra():
    nacer()
    resultado = renombrar("Pelusa")
    assert not resultado.ok and resultado.motivo == "no_tienes", (
        "no debería dejar renombrar sin la placa"
    )
    assert db.criatura_activa("u1", "g1").nombre == "Prueba"


def test_renombrar_al_mismo_nombre_no_gasta_nada():
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    resultado = renombrar("Prueba")
    assert not resultado.ok and resultado.motivo == "mismo_nombre", (
        "cambiar por el mismo nombre no debería gastar la placa"
    )
    assert db.inventario("u1", "g1") == {"placa": 1}


# --- Que ningún objeto mienta sobre lo que hizo -----------------------------

def con_hambre(valor: float):
    """La criatura activa con el hambre puesta. La crea sólo la primera vez:
    sólo puede haber una activa por persona."""
    from dataclasses import replace

    criatura = db.criatura_activa("u1", "g1") or nacer()
    db.guardar(replace(criatura, hambre=valor))
    return db.criatura_activa("u1", "g1")


def test_las_golosinas_alimentan_lo_que_dicen():
    """El fallo: usarlas desde la mochila las gastaba, no tocaba el hambre y el
    mensaje decía «Hambre al 100». No es que llenara de más — es que no hacía
    nada y lo contaba como si sí."""
    golosinas = obj.CATALOGO["golosinas"]
    con_hambre(30.0)
    dar(golosinas)

    resultado = usar(golosinas)

    assert db.criatura_activa("u1", "g1").hambre == 30.0 + golosinas.alimenta
    assert resultado.comida == golosinas.alimenta
    assert resultado.criatura.hambre == 30.0 + golosinas.alimenta


def test_las_golosinas_no_pasan_de_cien():
    golosinas = obj.CATALOGO["golosinas"]
    con_hambre(90.0)
    dar(golosinas)
    usar(golosinas)
    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_la_pocion_de_comida_sigue_llenando_del_todo():
    """El cambio de bandera a número no puede tocarle nada."""
    con_hambre(12.0)
    dar(obj.CATALOGO["pocion_comida"])
    usar(obj.CATALOGO["pocion_comida"])
    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_ningun_objeto_miente_sobre_lo_que_hizo():
    """El invariante que cubre la clase entera del fallo, no sólo las golosinas.

    Usar cualquier cosa del catálogo desde la mochila **o hace lo que dice, o se
    niega**. Lo que no puede es devolver un mensaje inventado, que es lo que
    pasaba por tener un caso por descarte al final de `usar`.

    Cada uno con algo que hacer (hambre, esperas): lo que no haría nada se niega
    con `no_hace_falta`, y eso tiene sus propias pruebas.
    """
    for clave, objeto in obj.CATALOGO.items():
        criatura = con_hambre(40.0)
        for accion in (sim.ENTRENAR, sim.COMPETIR):
            db.poner_cooldown(criatura.id, accion, T0)
        antes = db.criatura_activa("u1", "g1")
        dar(objeto)

        resultado = economia.usar_objeto(f"miente-{clave}", "u1", "g1", objeto, T0)
        if not resultado.ok:
            # La placa entra aquí y es correcto: se usa desde la mochila, pero
            # abre un formulario y se resuelve en `renombrar_con_placa`, no en
            # `usar_objeto`.
            assert resultado.motivo == "no_se_usa", (clave, resultado.motivo)
            assert not objeto.se_aplica_al_momento, (
                f"{clave} dice aplicarse al momento pero se niega"
            )
            continue

        assert objeto.se_aplica_al_momento, f"{clave} no debería poder usarse aquí"
        despues = db.criatura_activa("u1", "g1")

        if objeto.alimenta:
            assert despues.hambre > antes.hambre, clave
            assert resultado.comida == round(despues.hambre - antes.hambre), clave
        elif objeto.stat:
            assert db.efecto_activo(criatura.id, objeto.stat, T0) > 0, clave
        elif objeto.reinicia:
            assert db.espera_de(criatura.id, objeto.reinicia, T0) == timedelta(0)

        # Y en ningún caso puede prometer comida quien no la da.
        if not objeto.alimenta:
            assert resultado.comida == 0, (clave, resultado.comida)


def test_un_objeto_sin_uso_en_la_mochila_no_se_gasta():
    """La comprobación va antes de gastar: hoy `db.gastar` corre primero, así
    que un objeto sin uso ahí te costaría la unidad a cambio de nada."""
    from dataclasses import replace

    solo_cebo = replace(
        obj.CATALOGO["golosinas"], clave="solo_cebo", alimenta=0, ceba=True
    )
    assert not solo_cebo.se_usa_en_mochila

    con_hambre(40.0)
    dar(solo_cebo)
    resultado = usar(solo_cebo)
    assert not resultado.ok and resultado.motivo == "no_se_usa", (
        "un objeto sin uso en la mochila debería negarse"
    )
    assert db.criatura_activa("u1", "g1").hambre == 40.0
    assert db.inventario("u1", "g1") == {"solo_cebo": 1}


def test_las_golosinas_siguen_valiendo_de_cebo():
    """Lo que no se puede romper al arreglar esto."""
    import aventura as av

    golosinas = obj.CATALOGO["golosinas"]
    assert golosinas.ceba
    assert av.GOLOSINAS in av.OPCIONES
    assert av.BASE[av.GOLOSINAS] > 0
