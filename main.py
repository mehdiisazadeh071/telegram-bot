import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# --- 1. ساخت وب‌سرور صوری برای راضی کردن Render ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# --- 2. گرفتن کلیدها از متغیرهای محیطی ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# تنظیم کلاینت جمنای
client = genai.Client(api_key=GEMINI_KEY)

# --- 3. پاسخ‌گویی با هوش مصنوعی ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    # ارسال حالت در حال تایپ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # درخواست به API جمنای
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text,
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("ای بابا، گیج شدم یک لحظه! 😵")

# دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من ربات هوش مصنوعی جمنای هستم. هر سوالی داری ازم بپرس!")

# --- 4. اجرای برنامه ---
if __name__ == "__main__":
    # اجرای وب‌سرور روی یک ترد مجزا
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # اجرای ربات تلگرام
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()
