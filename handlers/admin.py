# handlers/admin.py
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMINS, GATES_STATUS
from database import load_keys, save_keys
from database import get_rango
# handlers/admin.py

async def genkey_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_id = u.effective_user.id
    rango_creador = get_rango(user_id)

    # 1. Si no es ni Admin ni Owner, fuera.
    if rango_creador < 2:
        return await u.message.reply_text("❌ No tienes rango suficiente.")

    # 2. Verificar qué rango quiere generar
    rango_solicitado = "Premium"
    if c.args and c.args[0].lower() == "admin":
        # Si intenta crear un ADMIN pero él solo es ADMIN (Nivel 2), se lo prohibimos
        if rango_creador < 3:
            return await u.message.reply_text("⚠️ Solo el Owner puede generar keys de rango ADMIN.")
        rango_solicitado = "Admin"

    # Guardamos en la memoria temporal para el callback
    c.user_data['temp_range'] = rango_solicitado
    
    kb = [[
        InlineKeyboardButton("Días 📅", callback_data="k_dias"),
        InlineKeyboardButton("Eterna ♾", callback_data="k_eterna")
    ]]
    
    await u.message.reply_text(
        f"✨ **Generador de Keys ({rango_solicitado.upper()})**\nSelecciona la duración:", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode='Markdown'
    )
async def users_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id not in ADMINS: return
    data = await load_keys()
    msg = "👥 **Usuarios Premium Activos:**\n\n"
    count = 0
    for k in data.get("keys", []):
        if k.get("used"):
            count += 1
            msg += f"• `{k['user']}` | {k.get('expires_at', 'Eterna')[:10]}\n"
    
    if count == 0: msg = "∅ No hay usuarios premium activos."
    await u.message.reply_text(msg, parse_mode='Markdown')

async def delmem(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id not in ADMINS: return
    if not c.args: return await u.message.reply_text("❌ Uso: `/delmem [ID]`")
    
    try:
        uid = int(c.args[0])
        data = await load_keys()
        data["keys"] = [k for k in data["keys"] if k.get("user") != uid]
        await save_keys(data)
        await u.message.reply_text(f"🗑️ El usuario `{uid}` ha sido eliminado de la DB.")
    except:
        await u.message.reply_text("❌ ID inválido.")

async def editgate(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id not in ADMINS: return
    if len(c.args) < 2: return await u.message.reply_text("❌ Uso: `/editgate [pp/gt] [on/off]`")
    
    gate, status = c.args[0].lower(), c.args[1].lower()
    if gate in GATES_STATUS:
        GATES_STATUS[gate] = (status == "on")
        await u.message.reply_text(f"✅ Gate **{gate.upper()}** actualizado a: `{status.upper()}`", parse_mode='Markdown')


async def setrank_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    # SOLO EL OWNER (Nivel 3)
    if get_rango(u.effective_user.id) < 3:
        return # Ni siquiera le contestamos para que no sepa que el comando existe

    if len(c.args) < 2:
        return await u.message.reply_text("💡 Uso: `/setrank [ID] [PREMIUM/ADMIN/FREE]`")

    target_id = c.args[0]
    nuevo_rango = c.args[1].upper()
    
    if nuevo_rango not in ["PREMIUM", "ADMIN", "FREE"]:
        return await u.message.reply_text("❌ Rango inválido. Usa: PREMIUM, ADMIN o FREE.")

    data = await load_keys()
    
    # Si el rango es FREE, lo quitamos de la lista de usuarios
    if nuevo_rango == "FREE":
        if target_id in data.get("usuarios", {}):
            del data["usuarios"][target_id]
    else:
        # Asignamos el rango con duración eterna por defecto
        if "usuarios" not in data: data["usuarios"] = {}
        data["usuarios"][target_id] = {
            "rango": nuevo_rango,
            "expires_at": "EVER"
        }

    await save_keys(data)
    await u.message.reply_text(f"✅ Usuario `{target_id}` actualizado a **{nuevo_rango}**.")