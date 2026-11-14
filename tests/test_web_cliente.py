"""Lo que se puede vigilar del cliente leyendo sus archivos."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / "web" / "static"
GUIONES = sorted((ESTATICOS / "js").glob("*.js"))


def test_hay_guiones_que_mirar():
    assert {g.name for g in GUIONES} >= {
        "api.js", "pantallas.js", "dom.js", "dibujo.js", "entrada.js", "principal.js",
    }


def test_nada_entra_en_la_pagina_como_marcado():
    prohibido = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")
    culpables = [
        f"{g.name}:{n}" for g in GUIONES
        for n, linea in enumerate(g.read_text(encoding="utf-8").splitlines(), 1)
        if prohibido.search(linea)
    ]
    assert not culpables, culpables


def test_el_cliente_no_depende_de_nada_de_fuera():
    for archivo in [ESTATICOS / "index.html", ESTATICOS / "estilo.css", *GUIONES]:
        texto = archivo.read_text(encoding="utf-8")
        assert "http://" not in texto and "https://" not in texto, archivo.name


def test_la_portada_carga_sus_archivos_por_la_ruta_con_version():
    portada = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    assert "static/__V__/estilo.css" in portada
    assert "static/__V__/js/principal.js" in portada
    assert 'type="module"' in portada and 'lang="es"' in portada
    assert 'name="viewport"' in portada


def test_los_modulos_se_importan_con_rutas_relativas():
    importa = re.compile(r"""from\s+['"]([^'"]+)['"]""")
    for guion in GUIONES:
        for ruta in importa.findall(guion.read_text(encoding="utf-8")):
            assert ruta.startswith("./") and ruta.endswith(".js"), f"{guion.name}: {ruta}"


def test_el_aviso_del_codigo_esta_escrito():
    entrada = (ESTATICOS / "js" / "entrada.js").read_text(encoding="utf-8")
    assert "/vincular" in entrada
    assert "no se lo pases a nadie" in entrada.lower()


def test_ningun_texto_del_cliente_usa_los_nombres_viejos():
    for archivo in [ESTATICOS / "index.html", *GUIONES]:
        assert not re.search(r"ascii\s?(coin|gem)", archivo.read_text(encoding="utf-8"), re.I)


def test_la_pantalla_principal_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"lugar.js", "tiempo.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./lugar.js" in principal


def test_la_pantalla_principal_dice_desfallecido_y_no_inventa_errores_al_acariciar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "esfallecid" in lugar
    assert "acariciar" in lugar and "cuidar" in lugar
    assert "visibilitychange" in lugar


def test_el_estilo_piensa_en_el_celular_y_en_el_computador():
    estilo = (ESTATICOS / "estilo.css").read_text(encoding="utf-8")
    assert "min-width: 900px" in estilo
    assert "prefers-reduced-motion" in estilo


def test_el_avatar_ya_no_se_dibuja_con_codigo():
    dibujo = (ESTATICOS / "js" / "dibujo.js").read_text(encoding="utf-8")
    assert "dibujarAvatar" not in dibujo and "COLORES_DE_PIEL" not in dibujo
    for nombre in ("entrada.js", "lugar.js"):
        assert "./avatar.js" in (ESTATICOS / "js" / nombre).read_text(encoding="utf-8")


def test_el_arte_se_pide_por_la_ruta_con_version():
    arte = (ESTATICOS / "js" / "arte.js").read_text(encoding="utf-8")
    assert "import.meta.url" in arte


def test_el_mapa_esta_y_se_usa():
    nombres = {g.name for g in GUIONES}
    assert {"mapa.js", "pueblo.js", "arte.js", "avatar.js"} <= nombres
    principal = (ESTATICOS / "js" / "principal.js").read_text(encoding="utf-8")
    assert "./mapa.js" in principal


def test_el_mapa_no_lleva_el_pueblo_escrito_en_el_codigo():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    logica = (ESTATICOS / "js" / "pueblo.js").read_text(encoding="utf-8")
    assert "pueblo.json" in mapa
    for clave in ("incubadora", "cementerio", "estadio", "barrio"):
        assert clave not in mapa and clave not in logica


def test_el_boton_de_volver_dice_hacia_donde_con_lo_que_traen_los_datos():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "hacia" in mapa
    assert "Volver a ${" not in mapa


def test_el_mapa_pone_la_sombra_del_gachamon_con_su_pieza():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "efectos/sombra.png" in mapa


def test_el_mapa_se_puede_usar_sin_el_lienzo_y_respeta_a_quien_no_quiere_movimiento():
    mapa = (ESTATICOS / "js" / "mapa.js").read_text(encoding="utf-8")
    assert "aria-hidden" in mapa and "prefers-reduced-motion" in mapa
    assert "requestAnimationFrame" in mapa and "cancelAnimationFrame" in mapa


def test_desde_un_lugar_se_va_al_pueblo():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "vista: 'pueblo'" in lugar or 'vista: "pueblo"' in lugar


def test_la_pantalla_del_lugar_dice_donde_estas_y_avisa_lo_del_lugar():
    lugar = (ESTATICOS / "js" / "lugar.js").read_text(encoding="utf-8")
    assert "lugar.nombre" in lugar and "lugar.aviso" in lugar
    assert "escenas/" in lugar


# --- la Tienda -------------------------------------------------------------------

def _guion(nombre: str) -> str:
    return (ESTATICOS / "js" / nombre).read_text(encoding="utf-8")


def _sin_comentarios(codigo: str) -> str:
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"(^|\s)//.*$", r"\1", codigo, flags=re.M)


def test_la_tienda_esta_y_se_usa():
    assert {"tienda.js", "compras.js"} <= {g.name for g in GUIONES}
    principal = _guion("principal.js")
    assert "./tienda.js" in principal
    # Una fila más en la tabla de las pantallas.
    assert re.search(r"^\s*tienda:", principal, re.M)


def test_la_tienda_compra_con_reintentos_y_un_evento_por_toque():
    tienda = _guion("tienda.js")
    assert "conReintentos" in tienda and "nuevoEvento" in tienda
    assert "innerHTML" not in tienda and "http" not in tienda


def test_los_reintentos_viven_en_api_y_el_lugar_los_usa():
    assert re.search(r"export\s+(async\s+)?function\s+conReintentos\b", _guion("api.js"))
    lugar = _guion("lugar.js")
    assert not re.search(r"function\s+conReintentos\b", lugar)
    assert "conReintentos(" in lugar


def test_desde_la_tienda_del_pueblo_se_entra_a_comprar_y_la_ficha_dice_el_titulo():
    lugar = _guion("lugar.js")
    assert "vista: 'tienda'" in lugar or 'vista: "tienda"' in lugar
    assert "ofrece" in lugar
    assert re.search(r"\bg\.titulo\b|gachamon\.titulo\b", lugar)


def test_las_pantallas_de_la_tienda_no_escriben_precios_ni_claves_del_catalogo():
    import casas as cas
    import cosmeticos as cos
    import objetos as obj

    objetos, cosmeticos = obj.a_la_venta(), cos.CATALOGO.values()
    casas, muebles = cas.CATALOGO.values(), cas.MUEBLES.values()
    claves = {p.clave for p in (*objetos, *cosmeticos, *casas, *muebles)}
    precios = {p.precio for p in (*objetos, *cosmeticos, *casas, *muebles)}
    # `articulos.js` lleva lo que la tienda comparte con la mochila.
    for nombre in ("tienda.js", "compras.js", "articulos.js"):
        codigo = _sin_comentarios(_guion(nombre))
        citadas = set(re.findall(r"""['"`]([a-z0-9_]+)['"`]""", codigo))
        assert not citadas & claves, (nombre, citadas & claves)
        numeros = {int(n) for n in re.findall(r"(?<![\w.])\d+(?![\w.])", codigo)}
        assert not numeros & precios, (nombre, numeros & precios)


