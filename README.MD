# 🛡️ Multilingual CyberBackup

**CyberBackup** is a lightweight and robust web system developed in **Python (Flask)** and automated via **Bash (`setup.sh`)**, designed to run as an unattended service on **Linux (Ubuntu/Debian)** servers. It enables local compressed `.zip` backups (including file folders and MySQL/MariaDB database dumps) and securely transfers them to network shared resources (**SMB / CIFS / TrueNAS / Windows**) or via **SFTP**, featuring full multilingual support and automatic scheduling (**Cron**).

---

## 🌟 Key Features

- **Multi-Server & Dynamic:** Automatically detects the operating system user, group, and execution path where it is deployed.
- **Multilingual Support:** Fully translated interface instantly selectable for **Spanish, English, Italian, Esperanto, Russian, Japanese, and Chinese**.
- **Smart SMB Mounting (TrueNAS / Windows):** Automatically separates the root share from destination subfolders, applying compatibility profiles and secure credentials.
- **Comprehensive Backups:** Compresses local files and generates a database dump (`mysqldump`) into a single `.zip` archive.
- **Cron Automation:** Allows setting the exact daily execution time directly from the web Dashboard.
- **Secure Control Panel:** Authentication protected with hashing (`bcrypt`) and full real-time configuration management.
- **Interactive Testing Center:** Dedicated buttons to verify network mounting, run upload tests, and execute manual backups with instant notifications.

---

## 🚀 System Requirements

- **OS:** Linux (Ubuntu / Debian / Linux Mint, or other `systemd`-compatible distributions).
- **Dependencies (installed automatically by the script):** `python3-venv`, `python3-pip`, `cifs-utils`, `smbclient`, `zip`, `default-mysql-client`, and `cron`.

---

## 📦 Quick Installation (Automatic Script)

1. Clone or copy the project files to your directory of choice (e.g., `/opt/cyber-backup` or your home folder).
2. Ensure you have the clean structure created:
   ```bash
   mkdir -p templates backups test_source