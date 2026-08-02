"""Carreras, sumo y torneos: dados fijos y marcos que no se descuadran."""
import random
import re
from datetime import datetime, timezone

import competir as comp
import especies as esp
import pantalla
import simulacion as sim

ANSI = re.compile(r"\x1b\[[0-9;]*m")
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


class DadosFijos(random.Random):
    """Dados guionizados: se recorren en orden y se repiten en bucle."""

    def __init__(self, valores):
        super().__init__()
        self.valores = list(valores)
        self.i = 0

    def randint(self, a, b):
        valor = self.valores[self.i % len(self.valores)]
        self.i += 1
        return valor

    def shuffle(self, x, *args, **kwargs):
        """El sorteo del torneo, también guionizado: no mezcla.

        Hace falta porque `random.Random.shuffle` no pasa por `randint` sino por
        `getrandbits`, que sigue siendo el del sistema: sin esto las parejas del
        torneo saldrían distintas en cada ejecución y ningún test del cuadro
        sería reproducible. Dejando el orden de invitación, la pareja de un test
        es la que se escribe.
        """
        return None


def competidor(
    nombre="A", especie="pulpo", stat=10, modificador=0, animo=esp.NORMAL,
    *, fuerza=None, velocidad=None, salud=None,
    bonus_fuerza=0, bonus_velocidad=0,
):
    return comp.Competidor(
        nombre=nombre,
        especie=especie,
        fuerza=stat if fuerza is None else fuerza,
        velocidad=stat if velocidad is None else velocidad,
        salud=stat if salud is None else salud,
        modificador=modificador,
        bonus_fuerza=bonus_fuerza,
        bonus_velocidad=bonus_velocidad,
        animo=animo,
    )


def combate(competidores, tipo, rng):
    """Un encuentro de un solo combate: `(encuentro, su único Resultado)`."""
    encuentro = comp.enfrentar(competidores, tipo, rng)
    return encuentro, encuentro.combates[0]


def espera_error(competidores, tipo, motivo):
    try:
        comp.enfrentar(competidores, tipo, DadosFijos([10]))
    except ValueError:
        return
    raise AssertionError(motivo)


# --- Resolución ------------------------------------------------------------

def test_las_seis_fases_usan_sus_mezclas_y_bonus_antes_del_estado():
    c = competidor(
        fuerza=10, velocidad=20, salud=30,
        bonus_fuerza=2, bonus_velocidad=4,
    )

    assert {
        fase: c.base_en(fase)
        for fase in (*comp.FASES_CARRERA, *comp.FASES_SUMO)
    } == {
        comp.SALIDA: 24,
        comp.TERRENO: 20,
        comp.FONDO: 26,
        comp.POSICION: 16,
        comp.EMPUJE: 12,
        comp.AGUANTE: 17,
    }

    con_estado = competidor(
        fuerza=10, velocidad=20, salud=30, modificador=2,
        bonus_fuerza=2, bonus_velocidad=4,
    )
    assert con_estado.base_en(comp.TERRENO) == 22
    assert con_estado.base_en(comp.POSICION) == 18


def test_las_mezclas_redondean_a_par_y_la_base_se_clampa():
    assert competidor(fuerza=5, velocidad=10).base_en(comp.TERRENO) == 8
    assert competidor(fuerza=10, velocidad=5).base_en(comp.TERRENO) == 6

    debil = competidor(stat=1, modificador=-5)
    assert all(
        debil.base_en(fase) == 1
        for fase in (*comp.FASES_CARRERA, *comp.FASES_SUMO)
    )


def test_sopaipilla_aporta_el_bonus_completo_en_mezclas_fuerza_velocidad():
    normal = competidor(fuerza=10, velocidad=20)
    sopa = competidor(
        fuerza=10, velocidad=20, bonus_fuerza=7, bonus_velocidad=7
    )

    assert sopa.base_en(comp.TERRENO) == normal.base_en(comp.TERRENO) + 7
    assert sopa.base_en(comp.POSICION) == normal.base_en(comp.POSICION) + 7


def test_carrera_juega_fases_nombradas_y_suma_sus_puntos():
    a = competidor("A", fuerza=10, velocidad=20, salud=30)
    b = competidor("B", fuerza=30, velocidad=10, salud=20)
    dados = DadosFijos([5, 1, 5, 1, 5, 1])
    _, r = combate([a, b], comp.CARRERA, dados)

    assert [ronda.fase for ronda in r.rondas] == list(comp.FASES_CARRERA)
    assert [ronda.totales for ronda in r.rondas] == [
        (25, 11),
        (22, 17),
        (28, 14),
    ]
    assert r.totales == (75, 42)
    assert r.marcadores == r.totales
    assert dados.i == 6


def test_gana_quien_suma_mas_no_quien_gana_mas_tramos():
    """Carrera sigue siendo acumulativa: manda la suma de las tres fases."""
    a = competidor("A", stat=0)
    b = competidor("B", stat=0)
    # A: 20, 1, 1 = 22+3(base mínima) ... B: 1, 20, 20 = 41+3
    _, r = combate([a, b], comp.CARRERA, DadosFijos([20, 1, 1, 20, 1, 20]))
    assert r.orden[0] == 1
    assert r.competidor_ganador.nombre == "B"


def test_sumo_para_en_dos_cero_y_no_juega_aguante():
    dados = DadosFijos([20, 1, 20, 1, 99])
    _, r = combate(
        [competidor("A", stat=10), competidor("B", stat=10)],
        comp.SUMO,
        dados,
    )

    assert [ronda.fase for ronda in r.rondas] == [comp.POSICION, comp.EMPUJE]
    assert r.marcadores == (2, 0)
    assert r.orden == (0, 1)
    assert dados.i == 4


def test_sumo_dos_a_un_lo_gana_por_intercambios_aunque_pierda_la_suma():
    dados = DadosFijos([2, 1, 1, 20, 2, 1])
    _, r = combate(
        [competidor("A", stat=10), competidor("B", stat=10)],
        comp.SUMO,
        dados,
    )

    assert [ronda.fase for ronda in r.rondas] == list(comp.FASES_SUMO)
    assert r.marcadores == (2, 1)
    assert r.totales == (35, 52)
    assert r.orden == (0, 1)
    assert dados.i == 6


def test_el_empate_de_sumo_se_repite_oculto_en_la_misma_fase():
    dados = DadosFijos([5, 5, 6, 4, 20, 1])
    _, r = combate(
        [competidor("A", stat=10), competidor("B", stat=10)],
        comp.SUMO,
        dados,
    )

    assert len(r.rondas) == 2
    assert r.rondas[0].fase == comp.POSICION
    assert r.rondas[0].dados == (6, 4)
    assert r.rondas[0].desempates == 1
    assert r.desempates == 1
    assert dados.i == 6


def test_un_empate_se_desempata_con_tramos_extra():
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    # Tres tramos idénticos -> empate; en el cuarto A saca más.
    dados = [5, 5, 5, 5, 5, 5, 20, 1]
    _, r = combate([a, b], comp.CARRERA, DadosFijos(dados))

    assert r.desempates == 1
    assert len(r.rondas) == 4
    assert r.orden[0] == 0


