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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))
    app.run_polling()

if __name__ == "__main__":
    main()
