"""Persistencia: ida y vuelta, el plantel con su incubadora y muere_en."""
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import pantalla
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
COLUMNAS_INGENIO = (
    "base_ingenio", "ent_ingenio", "niv_ingenio", "ten_ingenio",
)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1", guild="g1", especie="pulpo", nombre="Prueba", ahora=T0):
    return db.crear(usuario, guild, especie, nombre, STATS, ahora)


def test_crear_y_recuperar():
    creada = nacer()
    recuperada = db.criatura_activa("u1", "g1")

    assert recuperada is not None
    assert recuperada.id == creada.id
    assert recuperada.nombre == "Prueba"
    assert recuperada.especie == "pulpo"
    assert (
        recuperada.base_fuerza,
        recuperada.base_velocidad,
        recuperada.base_salud,
        recuperada.base_ingenio,
    ) == STATS
    assert recuperada.nacida_en == T0


def test_crear_persiste_el_ingenio_del_nacimiento():
    creada = db.crear("u1", "g1", "pulpo", "Prueba", (10, 11, 12, 13), T0)
    recuperada = db.por_id(creada.id)

    assert recuperada is not None
    assert recuperada.base_ingenio == 13
    assert recuperada.ingenio == 13
    assert all(campo in db.CAMPOS for campo in COLUMNAS_INGENIO)


def test_crear_deja_siempre_una_sola_activa():
    """Lo impone el índice único de SQLite, no el código: dos `/huevo` a la vez
    no pueden dejar dos criaturas recibiendo los comandos.

    Antes el índice prohibía una segunda criatura *viva*; desde el plantel de
    tres prohíbe una segunda *activa*, que es lo que de verdad no puede pasar."""
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
    assert db.criatura_activa("u1", "g1").nombre == "Segunda"


def test_dos_personas_distintas_no_se_estorban():
    nacer(usuario="u1")
    nacer(usuario="u2", nombre="Suya")
    assert db.criatura_activa("u1", "g1").nombre == "Prueba"
    assert db.criatura_activa("u2", "g1").nombre == "Suya"


def test_la_misma_persona_puede_tener_una_por_servidor():
    nacer(guild="g1")
    nacer(guild="g2", nombre="Otra")
    assert db.criatura_activa("u1", "g1").nombre == "Prueba"
    assert db.criatura_activa("u1", "g2").nombre == "Otra"


def test_guardar_conserva_todos_los_campos():
    criatura = nacer()
    from dataclasses import replace
    modificada = replace(
        criatura,
        hambre=42.5, animo=17.25, limpieza=3.0,
        ent_fuerza=9, ent_velocidad=4, ent_salud=1, ent_ingenio=6,
        niv_fuerza=2, niv_velocidad=1, niv_salud=0, niv_ingenio=3,
        ten_ingenio=2.5,
        xp=7, nivel=4, victorias=6, derrotas=3,
        actualizada_en=T0 + timedelta(hours=5),
        pantalla_msg_id="123456789",
    )
    db.guardar(modificada)

    assert db.criatura_activa("u1", "g1") == modificada


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

    assert sim.momento_de_muerte(db.criatura_activa("u1", "g1")) > antes


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
        db.criatura_activa("u1", "g1"), sim.ALIMENTAR, momento
    ).criatura
    db.guardar(llena)

    assert db.pendientes_de_aviso(momento + timedelta(minutes=2)) == []
    guardada = db.criatura_activa("u1", "g1")
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

    recuperada = db.criatura_activa("u1", "g1")
    assert recuperada is not None
    assert recuperada.nombre == "Veterana"
    assert not recuperada.avisada
    # Y el aviso vuelve a estar programado.
    assert db.pendientes_de_aviso(sim.momento_de_aviso(criatura) + timedelta(minutes=1))


def _simular_esquema_sin_ingenio():
    with db.conectar() as con:
        for columna in COLUMNAS_INGENIO:
            con.execute(f"ALTER TABLE criaturas DROP COLUMN {columna}")