def test_una_compra_sin_respuesta_no_dice_que_no_se_compro_ni_deja_comprar_con_lo_de_antes():
    tienda = _sin_comentarios(_guion("tienda.js"))
    # Pudo haber llegado igual (sólo se perdió la respuesta), y vale para vender o mejorar.
    assert "No hubo respuesta. Revisa tu conexión." in tienda
    assert "No se pudo comprar" not in tienda
    # El catálogo sólo se pinta con lo que llega: de la respuesta o de una lectura.
    pintado_con = set(re.findall(r"ponerCatalogo\(([\w.]+)\)", tienda))
    assert pintado_con <= {"nuevo", "respuesta.tienda", "leido"}, pintado_con
    # Se relee con reintentos (la pieza común), y si tampoco llega, la tienda no carga.
    assert tienda.count(".releer()") == 1
    # Ni la tienda pide el catálogo por su cuenta, ni un «no» lo vuelve a pedir: la respuesta ya lo trae.
    assert "pedir('GET'" not in tienda and 'pedir("GET"' not in tienda


def _argumentos(codigo: str, desde: int) -> str:
    """Lo que va entre el paréntesis que abre en `desde - 1` y el que lo cierra."""
    nivel = 1
    for i in range(desde, len(codigo)):
        nivel += {"(": 1, ")": -1}.get(codigo[i], 0)
        if nivel == 0:
            return codigo[desde:i]
    raise AssertionError("paréntesis sin cerrar")


