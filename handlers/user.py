# handlers/user.py
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from config import API_URL
from database import get_rango, load_keys, save_keys  # <-- AGREGAR get_rango AQUÍ
from engines.bins_engine import get_bin_info
from gates.payflow1 import ProphecyChecker
from database import check_antispam

from database import antispam_db  # Importamos el diccionario

import time

# handlers/user.py

async def start_cmd(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Gates 🛠", callback_data="main_gates"),
            InlineKeyboardButton("Tools 🎟", callback_data="main_tools"),
            InlineKeyboardButton("Info 👤", callback_data="ver_perfil")
        ]
    ]
    await update.message.reply_text(
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "<b>[      APION BOT MENÚ      ]</b>\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "Bienvenido a <b>APION BOT</b> descubre todos los <b>Comandos</b>, <b>Gates</b>, <b>Tools</b> Pulsando los botones de abajo 👇\n\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def me_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_id = u.effective_user.id
    rango_num = get_rango(user_id)
    
    rangos_nombres = {
        3: "OWNER 👑",
        2: "ADMIN 👨‍✈️",
        1: "PREMIUM 🌟",
        0: "FREE 👤"
    }
    
    mi_rango = rangos_nombres.get(rango_num, "FREE 👤")
    
    msg = f"👤 **PERFIL DE USUARIO**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"Nombre: {u.effective_user.first_name}\n"
    msg += f"ID: `{user_id}`\n"
    msg += f"Rango: **{mi_rango}**\n"
    
    if rango_num == 1:
        data = await load_keys()
        exp = data["usuarios"].get(str(user_id), {}).get("expires_at", "N/A")
        msg += f"Expira: `{exp[:10] if exp != 'EVER' else 'Eterna ♾'}`\n"
        
    msg += f"━━━━━━━━━━━━━━━━━━"
    await u.message.reply_text(msg, parse_mode='Markdown')

async def bin_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    args = u.message.text.split()
    if len(args) < 2: return await u.message.reply_text("🛠 Uso: `/bin 454924`")
    
    info, bank, pais = await get_bin_info(args[1])
    await u.message.reply_text(f"🔍 **BIN INFO:**\n\n━━━━━━━━╰☆╮━━━━━━━━\nInformation: {info}\nBank: {bank}\nCountry: {pais}\n━━━━━━━━╰☆╮━━━━━━━━", parse_mode='Markdown')

async def status_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient() as cl:
            await cl.get(f"{API_URL}/status", timeout=5)
            await u.message.reply_text("✅ **Server Online**\nLas APIs están respondiendo correctamente.")
    except:
        await u.message.reply_text("❌ **Server Offline**\nNo se pudo contactar con el servidor de validación.")

async def popo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    args = u.message.text.split()
    if len(args) > 1:
        try:
            monto = float(args[1])
            await u.message.reply_text(f"💰 **Conversión Glow:**\nEl monto de {monto} equivale a aproximadamente: `{monto * 0.7:.2f}` USD")
        except: pass

async def redeem_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    args = u.message.text.split()
    if len(args) < 2: return
    
    key_in = args[1]
    data = await load_keys()
    user_id = str(u.effective_user.id)
    
    for k in data["keys"]:
        if k["key"] == key_in and not k.get("used"):
            k["used"] = True
            k["user"] = u.effective_user.id
            rango_key = k.get("range", "Premium") # Si no tiene, por defecto es Premium
            
            # Calculamos expiración
            exp = "EVER"
            if not k.get("permanent"):
                dias = k.get("days", 30)
                exp = (datetime.now() + timedelta(days=dias)).isoformat()
            
            # Guardamos en la sección de usuarios para que get_rango() lo reconozca
            if "usuarios" not in data: data["usuarios"] = {}
            data["usuarios"][user_id] = {
                "rango": rango_key.upper(),
                "expires_at": exp
            }
            
            k["expires_at"] = exp
            await save_keys(data)
            return await u.message.reply_text(f"✅ **Suscripción Activada**\nAhora eres: **{rango_key.upper()}**")
    
    await u.message.reply_text("❌ Key inválida o ya usada.")




async def prophecy_command_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    message = u.message
    username = u.effective_user.username or u.effective_user.first_name
    # 1. Extraer CC
    try:
        cc_input = c.args[0]
    except IndexError:
        await message.reply_text(
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[ Gate Payflow CVV ]</b>\n\n"
            "<b>Uso ></b> <code>/pfw cc|mes|año|cvv</code>\n\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>", parse_mode="HTML")
        return
    

   

    OWNER_ID = 5651880136 
    ADMINS = [5133617831]
    
    user_id = u.effective_user.id
    
    # Una sola línea para el antispam
    puedo_pasar, espera = check_antispam(user_id, OWNER_ID, ADMINS)
    
    if not puedo_pasar:
        return await u.message.reply_text(
            f"<b>⚠️ ANTISPAM</b>\n\nDebes esperar <b>{espera}s</b>.",
            parse_mode="HTML"
        )


    # 2. Mensaje de carga
    status_msg = await message.reply_text(
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[ Gateway > Payflow CVV ]</b>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n⏳"
            " <i>Iniciando Check...</i>", parse_mode="HTML")
    start_time = time.time()

    # --- CORRECCIÓN AQUÍ ---
    try:
        # Seleccionamos un proxy de tu lista (asegúrate de tener PROXIES_LIST definida o impórtala)
        proxy_selected = "http://b7e37b644dc5b6cb:VYdXQ67KAtfPgacU@res.proxy-seller.com:10000"
        
        # 3. PASO A PASO: Instanciar y luego ejecutar
        checker = ProphecyChecker(cc_input, proxy_url=proxy_selected) # Instancia
        response = await checker.run() # Ejecución asíncrona
    except Exception as e:
        response = f"Error técnico: {str(e)}"
    # -----------------------
    
    # 4. Diseño de la respuesta final
    end_time = round(time.time() - start_time, 2)
    
    # Definir icono según respuesta
    if "CHARGED" in response or "10069" in response:
        status = "Aprobada ✅"
    elif "15005" in response:
        status = "Declinada ❌"
    else:
        status = "Declinada ❌"

    final_text = (
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "<b>[ Gateway > Payflow CVV ]</b>\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n\n"
        f"<b>CC ></b> <code>{cc_input}</code>\n"
        f"<b>Status ></b> {status}\n"
        f"<b>Response ></b> {response}\n\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        f"<b>Tiempo: ></b> {end_time}\n\n"
        f"<b>[Payflow CVV] > Chk By: @{username}</b>\n\n"
    )

    await status_msg.edit_text(final_text, parse_mode="HTML")