"""Cliente de IA: limpieza de respuestas y que nunca deje a la criatura muda.

Ni un solo test toca la red: el transporte se inyecta.
"""
import asyncio
from datetime import datetime, timezone

import pytest

import especies as esp
import ia
import personalidad as per
import simulacion as sim

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    """Los tests del camino de fallo no tienen por qué esperar el reintento,
    y cada uno arranca con el modelo preferido.

    Se le da clave a todos los proveedores porque los modelos de uno sin clave
    se saltan solos: sin esto, los tests de rotación y castigos medirían el
    filtro de claves en vez de lo suyo. Que ese filtro funciona lo comprueba su
    propio test.
    """
    monkeypatch.setattr(ia, "SEGUNDOS_ENTRE_INTENTOS", 0)
    monkeypatch.setattr(ia.config, "PROVEEDORES", {
        nombre: ia.config.Proveedor(
            nombre=proveedor.nombre, url=proveedor.url,
            api_key=proveedor.api_key or "clave-de-prueba",
            extras=proveedor.extras,
        )
        for nombre, proveedor in ia.config.PROVEEDORES.items()
    })
    ia.reiniciar_modelos()
    yield
    ia.reiniciar_modelos()


def criatura(**cambios) -> sim.Criatura:
    base = dict(
        id=1, usuario_id="u1", guild_id="g1", especie="pollito", nombre="Pelusa",
        nacida_en=T0, actualizada_en=T0,
        base_fuerza=15, base_velocidad=15, base_salud=15,
    )
    base.update(cambios)
    return sim.Criatura(**base)


def respuesta_de(texto):
    async def transporte(cuerpo):
        return {"choices": [{"message": {"content": texto}}]}
    return transporte


async def transporte_roto(cuerpo):
    raise ia.ErrorTransitorio("HTTP 503: congestionado")


def correr(corrutina):
    return asyncio.run(corrutina)


def identificador(cuerpo) -> str:
    """El modelo tal como se configura, a partir del nombre pelado del cuerpo.

    En `MODELO_IA` los modelos llevan su proveedor delante —«deepseek:...»— pero
    ese prefijo es nuestro y no sale a la red: al proveedor se le manda sólo el
    nombre que él conoce. Los tests razonan en identificadores, así que aquí se
    traduce de vuelta.
    """
    pelado = cuerpo["model"]
    for configurado in ia.config.MODELOS_IA:
        if ia.config.resolver_modelo(configurado)[1] == pelado:
            return configurado
    return pelado


# --- Limpieza --------------------------------------------------------------

def test_quita_el_nombre_que_el_modelo_antepone():
    """El modelo a veces contesta como un guion de teatro: «Pelusa: ¡pío!»."""
    assert ia.limpiar("Pelusa: ¡Pío pío!", "Pelusa") == "¡Pío pío!"
    assert ia.limpiar("Pelusa - ¡Pío!", "Pelusa") == "¡Pío!"


def test_no_se_come_el_nombre_si_forma_parte_de_la_frase():
    assert ia.limpiar("Pelusa se llama Pelusa, pío", "Pelusa") == \
        "Pelusa se llama Pelusa, pío"


def test_quita_markdown_pero_respeta_los_asteriscos_del_personaje():
    """*chisp* es la muletilla de Pyro: no se puede borrar."""
    assert "*chisp*" in ia.limpiar("*chisp* ¡Oye!", "Ceniza")
    assert ia.limpiar("## Hola\n- una cosa", "X") == "Hola\nuna cosa"


def test_quita_las_negritas_sin_tocar_los_asteriscos_sueltos():
    """El modelo mete negritas pese a las instrucciones, y en Discord se ven."""
    assert ia.limpiar("**Kuro: ¡Pío!** corre.", "X") == "Kuro: ¡Pío! corre."
    assert ia.limpiar("*chisp* y **fuerte**", "X") == "*chisp* y fuerte"


def test_quita_bloques_de_codigo():
    assert "```" not in ia.limpiar("Pío\n```python\nprint(1)\n```", "Pelusa")


def test_junta_las_lineas_en_blanco_de_sobra():
    assert ia.limpiar("Pío.\n\n\n\nPío otra vez.", "Pelusa") == \
        "Pío.\nPío otra vez."


def test_recorta_las_respuestas_larguisimas_por_una_frase():
    largo = ("Pío pío pío. " * 200)
    limpio = ia.limpiar(largo, "Pelusa")
    assert len(limpio) <= ia.LARGO_MAXIMO
    assert limpio.endswith(".")


