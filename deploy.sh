#!/bin/bash
# Despliega el bot en una Raspberry por SSH.
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
    --exclude '.pytest_cache' \
    "$ORIGEN/" "$PI:$DEST/"

echo "==> Preparando el entorno en la Pi"
ssh "$PI" "cd '$DEST' && \
    { [ -d venv ] || python3 -m venv venv; } && \
    ./venv/bin/pip install -q --upgrade pip && \
    ./venv/bin/pip install -q -r requirements.txt && \
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

echo "==> Instalando/actualizando el servicio"
ssh $TTY_FLAG "$PI" "sudo cp '$DEST/tamagotchi.service' /etc/systemd/system/tamagotchi.service && \
    sudo systemctl daemon-reload && \
    sudo systemctl enable tamagotchi && \
    sudo systemctl restart tamagotchi && \
    sleep 3 && sudo systemctl status tamagotchi --no-pager -l | head -20"

echo
echo "Deploy OK. Registro en vivo:  ssh $PI 'journalctl -u tamagotchi -f'"
