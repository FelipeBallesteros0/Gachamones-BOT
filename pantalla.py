"""Dibuja la pantalla de la mascota como texto de Discord.

Módulo puro: recibe una `Criatura` y devuelve una cadena lista para enviar.

Cómo se aprovecha el markdown de Discord
----------------------------------------
* El arte y las barras van dentro de un bloque ```ansi, que es el único sitio
  donde Discord respeta el espaciado Y admite color.
* Dentro de ese bloque NO se renderiza más markdown, así que el nombre y los
  avisos van fuera: `##` de encabezado arriba y `-#` (subtexto) abajo.
* Nada de emoji dentro del bloque: Discord los sustituye por imágenes de ancho
  variable y descuadra el marco. Dentro sólo ASCII y caracteres de caja.

Todas las filas se construyen con trozos de longitud fija y además pasan por
`_fila()`, que recorta o rellena a lo ancho exacto. Así ni un nombre larguísimo
ni un dibujo mal medido pueden romper el marco.
"""
from __future__ import annotations

import textwrap
from datetime import datetime, timedelta

import especies as esp
import personalidad as per
import simulacion as sim

# Va siempre FUERA del bloque ```ansi: dentro, Discord sustituye el emoji por
# una imagen de ancho variable y descuadra el marco. Por eso el género no sale
# en `/jardin`, `/ranking` ni `/cementerio`, que se dibujan enteros dentro.
EMOJI_GENERO = {esp.MACHO: "♂️", esp.HEMBRA: "♀️"}

# Por lo mismo, la poción activa y la incubadora se anuncian en el subtexto y
# nunca dentro del marco.
EMOJI_POCION = "⚗️"
EMOJI_INCUBADORA = "🥚"

ANCHO = 26          # espacio interior del marco
ANCHO_BARRA = 12
ANCHO_BARRA_XP = 10  # más corta: el número «524/525» ocupa siete caracteres
ALTO_ARTE = 7       # fijo, para que la caja no cambie de tamaño entre estados

RESET = "\x1b[0m"


def recibo(*partes: str) -> str:
    """Subtexto compacto con las partes mecánicas no vacías."""
    return "-# " + " · ".join(parte for parte in partes if parte)


def _c(texto: str, color: str) -> str:
    return f"\x1b[0;{color}m{texto}{RESET}"


def _fila(contenido: str) -> str:
    """Encaja una línea *sin códigos de color* en el marco."""
    return f"│{contenido[:ANCHO].ljust(ANCHO)}│"


# Nombres públicos para que `competir.py` dibuje sus marcos con las mismas
# piezas y no acabemos con dos anchos distintos.
fila = _fila
pintar = _c


def _color_barra(valor: float) -> str:
    """Los umbrales salen de `simulacion` porque además de pintar deciden
    cuándo se puede alimentar de urgencia: tienen que ser el mismo número."""
    if valor >= sim.UMBRAL_BARRA_BIEN:
        return esp.VERDE
    if valor >= sim.UMBRAL_BARRA_MAL:
        return esp.AMARILLO
    return esp.ROJO


def _fila_barra(etiqueta: str, valor: float) -> str:
    """Fila de barra. Las piezas tienen largo fijo, así que el ancho cuadra
    aunque el color meta caracteres invisibles."""
    llenas = round(valor / 100 * ANCHO_BARRA)
    llenas = max(0, min(ANCHO_BARRA, llenas))
    barra = "█" * llenas + "░" * (ANCHO_BARRA - llenas)
    # 1 + 7 + 1 + ANCHO_BARRA + 1 + 3 + 1 == ANCHO
    izq = f" {etiqueta.ljust(7)} "
    der = f" {round(valor):>3} "
    return f"│{izq}{_c(barra, _color_barra(valor))}{der}│"


