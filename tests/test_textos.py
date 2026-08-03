"""El vocabulario visible usa los términos canónicos del producto."""
import re
from dataclasses import replace
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

import aventura
from cogs import competencias, mascota, social
import competir as comp
import economia
import objetos
import pantalla
import personalidad as per
import simulacion as sim
import tienda
import vistas

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def gachamon(**cambios) -> sim.Criatura:
    datos: dict[str, Any] = dict(
        id=1,
        usuario_id="u1",
        guild_id="g1",
        especie="pulpo",
        nombre="Prueba",
        nacida_en=T0,
        actualizada_en=T0,
        base_fuerza=15,
        base_velocidad=15,
        base_salud=15,
    )
    datos.update(cambios)
    return sim.Criatura(**datos)


def contexto_salvaje(salvaje, acompañante):
    antes = aventura.Encuentro(salvaje, confianza=40, paciencia=4)
    despues = aventura.Encuentro(
        salvaje, confianza=45, paciencia=3, ultimo_cambio=5
    )
    return aventura.ContextoSalvaje(
        salvaje=salvaje,
        acompañante=acompañante,
        fase=aventura.fase_de(antes.confianza),
        fase_ahora=aventura.fase_de(despues.confianza),
        tendencia=aventura.tendencia_de(antes, despues),
        paciencia=despues.paciencia,
        dicho="hola",
    )


def test_prompts_usan_gachamon_y_aventura_nombra_comida():
    c = gachamon()
    salvaje = aventura.Salvaje("chispa", "Salvaje", c.genero, "gruñón", (10, 10, 10, 15))
    charla = per.construir_prompt(c, T0, "Alan")
    jardin = per.prompt_jardin([c], T0)[0]
    viaje = per.prompt_aventura(
        c, "al bosque", [], aventura.NADA, aventura.PERCANCE
    )[0]
    escena = per.prompt_escena(
        "al bosque", 1, especies=aventura.BIOMAS["bosque"].nombres_especies,
        pareja=(aventura.FUERZA, aventura.VELOCIDAD),
        favorecida=aventura.FUERZA,
    )[0]
    voz_salvaje = per.prompt_salvaje(contexto_salvaje(salvaje, c))[0]

    assert "no les hablas directamente" in jardin
    assert "Respeta el género indicado de cada gachamon" in jardin
    assert "no les hablas a ellas" not in jardin
    assert "referirte a él" not in jardin
    for sistema in (charla, jardin, viaje, escena, voz_salvaje):
        restante = sistema.replace(per.REGLA_NOMBRE_GACHAMON, "").casefold()
        assert "gachamon" in sistema.casefold()
        assert not re.search(r"\b(?:criaturas?|mascotas?)\b", restante)
    for sistema in (charla, jardin, viaje, voz_salvaje):
        assert per.REGLA_NOMBRE_GACHAMON in sistema
    assert "-5 comida y -5 ánimo" in viaje


def test_ficha_usa_barras_canonicas_sin_cambiar_el_marco():
    mensaje = ANSI.sub("", pantalla.render(gachamon(), T0))
    marco = mensaje.split("```ansi\n")[1].split("\n```")[0].splitlines()
    separadores = [i for i, linea in enumerate(marco) if linea.startswith("├")]
    barras = marco[separadores[0] + 1 : separadores[1]]

    assert [linea[2:9].strip() for linea in barras] == ["COMIDA", "ÁNIMO", "ASEO"]
    assert {len(linea) for linea in marco} == {pantalla.ANCHO + 2}
    assert all(linea[0] in "╭├╰│" and linea[-1] in "╮┤╯│" for linea in marco)


