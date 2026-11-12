import pytest

import avatar
import db
import especies as esp
from ayudas_web import T0

BUENO = dict(nombre="Feli", genero=esp.MACHO, piel="media", pelo="corto",
             color_de_pelo="castano", ropa="poleron")


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "avatar.db")
    db.inicializar()


def test_los_catalogos_son_los_acordados():
    claves = {nombre: tuple(o.clave for o in lista) for nombre, lista in avatar.opciones().items()}
    assert claves == {
        "generos": (esp.MACHO, esp.HEMBRA),
        "pieles": ("clara", "media", "tostada", "oscura"),
        "pelos": ("corto", "largo", "rizado", "coleta", "rapado"),
        "colores_de_pelo": ("negro", "castano", "rubio", "rojo", "cano", "azul"),
        "ropas": ("poleron", "camisa", "vestido", "overol"),
    }
    assert all(o.nombre and o.nombre[0].isupper() for lista in avatar.opciones().values() for o in lista)


def test_un_avatar_bien_hecho_se_crea_y_normaliza_el_nombre():
    hecho = avatar.crear(**{**BUENO, "nombre": "  Feli   Pe  "})
    assert hecho == avatar.Avatar("Feli Pe", esp.MACHO, "media", "corto", "castano", "poleron")


@pytest.mark.parametrize("campo, valor", [
    ("nombre", ""), ("nombre", "   "), ("nombre", "<b>Feli</b>"), ("nombre", "Feli🙂"),
    ("nombre", "x" * 25), ("genero", "otro"), ("piel", "verde"), ("pelo", "cresta"),
    ("color_de_pelo", "castaño"), ("ropa", "armadura"), ("piel", ""),
])
def test_lo_que_no_vale_se_rechaza_con_una_frase(campo, valor):
    with pytest.raises(ValueError) as error:
        avatar.crear(**{**BUENO, campo: valor})
    assert str(error.value).strip()


def test_se_guarda_se_lee_y_se_puede_cambiar():
    assert db.avatar_de("u", "g") is None
    db.guardar_avatar("u", "g", avatar.crear(**BUENO), T0)
    assert db.avatar_de("u", "g") == avatar.crear(**BUENO)
    db.guardar_avatar("u", "g", avatar.crear(**{**BUENO, "ropa": "overol"}), T0)
    assert db.avatar_de("u", "g").ropa == "overol"
    assert db.avatar_de("otro", "g") is None and db.avatar_de("u", "otro") is None
