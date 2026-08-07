"""Economía transaccional: saldos, límites diarios y operaciones idempotentes.

Este módulo concentra las reglas monetarias. ``db`` conserva el esquema, las
migraciones y los repositorios de dominio; la dependencia va sólo de aquí a db.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import aventura as av
import casas as cas
import competir as comp
import cosmeticos as cos
import db
import huerto as hue
import logros as lgr
import objetos as obj
import simulacion as sim

# El bote diario. Es **uno solo para todo** lo que se gana: cuidar, evolucionar,
# competir y lo que te encuentres en una aventura salen de aquí. Antes no había
# tope en monedas —sólo por número de eventos— y el techo de 40 era un número
# derivado; ahora el techo es esto y se puede decir en una frase.
TOPE_DIARIO_ASCIICOINS = 20

TOPE_CUIDADOS = 12
TOPE_EVOLUCIONES = 1
TOPE_COMPETENCIAS = 3
PREMIO_CUIDADO = 1
PREMIO_EVOLUCION = 10
PREMIO_COMPETENCIA = 4
PREMIO_GANADOR = 6


@dataclass(frozen=True)
class Saldos:
    asciicoins: int
    asciigems: int


@dataclass(frozen=True)
class ResultadoCompra:
    comprada: bool
    replay: bool
    saldos: Saldos
    objeto: str

    def __bool__(self) -> bool:
        return self.comprada


@dataclass(frozen=True)
class ResultadoCuidado:
    criatura: sim.Criatura
    mensaje: str
    ok: bool = True
    espera: timedelta | None = None
    rupturas: tuple[sim.Ruptura, ...] = ()
    marca: bool = False
    subidas: tuple[str, ...] = ()
    etapa_anterior: str | None = None
    delta_asciicoins: int = 0
    delta_evolucion: int = 0
    ent_salud_ganada: int = 0
    usados: int = 0
    limite: int = TOPE_CUIDADOS
    evolucion_usadas: int = 0
    replay: bool = False
    topada: bool = False
    # La acción era válida pero el dominio devolvió la misma criatura: no hay
    # nada nuevo que enseñar. Sin esto, Discord no distingue este caso de un
    # cuidado normal y publica otra ficha idéntica.
    sin_efecto: bool = False

    @property
    def evoluciono(self) -> bool:
        return (
            self.etapa_anterior is not None
            and self.etapa_anterior != self.criatura.etapa
        )


@dataclass(frozen=True)
class SeleccionEntrenamientoConjunto:
    activo_id: int
    activo_nombre: str
    reserva_id: int
    reserva_nombre: str


@dataclass(frozen=True)
class ResultadoEntrenamientoConjunto:
    participantes: tuple[sim.ResultadoAccion, ...] = ()
    delta_asciicoins: int = 0
    delta_evolucion: int = 0
    usados: int = 0
    limite: int = TOPE_CUIDADOS
    evolucion_usadas: int = 0
    topada: bool = False
    replay: bool = False
    problema: str | None = None
    bloqueada: sim.Criatura | None = None
    espera: timedelta | None = None


@dataclass(frozen=True)
class ReciboCompetencia:
    usuario_id: str
    delta_asciicoins: int
    delta_competencia: int
    delta_evolucion: int
    usados: int
    evolucion_usadas: int = 0
    limite: int = TOPE_COMPETENCIAS
    topada: bool = False
    evoluciono: bool = False
    evolucion_topada: bool = False


@dataclass(frozen=True)
class ResultadoCompetencia:
    encuentro: comp.Encuentro | None
    antes: tuple[sim.Criatura, ...] = ()
    despues: tuple[sim.Criatura, ...] = ()
    rupturas: tuple[tuple[sim.Ruptura, ...], ...] = ()
    subidas: tuple[tuple[str, ...], ...] = ()
    recibos: tuple[ReciboCompetencia, ...] = ()
    replay: bool = False
    problema: str | None = None
    problema_usuario_id: str | None = None
    problema_criatura: sim.Criatura | None = None
    espera: timedelta | None = None


@dataclass(frozen=True)
class ResultadoViaje:
    criatura: sim.Criatura | None
    antes: sim.Criatura | None = None
    rupturas: tuple[sim.Ruptura, ...] = ()
    problema: str | None = None


def ejecutar_viaje(
    usuario_id: str,
    guild_id: str,
    criatura_id: int,
    salida: av.Salida,
    ahora: datetime,
    percance: av.Percance | None = None,
    viaje: av.Viaje | None = None,
) -> ResultadoViaje:
    """Confirma el viaje sobre la criatura activa actual, antes de publicarlo.

    Las aventuras no tienen ledger histórico; esta frontera sólo evita aplicar
    una vista vieja sobre otra criatura o sobre un estado concurrente.

    `viaje` es de dónde sale el marcador —dónde estuvo y cuántos nodos pasó—,
    que se apunta aquí para que vaya en la misma transacción que el desgaste.
    Es opcional porque lo que confirma el viaje es la `salida`; sin él, todo
    ocurre igual pero no se apunta nada.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        actual = db.criatura_activa_en(con, usuario_id, guild_id)
        if actual is None:
            return ResultadoViaje(None, problema="No hay un gachamon activo.")
        if actual.id != criatura_id:
            return ResultadoViaje(
                actual,
                problema="La aventura ya no pertenece al gachamon activo.",
            )
        avanzado = db._avanzar_en(con, actual, ahora)
        nueva, rupturas = av.aplicar_viaje(
            avanzado, salida, ahora, percance
        )
        db._guardar(con, nueva)
        if viaje is not None:
            db.apuntar_en(con, nueva.id, lgr.AVENTURAS)
            db.apuntar_en(con, nueva.id, lgr.clave_de_bioma(viaje.bioma.clave))
            if viaje.nodos_superados:
                db.apuntar_en(
                    con, nueva.id, lgr.NODOS, viaje.nodos_superados
                )
        return ResultadoViaje(
            nueva, antes=avanzado, rupturas=tuple(rupturas)
        )


def _fecha_economica(ahora: datetime) -> str:
    return ahora.astimezone(timezone.utc).date().isoformat()


def _asegurar_monedero(con, usuario_id: str, guild_id: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO monederos "
        "(usuario_id, guild_id, asciicoins, asciigems) VALUES (?, ?, 50, 50)",
        (usuario_id, guild_id),
    )


def _saldos_en(con, usuario_id: str, guild_id: str) -> Saldos:
    _asegurar_monedero(con, usuario_id, guild_id)
    fila = con.execute(
        "SELECT asciicoins, asciigems FROM monederos "
        "WHERE usuario_id = ? AND guild_id = ?",
        (usuario_id, guild_id),
    ).fetchone()
    return Saldos(fila["asciicoins"], fila["asciigems"])


def saldos(usuario_id: str, guild_id: str) -> Saldos:
    with db.conectar() as con:
        return _saldos_en(con, usuario_id, guild_id)


# --- Los logros y lo que pagan ----------------------------------------------

@dataclass(frozen=True)
class ReciboLogros:
    """Lo que acaba de desbloquear un gachamon y lo que le ha valido."""

    nuevos: tuple[lgr.Logro, ...] = ()
    asciigems: int = 0
    saldo: int = 0          # lo que queda en reserva después de cobrar