def test_la_migracion_rellena_ingenio_por_rareza():
    pulpo = db.crear("u1", "g1", "pulpo", "Pulpo", STATS, T0)
    dragon = db.crear(
        "u1", "g1", "dragoncito", "Dragón", STATS, T0, activa=False
    )
    _simular_esquema_sin_ingenio()

    db.inicializar()

    pulpo_recuperado = db.por_id(pulpo.id)
    dragon_recuperado = db.por_id(dragon.id)
    assert pulpo_recuperado is not None and dragon_recuperado is not None
    assert pulpo_recuperado.base_ingenio == 15
    assert dragon_recuperado.base_ingenio == 17
    assert (
        pulpo_recuperado.ent_ingenio,
        pulpo_recuperado.niv_ingenio,
        pulpo_recuperado.ten_ingenio,
    ) == (0, 0, 0.0)


def test_el_backfill_de_ingenio_es_idempotente():
    db.crear("u1", "g1", "pulpo", "Veterana", STATS, T0)
    _simular_esquema_sin_ingenio()
    db.inicializar()
    with db.conectar() as con:
        antes = "\n".join(con.iterdump())

    db.inicializar()

    with db.conectar() as con:
        despues = "\n".join(con.iterdump())
    assert despues == antes


def test_una_especie_desconocida_recibe_15_neutro_sin_reventar(caplog):
    criatura = db.crear("u1", "g1", "pulpo", "Fósil", STATS, T0)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET especie = 'fosil_retirado' WHERE id = ?",
            (criatura.id,),
        )
    _simular_esquema_sin_ingenio()

    caplog.set_level("WARNING", logger="db")
    db.inicializar()

    recuperada = db.por_id(criatura.id)
    assert recuperada is not None and recuperada.base_ingenio == 15
    mensajes = [registro.getMessage() for registro in caplog.records]
    assert mensajes == ["1 criaturas de especie desconocida reciben ingenio 15"]
    assert "fosil_retirado" not in mensajes[0]


def test_ninguna_criatura_queda_con_ingenio_cero_tras_inicializar():
    conocida = db.crear("u1", "g1", "pulpo", "Conocida", STATS, T0)
    desconocida = db.crear(
        "u1", "g1", "pulpo", "Desconocida", STATS, T0, activa=False
    )
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET especie = 'fosil_retirado' WHERE id = ?",
            (desconocida.id,),
        )
    _simular_esquema_sin_ingenio()

    db.inicializar()

    with db.conectar() as con:
        ceros = con.execute(
            "SELECT COUNT(*) c FROM criaturas WHERE base_ingenio = 0"
        ).fetchone()["c"]
    assert conocida.id != desconocida.id
    assert ceros == 0


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


def test_esperas_admite_acciones_explicitas_en_orden():
    criatura = nacer()
    acciones = (*sim.ACCIONES_DE_CUIDADO, sim.COMPETIR, sim.AVENTURA)
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    db.poner_cooldown(criatura.id, sim.AVENTURA, T0)

    esperas = db.esperas(criatura.id, T0, acciones)

    assert tuple(esperas) == acciones
    assert esperas[sim.ALIMENTAR] == timedelta(0)
    assert esperas[sim.COMPETIR] == timedelta(minutes=10)
    assert esperas[sim.AVENTURA] == timedelta(minutes=37)


def test_la_criatura_recuerda_su_canal():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="555")
    assert db.criatura_activa("u1", "g1").canal_id == "555"


def test_publicar_en_otro_canal_mueve_los_avisos():
    """Con el bot en varios canales, los avisos siguen a la persona: se guarda
    el canal donde se atendió por última vez."""
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="111")

    db.guardar_pantalla(criatura.id, "msg1", "222")
    movida = db.criatura_activa("u1", "g1")
    assert movida.canal_id == "222"
    assert movida.pantalla_msg_id == "msg1"


def test_guardar_pantalla_sin_canal_no_borra_el_que_habia():
    criatura = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, canal_id="111")
    db.guardar_pantalla(criatura.id, "msg1")
    assert db.criatura_activa("u1", "g1").canal_id == "111"


def test_el_genero_y_el_caracter_van_y_vuelven():
    db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0,
             genero=esp.HEMBRA, caracter="gruñón")
    recuperada = db.criatura_activa("u1", "g1")
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
        recuperada = db.criatura_activa(f"u{i}", "g1")
        assert recuperada.nombre == f"Veterana{i}", "se ha perdido una criatura"
        assert recuperada.genero == esp.MACHO
        assert recuperada.caracter in per.CARACTERES
        caracteres.append(recuperada.caracter)

    # Lo que un DEFAULT en el ALTER TABLE no podría dar: variedad.
    assert len(set(caracteres)) > 1, caracteres


