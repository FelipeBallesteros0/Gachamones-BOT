"""Lo que los guiones de despliegue no pueden dejar de hacer."""
import os
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
    # `failed` borra el `tmp_path` de cada prueba que pasa; `none` sólo decide
    # cuántas sesiones se guardan y, con `--basetemp`, deja crecer el temporal.
    assert "-o tmp_path_retention_policy=failed" in linea
    assert "tmp_path_retention_policy=none" not in leer("actualizar-pi.sh")
    assert "rm -rf /dev/shm/gachamon-pytest" in linea
    # guarda el estado de pytest, borra, y sale con ese estado
    assert linea.index("estado=") < linea.index("rm -rf") < linea.index("exit ")
    assert "exit \\$estado" in linea


def _de_mentira(ruta: Path, apuntes: Path, nombre: str, despues: str = "exit 0") -> None:
    """Una orden que apunta en `apuntes` cómo la llamaron y hace `despues`."""
    ruta.write_text(f"#!/bin/bash\necho \"{nombre} $*\" >> '{apuntes}'\n{despues}\n")
    ruta.chmod(0o755)


def _correr_la_orden_remota(tmp_path, codigo, anterior=None, cortada=False):
    """Ejecuta en local la orden que iría por ssh, con `python`, `git` y `sudo` de mentira.

    El `python` del venv contesta a pytest con `codigo`; `anterior`, si no es
    None, es lo que hay en `.git/gachamon-anterior`. Con `cortada`, la conexión
    está caída: lo que la orden escriba ya no lo lee nadie. Devuelve lo que
    pasó, lo que apuntaron las órdenes de mentira y el temporal de la suite. El
    `sudo` de mentira impide que la prueba toque los servicios de esta máquina.
    """
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    destino, temporal, ordenes = tmp_path / "destino", tmp_path / "temporal", tmp_path / "bin"
    for carpeta in (destino / "venv" / "bin", destino / ".git", temporal, ordenes):
        carpeta.mkdir(parents=True)
    if anterior is not None:
        (destino / ".git" / "gachamon-anterior").write_text(anterior)
    apuntes = tmp_path / "apuntes"
    _de_mentira(
        destino / "venv" / "bin" / "python", apuntes, "python",
        f'if [ "$1 $2" = "-m pytest" ]; then echo resultado de mentira; exit {codigo}; fi',
    )
    _de_mentira(ordenes / "git", apuntes, "git")
    _de_mentira(ordenes / "sudo", apuntes, "sudo")

    linea = _linea_de_pytest_en_la_pi()
    crudo = linea.split('ssh "$PI" "', 1)[1].rsplit('"', 1)[0]
    # Primero el temporal y después el destino: el `tmp_path` de esta prueba
    # puede contener la cadena del temporal de la Pi (con
    # `--basetemp=/dev/shm/gachamon-pytest` la contiene), y sustituirla después
    # reescribiría también la ruta del destino.
    crudo = crudo.replace("/dev/shm/gachamon-pytest", str(temporal))
    # Lo que de verdad le llega a la Pi: la cadena entre comillas dobles tal
    # como la expande el bash de aquí (`$DEST`, `\$`, `\"`).
    orden = subprocess.run(
        [bash, "-c", f'printf %s "{crudo}"'], env={**os.environ, "DEST": str(destino)},
        capture_output=True, text=True, check=True,
    ).stdout
    assert str(destino) in orden and "\\" not in orden
    entorno = {**os.environ, "PATH": f"{ordenes}{os.pathsep}{os.environ.get('PATH', '')}"}
    if cortada:
        lectura, escritura = os.pipe()
        os.close(lectura)
        try:
            hecho = subprocess.run(
                [bash, "-c", orden], stdout=escritura, stderr=subprocess.PIPE, text=True, env=entorno
            )
        finally:
            os.close(escritura)
    else:
        hecho = subprocess.run([bash, "-c", orden], capture_output=True, text=True, env=entorno)
    lineas = apuntes.read_text().splitlines() if apuntes.exists() else []
    return hecho, lineas, temporal


