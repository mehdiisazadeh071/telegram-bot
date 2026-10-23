import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# --- ۱. وب‌سرور صوری برای روشن نگه داشتن هاست رایگان رندر ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# --- ۲. تنظیمات کلیدها و اتصال به جمنای ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# --- ۳. تابع اصلی پردازش پیام‌ها با سیستم ضد ارور و بدون فیلتر ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    bot_username = context.bot.username or ""

    # بررسی اینکه آیا ربات ریپلای شده یا اسمش آورده شده است
    is_reply_to_bot = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id
    )
    is_mentioned = (f"@{bot_username}" in text) or ("ربات" in text) or ("خنگ" in text)

    # اگر در گروه است و ربات مخاطب قرار نگرفته، دخالت نکند
    if update.effective_chat.type in ["group", "supergroup"] and not (is_reply_to_bot or is_mentioned):
        return

    # نمایش وضعیت «در حال نوشتن...» در تلگرام برای سرعت حس شدن پاسخ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = None
        # حلقه تلاش مجدد (Retry Loop) برای رد کردن خطاهای مقطعی و ۵۰۳ سرور گوگل
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=text,
                    config=types.GenerateContentConfig(
                        # خاموش کردن کامل فیلترهای ایمنی برای جلوگیری از لالی ربات در بحث‌های تند یا جدی
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                        ],
                        # دستورالعمل سیستم برای لحن پاسخ‌دهی دوستانه، باهوش و صمیمی
                        system_instruction="تو یک دستیار هوش مصنوعی صمیمی، باهوش و همراه در گروه تلگرامی هستی. به تمام پیام‌ها (چه جدی، چه دلخوری یا شوخی) با دقت، منطق و به زبان عامیانه و صمیمی پاسخ بده و هیچ‌وقت از جواب دادن امتناع نکن."
                    )
                )
                break
            except Exception as api_err:
                if "503" in str(api_err) and attempt < 2:
                    time.sleep(2)  # دو ثانیه مکث و تلاش دوباره
                    continue
                raise api_err

        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("داداش سرور یه لحظه هنگ کرد، متنی دریافت نشد!")
            
    except Exception as e:
        err_msg = str(e)
        print(f"Error details: {err_msg}")
        await update.message.reply_text("مشکلی پیش اومد، ولی حله!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من باهوش‌تر و بدون فیلتر آماده‌ام. روی پیامم ریپلای بزن تا گپ بزنیم.")

if __name__ == "__main__":
    # استارت سرور صوری برای جلوگیری از خوابیدن رندر در پس‌زمینه
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # راه‌اندازی ربات
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is starting up...")
    app.run_polling()