def test_la_migracion_no_le_cambia_el_caracter_a_quien_ya_lo_tiene():
    db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0, caracter="perezoso")
    db.inicializar()
    assert db.criatura_activa("u1", "g1").caracter == "perezoso"


def test_migracion_añade_canal_id_sin_perder_criaturas():
    criatura = nacer(nombre="Veterana")

    with db.conectar() as con:
        con.execute("ALTER TABLE criaturas DROP COLUMN canal_id")
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(criaturas)")}
    assert "canal_id" not in columnas

    db.inicializar()

    recuperada = db.criatura_activa("u1", "g1")
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

def test_el_monedero_dual_nace_50_50_y_es_idempotente():
    import economia

    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)
    assert economia.saldos("u1", "g1") == economia.Saldos(50, 50)


def test_cada_servidor_lleva_su_monedero():
    import economia
    import objetos as obj

    economia.comprar("compra-g1", "u1", "g1", obj.CATALOGO["fuerza_1d12"])
    assert economia.saldos("u1", "g1") != economia.saldos("u1", "otro")


def test_comprar_descuenta_y_entrega():
    import economia
    import objetos as obj

    pocion = obj.CATALOGO["fuerza_1d8"]
    assert economia.comprar("compra-1", "u1", "g1", pocion)
    assert economia.saldos("u1", "g1").asciicoins == 50 - pocion.precio
    assert db.inventario("u1", "g1") == {pocion.clave: 1}

    economia.comprar("compra-2", "u1", "g1", pocion)
    assert db.inventario("u1", "g1") == {pocion.clave: 2}


def test_si_no_llega_el_dinero_no_se_compra_ni_se_descuenta():
    import economia
    import objetos as obj

    cara = obj.CATALOGO["fuerza_1d12"]
    assert economia.comprar("compra-1", "u1", "g1", cara)
    rechazada = economia.comprar("compra-2", "u1", "g1", cara)
    assert not rechazada
    assert economia.saldos("u1", "g1").asciicoins == 50 - cara.precio
    assert db.inventario("u1", "g1") == {cara.clave: 1}


def test_usar_gasta_una_unidad_y_solo_una():
    import economia
    import objetos as obj

    pocion = obj.CATALOGO["pocion_comida"]
    economia.comprar("compra-1", "u1", "g1", pocion)
    economia.comprar("compra-2", "u1", "g1", pocion)

    assert db.gastar("u1", "g1", pocion.clave)
    assert db.inventario("u1", "g1") == {pocion.clave: 1}
    assert db.gastar("u1", "g1", pocion.clave)
    assert db.inventario("u1", "g1") == {}
    assert not db.gastar("u1", "g1", pocion.clave)


def test_el_monedero_y_los_objetos_sobreviven_a_la_criatura():
    import economia
    import objetos as obj

    nacer(usuario="u1", nombre="Primera")
    economia.comprar("compra-1", "u1", "g1", obj.CATALOGO["silbato"])
    saldo = economia.saldos("u1", "g1")

    muerta = sim.avanzar(db.criatura_activa("u1", "g1"), T0 + timedelta(days=10))
    db.guardar(muerta)
    db.crear("u1", "g1", "pulpo", "Segunda", STATS, T0 + timedelta(days=10))
    assert economia.saldos("u1", "g1") == saldo
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


# --- El plantel y la incubadora --------------------------------------------

def incubar(criatura, **cambios):
    """Deja una criatura en la incubadora sin pasar por `activar`, para montar
    el escenario sin depender de la función que se quiere probar."""
    db.guardar(replace(criatura, activa=False, **cambios))
    return db.por_id(criatura.id)