def test_los_desempates_de_sumo_tienen_tope_y_fallback_determinista():
    """Cada intercambio empatado se acota y el dorsal menor gana el fallback."""
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    dados = DadosFijos([7])
    _, r = combate([a, b], comp.SUMO, dados)

    assert len(r.rondas) == 2
    assert [ronda.desempates for ronda in r.rondas] == [
        comp.MAX_DESEMPATES,
        comp.MAX_DESEMPATES,
    ]
    assert r.desempates == 2 * comp.MAX_DESEMPATES
    assert r.marcadores == (2, 0)
    assert r.orden == (0, 1)
    assert dados.i == 4 * (comp.MAX_DESEMPATES + 1)


def test_al_agotar_los_desempates_manda_el_orden_de_llegada():
    """Con todo empatado el orden lo decide el índice, que es el equivalente al
    «gana `a` los empates» de cuando la carrera era de dos."""
    cinco = [competidor(f"C{i}", stat=10) for i in range(5)]
    _, r = combate(cinco, comp.CARRERA, DadosFijos([7]))

    assert len(set(r.totales)) == 1, r.totales
    assert r.orden == (0, 1, 2, 3, 4)


def test_competidor_de_conserva_stats_bonus_y_estado_visual():
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=30, base_velocidad=5, base_salud=10,
        hambre=90.0, animo=90.0,
    )
    c = comp.competidor_de(
        criatura, bonus_fuerza=7, bonus_velocidad=4
    )

    assert (c.fuerza, c.velocidad, c.salud) == (30, 5, 10)
    assert (c.bonus_fuerza, c.bonus_velocidad) == (7, 4)
    assert c.modificador == 2
    assert c.cara == esp.ESPECIES["pulpo"].caras[esp.FELIZ]


def test_sin_pocion_los_bonus_son_cero():
    criatura = sim.Criatura(
        id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=10, base_velocidad=10, base_salud=10,
        hambre=50.0, animo=50.0,
    )
    c = comp.competidor_de(criatura)
    assert c.bonus_fuerza == c.bonus_velocidad == 0


def test_el_competidor_se_lleva_la_cara_que_tiene_puesta():
    """La necesita el podio: sin ella habría que volver a la criatura, y este
    módulo es puro a propósito."""
    def criatura(hambre, animo):
        return sim.Criatura(
            id=1, usuario_id="u", guild_id="g", especie="pulpo", nombre="X",
            nacida_en=T0, actualizada_en=T0,
            base_fuerza=10, base_velocidad=10, base_salud=10,
            hambre=hambre, animo=animo,
        )

    contento = comp.competidor_de(criatura(90.0, 90.0))
    hecho_polvo = comp.competidor_de(criatura(10.0, 10.0))

    assert contento.cara == esp.ESPECIES["pulpo"].caras[esp.FELIZ]
    assert hecho_polvo.cara == esp.ESPECIES["pulpo"].caras[esp.MAL]


# --- Cuántos caben ---------------------------------------------------------

def test_una_carrera_admite_hasta_cinco():
    cinco = [competidor(f"C{i}", stat=10 + i) for i in range(comp.MAX_CORREDORES)]
    e, r = combate(cinco, comp.CARRERA, DadosFijos([10, 11, 12, 13, 14]))

    assert len(r.competidores) == 5
    assert len(e.orden) == 5
    for ronda in r.rondas:
        assert len(ronda.dados) == 5 and len(ronda.totales) == 5

    # Cinco pistas y cinco filas de dado en cada fotograma.
    for fotograma in comp.fotogramas_de(e)[0]:
        ls = lineas(fotograma)
        assert sum(1 for ln in ls if ">" in ln) == 5, ls
        assert sum(1 for ln in ls if "+d20" in ln) == 5, ls


def test_no_caben_mas_de_cinco():
    espera_error([competidor(f"C{i}") for i in range(6)], comp.CARRERA,
                 "una carrera de seis debería estar prohibida")


def test_hacen_falta_dos_para_competir():
    espera_error([competidor("Solo")], comp.CARRERA,
                 "una carrera de uno debería estar prohibida")


def test_solo_caben_dos_o_cuatro_en_el_sumo():
    """El sumo es un forcejeo: de dos, o de cuatro en torneo. Con tres no hay
    forma de emparejar sin que alguien pelee solo o dos veces."""
    espera_error([competidor(f"C{i}") for i in range(3)], comp.SUMO,
                 "un sumo de tres debería estar prohibido")
    espera_error([competidor(f"C{i}") for i in range(5)], comp.SUMO,
                 "un sumo de cinco debería estar prohibido")

    # Y los dos que sí valen no levantan nada.
    for cuantos in (2, 4):
        comp.enfrentar([competidor(f"C{i}", stat=10 + i) for i in range(cuantos)],
                       comp.SUMO, DadosFijos([20, 1]))


def test_la_clasificacion_va_del_primero_al_ultimo():
    cinco = [competidor(f"C{i}", stat=0) for i in range(5)]
    # Un dado fijo por competidor y por tramo: C4 saca 20 siempre, C0 saca 1.
    e, _ = combate(cinco, comp.CARRERA, DadosFijos([1, 5, 10, 15, 20]))

    nombres = [c.nombre for c, _ in e.clasificacion]
    assert nombres == ["C4", "C3", "C2", "C1", "C0"]

    marcadores = [marcador for _, marcador in e.clasificacion]
    assert marcadores == sorted(marcadores, reverse=True)
    assert e.campeon.nombre == "C4"


def test_un_empate_entre_cinco_se_desempata():
    cinco = [competidor(f"C{i}", stat=10) for i in range(5)]
    # Cinco iguales tres tramos; en el cuarto se rompe el empate del todo.
    dados = [7] * 15 + [1, 2, 3, 4, 5]
    _, r = combate(cinco, comp.CARRERA, DadosFijos(dados))

    assert r.desempates == 1
    assert len(set(r.totales)) == 5, r.totales


# --- El torneo -------------------------------------------------------------

def torneo_guionizado():
    """Cuatro al sumo con dados fijos, sin sorteo: parejas (C0,C1) y (C2,C3).

    C0 y C2 saca 20 siempre y sus rivales 1, así que C0 gana su semifinal, C2 la
    suya y C0 la final. Los eliminados quedan por lo que sumaron: C3 (42) sobre
    C1 (36).
    """
    cuatro = [competidor(f"C{i}", stat=10 + i) for i in range(4)]
    return comp.enfrentar(cuatro, comp.SUMO, DadosFijos([20, 1]))


def test_el_sumo_de_cuatro_es_un_torneo_de_tres_combates():
    e = torneo_guionizado()
    assert len(e.combates) == 3

    semi1, semi2, final = e.combates
    assert [c.nombre for c in semi1.competidores] == ["C0", "C1"]
    assert [c.nombre for c in semi2.competidores] == ["C2", "C3"]
    assert [c.nombre for c in final.competidores] == ["C0", "C2"]


def test_el_sumo_de_dos_sigue_siendo_un_solo_combate():
    e = comp.enfrentar([competidor("A", stat=10), competidor("B", stat=5)],
                       comp.SUMO, DadosFijos([20, 1]))
    assert len(e.combates) == 1


def test_la_carrera_sigue_siendo_un_solo_combate():
    """Aunque corran cinco: en una carrera se enfrentan todos a la vez."""
    for cuantos in range(2, comp.MAX_CORREDORES + 1):
        e = comp.enfrentar(
            [competidor(f"C{i}", stat=10 + i) for i in range(cuantos)],
            comp.CARRERA, DadosFijos([10, 11, 12, 13, 14]),
        )
        assert len(e.combates) == 1, cuantos


