"""La herramienta que levanta una página de prueba: sus reglas, sin servidores.

Se prueban las funciones puras (armar el entorno, validar la carpeta, la base de
Rowino de mentira, la cookie, las cabeceras del intermediario y el sembrado de
cuentas sobre una base temporal). Levantarla de verdad se hace a mano.
"""
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

import config
import db
import economia
from herramientas import pagina_de_prueba as pp
from web import sesion

REPO = Path(__file__).resolve().parent.parent


# --- La carpeta -------------------------------------------------------------

def test_la_carpeta_puede_no_existir_o_estar_vacia(tmp_path):
    assert pp.validar_carpeta(tmp_path / "nueva", REPO) == (tmp_path / "nueva").resolve()
    (tmp_path / "vacia").mkdir()
    assert pp.validar_carpeta(tmp_path / "vacia", REPO) == (tmp_path / "vacia").resolve()


def test_la_carpeta_con_algo_dentro_se_niega(tmp_path):
    (tmp_path / "usada").mkdir()
    (tmp_path / "usada" / "algo.txt").write_text("x")
    with pytest.raises(pp.NoSePuede):
        pp.validar_carpeta(tmp_path / "usada", REPO)
    (tmp_path / "archivo").write_text("x")
    with pytest.raises(pp.NoSePuede):
        pp.validar_carpeta(tmp_path / "archivo", REPO)


def test_la_carpeta_dentro_del_repo_se_niega(tmp_path):
    for dentro in (REPO, REPO / "nueva", REPO / "web" / "nueva"):
        with pytest.raises(pp.NoSePuede):
            pp.validar_carpeta(dentro, REPO)
    # Ni con un rodeo por `..` ni por un enlace.
    with pytest.raises(pp.NoSePuede):
        pp.validar_carpeta(REPO / "web" / ".." / "nueva", REPO)
    enlace = tmp_path / "enlace"
    enlace.symlink_to(REPO)
    with pytest.raises(pp.NoSePuede):
        pp.validar_carpeta(enlace / "nueva", REPO)


# --- Las bases y el entorno --------------------------------------------------

@pytest.mark.parametrize("nombre", ["RUTA_BD", "RUTA_ROWINO_BD"])
def test_se_niega_si_ya_hay_una_base_en_el_entorno(nombre):
    with pytest.raises(pp.NoSePuede):
        pp.exigir_entorno_sin_bases({nombre: "otra.db"})
    pp.exigir_entorno_sin_bases({"PATH": "/usr/bin"})   # sin ellas, bien


def test_el_entorno_de_la_web_es_el_de_la_carpeta_y_nada_mas(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "secreto-del-bot")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "otro-secreto")
    entorno = pp.entorno_de_la_web(tmp_path, 777)
    assert entorno["RUTA_BD"] == str(tmp_path / "juego.db")
    assert entorno["RUTA_ROWINO_BD"] == str(tmp_path / "rowino.db")
    assert entorno["GUILD_WEB"] == "777"
    assert entorno["ROWINO_SECRET_KEY"]
    # No hereda nada: ni los secretos del bot ni nada que lo apunte a otra base.
    assert not (set(entorno) - {"RUTA_BD", "RUTA_ROWINO_BD", "ROWINO_SECRET_KEY", "GUILD_WEB",
                                "PATH", "PYTHONDONTWRITEBYTECODE", "LANG"})
    assert "secreto-del-bot" not in entorno.values() and "otro-secreto" not in entorno.values()


def test_la_clave_de_sesion_se_inventa_en_cada_arranque_y_no_se_acepta_de_fuera(tmp_path, monkeypatch):
    monkeypatch.setenv("ROWINO_SECRET_KEY", "la-clave-de-verdad")
    una, otra = pp.entorno_de_la_web(tmp_path, 777), pp.entorno_de_la_web(tmp_path, 777)
    assert una["ROWINO_SECRET_KEY"] != otra["ROWINO_SECRET_KEY"]
    assert "la-clave-de-verdad" not in (una["ROWINO_SECRET_KEY"], otra["ROWINO_SECRET_KEY"])
    assert len(una["ROWINO_SECRET_KEY"]) >= 32
    with pytest.raises(TypeError):
        pp.entorno_de_la_web(tmp_path, 777, "una-clave")          # ni por parámetro
    with pytest.raises(SystemExit):
        pp.leer_argumentos(["--carpeta", "x", "--clave", "una-clave"])   # ni por la línea de órdenes