def pagar_logros(criatura: sim.Criatura, ahora: datetime) -> ReciboLogros:
    """Desbloquea las quince del gachamon y le paga las gemas a su dueño.

    Las tres de la persona no pasan por aquí: van en `pagar_logros_de_persona`.

    Vive aquí y no en `db` porque toca el monedero, y la orquestación monetaria
    es de este módulo. Desbloquear y pagar van bajo un mismo `BEGIN IMMEDIATE`,
    y no por costumbre: un logro apuntado sin pagar **no se puede reintentar**,
    porque el segundo intento ya lo encuentra puesto y no devuelve nada.

    No lleva ledger propio en `operaciones_economia` como los asciicoins. Allí
    hace falta porque el mismo clic puede reprocesarse y hay que congelar lo que
    pagó; aquí la clave primaria de `logros` ya dice, por sí sola, que cada uno
    se cobró una vez. Tampoco hay tope diario: todos son de una sola vez por
    construcción, así que no hay nada que machacar.

    Las gemas van al monedero de **la persona**, que es de quien son los
    monederos, aunque la medalla sea del gachamon: es lo que cierra el círculo
    con los cosméticos, que se compran para el que tengas activo.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hechos = lgr.hechos_de(criatura, db._marcador(con, criatura.id), ahora)
        nuevos = tuple(
            logro for logro in lgr.cumplidos(hechos, lgr.GACHAMON)
            if db.anotar_logro_en(con, criatura.id, logro.clave, ahora)
        )
        return _cobrar_logros(
            con, criatura.usuario_id, criatura.guild_id, nuevos
        )


def pagar_logros_de_persona(
    usuario_id: str, guild_id: str, ahora: datetime
) -> ReciboLogros:
    """Lo mismo, con las tres medallas que son tuyas y no de ningún gachamon.

    Se separa de `pagar_logros` en vez de meterle un modo porque las dos miran
    cosas distintas: aquella necesita una criatura viva delante y ésta funciona
    aunque se te haya muerto el plantel entero, que es de lo que van estas tres.
    """
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hechos = lgr.hechos_de_la_persona(
            db._marcador_de_persona(con, usuario_id, guild_id),
            db._especies_de(con, usuario_id, guild_id),
        )
        nuevos = tuple(
            logro for logro in lgr.cumplidos(hechos, lgr.PERSONA)
            if db.anotar_logro_de_persona_en(
                con, usuario_id, guild_id, logro.clave, ahora
            )
        )
        return _cobrar_logros(con, usuario_id, guild_id, nuevos)


def _cobrar_logros(
    con, usuario_id: str, guild_id: str, nuevos: tuple[lgr.Logro, ...]
) -> ReciboLogros:
    """Le paga a la persona lo que acaba de desbloquear, sea de quien sea.

    Compartido a propósito: las gemas van al mismo monedero se gane la medalla
    con un gachamon o por tu cuenta, y así el pago se escribe una vez.
    """
    if not nuevos:
        return ReciboLogros()

    gemas = sum(logro.gemas for logro in nuevos)
    _asegurar_monedero(con, usuario_id, guild_id)
    con.execute(
        "UPDATE monederos SET asciigems = asciigems + ? "
        "WHERE usuario_id = ? AND guild_id = ?",
        (gemas, usuario_id, guild_id),
    )
    return ReciboLogros(nuevos, gemas, _saldos_en(con, usuario_id, guild_id).asciigems)


def _contar_acreditadas(
    con, usuario_id: str, guild_id: str, fecha: str, tipo: str,
    hasta: int | None = None,
) -> int:
    if hasta is not None:
        return con.execute(
            "SELECT COUNT(*) FROM operaciones_economia "
            "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
            "AND tipo = ? AND resultado = 'acreditada' AND rowid <= ?",
            (usuario_id, guild_id, fecha, tipo, hasta),
        ).fetchone()[0]
    return con.execute(
        "SELECT COUNT(*) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND tipo = ? AND resultado = 'acreditada'",
        (usuario_id, guild_id, fecha, tipo),
    ).fetchone()[0]


def _ganado_hoy(con, usuario_id: str, guild_id: str, fecha: str) -> int:
    """Los asciicoins ya cobrados hoy, vengan de donde vengan.

    Sólo `acreditada`: las compras son `comprada` y llevan delta negativo, así
    que gastar no te devuelve sitio en el bote. El bote mide lo **ganado**, no
    lo que tienes.
    """
    return con.execute(
        "SELECT COALESCE(SUM(delta_asciicoins), 0) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND resultado = 'acreditada'",
        (usuario_id, guild_id, fecha),
    ).fetchone()[0]


def _resolver_recompensa(
    con, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int | None,
) -> tuple[int, int, bool]:
    """Cuánto se cobra de verdad, contra el tope de la actividad y el bote.

    Son dos frenos y el que manda es el bote: 20 al día para todo. Los topes por
    actividad siguen ahí porque limitan otra cosa —cuántas veces cobras por lo
    mismo— y quitarlos cambiaría el comportamiento de quien hace trece cuidados.
    `limite=None` es para lo que no tiene tope propio, como los hallazgos.

    **Se cobra lo que quepa, no todo o nada**: con 3 libres y un premio de 6
    entran 3. Es lo que espera quien lee «hasta 20 al día», y la fila del ledger
    lo admite tal cual; sólo cuando no cabe nada se apunta `topada`.
    """
    usados = _contar_acreditadas(con, usuario_id, guild_id, fecha, tipo)
    libre = max(0, TOPE_DIARIO_ASCIICOINS - _ganado_hoy(con, usuario_id, guild_id, fecha))
    cabe = limite is None or usados < limite
    delta = min(monto, libre) if cabe else 0
    acreditada = delta > 0
    if delta:
        _asegurar_monedero(con, usuario_id, guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (delta, usuario_id, guild_id),
        )
    return delta, usados + (1 if acreditada else 0), not acreditada


def _registrar_recompensa(
    con, evento_id: str, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int | None, solicitud: str,
) -> tuple[int, int, bool]:
    delta, usados, topada = _resolver_recompensa(
        con, usuario_id, guild_id, fecha, tipo, monto, limite
    )
    con.execute(
        "INSERT INTO operaciones_economia "
        "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
        "delta_asciicoins, solicitud) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            evento_id, usuario_id, guild_id, tipo, fecha,
            "topada" if topada else "acreditada", delta, solicitud,
        ),
    )
    return delta, usados, topada


@dataclass(frozen=True)
class ResultadoHallazgo:
    """Lo que te has encontrado por el camino y lo que de eso te llevas."""

    monedas: int = 0        # lo que entró de verdad, ya recortado por el bote
    monedas_vistas: int = 0  # lo que había en el suelo
    gemas: int = 0
    replay: bool = False

    @property
    def topado(self) -> bool:
        return self.monedas_vistas > self.monedas


def otorgar_hallazgo(
    evento_id: str, usuario_id: str, guild_id: str,
    monedas: int, gemas: int, ahora: datetime | None = None,
) -> ResultadoHallazgo:
    """Paga lo encontrado en una aventura, en una sola transacción.

    Las monedas pasan por el bote diario —un hallazgo puede salir topado y hay
    que decirlo— y las gemas no: son otra moneda y otra economía, y al 0,5 % no
    hacen falta frenos.

    La idempotencia sale de donde ya sale: la clave primaria del ledger sobre
    `(evento_id, usuario_id, guild_id, tipo)`. Con la fila puesta, reprocesar el
    mismo viaje no vuelve a pagar **ni monedas ni gemas**, aunque éstas no
    tengan ledger propio — van dentro de la misma transacción.
    """
    if not monedas and not gemas:
        return ResultadoHallazgo()

    ahora = ahora or db.ahora_utc()
    fecha = _fecha_economica(ahora)
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        ya_estaba = con.execute(
            "SELECT 1 FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ? AND tipo = 'aventura'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if ya_estaba is not None:
            return ResultadoHallazgo(replay=True)

        delta, _, _ = _registrar_recompensa(
            con, evento_id, usuario_id, guild_id, fecha, "aventura",
            monedas, None, json.dumps({"monedas": monedas, "gemas": gemas}),
        )
        if gemas:
            _asegurar_monedero(con, usuario_id, guild_id)
            con.execute(
                "UPDATE monederos SET asciigems = asciigems + ? "
                "WHERE usuario_id = ? AND guild_id = ?",
                (gemas, usuario_id, guild_id),
            )
        return ResultadoHallazgo(
            monedas=delta, monedas_vistas=monedas, gemas=gemas
        )


def _envolver_cuidado(
    resultado: sim.ResultadoAccion, *, delta: int = 0,
    delta_evolucion: int = 0, ent_salud_ganada: int = 0,
    usados: int = 0, evolucion_usadas: int = 0,
    topada: bool = False, sin_efecto: bool = False,
) -> ResultadoCuidado:
    return ResultadoCuidado(
        criatura=resultado.criatura,
        mensaje=resultado.mensaje,
        ok=resultado.ok,
        espera=resultado.espera,
        rupturas=tuple(resultado.rupturas),
        marca=resultado.marca,
        subidas=tuple(resultado.subidas),
        etapa_anterior=resultado.etapa_anterior,
        delta_asciicoins=delta + delta_evolucion,
        delta_evolucion=delta_evolucion,
        ent_salud_ganada=ent_salud_ganada,
        usados=usados,
        evolucion_usadas=evolucion_usadas,
        topada=topada,
        sin_efecto=sin_efecto,
    )


def ejecutar_cuidado(
    evento_id: str, usuario_id: str, guild_id: str,
    accion: str, ahora: datetime,
) -> ResultadoCuidado | None:
    """Aplica cuidado, cooldown y premios bajo un único ``BEGIN IMMEDIATE``."""
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        operacion = con.execute(
            "SELECT * FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ? AND tipo = 'cuidado'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if operacion is not None:
            if operacion["solicitud"] != accion:
                raise RuntimeError("el evento de cuidado pertenece a otra acción")
            criatura = db.criatura_activa_en(con, usuario_id, guild_id)
            if criatura is None:
                return None
            evolucion = con.execute(
                "SELECT resultado, delta_asciicoins FROM operaciones_economia "
                "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
                "AND tipo = 'evolucion'",
                (evento_id, usuario_id, guild_id),
            ).fetchone()
            delta_evolucion = evolucion["delta_asciicoins"] if evolucion else 0
            evolucion_usadas = (
                _contar_acreditadas(
                    con, usuario_id, guild_id, operacion["fecha_utc"], "evolucion"
                ) if evolucion else 0
            )
            return ResultadoCuidado(
                criatura=criatura,
                mensaje="",
                delta_asciicoins=operacion["delta_asciicoins"] + delta_evolucion,
                delta_evolucion=delta_evolucion,
                usados=_contar_acreditadas(
                    con, usuario_id, guild_id, operacion["fecha_utc"], "cuidado"
                ),
                evolucion_usadas=evolucion_usadas,
                replay=True,
                topada=operacion["resultado"] == "topada",
            )

        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return None
        criatura = db._avanzar_en(con, criatura, ahora)
        if not criatura.viva:
            db._guardar(con, criatura)
            return ResultadoCuidado(
                criatura, "Tu gachamon ya no está entre nosotros.", ok=False
            )

        espera = db.espera_en(con, criatura.id, accion, ahora)
        if espera and not sim.puede_saltarse_espera(criatura, accion):
            db._guardar(con, criatura)
            return ResultadoCuidado(criatura, "", ok=False, espera=espera)

        resultado = sim.aplicar_accion(criatura, accion, ahora)
        db._guardar(con, resultado.criatura)
        sin_efecto = (
            resultado.ok
            and accion != sim.ACTUALIZAR
            and resultado.criatura == criatura
        )
        if not resultado.ok or accion == sim.ACTUALIZAR or sin_efecto:
            return _envolver_cuidado(resultado, sin_efecto=sin_efecto)

        duracion = sim.COOLDOWNS.get(accion, timedelta(0))
        if duracion:
            db.poner_cooldown_en(con, criatura.id, accion, ahora + duracion)
        # Un cuidado de los que cuentan: los tres returns de arriba ya han
        # descartado el fallo, el `/actualizar` y el que no cambió nada.
        db.apuntar_en(con, criatura.id, lgr.CUIDADOS)
        fecha = _fecha_economica(ahora)
        delta, usados, topada = _registrar_recompensa(
            con, evento_id, usuario_id, guild_id, fecha,
            "cuidado", PREMIO_CUIDADO, TOPE_CUIDADOS, accion,
        )
        delta_evolucion = 0
        evolucion_usadas = 0
        if resultado.evoluciono:
            delta_evolucion, evolucion_usadas, _ = _registrar_recompensa(
                con, evento_id, usuario_id, guild_id, fecha,
                "evolucion", PREMIO_EVOLUCION, TOPE_EVOLUCIONES, accion,
            )
        return _envolver_cuidado(
            resultado,
            delta=delta,
            delta_evolucion=delta_evolucion,
            ent_salud_ganada=resultado.criatura.ent_salud - criatura.ent_salud,
            usados=usados,
            evolucion_usadas=evolucion_usadas,
            topada=topada,
        )


@dataclass(frozen=True)
class ResultadoConversacion:
    """Qué sacó la criatura de una conversación, si es que sacó algo."""

    ok: bool = False
    criatura: sim.Criatura | None = None
    # Los dos, y no uno: el entrenamiento sube siempre de uno en uno, pero
    # `stat_final` le saca la raíz, así que la estadística **casi nunca se mueve
    # en el mismo momento**. Decir «+1 de ingenio» cada vez sería mentir en tres
    # de cada cuatro conversaciones.
    entrenamiento_ganado: int = 0
    ingenio_ganado: int = 0
    animo_ganado: int = 0


def puede_aprender_hablando(criatura_id: int, ahora: datetime) -> bool:
    """Si a esta criatura le toca ya poder aprender algo de una conversación.

    Es una lectura suelta y barata, y existe para **no gastar una llamada a la
    IA cuando no hay nada que ganar**: juzgar cada mensaje serían veinte
    llamadas extra por hora y persona; juzgar sólo cuando el enfriamiento está
    listo es una cada 97 minutos como mucho.

    Que aquí diga que sí no basta: entre esta consulta y el premio pasa una
    llamada de red entera, así que `aprender_hablando` lo vuelve a comprobar
    dentro de su transacción.
    """
    with db.conectar() as con:
        return not db.espera_en(con, criatura_id, sim.CONVERSAR, ahora)


def aprender_hablando(
    usuario_id: str, guild_id: str, ahora: datetime | None = None
) -> ResultadoConversacion:
    """Le da a la activa lo que deja una buena conversación, si le toca.

    Quien llama ya ha decidido que la conversación valía la pena; aquí sólo se
    comprueba que el enfriamiento siga libre y se aplica. La comprobación se
    repite **dentro** de la transacción porque la de `puede_aprender_hablando`
    se hizo antes de hablar con la IA, y dos mensajes seguidos pueden llegar a
    este punto con el mismo permiso en la mano.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoConversacion()
        # Se avanza antes de premiar, igual que en `cuidar`: sin esto, una
        # criatura que lleva días sin comer cobraría por la conversación en vez
        # de morirse, porque la fila sólo se marca muerta al avanzarla.
        criatura = db._avanzar_en(con, criatura, ahora)
        if not criatura.viva:
            db._guardar(con, criatura)
            return ResultadoConversacion(criatura=criatura)
        if db.espera_en(con, criatura.id, sim.CONVERSAR, ahora):
            db._guardar(con, criatura)
            return ResultadoConversacion(criatura=criatura)

        resultado = sim.aplicar_conversacion(criatura)
        db._guardar(con, resultado.criatura)
        db.poner_cooldown_en(
            con, criatura.id, sim.CONVERSAR,
            ahora + sim.COOLDOWNS[sim.CONVERSAR],
        )
        return ResultadoConversacion(
            ok=True,
            criatura=resultado.criatura,
            entrenamiento_ganado=(
                resultado.criatura.ent_ingenio - criatura.ent_ingenio
            ),
            ingenio_ganado=resultado.criatura.ingenio - criatura.ingenio,
            animo_ganado=round(resultado.criatura.animo - criatura.animo),
        )