def colar_dormida(nombre="Dormida"):
    """Una segunda criatura incubada, insertada a pelo: `crear` la haría activa
    y el índice único lo impediría."""
    with db.conectar() as con:
        con.execute(
            "INSERT INTO criaturas (usuario_id, guild_id, especie, nombre, "
            "nacida_en, actualizada_en, base_fuerza, base_velocidad, "
            "base_salud, activa) VALUES ('u1','g1','pulpo',?,?,?,10,10,10,0)",
            (nombre, T0.isoformat(), T0.isoformat()),
        )
        return con.execute(
            "SELECT id FROM criaturas WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]


def test_a_la_incubadora_no_le_pasa_el_tiempo():
    """Es lo que hace viable tener tres: si decayeran todas, dos se morirían de
    hambre hiciera lo que hiciera su dueño."""
    dormida = incubar(nacer(), hambre=40.0)
    assert not dormida.activa

    tres_dias = sim.avanzar(dormida, T0 + timedelta(days=3))
    assert tres_dias.hambre == dormida.hambre
    assert tres_dias.animo == dormida.animo
    assert tres_dias.limpieza == dormida.limpieza
    assert tres_dias.viva


def test_una_incubada_no_entra_en_el_bucle_que_mata():
    """El bucle busca `muere_en <= ahora`; dejando ese campo a NULL para las
    incubadas quedan invisibles sin tocar la consulta."""
    incubar(nacer(), hambre=1.0)

    with db.conectar() as con:
        fila = con.execute("SELECT muere_en, avisa_en FROM criaturas").fetchone()
    assert fila["muere_en"] is None
    assert fila["avisa_en"] is None

    muy_tarde = T0 + timedelta(days=30)
    assert db.pendientes_de_morir(muy_tarde) == []
    assert db.pendientes_de_aviso(muy_tarde) == []


def test_la_activa_si_sigue_muriendo():
    """El contraste: la incubadora no puede haber apagado el bucle entero."""
    db.guardar(replace(nacer(), hambre=1.0))
    assert db.pendientes_de_morir(T0 + timedelta(days=30))


def test_al_sacarla_de_la_incubadora_no_se_le_cae_el_tiempo_encima():
    """El detalle fino: si `actualizada_en` no se pusiera al día al activarla,
    las horas de la incubadora se aplicarían de golpe y saldría muerta."""
    dormida = incubar(nacer(), hambre=50.0)
    tres_dias = T0 + timedelta(days=3)

    assert db.activar(dormida.id, "u1", "g1", tres_dias)
    despierta = db.criatura_activa("u1", "g1")

    assert despierta.activa
    assert despierta.hambre == 50.0
    assert despierta.actualizada_en == tres_dias
    # Y a partir de ahí vuelve a correrle el tiempo con normalidad.
    assert sim.avanzar(despierta, tres_dias + timedelta(hours=10)).hambre < 50.0


def test_el_tope_del_plantel_lo_pone_la_constante():
    """Sin el número escrito a mano: antes decía «tres pero no cuatro» y al
    subir el tope habría habido que reescribirlo, que es justo cuando un test
    con el número dentro se queda mintiendo."""
    incubar(nacer(nombre="C0"))
    for i in range(1, db.MAXIMO_PLANTEL):
        colar_dormida(f"C{i}")
    assert len(db.plantel("u1", "g1")) == db.MAXIMO_PLANTEL

    with pytest.raises(ValueError):
        db.crear("u1", "g1", "pulpo", "ElQueSobra", STATS, T0)
    assert len(db.plantel("u1", "g1")) == db.MAXIMO_PLANTEL


def test_el_tope_es_por_persona_y_por_servidor():
    """Llenar el plantel en un servidor no te deja sin sitio en el otro, ni le
    quita hueco a nadie más."""
    incubar(nacer(nombre="C0"))
    for i in range(1, db.MAXIMO_PLANTEL):
        colar_dormida(f"C{i}")

    assert db.crear("u1", "g2", "pulpo", "EnOtroServidor", STATS, T0)
    assert db.crear("u2", "g1", "pulpo", "DeOtraPersona", STATS, T0)


def test_solo_una_activa_a_la_vez_lo_impide_el_indice():
    """Como antes con `una_viva`: lo garantiza la base de datos y no el código,
    así que dos clics simultáneos no pueden dejar dos activas."""
    nacer()
    with db.conectar() as con:
        try:
            con.execute(
                "INSERT INTO criaturas (usuario_id, guild_id, especie, nombre, "
                "nacida_en, actualizada_en, base_fuerza, base_velocidad, "
                "base_salud, activa) VALUES "
                "('u1','g1','pulpo','Intrusa',?,?,10,10,10,1)",
                (T0.isoformat(), T0.isoformat()),
            )
        except sqlite3.IntegrityError:
            return
    raise AssertionError("el índice debería impedir dos activas")


def test_el_plantel_pone_a_la_activa_primero():
    activa = nacer(nombre="Activa")
    colar_dormida()

    plantel = db.plantel("u1", "g1")
    assert [c.nombre for c in plantel] == ["Activa", "Dormida"]
    assert plantel[0].id == activa.id


def test_activar_apaga_a_la_anterior():
    primera = nacer(nombre="Primera")
    segunda_id = colar_dormida("Segunda")

    assert db.activar(segunda_id, "u1", "g1", T0)

    assert db.criatura_activa("u1", "g1").nombre == "Segunda"
    assert not db.por_id(primera.id).activa


def test_no_se_puede_activar_la_de_otro():
    mia = nacer(nombre="Mia")
    nacer(usuario="u2", nombre="Suya")
    ajena = db.criatura_activa("u2", "g1")

    assert not db.activar(ajena.id, "u1", "g1", T0)
    assert db.criatura_activa("u1", "g1").id == mia.id


def test_el_jardin_solo_ve_a_las_activas():
    """Las de la incubadora están dormidas y con el tiempo parado: dibujarlas
    paseando por el jardín no se sostiene."""
    nacer(nombre="Despierta")
    colar_dormida("Dormida")
    nacer(usuario="u2", nombre="DeOtro")

    nombres = [c.nombre for c in db.vivas_del_servidor("g1")]
    assert nombres == ["Despierta", "DeOtro"]


def test_al_morir_la_activa_asciende_la_siguiente():
    activa = nacer(nombre="Primera")
    colar_dormida("Segunda")

    db.guardar(sim.avanzar(activa, T0 + timedelta(days=10)))
    assert db.criatura_activa("u1", "g1") is None

    relevo = db.ascender_de_la_incubadora("u1", "g1", T0 + timedelta(days=10))

    assert relevo is not None and relevo.nombre == "Segunda"
    assert db.criatura_activa("u1", "g1").nombre == "Segunda"


def test_si_no_hay_nadie_esperando_no_asciende_nadie():
    activa = nacer()
    db.guardar(sim.avanzar(activa, T0 + timedelta(days=10)))

    assert db.ascender_de_la_incubadora("u1", "g1", T0 + timedelta(days=10)) is None


def test_no_asciende_a_nadie_si_ya_hay_activa():
    nacer(nombre="Primera")
    colar_dormida("Segunda")

    assert db.ascender_de_la_incubadora("u1", "g1", T0) is None
    assert db.criatura_activa("u1", "g1").nombre == "Primera"


# --- El recluta sin bautizar ------------------------------------------------

def test_un_recluta_sin_nombre_no_sale_de_la_incubadora():
    """Lo pedido: no entra al equipo hasta que le pongas nombre.

    La comprobación vive en `activar` y no en el menú porque es un invariante
    del plantel: por ahí pasan el cambio manual y el relevo por muerte."""
    nacer(nombre="Primera")
    recluta = colar_dormida(sim.NOMBRE_PENDIENTE)

    assert not db.activar(recluta, "u1", "g1", T0)
    assert db.criatura_activa("u1", "g1").nombre == "Primera"


def test_al_ponerle_nombre_el_recluta_ya_puede_activarse():
    nacer(nombre="Primera")
    recluta = colar_dormida(sim.NOMBRE_PENDIENTE)

    db.guardar(replace(db.por_id(recluta), nombre="Pelusa"))

    assert db.activar(recluta, "u1", "g1", T0)
    assert db.criatura_activa("u1", "g1").nombre == "Pelusa"


def test_al_morir_la_activa_no_asciende_un_recluta_sin_nombre():
    """Ascenderlo dejaría el plantel sin ninguna activa, porque `activar` lo
    rechaza: se prefiere a quien sí tiene nombre y, si no hay, no se asciende."""
    activa = nacer(nombre="Primera")
    colar_dormida(sim.NOMBRE_PENDIENTE)
    con_nombre = colar_dormida("Tercera")

    db.guardar(sim.avanzar(activa, T0 + timedelta(days=10)))
    relevo = db.ascender_de_la_incubadora("u1", "g1", T0 + timedelta(days=10))

    assert relevo is not None and relevo.id == con_nombre
    assert relevo.nombre == "Tercera"


# --- La espera de aventura es de la persona ---------------------------------

def test_la_espera_de_aventura_es_de_la_persona_no_del_gachamon():
    """El bug: con tres gachamones se salía tres veces seguidas cambiando de
    activo entre viaje y viaje. A la aventura vas tú, así que la espera es
    tuya."""
    primero = nacer(nombre="Primero")
    segundo_id = colar_dormida("Segundo")

    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)

    assert db.espera_de_persona("u1", "g1", sim.AVENTURA, T0) == sim.COOLDOWNS[sim.AVENTURA]
    # Y el gachamon que no salió tampoco puede: la espera no es suya, es tuya.
    for criatura_id in (primero.id, segundo_id):
        assert db.espera_de(criatura_id, sim.AVENTURA, T0) == timedelta(0)


