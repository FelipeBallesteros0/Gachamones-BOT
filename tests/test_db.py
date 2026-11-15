"""Persistencia: ida y vuelta, el plantel con su incubadora y la base sin relojes de muerte."""
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import db
import especies as esp
import nombres
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)
U = "u1"
G = "g1"
COLUMNAS_INGENIO = (
    "base_ingenio", "ent_ingenio", "niv_ingenio", "ten_ingenio",
)


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "prueba.db")
    db.inicializar()


def nacer(usuario="u1", guild="g1", especie="pulpo", nombre="Prueba", ahora=T0):
    return db.crear(usuario, guild, especie, nombre, STATS, ahora)


def muerta_de_antes(criatura, cuando=T0 + timedelta(days=10)):
    """Una que murió cuando todavía se moría de hambre: sigue muerta."""
    return replace(criatura, hambre=0.0, muerta_en=cuando, causa_muerte="hambre")


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


def test_por_id_de_uno_que_no_existe_es_nada():
    creada = db.crear("u1", "g1", "pulpo", "Prueba", STATS, T0)

    assert db.por_id(creada.id + 1) is None
    assert db.por_id(creada.id) == creada


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


# --- Sin relojes de muerte --------------------------------------------------

def crear_activa(hambre):
    criatura = nacer()
    db.guardar(replace(criatura, hambre=hambre))
    return db.por_id(criatura.id)


def poner_en_la_fila(criatura_id, **columnas):
    """Escribe columnas a pelo, como las dejó el código de antes."""
    asignaciones = ", ".join(f"{c} = ?" for c in columnas)
    with db.conectar() as con:
        con.execute(
            f"UPDATE criaturas SET {asignaciones} WHERE id = ?",
            (*columnas.values(), criatura_id),
        )


def leer_fila(criatura_id):
    with db.conectar() as con:
        return con.execute(
            "SELECT * FROM criaturas WHERE id = ?", (criatura_id,)
        ).fetchone()


def tablas():
    with db.conectar() as con:
        return {f["name"] for f in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}


def indices():
    with db.conectar() as con:
        return {f["name"] for f in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'")}


def crear_la_tabla_vieja_con_una_fila():
    """La tabla de las muertes por anunciar como la dejaba el código de antes,
    con una muerte que el bot todavía no había anunciado."""
    muerta = nacer(nombre="Pendiente")
    db.guardar(muerta_de_antes(muerta))
    with db.conectar() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS muertes_por_anunciar "
            "(criatura_id INTEGER PRIMARY KEY, relevo_id INTEGER)"
        )
        con.execute(
            "INSERT INTO muertes_por_anunciar (criatura_id) VALUES (?)",
            (muerta.id,),
        )
    return muerta


def volcado():
    """La base entera, tabla por tabla: cualquier escritura la cambia."""
    with db.conectar() as con:
        return list(con.iterdump())


def test_a_quien_le_tocaba_morir_sigue_vivo_y_sin_reloj():
    c = crear_activa(hambre=2.0)
    poner_en_la_fila(
        c.id,
        muere_en=(T0 - timedelta(days=1)).isoformat(),
        avisa_en=(T0 - timedelta(days=2)).isoformat(),
        avisada=1,
    )
    db.inicializar()
    fila = leer_fila(c.id)
    assert fila["muere_en"] is None and fila["avisa_en"] is None and fila["muerta_en"] is None
    assert fila["avisada"] == 0
    al_dia = db.activa_al_dia(U, G, T0 + timedelta(days=3))
    assert al_dia.viva and al_dia.hambre == 0.0


def test_guardar_no_escribe_relojes():
    c = crear_activa(hambre=80.0)
    # Aunque llegue marcada como avisada: la marca ya no se guarda.
    db.guardar(replace(c, avisada=True))
    fila = leer_fila(c.id)
    assert (fila["muere_en"], fila["avisa_en"], fila["avisada"]) == (None, None, 0)