def ejecutar_entrenamiento_conjunto(
    evento_id: str,
    usuario_id: str,
    guild_id: str,
    seleccion: SeleccionEntrenamientoConjunto,
    ahora: datetime,
) -> ResultadoEntrenamientoConjunto:
    """Entrena activo y reserva bajo una sola transacción serializada."""
    solicitud = json.dumps(
        {
            "accion": "entrenar",
            "activo": {
                "id": seleccion.activo_id,
                "nombre": seleccion.activo_nombre,
            },
            "modo": "conjunto",
            "reserva": {
                "id": seleccion.reserva_id,
                "nombre": seleccion.reserva_nombre,
            },
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        filas = con.execute(
            "SELECT * FROM operaciones_economia WHERE evento_id = ? "
            "AND usuario_id = ? AND guild_id = ?",
            (evento_id, usuario_id, guild_id),
        ).fetchall()
        if filas:
            por_tipo = {fila["tipo"]: fila for fila in filas}
            if set(por_tipo) not in ({"cuidado"}, {"cuidado", "evolucion"}):
                raise RuntimeError("el evento de entrenamiento conjunto está incompleto")
            if any(fila["solicitud"] != solicitud for fila in filas):
                raise RuntimeError(
                    "el evento de entrenamiento conjunto pertenece a otra selección"
                )
            cuidado = por_tipo["cuidado"]
            evolucion = por_tipo.get("evolucion")
            delta_evolucion = (
                evolucion["delta_asciicoins"] if evolucion is not None else 0
            )
            return ResultadoEntrenamientoConjunto(
                delta_asciicoins=(
                    cuidado["delta_asciicoins"] + delta_evolucion
                ),
                delta_evolucion=delta_evolucion,
                usados=_contar_acreditadas(
                    con,
                    usuario_id,
                    guild_id,
                    cuidado["fecha_utc"],
                    "cuidado",
                ),
                evolucion_usadas=(
                    _contar_acreditadas(
                        con,
                        usuario_id,
                        guild_id,
                        evolucion["fecha_utc"],
                        "evolucion",
                    )
                    if evolucion is not None
                    else 0
                ),
                topada=cuidado["resultado"] == "topada",
                replay=True,
            )

        activo = db.criatura_activa_en(con, usuario_id, guild_id)
        if (
            activo is None
            or activo.id != seleccion.activo_id
            or activo.nombre != seleccion.activo_nombre
        ):
            return ResultadoEntrenamientoConjunto(problema="activo_caduco")

        reserva = db.criatura_en(con, seleccion.reserva_id)
        if (
            reserva is None
            or reserva.id == activo.id
            or reserva.usuario_id != usuario_id
            or reserva.guild_id != guild_id
            or not reserva.viva
            or reserva.activa
            or sim.esta_sin_nombrar(reserva)
            or reserva.nombre != seleccion.reserva_nombre
        ):
            return ResultadoEntrenamientoConjunto(problema="reserva_caduca")

        esperas = (
            (activo, db.espera_en(con, activo.id, sim.ENTRENAR, ahora)),
            (reserva, db.espera_en(con, reserva.id, sim.ENTRENAR, ahora)),
        )
        bloqueada, espera = max(esperas, key=lambda par: par[1])
        if espera > timedelta(0):
            return ResultadoEntrenamientoConjunto(
                problema="cooldown", bloqueada=bloqueada, espera=espera
            )

        # Por `db` y no por `sim` a secas: el hogar cambia el ritmo del activo,
        # y llamando directo se entrenaría con el de quien tiene techo aunque
        # esté a la intemperie. La reserva no avanza, que es su invariante.
        activo_avanzado = db._avanzar_en(con, activo, ahora)
        if not activo_avanzado.viva:
            db._guardar(con, activo_avanzado)
            return ResultadoEntrenamientoConjunto(
                problema="activo_muerto", bloqueada=activo_avanzado
            )

        participantes = (
            sim.aplicar_entrenamiento_conjunto(activo_avanzado),
            sim.aplicar_entrenamiento_conjunto(reserva),
        )
        for participante in participantes:
            db._guardar(con, participante.criatura)

        hasta = ahora + sim.COOLDOWNS[sim.ENTRENAR]
        for participante in participantes:
            db.poner_cooldown_en(
                con, participante.criatura.id, sim.ENTRENAR, hasta
            )
            db.apuntar_en(con, participante.criatura.id, lgr.CUIDADOS)

        fecha = _fecha_economica(ahora)
        delta, usados, topada = _registrar_recompensa(
            con,
            evento_id,
            usuario_id,
            guild_id,
            fecha,
            "cuidado",
            PREMIO_CUIDADO,
            TOPE_CUIDADOS,
            solicitud,
        )
        delta_evolucion = 0
        evolucion_usadas = 0
        if any(participante.evoluciono for participante in participantes):
            delta_evolucion, evolucion_usadas, _ = _registrar_recompensa(
                con,
                evento_id,
                usuario_id,
                guild_id,
                fecha,
                "evolucion",
                PREMIO_EVOLUCION,
                TOPE_EVOLUCIONES,
                solicitud,
            )
        return ResultadoEntrenamientoConjunto(
            participantes=participantes,
            delta_asciicoins=delta + delta_evolucion,
            delta_evolucion=delta_evolucion,
            usados=usados,
            evolucion_usadas=evolucion_usadas,
            topada=topada,
        )


# Qué cuenta cada victoria. Vive aquí y no en `competir.py` ni en `logros.py`
# porque es el único sitio que habla los dos vocabularios: la modalidad y la
# clave del marcador.
MARCADOR_DE_MODALIDAD = {
    comp.CARRERA: lgr.CARRERAS,
    comp.SUMO: lgr.SUMOS,
    comp.TOTEM: lgr.TOTEMS,
    comp.LABERINTO: lgr.LABERINTOS,
}


def _replay_competencia(
    con, evento_id: str, usuarios: tuple[str, ...],
    guild_id: str, solicitud: str,
) -> ResultadoCompetencia | None:
    filas = con.execute(
        "SELECT rowid AS orden_ledger, * FROM operaciones_economia "
        "WHERE evento_id = ? AND guild_id = ? AND tipo = 'competencia'",
        (evento_id, guild_id),
    ).fetchall()
    if not filas:
        return None
    por_usuario = {fila["usuario_id"]: fila for fila in filas}
    if set(por_usuario) != set(usuarios):
        raise RuntimeError("el evento de competencia está incompleto")
    recibos = []
    for usuario_id in usuarios:
        fila = por_usuario[usuario_id]
        if fila["solicitud"] != solicitud:
            raise RuntimeError("el evento de competencia pertenece a otro encuentro")
        evolucion = con.execute(
            "SELECT rowid AS orden_ledger, fecha_utc, resultado, "
            "delta_asciicoins FROM operaciones_economia "
            "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
            "AND tipo = 'evolucion'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        delta_evolucion = evolucion["delta_asciicoins"] if evolucion else 0
        recibos.append(ReciboCompetencia(
            usuario_id=usuario_id,
            delta_asciicoins=fila["delta_asciicoins"] + delta_evolucion,
            delta_competencia=fila["delta_asciicoins"],
            delta_evolucion=delta_evolucion,
            usados=_contar_acreditadas(
                con, usuario_id, guild_id, fila["fecha_utc"], "competencia",
                fila["orden_ledger"],
            ),
            evolucion_usadas=(
                _contar_acreditadas(
                    con, usuario_id, guild_id, evolucion["fecha_utc"], "evolucion",
                    evolucion["orden_ledger"],
                ) if evolucion else 0
            ),
            topada=fila["resultado"] == "topada",
            evoluciono=evolucion is not None,
            evolucion_topada=(
                evolucion is not None and evolucion["resultado"] == "topada"
            ),
        ))
    return ResultadoCompetencia(None, recibos=tuple(recibos), replay=True)


def ejecutar_competencia(
    evento_id: str,
    usuario_ids: list[str] | tuple[str, ...],
    guild_id: str,
    tipo: str,
    ahora: datetime,
    rng: random.Random | None = None,
) -> ResultadoCompetencia:
    """Resuelve y confirma el encuentro completo antes de cualquier publicación."""
    usuarios = tuple(usuario_ids)
    if len(set(usuarios)) != len(usuarios):
        raise ValueError("una persona no puede competir dos veces en el mismo encuentro")
    solicitud = json.dumps(
        {"participantes": usuarios, "tipo": tipo},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    rng = rng or random.Random()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        replay = _replay_competencia(
            con, evento_id, usuarios, guild_id, solicitud
        )
        if replay is not None:
            return replay

        antes_lista = []
        for usuario_id in usuarios:
            criatura = db.criatura_activa_en(con, usuario_id, guild_id)
            if criatura is None:
                return ResultadoCompetencia(
                    None,
                    problema="Falta un gachamon activo para competir.",
                    problema_usuario_id=usuario_id,
                )
            antes_lista.append(criatura)
        antes = tuple(antes_lista)
        criaturas = tuple(
            db._avanzar_en(con, criatura, ahora) for criatura in antes
        )
        for criatura in criaturas:
            db._guardar(con, criatura)
        for usuario_id, criatura in zip(usuarios, criaturas):
            if not criatura.viva:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon ha muerto antes de competir.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                )
            if criatura.hambre < sim.HAMBRE_MINIMA_COMPETIR:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon tiene demasiada hambre para competir.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                )
            espera = db.espera_en(con, criatura.id, sim.COMPETIR, ahora)
            if espera:
                return ResultadoCompetencia(
                    None, antes=antes, despues=criaturas,
                    problema="Un gachamon todavía se está recuperando.",
                    problema_usuario_id=usuario_id,
                    problema_criatura=criatura,
                    espera=espera,
                )

        stats = comp.STATS[tipo]
        encuentro = comp.enfrentar(
            [
                comp.competidor_de(
                    criatura,
                    **{
                        f"bonus_{stat}": db.efecto_activo_en(
                            con, criatura.id, stat, ahora
                        )
                        for stat in sim.ESTADISTICAS
                    },
                )
                for criatura in criaturas
            ],
            tipo,
            rng,
        )
        ganador = encuentro.orden[0]
        aplicadas = tuple(
            sim.aplicar_competencia(
                criatura,
                dorsal == ganador,
                stats,
                rng,
                comp.margen_de(encuentro, dorsal),
            )
            for dorsal, criatura in enumerate(criaturas)
        )
        despues = tuple(criatura for criatura, _ in aplicadas)
        rupturas = tuple(tuple(lista) for _, lista in aplicadas)
        subidas = tuple(
            tuple(ruptura.stat for ruptura in lista) for lista in rupturas
        )
        for criatura in despues:
            db._guardar(con, criatura)
            db.poner_cooldown_en(
                con, criatura.id, sim.COMPETIR,
                ahora + sim.COOLDOWNS[sim.COMPETIR],
            )

        # El marcador del ganador, aquí dentro y no después: si se cayera la
        # conexión entre ganar y apuntarlo quedaría una victoria que no cuenta
        # para nada, y nadie tendría forma de saberlo. El replay de más arriba
        # ya ha vuelto antes de llegar aquí, así que reprocesar el mismo evento
        # no cuenta dos veces.
        campeon = despues[ganador]
        db.apuntar_en(con, campeon.id, MARCADOR_DE_MODALIDAD[tipo])
        if encuentro.es_torneo:
            db.apuntar_en(con, campeon.id, lgr.TORNEOS)

        fecha = _fecha_economica(ahora)
        recibos = []
        for dorsal, (anterior, nueva) in enumerate(zip(criaturas, despues)):
            delta_comp, usados, topada = _registrar_recompensa(
                con, evento_id, nueva.usuario_id, guild_id, fecha,
                "competencia",
                PREMIO_GANADOR if dorsal == ganador else PREMIO_COMPETENCIA,
                TOPE_COMPETENCIAS,
                solicitud,
            )
            evoluciono = anterior.etapa != nueva.etapa
            delta_evolucion = 0
            evolucion_usadas = 0
            evolucion_topada = False
            if evoluciono:
                delta_evolucion, evolucion_usadas, evolucion_topada = (
                    _registrar_recompensa(
                        con, evento_id, nueva.usuario_id, guild_id, fecha,
                        "evolucion", PREMIO_EVOLUCION,
                        TOPE_EVOLUCIONES, solicitud,
                    )
                )
            recibos.append(ReciboCompetencia(
                usuario_id=nueva.usuario_id,
                delta_asciicoins=delta_comp + delta_evolucion,
                delta_competencia=delta_comp,
                delta_evolucion=delta_evolucion,
                usados=usados,
                evolucion_usadas=evolucion_usadas,
                topada=topada,
                evoluciono=evoluciono,
                evolucion_topada=evolucion_topada,
            ))
        return ResultadoCompetencia(
            encuentro=encuentro,
            antes=antes,
            despues=despues,
            rupturas=rupturas,
            subidas=subidas,
            recibos=tuple(recibos),
        )


@dataclass(frozen=True)
class ResultadoCosmetico:
    """Cómo salió comprar, poner o quitar un cosmético."""

    ok: bool = False
    criatura: sim.Criatura | None = None
    saldo: int = 0                  # asciigems que quedan
    problema: str | None = None
    # El que llevaba de ese tipo y se ha quitado para dejar sitio. **No se
    # pierde**: sigue en el ropero, que es de la persona.
    sustituido: cos.Cosmetico | None = None


def _vestir_en(
    con, criatura: sim.Criatura, tipo: str, clave: str | None
) -> tuple[sim.Criatura, cos.Cosmetico | None]:
    """Le cambia una pieza y devuelve cómo queda y qué llevaba antes."""
    llevaba = cos.buscar(getattr(criatura, tipo))
    vestido = replace(criatura, **{tipo: clave})
    db._guardar(con, vestido)
    return vestido, llevaba


def comprar_cosmetico(
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico
) -> ResultadoCosmetico:
    """Cobra las gemas, lo mete en tu ropero y se lo pone al activo.

    Como las compras de la tienda, la condición del cobro viaja **dentro** del
    UPDATE: así dos clics a la vez no pueden dejar el saldo en negativo pagando
    dos veces la última gema.

    No lleva fila en `operaciones_economia` porque allí sólo caben asciicoins
    —lo dice su CHECK—, pero el doble clic sí hace falta pararlo: dos compras del
    mismo sombrero cobrarían 120 gemas y dejarían una corona. Lo para el ropero:
    si ya lo tienes, ni se cobra ni se toca nada. Mirar antes de cobrar es seguro
    porque el `BEGIN IMMEDIATE` pone en fila a los que escriben, así que el
    segundo clic ya lo encuentra dentro.

    Que además se lo ponga es a propósito, y no un efecto secundario: es lo que
    espera quien acaba de gastarse sesenta gemas en una corona. Lo que llevara de
    ese tipo se le quita pero **no se pierde**, que es la diferencia con antes.

    Sin gachamon activo se puede comprar igual: va al ropero y se equipa cuando
    haya a quién.
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        _asegurar_monedero(con, usuario_id, guild_id)

        if cosmetico.clave in db._ropero(con, usuario_id, guild_id):
            return ResultadoCosmetico(
                criatura=criatura,
                saldo=_saldos_en(con, usuario_id, guild_id).asciigems,
                problema=(
                    f"Ya tienes **{cosmetico.nombre}** en tu ropero. "
                    "Póntelo desde 🎨 Personalizar."
                ),
            )

        pagado = con.execute(
            "UPDATE monederos SET asciigems = asciigems - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciigems >= ?",
            (cosmetico.precio, usuario_id, guild_id, cosmetico.precio),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        if not pagado:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=(
                    f"Te faltan {cosmetico.precio - saldo} asciigems. "
                    "Se ganan con los logros: mira `/logros`."
                ),
            )

        db.guardar_en_el_ropero_en(con, usuario_id, guild_id, cosmetico.clave)
        if criatura is None:
            return ResultadoCosmetico(ok=True, saldo=saldo)
        vestido, sustituido = _vestir_en(
            con, criatura, cosmetico.tipo, cosmetico.clave
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


@dataclass(frozen=True)
class ResultadoMudanza:
    """Cómo salió comprar casa."""

    ok: bool = False
    casa: cas.Casa | None = None        # la nueva
    desde: cas.Casa | None = None       # la que se mejoró; None es una casa más
    casa_id: int = 0                    # cuál es, para poder mudar gente a ella
    saldo: int = 0                      # asciicoins que quedan
    problema: str | None = None


@dataclass(frozen=True)
class ResultadoVenta:
    """Cómo salió vender la casa."""

    ok: bool = False
    casa: cas.Casa | None = None      # la que se ha vendido
    cobrado: int = 0
    saldo: int = 0
    guardados: int = 0                # muebles que vuelven al armario
    desalojados: int = 0              # gachamones que se van al refugio
    problema: str | None = None


def vender_casa(
    usuario_id: str, guild_id: str, casa_id: int,
    ahora: datetime | None = None,
) -> ResultadoVenta:
    """Vende **esa** casa y recoloca lo que tenía dentro.

    **Lo cobrado no pasa por el bote diario, y es lo más importante de aquí.**
    El bote son veinte asciicoins al día y la casa grande devuelve novecientos
    sesenta: si esto contara como ganancia se cobrarían veinte y se perderían
    novecientos cuarenta. Una venta es una **devolución**, no una ganancia, y por
    eso entra directa al monedero y no lleva fila en `operaciones_economia` —que
    además envenenaría el bote del día, porque `_ganado_hoy` suma todo lo
    acreditado.

    Lo que impide cobrarla dos veces no es el ledger sino el propio estado: la
    fila de `casas_propias` ya no está y el segundo intento no la encuentra. Es
    el cerrojo de `comprar_cosmetico`.

    Sus gachamones se van al refugio, sus muebles vuelven al armario —retirar uno
    nunca lo destruye— y lo plantado en sus bancales se pierde, porque la tierra
    era de esa casa. Las demás casas no se tocan.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        propia = hogar.casa_por_id(casa_id)
        if propia is None:
            return ResultadoVenta(
                saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
                problema=(
                    "No tienes casa que vender: vives en el refugio."
                    if not hogar.casas else "Esa casa no es tuya."
                ),
            )

        casa = propia.casa
        cobrado = cas.lo_que_dan_por(casa)
        _asegurar_monedero(con, usuario_id, guild_id)
        con.execute(
            "UPDATE monederos SET asciicoins = asciicoins + ? "
            "WHERE usuario_id = ? AND guild_id = ?",
            (cobrado, usuario_id, guild_id),
        )
        desalojados = db.inquilinos_en(con, usuario_id, guild_id).get(casa_id, 0)
        guardados = db.vender_la_casa_en(
            con, usuario_id, guild_id, casa_id, ahora
        )
        return ResultadoVenta(
            ok=True, casa=casa, cobrado=cobrado, guardados=guardados,
            desalojados=desalojados,
            saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        )


def comprar_casa(
    usuario_id: str, guild_id: str, casa: cas.Casa,
    ahora: datetime | None = None, mejorar: int | None = None,
) -> ResultadoMudanza:
    """Cobra los asciicoins y te da una casa, en una transacción.

    Hace dos cosas según venga `mejorar`:

    * **Sin él, es una casa más**, hasta el tope de `cas.MAXIMO_CASAS`.
    * **Con él, se mejora esa casa**, y ahí sigue mandando la regla de siempre:
      sólo se sube de tamaño. Mejorar conserva el `id`, así que sus inquilinos,
      sus muebles y sus bancales se quedan donde estaban — es una obra y no una
      mudanza.

    Se paga con asciicoins y no con gemas a propósito: las gemas están enteras
    comprometidas con los cosméticos, y los asciicoins hasta ahora sólo compraban
    pociones. Esto les da adónde ir.

    No lleva fila en `operaciones_economia` aunque sean asciicoins: allí se
    congela lo que pagó un evento que puede reprocesarse, y aquí cada compra es
    una acción deliberada que no se reprocesa.
    """
    if cas.CATALOGO.get(casa.clave) != casa:
        raise ValueError("la casa no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        _asegurar_monedero(con, usuario_id, guild_id)
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins

        vieja = hogar.casa_por_id(mejorar) if mejorar else None
        if mejorar is not None and vieja is None:
            return ResultadoMudanza(saldo=saldo, problema="Esa casa no es tuya.")
        if vieja is not None and not cas.puede_mejorarse_a(vieja, casa):
            return ResultadoMudanza(
                casa=vieja.casa, desde=vieja.casa, casa_id=vieja.id, saldo=saldo,
                problema=f"Esa ya es {vieja.casa.nombre}, y no se puede empeorar.",
            )
        if vieja is None and not hogar.puede_comprar_otra():
            return ResultadoMudanza(
                saldo=saldo,
                problema=(
                    f"Ya tienes {cas.MAXIMO_CASAS} casas, que es el máximo. "
                    "Vende una o mejora las que tienes."
                ),
            )

        # Mejorar cuesta sólo la diferencia: pagar el precio entero por subir de
        # tamaño saldría más caro que vender y comprar, y nadie mejoraría nunca.
        cuesta = casa.precio - (cas.lo_que_dan_por(vieja.casa) if vieja else 0)
        pagado = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (cuesta, usuario_id, guild_id, cuesta),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins
        if not pagado:
            return ResultadoMudanza(
                casa=casa, desde=vieja.casa if vieja else None, saldo=saldo,
                problema=(
                    f"Te faltan {cuesta - saldo} asciicoins. "
                    "Se ganan cuidando, evolucionando y compitiendo."
                ),
            )

        if vieja is not None:
            db.mejorar_casa_en(con, vieja.id, casa.clave)
            casa_id = vieja.id
        else:
            casa_id = db.anadir_casa_en(
                con, usuario_id, guild_id, casa.clave, ahora
            )
            # Los que estaban en el refugio se mudan solos hasta llenarla. Quien
            # se compra una casa quiere meter dentro a los suyos, y obligarle a
            # colocarlos uno a uno sería pedirle que repita lo obvio; repartir
            # sigue estando ahí para cuando quiera otra cosa.
            db.acoger_a_los_sin_casa_en(
                con, usuario_id, guild_id, casa_id, casa.aforo
            )
        return ResultadoMudanza(
            ok=True, casa=casa, desde=vieja.casa if vieja else None,
            casa_id=casa_id, saldo=saldo,
        )


@dataclass(frozen=True)
class ResultadoMudanzaDeGachamon:
    """Cómo salió cambiar de casa a un gachamon."""

    ok: bool = False
    criatura: sim.Criatura | None = None
    casa: cas.Casa | None = None       # adonde va; None es el refugio
    problema: str | None = None


def mudar_gachamon(
    usuario_id: str, guild_id: str, criatura_id: int, casa_id: int | None,
    ahora: datetime | None = None,
) -> ResultadoMudanzaDeGachamon:
    """Cambia de casa a un gachamon tuyo, si le queda sitio.

    `casa_id` a `None` lo manda al refugio, que es lo que hace falta para poder
    vaciar una casa antes de venderla y para sacar a alguien de una que se pasa
    del aforo.

    El aforo se comprueba **dentro** de la transacción y contando de verdad
    quién hay: entre que se pinta el menú y se pulsa pueden haber entrado otros,
    y el desplegable se queda con la foto vieja.

    Quien ya estaba por encima del aforo —lo que dejó la migración— no estorba:
    esto sólo frena que **entre** uno más, así que esas casas se van vaciando y
    nunca se llenan de nuevo por encima del tope.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        criatura = db.criatura_en(con, criatura_id)
        if (
            criatura is None
            or criatura.usuario_id != usuario_id
            or criatura.guild_id != guild_id
        ):
            return ResultadoMudanzaDeGachamon(problema="Ese gachamon no es tuyo.")
        if not criatura.viva:
            return ResultadoMudanzaDeGachamon(
                criatura=criatura, problema="Ya no está entre nosotros."
            )
        if criatura.casa_id == casa_id:
            return ResultadoMudanzaDeGachamon(
                criatura=criatura, problema="Ya vive ahí."
            )

        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        destino = hogar.casa_por_id(casa_id)
        if casa_id is not None and destino is None:
            return ResultadoMudanzaDeGachamon(
                criatura=criatura, problema="Esa casa no es tuya."
            )
        if destino is not None:
            dentro = db.inquilinos_en(con, usuario_id, guild_id).get(casa_id, 0)
            if not destino.caben_mas_inquilinos(dentro):
                return ResultadoMudanzaDeGachamon(
                    criatura=criatura,
                    problema=(
                        f"En {destino.casa.nombre} ya viven "
                        f"{dentro}/{destino.casa.aforo}. Saca a alguien primero."
                    ),
                )

        db.mudar_criatura_en(con, criatura_id, casa_id)
        return ResultadoMudanzaDeGachamon(
            ok=True,
            criatura=replace(criatura, casa_id=casa_id),
            casa=destino.casa if destino else None,
        )


@dataclass(frozen=True)
class ResultadoMueble:
    """Cómo salió comprar, colocar o retirar un mueble."""

    ok: bool = False
    mueble: cas.Mueble | None = None
    casa: cas.Casa | None = None
    comodidad: int = 0          # la de la casa después
    puestos: int = 0            # cuántos huecos van ocupados
    saldo: int = 0
    problema: str | None = None


def _estado_de_la_casa(
    con, usuario_id: str, guild_id: str, ahora: datetime,
    casa_id: int | None = None,
) -> tuple[cas.CasaPropia | None, dict[str, bool], str | None]:
    """La casa que se va a amueblar, lo que hay dentro, y por qué no se puede.

    El refugio no se decora —es común y no es tuyo— y a la intemperie no hay
    dónde poner nada. Las dos cosas se comprueban aquí, en un solo sitio, porque
    las tres operaciones necesitan lo mismo.

    Sin `casa_id` se coge la primera, que es la que compró antes: con una sola
    casa —el caso de casi todo el mundo— no hay nada que elegir y no tiene
    sentido obligar a decirlo.
    """
    hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
    if not hogar.casas:
        estorbo = (
            "El refugio no se puede amueblar: es de todos. Cómprate una casa."
            if hogar.estado(ahora) == cas.REFUGIO
            else "Estás a la intemperie. Cómprate una casa para amueblarla."
        )
        return None, {}, estorbo
    propia = hogar.casa_por_id(casa_id) if casa_id else hogar.casas[0]
    if propia is None:
        return None, {}, "Esa casa no es tuya."
    return propia, db._mobiliario(con, usuario_id, guild_id), None


def _recibo_mueble(
    con, usuario_id: str, guild_id: str, propia, mobiliario, mueble=None,
    ok=False, problema=None,
) -> ResultadoMueble:
    """El recibo, contando **lo que hay en esa casa** y no en todas.

    `mobiliario` es de la persona —uno de cada— y sirve para saber qué tienes;
    los huecos y la comodidad son de la casa, y salen de sus `puestos`.
    """
    # Se relee la casa en vez de fiarse de la que llegó: colocar y retirar ya
    # han escrito, y el recibo con la foto de antes anunciaría la comodidad
    # vieja justo en el mensaje que dice que acaba de cambiar.
    if propia is not None:
        fresca = next(
            (c for c in db._casas_de(con, usuario_id, guild_id)
             if c.id == propia.id),
            propia,
        )
    else:
        fresca = None
    return ResultadoMueble(
        ok=ok, mueble=mueble, casa=fresca.casa if fresca else None,
        comodidad=fresca.comodidad if fresca else 0,
        puestos=len(fresca.puestos) if fresca else 0,
        saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        problema=problema,
    )


def comprar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None, casa_id: int | None = None,
) -> ResultadoMueble:
    """Cobra el mueble y lo coloca si queda hueco; si no, se guarda.

    Uno de cada, como el ropero, y por lo mismo: repetir la chimenea no
    significaría nada y llegar al techo comprando cuatro veces el mueble más caro
    dejaría el catálogo sin sentido. Comprar el que ya tienes no cobra.
    """
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora, casa_id
        )
        _asegurar_monedero(con, usuario_id, guild_id)
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        assert casa is not None
        if mueble.clave in mobiliario:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"Ya tienes **{mueble.nombre}**.",
            )

        pagado = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (mueble.precio, usuario_id, guild_id, mueble.precio),
        ).rowcount > 0
        if not pagado:
            faltan = mueble.precio - _saldos_en(
                con, usuario_id, guild_id
            ).asciicoins
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"Te faltan {faltan} asciicoins.",
            )

        # Se cuelga solo si cabe **en esta casa**; si no, va al armario.
        dentro = cas.caben_mas(casa.casa, casa.puestos)
        db.comprar_mueble_en(
            con, usuario_id, guild_id, mueble.clave, dentro,
            casa.id if dentro else None,
        )
        mobiliario[mueble.clave] = dentro

        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def colocar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None, casa_id: int | None = None,
) -> ResultadoMueble:
    """Lo mete en la casa. Falla si no queda hueco, y lo dice con el número."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora, casa_id
        )
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        assert casa is not None
        if mueble.clave not in mobiliario:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"No tienes **{mueble.nombre}**.",
            )
        if mobiliario[mueble.clave]:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"**{mueble.nombre}** ya está puesto.",
            )
        if not cas.caben_mas(casa.casa, casa.puestos):
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=(
                    f"No cabe: {casa.casa.nombre} tiene {casa.casa.huecos} huecos y "
                    "están todos ocupados. Retira algo primero."
                ),
            )

        db.colocar_mueble_en(
            con, usuario_id, guild_id, mueble.clave, True, casa.id
        )
        mobiliario[mueble.clave] = True
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def retirar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None, casa_id: int | None = None,
) -> ResultadoMueble:
    """Lo saca de la casa. Se guarda: nunca se pierde, como el ropero."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora, casa_id
        )
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
        if not mobiliario.get(mueble.clave):
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=f"**{mueble.nombre}** no está puesto.",
            )

        db.colocar_mueble_en(con, usuario_id, guild_id, mueble.clave, False)
        mobiliario[mueble.clave] = False
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


@dataclass(frozen=True)
class ResultadoHuerto:
    """Cómo salió plantar, regar o cosechar."""

    ok: bool = False
    bancal: int = 0
    sembrado: str | None = None         # la clave de lo que se acaba de sembrar
    cosechado: str | None = None        # la clave del poroto que salió
    cuantos: int = 0                    # cuántos, todos de ese mismo color
    arcoiris: bool = False              # y si además salió uno arcoíris
    listo_en: datetime | None = None
    problema: str | None = None


def _huerto_abierto(
    con, usuario_id: str, guild_id: str, ahora: datetime
) -> tuple[list[hue.Bancal], str | None]:
    """Los bancales de **todas** tus casas, o por qué no tienes ninguno.

    Van en una sola lista y en el orden en que compraste las casas: quien juega
    ve su huerto entero de una vez, y cada bancal lleva de qué casa es.
    """
    hogar = db._hogar_leido(con, usuario_id, guild_id, ahora)
    bancales: list[hue.Bancal] = []
    for propia in hogar.casas:
        bancales += db._huerto_de(
            con, usuario_id, guild_id, propia.id,
            hue.bancales_de(propia.casa.clave),
        )
    if not bancales:
        return [], (
            "El refugio no tiene huerto. Cómprate una casa en 🛒 **Tienda**."
        )
    return bancales, None


def _bancal_de(
    bancales: list[hue.Bancal], casa_id: int, numero: int
) -> hue.Bancal | None:
    """El bancal `numero` de esa casa, o `None` si no es suyo.

    Hace falta la pareja porque cada casa numera los suyos desde 1: buscar sólo
    por número le daría el bancal de otra casa a quien tenga varias, y regaría o
    cosecharía donde no toca. Con `casa_id` a 0 —lo que manda quien sólo tiene
    una— vale el primero que lleve ese número.
    """
    return next(
        (b for b in bancales
         if b.numero == numero and (not casa_id or b.casa_id == casa_id)),
        None,
    )


def plantar(
    usuario_id: str, guild_id: str, bancal: int, ahora: datetime | None = None,
    que: str = hue.SEMILLA, casa_id: int = 0,
) -> ResultadoHuerto:
    """Gasta lo que se siembre y lo siembra.

    `que` va **después de `ahora`** y con valor por defecto porque hay bastante
    código que llama a esto por posición; así seguir sembrando semillas se
    escribe igual que antes.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = _bancal_de(bancales, casa_id, bancal)
        if elegido is None:
            return ResultadoHuerto(problema="Ese bancal no es tuyo.")
        if elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="En ese bancal ya hay algo creciendo."
            )
        objeto = obj.CATALOGO.get(que)
        if objeto is None:
            return ResultadoHuerto(bancal=bancal, problema="Eso no se siembra.")
        if not db.gastar_en(con, usuario_id, guild_id, que):
            # Con el nombre entero en vez de concordar en género: «ninguna
            # semilla» y «ningún poroto rojo» pedían dos frases para decir lo
            # mismo, y la lista de cosas sembrables sólo va a crecer.
            pista = " Cómpralas en 🛒 **Tienda**." if que == hue.SEMILLA else ""
            return ResultadoHuerto(
                bancal=bancal,
                problema=f"Ya no te queda {objeto.emoji} **{objeto.nombre}**.{pista}",
            )

        db.plantar_en(
            con, usuario_id, guild_id, elegido.casa_id, bancal, ahora, que
        )
        return ResultadoHuerto(
            ok=True, bancal=bancal, sembrado=que,
            listo_en=hue.Bancal(bancal, ahora).listo_en(),
        )


