"""El manual que el bot mantiene publicado en su canal.

Sustituye al viejo `/ayuda`: en vez de ocho mensajes efímeros que sólo veía
quien escribía el comando, hay ocho mensajes fijos en un canal que el bot pone
al día en cada arranque.

Lo que más se prueba aquí es que **no ensucie**: publicar en vez de editar
dejaría ocho mensajes más por despliegue, y en una semana el manual estaría
repetido veinte veces. Ni un solo test toca Discord: el canal se inyecta.
"""
import asyncio

import discord
import pytest

import cogs.social as social
import db

CANAL = 4242


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "manual.db")
    db.inicializar()


def correr(corrutina):
    return asyncio.run(corrutina)


class MensajeFalso:
    def __init__(self, canal, id_, contenido):
        self.canal = canal
        self.id = id_
        self.content = contenido

    async def edit(self, content):
        self.canal.editados.append((self.id, content))
        self.content = content


class CanalFalso:
    """Un canal de Discord de mentira, que apunta todo lo que le hacen."""

    # Compartido entre canales, como los de Discord: si cada canal empezara a
    # contar por su cuenta, dos mensajes de canales distintos saldrían con el
    # mismo id y este doble mentiría sobre lo que puede pasar de verdad.
    _siguiente = 1000

    def __init__(self, id_=CANAL):
        self.id = id_
        self.name = "gachamon-info"
        self.mensajes: dict[int, MensajeFalso] = {}
        self.publicados: list[str] = []
        self.editados: list[tuple[int, str]] = []

    async def send(self, contenido):
        CanalFalso._siguiente += 1
        mensaje = MensajeFalso(self, CanalFalso._siguiente, contenido)
        self.mensajes[mensaje.id] = mensaje
        self.publicados.append(contenido)
        return mensaje

    async def fetch_message(self, id_):
        if id_ not in self.mensajes:
            raise discord.NotFound(_RespuestaFalsa(), "no está")
        return self.mensajes[id_]


class _RespuestaFalsa:
    """Lo mínimo que `discord.NotFound` mira de una respuesta HTTP."""

    status = 404
    reason = "Not Found"


PAGINAS = ("## Uno\ntexto", "## Dos\ntexto", "## Tres\ntexto")


# --- Publicar y mantener ----------------------------------------------------

def test_la_primera_vez_publica_una_pagina_por_mensaje():
    """Una por mensaje y no todas juntas: Discord corta el contenido en 2000
    caracteres, que es lo que ya rompió la ayuda una vez."""
    canal = CanalFalso()

    correr(social.publicar_manual(canal, PAGINAS))

    assert canal.publicados == list(PAGINAS)
    assert canal.editados == []
    # Y queda apuntado dónde está cada una, que es lo que permite editarlas.
    ids = [db.publicacion_en(str(CANAL), i) for i in range(len(PAGINAS))]
    assert all(ids) and len(set(ids)) == len(ids)


def test_un_arranque_sin_cambios_no_toca_nada():
    """Lo que hace que reiniciar sea gratis: sin esto, cada despliegue dejaría
    un «editado» en las ocho páginas aunque no hubiera cambiado ni una coma."""
    canal = CanalFalso()
    correr(social.publicar_manual(canal, PAGINAS))
    canal.publicados.clear()

    correr(social.publicar_manual(canal, PAGINAS))

    assert canal.publicados == [] and canal.editados == []


def test_solo_se_edita_la_pagina_que_cambio():
    canal = CanalFalso()
    correr(social.publicar_manual(canal, PAGINAS))
    canal.publicados.clear()

    cambiadas = (PAGINAS[0], "## Dos\ntexto NUEVO", PAGINAS[2])
    correr(social.publicar_manual(canal, cambiadas))

    assert canal.publicados == []
    assert [texto for _, texto in canal.editados] == ["## Dos\ntexto NUEVO"]


def test_nunca_republica_lo_que_ya_esta_puesto():
    """El fallo que arruinaría el canal: diez arranques seguidos tienen que
    dejar tres mensajes, no treinta."""
    canal = CanalFalso()
    for _ in range(10):
        correr(social.publicar_manual(canal, PAGINAS))

    assert len(canal.mensajes) == len(PAGINAS)


def test_si_borras_una_pagina_la_vuelve_a_publicar():
    """Vaciar el canal a mano no es un error: es la forma de pedirle al bot que
    lo rehaga. Y sólo repone la que falta, sin tocar las demás."""
    canal = CanalFalso()
    correr(social.publicar_manual(canal, PAGINAS))
    perdido = int(db.publicacion_en(str(CANAL), 1))
    del canal.mensajes[perdido]
    canal.publicados.clear()

    correr(social.publicar_manual(canal, PAGINAS))

    assert canal.publicados == [PAGINAS[1]]
    assert canal.editados == []
    nuevo = db.publicacion_en(str(CANAL), 1)
    assert nuevo and int(nuevo) != perdido       # se apunta el id nuevo
    assert len(canal.mensajes) == len(PAGINAS)


