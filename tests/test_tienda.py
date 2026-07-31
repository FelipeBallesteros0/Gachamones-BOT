"""El camino completo de un consumible: comprarlo, usarlo y notarlo peleando."""
import random
from datetime import datetime, timedelta, timezone

import pytest

import competir as comp
import db
import economia
import objetos as obj
import simulacion as sim
import tienda

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


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


# --- De la tienda a la pelea ------------------------------------------------

def test_comprar_beber_y_que_se_note_en_la_carrera():
    """El recorrido entero: es lo que no se puede probar por partes."""
    criatura = nacer()
    pocion = obj.CATALOGO["velocidad_1d10"]

    assert comprar(pocion)
    assert db.gastar("u1", "g1", pocion.clave)
    aviso = tienda.usar(criatura, pocion, T0, DadoFijo(6))
    assert "+6" in aviso and "velocidad" in aviso

    bonus = db.efecto_activo(criatura.id, "velocidad", T0)
    competidor = comp.competidor_de(criatura, comp.CARRERA, bonus)
    normal = comp.competidor_de(criatura, comp.CARRERA)

    assert competidor.base == normal.base + 6


def test_la_pocion_de_fuerza_no_ayuda_en_la_carrera():
    """Cada poción sirve donde dice: la de fuerza, en el sumo."""
    criatura = nacer()
    tienda.usar(criatura, obj.CATALOGO["fuerza_1d12"], T0, DadoFijo(12))

    assert db.efecto_activo(criatura.id, comp.STATS[comp.SUMO], T0) == 12
    assert db.efecto_activo(criatura.id, comp.STATS[comp.CARRERA], T0) == 0


def test_al_caducar_deja_de_ayudar():
    criatura = nacer()
    tienda.usar(criatura, obj.CATALOGO["fuerza_1d8"], T0, DadoFijo(8))
    tarde = T0 + timedelta(minutes=obj.MINUTOS_DE_EFECTO + 1)

    assert db.efecto_activo(criatura.id, "fuerza", tarde) == 0
    assert comp.competidor_de(criatura, comp.SUMO, 0).base == \
        comp.competidor_de(criatura, comp.SUMO).base


# --- Los otros objetos -----------------------------------------------------

def test_la_pocion_de_comida_llena_y_se_guarda():
    criatura = db.guardar(sim.avanzar(nacer(), T0))
    from dataclasses import replace
    db.guardar(replace(db.criatura_activa("u1", "g1"), hambre=12.0))
    hambrienta = db.criatura_activa("u1", "g1")
    assert hambrienta.hambre == 12.0

    tienda.usar(hambrienta, obj.CATALOGO["pocion_comida"], T0)

    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_el_silbato_deja_entrenar_otra_vez():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0

    tienda.usar(criatura, obj.CATALOGO["silbato"], T0)

    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)