def test_la_tabla_de_muertes_por_anunciar_se_va_y_arrancar_dos_veces_no_falla():
    muerta = crear_la_tabla_vieja_con_una_fila()
    db.inicializar()
    db.inicializar()
    assert "muertes_por_anunciar" not in tablas()
    # Se va sin anunciar nada: la muerta de antes sigue muerta y no hay relevo.
    assert db.por_id(muerta.id).muerta_en is not None
    assert db.criatura_activa(U, G) is None


def test_los_indices_de_los_relojes_se_van_y_no_vuelven():
    with db.conectar() as con:
        con.execute("CREATE INDEX IF NOT EXISTS idx_muere "
                    "ON criaturas(muere_en) WHERE muerta_en IS NULL")
        con.execute("CREATE INDEX IF NOT EXISTS idx_avisa "
                    "ON criaturas(avisa_en) WHERE muerta_en IS NULL AND avisada = 0")
    db.inicializar()
    db.inicializar()
    assert not {"idx_muere", "idx_avisa"} & indices()


def test_una_base_nueva_nace_sin_relojes_ni_tabla_de_muertes():
    assert "muertes_por_anunciar" not in tablas()
    assert not {"idx_muere", "idx_avisa"} & indices()


def test_activa_al_dia_no_escribe():
    crear_activa(hambre=0.0)
    antes = volcado()
    db.activa_al_dia(U, G, T0 + timedelta(days=10))
    assert volcado() == antes


# --- El tiempo para todos -----------------------------------------------------

def borrar_la_marca(clave):
    with db.conectar() as con:
        con.execute("DELETE FROM cambios_hechos WHERE clave = ?", (clave,))


def test_el_dia_del_cambio_el_reloj_de_las_que_dormian_parte_de_ahi():
    activa = nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    cambio = T0 + timedelta(days=40)
    db.inicializar(cambio)
    assert db.por_id(dormida.id).actualizada_en == cambio
    assert db.por_id(activa.id).actualizada_en == T0
    assert db.avanzar(db.por_id(dormida.id), cambio + timedelta(hours=1)).hambre > 95.0


def test_el_reloj_de_las_que_dormian_se_pone_una_sola_vez():
    nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    cambio = T0 + timedelta(days=40)
    db.inicializar(cambio)
    db.inicializar(cambio + timedelta(days=3))
    assert db.por_id(dormida.id).actualizada_en == cambio


def test_dos_arranques_a_la_vez_ponen_el_reloj_una_vez():
    nacer(nombre="Ana")
    dormida = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    momentos = [T0 + timedelta(days=40), T0 + timedelta(days=41)]
    with ThreadPoolExecutor(max_workers=2) as hilos:
        list(hilos.map(db.inicializar, momentos))
    with db.conectar() as con:
        marca = con.execute("SELECT hecho_en FROM cambios_hechos WHERE clave = 'el_tiempo_para_todos'").fetchone()[0]
    assert db.por_id(dormida.id).actualizada_en.isoformat() == marca


def test_el_dia_del_cambio_una_muerta_de_antes_no_cambia():
    activa = nacer(nombre="Ana")
    finada = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    db.guardar(muerta_de_antes(finada))
    antes = db.por_id(finada.id)
    borrar_la_marca("el_tiempo_para_todos")
    db.inicializar(T0 + timedelta(days=40))
    assert db.por_id(finada.id) == antes
    assert db.por_id(finada.id).actualizada_en == T0
    assert db.por_id(activa.id).actualizada_en == T0


def test_el_plantel_al_dia_avanza_a_cada_uno_y_no_escribe():
    nacer(nombre="Ana")
    otra = db.crear(U, G, "pulpo", "Bea", STATS, T0, activa=False)
    antes = volcado()
    al_dia = db.plantel_al_dia(U, G, T0 + timedelta(hours=10))
    assert [c.nombre for c in al_dia] == ["Ana", "Bea"]
    assert all(c.hambre < 100.0 for c in al_dia) and volcado() == antes


