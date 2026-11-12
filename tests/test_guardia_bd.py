import sqlite3

import pytest

import db


def test_sin_base_propia_ninguna_prueba_abre_la_de_verdad(tmp_path):
    """Fija la guardia de `conftest.py`: por defecto `db.RUTA` apunta a un
    directorio que no existe, así que olvidar la base temporal falla en vez de
    tocar `tamagotchi.db` (en la Pi la suite corre en la carpeta de producción)."""
    assert not db.RUTA.parent.exists()
    with pytest.raises(sqlite3.OperationalError):
        db.conectar()
    assert not db.RUTA.exists()
    assert not db.RUTA.parent.exists()
