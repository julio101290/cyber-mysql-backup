import os
import sys
import json
import socket
import shutil
import zipfile
import subprocess
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import bcrypt
import paramiko

app = Flask(__name__)
app.secret_key = "cyberbackup_secret_key_prod_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_BIN = os.path.join(BASE_DIR, "venv", "bin", "python")
if not os.path.exists(PYTHON_BIN):
    PYTHON_BIN = sys.executable

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "backup.log")
CREDS_FILE = os.path.join(BASE_DIR, ".smbcreds")
LOCAL_BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TEST_SOURCE_DIR = os.path.join(BASE_DIR, "test_source")
SERVER_HOSTNAME = socket.gethostname()
CRON_TAG = "# CYBERBACKUP_AUTO_CRON"

os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)
os.makedirs(TEST_SOURCE_DIR, exist_ok=True)

# =========================================================
# DICCIONARIO MULTILENGUAJE (ES, EN, IT, EO, RU, JA, ZH)
# =========================================================
LANGS = {
    "es": {
        "title": "Panel de Control de Respaldos",
        "login_title": "Iniciar Sesión",
        "user": "Usuario",
        "pass": "Contraseña",
        "enter": "Ingresar al Panel",
        "logout": "Salir",
        "test_center": "Centro de Pruebas y Ejecución",
        "mounted": "Unidad Montada",
        "not_mounted": "Unidad No Montada",
        "btn_test_backup": "Probar Respaldo y Envío a Red",
        "btn_test_mount": "Probar Solo Montaje SMB",
        "btn_run_backup": "Ejecutar Respaldo Completo Ahora",
        "net_config": "Datos del Recurso Compartido en Red (SMB / TrueNAS)",
        "ip_server": "IP del Servidor de Red",
        "share_root": "Recurso Compartido Raíz",
        "subpath": "Subcarpeta de Destino (Opcional)",
        "smb_user": "Usuario SMB",
        "smb_pass": "Contraseña SMB",
        "domain": "Dominio / Workgroup",
        "mount_point": "Punto de Montaje Local en Linux",
        "cron_title": "Programación Automática Diaria (Cron)",
        "cron_enable": "Habilitar respaldo diario automático",
        "cron_time": "Hora de Ejecución (24h)",
        "origin_title": "Origen de Archivos y Base de Datos",
        "local_folder": "Carpeta Local a Respaldar",
        "include_db": "Incluir Base de Datos MySQL / MariaDB en el respaldo",
        "db_host": "Host BD",
        "db_name": "Nombre Base de Datos",
        "db_user": "Usuario BD",
        "db_pass": "Password BD",
        "save_config": "Guardar Configuración y Horario Cron",
        "logs_title": "Bitácora de Eventos",
        "local_backups": "Últimos Respaldos Locales",
        "security_title": "Seguridad: Cambiar Contraseña de Admin",
        "current_pass": "Contraseña Actual",
        "new_pass": "Nueva Contraseña",
        "confirm_pass": "Confirmar Nueva",
        "update_creds": "Actualizar Credenciales"
    },
    "en": {
        "title": "Backup Control Panel",
        "login_title": "Sign In",
        "user": "Username",
        "pass": "Password",
        "enter": "Log In",
        "logout": "Logout",
        "test_center": "Testing & Execution Center",
        "mounted": "Drive Mounted",
        "not_mounted": "Drive Not Mounted",
        "btn_test_backup": "Test Backup & Network Send",
        "btn_test_mount": "Test SMB Mount Only",
        "btn_run_backup": "Run Full Backup Now",
        "net_config": "Network Share Details (SMB / TrueNAS)",
        "ip_server": "Network Server IP",
        "share_root": "Root Share Name",
        "subpath": "Destination Subfolder (Optional)",
        "smb_user": "SMB Username",
        "smb_pass": "SMB Password",
        "domain": "Domain / Workgroup",
        "mount_point": "Linux Local Mount Point",
        "cron_title": "Daily Automatic Schedule (Cron)",
        "cron_enable": "Enable automatic daily backup",
        "cron_time": "Execution Time (24h)",
        "origin_title": "Files Origin and Database",
        "local_folder": "Local Folder to Backup",
        "include_db": "Include MySQL / MariaDB Database in backup",
        "db_host": "DB Host",
        "db_name": "Database Name",
        "db_user": "DB User",
        "db_pass": "DB Password",
        "save_config": "Save Configuration & Cron Schedule",
        "logs_title": "Event Log",
        "local_backups": "Latest Local Backups",
        "security_title": "Security: Change Admin Password",
        "current_pass": "Current Password",
        "new_pass": "New Password",
        "confirm_pass": "Confirm New",
        "update_creds": "Update Credentials"
    },
    "it": {
        "title": "Pannello di Controllo Backup",
        "login_title": "Accedi",
        "user": "Utente",
        "pass": "Password",
        "enter": "Entra nel Pannello",
        "logout": "Esci",
        "test_center": "Centro Test ed Esecuzione",
        "mounted": "Unità Montata",
        "not_mounted": "Unità non Montata",
        "btn_test_backup": "Test Backup e Invio in Rete",
        "btn_test_mount": "Test Solo Mount SMB",
        "btn_run_backup": "Esegui Backup Completo Ora",
        "net_config": "Dettagli Condivisione Rete (SMB / TrueNAS)",
        "ip_server": "IP Server di Rete",
        "share_root": "Nome Condivisione Principale",
        "subpath": "Sottocartella di Destinazione (Opzionale)",
        "smb_user": "Utente SMB",
        "smb_pass": "Password SMB",
        "domain": "Dominio / Workgroup",
        "mount_point": "Punto di Mount Locale in Linux",
        "cron_title": "Pianificazione Automatica Giornaliera (Cron)",
        "cron_enable": "Abilita backup giornaliero automatico",
        "cron_time": "Ora di Esecuzione (24h)",
        "origin_title": "Origine File e Database",
        "local_folder": "Cartella Locale da Backup",
        "include_db": "Includi Database MySQL / MariaDB nel backup",
        "db_host": "Host DB",
        "db_name": "Nome Database",
        "db_user": "Utente DB",
        "db_pass": "Password DB",
        "save_config": "Salva Configurazione e Orario Cron",
        "logs_title": "Registro Eventi",
        "local_backups": "Ultimi Backup Locali",
        "security_title": "Sicurezza: Cambia Password Admin",
        "current_pass": "Password Attuale",
        "new_pass": "Nuova Password",
        "confirm_pass": "Conferma Nuova",
        "update_creds": "Aggiorna Credenziali"
    },
    "eo": {
        "title": "Rezerva Kontrolpanelo",
        "login_title": "Ensaluti",
        "user": "Uzantnomo",
        "pass": "Pasvorto",
        "enter": "Eniri Panelon",
        "logout": "Elsaluti",
        "test_center": "Testa kaj Ekzekuta Centro",
        "mounted": "Disko Muntita",
        "not_mounted": "Disko Ne Muntita",
        "btn_test_backup": "Testi Rezervon kaj Retan Sendon",
        "btn_test_mount": "Testi Nur SMB-Muntadon",
        "btn_run_backup": "Ruli Plenan Rezervon Nun",
        "net_config": "Retaj Detaloj (SMB / TrueNAS)",
        "ip_server": "Reta Servila IP",
        "share_root": "Radika Kunhavigo",
        "subpath": "Cela Subdosierujo (Laŭvola)",
        "smb_user": "SMB Uzanto",
        "smb_pass": "SMB Pasvorto",
        "domain": "Domajno / Laborgrupo",
        "mount_point": "Loka Muntpunkto en Linukso",
        "cron_title": "Ĉiutaga Aŭtomata Horaro (Cron)",
        "cron_enable": "Ebligi aŭtomatan ĉiutagan rezervon",
        "cron_time": "Ekzekuta Horo (24h)",
        "origin_title": "Dosierfonto kaj Datumbazo",
        "local_folder": "Loka Dosierujo por Rezervi",
        "include_db": "Inkluzivi MySQL / MariaDB Datumbazon",
        "db_host": "DB Gastiganto",
        "db_name": "Datumbaza Nomo",
        "db_user": "DB Uzanto",
        "db_pass": "DB Pasvorto",
        "save_config": "Konservi Agordon kaj Horaron",
        "logs_title": "Eventa Protokolo",
        "local_backups": "Lokaj Rezervkopioj",
        "security_title": "Sekureco: Ŝanĝi Administrantan Pasvorton",
        "current_pass": "Nuna Pasvorto",
        "new_pass": "Nova Pasvorto",
        "confirm_pass": "Konfirmi Novan",
        "update_creds": "Ĝisdatigi Akreditaĵojn"
    },
    "ru": {
        "title": "Панель управления резервным копированием",
        "login_title": "Вход в систему",
        "user": "Имя пользователя",
        "pass": "Пароль",
        "enter": "Войти",
        "logout": "Выйти",
        "test_center": "Центр тестирования и выполнения",
        "mounted": "Диск смонтирован",
        "not_mounted": "Диск не смонтирован",
        "btn_test_backup": "Тест бэкапа и отправки в сеть",
        "btn_test_mount": "Тест только SMB монтажа",
        "btn_run_backup": "Запустить полный бэкап сейчас",
        "net_config": "Параметры сетевого ресурса (SMB / TrueNAS)",
        "ip_server": "IP сетевого сервера",
        "share_root": "Корневой общий ресурс",
        "subpath": "Целевая подпапка (необязательно)",
        "smb_user": "SMB Пользователь",
        "smb_pass": "SMB Пароль",
        "domain": "Домен / Рабочая группа",
        "mount_point": "Точка монтирования в Linux",
        "cron_title": "Автоматическое расписание (Cron)",
        "cron_enable": "Включить автоматический ежедневный бэкап",
        "cron_time": "Время выполнения (24ч)",
        "origin_title": "Источник файлов и база данных",
        "local_folder": "Локальная папка для бэкапа",
        "include_db": "Включить базу данных MySQL / MariaDB",
        "db_host": "Хост БД",
        "db_name": "Имя БД",
        "db_user": "Пользователь БД",
        "db_pass": "Пароль БД",
        "save_config": "Сохранить конфигурацию и Cron",
        "logs_title": "Журнал событий",
        "local_backups": "Последние локальные бэкапы",
        "security_title": "Безопасность: Изменить пароль администратора",
        "current_pass": "Текущий пароль",
        "new_pass": "Новый пароль",
        "confirm_pass": "Подтвердите новый",
        "update_creds": "Обновить учетные данные"
    },
    "ja": {
        "title": "バックアップ管理パネル",
        "login_title": "ログイン",
        "user": "ユーザー名",
        "pass": "パスワード",
        "enter": "ログイン",
        "logout": "ログアウト",
        "test_center": "テストおよび実行センター",
        "mounted": "マウント済み",
        "not_mounted": "未マウント",
        "btn_test_backup": "バックアップ＆ネットワーク送信テスト",
        "btn_test_mount": "SMBマウントテストのみ",
        "btn_run_backup": "今すぐ完全バックアップを実行",
        "net_config": "ネットワーク共有の詳細 (SMB / TrueNAS)",
        "ip_server": "サーバーIP",
        "share_root": "ルート共有名",
        "subpath": "宛先サブフォルダ (オプション)",
        "smb_user": "SMB ユーザー",
        "smb_pass": "SMB パスワード",
        "domain": "ドメイン / ワークグループ",
        "mount_point": "Linuxローカルマウントポイント",
        "cron_title": "自動日次スケジュール (Cron)",
        "cron_enable": "自動日次バックアップを有効にする",
        "cron_time": "実行時刻 (24時間)",
        "origin_title": "ファイル元とデータベース",
        "local_folder": "バックアップ対象のローカルフォルダ",
        "include_db": "MySQL / MariaDBデータベースを含める",
        "db_host": "DBホスト",
        "db_name": "DB名",
        "db_user": "DBユーザー",
        "db_pass": "DBパスワード",
        "save_config": "設定とCronスケジュールを保存",
        "logs_title": "イベントログ",
        "local_backups": "最新のローカルバックアップ",
        "security_title": "セキュリティ: 管理者パスワードの変更",
        "current_pass": "現在のパスワード",
        "new_pass": "新しいパスワード",
        "confirm_pass": "新しいパスワード (確認)",
        "update_creds": "認証情報を更新"
    },
    "zh": {
        "title": "备份控制面板",
        "login_title": "登录系统",
        "user": "用户名",
        "pass": "密码",
        "enter": "登录",
        "logout": "登出",
        "test_center": "测试与执行中心",
        "mounted": "已挂载",
        "not_mounted": "未挂载",
        "btn_test_backup": "测试备份并发送至网络",
        "btn_test_mount": "仅测试 SMB 挂载",
        "btn_run_backup": "立即运行完整备份",
        "net_config": "网络共享详情 (SMB / TrueNAS)",
        "ip_server": "网络服务器 IP",
        "share_root": "根共享名称",
        "subpath": "目标子文件夹 (可选)",
        "smb_user": "SMB 用户名",
        "smb_pass": "SMB 密码",
        "domain": "域 / 工作组",
        "mount_point": "Linux 本地挂载点",
        "cron_title": "每日自动计划 (Cron)",
        "cron_enable": "启用每日自动备份",
        "cron_time": "执行时间 (24小时)",
        "origin_title": "文件来源与数据库",
        "local_folder": "本地备份文件夹",
        "include_db": "在备份中包含 MySQL / MariaDB 数据库",
        "db_host": "数据库主机",
        "db_name": "数据库名称",
        "db_user": "数据库用户",
        "db_pass": "数据库密码",
        "save_config": "保存配置与 Cron 计划",
        "logs_title": "事件日志",
        "local_backups": "最新本地备份",
        "security_title": "安全：修改管理员密码",
        "current_pass": "当前密码",
        "new_pass": "新密码",
        "confirm_pass": "确认新密码",
        "update_creds": "更新凭据"
    }
}