@pytest.mark.parametrize("codigo", [0, 1])
def test_la_orden_remota_conserva_el_codigo_de_pytest_y_borra(codigo, tmp_path):
    hecho, _, temporal = _correr_la_orden_remota(tmp_path, codigo)
    assert hecho.returncode == codigo, hecho.stderr
    assert "resultado de mentira" in hecho.stdout
    assert not temporal.exists()


@pytest.mark.parametrize("codigo", [1, 2])
def test_con_la_suite_en_rojo_la_pi_vuelve_al_commit_de_antes(codigo, tmp_path):
    hecho, apuntes, temporal = _correr_la_orden_remota(tmp_path, codigo, anterior="abc1234\n")
    # El código de salida sigue siendo el de pytest, y el temporal se borró.
    assert hecho.returncode == codigo, hecho.stderr
    assert not temporal.exists()
    assert "git reset -q --hard abc1234" in apuntes
    instalar = "python -m pip install -q -r requirements.txt"
    assert instalar in apuntes
    assert apuntes.index("git reset -q --hard abc1234") < apuntes.index(instalar)
    # Y lo dice, en una línea.
    aviso = [l for l in hecho.stdout.splitlines() if "abc1234" in l]
    assert len(aviso) == 1


def test_con_la_suite_en_verde_no_se_vuelve_atras(tmp_path):
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, 0, anterior="abc1234\n")
    assert hecho.returncode == 0
    assert not [a for a in apuntes if a.startswith("git ") or " pip " in a]
    assert "abc1234" not in hecho.stdout


@pytest.mark.parametrize("anterior", [None, ""], ids=["sin_archivo", "vacio"])
def test_sin_commit_guardado_no_se_intenta_volver(anterior, tmp_path):
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, 1, anterior=anterior)
    assert hecho.returncode == 1
    assert not [a for a in apuntes if a.startswith("git ") or " pip " in a]


# --- La web, parada mientras se tocan sus archivos ---------------------------
#
# Los estáticos versionados se guardan un año (`immutable`). Si la web vieja
# siguiera en marcha mientras se cambian los archivos, serviría los nuevos bajo
# su versión vieja y navegadores y Cloudflare se quedarían con copias mezcladas.

ARRANCAR_LA_WEB = "sudo systemctl start gachamon-web"


def test_la_web_se_para_antes_de_tocar_sus_archivos():
    remoto = _bloque_remoto()
    assert "sudo systemctl stop gachamon-web" in remoto
    assert remoto.index("systemctl stop gachamon-web") < remoto.index("git reset -q --hard")
    # El bot no sirve archivos: sigue en marcha hasta el reinicio del final.
    assert "stop tamagotchi" not in leer("actualizar-pi.sh")


def test_el_bloque_remoto_no_lleva_comillas_invertidas():
    # Va en un heredoc sin comillas: una comilla invertida, aunque esté en un
    # comentario, ejecutaría aquí lo que encierra antes de mandarlo a la Pi.
    assert "`" not in _bloque_remoto()


@pytest.mark.parametrize("codigo", [1, 2])
def test_con_la_suite_en_rojo_la_web_vuelve_a_arrancar_tras_volver_atras(codigo, tmp_path):
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, codigo, anterior="abc1234\n")
    # El código de salida sigue siendo el de pytest: el guion corta igual.
    assert hecho.returncode == codigo, hecho.stderr
    assert apuntes.count(ARRANCAR_LA_WEB) == 1
    instalar = "python -m pip install -q -r requirements.txt"
    assert (apuntes.index("git reset -q --hard abc1234") < apuntes.index(instalar)
            < apuntes.index(ARRANCAR_LA_WEB))


@pytest.mark.parametrize("anterior", [None, ""], ids=["sin_archivo", "vacio"])
def test_sin_commit_al_que_volver_la_web_vuelve_a_arrancar_igual(anterior, tmp_path):
    # Se paró antes de tocar los archivos: si no arrancara, se quedaría parada.
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, 1, anterior=anterior)
    assert hecho.returncode == 1
    assert apuntes.count(ARRANCAR_LA_WEB) == 1


