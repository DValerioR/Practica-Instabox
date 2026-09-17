#!/bin/bash
# Script de bootstrap para la instancia EC2 (Ubuntu 22.04/24.04).
# Ejecutar con sudo, ya con el instance profile LabInstanceProfile asignado
# a la instancia y el código del proyecto ya clonado/copiado en ella.
#
# Uso:
#   sudo bash deploy/ec2-setup.sh
#
# Antes de correrlo, edita /opt/instabox/.env.runtime con los valores
# reales de AWS_REGION, DB_SECRET_NAME y S3_BUCKET (ver .env.example).

set -euo pipefail

APP_DIR="/opt/instabox"

if [ "$(id -u)" -ne 0 ]; then
  echo "Ejecuta este script con sudo." >&2
  exit 1
fi

apt-get update -y
apt-get install -y python3-pip python3-venv postgresql-client

if [ ! -d "$APP_DIR" ]; then
  echo "No se encontró $APP_DIR. Copia/clona ahí el código del proyecto antes de continuar." >&2
  exit 1
fi

cd "$APP_DIR"

if [ ! -f ".env.runtime" ]; then
  cp .env.example .env.runtime
  echo "Se creó $APP_DIR/.env.runtime a partir de .env.example."
  echo "Edítalo con los valores reales antes de iniciar el servicio."
fi

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

cp deploy/instabox.service /etc/systemd/system/instabox.service
systemctl daemon-reload
systemctl enable instabox
systemctl restart instabox

echo ""
echo "Listo. Verifica el estado con: systemctl status instabox"
echo "Logs en vivo con:              journalctl -u instabox -f"