def test_recorta_aunque_no_haya_donde_cortar():
    limpio = ia.limpiar("a" * 2000, "Pelusa")
    assert len(limpio) <= ia.LARGO_MAXIMO + 1
    assert limpio.endswith("…")


# --- Llamada ---------------------------------------------------------------

def test_una_respuesta_buena_llega_limpia():
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola",
        transporte=respuesta_de("  ¡Pío! Hola.  "),
    ))
    assert texto == "¡Pío! Hola."
    assert de_la_ia


def test_el_prompt_y_el_historial_llegan_en_orden():
    visto = {}

    async def espia(cuerpo):
        visto.update(cuerpo)
        return {"choices": [{"message": {"content": "pío"}}]}

    historial = [
        {"role": "user", "content": "me llamo felipe"},
        {"role": "assistant", "content": "¡pío! hola felipe"},
    ]
    correr(ia.responder(criatura(), T0, "felipe", historial, "te acuerdas?",
                        transporte=espia))

    mensajes = visto["messages"]
    assert mensajes[0]["role"] == "system"
    assert "Pelusa" in mensajes[0]["content"]
    assert mensajes[1:3] == historial
    assert mensajes[-1] == {"role": "user", "content": "te acuerdas?"}


def test_se_desactiva_el_modo_de_razonamiento():
    """Pensar aquí sólo añade segundos: son tres líneas en boca de un pollito.

    Cada proveedor lo apaga con su campo, así que se comprueba contra el del
    modelo que haya tocado en vez de contra uno fijo. En DeepSeek además se
    cobra, y sin apagarlo se comería los MAX_TOKENS razonando."""
    visto = {}

    async def espia(cuerpo):
        visto.update(cuerpo)
        return {"choices": [{"message": {"content": "pío"}}]}

    correr(ia.responder(criatura(), T0, "felipe", [], "hola", transporte=espia))
    proveedor, _ = ia.config.resolver_modelo(ia._modelos_a_probar()[0])
    assert proveedor.extras, "algo tiene que apagar el razonamiento"
    for campo, valor in proveedor.extras.items():
        assert visto[campo] == valor
    assert visto["max_tokens"] == ia.MAX_TOKENS


# --- Que nunca se quede muda -----------------------------------------------

def test_si_la_api_falla_contesta_con_su_frase_de_respaldo():
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte_roto,
    ))
    assert not de_la_ia
    assert texto in per.VOCES["pollito"].respaldo


def test_un_error_permanente_no_se_reintenta():
    """Regresión de producción: NVIDIA marcó el modelo como DEGRADED y devolvía
    400 al instante. Reintentarlo 3 veces con espera creciente convertía un
    fallo inmediato en 65 s de «escribiendo…» antes de la frase de respaldo.
    Para quien hablaba con su criatura, el bot parecía muerto."""
    intentos = []

    async def degradado(cuerpo):
        intentos.append(identificador(cuerpo))
        raise ia.ErrorPermanente("HTTP 400: DEGRADED function cannot be invoked")

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=degradado,
    ))
    assert not de_la_ia
    # Un intento por modelo, nunca dos veces el mismo.
    assert len(intentos) == len(set(intentos))


def test_un_modelo_degradado_hace_que_se_pruebe_el_siguiente():
    """La defensa de verdad: si NVIDIA degrada un modelo, el bot se pasa al
    siguiente solo, sin esperar a que alguien lo redespliegue."""
    vistos = []

    async def solo_funciona_el_segundo(cuerpo):
        vistos.append(identificador(cuerpo))
        if len(vistos) == 1:
            raise ia.ErrorPermanente("HTTP 400: DEGRADED")
        return {"choices": [{"message": {"content": "¡Pío!"}}]}

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=solo_funciona_el_segundo,
    ))
    assert de_la_ia
    assert texto == "¡Pío!"
    assert vistos == [ia.config.MODELOS_IA[0], ia.config.MODELOS_IA[1]]


def test_hay_mas_de_un_modelo_configurado():
    assert len(ia.config.MODELOS_IA) >= 2


def test_reintenta_una_vez_antes_de_rendirse():
    intentos = []

    async def falla_solo_la_primera(cuerpo):
        intentos.append(1)
        if len(intentos) == 1:
            raise ia.ErrorTransitorio("caída pasajera")
        return {"choices": [{"message": {"content": "¡Pío!"}}]}

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=falla_solo_la_primera,
    ))
    assert de_la_ia
    assert texto == "¡Pío!"
    assert len(intentos) == 2


def test_un_timeout_tampoco_la_deja_muda():
    async def se_cuelga(cuerpo):
        raise asyncio.TimeoutError()

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=se_cuelga,
    ))
    assert not de_la_ia
    assert texto.strip()