def test_el_evento_se_crea_una_vez_fuera_de_lo_que_se_reintenta():
    # Lo que impide cobrar, gastar o cuidar dos veces: los reintentos de un toque
    # llevan el mismo evento, creado antes y guardado en una constante.
    for nombre in ("tienda.js", "mochila.js", "lugar.js"):
        codigo = _sin_comentarios(_guion(nombre))
        llamadas = list(re.finditer(r"\bconReintentos\(", codigo))
        assert llamadas, nombre
        for llamada in llamadas:
            reintentado = _argumentos(codigo, llamada.end())
            assert "nuevoEvento" not in reintentado, (nombre, reintentado)
            usado = re.search(r"evento_id:\s*(\w+)", reintentado)
            assert usado, (nombre, reintentado)
            antes = codigo[:llamada.start()]
            funcion = list(re.finditer(r"\bfunction\s+\w+\s*\(", antes))
            assert funcion, nombre
            dentro = antes[funcion[-1].start():]
            assert re.search(rf"\bconst\s+{usado.group(1)}\s*=\s*nuevoEvento\(\)\s*;", dentro), (nombre, usado.group(1))


# --- la mochila ------------------------------------------------------------------

def test_la_mochila_esta_y_se_usa():
    assert "mochila.js" in {g.name for g in GUIONES}
    principal = _guion("principal.js")
    assert "./mochila.js" in principal
    # Una fila más en la tabla de las pantallas.
    assert re.search(r"^\s*mochila:", principal, re.M)


def test_la_mochila_usa_con_reintentos_y_un_evento_por_toque():
    mochila = _guion("mochila.js")
    assert "conReintentos" in mochila and "nuevoEvento" in mochila
    assert "innerHTML" not in mochila and "http" not in mochila


def test_el_uso_dice_a_que_gachamon_va_y_sus_reintentos_dicen_el_mismo():
    # El que la pantalla enseña, fijado en el cuerpo antes de reintentar, como el
    # evento: si el activo ya es otro, el servidor no se lo da al relevo.
    mochila = _sin_comentarios(_guion("mochila.js"))
    assert re.search(r"\bgachamon_id\b", mochila)
    for llamada in re.finditer(r"\bconReintentos\(", mochila):
        assert "gachamon" not in _argumentos(mochila, llamada.end())


def test_un_uso_sin_respuesta_no_dice_que_no_se_hizo_y_vuelve_a_pedir_la_lista():
    mochila = _guion("mochila.js")
    # Pudo haberse usado igual: la frase no lo niega, y lo de antes no se repinta.
    assert "No hubo respuesta. Revisa tu conexión." in mochila
    assert "No se pudo usar" not in mochila
    assert ".releer()" in mochila
    # La relectura se reintenta, en la pieza que comparte con la tienda.
    assert "conReintentos(" in _guion("articulos.js")


def test_desde_cualquier_lugar_se_abre_la_mochila():
    lugar = _guion("lugar.js")
    assert "vista: 'mochila'" in lugar or 'vista: "mochila"' in lugar


def test_ningun_archivo_del_cliente_escribe_una_clave_del_catalogo_de_objetos():
    import objetos as obj

    claves = set(obj.CATALOGO)
    for archivo in [ESTATICOS / "index.html", *GUIONES]:
        codigo = _sin_comentarios(archivo.read_text(encoding="utf-8"))
        # El nombre de una clase de CSS (la placa del bautizo) no es una cosa del catálogo.
        codigo = re.sub(r"""\bclass\s*[:=]\s*(['"])[^'"]*\1""", "", codigo)
        citadas = set(re.findall(r"""['"`]([a-z0-9_]+)['"`]""", codigo))
        assert not citadas & claves, (archivo.name, citadas & claves)