def write_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{SERVER_HOSTNAME}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def load_config():
    default_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
    default_cfg = {
        "username": "admin",
        "password_hash": default_hash,
        "windows_ip": "192.168.0.101",
        "windows_share": "Compartido",
        "windows_subpath": "Respaldos",
        "windows_domain": "WORKGROUP",
        "windows_user": "admin",
        "windows_pass": "",
        "mount_point": "/mnt/red_s",
        "cron_enabled": False,
        "cron_time": "02:00",
        "source_folder": TEST_SOURCE_DIR,
        "db_enabled": False,
        "db_host": "localhost",
        "db_user": "root",
        "db_pass": "",
        "db_name": "",
        "use_sftp": False,
        "sftp_host": "192.168.0.101",
        "sftp_port": 22,
        "sftp_user": "root",
        "sftp_pass": "",
        "sftp_remote_dir": "/mnt/Pool/Respaldos"
    }

    if not os.path.exists(CONFIG_FILE):
        save_config(default_cfg)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            default_cfg.update(saved)
            return default_cfg
    except Exception:
        return default_cfg


def normalizar_share_y_subcarpeta(cfg):
    raw_share = cfg.get("windows_share", "").strip().replace("\\", "/").strip("/")
    raw_sub = cfg.get("windows_subpath", "").strip().replace("\\", "/").strip("/")

    if "/" in raw_share:
        partes = raw_share.split("/", 1)
        share_raiz = partes[0]
        sub_extra = partes[1]
        subpath = f"{sub_extra}/{raw_sub}".strip("/") if raw_sub else sub_extra
    else:
        share_raiz = raw_share
        subpath = raw_sub

    return share_raiz, subpath


