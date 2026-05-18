import os
import sys
import json
import mysql.connector
from cryptography.fernet import Fernet

def print_usage():
    """Menampilkan panduan penggunaan jika argumen baris perintah tidak lengkap."""
    print("\n[!] Penggunaan Argumen Salah.")
    print("Format: python3 decrypt_simulasi.py [user] [password] [nama_database] [nama_tabel] [file_kunci]")
    print("Contoh: python3 decrypt_simulasi.py root '' bassist users secret.key\n")

def run_decryption(db_config, table_name, key_file_path, schema_file_path):
    """Fungsi utama untuk memulihkan data dan struktur tabel ke kondisi semula."""
    
    # Validasi awal ketersediaan file kunci dan file skema JSON sebelum memproses database
    if not os.path.exists(key_file_path):
        print(f"[ERROR] File kunci enkripsi tidak ditemukan di: {key_file_path}")
        return

    if not os.path.exists(schema_file_path):
        print(f"[ERROR] File skema struktur (.json) tidak ditemukan di: {schema_file_path}")
        print("[-] Proses pemulihan dibatalkan karena tidak ada acuan tipe data asli.")
        return

    try:
        # Memuat kunci Fernet untuk inisialisasi modul dekripsi
        raw_key = open(key_file_path, "rb").read()
        cipher_suite = Fernet(raw_key)
        
        # Memuat peta struktur kolom asli dari file JSON
        with open(schema_file_path, "r") as f:
            original_schema = json.load(f)

        # Membuka koneksi ke database target
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Mengambil seluruh baris data yang saat ini terenkripsi di dalam database
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        print(f"\n[*] Tahap 1: Memproses Dekripsi Data (Menampilkan maksimal 10 baris pertama)...")
        print("-" * 80)

        updated_count = 0
        for i, row in enumerate(rows):
            updates = {}
            show_log = i < 10  # Pembatasan visual output di terminal

            if show_log:
                print(f"RECORD #{i+1} [ID: {row.get('ID', row.get('ID'))}]")

            # Melakukan perulangan hanya pada kolom yang tercatat di dalam skema asli
            for col in original_schema.keys():
                val = row.get(col)
                
                # Memastikan data ada dan memiliki ciri string terenkripsi Fernet ('gAAAA')
                if val and str(val).startswith("gAAAA"):
                    try:
                        # Proses dekripsi balik dari Base64 ke string teks asli
                        dec_val = cipher_suite.decrypt(val.encode()).decode()
                        updates[col] = dec_val
                        if show_log:
                            print(f"  > {col}: {str(val)[:30]}... -> {dec_val}")
                    except Exception as decrypt_err:
                        # Jika baris data gagal didekripsi (misal kunci salah atau data rusak), dilewati
                        if show_log:
                            print(f"  > {col}: [GAGAL DEKRIPSI] {decrypt_err}")
            
            # Jika ada data kolom yang berhasil didekripsi, lakukan pembaruan ke database
            if updates:
                set_query = ", ".join([f"{k}=%s" for k in updates.keys()])
                primary_id = row.get("ID", row.get("ID"))
                query = f"UPDATE {table_name} SET {set_query} WHERE id=%s"
                cursor.execute(query, list(updates.values()) + [primary_id])
                updated_count += 1
                if show_log: 
                    print("  [STATUS] Data terenkripsi berhasil dipulihkan ke teks asli.")

            if show_log: 
                print("-" * 80)

        # Melakukan commit pertama untuk menyimpan pemulihan data teks asli
        conn.commit()
        print(f"[✔] Pemulihan data selesai. Total {updated_count} baris diperbarui.")

        print("\n[*] Tahap 2: Mengembalikan struktur kolom database ke tipe semula...")
        # Mengembalikan tipe data kolom (misal dari TEXT balik menjadi VARCHAR(50), INT, dll)
        for col_name, col_type in original_schema.items():
            print(f"  > Mengubah kembali {col_name} -> {col_type}")
            cursor.execute(f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {col_type}")
        
        # Melakukan commit kedua untuk menerapkan perubahan struktur tabel secara permanen
        conn.commit()
        print("[✔] STRUKTUR TABEL BERHASIL DIPULIHKAN KEMBALI NORMAL.")
        
    except mysql.connector.Error as db_err:
        print(f"[ERROR] Kegagalan operasi database: {db_err}")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan tak terduga: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Memeriksa kecukupan argumen CLI (minimal 6 argumen termasuk nama file skrip)
    if len(sys.argv) < 6:
        print_usage()
        sys.exit(1)

    # Menangkap argumen masukan dari terminal berdasarkan urutan indeks sys.argv
    input_user = sys.argv[1]
    input_password = sys.argv[2]
    input_database = sys.argv[3]
    input_table = sys.argv[4]
    input_key_file = sys.argv[5]
    
    # Menentukan nama berkas skema target agar sesuai dengan yang dibuat oleh skrip enkripsi
    derived_schema_file = f"schema_{input_table}.json"

    # Menyusun kamus konfigurasi database konektor
    target_db_config = {
        "host": "localhost",
        "user": input_user,
        "password": input_password,
        "database": input_database
    }

    # Mengeksekusi proses dekripsi
    run_decryption(target_db_config, input_table, input_key_file, derived_schema_file)