def test_una_respuesta_vacia_cuenta_como_fallo():
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=respuesta_de("   "),
    ))
    assert not de_la_ia
    assert texto.strip()


def test_una_respuesta_con_forma_rara_no_rompe_nada():
    async def rara(cuerpo):
        return {"algo": "inesperado"}

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=rara,
    ))
    assert not de_la_ia
    assert texto.strip()


def test_sin_key_configurada_usa_el_respaldo_sin_llamar_a_nadie(monkeypatch):
    monkeypatch.setattr(ia.config, "IA_ACTIVA", False)
    texto, de_la_ia = correr(
        ia.responder(criatura(), T0, "felipe", [], "hola")
    )
    assert not de_la_ia
    assert texto in per.VOCES["pollito"].respaldo


def test_cada_especie_cae_en_su_propio_respaldo():
    for clave in ("chispa", "pedrusco", "fantasma"):
        c = criatura(especie=clave)
        texto, _ = correr(ia.responder(
            c, T0, "felipe", [], "hola", transporte=transporte_roto,
        ))
        # Concordadas: la de Pyro lleva marca de género («ocupad{o/a}»).
        esperadas = [esp.concordar(f, c.genero) for f in per.VOCES[clave].respaldo]
        assert texto in esperadas


# --- Generación suelta (la usa el jardín) ----------------------------------

def test_generar_devuelve_lo_que_dice_el_modelo():
    texto, de_la_ia = correr(ia.generar(
        "eres un narrador", "cuenta algo", "respaldo",
        transporte=respuesta_de("Nube le da un zarpazo a Kuro."),
    ))
    assert de_la_ia
    assert texto == "Nube le da un zarpazo a Kuro."


def test_generar_manda_sistema_y_peticion_en_orden():
    visto = {}

    async def espia(cuerpo):
        visto.update(cuerpo)
        return {"choices": [{"message": {"content": "algo"}}]}

    correr(ia.generar("SISTEMA", "PETICION", "respaldo", transporte=espia))
    assert visto["messages"] == [
        {"role": "system", "content": "SISTEMA"},
        {"role": "user", "content": "PETICION"},
    ]


def test_generar_cae_en_el_respaldo_que_le_pasen():
    texto, de_la_ia = correr(ia.generar(
        "sistema", "peticion", "el jardín está tranquilo",
        transporte=transporte_roto,
    ))
    assert not de_la_ia
    assert texto == "el jardín está tranquilo"


def test_generar_no_se_come_un_guion_inicial():
    """Sin nombre que quitar, el patrón de prefijo vacío se llevaba por delante
    cualquier guion al principio de la frase."""
    texto, _ = correr(ia.generar(
        "s", "p", "respaldo", transporte=respuesta_de("— Nube bufa."),
    ))
    assert "Nube bufa" in texto


def test_el_respaldo_va_rotando():
    c = criatura()
    frases = {
        correr(ia.responder(c, T0, "felipe", [], "hola",
                            transporte=transporte_roto, semilla=i))[0]
        for i in range(3)
    }
    assert len(frases) == 3


# --- La respuesta vacía no puede tumbar la cadena --------------------------

def transporte_por_modelo(por_modelo):
    """Transporte que se comporta distinto según el modelo que le pidan.

    El valor puede ser una excepción a lanzar, el texto a devolver, o un dict
    crudo para simular una respuesta con forma rara.
    """
    llamadas = []

    async def transporte(cuerpo):
        modelo = identificador(cuerpo)
        llamadas.append(modelo)
        que = por_modelo[modelo]
        if isinstance(que, Exception):
            raise que
        if isinstance(que, dict):
            return que
        return {"choices": [{"message": {"content": que}}]}

    transporte.llamadas = llamadas
    return transporte


def test_una_respuesta_vacia_no_abandona_la_cadena_de_modelos():
    """Regresión de lo que le pasó a John Bazooka. `pedir()` lanzaba un `ErrorIA`
    de la clase base, que no era ni transitorio ni permanente, así que caía en el
    cajón de sastre de `_intentar()` y se rendía en el acto: ni reintentaba ni
    probaba los otros dos modelos. Una respuesta vacía es ruido pasajero."""
    preferido, *resto = ia.config.MODELOS_IA
    transporte = transporte_por_modelo({
        preferido: "",                       # vacía: el caso real
        resto[0]: "¡Pío! Aquí estoy.",
        resto[1]: "no debería hacer falta",
    })

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))

    assert de_la_ia, "se rindió y sirvió la frase de respaldo"
    assert texto == "¡Pío! Aquí estoy."
    # Se va por rondas: el preferido falla una vez y se pasa al siguiente en el
    # acto, en vez de gastar en él los tres intentos teniendo un recambio sano.
    assert transporte.llamadas == [preferido, resto[0]], transporte.llamadas


