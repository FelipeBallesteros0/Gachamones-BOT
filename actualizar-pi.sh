#!/bin/bash
# Deja la Raspberry exactamente en lo que haya en GitHub.
#
#   ./actualizar-pi.sh                 # lo normal
#   SIN_TESTS=1 ./actualizar-pi.sh     # sin correr la suite en la Pi (~50 s)
#   RAMA=otra ./actualizar-pi.sh       # otra rama
#   PI=usuario@ip DEST=/ruta ./actualizar-pi.sh
#
# Frente a `deploy.sh`, que copia ESTA carpeta: aquí la Pi se baja el código de
# GitHub por su cuenta. Es lo que evita el desfase de desplegar una copia local
# que no está al día con `main`.
#
# El .env, la base de datos y el venv viven sólo en la Pi y están en .gitignore,
# así que `git reset --hard` no los toca. Aun así se copia el .db antes.
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

git fetch -q origin '$RAMA'
# --hard sobre los ficheros versionados; los ignorados (.env, *.db, venv/) no se
# tocan. Es lo que hace que esto sea repetible y no dependa del estado previo.
git reset -q --hard "origin/$RAMA"

{ [ -d venv ] || python3 -m venv venv; }
./venv/bin/python -m pip install -q -r requirements.txt

echo "    en el commit: \$(git rev-parse --short HEAD) \$(git log -1 --format=%s)"
REMOTO

if [ -z "$SIN_TESTS" ]; then
    echo "==> Tests en la Pi (SIN_TESTS=1 para saltarlos)"
    ssh "$PI" "cd '$DEST' && ./venv/bin/python -m pytest tests/ -q 2>&1 | tail -3"
fi

# El servicio se toca al final y sólo si todo lo anterior salió bien: con
# `set -e`, un fallo de los tests corta aquí y el bot sigue con la versión buena.
echo "==> Reiniciando el servicio"
TTY_FLAG=""
[ -t 0 ] && TTY_FLAG="-t"
ssh $TTY_FLAG "$PI" "sudo cp '$DEST/tamagotchi.service' /etc/systemd/system/tamagotchi.service && \
    sudo systemctl daemon-reload && \
    sudo systemctl restart tamagotchi && \
    sleep 3 && systemctl is-active tamagotchi"

echo
echo "Listo. Registro en vivo:  ssh $PI 'journalctl -u tamagotchi -f'"