# --- la ficha y el ropero --------------------------------------------------------

def test_la_ficha_y_el_ropero_estan_y_se_usan():
    assert {"ficha.js", "ropero.js"} <= {g.name for g in GUIONES}
    principal = _guion("principal.js")
    for nombre in ("ficha", "ropero"):
        assert f"./{nombre}.js" in principal
        # Una fila más en la tabla de las pantallas.
        assert re.search(rf"^\s*{nombre}:", principal, re.M), nombre


def test_la_ficha_y_el_ropero_no_meten_marcado_ni_dependen_de_fuera():
    for nombre in ("ficha.js", "ropero.js"):
        codigo = _guion(nombre)
        assert "innerHTML" not in codigo, nombre
        assert "http://" not in codigo and "https://" not in codigo, nombre


def test_del_lugar_se_abre_la_ficha_de_la_ficha_el_ropero_y_del_ropero_se_vuelve_a_la_ficha():
    assert "Ver ficha" in _guion("lugar.js")
    assert "vista: 'ficha'" in _guion("lugar.js")
    assert "vista: 'ropero'" in _guion("ficha.js")
    assert "vista: 'ficha'" in _guion("ropero.js")


def test_el_ropero_viste_al_gachamon_de_la_pantalla_al_poner_y_al_quitar():
    ropero = _sin_comentarios(_guion("ropero.js"))
    assert "'ropero/poner'" in ropero and "'ropero/quitar'" in ropero
    llamadas = list(re.finditer(r"\bconReintentos\(", ropero))
    assert llamadas
    for llamada in llamadas:
        reintentado = _argumentos(ropero, llamada.end())
        # El cuerpo se arma una vez, antes de reintentar, y lleva el gachamon.
        enviado = re.search(r"pedir\('POST',\s*\w+,\s*(\w+)\)", reintentado)
        assert enviado, reintentado
        assert "gachamon" not in reintentado
        antes = ropero[:llamada.start()]
        funcion = list(re.finditer(r"\bfunction\s+\w+\s*\(", antes))
        assert funcion
        dentro = antes[funcion[-1].start():]
        cuerpo = enviado.group(1)
        assert re.search(rf"\bconst\s+{cuerpo}\s*=\s*\{{[^;]*\bgachamon_id:\s*gachamonId\b", dentro), dentro


def test_el_ropero_y_la_ficha_no_escriben_claves_del_catalogo_de_cosmeticos():
    import cosmeticos as cos

    claves = set(cos.CATALOGO)
    for nombre in ("ficha.js", "ropero.js"):
        codigo = _sin_comentarios(_guion(nombre))
        citadas = set(re.findall(r"""['"`]([a-z0-9_]+)['"`]""", codigo))
        assert not citadas & claves, (nombre, citadas & claves)


def test_las_frases_de_la_ficha_y_del_ropero_son_las_del_plan():
    ficha = _guion("ficha.js")
    for frase in ("Estadísticas", "Experiencia: ", " para el nivel ", "Medallas de ", "Tuyas",
                  " si se muere; las tuyas se quedan.", "Ropero"):
        assert frase in ficha, frase
    ropero = _guion("ropero.js")
    for frase in ("Sombreros", "Títulos", "Poner", "Quitar", "Lo lleva ",
                  "Tu ropero está vacío. Los sombreros y los títulos se compran en la tienda, con gemas."):
        assert frase in ropero, frase


def test_la_ficha_dice_lo_que_lleva_y_de_quien_son_las_medallas_con_su_genero():
    ficha = _guion("ficha.js")
    assert "Lleva " in ficha and "Las de " in ficha
    # El pie concuerda con el gachamon: «se van con él» o «se van con ella».
    assert re.search(r"se van con \$\{[^}]*'él'[^}]*'ella'[^}]*\} si se muere", ficha)


def test_la_ficha_y_el_ropero_vuelven_a_decidir_si_llega_otro_gachamon():
    # El ropero viste al gachamon que enseña el estado: si lo que llega es de
    # otro (cambió en otra pestaña o en Discord), se vuelve a decidir.
    for nombre in ("ficha.js", "ropero.js"):
        codigo = _sin_comentarios(_guion(nombre))
        assert re.search(
            r"\b\w+\.gachamon\.id\s*!==\s*(estado\.gachamon\.id|gachamonId)\)\s*\{\s*irse\(\);", codigo,
        ), nombre


