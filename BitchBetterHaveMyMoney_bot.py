import os
import base64
import json
import gspread
import io
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict

from telegram import Update, InputFile
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# Carrega credenciais Google
creds_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
creds_json = base64.b64decode(creds_b64).decode("utf-8")
creds_dict = json.loads(creds_json)

gc = gspread.service_account_from_dict(creds_dict)
SHEET_ID = os.getenv("SHEET_ID")
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

BOT_TOKEN = os.getenv("BOT_TOKEN")


def parse_date(text):
    """Tenta identificar datas no texto."""
    try:
        return datetime.strptime(text, "%d/%m/%Y")
    except:
        return datetime.today()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envie seus gastos no formato:\n\n"
        "valor categoria meio_de_pagamento data\n\n"
        "Exemplo:\n"
        "15 mercado caixa 01/11/2025\n\n"
        "Comandos disponíveis:\n"
        "/total\n"
        "/total_mes 11/2025\n"
        "/total_categoria mercado\n"
        "/total_meio caixa\n"
        "/grafico_mes 11/2025"
    )


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().split()

    if len(text) < 4:
        await update.message.reply_text("Formato inválido. Use: valor categoria meio data")
        return

    valor = float(text[0])
    categoria = text[1]
    meio = text[2]
    data = parse_date(text[3]).strftime("%d/%m/%Y")

    worksheet.append_row([update.effective_user.id, valor, categoria, meio, data])

    await update.message.reply_text(
        f"Gasto registrado:\nValor: {valor}\nCategoria: {categoria}\nMeio: {meio}\nData: {data}"
    )


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = worksheet.get_all_values()[1:]
    uid = str(update.effective_user.id)

    valores = [float(r[1]) for r in rows if r[0] == uid]
    await update.message.reply_text(f"Total gasto: R$ {sum(valores):.2f}")


async def total_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = worksheet.get_all_values()[1:]
    uid = str(update.effective_user.id)
    
    if len(context.args) == 0:
        await update.message.reply_text("Use: /total_mes 11/2025")
        return
    
    mes_ano = context.args[0]

    total = 0
    for r in rows:
        if r[0] == uid:
            data = datetime.strptime(r[4], "%d/%m/%Y")
            if data.strftime("%m/%Y") == mes_ano:
                total += float(r[1])

    await update.message.reply_text(f"Total gasto em {mes_ano}: R$ {total:.2f}")


async def total_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Use: /total_categoria mercado")
        return

    categoria = context.args[0]

    rows = worksheet.get_all_values()[1:]
    uid = str(update.effective_user.id)

    total = sum(float(r[1]) for r in rows if r[0] == uid and r[2] == categoria)
    await update.message.reply_text(f"Total gasto em {categoria}: R$ {total:.2f}")


async def total_meio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Use: /total_meio caixa")
        return

    meio = context.args[0]

    rows = worksheet.get_all_values()[1:]
    uid = str(update.effective_user.id)

    total = sum(float(r[1]) for r in rows if r[0] == uid and r[3] == meio)
    await update.message.reply_text(f"Total gasto no meio '{meio}': R$ {total:.2f}")


async def grafico_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Use: /grafico_mes 11/2025")
        return

    mes_ano = context.args[0]
    rows = worksheet.get_all_values()[1:]
    uid = str(update.effective_user.id)

    categorias = defaultdict(float)

    for r in rows:
        if r[0] == uid:
            data = datetime.strptime(r[4], "%d/%m/%Y")
            if data.strftime("%m/%Y") == mes_ano:
                categorias[r[2]] += float(r[1])

    if not categorias:
        await update.message.reply_text("Nenhum gasto nesse mês.")
        return

    labels = categorias.keys()
    values = categorias.values()

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.set_title(f"Gastos por categoria - {mes_ano}")

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    await update.message.reply_photo(InputFile(buffer, filename="grafico.png"))
    buffer.close()


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("total_mes", total_mes))
    app.add_handler(CommandHandler("total_categoria", total_categoria))
    app.add_handler(CommandHandler("total_meio", total_meio))
    app.add_handler(CommandHandler("grafico_mes", grafico_mes))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))

    app.run_polling()


if __name__ == "__main__":
    main()
