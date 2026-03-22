"""
main_bot.py — The MAIN BOT.

Flow:
1. Student sends /start
2. Bot tells them to join the General Channel
3. Bot checks they joined the channel
4. Bot asks for their School (faculty)
5. Bot asks for their Department
6. Bot sends them the link to their Department Bot
7. Done!

Run this file: python main_bot.py
"""

import os, sys, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

from shared.schools import SCHOOLS, get_dept_name, get_dept_bot
from shared.db import load, save, now

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Config (from .env) ────────────────────────────────────────
BOT_TOKEN      = os.getenv("MAIN_BOT_TOKEN", "")
CHANNEL_ID     = os.getenv("GENERAL_CHANNEL_ID", "")   # e.g. @mychannel or -100123456789
CHANNEL_LINK   = os.getenv("GENERAL_CHANNEL_LINK", "https://t.me/yourchannel")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
SCHOOL_NAME    = os.getenv("SCHOOL_NAME", "Federal Polytechnic")
DATA_FILE      = "main_data.json"

DEFAULT_DATA = {
    "students":  {},   # {str(uid): {name, school, dept, joined, username}}
    "banned":    [],
    "admins":    [],
    "stats":     {"total": 0, "today": 0},
}

# ── Conversation states ───────────────────────────────────────
CHECK_CHANNEL, ENTER_NAME, PICK_SCHOOL, PICK_DEPT = range(4)


# ── Helpers ───────────────────────────────────────────────────
def load_data():   return load(DATA_FILE, DEFAULT_DATA)
def save_data(d):  save(DATA_FILE, d)

def is_admin(uid: int, d: dict) -> bool:
    return uid == SUPER_ADMIN_ID or uid in d["admins"]


async def check_channel_membership(bot, uid: int) -> bool:
    """Check if user has joined the general channel."""
    if not CHANNEL_ID:
        return True   # skip check if no channel configured
    try:
        member = await bot.get_chat_member(CHANNEL_ID, uid)
        return member.status not in (ChatMember.BANNED, ChatMember.LEFT)
    except BadRequest:
        return False   # channel not found or bot not admin of channel


# ── Keyboards ─────────────────────────────────────────────────
def channel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join General Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined — Continue", callback_data="check_joined")],
    ])


def schools_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key, info in SCHOOLS.items():
        rows.append([InlineKeyboardButton(
            f"{info['emoji']} {info['short']} — {info['name']}",
            callback_data=f"school:{key}"
        )])
    return InlineKeyboardMarkup(rows)


def depts_keyboard(school_key: str) -> InlineKeyboardMarkup:
    school = SCHOOLS[school_key]
    rows   = []
    for dk, dname in school["departments"].items():
        rows.append([InlineKeyboardButton(dname, callback_data=f"dept:{school_key}:{dk}")])
    rows.append([InlineKeyboardButton("← Back to Schools", callback_data="back:schools")])
    return InlineKeyboardMarkup(rows)


def confirm_keyboard(school_key: str, dept_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, that's correct", callback_data=f"confirm:{school_key}:{dept_key}")],
        [InlineKeyboardButton("🔄 Change Department",   callback_data=f"school:{school_key}")],
        [InlineKeyboardButton("🔄 Change School",       callback_data="back:schools")],
    ])


# ── /start ─────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid  = update.effective_user.id
    d    = load_data()

    if uid in d["banned"]:
        await update.message.reply_text("🚫 You are banned from this bot.")
        return ConversationHandler.END

    # Already registered — show their info
    if str(uid) in d["students"]:
        s       = d["students"][str(uid)]
        dept    = get_dept_name(s["school"], s["dept"])
        bot_url = get_dept_bot(s["dept"])
        btn     = [[InlineKeyboardButton("🤖 Go to My Department Bot", url=bot_url)]] if bot_url else []
        btn.append([InlineKeyboardButton("🔄 Change Department", callback_data="back:schools")])
        await update.message.reply_text(
            f"👋 Welcome back, <b>{s['name']}</b>!\n\n"
            f"🏫 School: <b>{SCHOOLS[s['school']]['short']}</b>\n"
            f"📚 Department: <b>{dept}</b>\n\n"
            f"{'Tap below to open your department bot 👇' if bot_url else '⏳ Your department bot is coming soon!'}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btn),
        )
        return ConversationHandler.END

    # New user — check channel first
    await update.message.reply_text(
        f"👋 Welcome to <b>{SCHOOL_NAME}</b> Student Bot!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Step 1 of 3 — Join Our Channel</b>\n\n"
        f"Before you can access your department bot, you must join our general student channel.\n\n"
        f"📢 This channel contains:\n"
        f"• School-wide announcements\n"
        f"• Important notices\n"
        f"• General information\n\n"
        f"👇 Join below, then tap <b>I've Joined</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=channel_keyboard(),
    )
    return CHECK_CHANNEL