def test_quien_pierde_la_semifinal_no_llega_a_la_final():
    e = torneo_guionizado()
    final = e.combates[-1]
    perdedores = {e.combates[0].competidor_perdedor.nombre,
                  e.combates[1].competidor_perdedor.nombre}

    assert perdedores == {"C1", "C3"}
    for c in final.competidores:
        assert c.nombre not in perdedores, c.nombre


def test_el_campeon_es_quien_gana_la_final():
    e = torneo_guionizado()
    assert e.campeon.nombre == "C0"
    assert e.campeon is e.combates[-1].competidor_ganador


def test_el_orden_del_torneo_es_campeon_finalista_y_los_de_semis():
    """Los caídos se ordenan por intercambios y después por puntos crudos."""
    e = torneo_guionizado()
    assert [c.nombre for c, _ in e.clasificacion] == ["C0", "C2", "C3", "C1"]

    marcadores = dict(e.clasificacion)
    # A cada uno se le apunta el marcador de su última pelea.
    assert marcadores[e.competidores[1]] == 0  # C1, su semifinal 2–0
    assert marcadores[e.competidores[3]] == 0  # C3, su semifinal 2–0


def test_el_sorteo_mezcla_las_parejas():
    """Lo que distingue un sorteo de haber dejado el orden de invitación: a la
    larga cada uno se cruza con todos, así que en la primera semifinal tienen que
    llegar a salir las seis parejas posibles."""
    from itertools import combinations

    cuatro = [competidor(f"C{i}", stat=10 + i) for i in range(4)]
    rng = random.Random(1)

    vistas = set()
    for _ in range(200):
        e = comp.enfrentar(cuatro, comp.SUMO, rng)
        vistas.add(frozenset(c.nombre for c in e.combates[0].competidores))

    posibles = {frozenset(p) for p in combinations([c.nombre for c in cuatro], 2)}
    assert len(posibles) == 6
    assert vistas == posibles, sorted(map(sorted, posibles - vistas))


def test_el_reto_se_anuncia_segun_lo_que_sea():
    assert comp.como_se_llama(comp.CARRERA, 2) == "una CARRERA"
    assert comp.como_se_llama(comp.CARRERA, 5) == "una CARRERA"
    assert comp.como_se_llama(comp.SUMO, 2) == "un SUMO"
    assert comp.como_se_llama(comp.SUMO, 4) == "un TORNEO DE SUMO"


def test_el_torneo_solo_cuenta_una_vez_para_cada_uno():
    """Los finalistas pelean dos veces pero el encuentro es uno: el cog reparte
    coste y XP con `orden`, y ahí cada dorsal aparece exactamente una vez."""
    e = torneo_guionizado()
    assert sorted(e.orden) == [0, 1, 2, 3]


def test_el_torneo_consume_solo_los_intercambios_reales():
    dados = DadosFijos([20, 1])
    cuatro = [competidor(f"C{i}", stat=10 + i) for i in range(4)]
    e = comp.enfrentar(cuatro, comp.SUMO, dados)

    assert len(e.combates) == 3
    assert all(len(combate.rondas) == 2 for combate in e.combates)
    assert dados.i == 12


def test_los_caidos_de_semis_se_ordenan_primero_por_intercambios():
    cuatro = [competidor(f"C{i}", stat=10) for i in range(4)]
    # C1 cae 2-1 con 34 puntos; C3 cae 2-0 con 58. El intercambio ganado
    # manda sobre los puntos crudos para ordenar tercero y cuarto.
    dados = DadosFijos([
        2, 1, 1, 2, 2, 1,
        20, 19, 20, 19,
        20, 1, 20, 1,
    ])
    e = comp.enfrentar(cuatro, comp.SUMO, dados)

    assert e.orden == (0, 2, 1, 3)
    assert e.marcadores == (2, 1, 0, 0)
    assert dados.i == 14


def test_los_caidos_empatados_se_ordenan_por_dorsal_global():
    class DadosBarajados(DadosFijos):
        def shuffle(self, dorsales, *args, **kwargs):
            dorsales[:] = [dorsales[i] for i in (0, 3, 2, 1)]
            self.sorteo = tuple(dorsales)

    dados = DadosBarajados([2, 1])
    e = comp.enfrentar(
        [competidor(f"C{i}", stat=10) for i in range(4)],
        comp.SUMO,
        dados,
    )
    semifinales = e.combates[:2]

    assert dados.sorteo == (0, 3, 2, 1)
    assert [
        (dados.sorteo[1], semifinales[0].marcadores[1], semifinales[0].totales[1]),
        (dados.sorteo[3], semifinales[1].marcadores[1], semifinales[1].totales[1]),
    ] == [(3, 0, 22), (1, 0, 22)]
    assert e.orden == (0, 2, 1, 3)
    assert sorted(e.orden) == [0, 1, 2, 3]


# --- Modificadores ---------------------------------------------------------

def test_el_estado_modifica_poco_comparado_con_el_d20():
    assert comp.modificador_por_estado(hambre=80, animo=80) == 2
    assert comp.modificador_por_estado(hambre=80, animo=50) == 0
    assert comp.modificador_por_estado(hambre=80, animo=10) == -2
    assert comp.modificador_por_estado(hambre=10, animo=10) == -5
    # El rango total (7 puntos) es menor que el del dado (19): el azar manda.
    assert 7 < comp.CARA_DADO - 1


def test_una_criatura_hecha_polvo_sigue_aportando_algo():
    debil = competidor(stat=1, modificador=-5)
    assert debil.base_en(comp.SALIDA) == 1


# --- Narración -------------------------------------------------------------

def lineas(texto: str) -> list[str]:
    dentro = texto.split("```ansi\n")[1].split("\n```")[0]
    return ANSI.sub("", dentro).split("\n")


def test_hay_un_fotograma_por_tramo():
    e, r = combate([competidor("A"), competidor("B")], comp.CARRERA,
                   DadosFijos([20, 1]))
    assert len(comp.fotogramas_de(e)[0]) == len(r.rondas)


def test_el_torneo_se_anima_combate_por_combate_y_con_su_ronda():
    e = torneo_guionizado()
    tandas = comp.fotogramas_de(e)

    assert len(tandas) == 3
    titulos = [lineas(tanda[0])[1] for tanda in tandas]
    assert "SEMIFINAL 1" in titulos[0]
    assert "SEMIFINAL 2" in titulos[1]
    assert "FINAL" in titulos[2]


def test_un_combate_suelto_se_titula_con_su_modalidad():
    for tipo in (comp.CARRERA, comp.SUMO):
        e, _ = combate([competidor("A"), competidor("B")], tipo,
                       DadosFijos([20, 1]))
        assert comp.NOMBRES[tipo] in lineas(comp.fotogramas_de(e)[0][0])[1]