def test_una_respuesta_con_forma_rara_tampoco_la_abandona():
    preferido, *resto = ia.config.MODELOS_IA
    transporte = transporte_por_modelo({
        preferido: {"lo_que_sea": "sin choices"},
        resto[0]: "¡Pío! Aquí estoy.",
        resto[1]: "no debería hacer falta",
    })
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert de_la_ia and texto == "¡Pío! Aquí estoy."


def test_un_error_permanente_sigue_saltando_de_modelo_al_instante():
    """Lo contrario: aquí insistir sí es tirar el tiempo de quien escribió."""
    preferido, *resto = ia.config.MODELOS_IA
    transporte = transporte_por_modelo({
        preferido: ia.ErrorPermanente("HTTP 400: DEGRADED"),
        resto[0]: "¡Pío!",
        resto[1]: "tampoco hace falta",
    })
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert de_la_ia and texto == "¡Pío!"
    assert transporte.llamadas.count(preferido) == 1, "reintentó un fallo permanente"


def test_con_todo_roto_sigue_sin_lanzar_y_contesta_de_su_cosecha():
    transporte = transporte_por_modelo(
        {m: ia.ErrorIA("vacía") for m in ia.config.MODELOS_IA})
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert not de_la_ia
    assert texto in [esp.concordar(f, esp.MACHO)
                     for f in per.VOCES["pollito"].respaldo]


def test_el_presupuesto_de_tiempo_se_respeta():
    """El tope es de tiempo y no de intentos porque el fallo real de este
    endpoint es tardar, no negarse: John esperó 58 s y 76 s con el
    «escribiendo...» puesto para acabar recibiendo la frase de respaldo."""
    import time as reloj

    async def transporte_colgado(cuerpo):
        await asyncio.sleep(10)  # más que cualquier límite del test

    ia.SEGUNDOS_PRESUPUESTO, presupuesto = 0.3, ia.SEGUNDOS_PRESUPUESTO
    ia.SEGUNDOS_TIMEOUT, limite = 0.1, ia.SEGUNDOS_TIMEOUT
    try:
        t0 = reloj.monotonic()
        texto, de_la_ia = correr(ia.responder(
            criatura(), T0, "felipe", [], "hola", transporte=transporte_colgado))
        transcurrido = reloj.monotonic() - t0
    finally:
        ia.SEGUNDOS_PRESUPUESTO, ia.SEGUNDOS_TIMEOUT = presupuesto, limite

    assert not de_la_ia          # acaba en respaldo, como debe
    assert texto.strip()         # pero nunca muda
    assert transcurrido < 1.0, f"se pasó del presupuesto: {transcurrido:.2f}s"


def test_un_transporte_lento_pero_dentro_de_plazo_sí_contesta():
    """El presupuesto no puede cortar una respuesta buena que sólo va lenta."""
    async def transporte_lento(cuerpo):
        await asyncio.sleep(0.05)
        return {"choices": [{"message": {"content": "¡Pío! Perdona la tardanza."}}]}

    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte_lento))
    assert de_la_ia and texto == "¡Pío! Perdona la tardanza."


# --- Nunca publicar una frase a medias -------------------------------------

def respuesta_cortada(texto, razon="length"):
    async def transporte(cuerpo):
        return {"choices": [{"message": {"content": texto},
                             "finish_reason": razon}]}
    return transporte


def pedir_con(transporte):
    return correr(ia.pedir([{"role": "user", "content": "hola"}], transporte))


def test_una_respuesta_cortada_se_deja_en_la_ultima_frase_entera():
    """Regresión con el texto exacto que salió en Discord, cortado donde se
    acabaron los tokens. Publicar eso queda peor que decir una frase menos.

    Los puntos suspensivos cuentan como final bueno: son la muletilla de
    Duskhouse y de Magora, así que cortar ahí conserva más y suena natural."""
    texto = pedir_con(respuesta_cortada(
        "Pío... ¿ya volviste con esas preguntas? Pío pío... ¡hasta cuándo"))
    assert texto == "Pío... ¿ya volviste con esas preguntas? Pío pío..."
    assert "hasta cuándo" not in texto


def test_el_corte_respeta_los_signos_de_cierre_del_castellano():
    texto = pedir_con(respuesta_cortada(
        "¡Pío! Estoy bien comido. ¿Y tú qué tal, Don Exo"))
    assert texto == "¡Pío! Estoy bien comido."


