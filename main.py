import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from config import GATES_STATUS
from handlers.admin import editgate
from handlers.user import start_cmd, me_cmd, redeem_cmd
from handlers.admin import genkey_cmd, setrank_cmd
from handlers.gates import process_gate, worker_bot
from handlers.callbacks import menu_callbacks, handle_text_input
from handlers.card_tools import bin_master_handler, bin_cmd, vbv_command_handler
from handlers.card_tools import extra_cmd
from handlers.user import prophecy_command_handler
from handlers.gates import worker_bot


from plugins.gen import gen_cmd
from handlers.callbacks import callback_regen
from telegram.ext import CommandHandler, CallbackQueryHandler
# Si tienes una función para lanzar tu API de Promerica:
# from api_launcher import lanzar_api 

# Configuración de Logging para ver errores en consola
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def post_init(application):
    """
    Esta función se ejecuta justo después de iniciar el bot.
    Lanzamos los Workers que procesarán las tarjetas en segundo plano.
    """
    # Lanzamos 10 workers para procesar los Gates simultáneamente
    for i in range(1, 11):
        asyncio.create_task(worker_bot(i, application))
    print(f"🚀 {10} Workers de Gates iniciados correctamente.")

def main():
    # 1. (Opcional) Lanzar tu API local de Promerica si la tienes integrada
    # lanzar_api()

    # 2. Configurar la Aplicación con 32 Workers para fd múltiples usuarios
    # Esto permite que el bot responda a muchas personas al mismo tiempo
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True) # Esto activa el manejo de múltiples mensajes a la vez
        .build()
    )

    # --- HANDLERS DE USUARIO ---
    app.add_handler(CommandHandler("cmds", start_cmd))
    app.add_handler(CommandHandler("me", me_cmd))
    app.add_handler(CommandHandler("redeem", redeem_cmd))

    # --- HANDLERS DE ADMINISTRACIÓN ---
# --- HANDLERS DE ADMINISTRACIÓN ---
    app.add_handler(CommandHandler("editgate", editgate))
    app.add_handler(CommandHandler("genkey", genkey_cmd))
    app.add_handler(CommandHandler("setrank", setrank_cmd))

    # --- HANDLERS DE HERRAMIENTAS (BINS) ---
    app.add_handler(CommandHandler("vbv", vbv_command_handler))
    app.add_handler(CommandHandler("gen", gen_cmd))
    app.add_handler(CommandHandler("bin", bin_cmd))
    app.add_handler(CommandHandler("binlook", bin_master_handler))
    app.add_handler(CommandHandler("binbank", bin_master_handler))
    app.add_handler(CommandHandler("extra", extra_cmd))

    # --- HANDLERS DE GATES ---
    # Este va de ÚLTIMO porque el Regex r'^/' atrapa CUALQUIER cosa que empiece con /
    # Solo los comandos que REALMENTE son gates:
    app.add_handler(CommandHandler("pfw", prophecy_command_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^/(gt|pp|chk|vbv|py)'), process_gate))    # --- HANDLERS DE CALLBACKS Y TEXTO ---
    # Maneja todos los botones 
    app.add_handler(CallbackQueryHandler(callback_regen, pattern="^regen_")) # <--- AGREGA ESTA
    app.add_handler(CallbackQueryHandler(menu_callbacks))    # Maneja entradas de texto (como cuando el bot pide los días para una key)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print("🚀 Bot Modular con Multihilos Iniciado...")
    app.run_polling()

if __name__ == '__main__':
    main()