def test_con_la_suite_en_verde_la_web_arranca_con_el_reinicio_del_final(tmp_path):
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, 0, anterior="abc1234\n")
    assert hecho.returncode == 0
    assert not [a for a in apuntes if a.startswith("sudo ")]


def _bloque_remoto() -> str:
    return leer("actualizar-pi.sh").split("<<REMOTO\n", 1)[1].split("\nREMOTO\n", 1)[0]


def _guardar_el_commit() -> str:
    """Las líneas del primer bloque remoto que apuntan dónde estaba la Pi."""
    lineas = _bloque_remoto().splitlines()
    inicio = next(i for i, l in enumerate(lineas) if l.startswith("if ") and "HEAD" in l)
    fin = next(i for i in range(inicio, len(lineas)) if lineas[i] == "fi")
    return "\n".join(lineas[inicio:fin + 1])


def test_el_commit_de_antes_se_apunta_antes_de_bajar_el_nuevo():
    remoto = _bloque_remoto()
    bloque = _guardar_el_commit()
    assert ".git/gachamon-anterior" in bloque
    # Después de que exista el clon y antes de tocar el código.
    assert remoto.index("git init") < remoto.index(bloque) < remoto.index("git fetch")
    # El bloque va en un heredoc sin comillas: sin `$` ni comillas invertidas,
    # aquí no se expande nada y en la Pi corre tal cual se lee.
    assert "$" not in bloque and "`" not in bloque


