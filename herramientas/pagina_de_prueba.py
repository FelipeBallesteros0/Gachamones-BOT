"""Levanta una página de prueba del juego sobre bases de mentira.

Se corre con `./venv/bin/python -m herramientas.pagina_de_prueba --carpeta <carpeta nueva>`.

Qué hace, y qué nunca hace:

- Saca una copia del último commit con `git archive` dentro de la carpeta y
  arranca la web desde ahí: nunca desde el directorio de trabajo, así que no
  lee su `.env` ni su base.
- La base del juego y la de Rowino de mentira viven en la carpeta. La clave de
  la sesión se inventa en cada arranque y no se puede dar de fuera.
- Por cada cuenta de mentira abre un puerto propio, `127.0.0.1:<puerto>`, que
  reenvía todo a la web y le pone la cookie firmada de esa cuenta: abrir
  `/gachamon/` en ese puerto es entrar como esa persona.
- Sólo escucha en `127.0.0.1`.
- Con `--con-gachamones`, antes de levantar la web, a cada cuenta le da avatar,
  monedas, muebles y algunos gachamones usando las reglas del propio juego.

Escribe en la carpeta `pids` (la herramienta y la web) y dice cómo apagarla.
"""
from __future__ import annotations

import argparse
import ctypes
import http.client
import http.server
import os
import random
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time
from datetime import timedelta
from pathlib import Path

from itsdangerous import URLSafeSerializer

REPO = Path(__file__).resolve().parent.parent
DIRECCION = "127.0.0.1"
PUERTO_POR_DEFECTO = 8421
CUENTAS_POR_DEFECTO = 3
MAX_CUENTAS = 20
GUILD_DE_PRUEBA = 777
GACHAMONES_POR_CUENTA = 3

# Los usa el dueño o producción: ni la web ni los intermediarios caen en ellos.
RESERVADOS = frozenset({8000, 8010, 8011, 8061, 8497, *range(9950, 9961)})
MUEBLES_DE_PRUEBA = (
    "maceta", "cuadro", "lampara", "alfombra", "refrigerador", "consola", "ducha", "pesas",
)
MONEDAS_DE_PRUEBA = 4000
GEMAS_DE_PRUEBA = 60

# Cabeceras que no se reenvían tal cual: las fija cada salto.
_SALTO_A_SALTO = {"connection", "keep-alive", "transfer-encoding", "te", "upgrade",
                  "proxy-authorization", "proxy-connection", "trailer"}
_PROPIAS_DE_LA_RESPUESTA = {"date", "server", "content-length"}


class NoSePuede(Exception):
    """Algo que la herramienta se niega a hacer, dicho para quien la corre."""


# --- Validaciones ---------------------------------------------------------------

def validar_carpeta(carpeta: Path, repo: Path = REPO) -> Path:
    """La carpeta resuelta, si no existe o está vacía y no cae dentro del repo."""
    carpeta = Path(carpeta).resolve()
    repo = Path(repo).resolve()
    if carpeta == repo or repo in carpeta.parents:
        raise NoSePuede("La carpeta no puede estar dentro del repositorio.")
    if carpeta.exists() and (not carpeta.is_dir() or any(carpeta.iterdir())):
        raise NoSePuede("La carpeta tiene que no existir o estar vacía.")
    return carpeta


def exigir_entorno_sin_bases(entorno) -> None:
    """Se niega si el entorno ya apunta a una base: esa podría ser la de verdad."""
    for nombre in ("RUTA_BD", "RUTA_ROWINO_BD"):
        if nombre in entorno:
            raise NoSePuede(
                f"{nombre} está puesta en el entorno; quítala para correr esta herramienta."
            )


def validar_puertos(puerto: int, cuentas: int) -> None:
    if not 1 <= cuentas <= MAX_CUENTAS:
        raise NoSePuede(f"Las cuentas van de 1 a {MAX_CUENTAS}.")
    usados = range(puerto, puerto + cuentas + 1)
    if puerto < 1024 or usados[-1] > 65535:
        raise NoSePuede("El puerto tiene que estar entre 1024 y 65535, con sitio para las cuentas.")
    if RESERVADOS.intersection(usados):
        raise NoSePuede("Esos puertos incluyen alguno reservado; elige otro rango.")


def exigir_puertos_libres(puerto: int, cuentas: int) -> None:
    """Se niega si algún puerto de la web o de las cuentas ya está en uso en local."""
    for candidato in range(puerto, puerto + cuentas + 1):
        with socket.socket() as prueba:
            prueba.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                prueba.bind((DIRECCION, candidato))
            except OSError:
                raise NoSePuede(f"El puerto {candidato} está ocupado.") from None


