import os
import pandas as pd
import gspread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

# Se a planilha estiver vazia, cria cabeçalho
if worksheet.row_count == 1 and worksheet.col_count == 1 and worksheet.acell("A1").value is None:
    worksheet.append_row(["user_id", "valor", "categoria", "metodo"])

def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text(
        "Me envie seus gastos no formato:\n\n"
        "valor; categoria; metodo\n\n"
        "Exemplo:\n15; mercado; cartão caixa\n\n"
        "Depois pergunte:\n- quanto gastei no cartão caixa?\n- qual categoria eu mais gastei?"
    )

def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    texto = update.message.text.lower()

    # Espera formato "valor; categoria; metodo"
    if ";" not in texto:
        return

    try:
        valor, categoria, metodo = [x.strip() for x in texto.split(";")]
        valor = float(valor.replace(",", "."))
        worksheet.append_row([user_id, valor, categoria, metodo])
        update.message.reply_text("Gasto registrado com sucesso.")
    except:
        update.message.reply_text("Formato inválido. Use: valor; categoria; metodo")

def quanto_gastei(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    texto = update.message.text.lower()

    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["user_id"] == user_id]

    palavras = texto.split(" ")
    metodo = palavras[-1]  # ex: "cartão caixa"

    gastos = df[df["metodo"].str.contains(metodo, case=False, na=False)]
    total = gastos["valor"].sum()

    update.message.reply_text(f"Você gastou R$ {total:.2f} usando {metodo}.")

def categoria_mais_gasta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["user_id"] == user_id]

    if df.empty:
        update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    cat = df.groupby("categoria")["valor"].sum().idxmax()
    update.message.reply_text(f"A categoria em que você mais gastou foi: {cat}.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("quanto gastei"), quanto_gastei))
    app.add_handler(MessageHandler(filters.Regex("categoria"), categoria_mais_gasta))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_gasto))

    app.run_polling()

if __name__ == "__main__":
    main()
