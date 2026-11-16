"""Contrasta lo que el cliente cree que cabe (casillas.js) con lo que dice el servidor.

Lo que recibe el cliente sale de `web.departamento.vista`, la que arma `GET
/departamento`: si cambia el nombre de un campo, esta prueba lo nota.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import db
import departamento as dep
from web import departamento as web_departamento
from web.cuenta import Jugador

RAIZ = Path(__file__).resolve().parent.parent
MODULO = RAIZ / "web" / "static" / "js" / "casillas.js"

CANDIDATA = 100

PROGRAMA = f"""
import {{ huellaDe, problemaAlPoner }} from {json.dumps(MODULO.as_uri())};
let texto = '';
for await (const trozo of process.stdin) texto += trozo;
const {{ depto, casos }} = JSON.parse(texto);
const respuestas = casos.map(({{ pieza, x, y, giro }}) => ({{
  huella: huellaDe(pieza, x, y, giro),
  problema: problemaAlPoner(depto, pieza, x, y, giro),
}}));
process.stdout.write(JSON.stringify(respuestas));
"""


def _departamento_de_ejemplo() -> dep.Departamento:
    return dep.Departamento(4, 3, (
        dep.Pieza(1, "alfombra", 0, 0),
        dep.Pieza(2, "cama_sencilla", 2, 2),
        dep.Pieza(3, "cortinas", 1, -1),
        dep.Pieza(4, "cortinas", -1, 1),
    ))


# Una persona sintética, en una base temporal: la vista lee sus saldos y su plantel.
JUGADOR = Jugador(persona=None, usuario_id="web:casillas", guild_id="g", vinculada=False)


@pytest.fixture
def base_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "casillas.db")
    db.inicializar()


def test_el_cliente_y_el_servidor_dicen_lo_mismo(base_temporal):
    node = shutil.which("node")
    if node is None:
        pytest.skip("no hay Node en esta máquina")
    base = _departamento_de_ejemplo()
    casos, esperado = [], []
    for mueble in dep.MUEBLES.values():
        depto = dep.Departamento(base.ancho, base.fondo, (*base.piezas, dep.Pieza(CANDIDATA, mueble.clave)))
        # El candidato, como lo trae la vista: guardado, a la espera de ponerse.
        [pieza] = [g for g in web_departamento.vista(JUGADOR, depto)["guardados"] if g["id"] == CANDIDATA]
        for x in range(-1, base.ancho + 1):
            for y in range(-1, base.fondo + 1):
                for giro in range(4):
                    casos.append({"pieza": pieza, "x": x, "y": y, "giro": giro})
                    esperado.append({
                        "huella": [list(c) for c in sorted(dep.huella(mueble, x, y, giro))],
                        "problema": dep.problema_al_poner(depto, CANDIDATA, x, y, giro),
                    })
    entrada = json.dumps({"depto": web_departamento.vista(JUGADOR, base), "casos": casos})
    hecho = subprocess.run([node, "--input-type=module", "-e", PROGRAMA], input=entrada,
                           capture_output=True, text=True, cwd=RAIZ)
    assert hecho.returncode == 0, hecho.stderr
    respuestas = json.loads(hecho.stdout)
    assert len(respuestas) == len(casos) == len(dep.MUEBLES) * (base.ancho + 2) * (base.fondo + 2) * 4
    for caso, dijo, debia in zip(casos, respuestas, esperado):
        assert dijo == debia, (caso["pieza"]["clave"], caso["x"], caso["y"], caso["giro"], dijo, debia)
    # La prueba tiene que ver los dos veredictos y los dos rechazos, o no contrasta nada.
    assert {r["problema"] for r in esperado} == {None, dep.NO_CABE, dep.OCUPADO}