def test_recibos_deltas_y_requisitos_nombrar_comida_animo_y_aseo(monkeypatch):
    criatura = gachamon(hambre=40.0, limpieza=25.0)
    monkeypatch.setattr(tienda.db, "guardar", lambda _: None)

    assert "Comida +25 (ahora 65)." in tienda.usar(
        criatura, objetos.CATALOGO["golosinas"], T0
    )
    assert aventura.render_percance(aventura.PERCANCE) == (
        "⚠️ Percance: -5 comida y -5 ánimo."
    )
    problema = competencias._problema_para_competir(
        replace(criatura, hambre=0), "Alan", timedelta(0)
    )
    assert problema and "hambriento" in problema and "de comida" in problema

    resultado = economia.ResultadoCuidado(criatura=criatura, mensaje="")
    assert vistas._efecto_recibo_cuidado(resultado, sim.LIMPIAR) == (
        "🧼 Limpiar",
        "aseo 100",
        "+0 XP",
    )


def test_catalogo_visible_nombra_la_barra_comida():
    assert objetos.CATALOGO["pocion_comida"].descripcion.startswith(
        "Deja la comida a 100."
    )
    assert "+25 de comida" in objetos.CATALOGO["golosinas"].descripcion


def test_ayuda_conserva_el_comando_mascota_y_el_limite_de_discord():
    paginas = social.paginas_de_ayuda("Gachamones")
    ayuda = "\n".join(paginas)

    assert "**Cuidarlo**" in ayuda
    assert "Cuidarlo da experiencia" in ayuda
    assert "Y qué hacer con él" in ayuda
    assert getattr(mascota.Mascota, "mascota").name == "mascota"
    # Los números salen del catálogo, no escritos aquí: al pasar de 10 a 25
    # especies este test habría fallado sin que la ayuda estuviera mal.
    import especies as esp
    assert (f"ves cuál de los {len(esp.DEL_HUEVO)} gachamones de partida"
            in ayuda)
    del_campo = len(esp.ESPECIES) - len(esp.DEL_HUEVO)
    assert f"Los otros **{del_campo}** no salen del huevo" in ayuda
    assert "El buen ánimo suma un poco; tener poca comida resta." in ayuda
    assert (
        "`/jardin` todos juntos · `/mascota` el tuyo · "
        "`/mascota @alguien` el de otro"
    ) in ayuda
    assert all(len(pagina) <= 2000 for pagina in paginas)


# «Coger» es de España y aquí se dice tomar. Va con frontera de palabra para no
# pisar «recoger» ni «escoger», que sí son neutras.
COGER = re.compile(r"\bcog[ei]\w*", re.IGNORECASE)


def test_el_texto_visible_de_competir_usa_espanol_neutro():
    visible = "\n".join((
        *social.paginas_de_ayuda("Gachamones"),
        *comp.REGLAS.values(),
        *comp.ARTICULOS.values(),
        (Path(__file__).resolve().parent.parent / "README.md").read_text(
            encoding="utf-8"
        ),
    ))

    encontrado = COGER.search(visible)
    assert encontrado is None, encontrado.group(0)


def test_la_ayuda_explica_las_tres_fases_del_asalto_al_totem():
    """Quien lea la ayuda tiene que poder llamar al comando y saber qué mide."""
    paginas = social.paginas_de_ayuda("Gachamones")
    ayuda = "\n".join(paginas)

    assert "`/totem @alguien`" in ayuda
    assert "Asalto al Tótem" in ayuda
    for fase, stat in zip(comp.FASES_TOTEM, comp.STATS[comp.TOTEM]):
        assert f"**{fase}** ({stat}" in ayuda
    assert "puntos de colocación" in ayuda
    assert all(len(pagina) <= 2000 for pagina in paginas)


def test_la_ayuda_explica_las_fases_del_laberinto():
    """Quien lea la ayuda tiene que saber contra qué juega y cuándo cruza."""
    paginas = social.paginas_de_ayuda("Gachamones")
    ayuda = "\n".join(paginas)

    assert "`/laberinto @alguien`" in ayuda
    for fase in comp.FASES_LABERINTO:
        assert f"**{fase}**" in ayuda, fase
    assert "eco" in ayuda and "puertas" in ayuda
    assert "participante del medio" in ayuda
    assert "igualarlo no basta" in ayuda
    assert f"Entran hasta {comp.MAX_CORREDORES}" in ayuda
    assert all(len(pagina) <= 2000 for pagina in paginas)


