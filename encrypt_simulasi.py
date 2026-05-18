import os
import sys
import json
import mysql.connector
from cryptography.fernet import Fernet

def print_usage():
    """Menampilkan panduan penggunaan jika argumen tidak sesuai."""
    print("\n[!] Penggunaan Argumen Salah.")
    print("Format: python3 encrypt_simulasi.py [user] [password] [nama_database] [nama_tabel] [file_kunci]")
    print("Contoh: python3 encrypt_simulasi.py root '' bassist users secret.key\n")

def load_key(key_file_path):
    """Memuat kunci enkripsi yang ada atau membuat baru jika belum tersedia."""
    if not os.path.exists(key_file_path):
        # Membuat kunci Fernet baru yang valid (32 url-safe base64-encoded bytes)
        key = Fernet.generate_key()
        with open(key_file_path, "wb") as f:
            f.write(key)
        print(f"[+] Kunci baru berhasil dibuat dan disimpan di: {key_file_path}")
    else:
        print(f"[*] Menggunakan kunci yang sudah ada dari: {key_file_path}")
    
    with open(key_file_path, "rb") as f:
        return f.read()

def backup_schema_and_alter(cursor, table_name, schema_file_path):
    """Membaca skema asli tabel, menyimpannya ke JSON, lalu mengubah kolom ke TEXT."""
    print(f"[*] Menyesuaikan struktur tabel '{table_name}' (Mengubah kolom ke TEXT)...")
    
    # Mengambil informasi struktur kolom dari tabel target
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    columns_info = cursor.fetchall()
    
    schema_data = {}
    for col in columns_info:
        field_name = col['Field']
        field_type = col['Type']
        
        # Kolom 'id' (baik huruf besar maupun kecil) dilewati agar relasi utama tidak rusak
        if field_name.lower() != 'id':
            # Decode bytes ke string jika driver mengembalikan objek bytes
            type_str = field_type.decode('utf-8') if isinstance(field_type, bytes) else str(field_type)
            schema_data[field_name] = type_str
            
            # Mengubah tipe data ke TEXT agar mampu menampung string hasil enkripsi Fernet yang panjang
            cursor.execute(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` TEXT")
    
    # Menyimpan skema asli ke dalam berkas JSON sebagai acuan pemulihan (dekripsi)
    with open(schema_file_path, "w") as f:
        json.dump(schema_data, f, indent=4)
    print(f"[✔] Skema struktur asli berhasil disimpan ke: {schema_file_path}")
    
    return schema_data  # Mengembalikan dict agar bisa langsung dipakai di memori

def run_encryption(db_config, table_name, key_file_path, schema_file_path):
    """Fungsi utama untuk melakukan enkripsi data pada tabel."""
    conn = None
    try:
        # Menginisialisasi kunci dan suite enkripsi Fernet
        raw_key = load_key(key_file_path)
        cipher_suite = Fernet(raw_key)
        
        # Membuka koneksi ke database berdasarkan parameter yang diterima
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Eksekusi penyesuaian skema database dan ambil datanya langsung ke memori
        schema_data = backup_schema_and_alter(cursor, table_name, schema_file_path)
        active_columns = list(schema_data.keys())
        
        if not active_columns:
            print("[!] Tidak ada kolom yang dapat dienkripsi (atau tabel kosong).")
            return
        
        # Mengambil seluruh data dari tabel
        cursor.execute(f"SELECT * FROM `{table_name}`")
        rows = cursor.fetchall()
        
        print(f"\n[*] Memproses Enkripsi (Menampilkan maksimal 10 baris pertama untuk log)...")
        print("-" * 80)

        updated_count = 0
        for i, row in enumerate(rows):
            updates = {}
            show_log = i < 10  # Pembatasan visual output di terminal

            # Deteksi dinamis nama kolom Primary Key (ID atau id)
            row_id_key = 'ID' if 'ID' in row else ('id' if 'id' in row else None)
            primary_id = row.get(row_id_key) if row_id_key else None

            if show_log:
                print(f"RECORD #{i+1} [ID: {primary_id}]")

            # Melakukan enkripsi pada setiap kolom yang tercatat di dalam skema
            for col in active_columns:
                val = row.get(col)
                
                # Memastikan data ada dan belum pernah dienkripsi (token Fernet standar diawali 'gAAAA')
                if val is not None and not str(val).startswith("gAAAA"):
                    enc_val = cipher_suite.encrypt(str(val).encode()).decode()
                    updates[col] = enc_val
                    if show_log:
                        print(f"  > {col}: {str(val)[:15]}... -> {enc_val[:30]}...")
            
            # Memperbarui baris data di database jika ada kolom yang diubah
            if updates and primary_id is not None:
                set_query = ", ".join([f"`{k}`=%s" for k in updates.keys()])
                query = f"UPDATE `{table_name}` SET {set_query} WHERE `{row_id_key}`=%s"
                cursor.execute(query, list(updates.values()) + [primary_id])
                updated_count += 1
                if show_log: 
                    print("  [STATUS] Kolom berhasil diperbarui dengan data terenkripsi.")
            
            if show_log: 
                print("-" * 80)
            if i == 9 and len(rows) > 10:
                print(f"... Memproses sisa {len(rows)-10} baris data lainnya di latar belakang ...")

        # Menerapkan perubahan ke database secara permanen
        conn.commit()
        print(f"\n[✔] PROSES SELESAI. Total {updated_count} baris data berhasil dienkripsi.")

    except mysql.connector.Error as db_err:
        print(f"[ERROR] Kegagalan pada koneksi atau operasi database: {db_err}")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan tak terduga: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print_usage()
        sys.exit(1)

    input_user = sys.argv[1]
    input_password = sys.argv[2]
    input_database = sys.argv[3]
    input_table = sys.argv[4]
    input_key_file = sys.argv[5]
    
    derived_schema_file = f"schema_{input_table}.json"

    target_db_config = {
        "host": "localhost",
        "user": input_user,
        "password": input_password,
        "database": input_database
    }

    run_encryption(target_db_config, input_table, input_key_file, derived_schema_file)
