#!/bin/bash
# Despliega ESTA carpeta en una Raspberry por SSH.
#
# ¿Cuál de los dos scripts? Para lo normal, `actualizar-pi.sh`: baja de GitHub y
# la Pi queda en lo que hay en `main`. Éste sube tu copia local tal cual, y sirve
# para probar en la Pi algo que todavía no has commiteado.
#
#   ./deploy.sh
#   PI=usuario@192.168.1.50 DEST=/opt/tamagotchi ./deploy.sh
#
# Los valores de abajo son los de la máquina de casa; para apuntar a otra basta
# con las variables de entorno, sin tocar el script.
#
# El .env NO viaja: se copia a mano una sola vez (ver README).
set -euo pipefail

PI="${PI:-felipe@192.168.1.109}"
DEST="${DEST:-/home/felipe/tamagotchi-bot}"
ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Copiando a $PI:$DEST"
rsync -av --delete \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.db-journal' \
    --exclude '*.db-wal' \
    --exclude '*.db-shm' \
    --exclude '*.bak' \
    --exclude '.pytest_cache' \
    "$ORIGEN/" "$PI:$DEST/"

echo "==> Preparando el entorno en la Pi"
ssh "$PI" "cd '$DEST' && \
    { [ -d venv ] || python3 -m venv venv; } && \
    ./venv/bin/python -m pip install -q -r requirements.txt && \
    ./venv/bin/python -c 'import discord; print(\"discord.py\", discord.__version__)'"

if ! ssh "$PI" "test -f '$DEST/.env'"; then
    echo
    echo "!! Falta $DEST/.env en la Pi. Cópialo con:"
    echo "   scp .env $PI:$DEST/.env"
    echo "   (sin él el bot no arranca)"
    exit 1
fi

# -t sólo si hay terminal: sin él sudo no puede pedir contraseña, y con él
# desde un script sin tty ssh se queja. En esta Pi sudo es sin contraseña.
TTY_FLAG=""
[ -t 0 ] && TTY_FLAG="-t"

# Una copia de las mascotas antes de reiniciar: el arranque puede devolver gemas
# y borrar piezas, y eso se respalda siempre. Mismo nombre y misma rotación (las
# 5 últimas) que `actualizar-pi.sh`, para que las dos sean una sola.
echo "==> Copiando la base de datos"
ssh "$PI" "cd '$DEST' && \
    if [ -f tamagotchi.db ]; then \
        copia=\"tamagotchi.db.\$(date +%Y%m%d-%H%M%S).bak\" && \
        cp tamagotchi.db \"\$copia\" && \
        echo \"    copia de seguridad: \$copia\" && \
        { ls -1t tamagotchi.db.*.bak 2>/dev/null | tail -n +6 | xargs -r rm -- || true; }; \
    fi"

echo "==> Instalando/actualizando los servicios (primero el bot, después la web)"
ssh $TTY_FLAG "$PI" "sudo cp '$DEST/tamagotchi.service' /etc/systemd/system/tamagotchi.service && \
    sudo cp '$DEST/gachamon-web.service' /etc/systemd/system/gachamon-web.service && \
    sudo systemctl daemon-reload && \
    sudo systemctl enable tamagotchi gachamon-web && \
    sudo systemctl restart tamagotchi && \
    sudo systemctl restart gachamon-web && \
    sleep 3 && systemctl is-active tamagotchi && systemctl is-active gachamon-web && \
    curl -fsS --retry 10 --retry-delay 1 --retry-connrefused -o /dev/null http://127.0.0.1:8010/gachamon/api/salud"

echo
echo "Deploy OK. Registro en vivo:  ssh $PI 'journalctl -u tamagotchi -u gachamon-web -f'"