def save_config(cfg):
    share_raiz, subpath = normalizar_share_y_subcarpeta(cfg)
    cfg["windows_share"] = share_raiz
    cfg["windows_subpath"] = subpath

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def sincronizar_crontab(cfg):
    res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lineas_actuales = res.stdout.splitlines() if res.returncode == 0 else []
    lineas_limpias = [linea for linea in lineas_actuales if CRON_TAG not in linea and linea.strip() != ""]

    if cfg.get("cron_enabled"):
        hora_str = cfg.get("cron_time", "02:00").strip()
        try:
            partes = hora_str.split(":")
            hora = int(partes[0])
            minuto = int(partes[1])
        except Exception:
            hora, minuto = 2, 0

        script_path = os.path.abspath(__file__)
        nueva_linea = f"{minuto} {hora} * * * {PYTHON_BIN} {script_path} --cron-backup {CRON_TAG}"
        lineas_limpias.append(nueva_linea)

    nuevo_contenido = "\n".join(lineas_limpias) + ("\n" if lineas_limpias else "")
    proc = subprocess.run(["crontab", "-"], input=nuevo_contenido, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"No se pudo actualizar crontab: {proc.stderr}")


def obtener_estado_cron():
    res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        return None
    for linea in res.stdout.splitlines():
        if CRON_TAG in linea:
            return linea.replace(CRON_TAG, "").strip()
    return None


