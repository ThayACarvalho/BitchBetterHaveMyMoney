import os
import base64
import json
import gspread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# Carrega credenciais Google a partir de Base64
creds_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
creds_dict = json.loads(creds_json)

# Autentica Google Sheets
gc = gspread.service_account_from_dict(creds_dict)
SHEET_ID = os.getenv("SHEET_ID")
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envie seus gastos no formato:\n\n"
        "valor categoria meio_de_pagamento\n\n"
        "Exemplo:\n"
        "15 mercado cartao_caixa"
    )

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    all_rows = worksheet.get_all_values()[1:]
    valores = [float(r[1]) for r in all_rows if r[0] == user_id]
    total_gasto = sum(valores) if valores else 0
    await update.message.reply_text(f"Você já gastou: R$ {total_gasto:.2f}")

async def categoria_mais_gasta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from collections import defaultdict
    user_id = str(update.effective_user.id)
    all_rows = worksheet.get_all_values()[1:]
    categorias = defaultdict(float)
    for r in all_rows:
        if r[0] == user_id:
            categorias[r[2]] += float(r[1])
    if not categorias:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return
    categoria = max(categorias, key=categorias.get)
    await update.message.reply_text(f"Categoria que você mais gastou: {categoria}")

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()

    if len(parts) < 3:
        await update.message.reply_text("Formato inválido. Use: valor categoria meio_de_pagamento")
        return

    valor = parts[0]
    categoria = parts[1]
    meio = " ".join(parts[2:])

    # Salva no Google Sheets com ID do usuário
    worksheet.append_row([update.effective_user.id, valor, categoria, meio])

    await update.message.reply_text(
        f"Recebido:\nValor: {valor}\nCategoria: {categoria}\nMeio: {meio}"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("categoria_mais_gasta", categoria_mais_gasta))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))
    app.run_polling()

if __name__ == "__main__":
    main()