def test_apuntar_el_commit_de_antes_lo_guarda_o_lo_borra(tmp_path):
    bash, git = shutil.which("bash"), shutil.which("git")
    if bash is None or git is None:
        pytest.skip("no hay bash o git")
    bloque = _guardar_el_commit()
    sin_identidad = {**os.environ, "GIT_AUTHOR_NAME": "x", "GIT_AUTHOR_EMAIL": "x@x",
                     "GIT_COMMITTER_NAME": "x", "GIT_COMMITTER_EMAIL": "x@x"}

    con_commit = tmp_path / "con_commit"
    con_commit.mkdir()
    subprocess.run([git, "init", "-q"], cwd=con_commit, check=True)
    subprocess.run([git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=con_commit,
                   check=True, env=sin_identidad)
    cabeza = subprocess.run([git, "rev-parse", "HEAD"], cwd=con_commit, check=True,
                            capture_output=True, text=True).stdout.strip()
    subprocess.run([bash, "-c", f"set -euo pipefail\n{bloque}"], cwd=con_commit, check=True)
    assert (con_commit / ".git" / "gachamon-anterior").read_text().strip() == cabeza

    # La primera vez no hay HEAD: no se guarda nada y se borra uno viejo.
    primera = tmp_path / "primera"
    primera.mkdir()
    subprocess.run([git, "init", "-q"], cwd=primera, check=True)
    (primera / ".git" / "gachamon-anterior").write_text("viejo\n")
    subprocess.run([bash, "-c", f"set -euo pipefail\n{bloque}"], cwd=primera, check=True)
    assert not (primera / ".git" / "gachamon-anterior").exists()


# --- Un despliegue cortado no deja la web parada -----------------------------
#
# Desde que el bloque remoto para la web hasta el reinicio del final, cualquier
# corte (falla pip, se cae la conexión, falla el reinicio) la dejaba parada
# hasta que alguien la arrancara a mano.

PARAR_LA_WEB = "sudo systemctl stop gachamon-web"


def _correr_el_bloque_remoto(tmp_path, pip=0, con_unidad=True, cortar=False):
    """Ejecuta en local el bloque remoto tal como le llega a la Pi, con `git`, `sudo` y `python` de mentira.

    `pip` es el código con el que sale la instalación de requisitos;
    `con_unidad`, si la unidad de la web ya está instalada. Con `cortar`, la
    conexión se cae justo después de parar la web: lo que el bloque escriba
    desde ahí ya no lo lee nadie. Devuelve el código de salida y lo que
    apuntaron las órdenes de mentira.
    """
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    destino, ordenes = tmp_path / "destino", tmp_path / "bin"
    for carpeta in (destino / "venv" / "bin", destino / ".git", ordenes):
        carpeta.mkdir(parents=True)
    apuntes, cortada, unidad = tmp_path / "apuntes", tmp_path / "cortada", tmp_path / "gachamon-web.service"
    if con_unidad:
        unidad.write_text("")
    _de_mentira(destino / "venv" / "bin" / "python", apuntes, "python", f"exit {pip}")
    _de_mentira(ordenes / "git", apuntes, "git")
    # Con `cortar`, parar la web espera a que la prueba haya cortado la conexión.
    espera = (
        'if [ "$*" = "systemctl stop gachamon-web" ]; then\n'
        f"    for _ in $(seq 1000); do [ -f '{cortada}' ] && exit 0; sleep 0.01; done\n"
        "    exit 1\n"
        "fi\n"
    ) if cortar else ""
    _de_mentira(ordenes / "sudo", apuntes, "sudo", espera + "exit 0")

    crudo = _bloque_remoto().replace("/etc/systemd/system/gachamon-web.service", str(unidad))
    # El heredoc no lleva comillas: a la Pi le llega lo que expande el bash de aquí.
    variables = {**os.environ, "DEST": str(destino), "RAMA": "main", "REMOTO_URL": "origen", "SIN_TESTS": "1"}
    bloque = subprocess.run(
        [bash, "-c", f"cat <<REMOTO\n{crudo}\nREMOTO\n"], env=variables,
        capture_output=True, text=True, check=True,
    ).stdout
    entorno = {**os.environ, "PATH": f"{ordenes}{os.pathsep}{os.environ.get('PATH', '')}"}
    if cortar:
        with open(tmp_path / "errores", "w") as errores:
            proceso = subprocess.Popen(
                [bash, "-c", bloque], stdout=subprocess.PIPE, stderr=errores, text=True, env=entorno
            )
            primera = proceso.stdout.readline()
            proceso.stdout.close()       # se cae la conexión
            cortada.touch()
            codigo = proceso.wait(timeout=30)
        assert "la web se para" in primera
    else:
        codigo = subprocess.run([bash, "-c", bloque], capture_output=True, text=True, env=entorno).returncode
    return codigo, apuntes.read_text().splitlines() if apuntes.exists() else []


def _de_sudo(apuntes):
    return [a for a in apuntes if a.startswith("sudo ")]


def test_tras_parar_la_web_el_bloque_remoto_pone_su_trap():
    remoto = _bloque_remoto()
    trap = next(l for l in remoto.splitlines() if l.lstrip().startswith("trap ") and "EXIT" in l)
    assert "systemctl start gachamon-web" in trap
    # Después de pararla y antes de tocar nada: un corte anterior no la ha parado.
    assert remoto.index(PARAR_LA_WEB) < remoto.index(trap) < remoto.index("git reset -q --hard")


def test_si_el_bloque_remoto_sale_bien_no_arranca_la_web(tmp_path):
    # La arranca el reinicio del final, después del bot.
    codigo, apuntes = _correr_el_bloque_remoto(tmp_path, pip=0)
    assert codigo == 0
    assert _de_sudo(apuntes) == [PARAR_LA_WEB]


@pytest.mark.parametrize("pip", [1, 2])
def test_si_falla_pip_la_web_vuelve_a_arrancar(pip, tmp_path):
    codigo, apuntes = _correr_el_bloque_remoto(tmp_path, pip=pip)
    assert codigo == pip                   # y el guion corta igual
    assert _de_sudo(apuntes) == [PARAR_LA_WEB, ARRANCAR_LA_WEB]
    assert apuntes.index("python -m pip install -q -r requirements.txt") < apuntes.index(ARRANCAR_LA_WEB)


def test_si_se_cae_la_conexion_tras_pararla_la_web_vuelve_a_arrancar(tmp_path):
    codigo, apuntes = _correr_el_bloque_remoto(tmp_path, cortar=True)
    assert codigo != 0
    assert _de_sudo(apuntes) == [PARAR_LA_WEB, ARRANCAR_LA_WEB]


def test_sin_la_unidad_instalada_no_se_para_ni_se_arranca_nada(tmp_path):
    codigo, apuntes = _correr_el_bloque_remoto(tmp_path, pip=1, con_unidad=False)
    assert codigo == 1
    assert _de_sudo(apuntes) == []


def test_la_orden_de_la_suite_ignora_sigpipe_antes_de_correrla():
    linea = _linea_de_pytest_en_la_pi()
    assert linea.index("trap '' PIPE") < linea.index("pytest")


def test_si_se_cae_la_conexion_durante_la_suite_la_web_vuelve_a_arrancar(tmp_path):
    # Sin respuesta que leer, el `tail` y el aviso del camino en rojo escriben a
    # nadie: un SIGPIPE cortaba la orden antes de volver atrás y de arrancar la web.
    hecho, apuntes, _ = _correr_la_orden_remota(tmp_path, 1, anterior="abc1234\n", cortada=True)
    assert hecho.returncode != 0
    assert "git reset -q --hard abc1234" in apuntes
    assert apuntes.count(ARRANCAR_LA_WEB) == 1


AVISO_DE_LA_WEB_PARADA = (
    "La web puede haber quedado parada. Para arrancarla: ssh usuario@pi 'sudo systemctl start gachamon-web'"
)


def _aviso_local() -> str:
    """Las líneas del guion que preparan el aviso de la web parada."""
    lineas = leer("actualizar-pi.sh").splitlines()
    inicio = next(i for i, l in enumerate(lineas) if l.startswith("web_en_marcha="))
    fin = next(i for i in range(inicio, len(lineas)) if lineas[i].startswith("trap ") and "EXIT" in lineas[i])
    return "\n".join(lineas[inicio:fin + 1])


@pytest.mark.parametrize("final", ["exit 1", "false", "kill -INT $$"], ids=["error", "orden_fallida", "ctrl_c"])
def test_si_el_guion_no_termina_bien_lo_ultimo_es_como_arrancar_la_web(final):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    hecho = subprocess.run(
        [bash, "-c", f"set -euo pipefail\n{_aviso_local()}\necho '==> lo que iba haciendo'\n{final}\n"],
        env={**os.environ, "PI": "usuario@pi"}, capture_output=True, text=True,
    )
    assert hecho.returncode != 0
    assert hecho.stdout.splitlines() == ["==> lo que iba haciendo", AVISO_DE_LA_WEB_PARADA]


def test_si_el_guion_termina_bien_no_avisa():
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no hay bash")
    hecho = subprocess.run(
        [bash, "-c", f"set -euo pipefail\n{_aviso_local()}\nweb_en_marcha=1\n"],
        env={**os.environ, "PI": "usuario@pi"}, capture_output=True, text=True,
    )
    assert hecho.returncode == 0
    assert hecho.stdout == ""


def test_el_aviso_se_arma_antes_de_parar_la_web_y_se_calla_al_final():
    texto = leer("actualizar-pi.sh")
    aviso = _aviso_local()
    # Cancelar por los commits sin subir no ha parado nada: no avisa.
    assert texto.index('echo "Cancelado."') < texto.index(aviso) < texto.index('ssh "$PI" "bash -s" <<REMOTO')
    # La web queda en marcha sólo cuando el reinicio del final ya la vio contestar.
    assert texto.count("web_en_marcha=1") == 1
    assert texto.index(SALUD) < texto.index("web_en_marcha=1")
    # La dirección sale de `$PI`, no se escribe a mano.
    assert "ssh $PI 'sudo systemctl start gachamon-web'" in aviso


SALUD = (
    "curl -fsS --retry 10 --retry-delay 1 --retry-connrefused -o /dev/null "
    "http://127.0.0.1:8010/gachamon/api/salud"
)


@pytest.mark.parametrize("guion", GUIONES)
def test_cada_guion_pregunta_a_la_web_por_su_salud(guion):
    # `is-active` dice «active» mientras Python todavía importa: la web se da
    # por buena cuando contesta. Encadenada con &&, si no contesta el guion falla.
    texto = leer(guion)
    assert texto.count(SALUD) == 1
    assert texto.index("restart gachamon-web") < texto.index("is-active gachamon-web") < texto.index(SALUD)
    assert re.search(r"is-active gachamon-web\s*&&[\s\\]*" + re.escape(SALUD), texto)


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