def test_la_espera_de_aventura_se_acaba_a_su_hora():
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)
    despues = T0 + sim.COOLDOWNS[sim.AVENTURA]

    assert db.espera_de_persona("u1", "g1", sim.AVENTURA, despues) == timedelta(0)


def test_la_espera_de_aventura_no_pasa_de_una_persona_a_otra():
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)

    assert db.espera_de_persona("u2", "g1", sim.AVENTURA, T0) == timedelta(0)


def test_la_espera_de_aventura_no_pasa_de_un_servidor_a_otro():
    """Todo estado de una persona está aislado por persona + servidor, y la
    tabla nueva no puede ser la excepción."""
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)

    assert db.espera_de_persona("u1", "g2", sim.AVENTURA, T0) == timedelta(0)


def test_poner_la_espera_de_aventura_dos_veces_reemplaza():
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0 + timedelta(minutes=10))

    espera = db.espera_de_persona(
        "u1", "g1", sim.AVENTURA, T0 + timedelta(minutes=10)
    )
    assert espera == sim.COOLDOWNS[sim.AVENTURA]


def test_competir_sigue_siendo_del_gachamon():
    """Lo que NO cambia, escrito para que nadie lo mueva por descuido: en un
    sumo pelea él y es él quien queda cansado."""
    primero = nacer(nombre="Primero")
    segundo_id = colar_dormida("Segundo")

    db.poner_cooldown(primero.id, sim.COMPETIR, T0)

    assert db.espera_de(primero.id, sim.COMPETIR, T0) == sim.COOLDOWNS[sim.COMPETIR]
    assert db.espera_de(segundo_id, sim.COMPETIR, T0) == timedelta(0)