def regar(
    usuario_id: str, guild_id: str, bancal: int, ahora: datetime | None = None,
    casa_id: int = 0,
) -> ResultadoHuerto:
    """Adelanta la cosecha. Sólo mientras crece: regar lo listo no haría nada."""
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = _bancal_de(bancales, casa_id, bancal)
        if elegido is None or not elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="Ahí no hay nada plantado."
            )
        if elegido.regado:
            return ResultadoHuerto(bancal=bancal, problema="Ya está regado.")
        if elegido.listo(ahora):
            return ResultadoHuerto(
                bancal=bancal, problema="Ya está listo: cosecha y vuelve a sembrar."
            )

        db.regar_en(con, usuario_id, guild_id, elegido.casa_id, bancal)
        regado = replace(elegido, regado=True)
        return ResultadoHuerto(ok=True, bancal=bancal, listo_en=regado.listo_en())


def cosechar(
    usuario_id: str, guild_id: str, bancal: int,
    ahora: datetime | None = None, rng=None, casa_id: int = 0,
) -> ResultadoHuerto:
    """Recoge la cosecha y deja el bancal en barbecho.

    **El color lo hereda lo sembrado**, y sólo se sortea cuando lo sembrado no
    tiene ninguno: la semilla de la tienda y el arcoíris. Sembrar un poroto rojo
    y recoger azules sería no entender qué se plantó.

    Salen varios y **todos del mismo color**: se tira una vez y esa tirada vale
    para la mata entera, que es lo que se espera de una planta. Aparte va el
    arcoíris, que sale de cualquier cosecha, sustituye a uno del lote y no cambia
    cuántos recoges.
    """
    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        bancales, estorbo = _huerto_abierto(con, usuario_id, guild_id, ahora)
        if estorbo:
            return ResultadoHuerto(problema=estorbo)
        elegido = _bancal_de(bancales, casa_id, bancal)
        if elegido is None or not elegido.plantado:
            return ResultadoHuerto(
                bancal=bancal, problema="Ahí no hay nada plantado."
            )
        if not elegido.listo(ahora):
            return ResultadoHuerto(
                bancal=bancal, listo_en=elegido.listo_en(),
                problema="Todavía no está listo.",
            )

        color = hue.color_sembrado(elegido.sembrado) or hue.tirar_color(rng)
        clave = hue.clave_de_poroto(color)
        lote = hue.tirar_cuantos(rng)
        arcoiris = hue.tirar_arcoiris(rng)

        # El arcoíris **sustituye** a uno del lote, no se suma: lo raro es que
        # salga, no que la cosecha rinda más de la cuenta.
        normales = lote - 1 if arcoiris else lote
        if normales:
            db.guardar_en_la_mochila_en(
                con, usuario_id, guild_id, clave, normales
            )
        if arcoiris:
            db.guardar_en_la_mochila_en(
                con, usuario_id, guild_id,
                hue.clave_de_poroto(hue.ARCOIRIS), 1,
            )
        db.arrancar_en(con, usuario_id, guild_id, elegido.casa_id, bancal)
        return ResultadoHuerto(
            ok=True, bancal=bancal, cosechado=clave, cuantos=normales,
            arcoiris=arcoiris,
        )


