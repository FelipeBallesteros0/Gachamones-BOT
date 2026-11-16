"""El Refugio cerró: sigue en el mapa, sin nada dentro, y lo avisa."""
from ayudas_web import con_gachamon, ir, poner_reloj

CERRO = "El refugio cerró. Ahora cada quien vive en su departamento."


def test_el_refugio_sigue_en_el_mapa_pero_cerro(cliente):
    con_gachamon(cliente)
    lugar = ir(cliente, "refugio").json()["lugar"]
    assert (lugar["aviso"], lugar["ofrece"]) == ("El refugio cerró. Ahora cada quien vive en su departamento.", [])
    assert "refugio" not in lugar


def test_en_el_refugio_cerrado_el_gachamon_solo_charla(cliente, monkeypatch):
    poner_reloj(monkeypatch)
    con_gachamon(cliente)                     # recién nacido: no necesita nada
    estado = ir(cliente, "refugio").json()
    assert (estado["lugar"]["clave"], estado["lugar"]["aviso"]) == ("refugio", CERRO)
    assert [g for g in estado["globos"] if g["tipo"] == "lugar"] == []
    assert estado["globos"] and all(g["tipo"] == "suelta" for g in estado["globos"])
