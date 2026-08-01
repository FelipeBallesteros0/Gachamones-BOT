"""El vocabulario visible usa los términos canónicos del producto."""
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import aventura
from cogs import competencias, mascota, social
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


def test_prompts_usan_gachamon_y_aventura_nombra_comida():
    c = gachamon()
    salvaje = aventura.Salvaje(
        "chispa", "Salvaje", c.genero, "gruñón", (10, 10, 10)
    )
    charla = per.construir_prompt(c, T0, "Alan")
    jardin = per.prompt_jardin([c], T0)[0]
    viaje = per.prompt_aventura(
        c, "al bosque", [], aventura.NADA, aventura.PERCANCE
    )[0]
    escena = per.prompt_escena("al bosque", 1)[0]
    voz_salvaje = per.prompt_salvaje(salvaje, c, "hola")[0]

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
    # El número sale del catálogo, no escrito aquí: al pasar de 10 a 25
    # especies este test habría fallado sin que la ayuda estuviera mal.
    import especies as esp
    assert (f"ves cuál de los {len(esp.ESPECIES)} gachamones te ha tocado"
            in ayuda)
    assert "El buen ánimo suma un poco; tener poca comida resta." in ayuda
    assert (
        "`/jardin` todos juntos · `/mascota` el tuyo · "
        "`/mascota @alguien` el de otro"
    ) in ayuda
    assert all(len(pagina) <= 2000 for pagina in paginas)