def test_si_acaba_bien_no_se_toca_aunque_venga_marcada_como_cortada():
    """El modelo puede quedarse sin tokens justo después de un punto."""
    texto = pedir_con(respuesta_cortada("¡Pío! Estoy bien comido."))
    assert texto == "¡Pío! Estoy bien comido."


def test_una_respuesta_completa_no_se_recorta_nunca():
    """Sin `finish_reason: length` el texto va tal cual, aunque no lleve punto
    final: hay criaturas que hablan así (Duskhouse deja frases en el aire)."""
    texto = pedir_con(respuesta_cortada("Iba a decirte algo importante y",
                                        razon="stop"))
    assert texto == "Iba a decirte algo importante y"


def test_sin_finish_reason_se_supone_completa():
    """Los transportes de los tests no lo mandan, y la API tampoco siempre."""
    texto = pedir_con(respuesta_de("¡Pío! sin finish_reason"))
    assert texto == "¡Pío! sin finish_reason"


def test_un_corte_sin_ninguna_frase_entera_acaba_en_puntos_pero_no_vacio():
    texto = pedir_con(respuesta_cortada("Pío pío estaba pensando que quizá"))
    assert texto.endswith("…")
    assert "quizá" in texto


def test_el_recorte_por_largo_sigue_funcionando_igual():
    """Las dos reglas comparten la misma función de cortar por frase."""
    largo = ("¡Pío! " + "Corro y picoteo sin parar. " * 40)
    limpio = ia.limpiar(largo, "Pelusa")
    assert len(limpio) <= ia.LARGO_MAXIMO
    assert limpio.endswith(".")


# --- El presupuesto no puede dejar sin turno a los otros modelos -----------

def test_un_primer_modelo_colgado_no_impide_probar_los_demas():
    """Regresión de producción: el presupuesto de 90 s se lo comían los tres
    intentos del primer modelo (3 x 30 s), así que la cadena de recambio no se
    alcanzaba nunca. En el log salían seis fallos seguidos del mismo modelo
    mientras deepseek contestaba en 1,3 s sin que nadie se lo pidiera."""
    preferido, segundo, *_ = ia.config.MODELOS_IA
    probados = []

    async def transporte(cuerpo):
        probados.append(identificador(cuerpo))
        if identificador(cuerpo) == preferido:
            await asyncio.sleep(10)          # se cuelga, como en producción
        return {"choices": [{"message": {"content": "¡Pío! Aquí estoy."}}]}

    ia.SEGUNDOS_TIMEOUT, limite = 0.05, ia.SEGUNDOS_TIMEOUT
    ia.SEGUNDOS_PRESUPUESTO, presupuesto = 0.15, ia.SEGUNDOS_PRESUPUESTO
    try:
        texto, de_la_ia = correr(ia.responder(
            criatura(), T0, "felipe", [], "hola", transporte=transporte))
    finally:
        ia.SEGUNDOS_TIMEOUT, ia.SEGUNDOS_PRESUPUESTO = limite, presupuesto

    assert segundo in probados, f"sólo probó {set(probados)}"
    assert de_la_ia, "se rindió con la frase de respaldo teniendo recambios sanos"
    assert texto == "¡Pío! Aquí estoy."


