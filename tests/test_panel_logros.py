"""Las medallas que se ganan jugando: la que se cumple sólo con esperar y las
tres tuyas, que se ganan al nacer un gachamon y al reclutar."""
from datetime import datetime, timedelta, timezone

import pytest

import db
import economia
import logros

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATS = (15, 15, 15, 15)


@pytest.fixture(autouse=True)
def bd(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "panel.db")
    db.inicializar()


def nacer(nombre="Mia"):
    return db.crear("u1", "g1", "pulpo", nombre, STATS, T0)


def test_veterano_se_paga_aunque_nadie_haya_jugado():
    """El único que se cumple solo con esperar: pagar las medallas lo apunta y
    lo cobra aunque en ese mes no haya pasado nada más."""
    bicho = nacer()
    un_mes = T0 + timedelta(days=31)

    assert "veterano" not in db.logros_de(bicho.id)
    recibo = economia.pagar_logros(bicho, un_mes)

    assert "veterano" in {logro.clave for logro in recibo.nuevos}
    assert "veterano" in db.logros_de(bicho.id)
    assert recibo.asciigems >= logros.POR_CLAVE["veterano"].gemas


# --- Las tres tuyas: al nacer y al reclutar ---------------------------------
#
# Las tres de la persona sólo pueden cambiar al nacer un gachamon y al reclutar.
# Se prueban por el camino de verdad —`nacer` y luego cobrar— porque el fallo
# que importa es el cable suelto: el gachamon nace o se une, y la medalla no.


def test_al_romper_el_huevo_una_rara_es_tuya(monkeypatch):
    import especies as esp
    import nacer as nac

    monkeypatch.setattr(
        esp, "elegir_del_huevo", lambda _: esp.ESPECIES["dragoncito"]
    )
    bicho = nac.romper_el_huevo("1", "g1", T0)

    recibo = economia.pagar_logros_de_persona("1", "g1", T0)

    assert {logro.clave for logro in recibo.nuevos} == {"uno_entre_veinticinco"}
    assert set(db.logros_de_persona("1", "g1")) == {"uno_entre_veinticinco"}
    # Tuya, no del bicho: la suerte fue de quien rompió el cascarón.
    assert "uno_entre_veinticinco" not in db.logros_de(bicho.id)


def test_al_reclutar_domador_es_tuyo():
    import nacer as nac

    bicho = db.crear("1", "g1", "pulpo", "Aventurero", STATS, T0)
    nac.unir_recluta(
        "1", "g1", especie="michi", stats=(10, 10, 10, 15), genero="macho",
        caracter="sereno", ahora=T0,
    )

    economia.pagar_logros_de_persona("1", "g1", T0)

    assert set(db.logros_de_persona("1", "g1")) == {"domador"}
    # Y el gachamon que salió no se lleva ninguna de las tres.
    assert "domador" not in db.logros_de(bicho.id)


@pytest.mark.parametrize("clave", ["dragoncito", "cefiro", "prismlon"])
def test_reclutar_un_raro_tambien_da_uno_entre_veinticinco(clave):
    """Pedido tras jugarlo: la medalla no es sólo del huevo de partida.

    Se prueban las tres raras y no una: **dos de ellas no salen del huevo**, así
    que reclutarlas es la única forma de conseguirlas, y si esto sólo mirase a
    la del huevo no habría manera de ganarla con ellas.
    """
    import especies as esp
    import nacer as nac

    assert esp.ESPECIES[clave].rareza == esp.RARA
    db.crear("1", "g1", "pulpo", "Aventurero", STATS, T0)
    nac.unir_recluta(
        "1", "g1", especie=clave, stats=(10, 10, 10, 15), genero=esp.MACHO,
        caracter="sereno", ahora=T0,
    )

    economia.pagar_logros_de_persona("1", "g1", T0)

    assert set(db.logros_de_persona("1", "g1")) == {
        "domador", "uno_entre_veinticinco"
    }


def test_dos_de_las_tres_raras_no_salen_del_huevo():
    """Lo que hace imprescindible al test de arriba: si «Uno entre veinticinco»
    dependiera del cascarón, Céfiro y Prismlon no la darían nunca."""
    import especies as esp

    raras = {c for c, e in esp.ESPECIES.items() if e.rareza == esp.RARA}
    assert raras - set(esp.DEL_HUEVO) == {"cefiro", "prismlon"}
