import asyncio
import random
import string
from unittest.mock import AsyncMock, MagicMock
from handlers.admin import genkey_cmd
from handlers.callbacks import menu_callbacks, handle_text_input
from database import load_keys, OWNER_ID

async def test_genkey_flow():
    print("🔑 INICIANDO PRUEBAS DE SISTEMA DE KEYS\n")

    # --- CONFIGURACIÓN DE MOCKS ---
    def crear_contexto(args=None):
        ctx = MagicMock()
        ctx.args = args or []
        ctx.user_data = {}
        return ctx

    def crear_update(user_id, text=""):
        up = AsyncMock()
        up.effective_user.id = user_id
        up.message.text = text
        up.message.reply_text = AsyncMock()
        up.callback_query = AsyncMock()
        up.callback_query.message = up.message
        return up

    # --- TEST 1: SEGURIDAD (USUARIO FREE) ---
    print("Test 1: Usuario sin rango intentando generar key...")
    up_free = crear_update(12345)
    ctx_free = crear_contexto()
    await genkey_cmd(up_free, ctx_free)
    if "No tienes rango suficiente" in up_free.message.reply_text.call_args[0][0]:
        print("✅ Bloqueo de seguridad exitoso.\n")

    # --- TEST 2: FLUJO KEY ETERNA (ADMIN) ---
    print("Test 2: Generando Key ETERNA para Premium (Rango 1)...")
    up_admin = crear_update(OWNER_ID) # Usamos tu ID de jefe
    ctx_admin = crear_contexto(["premium"])
    
    # 1. Ejecutar comando inicial
    await genkey_cmd(up_admin, ctx_admin)
    
    # 2. Simular clic en botón "Eterna"
    up_admin.callback_query.data = "k_eterna"
    await menu_callbacks(up_admin, ctx_admin)
    
    res_eterna = up_admin.callback_query.edit_message_text.call_args[0][0]
    if "Eterna Generada" in res_eterna:
        key = res_eterna.split("`")[1]
        print(f"✅ Key Eterna creada: {key}\n")

    # --- TEST 3: FLUJO KEY TEMPORAL (30 DÍAS) ---
    print("Test 3: Generando Key por 30 DÍAS...")
    ctx_time = crear_contexto(["premium"])
    
    # 1. Comando inicial
    await genkey_cmd(up_admin, ctx_time)
    
    # 2. Simular clic en "Días"
    up_admin.callback_query.data = "k_dias"
    await menu_callbacks(up_admin, ctx_time)
    
    # 3. Simular que el usuario escribe "30" en el chat
    up_admin.message.text = "30"
    await handle_text_input(up_admin, ctx_time)
    
    res_time = up_admin.message.reply_text.call_args[0][0]
    if "30 días generada" in res_time:
        key_t = res_time.split("`")[1]
        print(f"✅ Key Temporal creada: {key_t}\n")

    # --- VERIFICACIÓN FINAL EN BASE DE DATOS ---
    db = await load_keys()
    print(f"📊 Estadísticas finales:")
    print(f"Total de llaves en DB: {len(db['keys'])}")
    
    # Buscar las llaves creadas en la DB para confirmar persistencia
    keys_db = [k['key'] for k in db['keys']]
    if key in keys_db and key_t in keys_db:
        print("✅ PERSISTENCIA: Todas las llaves se guardaron correctamente en el JSON.")
    else:
        print("❌ ERROR: Las llaves no se encuentran en el archivo físico.")

if __name__ == "__main__":
    asyncio.run(test_genkey_flow())