def test_migracion_de_una_base_de_datos_antigua():
    """Una BD de la versión anterior no tiene avisa_en ni avisada: al abrirla
    hay que añadir las columnas sin perder las criaturas."""
    criatura = nacer(nombre="Veterana")

    with db.conectar() as con:
        # El índice viejo referenciaba las columnas: hay que quitarlo primero.
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
    # Las columnas vuelven, pero vacías: ya no se programa ningún aviso.
    fila = leer_fila(criatura.id)
    assert (fila["avisa_en"], fila["avisada"]) == (None, 0)


def test_una_base_sin_difuntos_vistos_hasta_la_gana_al_inicializar():
    db.inicializar()
    db.crear_identidad_web(1, "g1", datetime(2026, 1, 1, tzinfo=timezone.utc))
    with db.conectar() as con:
        con.execute("ALTER TABLE cuentas_web DROP COLUMN difuntos_vistos_hasta")
        assert "difuntos_vistos_hasta" not in db._columnas(con, "cuentas_web")

    db.inicializar()

    with db.conectar() as con:
        assert "difuntos_vistos_hasta" in db._columnas(con, "cuentas_web")
    assert db.cuenta_web(1) is not None


def test_la_base_ya_no_lleva_la_cuenta_de_los_difuntos_vistos():
    """La columna se queda en el esquema, pero ya nadie la lee ni la escribe."""
    db.crear_identidad_web(1, "g1", T0)
    codigo = db.pedir_codigo_de_vinculo(1, T0)
    # Vincular una cuenta que ya existía no apunta nada en ella.
    assert db.canjear_codigo_de_vinculo(codigo, "111111111111111111", "g1", T0) == "ok"
    with db.conectar() as con:
        fila = con.execute(
            "SELECT difuntos_vistos_hasta FROM cuentas_web WHERE rowino_uid = 1"
        ).fetchone()
    assert fila[0] is None
    assert db.cuenta_web(1).vinculada


def test_una_base_sin_lugar_la_gana_al_inicializar():
    db.inicializar()
    db.crear_identidad_web(1, "g1", datetime(2026, 1, 1, tzinfo=timezone.utc))
    with db.conectar() as con:
        con.execute("ALTER TABLE cuentas_web DROP COLUMN lugar")
        assert "lugar" not in db._columnas(con, "cuentas_web")

    db.inicializar()

    with db.conectar() as con:
        assert "lugar" in db._columnas(con, "cuentas_web")
    assert db.cuenta_web(1) is not None
    assert db.lugar_de_cuenta(1) is None


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
    # Sin canal guardado: la pantalla vieja se busca donde se publica la nueva.
    assert recuperada.canal_id is None



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
    db.guardar(muerta_de_antes(primera))

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


def test_el_cementerio_solo_tiene_muertas():
    viva = nacer(usuario="u1")
    db.guardar(muerta_de_antes(nacer(usuario="u2", nombre="Finada")))

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

    db.guardar(muerta_de_antes(db.criatura_activa("u1", "g1")))
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


def test_a_la_que_no_es_la_activa_tambien_le_pasa_el_tiempo():
    """Salir contigo no cambia cómo le corre el reloj: decae como la activa."""
    otra = incubar(nacer(), hambre=40.0)
    assert not otra.activa

    tres_dias = db.avanzar(otra, T0 + timedelta(days=3))
    assert tres_dias.hambre < otra.hambre
    assert tres_dias.animo < otra.animo
    assert tres_dias.limpieza < otra.limpieza
    assert tres_dias.viva and tres_dias.actualizada_en == T0 + timedelta(days=3)


