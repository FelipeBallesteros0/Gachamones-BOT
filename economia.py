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
import logros as lgr
import objetos as obj
import simulacion as sim

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
        avanzado = sim.avanzar(actual, ahora)
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
    con, usuario_id: str, guild_id: str, fecha: str, tipo: str
) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM operaciones_economia "
        "WHERE usuario_id = ? AND guild_id = ? AND fecha_utc = ? "
        "AND tipo = ? AND resultado = 'acreditada'",
        (usuario_id, guild_id, fecha, tipo),
    ).fetchone()[0]


def _resolver_recompensa(
    con, usuario_id: str, guild_id: str, fecha: str,
    tipo: str, monto: int, limite: int,
) -> tuple[int, int, bool]:
    usados = _contar_acreditadas(con, usuario_id, guild_id, fecha, tipo)
    acreditada = usados < limite
    delta = monto if acreditada else 0
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
    tipo: str, monto: int, limite: int, solicitud: str,
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


def _envolver_cuidado(
    resultado: sim.ResultadoAccion, *, delta: int = 0,
    delta_evolucion: int = 0, usados: int = 0,
    evolucion_usadas: int = 0, topada: bool = False,
    sin_efecto: bool = False,
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
        criatura = sim.avanzar(criatura, ahora)
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
            usados=usados,
            evolucion_usadas=evolucion_usadas,
            topada=topada,
        )