def get_lang():
    lang = session.get("lang", "en")
    if lang not in LANGS:
        lang = "es"
    return LANGS[lang]


@app.context_processor
def inject_lang():
    return dict(t=get_lang(), current_lang=session.get("lang", "es"))


@app.route("/set_lang/<lang_code>")
def set_lang(lang_code):
    if lang_code in LANGS:
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("index"))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Sesión no iniciada."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def preparar_archivo_credenciales(user, password, domain=""):
    if "\\" in user:
        domain, user = user.split("\\", 1)

    lineas = [
        f"username={user}",
        f"password={password}"
    ]
    if domain:
        lineas.append(f"domain={domain}")

    with open(CREDS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    os.chmod(CREDS_FILE, 0o600)


def montar_carpeta_windows(cfg, forzar_remontaje=False):
    ip = cfg.get("windows_ip", "").strip()
    share_raiz, subpath = normalizar_share_y_subcarpeta(cfg)
    user = cfg.get("windows_user", "").strip()
    password = cfg.get("windows_pass", "")
    domain = cfg.get("windows_domain", "").strip()
    mount_point = cfg.get("mount_point", "/mnt/red_s").strip()

    if not ip or not share_raiz or not mount_point:
        raise ValueError("Faltan datos de configuración de red.")

    subprocess.run(["sudo", "-n", "mkdir", "-p", mount_point], check=False)
    uid = os.getuid()
    gid = os.getgid()
    subprocess.run(["sudo", "-n", "chown", f"{uid}:{gid}", mount_point], check=False)

    ya_montado = os.path.ismount(mount_point)
    if ya_montado and forzar_remontaje:
        subprocess.run(["sudo", "-n", "umount", "-l", mount_point], check=False)
        ya_montado = False

    if not ya_montado:
        preparar_archivo_credenciales(user, password, domain)
        unc_raiz = f"//{ip}/{share_raiz}"
        base_opts = f"credentials={CREDS_FILE},uid={uid},gid={gid},iocharset=utf8,file_mode=0777,dir_mode=0777,noperm"

        perfiles_montaje = [
            f"{base_opts},vers=3.0,sec=ntlmssp",
            f"{base_opts},vers=2.1,sec=ntlmssp",
            f"{base_opts},vers=3.0,sec=ntlmv2",
            f"{base_opts},vers=2.0,sec=ntlmssp",
            f"{base_opts},sec=ntlmssp",
            f"{base_opts}"
        ]

        errores_intentos = []
        montado_exito = False

        for opts in perfiles_montaje:
            cmd = ["sudo", "-n", "mount", "-t", "cifs", unc_raiz, mount_point, "-o", opts]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                montado_exito = True
                break
            else:
                errores_intentos.append(res.stderr.strip())

        if not montado_exito and domain:
            preparar_archivo_credenciales(user, password, domain="")
            for opts in perfiles_montaje[:3]:
                cmd = ["sudo", "-n", "mount", "-t", "cifs", unc_raiz, mount_point, "-o", opts]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    montado_exito = True
                    break

        if not montado_exito:
            ultimo_error = errores_intentos[0] if errores_intentos else "Error desconocido"
            raise RuntimeError(f"No se pudo montar {unc_raiz} en {mount_point}. Detalle: {ultimo_error}")

    ruta_destino_final = os.path.join(mount_point, subpath) if subpath else mount_point
    if not os.path.exists(ruta_destino_final):
        os.makedirs(ruta_destino_final, exist_ok=True)

    return ruta_destino_final


def generar_zip_respaldo(origen_dir, ruta_zip_destino, incluir_db=False, cfg=None):
    sql_file = None
    try:
        if incluir_db and cfg and cfg.get("db_enabled") and cfg.get("db_name"):
            sql_file = os.path.join(LOCAL_BACKUP_DIR, f"db_{cfg['db_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
            cmd = [
                "mysqldump",
                f"-h{cfg.get('db_host', 'localhost')}",
                f"-u{cfg.get('db_user', 'root')}"
            ]
            if cfg.get("db_pass"):
                cmd.append(f"-p{cfg['db_pass']}")
            cmd.append(cfg["db_name"])

            with open(sql_file, "w", encoding="utf-8") as out:
                res = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Error en mysqldump: {res.stderr}")

        with zipfile.ZipFile(ruta_zip_destino, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(origen_dir):
                for root, dirs, files in os.walk(origen_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        arcname = os.path.relpath(filepath, os.path.dirname(origen_dir))
                        zipf.write(filepath, arcname)

            if sql_file and os.path.exists(sql_file):
                zipf.write(sql_file, os.path.basename(sql_file))
    finally:
        if sql_file and os.path.exists(sql_file):
            try:
                os.remove(sql_file)
            except Exception:
                pass


def enviar_archivo_a_red(archivo_local, cfg):
    nombre_archivo = os.path.basename(archivo_local)

    if cfg.get("use_sftp"):
        transport = paramiko.Transport((cfg["sftp_host"], int(cfg.get("sftp_port", 22))))
        transport.connect(username=cfg["sftp_user"], password=cfg["sftp_pass"])
        sftp = paramiko.SFTPClient.from_transport(transport)
        ruta_remota_dir = cfg["sftp_remote_dir"].replace("\\", "/").rstrip("/")
        ruta_remota = f"{ruta_remota_dir}/{nombre_archivo}"
        sftp.put(archivo_local, ruta_remota)
        sftp.close()
        transport.close()
        return f"SFTP://{cfg['sftp_host']}{ruta_remota}"

    carpeta_destino = montar_carpeta_windows(cfg, forzar_remontaje=False)
    if not os.path.exists(carpeta_destino):
        raise FileNotFoundError(f"La ruta destino '{carpeta_destino}' no existe.")

    destino_final = os.path.join(carpeta_destino, nombre_archivo)
    shutil.copy2(archivo_local, destino_final)

    if not os.path.exists(destino_final):
        raise IOError("El archivo se copió pero no se encontró al verificar la red.")

    share_raiz, subpath = normalizar_share_y_subcarpeta(cfg)
    ruta_unc = f"\\\\{cfg['windows_ip']}\\{share_raiz}" + (f"\\{subpath.replace('/', chr(92))}" if subpath else "")
    return f"{destino_final} ({ruta_unc}\\{nombre_archivo})"


def ejecutar_respaldo_completo(origen="MANUAL"):
    cfg = load_config()
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_zip = f"backup_{SERVER_HOSTNAME}_{fecha_str}.zip"
    ruta_zip_local = os.path.join(LOCAL_BACKUP_DIR, nombre_zip)

    generar_zip_respaldo(cfg["source_folder"], ruta_zip_local, incluir_db=cfg.get("db_enabled", False), cfg=cfg)
    tamano_kb = round(os.path.getsize(ruta_zip_local) / 1024, 2)
    ruta_remota = enviar_archivo_a_red(ruta_zip_local, cfg)

    msg = f"Respaldo [{origen}] '{nombre_zip}' ({tamano_kb} KB) -> {ruta_remota}"
    write_log(f"[RESPALDO OK] {msg}")
    return msg


@app.route("/login", methods=["GET", "POST"])
def login():
    cfg = load_config()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").encode("utf-8")

        if username == cfg["username"] and bcrypt.checkpw(password, cfg["password_hash"].encode("utf-8")):
            session["logged_in"] = True
            session["username"] = username
            write_log(f"Sesión iniciada por '{username}'.")
            return redirect(url_for("index"))
        else:
            write_log(f"Intento fallido para '{username}'.")
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html", hostname=SERVER_HOSTNAME)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@login_required
def index():
    cfg = load_config()
    esta_montado = os.path.ismount(cfg.get("mount_point", "/mnt/red_s"))
    cron_linea = obtener_estado_cron()

    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.readlines()[-40:]
            logs.reverse()

    backups = sorted(os.listdir(LOCAL_BACKUP_DIR), reverse=True)
    return render_template(
        "index.html",
        config=cfg,
        logs=logs,
        backups=backups,
        esta_montado=esta_montado,
        cron_linea=cron_linea,
        hostname=SERVER_HOSTNAME
    )


@app.route("/save_config", methods=["POST"])
@login_required
def save_config_route():
    cfg = load_config()
    cfg["windows_ip"] = request.form.get("windows_ip", "192.168.0.101").strip()
    cfg["windows_share"] = request.form.get("windows_share", "Compartido").strip()
    cfg["windows_subpath"] = request.form.get("windows_subpath", "").strip()
    cfg["windows_domain"] = request.form.get("windows_domain", "WORKGROUP").strip()
    cfg["windows_user"] = request.form.get("windows_user", "admin").strip()
    if request.form.get("windows_pass"):
        cfg["windows_pass"] = request.form.get("windows_pass")
    cfg["mount_point"] = request.form.get("mount_point", "/mnt/red_s").strip()

    cfg["cron_enabled"] = True if request.form.get("cron_enabled") == "on" else False
    cfg["cron_time"] = request.form.get("cron_time", "02:00").strip()

    cfg["source_folder"] = request.form.get("source_folder", TEST_SOURCE_DIR).strip()
    cfg["db_enabled"] = True if request.form.get("db_enabled") == "on" else False
    cfg["db_host"] = request.form.get("db_host", "localhost").strip()
    cfg["db_user"] = request.form.get("db_user", "root").strip()
    if request.form.get("db_pass"):
        cfg["db_pass"] = request.form.get("db_pass")
    cfg["db_name"] = request.form.get("db_name", "").strip()

    save_config(cfg)
    try:
        sincronizar_crontab(cfg)
        flash("Configuración guardada correctamente.", "success")
    except Exception as e:
        flash(f"Configuración guardada, error en Cron: {str(e)}", "warning")

    return redirect(url_for("index"))


@app.route("/change_password", methods=["POST"])
@login_required
def change_password_route():
    cfg = load_config()
    current_pass = request.form.get("current_password", "").encode("utf-8")
    new_user = request.form.get("new_username", cfg["username"]).strip()
    new_pass = request.form.get("new_password", "")
    confirm_pass = request.form.get("confirm_password", "")

    if not bcrypt.checkpw(current_pass, cfg["password_hash"].encode("utf-8")):
        flash("Contraseña actual incorrecta.", "danger")
        return redirect(url_for("index"))

    if len(new_pass) < 4:
        flash("La nueva contraseña debe tener al menos 4 caracteres.", "warning")
        return redirect(url_for("index"))

    if new_pass != confirm_pass:
        flash("Las contraseñas no coinciden.", "danger")
        return redirect(url_for("index"))

    cfg["username"] = new_user or "admin"
    cfg["password_hash"] = bcrypt.hashpw(new_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    save_config(cfg)
    session["username"] = cfg["username"]
    flash("Credenciales actualizadas correctamente.", "success")
    return redirect(url_for("index"))


def actualizar_cfg_desde_json(cfg, data):
    if not data:
        return cfg
    cfg["windows_ip"] = data.get("windows_ip", cfg["windows_ip"]).strip()
    cfg["windows_share"] = data.get("windows_share", cfg["windows_share"]).strip()
    cfg["windows_subpath"] = data.get("windows_subpath", cfg.get("windows_subpath", "")).strip()
    cfg["windows_domain"] = data.get("windows_domain", cfg.get("windows_domain", "WORKGROUP")).strip()
    cfg["windows_user"] = data.get("windows_user", cfg["windows_user"]).strip()
    if data.get("windows_pass"):
        cfg["windows_pass"] = data.get("windows_pass")
    cfg["mount_point"] = data.get("mount_point", cfg["mount_point"]).strip()
    save_config(cfg)
    return cfg


@app.route("/api/test_mount", methods=["POST"])
@login_required
def api_test_mount():
    cfg = load_config()
    data = request.get_json(silent=True) or {}
    cfg = actualizar_cfg_desde_json(cfg, data)
    try:
        ruta_final = montar_carpeta_windows(cfg, forzar_remontaje=True)
        return jsonify({"status": "success", "message": f"Montaje exitoso. Destino: {ruta_final}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/test_backup", methods=["POST"])
@login_required
def api_test_backup():
    cfg = load_config()
    data = request.get_json(silent=True) or {}
    cfg = actualizar_cfg_desde_json(cfg, data)

    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_zip = f"prueba_{SERVER_HOSTNAME}_{fecha_str}.zip"
    ruta_zip_local = os.path.join(LOCAL_BACKUP_DIR, nombre_zip)

    try:
        archivo_prueba = os.path.join(TEST_SOURCE_DIR, "verificacion_red.txt")
        with open(archivo_prueba, "w", encoding="utf-8") as f:
            f.write(f"Servidor: {SERVER_HOSTNAME}\nFecha: {fecha_str}\n")

        generar_zip_respaldo(TEST_SOURCE_DIR, ruta_zip_local, incluir_db=cfg.get("db_enabled", False), cfg=cfg)
        tamano_kb = round(os.path.getsize(ruta_zip_local) / 1024, 2)
        ruta_remota_confirmada = enviar_archivo_a_red(ruta_zip_local, cfg)

        return jsonify({"status": "success", "message": f"¡Éxito! Archivo '{nombre_zip}' ({tamano_kb} KB) enviado a: {ruta_remota_confirmada}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/run_backup", methods=["POST"])
@login_required
def api_run_backup():
    cfg = load_config()
    data = request.get_json(silent=True) or {}
    actualizar_cfg_desde_json(cfg, data)
    try:
        msg = ejecutar_respaldo_completo(origen="MANUAL")
        return jsonify({"status": "success", "message": msg}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cron-backup":
        try:
            ejecutar_respaldo_completo(origen="CRON")
        except Exception as exc:
            write_log(f"[CRON ERROR] {str(exc)}")
        sys.exit(0)

    app.run(host="0.0.0.0", port=5009, debug=False)