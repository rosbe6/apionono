# database.py
import json
import os
import time
import asyncio

#Antispam db

antispam_db = {}


# Configuración de IDs
OWNER_ID = 5651880136 
FILE_KEYS = "keys.json"         # Aquí se guardan Keys y Usuarios
FILE_EXTRAS = "database_apion.json" # Aquí solo están tus listas de BINS

DB_LOCK = asyncio.Lock()

# --- FUNCIONES PARA KEYS Y USUARIOS ---
async def load_keys():
    async with DB_LOCK:
        if not os.path.exists(FILE_KEYS):
            base = {"keys": [], "usuarios": {}}
            with open(FILE_KEYS, "w") as f:
                json.dump(base, f, indent=4)
            return base
        with open(FILE_KEYS, "r") as f:
            try:
                return json.load(f)
            except:
                return {"keys": [], "usuarios": {}}

async def save_keys(data):
    async with DB_LOCK:
        with open(FILE_KEYS, "w") as f:
            json.dump(data, f, indent=4)

# --- FUNCIÓN EXCLUSIVA PARA EXTRAS ---
async def load_extras():
    # Esta solo lee, no necesita bloqueo de escritura usualmente
    if not os.path.exists(FILE_EXTRAS):
        return {}
    with open(FILE_EXTRAS, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def get_rango(user_id):
    if user_id == OWNER_ID: return 3
    if os.path.exists(FILE_KEYS):
        try:
            with open(FILE_KEYS, "r") as f:
                data = json.load(f)
                user_str = str(user_id)
                u_data = data.get("usuarios", {}).get(user_str, {})
                rango = u_data.get("rango", "FREE")
                return {"OWNER": 3, "ADMIN": 2, "PREMIUM": 1}.get(rango, 0)
        except: return 0
    return 0



def obtener_rango(user_id):
    try:
        with open('keys.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertimos ID a string porque en el JSON están como "12345"
        user_id_str = str(user_id)
        
        # Buscamos al usuario dentro de la sección "usuarios"
        usuarios = data.get("usuarios", {})
        
        if user_id_str in usuarios:
            return usuarios[user_id_str].get("rango", "FREE")
        
        return "FREE" # Si el usuario no existe en el JSON
    except Exception as e:
        print(f"Error al leer keys.json: {e}")
        return "FREE"

def check_antispam_vbv(user_id, owner_id, admins_list):
    """
    Función maestra para llamar antes de cualquier comando.
    Retorna (True, 0) si puede pasar.
    Retorna (False, tiempo) si debe esperar.
    """
    now = time.time()
    
    # 1. Los jefes no tienen antispam
    if user_id == owner_id or user_id in admins_list:
        return True, 0

    # 2. Llamamos a tu función para ver el rango
    rango = obtener_rango(user_id)
    
    # 3. Definimos segundos según rango
    cooldown = 20 if rango == "PREMIUM" else 30
    
    # 4. Cálculo de tiempo restante
    last_time = antispam_db.get(user_id, 0)
    tiempo_restante = int(last_time + cooldown - now)

    if tiempo_restante > 0:
        return False, tiempo_restante

    # 5. Si pasó, actualizamos el último uso
    antispam_db[user_id] = now
    return True, 0


def check_antispam(user_id, owner_id, admins_list):
    """
    Función maestra para llamar antes de cualquier comando.
    Retorna (True, 0) si puede pasar.
    Retorna (False, tiempo) si debe esperar.
    """
    now = time.time()
    
    # 1. Los jefes no tienen antispam
    if user_id == owner_id or user_id in admins_list:
        return True, 0

    # 2. Llamamos a tu función para ver el rango
    rango = obtener_rango(user_id)
    
    # 3. Definimos segundos según rango
    cooldown = 30 if rango == "PREMIUM" else 60
    
    # 4. Cálculo de tiempo restante
    last_time = antispam_db.get(user_id, 0)
    tiempo_restante = int(last_time + cooldown - now)

    if tiempo_restante > 0:
        return False, tiempo_restante

    # 5. Si pasó, actualizamos el último uso
    antispam_db[user_id] = now
    return True, 0