def test_activar_no_le_toca_el_reloj_a_nadie():
    """Salir contigo no es despertar: `activar` sólo cambia la marca, y el
    tiempo que les pasó a las dos sigue contando desde donde estaba."""
    primera = nacer(nombre="Primera")
    segunda = db.por_id(colar_dormida("Segunda"))

    assert db.activar(segunda.id, "u1", "g1")

    sale = db.por_id(segunda.id)
    se_queda = db.por_id(primera.id)
    assert sale.activa and not se_queda.activa
    assert sale.actualizada_en == segunda.actualizada_en == T0
    assert se_queda.actualizada_en == primera.actualizada_en == T0
    assert sale.hambre == segunda.hambre
    tres_dias = T0 + timedelta(days=3)
    assert db.avanzar(sale, tres_dias).hambre == pytest.approx(
        db.avanzar(segunda, tres_dias).hambre
    )


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

    assert db.activar(segunda_id, "u1", "g1")

    assert db.criatura_activa("u1", "g1").nombre == "Segunda"
    assert not db.por_id(primera.id).activa


def test_no_se_puede_activar_la_de_otro():
    mia = nacer(nombre="Mia")
    nacer(usuario="u2", nombre="Suya")
    ajena = db.criatura_activa("u2", "g1")

    assert not db.activar(ajena.id, "u1", "g1")
    assert db.criatura_activa("u1", "g1").id == mia.id


def test_al_morir_la_activa_asciende_la_siguiente():
    activa = nacer(nombre="Primera")
    colar_dormida("Segunda")

    db.guardar(muerta_de_antes(activa))
    assert db.criatura_activa("u1", "g1") is None

    relevo = db.ascender_un_relevo("u1", "g1")

    assert relevo is not None and relevo.nombre == "Segunda"
    # Sólo cambia la marca: el tiempo le sigue corriendo desde donde estaba.
    assert relevo.actualizada_en == T0
    assert db.criatura_activa("u1", "g1").nombre == "Segunda"


def test_si_no_hay_nadie_esperando_no_asciende_nadie():
    activa = nacer()
    db.guardar(muerta_de_antes(activa))

    assert db.ascender_un_relevo("u1", "g1") is None


def test_no_asciende_a_nadie_si_ya_hay_activa():
    nacer(nombre="Primera")
    colar_dormida("Segunda")

    assert db.ascender_un_relevo("u1", "g1") is None
    assert db.criatura_activa("u1", "g1").nombre == "Primera"


# --- Nadie nace sin nombre --------------------------------------------------

def test_nadie_nace_sin_nombre():
    with pytest.raises(ValueError, match="nace con nombre"):
        db.crear(U, G, "pulpo", "", STATS, T0)
    assert db.plantel(U, G) == []


# --- Los que esperaban nombre se lo ponen solos al arrancar -----------------

def test_los_reclutas_sin_nombre_se_lo_ponen_solos_al_arrancar():
    nube = nacer(nombre="Nube")
    uno = db.crear(U, G, "michi", "Uno", STATS, T0, activa=False)
    otro = db.crear(U, G, "michi", "Otro", STATS, T0, activa=False)
    with db.conectar() as con:                           # como los dejó el bot de antes
        con.execute(
            "UPDATE criaturas SET nombre = '' WHERE id IN (?, ?)", (uno.id, otro.id)
        )

    db.inicializar()

    nombrados = [db.por_id(uno.id), db.por_id(otro.id)]
    assert all(c.nombre in nombres.NOMBRES and c.se_nombro_solo for c in nombrados)
    assert nombrados[0].nombre != nombrados[1].nombre
    assert "Nube" not in {c.nombre for c in nombrados}

    db.inicializar()

    assert [db.por_id(uno.id), db.por_id(otro.id)] == nombrados
    sigue = db.por_id(nube.id)
    assert sigue.nombre == "Nube" and sigue.se_nombro_solo is False


