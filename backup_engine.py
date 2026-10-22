#!/usr/bin/env python3
import os
import sys
import json
import gzip
import shutil
import subprocess
import paramiko
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("config.json no existe. Configure desde la web primero.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def run_backup(backup_type="daily"):
    config = load_config()
    db = config.get("database", {})
    remote = config.get("remote", {})
    local_dir = config.get("local_backup_dir", os.path.join(BASE_DIR, "backups"))

    os.makedirs(local_dir, exist_ok=True)

    # Nombre de archivo fijo para reemplazo según frecuencia
    # backup_daily.sql.gz, backup_weekly.sql.gz, etc.
    filename = f"backup_{backup_type}.sql.gz"
    local_file_path = os.path.join(local_dir, filename)

    print(f"[{datetime.now()}] Iniciando respaldo tipo: {backup_type}...")

    # Comando mysqldump
    host = db.get("host", "127.0.0.1")
    port = str(db.get("port", 3306))
    user = db.get("user", "root")
    password = db.get("password", "")
    database = db.get("dbname", "")

    dump_cmd = [
        "mysqldump",
        f"-h{host}",
        f"-P{port}",
        f"-u{user}",
        f"-p{password}",
        "--single-transaction",
        "--quick"
    ]

    if database:
        dump_cmd.append(database)
    else:
        dump_cmd.append("--all-databases")

    # Ejecutar dump y comprimir al vuelo
    try:
        proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(local_file_path, "wb") as f_out:
            shutil.copyfileobj(proc.stdout, f_out)
        
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"mysqldump falló: {stderr.decode('utf-8')}")
        
        print(f"Respaldo generado exitosamente: {local_file_path}")
    except Exception as e:
        print(f"Error durante el respaldo: {e}", file=sys.stderr)
        return False

    # Transferencia remota vía SFTP si está habilitada
    if remote.get("enabled", False):
        try:
            print(f"Enviando respaldo a {remote.get('host')}...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=remote.get("host"),
                port=int(remote.get("port", 22)),
                username=remote.get("user"),
                password=remote.get("password"),
                timeout=20
            )

            sftp = ssh.open_sftp()
            remote_dir = remote.get("path", "/tmp").rstrip("/")
            remote_file_path = f"{remote_dir}/{filename}"

            sftp.put(local_file_path, remote_file_path)
            sftp.close()
            ssh.close()
            print(f"Archivo enviado exitosamente a {remote_file_path}")
        except Exception as e:
            print(f"Error en transferencia remota: {e}", file=sys.stderr)
            return False

    return True

if __name__ == "__main__":
    b_type = sys.argv[1] if len(sys.argv) > 1 else "daily"
    run_backup(b_type)
