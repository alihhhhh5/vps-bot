import sqlite3
import asyncio
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from datetime import datetime, timedelta

ASK_NAME, ASK_PHONE, ASK_SERVICE, ASK_DATE = range(4)

ADMIN_CHAT_ID = 7961751174  # چت آیدی ادمین

def init_db():
    conn = sqlite3.connect("appointments.db")
    c = conn.cursor()
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def is_date_taken(date: str) -> bool:
    conn = sqlite3.connect("appointments.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM appointments WHERE date = ?", (date,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0

def get_available_dates(start_date: str, num_dates: int = 5) -> list:
    available = []
    try:
        date_obj = datetime.strptime(start_date, "%Y/%m/%d")
    except:
        return []
    while len(available) < num_dates:
        date_obj += timedelta(days=1)
        date_str = date_obj.strftime("%Y/%m/%d")
        if not is_date_taken(date_str):
            available.append(date_str)
    return available

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "سلام! به ربات نوبت‌گیری مطب خوش آمدید.\n\n"
        "ساعت کاری مطب از 6 عصر تا 8 شب می‌باشد.\n\n"
        "خدمات قابل ارائه و قیمت‌ها:\n"
        "- بوتاکس: یک میلیون تومان\n"
        "- فیلر لب: چهار میلیون و دویست هزار تومان\n"
        "- فیلر چانه، گونه و خط خنده: سه میلیون و نهصد هزار تومان\n"
        "- پی آر پی: یک میلیون و پانصد هزار تومان\n"
        "- مزو صورت و مو: یک میلیون تومان\n"
        "- برداشت خال: از پانصد هزار تا دو میلیون تومان\n"
        "- ویزیت آزاد: صد و هشتاد هزار تومان\n\n"
        "برای مشاهده نمونه کارها:\n"
        "https://t.me/+e9uBzWtEBdUwNTM8\n\n"
        "لطفاً نام و نام خانوادگی خود را وارد کنید:"
    )
    return ASK_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("شماره همراه خود را وارد کنید (مثلاً 09123456789):")
    return ASK_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    if not re.match(r"^09\d{9}$", phone):
        await update.message.reply_text("شماره وارد شده صحیح نیست. لطفاً شماره‌ای معتبر وارد کنید:")
        return ASK_PHONE
    context.user_data['phone'] = phone
    await update.message.reply_text("خدمت مورد نظر خود را وارد کنید:")
    return ASK_SERVICE

async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['service'] = update.message.text.strip()
    await update.message.reply_text("تاریخ و ساعت مورد نظر خود را وارد کنید (مثلاً 1403/02/15 ساعت 18:30):")
    return ASK_DATE

def extract_date_time(text):
    date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text)
    if not date_match:
        return None, None

    date = date_match.group(1)
    text_after_date = text[date_match.end():]
    time_match = re.search(r"(?:ساعت)?\s*(\d{1,2}[:٫.,]?\d{0,2})", text_after_date)

    if time_match:
        raw_time = time_match.group(1).replace("٫", ":").replace(".", ":").replace(",", ":")
        parts = raw_time.split(":")
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            time = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        elif len(parts) == 1 and parts[0].isdigit():
            time = f"{int(parts[0]):02d}:00"
        else:
            time = "18:00"
    else:
        time = "18:00"

    return date, time

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text
    date_str, time_str = extract_date_time(raw)

    if not date_str:
        await update.message.reply_text("فرمت تاریخ صحیح نیست. لطفاً به‌صورت 1403/02/15 ساعت 18:30 وارد کنید.")
        return ASK_DATE

    if is_date_taken(date_str):
        alternatives = get_available_dates(date_str)
        if alternatives:
            await update.message.reply_text("تاریخ وارد شده قبلاً رزرو شده است.\nتاریخ‌های پیشنهادی:\n" + "\n".join(alternatives))
        else:
            await update.message.reply_text("متأسفانه تاریخ وارد شده قبلاً رزرو شده است و پیشنهادی فعلاً نداریم.")
        return ASK_DATE

    name = context.user_data['name']
    phone = context.user_data['phone']
    service = context.user_data['service']

    conn = sqlite3.connect("appointments.db")
    c = conn.cursor()
    c.execute("INSERT INTO appointments (name, phone, service, date, time) VALUES (?, ?, ?, ?, ?)",
              (name, phone, service, date_str, time_str))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"نوبت شما با موفقیت ثبت شد:\n"
        f"نام: {name}\n"
        f"شماره: {phone}\n"
        f"خدمت: {service}\n"
        f"تاریخ: {date_str}\n"
        f"ساعت: {time_str}\n\n"
        "برای مشاهده نمونه کارها:\n"
        "https://t.me/+e9uBzWtEBdUwNTM8\n"
        "ممنون از ثبت نوبت شما!"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"نوبت جدید:\n"
             f"نام: {name}\n"
             f"شماره: {phone}\n"
             f"خدمت: {service}\n"
             f"تاریخ: {date_str} ساعت {time_str}"
    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("گفتگو لغو شد.")
    return ConversationHandler.END

async def main():
    init_db()
    TOKEN = '7578148103:AAGyfRcWCW4djl7i9EInKR2srBNbSWgDPQo'

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ASK_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)

    print("ربات در حال اجراست...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