@dataclass(frozen=True)
class ResultadoCocina:
    ok: bool = False
    sopaipilla: obj.Objeto | None = None
    problema: str | None = None


def cocinar(
    usuario_id: str, guild_id: str, color: str, ahora: datetime | None = None,
    rng=None,
) -> ResultadoCocina:
    """Cambia porotos de un color por una sopaipilla de ese color.

    El arcoíris se cuece igual y cuesta lo mismo que los demás: lo que lo hace
    raro es encontrarlo, no cocinarlo. Lo que sí cambia es que **su dado se tira
    aquí**, porque no tiene color del que sacarlo; las de color lo consultan al
    comerse, en la tabla de gustos de quien se la come.
    """
    if color not in hue.COCINABLES:
        raise ValueError(f"color de poroto desconocido: {color!r}")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        if not db.gastar_en(
            con, usuario_id, guild_id, hue.clave_de_poroto(color),
            hue.POROTOS_POR_SOPAIPILLA,
        ):
            tengo = db._inventario(con, usuario_id, guild_id).get(
                hue.clave_de_poroto(color), 0
            )
            return ResultadoCocina(
                problema=(
                    f"Hacen falta {hue.POROTOS_POR_SOPAIPILLA} porotos "
                    f"{hue.plural_de(color)} y tienes {tengo}."
                ),
            )
        # El dado se tira con los porotos ya gastados: así una cocina que falla
        # por falta de ingredientes no consume una tirada.
        caras = hue.tirar_caras_de_arcoiris(rng) if color == hue.ARCOIRIS else 0
        sopaipilla = obj.CATALOGO[hue.clave_de_sopaipilla(color, caras)]
        db.guardar_en_la_mochila_en(
            con, usuario_id, guild_id, sopaipilla.clave
        )
        return ResultadoCocina(ok=True, sopaipilla=sopaipilla)