def test_los_marcos_de_competencia_nunca_se_descuadran():
    """Con campos de dos a cinco y con torneos: las filas del corredor y del dado
    se montan a mano por el color, así que pasarse de ancho no recorta, rompe el
    marco."""
    rng = random.Random(0)
    for cuantos in range(2, comp.MAX_CORREDORES + 1):
        tipos = [comp.CARRERA, comp.TOTEM]
        if cuantos in comp.CUANTOS_CABEN[comp.SUMO]:
            tipos.append(comp.SUMO)
        for tipo in tipos:
            for _ in range(40):
                corredores = [
                    competidor(
                        nombre=rng.choice(["Bartolomeo", "Yo", "X" * 24]),
                        especie=rng.choice(list(esp.ESPECIES)),
                        stat=rng.randint(1, sim.MAXIMO_STAT),
                        modificador=rng.randint(-5, 2),
                        animo=rng.choice(esp.ANIMOS),
                    )
                    for _ in range(cuantos)
                ]
                e = comp.enfrentar(corredores, tipo, rng)
                for tanda in comp.fotogramas_de(e):
                    for fotograma in tanda:
                        for linea in lineas(fotograma):
                            assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_la_fila_del_corredor_aguanta_marcadores_de_cuatro_cifras():
    """Regresión: esta fila se monta a mano por el color de la pista, así que
    pasarse de ancho no recorta, rompe el marco. Con la estadística al tope los
    marcadores llegan a cuatro cifras (3 tramos de ~1000).

    El modificador va a +2 a propósito: `base` puede pasar del tope aunque la
    estadística esté topada, así que los anchos no pueden darlo por hecho."""
    a = competidor("Bartolomeo", stat=sim.MAXIMO_STAT, modificador=2)
    b = competidor("Yo", stat=sim.MAXIMO_STAT, modificador=2)
    for tipo in (comp.CARRERA, comp.SUMO):
        e, r = combate([a, b], tipo, DadosFijos([20, 19]))
        assert r.totales[0] > 999, r.totales  # si no, el test no prueba nada
        for fotograma in comp.fotogramas_de(e)[0]:
            for linea in lineas(fotograma):
                assert len(linea) == pantalla.ANCHO + 2, repr(linea)


def test_las_columnas_del_dado_no_bailan_entre_las_filas():
    """Los anchos se miden sobre el combate entero, no fila a fila: si cada una
    midiera lo suyo, con un competidor a 9 y otro a 240 el `+d20` de arriba no
    caería en la misma columna que el de abajo."""
    for tipo in (comp.CARRERA, comp.SUMO):
        e, _ = combate([competidor("Aaa", stat=9), competidor("Bbb", stat=240)],
                       tipo, DadosFijos([20, 19]))
        for fotograma in comp.fotogramas_de(e)[0]:
            filas = [ln for ln in lineas(fotograma) if "+d20" in ln]
            assert len(filas) == 2
            assert filas[0].index("+d20") == filas[1].index("+d20"), filas
            assert filas[0].index(" = ") == filas[1].index(" = "), filas


def test_las_columnas_del_dado_cuadran_tambien_con_cinco():
    corredores = [competidor(f"C{i}", stat=9 * 10 ** (i % 3)) for i in range(5)]
    e, _ = combate(corredores, comp.CARRERA, DadosFijos([20, 19, 18, 17, 16]))
    for fotograma in comp.fotogramas_de(e)[0]:
        filas = [ln for ln in lineas(fotograma) if "+d20" in ln]
        assert len(filas) == 5
        assert len({f.index("+d20") for f in filas}) == 1, filas
        assert len({f.index(" = ") for f in filas}) == 1, filas


def test_un_combate_normal_se_dibuja_igual_que_siempre():
    """El ancho se calcula, pero el caso corriente no puede cambiar: los
    mínimos (2 para la base, 3 para el total) son los de toda la vida."""
    e, _ = combate([competidor("Bartolomeo", stat=22, modificador=2),
                    competidor("Yo", stat=19)], comp.CARRERA,
                   DadosFijos([20, 19]))
    filas = [ln for ln in lineas(comp.fotogramas_de(e)[0][0]) if "+d20" in ln]
    assert filas[0] == "│ Bartolo 24+d20 20 =  44  │"
    assert filas[1] == "│ Yo      19+d20 19 =  38  │"


def test_el_total_del_tramo_se_ve_entero():
    """Regresión: la fila del dado se pasaba de ancho y se recortaba justo el
    total, que es el número que importa."""
    for stat in (99, sim.MAXIMO_STAT):
        a = competidor("Bartolomeo", stat=stat, modificador=2)
        e, r = combate([a, competidor("B", stat=stat)], comp.SUMO,
                       DadosFijos([20, 19]))
        primera = lineas(comp.fotogramas_de(e)[0][0])
        fila_dado = next(ln for ln in primera if "+d20" in ln)
        assert str(r.rondas[0].totales[0]) in fila_dado, (stat, fila_dado)
        assert f"{a.base_en(comp.POSICION)}+d20" in fila_dado, (stat, fila_dado)


def test_el_ganador_llega_a_la_meta_en_la_carrera():
    a = competidor("A", stat=30)
    e, _ = combate([a, competidor("B", stat=1)], comp.CARRERA,
                   DadosFijos([20, 1]))
    ultimo = lineas(comp.fotogramas_de(e)[0][-1])
    fila_ganador = ultimo[3]  # cabecera(3 líneas) -> primer corredor
    assert fila_ganador.count("=") == comp.ANCHO_PISTA


def test_en_el_sumo_la_marca_se_mueve_por_intercambios():
    a = competidor("A", stat=10)
    b = competidor("B", stat=10)
    e, _ = combate([a, b], comp.SUMO, DadosFijos([12, 8]))

    posiciones = []
    for fotograma in comp.fotogramas_de(e)[0]:
        fila = next(ln for ln in lineas(fotograma) if ln.count("(") and "O" in ln)
        posiciones.append(fila.index("O"))

    assert posiciones == sorted(posiciones)
    assert len(set(posiciones)) > 1, posiciones


def test_los_fotogramas_nombrados_no_inventan_aguante_despues_del_dos_cero():
    e, _ = combate(
        [competidor("A"), competidor("B")],
        comp.SUMO,
        DadosFijos([20, 1, 20, 1]),
    )
    fotogramas = comp.fotogramas_de(e)[0]
    texto = "\n".join(fotogramas)

    assert len(fotogramas) == 2
    assert comp.POSICION in lineas(fotogramas[0])[1]
    assert comp.EMPUJE in lineas(fotogramas[1])[1]
    assert comp.AGUANTE not in texto
    assert "2–0" in comp.resumen(e)
    assert "intercambios" in comp.resumen(e)


def test_un_reintento_de_sumo_se_marca_sin_crear_otro_fotograma():
    e, r = combate(
        [competidor("A"), competidor("B")],
        comp.SUMO,
        DadosFijos([5, 5, 6, 4, 20, 1]),
    )
    fotogramas = comp.fotogramas_de(e)[0]

    assert len(fotogramas) == len(r.rondas) == 2
    assert f"{comp.POSICION}*" in lineas(fotogramas[0])[1]
    assert "desempatar 1" in comp.resumen(e)


# --- El podio --------------------------------------------------------------

def carrera_de(cuantos, **kwargs):
    corredores = [
        competidor(f"C{i}", stat=cuantos - i, **kwargs) for i in range(cuantos)
    ]
    return comp.enfrentar(corredores, comp.CARRERA, DadosFijos([10]))


def test_con_dos_no_hay_podio_sino_la_linea_de_siempre():
    """El 1 contra 1 tiene que quedar igual que antes: no hay tres mejores."""
    texto = comp.resumen(carrera_de(2))
    assert "```" not in texto
    assert "🥇" not in texto
    assert "gana a" in texto