def test_el_recambio_entra_a_la_primera_ronda_no_a_la_cuarta():
    """Antes de dar un segundo intento a nadie, todos tienen que haber tenido
    el primero: si el preferido está muerto, insistir es tirar el presupuesto."""
    preferido = ia.config.MODELOS_IA[0]
    probados = []

    async def transporte(cuerpo):
        probados.append(identificador(cuerpo))
        raise ia.ErrorTransitorio("congestionado")

    correr(ia.responder(criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert probados[:len(ia.config.MODELOS_IA)] == list(ia.config.MODELOS_IA), \
        probados[:len(ia.config.MODELOS_IA) + 2]
    assert probados.count(preferido) == ia.INTENTOS


# --- Un modelo que acaba de fallar se aparta un rato ------------------------

def contador_por_modelo(sanos):
    """Transporte que sólo contesta con los modelos de `sanos`."""
    orden = []

    async def transporte(cuerpo):
        modelo = identificador(cuerpo)
        orden.append(modelo)
        if modelo not in sanos:
            raise ia.ErrorTransitorio("colgado")
        return {"choices": [{"message": {"content": "¡Pío!"}}]}

    transporte.orden = orden
    return transporte


def test_el_modelo_que_acaba_de_fallar_va_el_ultimo_la_proxima_vez():
    """Los fallos de este endpoint van a rachas: cuando uno se cuelga, se cuelga
    varios minutos seguidos. Sin esto, cada mensaje de la racha vuelve a pagar
    el plazo entero antes de caer en un modelo sano."""
    preferido, segundo, *_ = ia.config.MODELOS_IA
    transporte = contador_por_modelo({segundo})

    correr(ia.responder(criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert transporte.orden[0] == preferido        # la primera vez sí lo prueba

    transporte.orden.clear()
    correr(ia.responder(criatura(), T0, "felipe", [], "otra", transporte=transporte))
    assert transporte.orden[0] == segundo, transporte.orden
    assert preferido not in transporte.orden, "no debería hacer falta probarlo"


def test_acertar_le_quita_el_castigo_al_modelo():
    """Sólo se perdona al que contesta, así que el escenario es: el castigado
    va el último, los otros fallan, le toca a él y acierta. A partir de ahí
    vuelve a ser el primero."""
    preferido = ia.config.MODELOS_IA[0]
    ia._penalizar(preferido, 30)
    assert ia._modelos_a_probar()[0] != preferido

    transporte = contador_por_modelo({preferido})
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))

    assert de_la_ia and texto == "¡Pío!"
    assert transporte.orden[-1] == preferido, "debería probarse el último"
    assert ia._modelos_a_probar()[0] == preferido, "sigue castigado tras acertar"


def test_el_castigo_caduca_solo():
    preferido = ia.config.MODELOS_IA[0]
    ia._penalizar(preferido, 0)      # caducado al instante
    assert ia._modelos_a_probar()[0] == preferido


def test_aunque_esten_todos_castigados_se_siguen_probando_todos():
    """Nunca puede quedarse sin modelos: castigado significa «el último», no
    «fuera de la lista»."""
    for m in ia.config.MODELOS_IA:
        ia._penalizar(m, 30)
    assert sorted(ia._modelos_a_probar()) == sorted(ia.config.MODELOS_IA)

    transporte = contador_por_modelo({ia.config.MODELOS_IA[-1]})
    texto, de_la_ia = correr(ia.responder(
        criatura(), T0, "felipe", [], "hola", transporte=transporte))
    assert de_la_ia and texto == "¡Pío!"


def test_un_degradado_se_aparta_mucho_mas_que_un_colgado():
    """Un DEGRADED de NVIDIA duró horas; una racha de timeouts, minutos."""
    preferido = ia.config.MODELOS_IA[0]

    async def degradado(cuerpo):
        if identificador(cuerpo) == preferido:
            raise ia.ErrorPermanente("HTTP 400: DEGRADED")
        return {"choices": [{"message": {"content": "¡Pío!"}}]}

    correr(ia.responder(criatura(), T0, "felipe", [], "hola", transporte=degradado))
    castigo = ia._penalizado_hasta[preferido] - ia.time.monotonic()
    assert castigo > ia.MINUTOS_PENALIZACION * 60


# --- Notas del modelo que no son parte de la escena ------------------------

def test_se_quita_la_nota_de_recuento_del_final():
    """Visto en un /jardin publicado: el modelo terminaba la escena y añadía
    «(Palabras: 40).» en una línea aparte, haciéndole caso al límite del prompt
    como si fuera un formulario."""
    escena = ("Haki bufa y se encorva para embestir, pero Rimuru lo derriba.\n"
              "(Palabras: 40).")
    assert ia.limpiar(escena, "") == \
        "Haki bufa y se encorva para embestir, pero Rimuru lo derriba."


def test_se_quita_la_nota_aunque_no_lleve_punto():
    assert ia.limpiar("Kuro corre por el jardín.\n(40 words)", "") == \
        "Kuro corre por el jardín."


def test_no_se_toca_un_parentesis_que_forma_parte_de_la_frase():
    """«(plop)» y «(se cae)» son narración, no anotaciones: van dentro."""
    escena = "Rimuru rebota (plop) y se queda mirando."
    assert ia.limpiar(escena, "") == escena


def test_no_se_toca_una_acotacion_del_personaje():
    """La muletilla de Pyro y las acotaciones con asteriscos se quedan."""
    assert ia.limpiar("*chisp* No me toques.", "") == "*chisp* No me toques."


def test_si_la_nota_era_todo_lo_que_habia_no_queda_texto():
    """Y entonces `generar()` cae en la frase de respaldo, que es lo correcto."""
    assert ia.limpiar("(Palabras: 40).", "") == ""


# --- Generación en crudo (la usan las escenas de la aventura) ---------------

def test_generar_crudo_no_limpia_el_json():
    """`limpiar` está hecho para frases: quita bloques de código y marcas, y con
    un objeto JSON haría destrozos. Por eso las escenas no pasan por ahí."""
    json = '{"situacion": "Un muro **viejo**", "fuerza": "Empujar"}'

    devuelto = correr(ia.generar_crudo("sistema", "peticion",
                                       transporte=respuesta_de(json)))

    assert devuelto == json


def test_generar_crudo_devuelve_nada_si_falla_el_modelo():
    """`None` es la señal de tirar del respaldo escrito; no lanza, como todo el
    módulo."""
    assert correr(ia.generar_crudo(
        "sistema", "peticion", transporte=transporte_roto
    )) is None


# --- Varios proveedores a la vez -------------------------------------------
#
# El motivo: DeepSeek de pago para la prosa y NVIDIA gratis de red. Antes había
# una sola URL y una sola clave para toda la lista, así que era o uno o el otro.

class SesionFalsa:
    """Apunta a dónde y con qué credenciales sale cada petición."""

    def __init__(self):
        self.enviados = []

    def post(self, url, *, headers, json, timeout):
        self.enviados.append({"url": url, "headers": headers, "cuerpo": json})

        class Respuesta:
            status = 200

            async def json(self):
                return {"choices": [{"message": {"content": "hola"}}]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

        return Respuesta()


@pytest.fixture
def dos_proveedores(monkeypatch):
    """Un DeepSeek de pago y un NVIDIA gratuito, como quedará en producción."""
    deepseek = ia.config.Proveedor(
        nombre="deepseek",
        url="https://api.deepseek.com/chat/completions",
        api_key="clave-deepseek",
        extras={"thinking": {"type": "disabled"}},
    )
    nvidia = ia.config.Proveedor(
        nombre="nvidia",
        url="https://integrate.api.nvidia.com/v1/chat/completions",
        api_key="clave-nvidia",
        extras={"chat_template_kwargs": {"thinking": False}},
    )
    monkeypatch.setattr(
        ia.config, "PROVEEDORES", {"deepseek": deepseek, "nvidia": nvidia}
    )
    monkeypatch.setattr(ia.config, "MODELOS_IA", (
        "deepseek:deepseek-v4-pro",
        "nvidia:mistralai/mistral-nemotron",
    ))
    sesion = SesionFalsa()

    async def compartida():
        return sesion

    monkeypatch.setattr(ia, "_sesion_compartida", compartida)
    return sesion


def test_cada_modelo_va_a_la_url_de_su_proveedor_con_su_clave(dos_proveedores):
    """Es el motivo entero del cambio: con una sola URL global, mezclar
    proveedores era imposible."""
    correr(ia.pedir([{"role": "user", "content": "hola"}],
                    modelo="deepseek:deepseek-v4-pro"))
    correr(ia.pedir([{"role": "user", "content": "hola"}],
                    modelo="nvidia:mistralai/mistral-nemotron"))

    primero, segundo = dos_proveedores.enviados
    assert primero["url"] == "https://api.deepseek.com/chat/completions"
    assert primero["headers"]["Authorization"] == "Bearer clave-deepseek"
    assert segundo["url"].startswith("https://integrate.api.nvidia.com")
    assert segundo["headers"]["Authorization"] == "Bearer clave-nvidia"


def test_el_proveedor_no_viaja_dentro_del_nombre_del_modelo(dos_proveedores):
    """El prefijo es nuestro, no suyo: DeepSeek no conoce ningún
    «deepseek:deepseek-v4-pro»."""
    correr(ia.pedir([{"role": "user", "content": "hola"}],
                    modelo="deepseek:deepseek-v4-pro"))

    assert dos_proveedores.enviados[0]["cuerpo"]["model"] == "deepseek-v4-pro"


def test_a_deepseek_se_le_apaga_el_razonamiento(dos_proveedores):
    """Sin esto la integración no funciona: `thinking` viene en `high` por
    defecto, y v4-pro se gastaría los 1200 tokens razonando sin llegar a
    contestar —el fallo que `pedir` ya sabe describir— pagando por tokens que
    nadie lee. Cada proveedor lo apaga a su manera."""
    correr(ia.pedir([{"role": "user", "content": "hola"}],
                    modelo="deepseek:deepseek-v4-pro"))
    correr(ia.pedir([{"role": "user", "content": "hola"}],
                    modelo="nvidia:mistralai/mistral-nemotron"))

    a_deepseek, a_nvidia = (e["cuerpo"] for e in dos_proveedores.enviados)
    assert a_deepseek["thinking"] == {"type": "disabled"}
    assert "chat_template_kwargs" not in a_deepseek

    assert a_nvidia["chat_template_kwargs"] == {"thinking": False}
    assert "thinking" not in a_nvidia


def test_un_modelo_sin_prefijo_sigue_siendo_de_nvidia():
    """Compatibilidad: los `.env` de ahora no llevan prefijo y tienen que
    seguir funcionando igual."""
    proveedor, nombre = ia.config.resolver_modelo("mistralai/mistral-nemotron")

    assert proveedor.nombre == "nvidia"
    assert nombre == "mistralai/mistral-nemotron"
    # Y el nombre de NVIDIA lleva una barra, que no puede confundirse con el
    # separador de proveedor.
    assert ia.config.resolver_modelo("deepseek:deepseek-v4-pro")[1] == "deepseek-v4-pro"


def test_un_proveedor_desconocido_no_tumba_el_bot():
    """Una errata en el `.env` no puede dejar mudas a las criaturas: se trata
    como un modelo de NVIDIA y, si no existe, la cadena de recambio hace el
    resto."""
    proveedor, nombre = ia.config.resolver_modelo("inventado:loquesea")

    assert proveedor.nombre == "nvidia"
    assert nombre == "inventado:loquesea"


def test_si_deepseek_se_cae_contesta_nvidia(monkeypatch, dos_proveedores):
    """La red de seguridad: se paga por la prosa buena, pero quedarse mudo no es
    una opción."""
    vistos = []

    async def transporte(cuerpo):
        vistos.append(identificador(cuerpo))
        if identificador(cuerpo) == "deepseek:deepseek-v4-pro":
            raise ia.ErrorTransitorio("HTTP 503")
        return {"choices": [{"message": {"content": "Pío pío."}}]}

    texto, de_la_ia = correr(ia.generar(
        "sistema", "peticion", "respaldo", transporte=transporte
    ))

    assert de_la_ia and texto == "Pío pío."
    assert vistos == ["deepseek:deepseek-v4-pro", "nvidia:mistralai/mistral-nemotron"]


def test_sin_clave_de_un_proveedor_sus_modelos_se_quedan_fuera(monkeypatch):
    """Mientras no pagues, la lista con DeepSeek delante no puede hacer perder
    un intento contra un 401 seguro."""
    sin_clave = ia.config.Proveedor(
        nombre="deepseek", url="https://api.deepseek.com/chat/completions",
        api_key="", extras={},
    )
    con_clave = ia.config.Proveedor(
        nombre="nvidia", url="https://integrate.api.nvidia.com/v1/chat/completions",
        api_key="clave", extras={},
    )
    monkeypatch.setattr(
        ia.config, "PROVEEDORES", {"deepseek": sin_clave, "nvidia": con_clave}
    )
    monkeypatch.setattr(ia.config, "MODELOS_IA", (
        "deepseek:deepseek-v4-pro", "nvidia:mistralai/mistral-nemotron",
    ))

    assert ia._modelos_a_probar() == ["nvidia:mistralai/mistral-nemotron"]


def test_la_narracion_del_viaje_tiene_mas_sitio_que_una_respuesta_de_mascota():
    """Medido: con el tope de la charla se recortaban 7 de cada 10 narraciones,
    y lo que se perdía era el final —donde se cuenta si encontraste algo—."""
    largo = "Cruzan el río. " * 50  # 750 caracteres

    de_charla = ia.limpiar(largo, "")
    de_viaje = ia.limpiar(largo, "", ia.LARGO_MAXIMO_NARRACION)

    assert len(de_charla) <= ia.LARGO_MAXIMO
    assert len(de_charla) < len(de_viaje) <= ia.LARGO_MAXIMO_NARRACION


def test_limpiar_sigue_recortando_como_siempre_si_no_le_dicen_otra_cosa():
    """El parámetro es opcional: los dieciséis sitios que ya la llamaban no
    cambian de comportamiento."""
    assert len(ia.limpiar("Pío pío. " * 200, "Pelusa")) <= ia.LARGO_MAXIMO


def test_generar_le_pasa_el_tope_que_le_pidan():
    largo = "Cruzan el río. " * 50

    corto, _ = correr(ia.generar("s", "p", "respaldo",
                                 transporte=respuesta_de(largo)))
    ancho, _ = correr(ia.generar("s", "p", "respaldo",
                                 transporte=respuesta_de(largo),
                                 largo_maximo=ia.LARGO_MAXIMO_NARRACION))

    assert len(corto) <= ia.LARGO_MAXIMO < len(ancho)