def test_el_entorno_de_la_web_no_lee_el_env_del_repo(tmp_path):
    """La web arranca desde una copia de `git archive`, que no trae `.env`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(git + ["init", "-q"], check=True)
    (repo / ".gitignore").write_text(".env\n")
    (repo / "codigo.py").write_text("x = 1\n")
    (repo / ".env").write_text("DISCORD_TOKEN=secreto\n")
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "uno"], check=True)
    (repo / "sin_commit.py").write_text("y = 2\n")
    copia = tmp_path / "carpeta" / "copia"
    pp.copiar_del_repo(repo, copia)
    assert (copia / "codigo.py").read_text() == "x = 1\n"
    assert not (copia / ".env").exists() and not (copia / "sin_commit.py").exists()


# --- Rowino de mentira y la cookie ---------------------------------------------

def test_la_base_de_rowino_de_mentira_tiene_ids_chicos_y_sinteticos(tmp_path, monkeypatch):
    pp.crear_rowino(tmp_path / "rowino.db", 4)
    filas = sqlite3.connect(tmp_path / "rowino.db").execute(
        "SELECT id, username, blocked FROM users ORDER BY id").fetchall()
    assert filas == [(1, "persona1", 0), (2, "persona2", 0), (3, "persona3", 0), (4, "persona4", 0)]
    # Es una base que el servicio sabe leer.
    monkeypatch.setattr(config, "RUTA_ROWINO_BD", tmp_path / "rowino.db")
    assert sesion.buscar_persona(3) == sesion.Persona(3, "persona3")
    assert sesion.buscar_persona(5) is None


def test_la_cookie_firmada_la_acepta_la_web_con_esa_clave_y_con_ninguna_otra(monkeypatch):
    monkeypatch.setattr(config, "ROWINO_SECRET_KEY", "clave-uno")
    assert sesion.leer_cookie(pp.firmar_cookie(2, "clave-uno")) == 2
    assert sesion.leer_cookie(pp.firmar_cookie(2, "clave-dos")) is None


# --- Dónde escucha y qué puertos --------------------------------------------

def test_sólo_se_escucha_en_local():
    assert pp.DIRECCION == "127.0.0.1"
    assert "127.0.0.1" == pp.orden_de_la_web(8421)[pp.orden_de_la_web(8421).index("--host") + 1]
    intermediario = pp.crear_intermediario(0, 8421, "cookie")
    try:
        assert intermediario.server_address[0] == "127.0.0.1"
    finally:
        intermediario.server_close()


def test_los_puertos_reservados_se_niegan():
    pp.validar_puertos(pp.PUERTO_POR_DEFECTO, 3)
    for puerto in (8000, 8010, 8011, 8061, 8497, 9950, 9960, 80):
        with pytest.raises(pp.NoSePuede):
            pp.validar_puertos(puerto, 1)
    with pytest.raises(pp.NoSePuede):      # el intermediario de la cuenta 3 cae en 8011
        pp.validar_puertos(8008, 3)
    with pytest.raises(pp.NoSePuede):
        pp.validar_puertos(pp.PUERTO_POR_DEFECTO, 0)
    with pytest.raises(pp.NoSePuede):
        pp.validar_puertos(pp.PUERTO_POR_DEFECTO, pp.MAX_CUENTAS + 1)


def test_el_intermediario_cambia_la_cookie_y_el_destino_y_deja_pasar_lo_demas():
    entrantes = [
        ("Host", "127.0.0.1:8422"), ("Cookie", "session=de-otra-cuenta; otra=1"),
        ("X-Gachamon", "1"), ("Content-Type", "application/json"), ("Content-Length", "2"),
        ("Connection", "keep-alive"), ("Accept", "*/*"), ("If-None-Match", '"abc"'),
    ]
    saliente = pp.cabeceras_para_la_web(entrantes, "session=nueva", "127.0.0.1:8421")
    assert saliente == {
        "Host": "127.0.0.1:8421", "Cookie": "session=nueva", "X-Gachamon": "1",
        "Content-Type": "application/json", "Accept": "*/*", "If-None-Match": '"abc"',
    }
    vuelta = pp.cabeceras_para_el_navegador([
        ("Location", "/monsteropolis/"), ("Set-Cookie", "a=1"), ("Content-Type", "text/html"),
        ("Content-Length", "10"), ("Transfer-Encoding", "chunked"), ("Date", "x"), ("Server", "uvicorn"),
    ])
    assert vuelta == [("Location", "/monsteropolis/"), ("Set-Cookie", "a=1"), ("Content-Type", "text/html")]


# --- Cuentas con algo dentro --------------------------------------------------

def test_con_gachamones_las_cuentas_traen_plantel_muebles_y_saldo(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    pp.sembrar([1, 2], 777)
    for uid in (1, 2):
        cuenta = db.cuenta_web(uid)
        assert cuenta is not None and cuenta.guild_id == "777"
        plantel = db.plantel(cuenta.usuario_id, cuenta.guild_id)
        assert len(plantel) == pp.GACHAMONES_POR_CUENTA
        assert sum(1 for c in plantel if c.activa) == 1
        assert all(not c.se_nombro_solo or not c.activa for c in plantel)
        depto = db.departamento_leido(cuenta.usuario_id, cuenta.guild_id)
        assert len(depto.puestas) > 3 and depto.camas_puestas >= pp.GACHAMONES_POR_CUENTA
        assert db.avatar_de(cuenta.usuario_id, cuenta.guild_id) is not None
        saldos = economia.saldos(cuenta.usuario_id, cuenta.guild_id)
        assert saldos.asciicoins > 0 and saldos.asciigems > 0
    # Cada cuenta es suya: nada compartido entre las dos.
    assert db.cuenta_web(1).usuario_id != db.cuenta_web(2).usuario_id
    assert db.cuenta_web(3) is None


def test_el_arranque_de_la_web_no_toca_lo_sembrado(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    pp.sembrar([1], 777)
    cuenta = db.cuenta_web(1)
    antes = [(c.id, c.nombre, c.especie) for c in db.plantel(cuenta.usuario_id, cuenta.guild_id)]
    saldos = economia.saldos(cuenta.usuario_id, cuenta.guild_id)
    economia.poner_al_dia(db.ahora_utc())     # lo que hace la web al arrancar
    assert [(c.id, c.nombre, c.especie) for c in db.plantel(cuenta.usuario_id, cuenta.guild_id)] == antes
    assert economia.saldos(cuenta.usuario_id, cuenta.guild_id) == saldos


def test_sembrar_dos_veces_la_misma_base_se_niega(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    pp.sembrar([1], 777)
    with pytest.raises(pp.NoSePuede):
        pp.sembrar([1], 777)


def test_nada_de_esto_toca_el_entorno_del_proceso():
    assert "RUTA_BD" not in os.environ and "RUTA_ROWINO_BD" not in os.environ


# --- Arreglos de la revisión final -----------------------------------------------

def test_un_puerto_ocupado_se_niega_antes_de_lanzar_nada():
    ocupado = socket.socket()
    ocupado.bind(("127.0.0.1", 0))
    ocupado.listen()
    puerto = ocupado.getsockname()[1]
    try:
        for desde in (puerto, puerto - 1, puerto - 2):   # la web o alguna de las cuentas
            with pytest.raises(pp.NoSePuede, match=f"El puerto {puerto} está ocupado"):
                pp.exigir_puertos_libres(desde, 2)
    finally:
        ocupado.close()
    pp.exigir_puertos_libres(puerto, 1)   # ya libre


def test_sembrar_se_niega_sobre_una_base_dentro_del_repo(monkeypatch):
    monkeypatch.setattr(db, "RUTA", REPO / "no-se-crea.db")
    with pytest.raises(pp.NoSePuede):
        pp.sembrar([1], 777)
    assert not (REPO / "no-se-crea.db").exists()


def test_el_sembrado_corre_el_archivo_de_la_copia(tmp_path):
    orden = pp.orden_del_sembrado(tmp_path / "copia", 2, 777)
    assert str(tmp_path / "copia" / "herramientas" / "pagina_de_prueba.py") in orden
    assert str(Path(pp.__file__).resolve()) not in orden


def test_tras_sembrar_la_entrada_de_cada_cuenta_no_tiene_bultos(tmp_path, monkeypatch):
    import departamento as dep

    monkeypatch.setattr(db, "RUTA", tmp_path / "juego.db")
    pp.sembrar([1, 2], 777)
    for uid in (1, 2):
        cuenta = db.cuenta_web(uid)
        depto = db.departamento_leido(cuenta.usuario_id, cuenta.guild_id)
        puerta = next(p for p in depto.puestas if p.clave == dep.PUERTA)
        entrada = dep.frente_a(puerta.x, puerta.y)
        bultos = [p for p in depto.puestas
                  if dep.MUEBLES[p.clave].capa == dep.BULTO
                  and entrada in dep.huella(dep.MUEBLES[p.clave], p.x, p.y, p.giro)]
        assert bultos == []


def test_las_senales_de_apagado_hacen_lo_que_ctrl_c():
    with pytest.raises(KeyboardInterrupt):
        pp._como_ctrl_c(signal.SIGTERM, None)


def test_main_no_saca_traza_si_lo_interrumpen_durante_el_arranque(monkeypatch, capsys):
    def interrumpida(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(pp, "ejecutar", interrumpida)
    assert pp.main(["--carpeta", "x"]) == 130
    assert "Interrumpida" in capsys.readouterr().err


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="sólo Linux")
def test_la_web_muere_si_matan_a_la_herramienta_sin_avisar():
    guion = (
        "import subprocess, sys, time\n"
        "from herramientas import pagina_de_prueba as pp\n"
        "hijo = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],\n"
        "                        start_new_session=True, preexec_fn=pp._morir_con_el_padre)\n"
        "print(hijo.pid, flush=True)\n"
        "time.sleep(60)\n"
    )
    padre = subprocess.Popen([sys.executable, "-c", guion], cwd=REPO, stdout=subprocess.PIPE, text=True)
    try:
        hijo = int(padre.stdout.readline())
        padre.kill()
        padre.wait()
        for _ in range(50):
            try:
                os.kill(hijo, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
        os.kill(hijo, signal.SIGKILL)
        pytest.fail("el hijo siguió vivo tras morir su padre")
    finally:
        padre.kill()