def test_la_ficha_junta_lo_del_gachamon_con_lo_de_la_persona():
    """La ficha enseña las dos clases de espera, y cada una vive en su tabla."""
    criatura = nacer()
    db.poner_cooldown(criatura.id, sim.COMPETIR, T0)
    db.poner_cooldown_persona("u1", "g1", sim.AVENTURA, T0)

    esperas = db.esperas_de_ficha(criatura, T0, pantalla.ACCIONES_EN_FICHA)

    assert esperas[sim.COMPETIR] == sim.COOLDOWNS[sim.COMPETIR]
    assert esperas[sim.AVENTURA] == sim.COOLDOWNS[sim.AVENTURA]
    assert esperas[sim.ALIMENTAR] == timedelta(0)


def test_la_migracion_conserva_la_espera_de_aventura_en_curso():
    """Sin esto, quien estuviera esperando al desplegar se llevaría una
    aventura gratis."""
    criatura = nacer()
    hasta = T0 + timedelta(minutes=20)
    with db.conectar() as con:
        con.execute(
            "INSERT INTO cooldowns (criatura_id, accion, hasta) VALUES (?, ?, ?)",
            (criatura.id, sim.AVENTURA, hasta.isoformat()),
        )

    db.inicializar()  # vuelve a migrar, como al arrancar tras el despliegue

    assert db.espera_de_persona("u1", "g1", sim.AVENTURA, T0) == timedelta(minutes=20)
    with db.conectar() as con:
        viejas = con.execute(
            "SELECT COUNT(*) c FROM cooldowns WHERE accion = ?", (sim.AVENTURA,)
        ).fetchone()["c"]
    assert viejas == 0, "la fila vieja se queda ahí engañando"
