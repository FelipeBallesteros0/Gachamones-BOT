"""Lo que los guiones de despliegue no pueden dejar de hacer."""
import re
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
def test_cada_guion_instala_y_habilita_las_dos_unidades(guion):
    texto = leer(guion)
    assert "/etc/systemd/system/gachamon-web.service" in texto
    assert "enable tamagotchi gachamon-web" in texto


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_comprueba_cada_servicio_por_separado(guion):
    # `systemctl is-active a b` sale con 0 si basta UNA activa: una web caída
    # pasaría. Una comprobación por unidad, encadenadas con &&.
    texto = leer(guion)
    lineas = [l for l in texto.splitlines() if "is-active" in l and not l.lstrip().startswith("#")]
    assert lineas, "falta la comprobación final"
    for linea in lineas:
        assert not re.search(r"is-active\s+(tamagotchi|gachamon-web)\s+(tamagotchi|gachamon-web)", linea)
    unidos = " ".join(lineas)
    assert "is-active tamagotchi &&" in unidos
    assert "&& systemctl is-active gachamon-web" in unidos
    # y van después de reiniciar la web: si no queda activa, el guion falla
    assert texto.index("restart gachamon-web") < texto.index("is-active gachamon-web")


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_copia_la_base_antes_de_reiniciar(guion):
    texto = leer(guion)
    assert texto.index("cp tamagotchi.db") < texto.index("systemctl restart")


def test_la_web_arranca_despues_del_bot_sin_depender_de_el():
    unidad = leer("gachamon-web.service")
    assert "After=network-online.target tamagotchi.service" in unidad
    assert "Requires=" not in unidad


def test_la_pi_instala_lo_que_la_suite_necesita_solo_si_la_corre():
    texto = leer("actualizar-pi.sh")
    assert "requisitos=requirements-dev.txt" in texto
    assert "requisitos=requirements.txt" in texto
    # el de desarrollo se elige cuando NO hay SIN_TESTS
    i = texto.index("if [ -z '$SIN_TESTS' ]")
    assert i < texto.index("requisitos=requirements-dev.txt") < texto.index("else", i)
    assert '-r "\\$requisitos"' in texto


def test_una_suite_en_rojo_frena_el_despliegue_y_corre_en_memoria():
    texto = leer("actualizar-pi.sh")
    linea = next(l for l in texto.splitlines() if "pytest" in l and "ssh" in l)
    assert "set -o pipefail" in linea
    assert "--basetemp=/dev/shm/" in linea


def _linea_de_pytest_en_la_pi():
    texto = leer("actualizar-pi.sh")
    return next(l for l in texto.splitlines() if "pytest" in l and "ssh" in l)


def test_la_suite_de_la_pi_no_se_queda_con_la_memoria():
    linea = _linea_de_pytest_en_la_pi()
    assert "-o tmp_path_retention_policy=none" in linea
    assert "rm -rf /dev/shm/gachamon-pytest" in linea
    # guarda el estado de pytest, borra, y sale con ese estado
    assert linea.index("estado=") < linea.index("rm -rf") < linea.index("exit ")
    assert "exit \\$estado" in linea


@pytest.mark.parametrize("codigo", [0, 1])
def test_la_orden_remota_conserva_el_codigo_de_pytest_y_borra(codigo, tmp_path):
    """Ejecuta en local la orden que iría por ssh, con un pytest de mentira."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    linea = _linea_de_pytest_en_la_pi()
    orden = linea.split('ssh "$PI" "', 1)[1].rsplit('"', 1)[0]
    orden = orden.replace("\\$", "$").replace("'$DEST'", f"'{tmp_path}'")
    temporal = tmp_path / "temporal"
    temporal.mkdir()
    orden = orden.replace("/dev/shm/gachamon-pytest", str(temporal))
    falso = tmp_path / "venv" / "bin"
    falso.mkdir(parents=True)
    (falso / "python").write_text(f"#!/bin/bash\necho resultado de mentira\nexit {codigo}\n")
    (falso / "python").chmod(0o755)
    hecho = subprocess.run([bash, "-c", orden], capture_output=True, text=True)
    assert hecho.returncode == codigo
    assert "resultado de mentira" in hecho.stdout
    assert not temporal.exists()


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