def test_al_arrancar_el_nombre_no_es_el_de_otro_vivo_ni_el_de_su_especie(monkeypatch):
    """Con la lista reducida a cuatro sólo quedan dos que valgan: «Nube» la
    lleva otro vivo y «Purreon» es su especie. «Miga» sí vale, porque quien la
    llevaba ya no vive, y el segundo no repite el que se acaba de poner el
    primero."""
    monkeypatch.setattr(nombres, "NOMBRES", ("Nube", "Purreon", "Miga", "Trufa"))
    db.guardar(muerta_de_antes(nacer(nombre="Miga")))
    nacer(nombre="Nube")
    uno = db.crear(U, G, "michi", "Uno", STATS, T0, activa=False)
    otro = db.crear(U, G, "michi", "Otro", STATS, T0, activa=False)
    with db.conectar() as con:
        con.execute(
            "UPDATE criaturas SET nombre = '' WHERE id IN (?, ?)", (uno.id, otro.id)
        )

    db.inicializar()

    assert {db.por_id(uno.id).nombre, db.por_id(otro.id).nombre} == {"Miga", "Trufa"}


def test_el_paso_de_los_nombres_con_un_azar_fijo_evita_lo_que_tiene_que_evitar(
    monkeypatch,
):
    """Con la semilla 2 y esta lista, lo bien hecho da «Miga» y «Trufa», y
    cualquier regresión da otra cosa siempre, no a veces: sin evitar al otro
    vivo salen «Nube» y «Nube»; sin evitar la especie, «Purreon» y «Miga»; sin
    contar el que se acaba de poner, «Miga» dos veces; y si evitara también el
    de la muerta, el primero sería «Trufa»."""
    monkeypatch.setattr(nombres, "NOMBRES", ("Nube", "Purreon", "Miga", "Trufa"))
    db.guardar(muerta_de_antes(nacer(nombre="Miga")))
    nacer(nombre="Nube")
    uno = db.crear(U, G, "michi", "Uno", STATS, T0, activa=False)
    otro = db.crear(U, G, "michi", "Otro", STATS, T0, activa=False)

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE criaturas SET nombre = '' WHERE id IN (?, ?)", (uno.id, otro.id)
        )
        db._nombrar_a_los_que_lo_esperaban(con, random.Random(2))

    assert [db.por_id(uno.id).nombre, db.por_id(otro.id).nombre] == ["Miga", "Trufa"]
    assert db.por_id(uno.id).se_nombro_solo and db.por_id(otro.id).se_nombro_solo


def test_el_unico_vivo_sin_nombre_recibe_nombre_y_pasa_a_ser_el_activo():
    db.guardar(muerta_de_antes(nacer(nombre="Ana")))
    recluta = db.crear(U, G, "pulpo", "Provisional", STATS, T0, activa=False)
    with db.conectar() as con:                           # como lo dejó el bot de antes
        con.execute("UPDATE criaturas SET nombre = '' WHERE id = ?", (recluta.id,))
    assert db.criatura_activa(U, G) is None
    db.inicializar()
    activa = db.activa_al_dia(U, G, T0 + timedelta(hours=1))
    assert activa.id == recluta.id and activa.activa and activa.nombre in nombres.NOMBRES


# --- Quien se quedó sin activo sale con uno al arrancar ---------------------

def sin_activo_como_lo_dejo_el_codigo_de_antes(usuario=U, guild=G):
    """El activo se le murió cuando todavía se moría y le quedan dos vivos que
    no salían; el primero, un recluta que todavía no tiene nombre."""
    muerta = nacer(usuario=usuario, guild=guild, nombre="Ana")
    db.guardar(muerta_de_antes(muerta))
    recluta = db.crear(usuario, guild, "pulpo", "Provisional", STATS, T0, activa=False)
    otro = db.crear(usuario, guild, "pulpo", "Bea", STATS, T0, activa=False)
    with db.conectar() as con:                           # como lo dejó el bot de antes
        con.execute("UPDATE criaturas SET nombre = '' WHERE id = ?", (recluta.id,))
    return db.por_id(muerta.id), db.por_id(recluta.id), db.por_id(otro.id)


def test_al_arrancar_quien_no_tenia_activo_sale_con_el_de_menor_id():
    muerta, recluta, otro = sin_activo_como_lo_dejo_el_codigo_de_antes()
    assert db.criatura_activa(U, G) is None
    # El índice que impide dos activas ya está puesto: el arranque corre bajo él.
    assert "una_activa" in indices()

    db.inicializar()

    activa = db.criatura_activa(U, G)
    assert activa is not None and activa.id == recluta.id < otro.id
    assert activa.nombre in nombres.NOMBRES
    assert [c.id for c in db.plantel(U, G) if c.activa] == [recluta.id]
    assert db.por_id(otro.id) == otro and not otro.activa
    assert db.por_id(muerta.id) == muerta


