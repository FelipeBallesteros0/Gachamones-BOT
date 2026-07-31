"""Lectura del .env, sobre todo la lista de canales."""
import pytest

import config


def lista(valor, monkeypatch):
    monkeypatch.setenv("CANALES_PRUEBA", valor)
    return config._lista_enteros("CANALES_PRUEBA")


def test_un_solo_canal(monkeypatch):
    assert lista("123456789012345678", monkeypatch) == (123456789012345678,)


def test_varios_canales_separados_por_comas(monkeypatch):
    assert lista("111,222,333", monkeypatch) == (111, 222, 333)


def test_tolera_espacios_saltos_y_punto_y_coma(monkeypatch):
    """Es lo que sale al pegar varios IDs copiados de Discord a mano."""
    assert lista(" 111 , 222;333 ,\n444 ", monkeypatch) == (111, 222, 333, 444)


def test_ignora_comas_sobrantes(monkeypatch):
    assert lista(",111,,222,", monkeypatch) == (111, 222)


def test_quita_repetidos_conservando_el_orden(monkeypatch):
    """El primero es el canal principal, así que el orden importa."""
    assert lista("333,111,333,222", monkeypatch) == (333, 111, 222)


def test_vacio_da_lista_vacia(monkeypatch):
    assert lista("", monkeypatch) == ()
    monkeypatch.delenv("CANALES_PRUEBA", raising=False)
    assert config._lista_enteros("CANALES_PRUEBA") == ()


def test_un_valor_que_no_es_id_avisa_con_claridad(monkeypatch):
    """El error típico: pegar el nombre del canal en vez de su ID."""
    with pytest.raises(ValueError) as fallo:
        lista("111,#general", monkeypatch)
    assert "#general" in str(fallo.value)
    assert "CANALES_PRUEBA" in str(fallo.value)


def test_el_canal_principal_es_el_primero(monkeypatch):
    canales = lista("777,888", monkeypatch)
    assert canales[0] == 777


def test_el_modelo_razonador_va_el_ultimo_de_la_cadena():
    """Con 300 tokens devolvía el contenido vacío 4 de cada 4 veces: se gasta
    más de mil caracteres razonando en inglés antes de contestar. Sigue en la
    lista como tercer recambio, pero no puede ser el primero al que se cae."""
    razonador = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    assert razonador in config.MODELOS_IA
    assert config.MODELOS_IA[-1] == razonador
    # Cuatro desde que DeepSeek de pago entró delante; sin clave se salta solo.
    assert len(config.MODELOS_IA) == 4


# --- Proveedores de IA ------------------------------------------------------

def proveedores(monkeypatch, **claves):
    """Sustituye la tabla de proveedores por una con las claves que se pidan."""
    tabla = {
        nombre: config.Proveedor(
            nombre=nombre, url=f"https://{nombre}.example/v1", api_key=clave,
        )
        for nombre, clave in claves.items()
    }
    monkeypatch.setattr(config, "PROVEEDORES", tabla)
    return tabla


def test_el_prefijo_manda_el_modelo_a_su_proveedor(monkeypatch):
    proveedores(monkeypatch, nvidia="a", deepseek="b")

    proveedor, nombre = config.resolver_modelo("deepseek:deepseek-v4-pro")

    assert proveedor.nombre == "deepseek"
    assert nombre == "deepseek-v4-pro"


def test_sin_prefijo_va_a_nvidia(monkeypatch):
    """Los `.env` anteriores no lo llevan y tienen que seguir funcionando."""
    proveedores(monkeypatch, nvidia="a", deepseek="b")

    proveedor, nombre = config.resolver_modelo("mistralai/mistral-nemotron")

    assert proveedor.nombre == "nvidia"
    assert nombre == "mistralai/mistral-nemotron"


def test_un_prefijo_con_erratas_no_deja_muda_a_la_criatura(monkeypatch):
    """Se trata como nombre y sale por NVIDIA: fallará ese modelo y la cadena de
    recambio hará el resto, que es mejor que no hablar por una letra de más."""
    proveedores(monkeypatch, nvidia="a", deepseek="b")

    proveedor, nombre = config.resolver_modelo("depseek:deepseek-v4-pro")

    assert proveedor.nombre == "nvidia"
    assert nombre == "depseek:deepseek-v4-pro"


def test_la_ia_esta_activa_si_hay_clave_de_algun_modelo_configurado(monkeypatch):
    def activa(modelos, **claves):
        proveedores(monkeypatch, **claves)
        return any(config.resolver_modelo(m)[0].api_key for m in modelos)

    assert not activa(("deepseek:pro", "mistralai/x"), nvidia="", deepseek="")
    assert activa(("deepseek:pro", "mistralai/x"), nvidia="", deepseek="b")
    assert activa(("deepseek:pro", "mistralai/x"), nvidia="a", deepseek="")
    # Tener clave de un proveedor que no usas no hace hablar a nadie.
    assert not activa(("mistralai/x",), nvidia="", deepseek="b")


def test_deepseek_va_delante_pero_sin_clave_no_estorba():
    """Así basta con poner la clave en el .env para que mande, sin tener que
    editar MODELO_IA en cada máquina. Sin clave se salta solo y la lista se
    comporta igual que antes de que existiera DeepSeek."""
    import ia

    assert config.MODELOS_IA[0] == "deepseek:deepseek-v4-pro"
    assert config.resolver_modelo(config.MODELOS_IA[0])[0].nombre == "deepseek"
    # Y los recambios gratuitos siguen ahí detrás.
    assert any(
        config.resolver_modelo(m)[0].nombre == "nvidia"
        for m in config.MODELOS_IA[1:]
    )
    assert ia is not None  # importable con esta configuración
