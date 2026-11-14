#!/bin/bash
# Deja la Raspberry exactamente en lo que haya en GitHub.
#
#   ./actualizar-pi.sh                 # lo normal
#   SIN_TESTS=1 ./actualizar-pi.sh     # sin correr la suite en la Pi
#   RAMA=otra ./actualizar-pi.sh       # otra rama
#   PI=usuario@ip DEST=/ruta ./actualizar-pi.sh
#
# Frente a `deploy.sh`, que copia ESTA carpeta: aquí la Pi se baja el código de
# GitHub por su cuenta. Es lo que evita el desfase de desplegar una copia local
# que no está al día con `main`.
#
# El .env, la base de datos y el venv viven sólo en la Pi y están en .gitignore,
# así que `git reset --hard` no los toca. Aun así se copia el .db antes.
#
# Mientras dura, la web no contesta: se para antes de tocar sus archivos (unos
# segundos con SIN_TESTS=1; con la suite en la Pi, unos minutos).
set -euo pipefail

PI="${PI:-felipe@192.168.1.109}"
DEST="${DEST:-/home/felipe/tamagotchi-bot}"
RAMA="${RAMA:-main}"
REMOTO_URL="${REMOTO_URL:-https://github.com/FelipeBallesteros0/Gachamones-BOT.git}"
SIN_TESTS="${SIN_TESTS:-}"

# --- Avisar si hay trabajo sin subir ---------------------------------------
# Es justo el desfase que este script viene a evitar: la Pi baja de GitHub, así
# que lo que no esté empujado no llega. Callárselo sería repetir el problema.
if git rev-parse --git-dir >/dev/null 2>&1; then
    git fetch -q origin "$RAMA" 2>/dev/null || true
    sin_subir="$(git rev-list --count "origin/$RAMA..HEAD" 2>/dev/null || echo 0)"
    if [ "$sin_subir" != "0" ]; then
        echo "⚠️  Tienes $sin_subir commit(s) sin subir a origin/$RAMA."
        echo "    La Pi baja de GitHub, así que NO los va a ver."
        read -r -p "    ¿Sigo de todas formas? [s/N] " respuesta
        [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ] || { echo "Cancelado."; exit 1; }
    fi
fi

echo "==> Actualizando $PI:$DEST desde $RAMA"

ssh "$PI" "bash -s" <<REMOTO
set -euo pipefail
cd '$DEST'

# Una copia de las mascotas antes de tocar nada. Cuesta un segundo y es la
# diferencia entre un susto y una pérdida. Se guardan las 5 últimas: si no, se
# acumula una por despliegue y acaban ocupando más que la propia base.
if [ -f tamagotchi.db ]; then
    copia="tamagotchi.db.\$(date +%Y%m%d-%H%M%S).bak"
    cp tamagotchi.db "\$copia"
    echo "    copia de seguridad: \$copia"
    ls -1t tamagotchi.db.*.bak 2>/dev/null | tail -n +6 | xargs -r rm --
fi

if [ ! -d .git ]; then
    echo "    primera vez: convirtiendo en clon de git"
    git init -q
    git remote add origin '$REMOTO_URL'
fi
git remote set-url origin '$REMOTO_URL'

# Dónde estaba la Pi, para volver ahí si la suite sale en rojo. La primera vez
# no hay commit al que volver, y se borra el apunte de un intento anterior.
if git rev-parse -q --verify HEAD >/dev/null; then
    git rev-parse HEAD > .git/gachamon-anterior
else
    rm -f .git/gachamon-anterior
fi

git fetch -q origin '$RAMA'

# La web se para antes de tocar sus archivos. Sus estáticos versionados se
# guardan un año como inmutables: si el proceso viejo siguiera en marcha,
# serviría los archivos nuevos bajo su versión vieja, y navegadores y
# Cloudflare se quedarían con copias mezcladas. Vuelve a arrancar con el
# reinicio del final o, si la suite sale en rojo, en la Pi después de volver al
# commit de antes. El bot sigue: no sirve archivos. La primera vez la unidad
# aún no está instalada y no hay nada que parar.
if [ -f /etc/systemd/system/gachamon-web.service ]; then
    echo "    la web se para mientras cambian sus archivos"
    sudo systemctl stop gachamon-web