def _fila_experiencia(criatura: sim.Criatura) -> str:
    """Cuánto falta para la siguiente evolución.

    Enseña «12/25» en vez de un porcentaje: como el objetivo cambia en cada
    etapa (25, 100, 250, 525), un «48 %» no dice si faltan trece puntos o
    doscientos setenta.

    Va en cian fijo y no con `_color_barra()`, que es la escala de bienestar:
    aplicada aquí saldría al revés, y una criatura recién evolucionada —con la
    barra a cero— aparecería en rojo justo en su mejor momento.
    """
    objetivo = sim.xp_para_subir(criatura.nivel)
    llenas = round(criatura.xp / objetivo * ANCHO_BARRA_XP) if objetivo else 0
    llenas = max(0, min(ANCHO_BARRA_XP, llenas))
    barra = "█" * llenas + "░" * (ANCHO_BARRA_XP - llenas)

    # 1 + 4 + 1 + ANCHO_BARRA_XP + 1 + 8 + 1 == ANCHO
    izq = f" {'EXP'.ljust(4)} "
    der = f" {f'{criatura.xp}/{objetivo}':>8} "
    return f"│{izq}{_c(barra, esp.CIAN)}{der}│"


def _fila_stats(criatura: sim.Criatura) -> str:
    """La fila de FUE / VEL / SAL, la misma en las tres pantallas.

    El ancho del número sale de los propios valores en vez de estar fijo en dos
    cifras: así, cuando una estadística pasa de 99, la fila apreta el hueco
    entre columnas en vez de que `_fila()` recorte el último número. Con dos
    cifras —el caso de siempre— el resultado es carácter por carácter el de
    antes, así que ninguna criatura cambia de aspecto por esto.
    """
    valores = (criatura.fuerza, criatura.velocidad, criatura.salud)
    ancho = max(2, len(str(max(valores))))
    piezas = [f"{etiqueta} {valor:>{ancho}}"
              for etiqueta, valor in zip(("FUE", "VEL", "SAL"), valores)]
    # Lo que sobra tras los dos espacios de los bordes se reparte entre los dos
    # huecos. Con estadísticas de dos cifras da 3, que es la separación de toda
    # la vida; con tres cifras da 1 y sigue cabiendo.
    hueco = " " * max(1, (ANCHO - 2 - sum(len(p) for p in piezas)) // 2)
    return _fila(" " + hueco.join(piezas) + " ")


def _lineas_arte(arte: str, color: str) -> list[str]:
    """Centra el dibujo y lo rellena hasta `ALTO_ARTE` líneas.

    El `dedent` quita la sangría que el dibujo arrastra del código fuente. Sin
    él se sumaría al margen de centrado y todo saldría escorado a la derecha.
    Como sólo elimina el prefijo *común*, la forma interna queda intacta.
    """
    lineas = [ln.rstrip() for ln in textwrap.dedent(arte.strip("\n")).split("\n")]
    while len(lineas) < ALTO_ARTE:
        # Repartir el hueco: primero abajo, luego arriba.
        if (ALTO_ARTE - len(lineas)) % 2 == 1:
            lineas.append("")
        else:
            lineas.insert(0, "")
    lineas = lineas[:ALTO_ARTE]

    ancho_dibujo = max((len(ln) for ln in lineas), default=0)
    margen = max(0, (ANCHO - ancho_dibujo) // 2)

    salida = []
    for ln in lineas:
        if not ln:
            salida.append(_fila(""))  # sin códigos de color en las líneas vacías
            continue
        cuerpo = (" " * margen + ln)[:ANCHO]
        relleno = ANCHO - len(cuerpo)
        salida.append(f"│{_c(cuerpo, color)}{' ' * relleno}│")
    return salida


def formato_espera(restante: timedelta) -> str:
    """'listo', '12 min' o '1 h 20 min'."""
    segundos = int(restante.total_seconds())
    if segundos <= 0:
        return "listo"
    minutos = (segundos + 59) // 60
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h" if resto == 0 else f"{horas} h {resto} min"


def _formato_edad(horas: float) -> str:
    if horas < 1:
        return "recién nacida"
    if horas < 24:
        return f"{int(horas)} h de vida"
    dias = horas / 24
    return f"{int(dias)} día{'s' if int(dias) != 1 else ''} de vida"


ACCIONES_EN_FICHA = (*sim.ACCIONES_DE_CUIDADO, sim.COMPETIR, sim.AVENTURA)

ICONOS_ACCION = {
    sim.ALIMENTAR: "🍖",
    sim.JUGAR: "🎮",
    sim.ENTRENAR: "🏋️",
    sim.LIMPIAR: "🧼",
    sim.COMPETIR: "🏁",
    sim.AVENTURA: "🧭",
}


def render(
    criatura: sim.Criatura,
    ahora: datetime,
    esperas: dict[str, timedelta] | None = None,
    aviso: str = "",
    efectos: dict[str, tuple[int, timedelta]] | None = None,
    en_la_incubadora: int = 0,
) -> str:
    """Pantalla completa de una criatura viva o muerta."""
    if not criatura.viva:
        return render_lapida(criatura, ahora)

    definicion = criatura.def_especie
    etapa = criatura.etapa
    arte = esp.arte_de(definicion, etapa, criatura.animo_visual)

    cuerpo = ["╭" + "─" * ANCHO + "╮"]
    cuerpo += _lineas_arte(arte, definicion.color)
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila_barra("COMIDA", criatura.hambre))
    cuerpo.append(_fila_barra("ÁNIMO", criatura.animo))
    cuerpo.append(_fila_barra("ASEO", criatura.limpieza))
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila_stats(criatura))
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila_experiencia(criatura))
    cuerpo.append("╰" + "─" * ANCHO + "╯")

    cabecera = [
        f"## {definicion.emoji} {criatura.nombre} {EMOJI_GENERO[criatura.genero]}",
        f"-# {definicion.nombre} · {per.nombre_caracter(criatura)}"
        f" · {esp.nombre_etapa(etapa, criatura.genero)} · nivel {criatura.nivel}"
        f" · {criatura.victorias}V-{criatura.derrotas}D"
        f" · {_formato_edad(criatura.edad_horas(ahora))}",
    ]
    if aviso:
        cabecera.append(f"> {aviso}")

    partes = cabecera + ["```ansi", "\n".join(cuerpo), "```"]

    if esperas:
        trozos = []
        for accion, restante in esperas.items():
            if accion not in ICONOS_ACCION:
                continue
            # Si la acción se puede hacer aunque el reloj siga corriendo, poner
            # «en 12 min» sería mentira: el botón funciona.
            texto = (
                "¡tiene hambre!"
                if sim.puede_saltarse_espera(criatura, accion)
                else formato_espera(restante)
            )
            trozos.append(f"{ICONOS_ACCION[accion]} {texto}")
        if trozos:
            partes.append("-# " + " · ".join(trozos))

    # Las pociones activas van FUERA del bloque. Dentro, Discord cambia el emoji
    # por una imagen de ancho variable y descuadra el marco; aquí además no hay
    # que medir nada, que es de donde han salido todos los descuadres.
    if efectos:
        partes.append("-# " + " · ".join(
            f"{EMOJI_POCION} +{bonus} {stat} · {formato_espera(restante)}"
            for stat, (bonus, restante) in sorted(efectos.items())
        ))

    if en_la_incubadora:
        cuantos = "1 espera" if en_la_incubadora == 1 else f"{en_la_incubadora} esperan"
        partes.append(
            f"-# {EMOJI_INCUBADORA} {cuantos} en la incubadora · «Cambiar» para sacarl"
            + ("o" if en_la_incubadora == 1 else "os")
        )

    return "\n".join(partes)


