import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- ۱. وب‌سرور صوری برای پورت رندر ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# --- ۲. تنظیمات توکن و جمنای ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- ۳. پردازش پیام‌های گروه ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    bot_username = context.bot.username

    # بررسی اینکه آیا به ربات ریپلای شده یا منشن شده
    is_reply_to_bot = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id
    )
    is_mentioned = f"@{bot_username}" in text or "ربات" in text or "خنگ" in text

    # اگر گروه است و به ربات اشاره نشده، بی‌خیال شو
    if update.effective_chat.type in ["group", "supergroup"] and not (is_reply_to_bot or is_mentioned):
        return

    # ارسال حالت typing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # دریافت پاسخ از جمنای
        response = model.generate_content(text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        await update.message.reply_text("ارتباط با هوش مصنوعی قطع شد، دوباره امتحان کن!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من ربات هوش مصنوعی جمنای هستم. من رو توی گروه منشن کن یا رو پیامم ریپلای بزن تا جوابت رو بدم!")

if __name__ == "__main__":
    # اجرای وب سرور در پس‌زمینه
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # اجرای ربات
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot starting...")
    app.run_polling()