fi

# --hard sobre los ficheros versionados; los ignorados (.env, *.db, venv/) no se
# tocan. Es lo que hace que esto sea repetible y no dependa del estado previo.
git reset -q --hard "origin/$RAMA"

{ [ -d venv ] || python3 -m venv venv; }
# La suite necesita pytest y httpx, que sólo están en requirements-dev.txt (que
# ya incluye a requirements.txt). Sin suite, basta con lo de producción.
if [ -z '$SIN_TESTS' ]; then
    requisitos=requirements-dev.txt
else
    requisitos=requirements.txt
fi
./venv/bin/python -m pip install -q -r "\$requisitos"

echo "    en el commit: \$(git rev-parse --short HEAD) \$(git log -1 --format=%s)"
REMOTO

if [ -z "$SIN_TESTS" ]; then
    echo "==> Tests en la Pi (SIN_TESTS=1 para saltarlos)"
    # Orden remota: con pipefail, el estado del pipe es el de pytest y no el de
    # `tail`; se guarda en `estado` y se borra el temporal (también si la suite
    # falla). En rojo, si hay un commit apuntado, la Pi vuelve a él y reinstala
    # sus requisitos; y, haya vuelto o no, arranca la web, que se paró antes de
    # tocar los archivos y aquí no llega al reinicio del final. Se sale con el
    # estado de pytest. Los \$ son de la Pi, no de aquí. La política es
    # `failed` y no `none`: sólo `failed` borra la carpeta de cada prueba que
    # pasa; con `none` el temporal en memoria crece.
    ssh "$PI" "set -o pipefail; cd '$DEST' && ./venv/bin/python -m pytest --basetemp=/dev/shm/gachamon-pytest -o tmp_path_retention_policy=failed tests/ -q 2>&1 | tail -3; estado=\$?; rm -rf /dev/shm/gachamon-pytest; if [ \$estado -ne 0 ] && [ -s .git/gachamon-anterior ]; then anterior=\$(cat .git/gachamon-anterior); echo \"    la suite salió en rojo: la Pi vuelve a \$anterior\"; git reset -q --hard \"\$anterior\" && ./venv/bin/python -m pip install -q -r requirements.txt; fi; if [ \$estado -ne 0 ]; then sudo systemctl start gachamon-web; fi; exit \$estado"
fi

# Los servicios se reinician al final y sólo si todo lo anterior salió bien:
# con `set -e` aquí y `set -o pipefail` en la orden remota, una suite en rojo
# hace que `ssh` devuelva el estado de pytest (y no el de `tail`) y el guion
# corta sin reiniciar. Antes de cortar, la Pi vuelve al commit en el que estaba
# y reinstala su `requirements.txt`, así que en disco queda el código que corre
# el bot en marcha, y un reinicio posterior del servicio o de la máquina
# levanta esa versión y no la que salió en rojo; y arranca la web, que calcula
# su versión con los archivos que encuentra al arrancar. La primera vez no hay
# commit anterior y el código nuevo se queda. La web está parada desde antes de
# tocar los archivos (ver el bloque remoto): aquí la arranca su `restart`.
echo "==> Reiniciando los servicios (primero el bot, después la web)"
TTY_FLAG=""
[ -t 0 ] && TTY_FLAG="-t"
ssh $TTY_FLAG "$PI" "sudo cp '$DEST/tamagotchi.service' /etc/systemd/system/tamagotchi.service && \
    sudo cp '$DEST/gachamon-web.service' /etc/systemd/system/gachamon-web.service && \
    sudo systemctl daemon-reload && \
    sudo systemctl enable tamagotchi gachamon-web && \
    sudo systemctl restart tamagotchi && \
    sudo systemctl restart gachamon-web && \
    sleep 3 && systemctl is-active tamagotchi && systemctl is-active gachamon-web && \
    curl -fsS --retry 10 --retry-delay 1 --retry-connrefused -o /dev/null http://127.0.0.1:8010/gachamon/api/salud"

echo
echo "Listo. Registro en vivo:  ssh $PI 'journalctl -u tamagotchi -u gachamon-web -f'"