def leer_argumentos(argv=None) -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        prog="python -m herramientas.pagina_de_prueba", description=__doc__.split("\n\n")[0],
    )
    analizador.add_argument("--carpeta", required=True, type=Path,
                            help="carpeta nueva (o vacía), fuera del repo, donde viven las bases")
    analizador.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO,
                            help="puerto de la web; las cuentas usan los siguientes")
    analizador.add_argument("--cuentas", type=int, default=CUENTAS_POR_DEFECTO,
                            help=f"cuántas cuentas de mentira (1 a {MAX_CUENTAS})")
    analizador.add_argument("--con-gachamones", action="store_true",
                            help="a cada cuenta, avatar, monedas, muebles y algunos gachamones")
    return analizador.parse_args(argv)


# --- La web y sus bases ------------------------------------------------------------

def entorno_de_la_web(carpeta: Path, guild: int) -> dict[str, str]:
    """El entorno de la web y nada más: no hereda secretos ni bases de quien la lanza."""
    entorno = {
        "RUTA_BD": str(Path(carpeta) / "juego.db"),
        "RUTA_ROWINO_BD": str(Path(carpeta) / "rowino.db"),
        "ROWINO_SECRET_KEY": secrets.token_urlsafe(32),
        "GUILD_WEB": str(guild),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if "LANG" in os.environ:
        entorno["LANG"] = os.environ["LANG"]
    return entorno


def copiar_del_repo(repo: Path, destino: Path) -> None:
    """Deja en `destino` el último commit de `repo`: lo que `.gitignore` y `git archive` dejan fuera, no viaja."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    proceso = subprocess.Popen(
        ["git", "-C", str(repo), "archive", "--format=tar", "HEAD"],
        stdout=subprocess.PIPE,
    )
    with tarfile.open(fileobj=proceso.stdout, mode="r|") as tar:
        tar.extractall(destino, filter="data")
    if proceso.wait() != 0:
        raise NoSePuede("`git archive HEAD` falló.")


def crear_rowino(ruta: Path, cuentas: int) -> None:
    """La base de Rowino de mentira: personas 1..cuentas, sin bloquear."""
    import sqlite3

    con = sqlite3.connect(ruta)
    try:
        con.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, "
            "blocked INTEGER NOT NULL DEFAULT 0)"
        )
        con.executemany(
            "INSERT INTO users VALUES (?, ?, 0)",
            [(n, f"persona{n}") for n in range(1, cuentas + 1)],
        )
        con.commit()
    finally:
        con.close()


def firmar_cookie(uid: int, clave: str) -> str:
    """El valor de la cookie `session` tal como lo firma Rowino."""
    return URLSafeSerializer(clave, salt="session").dumps({"uid": uid})


def orden_de_la_web(puerto: int) -> list[str]:
    return [sys.executable, "-B", "-m", "uvicorn", "web.app:app",
            "--host", DIRECCION, "--port", str(puerto)]


# --- El intermediario --------------------------------------------------------------

def cabeceras_para_la_web(entrantes, cookie: str, destino: str) -> dict[str, str]:
    """Las cabeceras de la petición reenviada: la cookie es la de la cuenta, el resto pasa."""
    saliente: dict[str, str] = {}
    for nombre, valor in entrantes:
        minuscula = nombre.lower()
        if minuscula in _SALTO_A_SALTO or minuscula in ("host", "cookie", "content-length"):
            continue
        saliente[nombre] = valor
    saliente["Host"] = destino
    saliente["Cookie"] = cookie
    return saliente


def cabeceras_para_el_navegador(recibidas) -> list[tuple[str, str]]:
    """Las de la respuesta, tal cual (con sus redirecciones y cookies), sin las que fija cada salto."""
    return [(n, v) for n, v in recibidas
            if n.lower() not in _SALTO_A_SALTO and n.lower() not in _PROPIAS_DE_LA_RESPUESTA]


def crear_intermediario(puerto: int, puerto_web: int, cookie: str) -> http.server.ThreadingHTTPServer:
    """Un servidor local que reenvía a la web poniendo `cookie` (`session=...`)."""
    destino = f"{DIRECCION}:{puerto_web}"

    class Reenviador(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _reenviar(self):
            largo = int(self.headers.get("Content-Length") or 0)
            cuerpo = self.rfile.read(largo) if largo else None
            cabeceras = cabeceras_para_la_web(self.headers.items(), cookie, destino)
            conexion = http.client.HTTPConnection(DIRECCION, puerto_web, timeout=60)
            try:
                conexion.request(self.command, self.path, body=cuerpo, headers=cabeceras)
                respuesta = conexion.getresponse()
                datos = respuesta.read()
                self.send_response(respuesta.status)
                for nombre, valor in cabeceras_para_el_navegador(respuesta.getheaders()):
                    self.send_header(nombre, valor)
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(datos)
            except OSError:
                self.send_error(502, "La web no contesta")
            finally:
                conexion.close()

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = _reenviar

    return http.server.ThreadingHTTPServer((DIRECCION, puerto), Reenviador)


# --- Cuentas con algo dentro -------------------------------------------------------

def _colocar(usuario_id: str, guild: str, mueble_id: int) -> None:
    """Pone ese mueble en la primera casilla donde las reglas lo dejan, sin tapar la entrada.

    La entrada es la casilla de dentro que queda frente a la puerta: ahí no se
    pone ningún mueble de bulto, porque el avatar no podría pasar.
    """
    import db
    import departamento as dep
    import economia

    depto = db.departamento_leido(usuario_id, guild)
    puerta = next(p for p in depto.puestas if p.clave == dep.PUERTA)
    entrada = dep.frente_a(puerta.x, puerta.y)
    mueble = dep.MUEBLES[next(p.clave for p in depto.piezas if p.id == mueble_id)]
    for y in range(-1, depto.fondo + 1):
        for x in range(-1, depto.ancho + 1):
            if mueble.capa == dep.BULTO and entrada in dep.huella(mueble, x, y, 0):
                continue
            if economia.poner_mueble(usuario_id, guild, mueble_id, x, y, 0).ok:
                return
    raise NoSePuede("No hay dónde poner un mueble de prueba.")


def _comprar_y_poner(usuario_id: str, guild: str, clave: str) -> None:
    import departamento as dep
    import economia

    hecho = economia.comprar_mueble(usuario_id, guild, dep.MUEBLES[clave])
    if not hecho.ok:
        raise NoSePuede(f"No se pudo comprar «{clave}» ({hecho.motivo}).")
    _colocar(usuario_id, guild, hecho.mueble_id)


def sembrar(uids, guild: int) -> None:
    """Cuentas de mentira con avatar, saldo, muebles y gachamones, por las reglas del juego.

    Va sobre la base a la que apunte `db.RUTA`, antes de que la web arranque, y
    se niega si ya hay una de esas cuentas. Hace el día del cambio un día antes
    de ahora, como las pruebas: así quienes nacen después son jugadores nuevos
    y el arranque de la web ya no tiene nada que hacer.
    """
    import avatar as av
    import db
    import departamento as dep
    import economia
    import especies as esp
    import nacer
    import personalidad as per

    if Path(db.RUTA).resolve().is_relative_to(REPO):
        raise NoSePuede("La base está dentro del repositorio: no se siembra ahí.")
    ahora = db.ahora_utc()
    economia.poner_al_dia(ahora - timedelta(days=1))
    if any(db.cuenta_web(uid) is not None for uid in uids):
        raise NoSePuede("Esas cuentas ya existen en esta base.")
    guild_id = str(guild)
    for uid in uids:
        rng = random.Random(uid)
        cuenta = db.crear_identidad_web(uid, guild_id, ahora)
        yo = cuenta.usuario_id
        db.guardar_avatar(
            yo, guild_id,
            av.Avatar(f"Persona{uid}", "hembra", "clara", "largo", "rojo", "camisa"), ahora,
        )
        economia.otorgar_hallazgo(f"prueba-{uid}", yo, guild_id,
                                  MONEDAS_DE_PRUEBA, GEMAS_DE_PRUEBA, ahora)
        depto = db.departamento_de(yo, guild_id, ahora)
        guardada = next(p for p in depto.guardadas if dep.MUEBLES[p.clave].cama)
        _colocar(yo, guild_id, guardada.id)
        nacer.encontrar_al_primero(yo, guild_id, ahora, rng)
        nacer.bautizar(yo, guild_id, "Pelusa", ahora)
        for eje in (dep.ANCHO, dep.FONDO, dep.ANCHO, dep.FONDO):
            economia.ampliar_departamento(yo, guild_id, eje)
        while len(db.plantel(yo, guild_id)) < GACHAMONES_POR_CUENTA:
            depto = db.departamento_leido(yo, guild_id)
            if not dep.cama_libre(depto, len(db.plantel(yo, guild_id))):
                _comprar_y_poner(yo, guild_id, "cama_sencilla")
                continue
            especie = esp.elegir_del_huevo(rng)
            nacer.unir_recluta(
                yo, guild_id, especie=especie.clave,
                stats=esp.tirar_stats_iniciales(especie, rng), genero=esp.tirar_genero(rng),
                caracter=per.tirar_caracter(rng), ahora=ahora, rng=rng,
            )
        for clave in MUEBLES_DE_PRUEBA:
            _comprar_y_poner(yo, guild_id, clave)


# --- Arrancar y apagar -------------------------------------------------------------

_ARRANQUE_DEL_SEMBRADO = (
    "import importlib.util, sys\n"
    "copia, herramienta, cuentas, guild = sys.argv[1:5]\n"
    "sys.path.insert(0, copia)\n"
    "spec = importlib.util.spec_from_file_location('pagina_de_prueba', herramienta)\n"
    "modulo = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(modulo)\n"
    "modulo.sembrar(range(1, int(cuentas) + 1), int(guild))\n"
)


def orden_del_sembrado(copia: Path, cuentas: int, guild: int) -> list[str]:
    """El subproceso que siembra: corre la herramienta de la copia, no la del árbol de trabajo."""
    return [sys.executable, "-I", "-c", _ARRANQUE_DEL_SEMBRADO, str(copia),
            str(copia / "herramientas" / "pagina_de_prueba.py"), str(cuentas), str(guild)]


def _esperar_a_la_web(puerto: int, web: subprocess.Popen, registro: Path) -> None:
    limite = time.monotonic() + 90
    while time.monotonic() < limite:
        if web.poll() is not None:
            break
        try:
            conexion = http.client.HTTPConnection(DIRECCION, puerto, timeout=2)
            conexion.request("GET", "/gachamon/")
            if conexion.getresponse().status == 200:
                return
        except OSError:
            pass
        time.sleep(0.5)
    ultimas = registro.read_text(errors="replace").splitlines()[-15:]
    raise NoSePuede("La web no contestó:\n" + "\n".join(ultimas))


def _como_ctrl_c(*_) -> None:
    raise KeyboardInterrupt


def _morir_con_el_padre() -> None:
    """En Linux, la web muere también si a la herramienta la matan sin avisar."""
    if sys.platform.startswith("linux"):
        ctypes.CDLL(None).prctl(1, signal.SIGTERM)   # PR_SET_PDEATHSIG


def ejecutar(argumentos: argparse.Namespace) -> int:
    exigir_entorno_sin_bases(os.environ)
    validar_puertos(argumentos.puerto, argumentos.cuentas)
    exigir_puertos_libres(argumentos.puerto, argumentos.cuentas)
    carpeta = validar_carpeta(argumentos.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    copia = carpeta / "copia"
    copiar_del_repo(REPO, copia)
    entorno = entorno_de_la_web(carpeta, GUILD_DE_PRUEBA)
    crear_rowino(carpeta / "rowino.db", argumentos.cuentas)

    if argumentos.con_gachamones:
        sembrado = subprocess.run(
            orden_del_sembrado(copia, argumentos.cuentas, GUILD_DE_PRUEBA),
            cwd=copia, env=entorno, capture_output=True, text=True,
        )
        if sembrado.returncode != 0:
            raise NoSePuede("No se pudieron sembrar las cuentas:\n" + sembrado.stderr[-1500:])

    # Desde aquí, cerrar la terminal o un `kill` hacen lo mismo que Ctrl-C.
    for senal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(senal, _como_ctrl_c)
    registro = carpeta / "web.log"
    web = None

    def apagar():
        if web is not None and web.poll() is None:
            web.terminate()
            try:
                web.wait(10)
            except subprocess.TimeoutExpired:
                web.kill()

    try:
        with registro.open("wb") as salida:
            web = subprocess.Popen(
                orden_de_la_web(argumentos.puerto), cwd=copia, env=entorno,
                stdout=salida, stderr=subprocess.STDOUT, start_new_session=True,
                preexec_fn=_morir_con_el_padre,
            )
        (carpeta / "pids").write_text(f"{os.getpid()} {web.pid}\n")
        _esperar_a_la_web(argumentos.puerto, web, registro)
        for uid in range(1, argumentos.cuentas + 1):
            servidor = crear_intermediario(
                argumentos.puerto + uid, argumentos.puerto,
                "session=" + firmar_cookie(uid, entorno["ROWINO_SECRET_KEY"]),
            )
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
    except BaseException:
        apagar()
        raise

    print("Página de prueba lista (bases de mentira, sin tocar las de verdad).")
    for uid in range(1, argumentos.cuentas + 1):
        print(f"  persona{uid}: http://{DIRECCION}:{argumentos.puerto + uid}/gachamon/")
    print(f"Carpeta: {carpeta}")
    print(f"Para apagarla: Ctrl-C, cerrar la terminal, o `kill {os.getpid()}` (apaga también la web, pid {web.pid}).")
    print("Los pids quedan en el archivo `pids` de la carpeta.")
    sys.stdout.flush()

    try:
        while web.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    apagar()
    print("Apagada.")
    return 0


def main(argv=None) -> int:
    argumentos = leer_argumentos(argv)
    try:
        return ejecutar(argumentos)
    except NoSePuede as error:
        print(f"No se puede: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrumpida; la web queda apagada.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