# ── Channel check ──────────────────────────────────────────────
async def check_joined(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id

    joined = await check_channel_membership(ctx.bot, uid)

    if not joined:
        await query.edit_message_text(
            "❌ <b>You haven't joined the channel yet!</b>\n\n"
            "Please join first, then tap the button again.\n\n"
            "We check this automatically — make sure you tapped <b>Join</b> in the channel.",
            parse_mode=ParseMode.HTML,
            reply_markup=channel_keyboard(),
        )
        return CHECK_CHANNEL

    # Joined! Ask for name
    await query.edit_message_text(
        "✅ <b>Channel membership confirmed!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Step 2 of 3 — Your Name</b>\n\n"
        "Please type your <b>full name</b> below:",
        parse_mode=ParseMode.HTML,
    )
    return ENTER_NAME


# ── Name entry ─────────────────────────────────────────────────
async def enter_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("⚠️ Please enter your full name (at least 2 characters).")
        return ENTER_NAME

    ctx.user_data["name"] = name

    await update.message.reply_text(
        f"Great, <b>{name}</b>! 👍\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Step 3 of 3 — Your School & Department</b>\n\n"
        f"Select your <b>School</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=schools_keyboard(),
    )
    return PICK_SCHOOL


# ── School selection ───────────────────────────────────────────
async def pick_school(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back:schools":
        await query.edit_message_text(
            "Select your <b>School</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=schools_keyboard(),
        )
        return PICK_SCHOOL

    school_key = query.data.split(":")[1]
    ctx.user_data["school"] = school_key
    school = SCHOOLS[school_key]

    await query.edit_message_text(
        f"{school['emoji']} <b>{school['name']}</b>\n\n"
        f"Now select your <b>Department</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=depts_keyboard(school_key),
    )
    return PICK_DEPT


# ── Department selection ───────────────────────────────────────
async def pick_dept(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back:schools":
        await query.edit_message_text(
            "Select your <b>School</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=schools_keyboard(),
        )
        return PICK_SCHOOL

    _, school_key, dept_key = query.data.split(":")
    ctx.user_data["dept"]   = dept_key
    ctx.user_data["school"] = school_key

    school    = SCHOOLS[school_key]
    dept_name = get_dept_name(school_key, dept_key)

    await query.edit_message_text(
        f"Please confirm your details:\n\n"
        f"👤 Name:       <b>{ctx.user_data.get('name', '?')}</b>\n"
        f"🏫 School:     <b>{school['emoji']} {school['name']}</b>\n"
        f"📚 Department: <b>{dept_name}</b>\n\n"
        f"Is this correct?",
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_keyboard(school_key, dept_key),
    )
    return PICK_DEPT


# ── Confirmation & bot link delivery ──────────────────────────
async def confirm_registration(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("school:"):
        # User wants to change school
        school_key = query.data.split(":")[1]
        ctx.user_data["school"] = school_key
        school = SCHOOLS[school_key]
        await query.edit_message_text(
            f"{school['emoji']} <b>{school['name']}</b>\n\nSelect your <b>Department</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=depts_keyboard(school_key),
        )
        return PICK_DEPT

    # Confirmed!
    _, school_key, dept_key = query.data.split(":")
    uid      = query.from_user.id
    name     = ctx.user_data.get("name", query.from_user.full_name)
    username = query.from_user.username or ""
    d        = load_data()

    # Save student
    d["students"][str(uid)] = {
        "name":     name,
        "username": username,
        "school":   school_key,
        "dept":     dept_key,
        "joined":   now(),
    }
    d["stats"]["total"] = d["stats"].get("total", 0) + 1
    save_data(d)

    school    = SCHOOLS[school_key]
    dept_name = get_dept_name(school_key, dept_key)
    bot_url   = get_dept_bot(dept_key)

    # Notify super admin
    if SUPER_ADMIN_ID:
        try:
            await ctx.bot.send_message(
                SUPER_ADMIN_ID,
                f"🆕 <b>New Student Registered!</b>\n\n"
                f"👤 {name} (@{username})\n"
                f"🏫 {school['short']}\n"
                f"📚 {dept_name}\n"
                f"🆔 <code>{uid}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    if bot_url:
        msg = (
            f"🎉 <b>Registration Complete!</b>\n\n"
            f"👤 Name:       {name}\n"
            f"🏫 School:     {school['emoji']} {school['short']}\n"
            f"📚 Department: {dept_name}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your department bot is ready! 👇\n\n"
            f"Tap the button below to open your <b>{dept_name}</b> Bot.\n\n"
            f"Your department bot can:\n"
            f"📂 Share lecture notes & past questions\n"
            f"🤖 Answer your academic questions with AI\n"
            f"📣 Send department announcements\n"
            f"📝 Assignment reminders"
        )
        buttons = [[InlineKeyboardButton(
            f"🤖 Open {dept_name} Bot →", url=bot_url
        )]]
    else:
        msg = (
            f"🎉 <b>Registration Complete!</b>\n\n"
            f"👤 Name:       {name}\n"
            f"🏫 School:     {school['emoji']} {school['short']}\n"
            f"📚 Department: {dept_name}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ <b>Your department bot is being set up!</b>\n\n"
            f"We will notify you as soon as the <b>{dept_name}</b> bot is live.\n\n"
            f"In the meantime, stay updated in the general channel!"
        )
        buttons = [[InlineKeyboardButton("📢 General Channel", url=CHANNEL_LINK)]]

    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


# ── /mystatus — check your registration ───────────────────────
async def my_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    d   = load_data()
    s   = d["students"].get(str(uid))

    if not s:
        await update.message.reply_text(
            "You are not registered yet. Send /start to begin! 👋"
        )
        return

    school    = SCHOOLS.get(s["school"], {})
    dept_name = get_dept_name(s["school"], s["dept"])
    bot_url   = get_dept_bot(s["dept"])

    btns = []
    if bot_url:
        btns.append([InlineKeyboardButton("🤖 Open My Department Bot", url=bot_url)])
    btns.append([InlineKeyboardButton("🔄 Change My Department", callback_data="back:schools")])

    await update.message.reply_text(
        f"👤 <b>Your Registration</b>\n\n"
        f"Name:       {s['name']}\n"
        f"School:     {school.get('emoji','')} {school.get('name','?')}\n"
        f"Department: {dept_name}\n"
        f"Registered: {s.get('joined','?')}\n\n"
        f"{'✅ Your department bot is live!' if bot_url else '⏳ Department bot coming soon!'}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btns) if btns else None,
    )


# ── /help ──────────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ <b>{SCHOOL_NAME} — Main Bot Help</b>\n\n"
        f"This bot registers you and connects you to your department bot.\n\n"
        f"<b>Commands:</b>\n"
        f"/start — Register or view your status\n"
        f"/mystatus — View your registration details\n"
        f"/change — Change your school/department\n"
        f"/help — Show this message\n\n"
        f"<b>How it works:</b>\n"
        f"1️⃣ Join the general channel\n"
        f"2️⃣ Enter your name\n"
        f"3️⃣ Select your school and department\n"
        f"4️⃣ Get your department bot link\n\n"
        f"❓ Need help? Contact your school admin.",
        parse_mode=ParseMode.HTML,
    )


# ── /change — update department ────────────────────────────────
async def change_dept(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    d   = load_data()
    if str(uid) not in d["students"]:
        await update.message.reply_text("Please /start first to register.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔄 <b>Change Department</b>\n\nSelect your new School:",
        parse_mode=ParseMode.HTML,
        reply_markup=schools_keyboard(),
    )
    return PICK_SCHOOL


# ── /admin — quick admin stats ─────────────────────────────────
async def admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d):
        return

    total   = len(d["students"])
    banned  = len(d["banned"])

    # Count per school
    school_counts = {}
    for s in d["students"].values():
        sk = s.get("school", "?")
        school_counts[sk] = school_counts.get(sk, 0) + 1

    school_lines = "\n".join(
        f"  {SCHOOLS[k]['emoji']} {SCHOOLS[k]['short']}: {v}"
        for k, v in sorted(school_counts.items(), key=lambda x: -x[1])
        if k in SCHOOLS
    )

    await update.message.reply_text(
        f"🛠️ <b>Admin Panel</b>\n\n"
        f"👥 Total Students: <b>{total}</b>\n"
        f"🚫 Banned: <b>{banned}</b>\n\n"
        f"<b>By School:</b>\n{school_lines or '  None yet'}\n\n"
        f"Commands:\n"
        f"/ban USER_ID — ban a user\n"
        f"/unban USER_ID — unban a user\n"
        f"/broadcast — message all students",
        parse_mode=ParseMode.HTML,
    )


# ── /ban and /unban ────────────────────────────────────────────
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d): return
    try:
        target = int(ctx.args[0])
        if target not in d["banned"]: d["banned"].append(target)
        save_data(d)
        s = d["students"].get(str(target), {})
        await update.message.reply_text(f"🚫 {s.get('name', target)} banned.")
        try: await ctx.bot.send_message(target, "🚫 You have been banned from this bot.")
        except: pass
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban USER_ID")


async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d): return
    try:
        target = int(ctx.args[0])
        if target in d["banned"]: d["banned"].remove(target)
        save_data(d)
        await update.message.reply_text(f"✅ User {target} unbanned.")
        try: await ctx.bot.send_message(target, "✅ You have been unbanned. Send /start to continue.")
        except: pass
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban USER_ID")


# ── /broadcast ────────────────────────────────────────────────
AWAITING_BROADCAST = 99

async def broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d):
        return ConversationHandler.END
    await update.message.reply_text(
        "📡 Type the message to send to ALL registered students.\n/cancel to abort."
    )
    return AWAITING_BROADCAST


async def broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid  = update.effective_user.id
    text = update.message.text.strip()
    d    = load_data()

    sent = 0
    for uid_str in d["students"]:
        tid = int(uid_str)
        if tid in d["banned"]: continue
        try:
            await ctx.bot.send_message(
                tid,
                f"📡 <b>Announcement from {SCHOOL_NAME}</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except: pass

    await update.message.reply_text(f"✅ Sent to {sent} students.")
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ── MAIN ──────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        log.error("❌ MAIN_BOT_TOKEN not set in .env!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Registration conversation
    reg_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start",  start),
            CommandHandler("change", change_dept),
        ],
        states={
            CHECK_CHANNEL: [CallbackQueryHandler(check_joined,           pattern="^check_joined$")],
            ENTER_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            PICK_SCHOOL:   [
                CallbackQueryHandler(pick_school,          pattern=r"^school:"),
                CallbackQueryHandler(pick_school,          pattern=r"^back:schools"),
            ],
            PICK_DEPT:     [
                CallbackQueryHandler(pick_dept,            pattern=r"^dept:"),
                CallbackQueryHandler(pick_school,          pattern=r"^back:schools"),
                CallbackQueryHandler(confirm_registration, pattern=r"^confirm:"),
                CallbackQueryHandler(confirm_registration, pattern=r"^school:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    # Broadcast conversation
    bc_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={AWAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(reg_conv)
    app.add_handler(bc_conv)
    app.add_handler(CommandHandler("mystatus", my_status))
    app.add_handler(CommandHandler("help",     help_cmd))
    app.add_handler(CommandHandler("admin",    admin_cmd))
    app.add_handler(CommandHandler("ban",      ban_cmd))
    app.add_handler(CommandHandler("unban",    unban_cmd))

    log.info(f"🤖 {SCHOOL_NAME} MAIN BOT running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
