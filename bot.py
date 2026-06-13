import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# -----------------------------
# تنظیمات اصلی
# -----------------------------

ADMIN_ID = 632939373
CARD_NUMBER = "6219861467997978 - جبرالدینی"

PLANS = {
    "plan_10": {"title": "کد دیجیتال پلن ۱", "price": "100,000", "id": 1},
    "plan_20": {"title": "کد دیجیتال پلن ۲", "price": "180,000", "id": 2},
}

# اینجا کدهای واقعی هر پلن رو می‌ذاری
CODES = {
    1: [
        # "CODE-PLAN1-1",
        # "CODE-PLAN1-2",
    ],
    2: [
        # "CODE-PLAN2-1",
    ],
}

USER_PENDING = {}
DB_NAME = "users.db"

# -----------------------------
# دیتابیس
# -----------------------------

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            total_orders INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_title TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_user_if_not_exists(user):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
    exists = c.fetchone()

    if not exists:
        c.execute(
            "INSERT INTO users (user_id, username, first_name, total_orders) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "", user.first_name or "", 0)
        )

    conn.commit()
    conn.close()


def add_order(user_id, plan_title):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute(
        "INSERT INTO orders (user_id, plan_title, date) VALUES (?, ?, ?)",
        (user_id, plan_title, date)
    )

    c.execute(
        "UPDATE users SET total_orders = total_orders + 1 WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def get_user_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT username, first_name, total_orders FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()

    c.execute("SELECT plan_title, date FROM orders WHERE user_id = ?", (user_id,))
    orders = c.fetchall()

    conn.close()
    return user, orders

# -----------------------------
# شروع ربات
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    add_user_if_not_exists(user)

    try:
        member = await context.bot.get_chat_member(chat_id="@spo_vpn", user_id=user.id)
        if member.status in ["left", "kicked"]:
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/spo_vpn")],
                [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
            ]
            await update.message.reply_text(
                "برای استفاده از ربات باید ابتدا در کانال عضو شوی:\n\n@spo_vpn",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    except:
        await update.message.reply_text("خطا در بررسی عضویت.")
        return

    keyboard = [
        [InlineKeyboardButton(plan["title"], callback_data=key)]
        for key, plan in PLANS.items()
    ]
    keyboard.append([InlineKeyboardButton("👤 حساب کاربری", callback_data="account")])
    keyboard.append([InlineKeyboardButton("📞 پشتیبانی", url="https://t.me/hoss41n")])

    await update.message.reply_text(
        f"سلام {user.first_name} عزیز 🌟\nیکی از پلن‌ها را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -----------------------------
# بررسی دوباره عضویت
# -----------------------------

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id="@spo_vpn", user_id=user_id)
        if member.status in ["left", "kicked"]:
            await query.answer("هنوز عضو کانال نشدی ❗", show_alert=True)
            return
    except:
        await query.answer("خطا در بررسی عضویت", show_alert=True)
        return

    await query.answer("عضویت تأیید شد ✔")
    fake_update = Update(update.update_id, message=None)
    fake_update.message = query.message
    fake_update.message.from_user = query.from_user
    await start(fake_update, context)

# -----------------------------
# حساب کاربری
# -----------------------------

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    user, orders = get_user_info(user_id)
    if not user:
        await query.edit_message_text("اطلاعاتی برای حساب کاربری شما ثبت نشده.")
        return

    username, first_name, total_orders = user

    text = (
        "👤 *حساب کاربری*\n\n"
        f"🆔 آیدی عددی: `{user_id}`\n"
        f"👥 نام کاربری: @{username or '---'}\n"
        f"🧾 نام: {first_name or '---'}\n"
        f"🛒 تعداد خریدها: {total_orders}\n\n"
        "📦 *لیست سرویس‌های خریداری‌شده:*\n"
    )

    if not orders:
        text += "هنوز خریدی انجام نداده‌ای."
    else:
        for plan_title, date in orders:
            text += f"- {plan_title} | {date}\n"

    await query.edit_message_text(text, parse_mode="Markdown")

# -----------------------------
# انتخاب پلن
# -----------------------------

async def choose_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    plan_key = query.data
    plan = PLANS[plan_key]
    plan_id = plan["id"]

    if not CODES.get(plan_id) or len(CODES[plan_id]) == 0:
        await query.edit_message_text("❌ کانفیگی در این پلن وجود ندارد.")
        return

    USER_PENDING[query.from_user.id] = plan_id

    text = (
        f"پلن انتخابی: {plan['title']}\n"
        f"مبلغ: {plan['price']} تومان\n\n"
        f"لطفاً مبلغ را به این کارت واریز کن:\n{CARD_NUMBER}\n\n"
        "بعد از واریز، رسید یا عکس پرداخت را همینجا ارسال کن."
    )

    keyboard = [[InlineKeyboardButton("📋 کپی شماره کارت", callback_data="copy_card")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# -----------------------------
# کپی شماره کارت
# -----------------------------

async def copy_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("شماره کارت کپی شد ✔️", show_alert=True)
    await query.message.reply_text(CARD_NUMBER)

# -----------------------------
# دریافت رسید
# -----------------------------

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id not in USER_PENDING:
        await update.message.reply_text("اول باید یک پلن انتخاب کنی. /start")
        return

    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id,
    )

    await update.message.reply_text("رسید دریافت شد ✔️\nلطفاً منتظر تأیید ادمین بمانید.")

    keyboard = [
        [
            InlineKeyboardButton("✅ تأیید", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject:{user_id}")
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"کاربر {user_id} رسید ارسال کرده.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -----------------------------
# دکمه‌های ادمین (تأیید/رد)
# -----------------------------

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("شما ادمین نیستید.")
        return

    action, user_id_str = query.data.split(":")
    user_id = int(user_id_str)

    if action == "approve":
        await send_code_to_user(context, user_id)
        await query.edit_message_text(f"پرداخت کاربر {user_id} تأیید شد.")
    else:
        await context.bot.send_message(chat_id=user_id, text="پرداخت تأیید نشد.")
        await query.edit_message_text(f"پرداخت کاربر {user_id} رد شد.")

# -----------------------------
# ارسال کد + ثبت در دیتابیس
# -----------------------------

async def send_code_to_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    plan_id = USER_PENDING.get(user_id)
    if not plan_id:
        return

    codes_list = CODES.get(plan_id, [])
    if not codes_list:
        await context.bot.send_message(chat_id=user_id, text="فعلاً کدی موجود نیست.")
        return

    code = codes_list.pop(0)

    plan_title = None
    for key, p in PLANS.items():
        if p["id"] == plan_id:
            plan_title = p["title"]
            break

    await context.bot.send_message(chat_id=user_id, text=f"کد دیجیتال شما:\n{code}")
    add_order(user_id, plan_title)
    USER_PENDING.pop(user_id, None)

# -----------------------------
# اجرای ربات
# -----------------------------

async def main():
    init_db()

    app = ApplicationBuilder().token("8260240341:AAF9MeIWmBtOX3RB5pnW1x-d9QjdPOxgbZ0").build()  # اینجا توکن خودت رو بذار

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(account, pattern="account"))
    app.add_handler(CallbackQueryHandler(copy_card, pattern="copy_card"))
    app.add_handler(CallbackQueryHandler(choose_plan, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(approve|reject):"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_payment_proof))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())