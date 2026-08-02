"""Las medallas: que se ganen cuando toca, y que sean de quien deben."""
from datetime import datetime, timedelta, timezone

import pytest

import aventura as av
import especies as esp
import logros
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def criatura(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pulpo", nombre="Prueba",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def cumplidos(marcador=None, bicho=None, ahora=T0):
    hechos = logros.hechos_de(bicho or criatura(), marcador or {}, ahora)
    return {l.clave for l in logros.cumplidos(hechos, logros.GACHAMON)}


def cumplidos_de_persona(marcador=None, especies=()):
    hechos = logros.hechos_de_la_persona(marcador or {}, especies)
    return {l.clave for l in logros.cumplidos(hechos, logros.PERSONA)}


# --- El catálogo -----------------------------------------------------------

def test_ningun_logro_esta_a_medias():
    for logro in logros.LOGROS:
        assert logro.clave and logro.nombre.strip(), logro.clave
        assert logro.como.strip(), logro.clave
        assert logro.meta > 0 and logro.gemas > 0, logro.clave


def test_ninguna_clave_ni_nombre_se_repite():
    claves = [logro.clave for logro in logros.LOGROS]
    nombres = [logro.nombre for logro in logros.LOGROS]
    assert len(set(claves)) == len(claves)
    assert len(set(nombres)) == len(nombres)


def test_todo_logro_mira_un_hecho_que_alguien_rellena():
    """Un logro que mire una clave que nadie cuenta no se gana nunca, y no hay
    forma de notarlo jugando: sólo se ve leyendo el código.

    Se comprueba por dueño: un logro del gachamon que mirase un hecho que sólo
    existe en la persona tampoco se ganaría, y ése es el fallo que puede colarse
    justo ahora que hay dos marcadores.
    """
    del_gachamon = {
        logros.CARRERAS, logros.SUMOS, logros.TOTEMS, logros.TORNEOS,
        logros.AVENTURAS, logros.NODOS, logros.CUIDADOS,
    } | set(logros.hechos_de(criatura(), {}, T0))
    de_la_persona = {logros.RECLUTADOS} | set(
        logros.hechos_de_la_persona({}, ())
    )

    for logro in logros.del_gachamon():
        assert logro.hecho in del_gachamon, logro.clave
    for logro in logros.de_la_persona():
        assert logro.hecho in de_la_persona, logro.clave


def test_los_dos_juegos_de_medallas_no_se_solapan():
    """Cada medalla es de uno o del otro, y entre las dos listas están las
    todas: si alguna se cayera de las dos, no se ganaría jamás."""
    suyas = logros.del_gachamon()
    mias = logros.de_la_persona()
    assert set(suyas) | set(mias) == set(logros.LOGROS)
    assert not set(suyas) & set(mias)
    assert {l.clave for l in mias} == {
        "domador", "flautista", "uno_entre_veinticinco"
    }


# --- Que se ganen cuando toca ----------------------------------------------

def test_recien_nacido_no_tiene_casi_nada():
    """Sólo «De la alfa», que se lleva por existir mientras la alfa siga
    abierta."""
    assert cumplidos() == {"de_la_alfa"}


def test_el_contador_justo_por_debajo_no_desbloquea():
    assert "velocista" not in cumplidos({logros.CARRERAS: 9})
    assert "velocista" in cumplidos({logros.CARRERAS: 10})


@pytest.mark.parametrize(("clave", "marcador"), [
    ("bolido", {logros.CARRERAS: 100}),
    ("luchador", {logros.SUMOS: 10}),
    ("yokozuna", {logros.SUMOS: 100}),
    ("asaltante", {logros.TOTEMS: 10}),
    ("dinastia", {logros.TORNEOS: 10}),
    ("explorador", {logros.AVENTURAS: 10}),
    ("paso_firme", {logros.NODOS: 50}),
    ("consentido", {logros.CUIDADOS: 100}),
    ("malcriado", {logros.CUIDADOS: 500}),
])
def test_cada_logro_de_contador_se_gana_con_lo_suyo(clave, marcador):
    assert clave in cumplidos(marcador)


def test_la_primera_victoria_sale_de_lo_que_ya_se_guardaba():
    """`victorias` existe desde siempre: este logro no necesita contador."""
    assert "primera_sangre" not in cumplidos()
    assert "primera_sangre" in cumplidos(bicho=criatura(victorias=1))


def test_bien_criado_es_llegar_a_la_forma_final():
    assert "bien_criado" not in cumplidos(bicho=criatura(nivel=4))
    assert "bien_criado" in cumplidos(bicho=criatura(nivel=5))


def test_veterano_cuenta_dias_enteros():
    casi = criatura(nacida_en=T0 - timedelta(days=29, hours=23))
    justo = criatura(nacida_en=T0 - timedelta(days=30))
    assert "veterano" not in cumplidos(bicho=casi)
    assert "veterano" in cumplidos(bicho=justo)


def test_cartografo_pide_los_diez_biomas_distintos():
    """Pisar el volcán diez veces no es haber pisado diez biomas, y por eso se
    guarda una clave por bioma en vez de un número."""
    mismo = {logros.clave_de_bioma("volcan"): 10}
    assert "cartografo" not in cumplidos(mismo)

    todos = {logros.clave_de_bioma(b): 1 for b in av.BIOMAS}
    assert len(todos) == 10
    assert "cartografo" in cumplidos(todos)


# --- Las tres que son de la persona ----------------------------------------

def test_reclutar_es_de_la_persona_y_no_de_ningun_gachamon():
    """Lo pedido: a la aventura vas tú, así que convencer al salvaje lo haces
    tú. Un gachamon con el contador puesto no gana nada, porque ese contador ya
    no vive en su marcador."""
    assert cumplidos_de_persona({logros.RECLUTADOS: 1}) == {"domador"}
    assert cumplidos_de_persona({logros.RECLUTADOS: 10}) == {
        "domador", "flautista"
    }
    assert not cumplidos({logros.RECLUTADOS: 10}) & {"domador", "flautista"}


def test_uno_entre_veinticinco_es_de_la_persona_y_cuenta_las_muertas():
    """Que te saliera una rara no deja de haber pasado porque se te muriera, y
    por eso mira todas tus especies y no la que lleves activa."""
    comunes = ("pulpo", "michi", "pollito")
    assert "uno_entre_veinticinco" not in cumplidos_de_persona(especies=comunes)

    raras = [c for c, d in esp.ESPECIES.items() if d.rareza == esp.RARA]
    assert len(raras) == 3
    for clave in raras:
        assert "uno_entre_veinticinco" in cumplidos_de_persona(
            especies=(*comunes, clave)
        )


def test_un_jugador_que_lo_ha_hecho_todo_gana_las_tres():
    conseguidos = cumplidos_de_persona(
        {logros.RECLUTADOS: 10}, especies=("dragoncito",)
    )
    assert conseguidos == {l.clave for l in logros.de_la_persona()}


def test_superviviente_pide_seguir_vivo():
    """El único con dos condiciones: cien aventuras no valen si te has muerto
    por el camino."""
    marcador = {logros.AVENTURAS: 100}
    assert "superviviente" in cumplidos(marcador)

    muerta = criatura(muerta_en=T0, causa_muerte="hambre")
    conseguidos = cumplidos(marcador, bicho=muerta)
    assert "superviviente" not in conseguidos
    # Y los demás sí los conserva: morirse no borra lo que hizo en vida.
    assert "explorador" in conseguidos


def test_la_alfa_se_puede_cerrar(monkeypatch):
    """Mientras `FIN_DE_LA_ALFA` sea None la alfa sigue abierta y cualquiera se
    lleva la medalla. Al ponerle fecha, quien nazca después ya no."""
    assert "de_la_alfa" in cumplidos()

    monkeypatch.setattr(logros, "FIN_DE_LA_ALFA", T0)
    veterana = criatura(nacida_en=T0 - timedelta(days=1))
    novata = criatura(nacida_en=T0 + timedelta(days=1))
    assert "de_la_alfa" in cumplidos(bicho=veterana)
    assert "de_la_alfa" not in cumplidos(bicho=novata)


def test_un_gachamon_hecho_de_todo_gana_todas_las_suyas():
    """Que ninguna se quede inalcanzable por una clave mal escrita."""
    marcador = {
        logros.CARRERAS: 100, logros.SUMOS: 100, logros.TOTEMS: 10,
        logros.TORNEOS: 10, logros.AVENTURAS: 100, logros.NODOS: 50,
        logros.CUIDADOS: 500,
    }
    marcador.update({logros.clave_de_bioma(b): 1 for b in av.BIOMAS})
    campeon = criatura(
        especie="dragoncito", nivel=5, victorias=200,
        nacida_en=T0 - timedelta(days=40),
    )

    assert cumplidos(marcador, bicho=campeon) == {
        l.clave for l in logros.del_gachamon()
    }
