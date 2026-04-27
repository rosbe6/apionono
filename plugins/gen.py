import io
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.card_tools import gen_logic 

async def gen_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ **Uso:** `/gen bin|mm|aa|cvv cantidad`", parse_mode="Markdown")
        return

    bin_format = context.args[0]
    quantity = int(context.args[1]) if len(context.args) > 1 else 10
    
    # Generar lista
    cards = [gen_logic(bin_format) for _ in range(min(quantity, 1000))]
    
    # Botón de Regenerar
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Regenerar", callback_data=f"regen_{bin_format}_{quantity}")]
    ])

    if quantity <= 15:
        # Aquí creamos una lista de tarjetas, cada una envuelta en <code>
        tarjetas_formateadas = "\n".join([f"<code>{c}</code>" for c in cards])

        txt = (
            f"<b>✨ Tarjetas Generadas</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
            f"{tarjetas_formateadas}\n"  # <--- Cada una es copiable por separado
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>Bin:</b> <code>{bin_format[:6]}</code>"
        )
        
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=keyboard)
    else:
        out = io.BytesIO(("\n".join(cards)).encode())
        out.name = f"{bin_format[:6]}.txt"
        await update.message.reply_document(document=out, caption=f"✨ BIN: `{bin_format[:6]}` | Cant: `{quantity}`", parse_mode="Markdown", reply_markup=keyboard)