def test_tras_releer_el_ropero_no_enfoca_nada_si_ya_se_fue():
    # Releer puede acabar en irse (llegó otro gachamon): entonces no se enfoca
    # un botón de una pantalla que se deja.
    ropero = _sin_comentarios(_guion("ropero.js"))
    releidas = re.findall(r"if \(await laLista\.releer\(\)[^)]*\)", ropero)
    assert releidas
    for releida in releidas:
        assert "sigueAqui()" in releida, releida


# --- la incubadora y el refugio --------------------------------------------------

def test_la_incubadora_esta_y_se_usa():
    assert "incubadora.js" in {g.name for g in GUIONES}
    principal = _guion("principal.js")
    assert "./incubadora.js" in principal
    # Una fila más en la tabla de las pantallas.
    assert re.search(r"^\s*incubadora:", principal, re.M)


def test_la_incubadora_no_mete_marcado_ni_depende_de_fuera():
    incubadora = _guion("incubadora.js")
    assert "innerHTML" not in incubadora
    assert "http" not in incubadora


def test_la_incubadora_manda_el_gachamon_de_la_fila_al_sacar_y_al_bautizar():
    # El cuerpo se arma una vez, antes de reintentar, y lleva el gachamon de la fila.
    incubadora = _sin_comentarios(_guion("incubadora.js"))
    mandadas = set()
    for llamada in re.finditer(r"\bconReintentos\(", incubadora):
        reintentado = _argumentos(incubadora, llamada.end())
        enviado = re.search(r"pedir\('POST',\s*'([\w/]+)',\s*(\w+)\)", reintentado)
        if not enviado:
            continue
        mandadas.add(enviado.group(1))
        assert "gachamon" not in reintentado, reintentado
        antes = incubadora[:llamada.start()]
        funcion = list(re.finditer(r"\bfunction\s+\w+\s*\(", antes))
        assert funcion
        dentro = antes[funcion[-1].start():]
        cuerpo = enviado.group(2)
        assert re.search(rf"\bconst\s+{cuerpo}\s*=\s*\{{[^;]*\bgachamon_id:", dentro), dentro
    assert mandadas == {"incubadora/sacar", "bautizar"}


def test_un_toque_de_la_incubadora_en_camino_no_deja_salir_otro_y_ya_bautizado_no_es_un_error():
    incubadora = _sin_comentarios(_guion("incubadora.js"))
    for nombre in ("sacar", "bautizar"):
        cuerpo = re.search(rf"async function {nombre}\([^)]*\)\s*\{{\s*if \(enCamino\) return;\s*enCamino = true;", incubadora)
        assert cuerpo, nombre
    # Un segundo envío del mismo nombre contesta `ya_bautizado`: ya está hecho.
    assert "'ya_bautizado'" in incubadora


def test_la_incubadora_vuelve_a_decidir_si_llega_otro_gachamon():
    incubadora = _sin_comentarios(_guion("incubadora.js"))
    assert re.search(r"\.id\s*!==\s*gachamonId\)\s*\{\s*irse\(\);", incubadora)
    releidas = re.findall(r"if \(await laLista\.releer\(\)[^)]*\)", incubadora)
    assert releidas
    for releida in releidas:
        assert "sigueAqui()" in releida, releida


def test_las_frases_de_la_incubadora_del_refugio_y_del_recluta_son_las_del_plan():
    incubadora = _guion("incubadora.js")
    for frase in ("'Incubadora'", "'Sin nombre'", "'Activo'", "'Sacar'", "'Ponerle nombre'",
                  "'¿Cómo se va a llamar?'", "'Ponerle este nombre'", " · nivel ${",
                  "`Aquí esperan los gachamones que no son el activo. Ahora sólo tienes a ${",
                  "`Caben ${", "} gachamones.`"):
        assert frase in incubadora, frase
    lugar = _guion("lugar.js")
    for frase in ("'Tu plantel'", "'Viven aquí'", "'Ninguno de tus gachamones vive aquí.'", "vista: 'incubadora'",
                  "ofreceLaIncubadora("):
        assert frase in lugar, frase
    assert "} espera en la incubadora y todavía no tiene nombre.`" in _guion("entrada.js")