def test_el_ascenso_del_arranque_no_toca_a_quien_ya_tiene_activo_y_es_repetible():
    sin_activo_como_lo_dejo_el_codigo_de_antes()
    # La reserva, con menor id que su activa: un ascenso que no mirara si ya
    # hay activo la elegiría a ella, y el índice lo haría saltar.
    reserva = db.crear("u2", G, "pulpo", "Reserva", STATS, T0, activa=False)
    activa = nacer(usuario="u2", nombre="Activa")
    suyas = [db.por_id(reserva.id), db.por_id(activa.id)]

    db.inicializar()

    assert db.criatura_activa(U, G) is not None
    assert [db.por_id(reserva.id), db.por_id(activa.id)] == suyas
    antes = volcado()
    db.inicializar()
    assert volcado() == antes


def test_al_ascendido_del_arranque_no_se_le_viene_encima_lo_que_durmio():
    """El paso del reloj mira a los que no son el activo: si el ascenso fuera
    antes, al ascendido no se le movería y se le cobraría todo lo que durmió."""
    solo = db.crear(U, G, "pulpo", "Solo", STATS, T0, activa=False)
    borrar_la_marca("el_tiempo_para_todos")
    cambio = T0 + timedelta(days=40)

    db.inicializar(cambio)

    activa = db.criatura_activa(U, G)
    assert activa is not None and activa.id == solo.id
    assert activa.actualizada_en == cambio


def test_el_ascenso_del_arranque_solo_da_activo_en_el_servidor_donde_faltaba():
    reserva = db.crear(U, G, "pulpo", "Reserva", STATS, T0, activa=False)
    activa = nacer(nombre="Activa")
    suyas = [db.por_id(reserva.id), db.por_id(activa.id)]
    en_otro = [db.crear(U, "g2", "pulpo", n, STATS, T0, activa=False) for n in ("Uno", "Dos")]

    db.inicializar()

    assert [db.por_id(reserva.id), db.por_id(activa.id)] == suyas
    assert [c.id for c in db.plantel(U, "g2") if c.activa] == [en_otro[0].id]


# --- Sin activa, la activa al día saca a alguien (el remiendo) --------------

def test_sin_activa_saca_al_de_la_incubadora_que_tiene_nombre():
    espera = db.crear("u1", "g1", "pulpo", "Espera", STATS, T0, activa=False)
    assert db.activa_al_dia("u1", "g1", T0).id == espera.id
    assert db.criatura_activa("u1", "g1").id == espera.id


def test_activa_al_dia_es_repetible():
    db.guardar(muerta_de_antes(nacer(nombre="Viejo")))
    primero = colar_dormida("Uno")
    colar_dormida("Dos")
    tarde = T0 + timedelta(days=10)

    assert db.activa_al_dia("u1", "g1", tarde).id == primero
    assert db.activa_al_dia("u1", "g1", tarde).id == primero
    activas = [c for c in db.plantel("u1", "g1") if c.activa]
    assert [c.id for c in activas] == [primero]


def test_dos_a_la_vez_sacan_un_solo_relevo():
    db.guardar(muerta_de_antes(nacer(nombre="Viejo")))
    relevo = colar_dormida("Tinta")
    tarde = T0 + timedelta(days=10)

    with ThreadPoolExecutor(max_workers=2) as hilos:
        resultados = list(hilos.map(
            lambda _: db.activa_al_dia("u1", "g1", tarde), range(2)))

    assert [r.id for r in resultados] == [relevo, relevo]
    activas = [c for c in db.plantel("u1", "g1") if c.activa]
    assert [c.id for c in activas] == [relevo]


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
