#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot de gastos multiusuário com integração ao Google Sheets e geração de gráficos.
Execução no Railway:

Variáveis de ambiente necessárias:
- BOT_TOKEN
- GOOGLE_SERVICE_ACCOUNT_BASE64  (conteúdo base64 do JSON de credenciais)

Dependências (requirements.txt):
python-telegram-bot==20.3
gspread==5.7.2
google-auth==2.23.2
pandas==2.2.2
matplotlib==3.8.2

No Railway, crie um service e defina essas env vars.

"""

import os
import base64
import json
import io
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
#  Configuração do Google Sheets
# -----------------------------

def get_gspread_client():
    key_b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_BASE64")
    if not key_b64:
        raise RuntimeError("A variável de ambiente GOOGLE_SERVICE_ACCOUNT_BASE64 não está definida.")

    data = base64.b64decode(key_b64)
    key_dict = json.loads(data.decode("utf-8"))

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_or_create_user_sheet(username: str):
    """Cria ou abre a planilha do usuário com base no @username."""
    client = get_gspread_client()
    sheet_name = f"Planilha de {username}" if username else f"Planilha (sem_username)"

    # Verifica se já existe
    for f in client.list_spreadsheet_files():
        if f.get("name") == sheet_name:
            return client.open(sheet_name).sheet1

    # Se não existir, cria
    sh = client.create(sheet_name)
    sh.share(None, perm_type='anyone', role='writer')  # torna editável (pode remover se quiser privado)
    ws = sh.sheet1
    ws.append_row(["Data", "Valor", "Categoria", "Meio"])
    return ws

# --------------
#   Utilidades
# --------------

def parse_expense_message(text):
    # Formato esperado: "valor categoria meio"
    # Ex: "15 mercado caixa"
    parts = text.split()
    if len(parts) < 3:
        return None
    try:
        valor = float(parts[0].replace(",", "."))
    except:
        return None
    categoria = parts[1]
    meio = parts[2]
    return valor, categoria, meio

# ----------------------------
#  Handlers do Telegram
# ----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Envie gastos no formato: \n"
        "`15 mercado caixa`\n"
        "Depois peça coisas como:\n"
        "- `total por categoria`\n"
        "- `gasto no caixa`\n"
        "- `grafico categorias`\n"
        "- `grafico meios`",
        parse_mode="Markdown"
    )


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parsed = parse_expense_message(text)
    if not parsed:
        return

    valor, categoria, meio = parsed
    user = update.message.from_user
    username = user.username or str(user.id)

    ws = get_or_create_user_sheet(username)
    ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), valor, categoria, meio])

    await update.message.reply_text(f"Registrado: R$ {valor} | {categoria} | {meio}")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    username = user.username or str(user.id)
    ws = get_or_create_user_sheet(username)
    data = ws.get_all_records()
    if not data:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    df = pd.DataFrame(data)
    total = df["Valor"].sum()
    by_cat = df.groupby("Categoria")["Valor"].sum().to_dict()
    cat_top = max(by_cat, key=by_cat.get)

    await update.message.reply_text(
        f"Total gasto: R$ {total:.2f}\nCategoria que mais gastou: {cat_top}"
    )


async def grafico_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    username = user.username or str(user.id)
    ws = get_or_create_user_sheet(username)
    data = ws.get_all_records()
    if not data:
        await update.message.reply_text("Nenhum gasto para gerar gráfico.")
        return

    df = pd.DataFrame(data)
    cat_sum = df.groupby("Categoria")["Valor"].sum()

    fig, ax = plt.subplots()
    ax.pie(cat_sum.values, labels=cat_sum.index, autopct="%1.1f%%")
    ax.set_title("Gasto por Categoria")

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    await update.message.reply_photo(buf)


async def grafico_meios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    username = user.username or str(user.id)
    ws = get_or_create_user_sheet(username)
    data = ws.get_all_records()
    if not data:
        await update.message.reply_text("Nenhum gasto para gerar gráfico.")
        return

    df = pd.DataFrame(data)
    meio_sum = df.groupby("Meio")["Valor"].sum()

    fig, ax = plt.subplots()
    meio_sum.plot(kind="bar", ax=ax)
    ax.set_title("Gasto por Meio de Pagamento")
    ax.set_ylabel("Valor Total (R$)")

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    await update.message.reply_photo(buf)


# ---------------------------------
#   Inicialização do Bot
# ---------------------------------

async def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("A variável de ambiente BOT_TOKEN não está definida.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("grafico_categorias", grafico_categorias))
    app.add_handler(CommandHandler("grafico_meios", grafico_meios))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
