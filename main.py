import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# --- ۱. وب‌سرور صوری برای راضی نگه داشتن Render ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# --- ۲. تنظیمات توکن‌ها و کلاینت جدید جمنای ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# تعریف کلاینت با پکیج جدید google-genai
client = genai.Client(api_key=GEMINI_KEY)

# --- ۳. پردازش پیام‌های گروه ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    bot_username = context.bot.username or ""

    # تشخیص ریپلای یا صدا زدن ربات
    is_reply_to_bot = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id
    )
    is_mentioned = (f"@{bot_username}" in text) or ("ربات" in text) or ("خنگ" in text)

    # اگر در گروه است و ربات مخاطب قرار نگرفته، پاسخی نده
    if update.effective_chat.type in ["group", "supergroup"] and not (is_reply_to_bot or is_mentioned):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # درخواست به API جمنای با آخرین مدل فعال gemini-2.5-flash
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=text,
        )
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("پاسخی از هوش مصنوعی دریافت نشد.")
    except Exception as e:
        err_msg = str(e)
        print(f"Error details: {err_msg}")
        await update.message.reply_text(f"خطا در ارتباط با جمنای:\n{err_msg[:200]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من فعال هستم. روی پیام من ریپلای بزن یا اسمم رو بیار تا جوابت رو بدم.")

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Starting bot...")
    app.run_polling()
