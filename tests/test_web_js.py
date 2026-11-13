"""Corre con Node las pruebas de la lógica del cliente que no necesita pantalla."""
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_la_logica_del_cliente():
    node = shutil.which("node")
    if node is None:
        pytest.skip("no hay Node en esta máquina")
    pruebas = sorted(str(p) for p in (RAIZ / "tests" / "js").glob("*.test.mjs"))
    assert pruebas, "no hay pruebas de JavaScript que correr"
    hecho = subprocess.run([node, "--test", *pruebas], cwd=RAIZ, capture_output=True, text=True)
    assert hecho.returncode == 0, hecho.stdout + hecho.stderr