def _replay_competencia(
    con, evento_id: str, usuarios: tuple[str, ...],
    guild_id: str, solicitud: str,
) -> ResultadoCompetencia | None:
    filas = con.execute(
        "SELECT * FROM operaciones_economia WHERE evento_id = ? "
        "AND guild_id = ? AND tipo = 'competencia'",
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
            "SELECT resultado, delta_asciicoins FROM operaciones_economia "
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
                con, usuario_id, guild_id, fila["fecha_utc"], "competencia"
            ),
            evolucion_usadas=(
                _contar_acreditadas(
                    con, usuario_id, guild_id, fila["fecha_utc"], "evolucion"
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
        criaturas = tuple(sim.avanzar(criatura, ahora) for criatura in antes)
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

        stat = comp.STATS[tipo]
        encuentro = comp.enfrentar(
            [
                comp.competidor_de(
                    criatura, tipo,
                    db.efecto_activo_en(con, criatura.id, stat, ahora),
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
                stat,
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
        db.apuntar_en(
            con, campeon.id,
            lgr.CARRERAS if tipo == comp.CARRERA else lgr.SUMOS,
        )
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
    desde: cas.Casa | None = None       # de dónde viene; None es el refugio
    saldo: int = 0                      # asciicoins que quedan
    problema: str | None = None


def comprar_casa(
    usuario_id: str, guild_id: str, casa: cas.Casa,
    ahora: datetime | None = None,
) -> ResultadoMudanza:
    """Cobra los asciicoins y te muda, en una transacción.

    **Sólo se sube de tamaño.** Comprar la que ya tienes, o una menor, no cobra
    ni cambia nada: es el mismo cerrojo que el del ropero contra el doble clic,
    y además es lo que quiere quien juega — nadie compra una casa pequeña
    teniendo la grande.

    Se paga con asciicoins y no con gemas a propósito: las gemas están enteras
    comprometidas con los cosméticos, y los asciicoins hasta ahora sólo compraban
    pociones. Esto les da adónde ir.

    No lleva fila en `operaciones_economia` aunque sean asciicoins: allí se
    congela lo que pagó un evento que puede reprocesarse, y aquí el cerrojo es el
    tamaño — el segundo intento ya encuentra la casa puesta y no cobra.
    """
    if cas.CATALOGO.get(casa.clave) != casa:
        raise ValueError("la casa no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
        _asegurar_monedero(con, usuario_id, guild_id)
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins

        if not cas.puede_mudarse_a(hogar, casa):
            return ResultadoMudanza(
                casa=hogar.casa, desde=hogar.casa, saldo=saldo,
                problema=(
                    f"Ya vives en {hogar.casa.nombre}, que no es peor."
                    if hogar.casa else "Esa casa no existe."
                ),
            )

        pagado = con.execute(
            "UPDATE monederos SET asciicoins = asciicoins - ? "
            "WHERE usuario_id = ? AND guild_id = ? AND asciicoins >= ?",
            (casa.precio, usuario_id, guild_id, casa.precio),
        ).rowcount > 0
        saldo = _saldos_en(con, usuario_id, guild_id).asciicoins
        if not pagado:
            return ResultadoMudanza(
                casa=casa, desde=hogar.casa, saldo=saldo,
                problema=(
                    f"Te faltan {casa.precio - saldo} asciicoins. "
                    "Se ganan cuidando, evolucionando y compitiendo."
                ),
            )

        db.mudar_en(con, usuario_id, guild_id, casa.clave)
        return ResultadoMudanza(
            ok=True, casa=casa, desde=hogar.casa, saldo=saldo
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
    con, usuario_id: str, guild_id: str, ahora: datetime
) -> tuple[cas.Casa | None, dict[str, bool], str | None]:
    """La casa, lo que hay dentro, y por qué no se puede amueblar si no se puede.

    El refugio no se decora —es común y no es tuyo— y a la intemperie no hay
    dónde poner nada. Las dos cosas se comprueban aquí, en un solo sitio, porque
    las tres operaciones necesitan lo mismo.
    """
    hogar = db._hogar_de(con, usuario_id, guild_id, ahora)
    if hogar.casa is None:
        estorbo = (
            "El refugio no se puede amueblar: es de todos. Cómprate una casa."
            if hogar.estado(ahora) == cas.REFUGIO
            else "Estás a la intemperie. Cómprate una casa para amueblarla."
        )
        return None, {}, estorbo
    return hogar.casa, db._mobiliario(con, usuario_id, guild_id), None


def _recibo_mueble(
    con, usuario_id: str, guild_id: str, casa, mobiliario, mueble=None, ok=False,
    problema=None,
) -> ResultadoMueble:
    dentro = [c for c, puesto in mobiliario.items() if puesto]
    return ResultadoMueble(
        ok=ok, mueble=mueble, casa=casa,
        comodidad=cas.comodidad_de(casa, dentro) if casa else 0,
        puestos=len(dentro),
        saldo=_saldos_en(con, usuario_id, guild_id).asciicoins,
        problema=problema,
    )


def comprar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
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
            con, usuario_id, guild_id, ahora
        )
        _asegurar_monedero(con, usuario_id, guild_id)
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
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

        dentro = cas.caben_mas(
            casa, [c for c, puesto in mobiliario.items() if puesto]
        )
        db.comprar_mueble_en(con, usuario_id, guild_id, mueble.clave, dentro)
        mobiliario[mueble.clave] = dentro
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def colocar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
) -> ResultadoMueble:
    """Lo mete en la casa. Falla si no queda hueco, y lo dice con el número."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora
        )
        if estorbo:
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=estorbo,
            )
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
        dentro = [c for c, puesto in mobiliario.items() if puesto]
        if not cas.caben_mas(casa, dentro):
            return _recibo_mueble(
                con, usuario_id, guild_id, casa, mobiliario, mueble,
                problema=(
                    f"No cabe: {casa.nombre} tiene {casa.huecos} huecos y están "
                    "todos ocupados. Retira algo primero."
                ),
            )

        db.colocar_mueble_en(con, usuario_id, guild_id, mueble.clave, True)
        mobiliario[mueble.clave] = True
        return _recibo_mueble(
            con, usuario_id, guild_id, casa, mobiliario, mueble, ok=True
        )


def retirar_mueble(
    usuario_id: str, guild_id: str, mueble: cas.Mueble,
    ahora: datetime | None = None,
) -> ResultadoMueble:
    """Lo saca de la casa. Se guarda: nunca se pierde, como el ropero."""
    if cas.MUEBLES.get(mueble.clave) != mueble:
        raise ValueError("el mueble no coincide con el catálogo actual")

    ahora = ahora or db.ahora_utc()
    with db.conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        casa, mobiliario, estorbo = _estado_de_la_casa(
            con, usuario_id, guild_id, ahora
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
