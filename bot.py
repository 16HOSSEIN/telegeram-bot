import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# -------------------------------
# تنظیمات
# -------------------------------

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_USERNAME = "Spo_Vpn"
ADMIN_ID = 632939373
CARD_NUMBER = "6219861467997978"

# -------------------------------
# دیتابیس
# -------------------------------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    total_orders INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan_title TEXT,
    date TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan TEXT,
    code TEXT
)
""")

conn.commit()

# -------------------------------
# لاگ
# -------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -------------------------------
# چک عضویت کانال (نسخه نهایی)
# -------------------------------

async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# -------------------------------
# منوی اصلی
# -------------------------------

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("📞 پشتیبانی", url="https://t.me/hoss41n")]
    ]
    return InlineKeyboardMarkup(keyboard)

# -------------------------------
# /start
# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_member(update, context):
        await update.message.reply_text(
            "🚀 برای استفاده از ربات باید عضو کانال شوید:\n"
            f"https://t.me/{CHANNEL_USERNAME}"
        )
        return

    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                   (user.id, user.username, user.first_name))
    conn.commit()

    await update.message.reply_text("سلام! 👋\nبه ربات فروش خوش آمدید.", reply_markup=main_menu())

# -------------------------------
# خرید سرویس
# -------------------------------

async def buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔹 پلن ۱۰ گیگ - 50T", callback_data="plan_10")],
        [InlineKeyboardButton("🔹 پلن ۲۰ گیگ - 90T", callback_data="plan_20")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]

    await query.edit_message_text("یکی از پلن‌ها را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------------------
# حساب کاربری
# -------------------------------

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    cursor.execute("SELECT total_orders FROM users WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT plan_title, date, status FROM orders WHERE user_id=?", (user_id,))
    orders = cursor.fetchall()

    text = f"👤 *حساب کاربری شما*\n\n"
    text += f"آیدی عددی: `{user_id}`\n"
    text += f"نام کاربری: @{query.from_user.username}\n"
    text += f"تعداد خریدها: {total}\n\n"

    if orders:
        text += "🛒 *سرویس‌های خریداری‌شده:*\n"
        for o in orders:
            text += f"- {o[0]} | {o[1]} | وضعیت: {o[2]}\n"
    else:
        text += "هنوز خریدی انجام نداده‌اید."

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

# -------------------------------
# مدیریت کال‌بک‌ها
# -------------------------------

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "buy":
        await buy_menu(update, context)

    elif data == "account":
        await account(update, context)

    elif data == "back":
        await query.edit_message_text("منوی اصلی:", reply_markup=main_menu())

    elif data.startswith("approve_"):
        order_id = int(data.split("_")[1])

        cursor.execute("SELECT plan_title, user_id FROM orders WHERE id=?", (order_id,))
        plan, user_id = cursor.fetchone()

        cursor.execute("SELECT code FROM codes WHERE plan=? LIMIT 1", (plan,))
        result = cursor.fetchone()

        if not result:
            await query.edit_message_text("❌ کد موجود نیست.")
            return

        code = result[0]

        cursor.execute("DELETE FROM codes WHERE code=?", (code,))
        cursor.execute("UPDATE orders SET status='تأیید شد' WHERE id=?", (order_id,))
        cursor.execute("UPDATE users SET total_orders = total_orders + 1 WHERE user_id=?", (user_id,))
        conn.commit()

        await context.bot.send_message(user_id, f"✅ سفارش شما تأیید شد.\nکد سرویس:\n`{code}`", parse_mode="Markdown")
        await query.edit_message_text("✔ رسید تأیید شد و کد ارسال شد.")

    elif data.startswith("reject_"):
        order_id = int(data.split("_")[1])

        cursor.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
        user_id = cursor.fetchone()[0]

        cursor.execute("UPDATE orders SET status='رد شد' WHERE id=?", (order_id,))
        conn.commit()

        await context.bot.send_message(user_id, "❌ رسید شما رد شد. لطفاً دوباره ارسال کنید.")
        await query.edit_message_text("✖ رسید رد شد.")

    elif data == "plan_10":
        await query.edit_message_text(
            f"برای خرید پلن ۱۰ گیگ، مبلغ را به شماره کارت زیر واریز کنید:\n\n"
            f"`{CARD_NUMBER}`\n\n"
            "سپس رسید پرداخت را ارسال کنید.",
            parse_mode="Markdown"
        )

    elif data == "plan_20":
        await query.edit_message_text(
            f"برای خرید پلن ۲۰ گیگ، مبلغ را به شماره کارت زیر واریز کنید:\n\n"
            f"`{CARD_NUMBER}`\n\n"
            "سپس رسید پرداخت را ارسال کنید.",
            parse_mode="Markdown"
        )

# -------------------------------
# دریافت رسید
# -------------------------------

async def receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("INSERT INTO orders (user_id, plan_title, date, status) VALUES (?, ?, DATE('now'), 'در انتظار تأیید')",
                   (user.id, "پلن خریداری‌شده"))
    conn.commit()

    order_id = cursor.lastrowid

    await update.message.reply_text("📨 رسید دریافت شد. منتظر تأیید ادمین باشید.")

    keyboard = [
        [InlineKeyboardButton("✔ تأیید", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton("✖ رد", callback_data=f"reject_{order_id}")]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"رسید جدید از @{user.username}\n\nOrder ID: {order_id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# اجرای ربات
# -------------------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, receipt))

    print("ربات اجرا شد...")
    app.run_polling()

if __name__ == "__main__":
    main()