def equipar_cosmetico(
    usuario_id: str, guild_id: str, cosmetico: cos.Cosmetico
) -> ResultadoCosmetico:
    """Le pone al activo algo que ya tienes. No cobra nada.

    Exige tenerlo en el ropero, y eso se comprueba **dentro** de la transacción:
    un menú abierto hace dos minutos puede ofrecer algo que ya no está.
    """
    if cos.CATALOGO.get(cosmetico.clave) != cosmetico:
        raise ValueError("el cosmético no coincide con el catálogo actual")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo."
            )
        if cosmetico.clave not in db._ropero(con, usuario_id, guild_id):
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"No tienes **{cosmetico.nombre}** en tu ropero.",
            )
        if getattr(criatura, cosmetico.tipo) == cosmetico.clave:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"{sim.nombre_visible(criatura)} ya lo lleva puesto.",
            )

        vestido, sustituido = _vestir_en(
            con, criatura, cosmetico.tipo, cosmetico.clave
        )
        return ResultadoCosmetico(
            ok=True, criatura=vestido, saldo=saldo, sustituido=sustituido
        )


def quitar_cosmetico(
    usuario_id: str, guild_id: str, tipo: str
) -> ResultadoCosmetico:
    """Le quita una pieza al activo. Se queda en el ropero, no se pierde."""
    if tipo not in cos.TIPOS:
        raise ValueError(f"tipo de cosmético desconocido: {tipo!r}")

    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        saldo = _saldos_en(con, usuario_id, guild_id).asciigems
        criatura = db.criatura_activa_en(con, usuario_id, guild_id)
        if criatura is None:
            return ResultadoCosmetico(
                saldo=saldo, problema="No tienes ningún gachamon activo."
            )
        if getattr(criatura, tipo) is None:
            return ResultadoCosmetico(
                criatura=criatura, saldo=saldo,
                problema=f"{sim.nombre_visible(criatura)} no lleva nada de eso.",
            )

        desnudo, quitado = _vestir_en(con, criatura, tipo, None)
        return ResultadoCosmetico(
            ok=True, criatura=desnudo, saldo=saldo, sustituido=quitado
        )


