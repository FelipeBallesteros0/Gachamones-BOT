"""Persistencia: ida y vuelta, el índice de una sola criatura viva y muere_en."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1", guild="g1", especie="pulpo", nombre="Prueba", ahora=T0):
    return db.crear(usuario, guild, especie, nombre, STATS, ahora)


def test_crear_y_recuperar():
    creada = nacer()
    recuperada = db.criatura_viva("u1", "g1")

    assert recuperada is not None
    assert recuperada.id == creada.id
    assert recuperada.nombre == "Prueba"
    assert recuperada.especie == "pulpo"
    assert (recuperada.base_fuerza, recuperada.base_velocidad, recuperada.base_salud) == STATS
    assert recuperada.nacida_en == T0


def test_solo_una_criatura_viva_por_persona():
    """Lo impone el índice único de SQLite, no el código: dos `/huevo` a la vez
    no pueden colar dos criaturas."""
    nacer()
    with pytest.raises(sqlite3.IntegrityError):
        nacer(nombre="Otra")


def test_tras_morir_se_puede_tener_otra():
    primera = nacer()
    db.guardar(sim.Criatura(**{
        **primera.__dict__, "muerta_en": T0 + timedelta(days=3), "causa_muerte": "hambre",
    }))

    segunda = nacer(nombre="Segunda")
    assert segunda.id != primera.id
    assert db.criatura_viva("u1", "g1").nombre == "Segunda"


def test_dos_personas_distintas_no_se_estorban():
    nacer(usuario="u1")
    nacer(usuario="u2", nombre="Suya")
    assert db.criatura_viva("u1", "g1").nombre == "Prueba"
    assert db.criatura_viva("u2", "g1").nombre == "Suya"


def test_la_misma_persona_puede_tener_una_por_servidor():
    nacer(guild="g1")
    nacer(guild="g2", nombre="Otra")
    assert db.criatura_viva("u1", "g1").nombre == "Prueba"
    assert db.criatura_viva("u1", "g2").nombre == "Otra"


def test_guardar_conserva_todos_los_campos():
    criatura = nacer()
    from dataclasses import replace
    modificada = replace(
        criatura,
        hambre=42.5, animo=17.25, limpieza=3.0,
        ent_fuerza=9, ent_velocidad=4, ent_salud=1,
        niv_fuerza=2, niv_velocidad=1, niv_salud=0,
        xp=7, nivel=4, victorias=6, derrotas=3,
        actualizada_en=T0 + timedelta(hours=5),
        pantalla_msg_id="123456789",
    )
    db.guardar(modificada)

    assert db.criatura_viva("u1", "g1") == modificada


def test_muere_en_se_guarda_y_lo_usa_el_bucle_de_muerte():
    criatura = nacer()
    momento = sim.momento_de_muerte(criatura)

    assert db.pendientes_de_morir(momento - timedelta(minutes=1)) == []

    pendientes = db.pendientes_de_morir(momento + timedelta(minutes=1))
    assert [c.id for c in pendientes] == [criatura.id]


def test_alimentar_aleja_la_hora_de_la_muerte():
    criatura = nacer()
    antes = sim.momento_de_muerte(criatura)

    hambrienta = sim.avanzar(criatura, T0 + timedelta(hours=40))
    llena = sim.aplicar_accion(hambrienta, sim.ALIMENTAR, T0 + timedelta(hours=40))
    db.guardar(llena.criatura)

    assert sim.momento_de_muerte(db.criatura_viva("u1", "g1")) > antes


def test_una_criatura_muerta_no_vuelve_a_salir_como_pendiente():
    criatura = nacer()
    muerta = sim.avanzar(criatura, T0 + timedelta(days=10))
    assert not muerta.viva
    db.guardar(muerta)

    assert db.pendientes_de_morir(T0 + timedelta(days=20)) == []


def test_el_aviso_de_hambre_se_dispara_una_sola_vez():
    from dataclasses import replace
    criatura = nacer()
    momento = sim.momento_de_aviso(criatura)

    assert db.pendientes_de_aviso(momento - timedelta(minutes=1)) == []

    pendientes = db.pendientes_de_aviso(momento + timedelta(minutes=1))
    assert [c.id for c in pendientes] == [criatura.id]

    # Una vez avisada, deja de aparecer aunque siga con hambre.
    avisada = sim.avanzar(criatura, momento + timedelta(minutes=1))
    db.guardar(replace(avisada, avisada=True))
    assert db.pendientes_de_aviso(momento + timedelta(hours=1)) == []


def test_alimentarla_hace_que_vuelva_a_avisar_mas_adelante():
    criatura = nacer()
    momento = sim.momento_de_aviso(criatura)

    hambrienta = sim.avanzar(criatura, momento + timedelta(minutes=1))
    from dataclasses import replace
    db.guardar(replace(hambrienta, avisada=True))

    llena = sim.aplicar_accion(
        db.criatura_viva("u1", "g1"), sim.ALIMENTAR, momento
    ).criatura
    db.guardar(llena)

    assert db.pendientes_de_aviso(momento + timedelta(minutes=2)) == []
    guardada = db.criatura_viva("u1", "g1")
    assert not guardada.avisada
    assert sim.momento_de_aviso(guardada) > momento


def test_una_criatura_muerta_no_genera_avisos():
    criatura = nacer()
    db.guardar(sim.avanzar(criatura, T0 + timedelta(days=10)))
    assert db.pendientes_de_aviso(T0 + timedelta(days=20)) == []


def test_migracion_de_una_base_de_datos_antigua():
    """Una BD de la versión anterior no tiene avisa_en ni avisada: al abrirla
    hay que añadir las columnas y rellenarlas sin perder las criaturas."""
    criatura = nacer(nombre="Veterana")

    with db.conectar() as con:
        # El índice referencia las columnas: hay que quitarlo primero.
        con.execute("DROP INDEX IF EXISTS idx_avisa")
        for columna in ("avisa_en", "avisada"):
            con.execute(f"ALTER TABLE criaturas DROP COLUMN {columna}")
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert "avisa_en" not in columnas

    db.inicializar()

    recuperada = db.criatura_viva("u1", "g1")
    assert recuperada is not None
    assert recuperada.nombre == "Veterana"
    assert not recuperada.avisada
    # Y el aviso vuelve a estar programado.
    assert db.pendientes_de_aviso(sim.momento_de_aviso(criatura) + timedelta(minutes=1))


def test_cooldowns():
    criatura = nacer()
    assert db.espera_de(criatura.id, sim.ALIMENTAR, T0) == timedelta(0)

    db.poner_cooldown(criatura.id, sim.ALIMENTAR, T0)
    espera = db.espera_de(criatura.id, sim.ALIMENTAR, T0)
    assert espera == sim.COOLDOWNS[sim.ALIMENTAR]

    assert db.espera_de(criatura.id, sim.ALIMENTAR, T0 + timedelta(hours=1)) == timedelta(0)


def test_poner_cooldown_dos_veces_reemplaza():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.JUGAR, T0)
    db.poner_cooldown(criatura.id, sim.JUGAR, T0 + timedelta(minutes=10))
    espera = db.espera_de(criatura.id, sim.JUGAR, T0 + timedelta(minutes=10))
    assert espera == sim.COOLDOWNS[sim.JUGAR]


def test_esperas_solo_lista_las_acciones_de_cuidado():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    esperas = db.esperas(criatura.id, T0)
    assert set(esperas) == set(sim.ACCIONES_DE_CUIDADO)


def test_la_criatura_recuerda_su_canal():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="555")
    assert db.criatura_viva("u1", "g1").canal_id == "555"


def test_publicar_en_otro_canal_mueve_los_avisos():
    """Con el bot en varios canales, los avisos siguen a la persona: se guarda
    el canal donde se atendió por última vez."""
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="111")

    db.guardar_pantalla(criatura.id, "msg1", "222")
    movida = db.criatura_viva("u1", "g1")
    assert movida.canal_id == "222"
    assert movida.pantalla_msg_id == "msg1"


def test_guardar_pantalla_sin_canal_no_borra_el_que_habia():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="111")
    db.guardar_pantalla(criatura.id, "msg1")
    assert db.criatura_viva("u1", "g1").canal_id == "111"


def test_el_genero_y_el_caracter_van_y_vuelven():
    db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0,
             genero=esp.HEMBRA, caracter="gruñón")
    recuperada = db.criatura_viva("u1", "g1")
    assert recuperada.genero == esp.HEMBRA
    assert recuperada.caracter == "gruñón"


def test_migracion_pone_macho_y_un_caracter_al_azar_a_las_de_antes():
    """Las criaturas anteriores al género se quedan macho —es lo pedido— y cada
    una recibe una personalidad distinta, no todas la misma."""
    for i in range(30):
        db.crear(f"u{i}", "g1", "pulpo", f"Veterana{i}", STATS, T0)

    with db.conectar() as con:
        for columna in ("genero", "caracter"):
            con.execute(f"ALTER TABLE criaturas DROP COLUMN {columna}")
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert "genero" not in columnas and "caracter" not in columnas

    db.inicializar()

    caracteres = []
    for i in range(30):
        recuperada = db.criatura_viva(f"u{i}", "g1")
        assert recuperada.nombre == f"Veterana{i}", "se ha perdido una criatura"
        assert recuperada.genero == esp.MACHO
        assert recuperada.caracter in per.CARACTERES
        caracteres.append(recuperada.caracter)

    # Lo que un DEFAULT en el ALTER TABLE no podría dar: variedad.
    assert len(set(caracteres)) > 1, caracteres


def test_la_migracion_no_le_cambia_el_caracter_a_quien_ya_lo_tiene():
    db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, caracter="perezoso")
    db.inicializar()
    assert db.criatura_viva("u1", "g1").caracter == "perezoso"


def test_migracion_añade_canal_id_sin_perder_criaturas():
    criatura = nacer(nombre="Veterana")

    with db.conectar() as con:
        con.execute("ALTER TABLE criaturas DROP COLUMN canal_id")
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert "canal_id" not in columnas

    db.inicializar()

    recuperada = db.criatura_viva("u1", "g1")
    assert recuperada.nombre == "Veterana"
    # Sin canal guardado: el bot cae al canal principal para avisar.
    assert recuperada.canal_id is None


def test_saber_de_quien_es_una_pantalla():
    criatura = nacer()
    db.guardar_pantalla(criatura.id, "999")

    encontrada = db.criatura_por_pantalla("999")
    assert encontrada is not None and encontrada.id == criatura.id
    assert db.criatura_por_pantalla("otra") is None


# --- Memoria de la conversación --------------------------------------------

def test_el_historial_sale_en_orden_cronologico():
    c = nacer()
    db.guardar_turnos(c.id, "hola", "¡pío!", T0)
    db.guardar_turnos(c.id, "que tal?", "bien, pío", T0 + timedelta(minutes=1))

    assert db.historial(c.id) == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡pío!"},
        {"role": "user", "content": "que tal?"},
        {"role": "assistant", "content": "bien, pío"},
    ]


def test_la_memoria_se_poda_a_los_ultimos_turnos():
    """El prompt no puede crecer sin límite: cada turno guardado se paga en
    tokens en todas las respuestas siguientes."""
    c = nacer()
    for i in range(30):
        db.guardar_turnos(c.id, f"mensaje {i}", f"respuesta {i}", T0)

    memoria = db.historial(c.id)
    assert len(memoria) == db.TURNOS_RECORDADOS
    assert memoria[-1]["content"] == "respuesta 29"
    assert "mensaje 0" not in [m["content"] for m in memoria]


def test_cada_criatura_tiene_su_propia_memoria():
    una = nacer(usuario="u1")
    otra = nacer(usuario="u2", nombre="Otra")
    db.guardar_turnos(una.id, "secreto", "lo guardo", T0)

    assert db.historial(otra.id) == []
    assert len(db.historial(una.id)) == 2


def test_una_criatura_nueva_empieza_sin_recuerdos():
    """La memoria va atada a criatura_id: al morir y sacar otro huevo, la
    relación empieza de cero sin código que lo gestione."""
    primera = nacer()
    db.guardar_turnos(primera.id, "hola", "¡pío!", T0)
    db.guardar(sim.avanzar(primera, T0 + timedelta(days=10)))

    segunda = nacer(nombre="Segunda")
    assert db.historial(segunda.id) == []


def test_se_puede_olvidar_a_mano():
    c = nacer()
    db.guardar_turnos(c.id, "hola", "¡pío!", T0)
    db.olvidar(c.id)
    assert db.historial(c.id) == []


# --- Límite de uso de la IA ------------------------------------------------

def test_el_uso_se_cuenta_por_hora():
    assert db.uso_ia_ultima_hora("u1", T0) == 0

    for i in range(3):
        db.registrar_uso_ia("u1", T0 + timedelta(minutes=i))
    assert db.uso_ia_ultima_hora("u1", T0 + timedelta(minutes=5)) == 3

    # Una hora después ya no cuentan.
    assert db.uso_ia_ultima_hora("u1", T0 + timedelta(hours=2)) == 0


def test_el_limite_es_por_persona():
    db.registrar_uso_ia("u1", T0)
    db.registrar_uso_ia("u1", T0)
    db.registrar_uso_ia("u2", T0)

    assert db.uso_ia_ultima_hora("u1", T0) == 2
    assert db.uso_ia_ultima_hora("u2", T0) == 1


def test_se_sabe_cuando_fue_el_ultimo_mensaje():
    assert db.ultimo_uso_ia("u1") is None
    db.registrar_uso_ia("u1", T0)
    db.registrar_uso_ia("u1", T0 + timedelta(minutes=10))
    assert db.ultimo_uso_ia("u1") == T0 + timedelta(minutes=10)


def test_los_registros_viejos_se_limpian():
    db.registrar_uso_ia("u1", T0)
    db.registrar_uso_ia("u1", T0 + timedelta(hours=5))

    borrados = db.limpiar_uso_ia(T0 + timedelta(hours=5))
    assert borrados == 1
    assert db.uso_ia_ultima_hora("u1", T0 + timedelta(hours=5)) == 1


def test_ranking_ordena_por_victorias():
    from dataclasses import replace
    for usuario, victorias in (("u1", 1), ("u2", 7), ("u3", 3)):
        criatura = nacer(usuario=usuario, nombre=usuario)
        db.guardar(replace(criatura, victorias=victorias))

    assert [c.nombre for c in db.ranking("g1")] == ["u2", "u3", "u1"]


def test_las_vivas_del_servidor_son_las_del_jardin():
    nacer(usuario="u1", nombre="Viva1")
    nacer(usuario="u2", nombre="Viva2")
    nacer(usuario="u3", guild="otro", nombre="DeOtroServidor")
    muerta = sim.avanzar(nacer(usuario="u4", nombre="Finada"), T0 + timedelta(days=10))
    db.guardar(muerta)

    nombres = [c.nombre for c in db.vivas_del_servidor("g1")]
    assert nombres == ["Viva1", "Viva2"]


def test_el_cementerio_solo_tiene_muertas():
    viva = nacer(usuario="u1")
    muerta = sim.avanzar(nacer(usuario="u2", nombre="Finada"), T0 + timedelta(days=10))
    db.guardar(muerta)

    nombres = [c.nombre for c in db.cementerio("g1")]
    assert nombres == ["Finada"]
    assert viva.nombre not in nombres


# --- Monedero, inventario y efectos ---------------------------------------

def test_las_gemas_de_bienvenida_se_dan_una_sola_vez():
    """El monedero se crea al consultarlo. Si el regalo se repitiera en cada
    consulta, mirar el saldo sería una forma de hacerse rico."""
    import objetos as obj

    assert db.gemas("u1", "g1") == obj.GEMAS_DE_BIENVENIDA
    assert db.gemas("u1", "g1") == obj.GEMAS_DE_BIENVENIDA
    assert db.gemas("u1", "g1") == obj.GEMAS_DE_BIENVENIDA

    db.cobrar("u1", "g1", 30)
    assert db.gemas("u1", "g1") == obj.GEMAS_DE_BIENVENIDA - 30


def test_cada_servidor_lleva_su_monedero():
    """Como las criaturas y el ranking: lo de un servidor no se mezcla."""
    db.cobrar("u1", "g1", 40)
    assert db.gemas("u1", "g1") != db.gemas("u1", "otro")


def test_no_se_puede_gastar_lo_que_no_hay():
    import objetos as obj

    assert not db.cobrar("u1", "g1", obj.GEMAS_DE_BIENVENIDA + 1)
    assert db.gemas("u1", "g1") == obj.GEMAS_DE_BIENVENIDA, "no debe descontar nada"

    assert db.cobrar("u1", "g1", obj.GEMAS_DE_BIENVENIDA)
    assert db.gemas("u1", "g1") == 0


def test_comprar_descuenta_y_entrega():
    import objetos as obj

    pocion = obj.CATALOGO["fuerza_1d8"]
    antes = db.gemas("u1", "g1")

    assert db.comprar("u1", "g1", pocion)
    assert db.gemas("u1", "g1") == antes - pocion.precio
    assert db.inventario("u1", "g1") == {pocion.clave: 1}

    db.comprar("u1", "g1", pocion)
    assert db.inventario("u1", "g1") == {pocion.clave: 2}


def test_si_no_llega_el_dinero_no_se_compra_ni_se_descuenta():
    import objetos as obj

    caro = obj.CATALOGO["fuerza_1d12"]
    db.cobrar("u1", "g1", db.gemas("u1", "g1"))  # a cero

    assert not db.comprar("u1", "g1", caro)
    assert db.gemas("u1", "g1") == 0
    assert db.inventario("u1", "g1") == {}


def test_usar_gasta_una_unidad_y_solo_una():
    import objetos as obj

    pocion = obj.CATALOGO["pocion_comida"]
    db.comprar("u1", "g1", pocion)
    db.comprar("u1", "g1", pocion)

    assert db.gastar("u1", "g1", pocion.clave)
    assert db.inventario("u1", "g1") == {pocion.clave: 1}

    assert db.gastar("u1", "g1", pocion.clave)
    assert db.inventario("u1", "g1") == {}, "al llegar a cero desaparece"

    assert not db.gastar("u1", "g1", pocion.clave), "no se puede usar lo que no hay"


def test_las_gemas_y_los_objetos_sobreviven_a_la_criatura():
    """Son de la persona, no de la criatura: al morir una y nacer otra sigues
    teniendo lo que compraste."""
    import objetos as obj

    nacer(usuario="u1", nombre="Primera")
    db.comprar("u1", "g1", obj.CATALOGO["silbato"])
    saldo = db.gemas("u1", "g1")

    muerta = sim.avanzar(db.criatura_viva("u1", "g1"), T0 + timedelta(days=10))
    db.guardar(muerta)
    assert db.criatura_viva("u1", "g1") is None

    db.crear("u1", "g1", "pulpo", "Segunda", STATS, T0 + timedelta(days=10))
    assert db.gemas("u1", "g1") == saldo
    assert db.inventario("u1", "g1") == {"silbato": 1}


def test_una_pocion_sustituye_a_la_anterior():
    """El invariante que sostiene el equilibrio: si se acumularan, cinco
    pociones de 1d12 serían +60 y el dado de 20 caras dejaría de mandar."""
    criatura = nacer()

    db.poner_efecto(criatura.id, "fuerza", 5, T0)
    db.poner_efecto(criatura.id, "fuerza", 11, T0)

    assert db.efecto_activo(criatura.id, "fuerza", T0) == 11
    with db.conectar() as con:
        filas = con.execute(
            "SELECT * FROM efectos WHERE criatura_id = ?", (criatura.id,)
        ).fetchall()
    assert len(filas) == 1


def test_fuerza_y_velocidad_corren_por_separado():
    criatura = nacer()
    db.poner_efecto(criatura.id, "fuerza", 5, T0)
    db.poner_efecto(criatura.id, "velocidad", 9, T0)

    assert db.efecto_activo(criatura.id, "fuerza", T0) == 5
    assert db.efecto_activo(criatura.id, "velocidad", T0) == 9


def test_un_efecto_caducado_no_se_aplica():
    import objetos as obj

    criatura = nacer()
    db.poner_efecto(criatura.id, "fuerza", 7, T0)
    dura = timedelta(minutes=obj.MINUTOS_DE_EFECTO)

    assert db.efecto_activo(criatura.id, "fuerza", T0 + dura - timedelta(seconds=1)) == 7
    assert db.efecto_activo(criatura.id, "fuerza", T0 + dura) == 0
    assert db.efecto_activo(criatura.id, "fuerza", T0 + timedelta(hours=1)) == 0


def test_sin_pocion_el_bonus_es_cero():
    criatura = nacer()
    assert db.efecto_activo(criatura.id, "fuerza", T0) == 0


def test_reiniciar_borra_el_enfriamiento():
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.ENTRENAR, T0)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0).total_seconds() > 0

    db.quitar_cooldown(criatura.id, sim.ENTRENAR)
    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)


def test_reiniciar_uno_no_toca_los_demas():
    criatura = nacer()
    for accion in (sim.ENTRENAR, sim.COMPETIR, sim.ALIMENTAR):
        db.poner_cooldown(criatura.id, accion, T0)

    db.quitar_cooldown(criatura.id, sim.ENTRENAR)

    assert db.espera_de(criatura.id, sim.ENTRENAR, T0) == timedelta(0)
    assert db.espera_de(criatura.id, sim.COMPETIR, T0).total_seconds() > 0
    assert db.espera_de(criatura.id, sim.ALIMENTAR, T0).total_seconds() > 0
