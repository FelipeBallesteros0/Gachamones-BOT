import sys
from pathlib import Path

import pytest

# Los módulos del bot viven en la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_base_por_defecto(tmp_path, monkeypatch):
    """Ninguna prueba abre la base de verdad por descuido.

    `db.RUTA` apunta a un archivo dentro de un directorio que no existe y que
    nadie crea: una prueba que olvide su base temporal falla con
    `sqlite3.OperationalError`. Las que ponen la suya con
    `monkeypatch.setattr(db, "RUTA", ...)` siguen igual: sus fixtures corren
    después de ésta y la pisan.
    """
    monkeypatch.setattr(db, "RUTA", tmp_path / "no-existe" / "tamagotchi.db")