def comprar(
    evento_id: str,
    usuario_id: str,
    guild_id: str,
    objeto: obj.Objeto,
    ahora: datetime | None = None,
) -> ResultadoCompra:
    """Decide, debita, entrega y registra una compra en una transacción."""
    if obj.CATALOGO.get(objeto.clave) != objeto:
        raise ValueError("el objeto no coincide exactamente con el catálogo actual")
    fecha = _fecha_economica(ahora or db.ahora_utc())
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        previa = con.execute(
            "SELECT resultado, solicitud FROM operaciones_economia "
            "WHERE evento_id = ? AND usuario_id = ? AND guild_id = ? "
            "AND tipo = 'compra'",
            (evento_id, usuario_id, guild_id),
        ).fetchone()
        if previa is not None:
            if previa["solicitud"] != objeto.clave:
                raise RuntimeError("el evento de compra pertenece a otro objeto")
            return ResultadoCompra(
                previa["resultado"] == "comprada",
                True,
                _saldos_en(con, usuario_id, guild_id),
                objeto.clave,
            )

        _asegurar_monedero(con, usuario_id, guild_id)
        debitada = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (objeto.precio, usuario_id, guild_id, objeto.precio),
        ).rowcount > 0
        resultado = "comprada" if debitada else "saldo_insuficiente"
        delta = -objeto.precio if debitada else 0
        if debitada:
            con.execute(
                "INSERT INTO inventario (usuario_id, guild_id, objeto, cantidad) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(usuario_id, guild_id, objeto) "
                "DO UPDATE SET cantidad = cantidad + 1",
                (usuario_id, guild_id, objeto.clave),
            )
        con.execute(
            "INSERT INTO operaciones_economia "
            "(evento_id, usuario_id, guild_id, tipo, fecha_utc, resultado, "
            "delta_asciicoins, solicitud) VALUES (?, ?, ?, 'compra', ?, ?, ?, ?)",
            (evento_id, usuario_id, guild_id, fecha, resultado, delta, objeto.clave),
        )
        return ResultadoCompra(
            debitada, False, _saldos_en(con, usuario_id, guild_id), objeto.clave
        )
