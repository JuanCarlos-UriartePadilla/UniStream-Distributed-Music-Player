import json
import os
from cryptography.fernet import Fernet

# --- CONFIGURACIÓN ---
# Ruta exacta de tu montaje NFS en el cliente
NFS_PATH = "/mnt/dfs/music_data"
KEY_FILE = "secret.key"

class SecureStorage:
    def __init__(self):
        # Verificación de seguridad: ¿Existe la carpeta?
        if not os.path.exists(NFS_PATH):
            # Intentar crearla si no existe (opcional, pero ayuda en pruebas)
            try:
                os.makedirs(NFS_PATH, exist_ok=True)
            except:
                pass
            
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self):
        """Carga la llave existente o crea una nueva si no existe."""
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(KEY_FILE, "wb") as key_file:
                key_file.write(key)
            return key

    def save_table(self, table_name, data):
        """
        1. Convierte data a JSON
        2. Encripta el JSON
        3. Guarda en el NFS
        """
        try:
            # Convertir a String JSON
            json_data = json.dumps(data)
            
            # Encriptar (Fernet usa AES)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            # Definir ruta final en el NFS
            file_path = os.path.join(NFS_PATH, f"{table_name}.json")
            
            # Escribir en disco (NFS)
            with open(file_path, "wb") as file:
                file.write(encrypted_data)
            
            print(f"[STORAGE] Tabla '{table_name}' guardada y encriptada.")
            
        except Exception as e:
            print(f"[ERROR STORAGE] No se pudo guardar {table_name}: {e}")
            raise e

    def read_table(self, table_name):
        """
        1. Lee el archivo encriptado del NFS
        2. Desencripta
        3. Retorna JSON usable
        """
        file_path = os.path.join(NFS_PATH, f"{table_name}.json")
        
        if not os.path.exists(file_path):
            return [] # Retorna lista vacia si no existe

        try:
            with open(file_path, "rb") as file:
                encrypted_data = file.read()
                
            # Desencriptar
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Convertir de nuevo a Objeto Python
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"[ERROR STORAGE] No se pudo leer {table_name}: {e}")
            return []
