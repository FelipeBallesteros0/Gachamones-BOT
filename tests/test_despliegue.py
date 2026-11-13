"""Lo que los guiones de despliegue no pueden dejar de hacer."""
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GUIONES = ("actualizar-pi.sh", "deploy.sh")


def leer(nombre: str) -> str:
    return (RAIZ / nombre).read_text(encoding="utf-8")


def test_el_servicio_web_escucha_solo_en_la_propia_maquina():
    unidad = leer("gachamon-web.service")
    assert "uvicorn web.app:app" in unidad
    assert "--host 127.0.0.1" in unidad and "--port 8010" in unidad
    assert "0.0.0.0" not in unidad
    assert "Restart=always" in unidad
    assert "WorkingDirectory=/home/felipe/tamagotchi-bot" in unidad
    assert "User=felipe" in unidad


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_reinicia_los_dos_servicios(guion):
    texto = leer(guion)
    assert "gachamon-web.service" in texto
    assert "restart tamagotchi" in texto and "gachamon-web" in texto.split("restart tamagotchi", 1)[1]


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_reinicia_el_bot_antes_que_la_web(guion):
    texto = leer(guion)
    assert texto.index("restart tamagotchi") < texto.index("restart gachamon-web")


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_instala_habilita_y_comprueba_la_web(guion):
    texto = leer(guion)
    assert "/etc/systemd/system/gachamon-web.service" in texto
    assert "enable tamagotchi gachamon-web" in texto
    assert "systemctl is-active tamagotchi gachamon-web" in texto
    # la comprobación va después de reiniciar: si la web no queda activa, falla
    assert texto.index("restart gachamon-web") < texto.index("is-active tamagotchi gachamon-web")


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_copia_la_base_antes_de_reiniciar(guion):
    texto = leer(guion)
    assert texto.index(".bak") < texto.index("systemctl restart")


def test_una_suite_en_rojo_frena_el_despliegue_y_corre_en_memoria():
    texto = leer("actualizar-pi.sh")
    linea = next(l for l in texto.splitlines() if "pytest" in l and "ssh" in l)
    assert "set -o pipefail" in linea
    assert "--basetemp=/dev/shm/" in linea


def test_rsync_no_borra_el_diario_de_sqlite():
    texto = leer("deploy.sh")
    for patron in ("*.db", "*.db-journal", "*.db-wal", "*.db-shm"):
        assert f"--exclude '{patron}'" in texto


@pytest.mark.parametrize("guion", GUIONES)
def test_los_guiones_son_bash_valido(guion):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    hecho = subprocess.run([bash, "-n", str(RAIZ / guion)], capture_output=True, text=True)
    assert hecho.returncode == 0, hecho.stderr
