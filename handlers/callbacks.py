# handlers/callbacks.py
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GATES_STATUS
from database import load_keys, save_keys, get_rango 
from handlers.card_tools import cache_bins # Asegúrate de importar el cache

import io
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.card_tools import gen_logic

async def menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data 
    chat_id = update.effective_chat.id # Lo necesitamos para el cache
    await query.answer()

    # Mantenemos el teclado siempre visible para que no desaparezca
    keyboard = [
        [
            InlineKeyboardButton("Gates 🛠", callback_data="main_gates"),
            InlineKeyboardButton("Tools 🎟", callback_data="main_tools"),
            InlineKeyboardButton("Info 👤", callback_data="ver_perfil")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # --- TUS GATES ---
    if data == "main_gates":
        # 🟢 Lógica de actualización en vivo 🔴
        # Consultamos el estado de cada uno. Si no existe, por defecto es True (ON)
        status_pp = "🟢 ON" if GATES_STATUS.get("pp", True) else "🔴 OFF"
        status_gt = "🟢 ON" if GATES_STATUS.get("gt", True) else "🔴 OFF"
        status_pfw = "🟢 ON" if GATES_STATUS.get("pfw", True) else "🔴 OFF"
        # Supongamos que /chk es el gate 'gt' o tiene su propio status
        txt = (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[                 GATES                 ]</b>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            f"• <code>/gt</code> | <b>Gate Promerica</b> - Status > {status_gt}\n"
            "<i>Uso Exclusivo Para Tarjetas Promerica Guatemala</i>\n\n"
            
            f"• <code>/pp</code> | <b>Gate PayPal</b> - Status > {status_pp}\n"
            "<i>Gate PayPal Auth</i>\n\n"

            f"• <code>/pp</code> | <b>Gate Payflow CVV</b> - Status > {status_pfw}\n"
            "<i>Gate Payflow CVV Charged</i>\n"


            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
        )
        
        await query.edit_message_text(txt, reply_markup=reply_markup, parse_mode='HTML')

    # --- TUS TOOLS ---


    
    elif data == "main_tools":
        txt = (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[                 TOOLS                 ]</b>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "• <code>/bin</code> | <b>Información del Bin</b>\n"
            "<i>Ejemplo:</i> <code>/bin 443019</code>\n\n"
            
            "• <code>/binlook</code> | <b>Búsqueda de Bins</b>\n"
            "<i>Ejemplo:</i> <code>/binlook [Pais] - [Categoría] - [Nivel]</code>\n\n"
            
            "• <code>/extra</code> | <b>Genera una extra</b>\n"
            "<i>Ejemplo:</i> <code>/extra [Bin]</code>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"

            "• <code>/vbv</code> | <b>Verifica si un bin tiene 3D</b>\n"
            "<i>Ejemplo:</i> <code>/3d [cc|mm|aa|cvv]</code>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
        )
        # Cambiamos parse_mode a 'HTML' para que reconozca las etiquetas <b> e <i>
        await query.edit_message_text(txt, reply_markup=reply_markup, parse_mode='HTML')


    # --- TU PERFIL ---
    elif data == "ver_perfil":
        # 1. Obtenemos el rango y nombre
        user_id = query.from_user.id
        rango_num = get_rango(user_id)
        
        rangos_nombres = {
            3: "OWNER 👑",
            2: "ADMIN 👨‍✈️",
            1: "PREMIUM 🌟",
            0: "FREE 👤"
        }
        mi_rango = rangos_nombres.get(rango_num, "FREE 👤")

        # 2. Lógica de expiración integrada
        expira_txt = "N/A"
        if rango_num == 1:
            data_keys = await load_keys()
            exp = data_keys["usuarios"].get(str(user_id), {}).get("expires_at", "N/A")
            expira_txt = f"{exp[:10]}" if exp != "EVER" else "Eterna ♾"
        elif rango_num in [2, 3]:
            expira_txt = "Ilimitada 🛡️"

        # 3. El diseño que me pediste
        txt = (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[     PERFIL DE USUARIO     ]</b>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            f"<b>Nombre |</b> {query.from_user.first_name}\n"
            f"<b>ID |</b> <code>{user_id}</code>\n"
            f"<b>Rango |</b> {mi_rango}\n"
            f"<b>Expira |</b> {expira_txt}\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
        )
        
        await query.edit_message_text(txt, reply_markup=reply_markup, parse_mode='HTML')

    # --- TU GENERACIÓN DE KEYS ---
    elif data == "k_eterna":
        rango_key = context.user_data.get('temp_range', 'Premium')
        key = f"APION-{rango_key.upper()}-EVER-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        db_data = await load_keys()
        if "keys" not in db_data: db_data["keys"] = [] # Seguridad extra
        
        db_data["keys"].append({
            "key": key, 
            "used": False, 
            "permanent": True, 
            "range": rango_key 
        })
        await save_keys(db_data)
        await query.edit_message_text(f"♾ **Key {rango_key} Eterna Generada:**\n`{key}`", parse_mode='Markdown')
        context.user_data.pop('temp_range', None)
        
    elif data == "k_dias":
        context.user_data['esperando_dias'] = True
        await query.message.reply_text("🔢 **¿Cuántos días de suscripción deseas asignar?**")

    # --- NUEVA LÓGICA DE BANCOS (AGREGADA SIN BORRAR NADA) ---
    elif data.startswith("bnk_"):
        index = int(data.split("_")[1])
        
        if chat_id in cache_bins:
            bin_data = cache_bins[chat_id]["data"]
            keys_list = cache_bins[chat_id]["sorted_keys"]
            query_name = cache_bins[chat_id]["query"]
            
            selected_key = keys_list[index]
            banco = bin_data[selected_key]
            
            txt = (
                f"🏦 BANCO:  `{banco['nombre']}`\n"
                f"🔍 Resultados para: `{query_name}`\n"
                "━━━━━━━━━━━━━━━━━━\n"
            )
            
            for cat, bins in banco["sub"].items():
                bins_str = ", ".join([f"`{b}`" for b in bins])
                txt += f"• **{cat}:**\n  └ {bins_str}\n"
            
            kb = [[InlineKeyboardButton("⬅️ Volver a la lista", callback_data="back_bins")]]
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        else:
            await query.edit_message_text("⚠️ El buscador expiró o el bot se reinició. Usa `/binlook` de nuevo.")

    elif data == "back_bins":
        if chat_id in cache_bins:
            data_cache = cache_bins[chat_id]["data"]
            keys_list = cache_bins[chat_id]["sorted_keys"]
            q = cache_bins[chat_id]["query"]
            
            kb_list = [[InlineKeyboardButton(f"🏦 {data_cache[k]['nombre'][:35]}", callback_data=f"bnk_{i}")] for i, k in enumerate(keys_list)]
            await query.edit_message_text(f"✅ Resultados para: {q}", reply_markup=InlineKeyboardMarkup(kb_list), parse_mode='Markdown')

# --- ESTA ES LA FUNCIÓN QUE FALTABA Y DABA EL ERROR DE IMPORTACIÓN ---
async def handle_text_input(u: Update, c: ContextTypes.DEFAULT_TYPE):
    # Solo ADMIN (Nivel 2) o superior pueden procesar esto
    if get_rango(u.effective_user.id) < 2: 
        return
        
    if c.user_data.get('esperando_dias'):
        try:
            dias = int(u.message.text)
            rango = c.user_data.get('temp_range', 'Premium')
            key = f"APION-{rango.upper()}-TIME-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            data = await load_keys()
            data["keys"].append({
                "key": key, 
                "used": False, 
                "days": dias, 
                "permanent": False,
                "range": rango 
            })
            await save_keys(data)
            await u.message.reply_text(f"🔑 Key {rango} de {dias} días generada:**\n`{key}`", parse_mode='Markdown')
        except ValueError:
            await u.message.reply_text("❌ Por favor, envía un número válido de días.")
        finally:
            c.user_data['esperando_dias'] = False
            c.user_data.pop('temp_range', None)



async def callback_regen(update, context):
    query = update.callback_query
    # data: regen_451012|12|28_20
    _, bin_format, quantity = query.data.split("_")
    quantity = int(quantity)

    await query.answer("Generando nuevas tarjetas... ⏳")
    cards = [gen_logic(bin_format) for _ in range(quantity)]
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Regenerar", callback_data=f"regen_{bin_format}_{quantity}")]])

    if quantity <= 15:
        # Lo mismo: lista de <code> para el mensaje editado
        tarjetas_formateadas = "\n".join([f"<code>{c}</code>" for c in cards])

        txt = (
            f"<b>✨ Tarjetas Generadas</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
            f"{tarjetas_formateadas}\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>"
        )
        
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=keyboard)
    else:
        out = io.BytesIO(("\n".join(cards)).encode())
        out.name = f"{bin_format[:6]}.txt"
        await context.bot.send_document(chat_id=query.message.chat_id, document=out, caption=f"✨ **Nuevas:** `{quantity}`", parse_mode="Markdown", reply_markup=keyboard)