def render_lapida(criatura: sim.Criatura, ahora: datetime) -> str:
    definicion = criatura.def_especie
    vivio = (criatura.muerta_en or ahora) - criatura.nacida_en
    horas = vivio.total_seconds() / 3600.0

    cuerpo = ["╭" + "─" * ANCHO + "╮"]
    cuerpo += _lineas_arte(esp.LAPIDA, esp.GRIS)
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila(f" {criatura.nombre[:ANCHO - 2]} "))
    cuerpo.append(_fila(f" {definicion.nombre} · nivel {criatura.nivel} "))
    cuerpo.append(_fila(f" {criatura.victorias} victorias "))
    cuerpo.append("╰" + "─" * ANCHO + "╯")

    return "\n".join([
        f"## 🪦 {criatura.nombre} {EMOJI_GENERO[criatura.genero]}",
        f"-# {definicion.nombre} · {per.nombre_caracter(criatura)}"
        f" · vivió {_formato_edad(horas).replace(' de vida', '')}"
        f" · murió de {criatura.causa_muerte or 'vieja'}",
        "```ansi",
        "\n".join(cuerpo),
        "```",
        "-# Usa `/huevo` para empezar de nuevo.",
    ])


def render_evolucion(
    criatura: sim.Criatura, etapa_anterior: str, subidas: tuple[str, ...] = ()
) -> str:
    """El anuncio de que la criatura ha cambiado de etapa.

    Enseña el dibujo nuevo y qué ha ganado. Es el momento que justifica toda la
    mecánica de niveles, así que va en su propio mensaje y no de pasada.
    """
    definicion = criatura.def_especie
    etapa = criatura.etapa
    ultima = etapa == esp.ETAPAS[-1]

    cuerpo = ["╭" + "─" * ANCHO + "╮"]
    cuerpo += _lineas_arte(esp.arte_de(definicion, etapa, esp.FELIZ), definicion.color)
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila_stats(criatura))
    cuerpo.append("╰" + "─" * ANCHO + "╯")

    ganado = ""
    if subidas:
        cuenta: dict[str, int] = {}
        for stat in subidas:
            cuenta[stat] = cuenta.get(stat, 0) + 1
        ganado = " · ".join(f"+{n} {stat}" for stat, n in cuenta.items())

    titulo = (
        f"## ✨ ¡{criatura.nombre} ha alcanzado su forma final!"
        if ultima else
        f"## ✨ ¡{criatura.nombre} ha evolucionado!"
    )
    detalle = (
        f"-# De {esp.nombre_etapa(etapa_anterior, criatura.genero)}"
        f" a **{esp.nombre_etapa(etapa, criatura.genero)}**"
        f" · nivel {criatura.nivel}"
    )
    if ultima:
        detalle += f" · ahora es un **{definicion.evolucion}**"

    partes = [titulo, detalle, "```ansi", "\n".join(cuerpo), "```"]
    if ganado:
        partes.append(f"-# {ganado}")
    return "\n".join(partes)