def test_el_resumen_nombra_al_ganador():
    e = comp.enfrentar([competidor("Pelusa", stat=30), competidor("Slimy", stat=1)],
                       comp.CARRERA, DadosFijos([20, 1]))
    texto = comp.resumen(e)
    assert "Pelusa" in texto and "Slimy" in texto
    assert str(e.combates[0].totales[0]) in texto


def test_con_tres_o_mas_el_resumen_es_el_podio():
    for cuantos in (3, 4, 5):
        assert comp.resumen(carrera_de(cuantos)) == comp.podio(carrera_de(cuantos))


def test_el_podio_dibuja_a_los_tres_de_arriba():
    e = carrera_de(5)
    texto = comp.podio(e)

    # Las medallas van FUERA del bloque: dentro Discord las convierte en
    # imágenes de ancho variable y descuadra el marco.
    cabecera = texto.split("```ansi")[0]
    assert "🥇" in cabecera and "🥈" in cabecera and "🥉" in cabecera
    dentro = "\n".join(lineas(texto))
    assert "🥇" not in dentro

    for puesto, (c, _) in enumerate(e.clasificacion[:3], start=1):
        assert c.nombre in cabecera, c.nombre
        assert f"│ {puesto} │" in dentro, (puesto, dentro)

    # Los cinco salen en la lista de abajo, no sólo los del podio.
    for c, marcador in e.clasificacion:
        assert c.nombre in dentro and str(marcador) in dentro


def _donde_esta_el_cajon(ls: list[str], puesto: int) -> tuple[int, int]:
    """Fila y columna del `│ n │` de un puesto dentro del dibujo."""
    marca = f"│ {puesto} │"
    fila = next(i for i, ln in enumerate(ls) if marca in ln)
    return fila, ls[fila].index(marca)


def test_cada_gachamon_va_encima_de_su_cajon():
    """Lo que se pidió: el gachamón subido a SU cajón. Un descuadre de una sola
    columna se ve a simple vista en Discord, así que se comprueba por posición:
    encima del número va el techo del cajón, y encima del techo la cara, las tres
    piezas empezando en la misma columna.

    Se prueban las veinticinco porque la cara la pone la especie, y con caras
    de distinto ancho el dibujo se torcería. (Hoy las 25 miden 3, y hay un test
    en `test_especies.py` que lo vigila; esto cuida el otro lado.)
    """
    for clave in esp.ESPECIES:
        e = carrera_de(3, especie=clave)
        ls = lineas(comp.podio(e))
        for puesto, (c, _) in enumerate(e.clasificacion[:3], start=1):
            y, x = _donde_esta_el_cajon(ls, puesto)
            ancho = comp.ANCHO_CAJON
            assert ls[y - 1][x:x + ancho] == "┌───┐", (
                f"{clave} puesto {puesto}: encima del número hay "
                f"«{ls[y - 1][x:x + ancho]}» y no el techo del cajón"
            )
            assert ls[y - 2][x:x + ancho] == f"({c.cara})", (
                f"{clave} puesto {puesto}: encima del cajón hay "
                f"«{ls[y - 2][x:x + ancho]}» y no «({c.cara})»"
            )


def test_el_podio_esta_en_el_orden_clasico_dos_uno_tres():
    """El 1.º en medio y más alto, el 2.º a su izquierda, el 3.º a su derecha."""
    ls = lineas(comp.podio(carrera_de(3)))
    sitios = {p: _donde_esta_el_cajon(ls, p) for p in (1, 2, 3)}

    _, x1 = sitios[1]
    _, x2 = sitios[2]
    _, x3 = sitios[3]
    assert x2 < x1 < x3

    # Cuanto más arriba empieza el cajón, más alto es.
    alturas = [sitios[p][0] for p in (1, 2, 3)]
    assert alturas == sorted(alturas) and len(set(alturas)) == 3, alturas


def test_el_podio_no_se_descuadra():
    """Las filas del podio llevan color, así que se montan a mano y pasarse de
    ancho rompe el marco en vez de recortar. Se aprieta con lo peor de todo:
    nombres del largo máximo, estadísticas al tope y desempates encadenados,
    que es lo que hace crecer los marcadores hasta cinco cifras."""
    rng = random.Random(7)
    largo = "M" * 24  # vistas.LARGO_MAXIMO_NOMBRE
    for cuantos in (3, 4, 5):
        for _ in range(40):
            corredores = [
                competidor(
                    nombre=rng.choice([largo, "Yo", "Juan III"]),
                    especie=rng.choice(list(esp.ESPECIES)),
                    stat=rng.randint(1, sim.MAXIMO_STAT),
                    modificador=2,
                    animo=rng.choice(esp.ANIMOS),
                )
                for _ in range(cuantos)
            ]
            e = comp.enfrentar(corredores, comp.CARRERA, rng)
            for linea in lineas(comp.podio(e)):
                assert len(linea) == pantalla.ANCHO + 2, repr(linea)

    # Y el caso extremo de verdad: todos empatados hasta agotar los desempates.
    iguales = [competidor(largo, stat=sim.MAXIMO_STAT, modificador=2)
               for _ in range(5)]
    e = comp.enfrentar(iguales, comp.CARRERA, DadosFijos([7]))
    assert e.combates[0].totales[0] > 9999  # cinco cifras: el marcador aprieta
    for linea in lineas(comp.podio(e)):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


# --- El cuadro del torneo --------------------------------------------------

def test_el_resumen_de_un_torneo_es_el_cuadro():
    e = torneo_guionizado()
    assert comp.resumen(e) == comp.cuadro(e)


def test_el_cuadro_nombra_al_campeon_fuera_del_bloque():
    e = torneo_guionizado()
    texto = comp.cuadro(e)

    cabecera = texto.split("```ansi")[0]
    assert "🥇" in cabecera and "C0" in cabecera
    assert "🥇" not in "\n".join(lineas(texto))


def test_el_cuadro_une_a_cada_pareja_con_su_ganador():
    """El invariante del dibujo: las tres esquinas de un cruce (`┐`, `├`, `┘`) en
    la misma columna, y el nombre pegado al `├` es el del que ganó esa pelea.
    Un descuadre de una columna deja el cuadro sin sentido."""
    e = torneo_guionizado()
    ls = lineas(comp.cuadro(e))

    # Con el espacio: el separador del marco, `├────┤`, también empieza por `├─`.
    cruces = [i for i, ln in enumerate(ls) if "├─ " in ln]
    assert len(cruces) == len(e.combates) == 3

    for fila, resultado in zip(cruces, e.combates):
        columna = ls[fila].index("├─ ")
        assert ls[fila - 1][columna] == "┐", (fila, ls[fila - 1])
        assert ls[fila + 1][columna] == "┘", (fila, ls[fila + 1])

        ancho = comp.ANCHO_NOMBRE_CUADRO
        ganador = resultado.competidor_ganador.nombre[:ancho]
        hueco = ls[fila][columna + 3:columna + 3 + ancho]
        assert hueco == f"{ganador:<{ancho}}", (
            f"junto al cruce hay «{hueco}» y ganó «{ganador}»"
        )


def test_el_cuadro_ensena_a_los_cuatro_y_las_tres_peleas():
    e = torneo_guionizado()
    dentro = "\n".join(lineas(comp.cuadro(e)))
    for c in e.competidores:
        assert c.nombre in dentro, c.nombre
    assert dentro.count("├─ ") == 3