def test_el_descanso_solo_toca_el_de_competir():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)

    tienda.usar(criatura, obj.CATALOGO["descanso_rapido"], T0)

    assert db.espera_de(criatura.id, sim.COMPETIR, T0) == timedelta(0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0


# --- Los textos de los menús -----------------------------------------------

def test_la_mochila_vacia_manda_a_la_tienda():
    texto = tienda.texto_del_inventario("u1", "g1")
    assert "Tienda" in texto and "50" in texto and "asciigems" in texto


def test_la_mochila_cuenta_lo_que_hay():
    comprar(obj.CATALOGO["silbato"])
    comprar(obj.CATALOGO["silbato"])
    comprar(obj.CATALOGO["pocion_comida"])

    texto = tienda.texto_del_inventario("u1", "g1")
    assert "×2" in texto and "Silbato del entrenador" in texto
    assert "Poción de comida" in texto


def test_la_tienda_dice_los_dos_saldos():
    texto = tienda.texto_de_la_tienda("u1", "g1")
    assert "50" in texto and "asciicoins" in texto and "asciigems" in texto


def test_un_objeto_que_ya_no_existiera_no_rompe_la_mochila():
    """Si algún día se retira un objeto del catálogo, quien lo tuviera guardado
    no puede quedarse con la mochila rota."""
    with db.conectar() as con:
        con.execute(
            "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
            "VALUES ('u1', 'g1', 'objeto_retirado', 3)"
        )
    texto = tienda.texto_del_inventario("u1", "g1")
    assert "objeto_retirado" not in texto


# --- La placa con nombre ---------------------------------------------------

def test_renombrar_gasta_la_placa_y_cambia_el_nombre():
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    aviso = tienda.renombrar("u1", "g1", placa, "  Pelusa  ")

    assert "Pelusa" in aviso
    assert db.criatura_activa("u1", "g1").nombre == "Pelusa"
    assert db.inventario("u1", "g1") == {}


def test_un_nombre_invalido_no_gasta_la_placa():
    """Si se gastara antes de validar, escribir un nombre con caracteres raros
    te costaría el objeto sin cambiar nada."""
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    for malo in ("", "   ", "a" * 40, "Pelusa <@everyone>", "```ansi"):
        try:
            tienda.renombrar("u1", "g1", placa, malo)
        except ValueError:
            pass
        else:
            raise AssertionError(f"«{malo}» no debería valer")

    assert db.inventario("u1", "g1") == {"placa": 1}, "la placa sigue ahí"
    assert db.criatura_activa("u1", "g1").nombre == "Prueba"


def test_sin_placa_no_se_renombra():
    nacer()
    try:
        tienda.renombrar("u1", "g1", obj.CATALOGO["placa"], "Pelusa")
    except ValueError:
        assert db.criatura_activa("u1", "g1").nombre == "Prueba"
        return
    raise AssertionError("no debería dejar renombrar sin la placa")


def test_renombrar_al_mismo_nombre_no_gasta_nada():
    nacer()
    placa = obj.CATALOGO["placa"]
    comprar(placa)

    try:
        tienda.renombrar("u1", "g1", placa, "Prueba")
    except ValueError:
        assert db.inventario("u1", "g1") == {"placa": 1}
        return
    raise AssertionError("cambiar por el mismo nombre no debería gastar la placa")


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
    criatura = con_hambre(30.0)

    aviso = tienda.usar(criatura, golosinas, T0)

    assert db.criatura_activa("u1", "g1").hambre == 30.0 + golosinas.alimenta
    assert f"+{golosinas.alimenta}" in aviso
    assert "100" not in aviso


def test_las_golosinas_no_pasan_de_cien():
    golosinas = obj.CATALOGO["golosinas"]
    criatura = con_hambre(90.0)
    tienda.usar(criatura, golosinas, T0)
    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_la_pocion_de_comida_sigue_llenando_del_todo():
    """El cambio de bandera a número no puede tocarle nada."""
    criatura = con_hambre(12.0)
    tienda.usar(criatura, obj.CATALOGO["pocion_comida"], T0)
    assert db.criatura_activa("u1", "g1").hambre == 100.0


def test_ningun_objeto_miente_sobre_lo_que_hizo():
    """El invariante que cubre la clase entera del fallo, no sólo las golosinas.

    Usar cualquier cosa del catálogo desde la mochila **o hace lo que dice, o se
    niega**. Lo que no puede es devolver un mensaje inventado, que es lo que
    pasaba por tener un caso por descarte al final de `usar`.
    """
    for clave, objeto in obj.CATALOGO.items():
        criatura = con_hambre(40.0)
        antes = db.criatura_activa("u1", "g1")

        try:
            aviso = tienda.usar(criatura, objeto, T0)
        except ValueError:
            # La placa entra aquí y es correcto: se usa desde la mochila, pero
            # abre un formulario y se resuelve en `renombrar`, no en `usar`.
            assert not objeto.se_aplica_al_momento, (
                f"{clave} dice aplicarse al momento pero se niega"
            )
            continue

        assert objeto.se_aplica_al_momento, f"{clave} no debería poder usarse aquí"
        despues = db.criatura_activa("u1", "g1")

        if objeto.alimenta:
            assert despues.hambre > antes.hambre, clave
            assert str(round(despues.hambre - antes.hambre)) in aviso, clave
        elif objeto.stat:
            assert db.efecto_activo(criatura.id, objeto.stat, T0) > 0, clave
        elif objeto.reinicia:
            assert db.espera_de(criatura.id, objeto.reinicia, T0) == timedelta(0)

        # Y en ningún caso puede prometer comida quien no la da.
        if not objeto.alimenta:
            assert "hambre" not in aviso.lower(), (clave, aviso)


def test_un_objeto_sin_uso_en_la_mochila_no_se_gasta():
    """La comprobación va antes de gastar: hoy `db.gastar` corre primero, así
    que un objeto sin uso ahí te costaría la unidad a cambio de nada."""
    from dataclasses import replace

    solo_cebo = replace(
        obj.CATALOGO["golosinas"], clave="solo_cebo", alimenta=0, ceba=True
    )
    assert not solo_cebo.se_usa_en_mochila

    criatura = con_hambre(40.0)
    try:
        tienda.usar(criatura, solo_cebo, T0)
    except ValueError:
        assert db.criatura_activa("u1", "g1").hambre == 40.0
        return
    raise AssertionError("un objeto sin uso en la mochila debería negarse")


def test_las_golosinas_siguen_valiendo_de_cebo():
    """Lo que no se puede romper al arreglar esto."""
    import aventura as av

    golosinas = obj.CATALOGO["golosinas"]
    assert golosinas.ceba
    assert av.GOLOSINAS in av.OPCIONES
    assert av.BASE[av.GOLOSINAS] > 0