def render_revelacion(criatura: sim.Criatura, ahora: datetime) -> str:
    """Lo que sale del cascarón, antes de tener nombre.

    Enseña la especie y la tirada de estadísticas, que es lo emocionante de
    abrir un huevo, y deja el bautizo para el botón.
    """
    definicion = criatura.def_especie

    cuerpo = ["╭" + "─" * ANCHO + "╮"]
    cuerpo += _lineas_arte(esp.arte_de(definicion, esp.BEBE), definicion.color)
    cuerpo.append("├" + "─" * ANCHO + "┤")
    cuerpo.append(_fila_stats(criatura))
    cuerpo.append("╰" + "─" * ANCHO + "╯")

    rareza = "" if definicion.rareza == esp.COMUN else f" · **{definicion.rareza}**"

    return "\n".join([
        f"## {definicion.emoji} ¡Ha salido {definicion.articulo} {definicion.nombre}! "
        f"{EMOJI_GENERO[criatura.genero]}{rareza}",
        f"-# {definicion.descripcion}",
        "```ansi",
        "\n".join(cuerpo),
        "```",
        f"-# Es {per.nombre_caracter(criatura)}. Aguantará unas "
        f"{int(sim.horas_de_vida(criatura.salud))} h sin comer. "
        "Ahora ponle nombre.",
    ])


def render_huevo(rajado: bool = False) -> str:
    arte = esp.HUEVO_RAJADO if rajado else esp.HUEVO
    cuerpo = ["╭" + "─" * ANCHO + "╮"]
    cuerpo += _lineas_arte(arte, esp.BLANCO)
    cuerpo.append("╰" + "─" * ANCHO + "╯")
    texto = (
        "Algo se mueve ahí dentro..."
        if not rajado
        else "¡El cascarón se está rompiendo!"
    )
    return "\n".join([
        "## 🥚 Un huevo",
        f"-# {texto}",
        "```ansi",
        "\n".join(cuerpo),
        "```",
    ])