def test_el_que_cae_sale_en_gris():
    """El color es lo que hace legible el cuadro de un golpe: quien pasa va del
    color de su especie y quien cae, en gris, como en `/cementerio`."""
    e = torneo_guionizado()
    con_color = comp.cuadro(e)
    gris = f"\x1b[0;{esp.GRIS}m"

    for combate_ in e.combates:
        perdedor = combate_.competidor_perdedor
        recorte = perdedor.nombre[:comp.ANCHO_NOMBRE_CUADRO]
        assert f"{gris}{recorte:<{comp.ANCHO_NOMBRE_CUADRO}}" in con_color, recorte

    campeon = e.campeon
    suyo = f"\x1b[0;{campeon.color}m"
    assert suyo in con_color
    # Y el campeón no aparece nunca en gris: no ha caído en ninguna ronda.
    assert f"{gris}{campeon.nombre[:comp.ANCHO_NOMBRE_CUADRO]}" not in con_color


def test_los_marcadores_del_torneo_van_fuera_del_marco():
    """En el cuadro no caben, y meterlos a la fuerza lo rompería."""
    e = torneo_guionizado()
    texto = comp.cuadro(e)
    cola = texto.split("```")[-1]

    assert cola.count("2–0") == 3
    assert "intercambios" in cola.lower()
    for combate_ in e.combates:
        assert str(max(combate_.totales)) not in cola


def test_el_cuadro_no_se_descuadra():
    """Las filas del cuadro llevan color, así que se montan a mano. Se aprieta
    con nombres del largo máximo y desempates encadenados."""
    rng = random.Random(5)
    largo = "M" * 24  # vistas.LARGO_MAXIMO_NOMBRE
    for _ in range(60):
        cuatro = [
            competidor(
                nombre=rng.choice([largo, "Yo", "Bartolomeo"]),
                especie=rng.choice(list(esp.ESPECIES)),
                stat=rng.randint(1, sim.MAXIMO_STAT),
                modificador=2,
                animo=rng.choice(esp.ANIMOS),
            )
            for _ in range(4)
        ]
        e = comp.enfrentar(cuatro, comp.SUMO, rng)
        for linea in lineas(comp.cuadro(e)):
            assert len(linea) == pantalla.ANCHO + 2, repr(linea)

    # Todos iguales: desempates hasta el tope y marcadores de cinco cifras.
    iguales = [competidor(largo, stat=sim.MAXIMO_STAT, modificador=2)
               for _ in range(4)]
    e = comp.enfrentar(iguales, comp.SUMO, DadosFijos([7]))
    for linea in lineas(comp.cuadro(e)):
        assert len(linea) == pantalla.ANCHO + 2, repr(linea)


# --- El Asalto al Tótem ----------------------------------------------------

def test_las_tres_fases_del_totem_miran_una_estadistica_cada_una():
    """Sin mezclas: cada fase lee su estadística y nada más."""
    c = competidor(
        fuerza=10, velocidad=20, salud=30,
        bonus_fuerza=2, bonus_velocidad=4,
    )

    assert {fase: c.base_en(fase) for fase in comp.FASES_TOTEM} == {
        comp.CENTRO: 24,
        comp.FORCEJEO: 12,
        comp.HUIDA: 30,
    }


def test_cada_fase_del_totem_reparte_puntos_de_colocacion_de_n_a_uno():
    tres = [
        competidor("Alta", stat=30),
        competidor("Media", stat=20),
        competidor("Baja", stat=10),
    ]
    _, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert len(r.rondas) == len(comp.FASES_TOTEM)
    assert [ronda.fase for ronda in r.rondas] == list(comp.FASES_TOTEM)
    assert r.marcadores == (9, 6, 3)
    assert r.orden == (0, 1, 2)


def test_los_empatados_en_una_fase_del_totem_se_llevan_los_mismos_puntos():
    """Empatar comparte el puesto de arriba y salta el de abajo.

        AL CENTRO  40 30 20 -> 3 2 1
        FORCEJEO   20 20 40 -> 2 2 3   el empate cobra 2 y nadie cobra el 1
        HUIDA      26 35 15 -> 2 3 1
                              --------
                               7 7 5   diecinueve y no dieciocho
    """
    tres = [
        competidor("Justa", velocidad=30, fuerza=10, salud=16),
        competidor("Gemela", velocidad=20, fuerza=10, salud=25),
        competidor("Otra", velocidad=10, fuerza=30, salud=5),
    ]
    _, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert r.marcadores == (7, 7, 5)
    assert sum(r.marcadores) == 19


def test_el_desempate_de_puntos_del_totem_mira_el_rendimiento_bruto():
    """Con los mismos puntos manda lo acumulado; el bruto solo no gana el tótem."""
    tres = [
        competidor("Justa", velocidad=32, fuerza=5, salud=20),
        competidor("Fina", velocidad=20, fuerza=5, salud=30),
        competidor("Bruta", velocidad=10, fuerza=40, salud=10),
    ]
    _, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert r.marcadores == (7, 7, 5)
    assert r.totales == (87, 85, 90)
    assert r.orden == (0, 1, 2)


def test_el_empate_exacto_del_totem_se_desempata_con_un_forcejeo_visible():
    tres = [
        competidor("A", velocidad=30, fuerza=20, salud=10),
        competidor("B", velocidad=20, fuerza=10, salud=30),
        competidor("C", velocidad=10, fuerza=30, salud=20),
    ]
    _, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert r.desempates == 1
    assert len(r.rondas) == len(comp.FASES_TOTEM) + 1
    assert r.rondas[-1].fase == comp.DESEMPATE
    # Empate exacto a tres: el marcador y el bruto oficiales no se mueven, y
    # quien más saca en el forcejeo se lleva el tótem.
    assert r.marcadores == (6, 6, 6)
    assert r.totales == (90, 90, 90)
    assert r.orden == (2, 0, 1)


def test_los_desempates_del_totem_tienen_tope_y_fallback_determinista():
    dos = [competidor("A", stat=10), competidor("B", stat=10)]
    _, r = combate(dos, comp.TOTEM, DadosFijos([7]))

    assert r.desempates == comp.MAX_DESEMPATES
    assert len(r.rondas) == len(comp.FASES_TOTEM) + comp.MAX_DESEMPATES
    assert r.orden == (0, 1)


def test_el_totem_admite_de_dos_a_cinco_y_nunca_es_torneo():
    for cuantos in range(2, comp.MAX_CORREDORES + 1):
        e = comp.enfrentar(
            [competidor(f"C{i}", stat=10 + i) for i in range(cuantos)],
            comp.TOTEM, DadosFijos([10]),
        )
        assert len(e.orden) == cuantos
        assert not e.es_torneo


def test_el_totem_no_admite_ni_uno_ni_seis():
    espera_error([competidor("Solo")], comp.TOTEM,
                 "un asalto al tótem de uno debería estar prohibido")
    espera_error([competidor(f"C{i}") for i in range(6)], comp.TOTEM,
                 "un asalto al tótem de seis debería estar prohibido")


