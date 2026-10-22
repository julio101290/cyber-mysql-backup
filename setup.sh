#!/bin/bash
set -e

# =========================================================
# DETECCIÓN AUTOMÁTICA DE RUTA Y USUARIO DEL SERVIDOR
# =========================================================
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
RUN_USER="${SUDO_USER:-$(whoami)}"
RUN_GROUP="$(id -gn "$RUN_USER")"
PORT="5009"
DEFAULT_MOUNT="/mnt/red_s"

echo "========================================================="
echo " Reinstalando CyberBackup (Multi-Servidor)..."
echo " Ruta detectada : $APP_DIR"
echo " Usuario/Grupo  : $RUN_USER:$RUN_GROUP"
echo "========================================================="

# 1. Instalar paquetes necesarios del sistema
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip cifs-utils smbclient zip default-mysql-client cron

# Asegurar que el demonio cron esté activo
sudo systemctl enable cron
sudo systemctl start cron

# 2. Crear carpetas de trabajo y punto de montaje por defecto
mkdir -p "$APP_DIR/templates"
mkdir -p "$APP_DIR/backups"
mkdir -p "$APP_DIR/test_source"
echo "Archivo de prueba generado por CyberBackup en $(hostname)" > "$APP_DIR/test_source/leeme.txt"

sudo mkdir -p "$DEFAULT_MOUNT"
sudo chown -R "$RUN_USER:$RUN_GROUP" "$DEFAULT_MOUNT"

# 3. Configurar sudoers dinámicamente para permitir montar unidades de red desde el Dashboard
SUDOERS_FILE="/etc/sudoers.d/cyberbackup"
sudo bash -c "cat > $SUDOERS_FILE" <<EOF
$RUN_USER ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount, /usr/sbin/mount.cifs, /bin/mkdir, /bin/chown, /bin/chmod
EOF
sudo chmod 0440 "$SUDOERS_FILE"

# 4. Configurar entorno virtual e instalar paquetes de Python
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install Flask Werkzeug bcrypt blinker cffi click cryptography invoke itsdangerous jinja2 markupsafe paramiko pycparser pynacl
deactivate

sudo chown -R "$RUN_USER:$RUN_GROUP" "$APP_DIR"

# 5. Crear y configurar el servicio Systemd para inicio automático
SERVICE_FILE="/etc/systemd/system/cyberbackup.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Servicio Web CyberBackup
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$VENV_DIR/bin/python $APP_DIR/app.py
Restart=always
RestartSec=3
StandardOutput=append:$APP_DIR/service.log
StandardError=append:$APP_DIR/service_error.log

[Install]
WantedBy=multi-user.target
EOF

# 6. Recargar demonios, habilitar en el arranque e iniciar de inmediato
sudo systemctl daemon-reload
sudo systemctl enable cyberbackup.service
sudo systemctl restart cyberbackup.service

sleep 2
IP_SERVIDOR=$(hostname -I | awk '{print $1}')

echo "========================================================="
echo " Reinstalación completada en $(hostname)."
echo " Estado del servicio : $(sudo systemctl is-active cyberbackup.service)"
echo " Servicio activo en  : http://${IP_SERVIDOR}:${PORT}"
echo " Usuario por defecto : admin"
echo " Password por defecto: admin123"
echo "========================================================="