def test_la_ayuda_dice_que_las_estadisticas_de_nacimiento_son_cuatro():
    ayuda = "\n".join(social.paginas_de_ayuda("Gachamones"))

    assert "las cuatro" in ayuda
    for stat in ("fuerza", "velocidad", "salud", "ingenio"):
        assert stat in ayuda, stat


def test_la_ayuda_mapea_cada_entrenamiento_sin_prometer_subida_inmediata():
    ayuda = "\n".join(social.paginas_de_ayuda("Gachamones"))

    for regla in (
        "**Alimentar** → Salud +1 entrenamiento si no hay empacho.",
        "**Jugar** → Velocidad +1 entrenamiento.",
        "**Entrenar fuerza** → Fuerza +2 entrenamiento.",
        "**Laberinto completado** → Ingenio +1 entrenamiento por participante.",
    ):
        assert regla in ayuda, regla
    assert "alimentar +1, jugar +2, entrenar fuerza +3" in ayuda
    assert "puntos de entrenamiento" in ayuda
    assert "raíz cuadrada" in ayuda
    assert "no siempre cambia el número visible" in ayuda


# --- Los nombres de las especies -------------------------------------------
#
# Jugando salió «un grupo de chispas», y Chispa dejó de existir el 31 de julio:
# hoy se llama Pyro. Lo que lo permitía es que a la escena se le pedía inventar
# —incluso «otro gachamon que no deja pasar»— sin decirle qué especies hay.

def test_la_escena_solo_puede_nombrar_a_los_del_bioma():
    """El censo va en el prompt y sale del catálogo, no escrito aquí: así un
    rebautizo futuro llega solo y este test no se puede quedar viejo."""
    import especies as esp

    for clave, bioma in aventura.BIOMAS.items():
        sistema, _ = per.prompt_escena(
            bioma.adonde, 1, especies=bioma.nombres_especies,
            pareja=(aventura.FUERZA, aventura.VELOCIDAD),
            favorecida=aventura.FUERZA,
        )
        for nombre in bioma.nombres_especies:
            assert nombre in sistema, (clave, nombre)
        for otra in esp.ESPECIES.values():
            if otra.clave not in bioma.especies:
                assert otra.nombre not in sistema, (clave, otra.nombre)
        assert "Nunca te inventes nombres de especie." in sistema


def test_el_censo_enumera_en_castellano():
    """La «o» pasa a «u» ante palabra que empieza por o-, y en el catálogo hay
    justo un caso: el Arrecife acaba en «Remolín u Octopul». No rompe nada y
    canta al leerlo, que es exactamente lo que no cazaría ningún otro test."""
    assert per.enumerar(("Pyro",)) == "Pyro"
    assert per.enumerar(("Pyro", "Tsushimon")) == "Pyro o Tsushimon"
    assert per.enumerar(("Geo", "Ostra")) == "Geo u Ostra"
    assert per.enumerar(("Geo", "Hongo")) == "Geo u Hongo"
    assert per.enumerar(aventura.BIOMAS["arrecife"].nombres_especies) == (
        "Coralito, Nacar, Remolín u Octopul"
    )


def test_ninguna_pantalla_ensena_la_clave_de_la_especie():
    """El invariante de fondo: lo que se guarda es la clave y lo que se ve es el
    nombre. Diez especies tienen los dos distintos desde el rebautizo, y son las
    únicas donde confundirlos se nota."""
    import especies as esp

    for especie in esp.ESPECIES.values():
        if especie.clave.casefold() == especie.nombre.casefold():
            continue
        ficha = ANSI.sub("", pantalla.render(gachamon(especie=especie.clave), T0))
        assert especie.nombre in ficha, especie.clave
        assert especie.clave not in ficha.casefold(), especie.clave