def test_el_totem_lo_gana_la_versatilidad_y_la_carrera_el_velocista():
    """El mismo trío, dos modalidades y dos ganadores distintos."""
    tres = [
        competidor("Equilibrio", stat=20),
        competidor("Velocista", velocidad=35, fuerza=10, salud=11),
        competidor("Forzudo", velocidad=10, fuerza=35, salud=10),
    ]
    _, totem = combate(tres, comp.TOTEM, DadosFijos([10]))
    _, carrera = combate(tres, comp.CARRERA, DadosFijos([10]))

    # Ninguna fase la manda el mismo: cada uno gana la suya.
    mejores = [
        max(range(3), key=lambda i: ronda.totales[i]) for ronda in totem.rondas
    ]
    assert mejores == [1, 2, 0]

    assert totem.marcadores == (7, 6, 5)
    assert totem.competidor_ganador.nombre == "Equilibrio"
    assert carrera.competidor_ganador.nombre == "Velocista"


def test_el_reto_del_totem_se_anuncia_por_su_nombre():
    assert comp.como_se_llama(comp.TOTEM, 3) == "un ASALTO AL TÓTEM"


def test_con_dos_el_totem_se_resume_por_puntos_de_colocacion():
    e, _ = combate([competidor("A", stat=20), competidor("B", stat=10)],
                   comp.TOTEM, DadosFijos([10]))

    assert comp.resumen(e) == (
        "🏆 **A** gana a **B** por 6–3 puntos de colocación."
    )


def test_con_tres_o_mas_el_totem_termina_en_podio():
    e, _ = combate([competidor(f"C{i}", stat=10 + i) for i in range(3)],
                   comp.TOTEM, DadosFijos([10]))
    resumen = comp.resumen(e)

    assert resumen.startswith("## 🏁 Podio")
    assert comp.NOMBRES[comp.TOTEM] in resumen


def test_el_totem_tiene_un_fotograma_por_fase_y_tres_escenas_distintas():
    e, _ = combate([competidor("A", stat=20), competidor("B", stat=10)],
                   comp.TOTEM, DadosFijos([10]))
    fotogramas = comp.fotogramas_de(e)[0]

    assert len(fotogramas) == len(comp.FASES_TOTEM)
    escenas = []
    for fase, fotograma in zip(comp.FASES_TOTEM, fotogramas):
        ls = lineas(fotograma)
        assert fase in ls[1]
        escena = tuple(ls[3:3 + comp.ALTO_ESCENA])
        assert all("#" in "".join(escena) for _ in (0,)), escena
        escenas.append(escena)
    assert len(set(escenas)) == len(comp.FASES_TOTEM)


def test_el_fotograma_del_totem_ensena_el_dado_y_los_puntos_de_cada_uno():
    e, _ = combate([competidor("A", stat=20), competidor("B", stat=10)],
                   comp.TOTEM, DadosFijos([10]))
    ultimo = lineas(comp.fotogramas_de(e)[0][-1])

    assert sum(1 for linea in ultimo if "+d20" in linea) == 2
    puestos = [linea for linea in ultimo if linea.startswith(("│  1 ", "│  2 "))]
    assert len(puestos) == 2
    assert "A" in puestos[0] and puestos[0].strip("│ ").endswith("6")
    assert "B" in puestos[1] and puestos[1].strip("│ ").endswith("3")


def test_la_escena_del_totem_cabe_entera_en_el_marco():
    assert comp.ANCHO_ESCENA <= pantalla.ANCHO
    for fase, escena in comp.ESCENAS_TOTEM.items():
        assert len(escena) == comp.ALTO_ESCENA, fase
        assert {len(linea) for linea in escena} == {comp.ANCHO_ESCENA}, fase


def test_el_totem_de_cinco_cabe_en_un_mensaje_de_discord():
    largo = "M" * 24  # vistas.LARGO_MAXIMO_NOMBRE
    cinco = [
        competidor(largo, stat=sim.MAXIMO_STAT, modificador=2) for _ in range(5)
    ]
    e = comp.enfrentar(cinco, comp.TOTEM, DadosFijos([7]))

    for fotograma in comp.fotogramas_de(e)[0]:
        assert len(fotograma) <= 2000, len(fotograma)
    assert len(comp.resumen(e)) <= 2000


def test_cada_modalidad_esta_en_todas_las_tablas():
    """Media modalidad cableada es un KeyError en producción, no un test rojo."""
    modalidades = {comp.CARRERA, comp.SUMO, comp.TOTEM}
    for tabla in (
        comp.NOMBRES, comp.STATS, comp.CUANTOS_CABEN, comp.ARTICULOS,
        comp.REGLAS, comp.REGLA_DEL_MARCADOR, comp.DIBUJANTES,
    ):
        assert set(tabla) == modalidades


def test_cada_modalidad_dice_su_regla_para_anunciar_el_reto():
    assert comp.REGLAS[comp.TOTEM] == (
        "AL CENTRO, FORCEJEO y HUIDA; cada fase reparte puestos "
        "y gana quien más sume"
    )


def test_el_totem_de_cinco_ordena_el_podio_por_puntos_de_colocacion():
    """Tres especialistas, un equilibrado alto y otro bajo, con el dado fijo.

        AL CENTRO  50 10 13 30 20 -> 5 1 2 4 3
        FORCEJEO   11 50 10 30 20 -> 2 5 1 4 3
        HUIDA      10 12 50 30 20 -> 1 2 5 4 3
                                    -------------
                                     8 8 8 12 9
    """
    cinco = [
        competidor("C0", velocidad=50, fuerza=11, salud=10),
        competidor("C1", velocidad=10, fuerza=50, salud=12),
        competidor("C2", velocidad=13, fuerza=10, salud=50),
        competidor("C3", stat=30),
        competidor("C4", stat=20),
    ]
    e, r = combate(cinco, comp.TOTEM, DadosFijos([10]))

    assert r.marcadores == (8, 8, 8, 12, 9)
    assert r.totales == (101, 102, 103, 120, 90)
    assert e.orden == (3, 4, 2, 1, 0)
    assert [c.nombre for c, _ in e.clasificacion] == [
        "C3", "C4", "C2", "C1", "C0"
    ]

    podio = comp.podio(e)
    assert "🥇 **C3**" in podio
    assert "🥈 **C4**" in podio
    assert "🥉 **C2**" in podio


def test_el_desempate_del_totem_no_es_una_cuarta_fase_para_los_demas():
    """Reproductor: A y B empatan exacto y C se queda atrás en bruto.

        AL CENTRO  40 30 20 -> 3 2 1
        FORCEJEO   30 20 40 -> 2 1 3
        HUIDA      20 40 25 -> 1 3 2
                              --------
        puestos                6  6  6
        bruto                 90 90 85

    Sólo A y B están empatados exacto. El forcejeo de desempate desempata
    **dentro** de ese empate: no es una fase más para todos, así que no puede
    coronar a C, que ya había quedado por detrás en el bruto oficial.
    """
    tres = [
        competidor("A", velocidad=30, fuerza=20, salud=10),
        competidor("B", velocidad=20, fuerza=10, salud=30),
        competidor("C", velocidad=10, fuerza=30, salud=15),
    ]
    e, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert r.desempates == 1
    assert r.marcadores == (6, 6, 6)
    assert r.totales == (90, 90, 85)
    assert e.orden == (0, 1, 2)
    assert e.campeon.nombre == "A"