def test_cada_canal_lleva_su_propia_cuenta():
    """Cada servidor necesita su canal, y el manual de uno no puede pisar el
    del otro."""
    uno, otro = CanalFalso(1), CanalFalso(2)

    correr(social.publicar_manual(uno, PAGINAS))
    correr(social.publicar_manual(otro, PAGINAS))

    assert len(uno.mensajes) == len(otro.mensajes) == len(PAGINAS)
    assert db.publicacion_en("1", 0) != db.publicacion_en("2", 0)


# --- El manual de verdad ----------------------------------------------------

def test_el_manual_publicado_es_el_de_siempre_y_cabe_en_discord():
    """Sale de `paginas_de_ayuda`, la misma función que alimentaba a `/ayuda`,
    así que se genera de las constantes del juego y no puede desfasarse.

    El tope de 2000 se comprueba aquí además de en `test_textos`: allí protegía
    un comando que fallaba en privado; ahora un desbordamiento dejaría el canal
    público a medias.
    """
    paginas = social.paginas_de_ayuda("Gachamones")
    canal = CanalFalso()

    correr(social.publicar_manual(canal, paginas))

    assert canal.publicados == list(paginas)
    assert len(paginas) > 1, "si fuera una sola, partirla no serviría de nada"
    for pagina in paginas:
        assert len(pagina) <= 2000, len(pagina)


def test_ya_no_existe_el_comando_de_ayuda():
    """Se quitó a propósito: el manual vive en el canal, donde se puede volver
    a mirar, y no en ocho mensajes efímeros que desaparecen."""
    assert not hasattr(social.Social, "ayuda")


# --- El arranque: nada de esto puede tumbar el bot --------------------------

def cog_con(canales, monkeypatch, canal=None, publicar=None):
    """El cog de Social sin construirlo entero, con su bot de mentira."""
    from types import SimpleNamespace

    monkeypatch.setattr(social.config, "CANALES_INFO", canales)
    if publicar is not None:
        monkeypatch.setattr(social, "publicar_manual", publicar)
    cog = social.Social.__new__(social.Social)
    cog.bot = SimpleNamespace(
        get_channel=lambda cid: canal if canal and canal.id == cid else None,
        user=SimpleNamespace(display_name="Gachamones"),
    )
    cog._manual_al_dia = set()
    return cog


def test_al_arrancar_deja_el_manual_al_dia(monkeypatch):
    """De punta a punta y sin dobles de la publicación: el canal acaba con el
    manual de verdad dentro, el que sale de las constantes del juego."""
    canal = CanalFalso()
    cog = cog_con((CANAL,), monkeypatch, canal=canal)

    correr(cog.on_ready())

    assert canal.publicados == list(social.paginas_de_ayuda("Gachamones"))
    assert cog._manual_al_dia == {CANAL}


def test_sin_canal_configurado_no_publica_nada(monkeypatch):
    """En local no hay canal, y un servidor sin él sigue funcionando igual."""
    llamadas = []

    async def espia(canal, paginas):
        llamadas.append(canal)

    cog = cog_con((), monkeypatch, publicar=espia)
    correr(cog.on_ready())

    assert llamadas == []


def test_un_canal_que_no_se_ve_avisa_y_no_revienta(monkeypatch, caplog):
    """El caso de equivocarse de ID o de no haber invitado al bot. Antes de que
    esto existiera, `bot.py` ya trataba así los servidores inalcanzables."""
    cog = cog_con((9999,), monkeypatch)

    with caplog.at_level("WARNING"):
        correr(cog.on_ready())

    assert "9999" in caplog.text
    assert not cog._manual_al_dia          # se reintentará al reconectar


@pytest.mark.parametrize("fallo", [
    discord.Forbidden(_RespuestaFalsa(), "sin permiso"),
    discord.HTTPException(_RespuestaFalsa(), "la nube"),
])
def test_un_fallo_de_discord_avisa_y_no_revienta(fallo, monkeypatch, caplog):
    canal = CanalFalso()

    async def revienta(canal_, paginas):
        raise fallo

    cog = cog_con((CANAL,), monkeypatch, canal=canal, publicar=revienta)

    with caplog.at_level("WARNING"):
        correr(cog.on_ready())      # no lanza

    assert caplog.records
    assert not cog._manual_al_dia          # se reintentará


def test_reconectar_no_vuelve_a_repasar_el_canal(monkeypatch):
    """`on_ready` se dispara en cada reconexión y el texto sólo cambia al
    desplegar, que reinicia: repasarlo una vez por arranque basta y ahorra ocho
    consultas a la API cada vez que Discord se cae un momento."""
    canal = CanalFalso()
    veces = []

    async def espia(canal_, paginas):
        veces.append(canal_)

    cog = cog_con((CANAL,), monkeypatch, canal=canal, publicar=espia)

    correr(cog.on_ready())
    correr(cog.on_ready())
    correr(cog.on_ready())

    assert len(veces) == 1
    assert cog._manual_al_dia == {CANAL}