def test_el_bruto_oficial_del_totem_manda_sobre_el_dorsal():
    tres = [
        competidor("C0", velocidad=20, fuerza=5, salud=30),
        competidor("C1", velocidad=32, fuerza=5, salud=20),
        competidor("C2", velocidad=10, fuerza=40, salud=10),
    ]
    _, r = combate(tres, comp.TOTEM, DadosFijos([10]))

    assert r.marcadores == (7, 7, 5)
    assert r.totales == (85, 87, 90)
    assert r.orden == (1, 0, 2)


def test_la_ultima_clasificacion_visible_del_totem_es_la_del_resultado():
    """Con un desempate de por medio, el último fotograma tiene que enseñar el
    orden con el que se reparte el premio y no otro."""
    tres = [
        competidor("A", velocidad=30, fuerza=20, salud=10),
        competidor("B", velocidad=20, fuerza=10, salud=30),
        competidor("C", velocidad=10, fuerza=30, salud=20),
    ]
    e, r = combate(tres, comp.TOTEM, DadosFijos([10]))
    assert r.desempates == 1
    assert r.orden == (2, 0, 1)

    ultimo = lineas(comp.fotogramas_de(e)[0][-1])
    puestos = [
        linea for linea in ultimo if linea.startswith(("│  1 ", "│  2 ", "│  3 "))
    ]
    assert [linea.split()[2] for linea in puestos] == ["C", "A", "B"]
    # Los puntos oficiales no se mueven por el desempate.
    assert [linea.split()[-2] for linea in puestos] == ["6", "6", "6"]


def test_un_desempate_no_vuelve_a_tirar_por_quien_ya_quedó_desempatado():
    """Dos empates exactos a la vez, y uno se resuelve antes que el otro.

    Cuatro iguales con dados `[6,6,1,1]` en las tres fases dejan dos grupos
    empatados exacto: A/B arriba y C/D abajo. El primer forcejeo deshace A/B
    (4 contra 2) pero no C/D (3 y 3), así que hace falta un segundo. Ese segundo
    es **de C y D**: si volviera a tirar por A y por B les cambiaría un orden ya
    decidido, que es justo lo que un desempate no puede hacer.
    """
    cuatro = [competidor(nombre, stat=10) for nombre in "ABCD"]
    dados = DadosFijos([6, 6, 1, 1] * 3 + [4, 2, 3, 3] + [1, 6, 1, 2])
    e, r = combate(cuatro, comp.TOTEM, dados)

    # Lo oficial no se mueve en ningún momento.
    assert r.marcadores == (12, 12, 6, 6)
    assert r.totales == (48, 48, 33, 33)

    desempates = [ronda for ronda in r.rondas if ronda.fase == comp.DESEMPATE]
    assert len(desempates) == 2
    # El primero es de los cuatro; el segundo, sólo de quien seguía empatado.
    assert desempates[0].dorsales == (0, 1, 2, 3)
    assert desempates[1].dorsales == (2, 3)
    assert dados.i == 12 + 4 + 2

    # A por delante de B como quedó en el primer forcejeo, y D sobre C por el
    # segundo (1 contra 6).
    assert e.orden == (0, 1, 3, 2)
    assert [c.nombre for c, _ in e.clasificacion] == ["A", "B", "D", "C"]


def test_el_fotograma_de_un_desempate_solo_ensena_a_quien_tira():
    cuatro = [competidor(nombre, stat=10) for nombre in "ABCD"]
    dados = DadosFijos([6, 6, 1, 1] * 3 + [4, 2, 3, 3] + [1, 6, 1, 2])
    e, r = combate(cuatro, comp.TOTEM, dados)
    fotogramas = comp.fotogramas_de(e)[0]
    assert len(fotogramas) == len(r.rondas)

    ultimo = lineas(fotogramas[-1])
    tiradas = [linea for linea in ultimo if "+d20" in linea]
    assert [linea.split()[1] for linea in tiradas] == ["C", "D"]

    # La clasificación sigue enseñando el campo entero, y en el orden con el que
    # se reparte el premio.
    puestos = [
        linea for linea in ultimo
        if linea.startswith(("│  1 ", "│  2 ", "│  3 ", "│  4 "))
    ]
    assert [linea.split()[2] for linea in puestos] == ["A", "B", "D", "C"]
    assert [linea.split()[-2] for linea in puestos] == ["12", "12", "6", "6"]


def test_un_grupo_que_no_se_deshace_agota_el_tope_y_cae_al_dorsal():
    """A y B se separan al primer forcejeo; C y D empatan siempre.

    El tope es global y el fallback sigue siendo el dorsal, así que C acaba por
    delante de D sin bucle infinito y sin tocar a A ni a B.
    """
    cuatro = [competidor(nombre, stat=10) for nombre in "ABCD"]
    dados = DadosFijos(
        [6, 6, 1, 1] * 3 + [4, 2, 3, 3] + [5, 5] * comp.MAX_DESEMPATES
    )
    _, r = combate(cuatro, comp.TOTEM, dados)

    desempates = [ronda for ronda in r.rondas if ronda.fase == comp.DESEMPATE]
    assert len(desempates) == comp.MAX_DESEMPATES
    assert all(ronda.dorsales == (2, 3) for ronda in desempates[1:])
    assert r.marcadores == (12, 12, 6, 6)
    assert r.orden == (0, 1, 2, 3)


def test_los_desempates_del_totem_van_por_ramas_y_no_por_un_marcador_sumado():
    """Cuatro idénticos: un solo empate oficial que se parte en dos.

        tres fases      16 16 16 16 -> puestos 12 12 12 12, bruto 48 48 48 48
        desempate 1     14 12 13 13 -> A arriba, B abajo, C y D en medio
        desempate 2      ·  · 11 16 -> el empate de C y D, sólo entre ellos

    Cada uno lleva su **senda**: A (14), B (12), C (13, 11) y D (13, 16). Se
    comparan por orden y de mayor a menor, así que C y D se colocan entre ellos
    sin salirse del hueco que les dejaron A y B. Sumarlo todo en un número —24 y
    29— los pondría por delante de A, que ya había ganado su desempate.
    """
    cuatro = [competidor(nombre, stat=10) for nombre in "ABCD"]
    dados = DadosFijos([6, 6, 6, 6] * 3 + [4, 2, 3, 3] + [1, 6])
    e, r = combate(cuatro, comp.TOTEM, dados)

    assert r.marcadores == (12, 12, 12, 12)
    assert r.totales == (48, 48, 48, 48)
    assert dados.i == 12 + 4 + 2

    desempates = [ronda for ronda in r.rondas if ronda.fase == comp.DESEMPATE]
    assert [ronda.dorsales for ronda in desempates] == [(0, 1, 2, 3), (2, 3)]
    assert [
        comp.senda_de_desempate(r.rondas, dorsal) for dorsal in range(4)
    ] == [(14,), (12,), (13, 11), (13, 16)]

    assert e.orden == (0, 3, 2, 1)
    assert [c.nombre for c, _ in e.clasificacion] == ["A", "D", "C", "B"]

    ultimo = lineas(comp.fotogramas_de(e)[0][-1])
    tiradas = [linea for linea in ultimo if "+d20" in linea]
    assert [linea.split()[1] for linea in tiradas] == ["C", "D"]
    puestos = [
        linea for linea in ultimo
        if linea.startswith(("│  1 ", "│  2 ", "│  3 ", "│  4 "))
    ]
    assert [linea.split()[2] for linea in puestos] == ["A", "D", "C", "B"]
    assert [linea.split()[-2] for linea in puestos] == ["12"] * 4
