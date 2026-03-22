"""
dept_bot.py — ONE script that runs as ANY department bot.

The same code runs for every department bot. The difference is just
the environment variables you set — the BOT_TOKEN and DEPT_KEY
tell the bot which department it is.

Run it like this:
  DEPT_KEY=computer_sci python dept_bot.py
  DEPT_KEY=electrical    python dept_bot.py
  DEPT_KEY=biochemistry  python dept_bot.py

Or set DEPT_KEY in the .env file for each deployment.
"""

import os, sys, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters,
)
from telegram.constants import ParseMode

from shared.schools import SCHOOLS, get_dept_name, get_school
from shared.db import load, save, now
from dept_ai import ask_gemini, clear_history

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("DEPT_BOT_TOKEN", "")
DEPT_KEY       = os.getenv("DEPT_KEY", "")            # e.g. "computer_sci"
SCHOOL_KEY     = os.getenv("SCHOOL_KEY", "")          # e.g. "sict"
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
SCHOOL_FULL    = os.getenv("SCHOOL_NAME", "Federal Polytechnic")
MAIN_BOT_LINK  = os.getenv("MAIN_BOT_LINK", "https://t.me/your_main_bot")

DATA_FILE      = f"dept_data_{DEPT_KEY}.json"

DEFAULT_DATA = {
    "members":       {},   # {str(uid): {name, username, joined}}
    "admins":        [],
    "banned":        [],
    "files":         [],   # [{file_id, file_type, ftype, caption, sender, date}]
    "announcements": [],   # [{text, sender, date}]
    "pinned":        "",   # pinned message text
    "pending":       [],   # users waiting for approval
    "approved":      [],   # approved posters
    "stats":         {"questions": 0, "files": 0, "announcements": 0},
}

# Conversation states
(AI_CHAT, SHARE_TYPE, SHARE_FILE, SHARE_CAP, ANN_TEXT, BROADCAST_MSG) = range(6)

FILE_TYPES = {
    "notes":      "📖 Lecture Notes",
    "past_q":     "📝 Past Questions",
    "assignment":  "📄 Assignments",
    "syllabus":   "📋 Syllabus / Course Outline",
    "timetable":  "📅 Timetable",
    "other":      "📦 Other Materials",
}


# ── Helpers ───────────────────────────────────────────────────
def load_data():  return load(DATA_FILE, DEFAULT_DATA)
def save_data(d): save(DATA_FILE, d)

def dept_name():
    return get_dept_name(SCHOOL_KEY, DEPT_KEY)

def school_info():
    return SCHOOLS.get(SCHOOL_KEY, {})

def is_admin(uid: int, d: dict) -> bool:
    return uid == SUPER_ADMIN_ID or uid in d["admins"]

def is_approved(uid: int, d: dict) -> bool:
    return is_admin(uid, d) or uid in d["approved"]

def is_banned(uid: int, d: dict) -> bool:
    return uid in d["banned"]

def get_file(msg):
    """Extract file_id and file_type from a message."""
    if msg.document: return msg.document.file_id, "document"
    if msg.photo:    return msg.photo[-1].file_id, "photo"
    if msg.video:    return msg.video.file_id,     "video"
    if msg.audio:    return msg.audio.file_id,     "audio"
    return None, None

async def send_file(bot, chat_id: int, file_id: str, ftype: str, caption: str):
    kw = dict(chat_id=chat_id, caption=caption, parse_mode=ParseMode.HTML)
    if ftype   == "photo":    await bot.send_photo(photo=file_id, **kw)
    elif ftype == "video":    await bot.send_video(video=file_id, **kw)
    elif ftype == "audio":    await bot.send_audio(audio=file_id, **kw)
    else:                     await bot.send_document(document=file_id, **kw)


# ── Keyboards ─────────────────────────────────────────────────
def main_menu(approved=False, admin=False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📂 Browse Materials", callback_data="browse"),
         InlineKeyboardButton("🤖 Ask AI",           callback_data="ai_start")],
        [InlineKeyboardButton("📣 Announcements",    callback_data="announcements"),
         InlineKeyboardButton("📌 Pinned Info",      callback_data="pinned")],
        [InlineKeyboardButton("👤 My Profile",       callback_data="profile"),
         InlineKeyboardButton("ℹ️ Help",              callback_data="help")],
    ]
    if approved or admin:
        rows.append([
            InlineKeyboardButton("📤 Share File",         callback_data="share_start"),
            InlineKeyboardButton("📢 Send Announcement",  callback_data="ann_start"),
        ])
    if admin:
        rows.append([InlineKeyboardButton("🛠️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def file_types_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(lbl, callback_data=f"browse_type:{k}")]
            for k, lbl in FILE_TYPES.items()]
    rows.append([InlineKeyboardButton("📂 All Files", callback_data="browse_type:all")])
    rows.append([InlineKeyboardButton("← Back",      callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def share_type_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(lbl, callback_data=f"stype:{k}")]
            for k, lbl in FILE_TYPES.items()]
    rows.append([InlineKeyboardButton("← Cancel", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Members",         callback_data="adm:members")],
        [InlineKeyboardButton("⏳ Pending Users",   callback_data="adm:pending")],
        [InlineKeyboardButton("📊 Stats",           callback_data="adm:stats")],
        [InlineKeyboardButton("📌 Set Pinned Info", callback_data="adm:pin")],
        [InlineKeyboardButton("🚫 Banned Users",    callback_data="adm:banned")],
        [InlineKeyboardButton("← Back",             callback_data="menu")],
    ])


def approve_reject_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{uid}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"reject:{uid}"),
    ]])


# ── /start ────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    user = update.effective_user
    d    = load_data()

    if is_banned(uid, d):
        await update.message.reply_text("🚫 You are banned from this bot.")
        return

    # Register if new
    if str(uid) not in d["members"]:
        d["members"][str(uid)] = {
            "name":     user.full_name,
            "username": user.username or "",
            "joined":   now(),
        }
        save_data(d)

        # Notify admin
        if SUPER_ADMIN_ID:
            try:
                await ctx.bot.send_message(
                    SUPER_ADMIN_ID,
                    f"🆕 New member in <b>{dept_name()}</b> bot!\n"
                    f"👤 {user.full_name} (@{user.username})\n"
                    f"🆔 <code>{uid}</code>",
                    parse_mode=ParseMode.HTML,
                )
            except: pass

    dn = dept_name()
    si = school_info()

    await update.message.reply_text(
        f"👋 Welcome to the <b>{dn}</b> Department Bot!\n"
        f"🏫 {si.get('emoji','')} {si.get('name', '')}\n\n"
        f"What would you like to do?",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )


# ── Menu button handler ────────────────────────────────────────
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    await query.edit_message_text(
        f"📋 <b>{dept_name()} Bot</b>\n\nWhat would you like to do?",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )


# ── BROWSE FILES ──────────────────────────────────────────────
async def browse_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📂 <b>Browse Materials</b>\n\nSelect the type of material you want:",
        parse_mode=ParseMode.HTML,
        reply_markup=file_types_keyboard(),
    )


async def browse_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    uid    = query.from_user.id
    ftype  = query.data.split(":")[1]
    d      = load_data()
    files  = d["files"]

    filtered = files if ftype == "all" else [f for f in files if f.get("ftype") == ftype]

    if not filtered:
        lbl = FILE_TYPES.get(ftype, "All Files")
        await query.edit_message_text(
            f"📭 No <b>{lbl}</b> uploaded yet for <b>{dept_name()}</b>.\n\n"
            f"Check back later or ask an approved user to upload materials.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Back", callback_data="browse")
            ]]),
        )
        return

    await query.edit_message_text(
        f"📂 Found <b>{len(filtered)}</b> file(s). Sending now...",
        parse_mode=ParseMode.HTML,
    )

    for f in filtered[-15:]:
        lbl = FILE_TYPES.get(f.get("ftype",""), "Material")
        cap = (
            f"<b>{lbl}</b>\n"
            f"{f.get('caption','')}\n"
            f"<i>Shared by {f.get('sender','?')} — {f.get('date','')}</i>"
        )
        try:
            await send_file(ctx.bot, uid, f["file_id"], f["file_type"], cap)
        except Exception as e:
            log.error(f"File send error: {e}")


# ── ANNOUNCEMENTS ──────────────────────────────────────────────
async def view_announcements(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d     = load_data()
    anns  = d["announcements"][-10:]

    if not anns:
        await query.edit_message_text(
            "📭 No announcements yet.\nCheck back later!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
        )
        return

    text = f"📣 <b>Latest Announcements — {dept_name()}</b>\n\n"
    for a in reversed(anns):
        text += f"━━━━━━━━━━━━\n{a.get('text','')}\n<i>— {a.get('sender','?')}, {a.get('date','')}</i>\n\n"

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
    )


# ── PINNED INFO ────────────────────────────────────────────────
async def view_pinned(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d     = load_data()
    pin   = d.get("pinned", "")

    text = (
        f"📌 <b>Pinned Info — {dept_name()}</b>\n\n{pin}"
        if pin else
        f"📌 No pinned information yet.\nAsk your department admin to pin important info."
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
    )


# ── MY PROFILE ─────────────────────────────────────────────────
async def view_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()
    m     = d["members"].get(str(uid), {})

    status = "👑 Admin" if is_admin(uid, d) else ("✅ Approved" if is_approved(uid, d) else "👤 Member")
    files_uploaded = len([f for f in d["files"] if f.get("sender") == m.get("name")])

    await query.edit_message_text(
        f"👤 <b>My Profile</b>\n\n"
        f"Name:     {m.get('name', '?')}\n"
        f"Status:   {status}\n"
        f"Dept:     {dept_name()}\n"
        f"Joined:   {m.get('joined', '?')}\n"
        f"Files Shared: {files_uploaded}\n\n"
        f"<i>Want to share files? Send /request</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📬 Request Upload Access", callback_data="request_access")],
            [InlineKeyboardButton("← Back", callback_data="menu")],
        ]),
    )


# ── HELP ──────────────────────────────────────────────────────
async def view_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    text = (
        f"ℹ️ <b>{dept_name()} Bot — Help</b>\n\n"
        f"<b>What I can do:</b>\n"
        f"📂 Browse lecture notes, past questions, assignments\n"
        f"🤖 Answer academic questions with AI\n"
        f"📣 Show department announcements\n"
        f"📌 Show pinned department info\n\n"
        f"<b>Commands:</b>\n"
        f"/start — Main menu\n"
        f"/request — Request upload access\n"
        f"/help — This message\n\n"
        f"<b>Back to main registration bot:</b>\n"
        f"{MAIN_BOT_LINK}\n\n"
    )
    if is_admin(uid, d):
        text += (
            f"<b>Admin Commands:</b>\n"
            f"/ban USER_ID\n"
            f"/unban USER_ID\n"
            f"/broadcast — Message all members\n"
        )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
    )


# ── AI CHAT ───────────────────────────────────────────────────
async def ai_start_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id

    await query.edit_message_text(
        f"🤖 <b>AI Academic Assistant — {dept_name()}</b>\n\n"
        f"Ask me anything about your course, assignments, or academic topics.\n\n"
        f"I specialise in subjects relevant to <b>{dept_name()}</b>.\n\n"
        f"Type your question below.\n"
        f"Type <b>done</b> to exit. Type <b>clear</b> to reset.",
        parse_mode=ParseMode.HTML,
    )
    return AI_CHAT


async def ai_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid  = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() in ("done", "quit", "exit", "stop"):
        d = load_data()
        await update.message.reply_text(
            "👋 Exited AI mode.",
            reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
        )
        return ConversationHandler.END

    if text.lower() == "clear":
        clear_history(uid, DEPT_KEY)
        await update.message.reply_text("🗑️ Conversation cleared! Ask your next question.")
        return AI_CHAT

    await ctx.bot.send_chat_action(uid, "typing")
    answer = await ask_gemini(uid, DEPT_KEY, dept_name(), text)

    chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            await update.message.reply_text(
                f"🤖 {chunk}\n\n_Type your next question or type_ *done* _to exit._",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text(chunk)

    return AI_CHAT


# ── SHARE FILE ────────────────────────────────────────────────
async def share_start_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    if not is_approved(uid, d):
        await query.edit_message_text(
            "🔒 You need approval to share files.\n\n"
            "Tap the button below to request access from the admin.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📬 Request Access", callback_data="request_access")],
                [InlineKeyboardButton("← Back",            callback_data="menu")],
            ]),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "📤 <b>Share a File</b>\n\nWhat type of material is this?",
        parse_mode=ParseMode.HTML,
        reply_markup=share_type_keyboard(),
    )
    return SHARE_TYPE


async def share_type_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "menu":
        await menu_callback(update, ctx)
        return ConversationHandler.END

    ctx.user_data["ftype"] = query.data.split(":")[1]
    await query.edit_message_text(
        "📎 Now <b>send the file</b> — any format (PDF, Word, image, video, audio):",
        parse_mode=ParseMode.HTML,
    )
    return SHARE_FILE


async def share_file_got(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    fid, ftype = get_file(update.message)
    if not fid:
        await update.message.reply_text("Please send a file (document, photo, video, or audio).")
        return SHARE_FILE

    ctx.user_data["fid"]   = fid
    ctx.user_data["ftype2"]= ftype

    await update.message.reply_text(
        "✏️ Add a caption for this file\n"
        "(e.g. <i>CHM 101 — Organic Chemistry Lecture 5</i>)\n\n"
        "Or type <b>skip</b> to use no caption.",
        parse_mode=ParseMode.HTML,
    )
    return SHARE_CAP


async def share_cap_got(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid     = update.effective_user.id
    cap     = update.message.text.strip()
    if cap.lower() == "skip": cap = ""
    d       = load_data()

    d["files"].append({
        "file_id":   ctx.user_data["fid"],
        "file_type": ctx.user_data["ftype2"],
        "ftype":     ctx.user_data.get("ftype", "other"),
        "caption":   cap,
        "sender":    update.effective_user.full_name,
        "date":      now(),
    })
    d["stats"]["files"] = d["stats"].get("files", 0) + 1
    save_data(d)

    await update.message.reply_text(
        f"✅ <b>File saved!</b>\n"
        f"Type: {FILE_TYPES.get(ctx.user_data.get('ftype','other'), 'Material')}\n"
        f"Caption: {cap or 'None'}\n\n"
        f"All members can now download it from Browse Materials.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ── SEND ANNOUNCEMENT ─────────────────────────────────────────
async def ann_start_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    if not is_approved(uid, d):
        await query.edit_message_text(
            "🔒 You need approval to send announcements.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "📢 <b>Send Announcement</b>\n\n"
        "Type your announcement message.\nIt will be sent to ALL members of this department bot.\n\n"
        "Type /cancel to abort.",
        parse_mode=ParseMode.HTML,
    )
    return ANN_TEXT


async def ann_text_got(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid    = update.effective_user.id
    text   = update.message.text.strip()
    sender = update.effective_user.full_name
    d      = load_data()

    d["announcements"].append({"text": text, "sender": sender, "date": now()})
    d["stats"]["announcements"] = d["stats"].get("announcements", 0) + 1
    save_data(d)

    msg  = (
        f"📣 <b>ANNOUNCEMENT — {dept_name()}</b>\n\n"
        f"{text}\n\n"
        f"— <i>{sender}, {now()}</i>"
    )
    sent = 0
    for uid_str, info in d["members"].items():
        tid = int(uid_str)
        if tid in d["banned"]: continue
        try:
            await ctx.bot.send_message(tid, msg, parse_mode=ParseMode.HTML)
            sent += 1
        except: pass

    await update.message.reply_text(
        f"✅ Announcement sent to <b>{sent}</b> member(s)!",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )
    return ConversationHandler.END


# ── REQUEST ACCESS ────────────────────────────────────────────
async def request_access_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    if is_approved(uid, d):
        await query.edit_message_text(
            "✅ You already have upload access!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
        )
        return

    if uid in d["pending"]:
        await query.edit_message_text(
            "⏳ Your request is already pending. Wait for admin approval.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
        )
        return

    d["pending"].append(uid)
    save_data(d)

    m      = d["members"].get(str(uid), {})
    notif  = (
        f"📬 <b>Access Request — {dept_name()}</b>\n\n"
        f"👤 {m.get('name', '?')} (@{m.get('username','')})\n"
        f"🆔 <code>{uid}</code>"
    )
    if SUPER_ADMIN_ID:
        try:
            await ctx.bot.send_message(
                SUPER_ADMIN_ID, notif,
                parse_mode=ParseMode.HTML,
                reply_markup=approve_reject_kb(uid),
            )
        except: pass

    await query.edit_message_text(
        "📬 Request sent to the admin!\nYou will be notified when approved.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="menu")]]),
    )


async def handle_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    target = int(query.data.split(":")[1])
    d      = load_data()

    if target not in d["approved"]: d["approved"].append(target)
    if target in d["pending"]:      d["pending"].remove(target)
    if target in d["banned"]:       d["banned"].remove(target)
    save_data(d)

    m = d["members"].get(str(target), {})
    await query.edit_message_text(f"✅ {m.get('name', target)} approved for {dept_name()}!")
    try:
        await ctx.bot.send_message(
            target,
            f"🎉 You have been approved to share files and send announcements in the "
            f"<b>{dept_name()}</b> bot!",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(True, False),
        )
    except: pass


async def handle_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    target = int(query.data.split(":")[1])
    d      = load_data()

    if target in d["pending"]: d["pending"].remove(target)
    save_data(d)

    m = d["members"].get(str(target), {})
    await query.edit_message_text(f"❌ {m.get('name', target)}'s request rejected.")
    try: await ctx.bot.send_message(target, "❌ Your access request was not approved.")
    except: pass


# ── ADMIN PANEL ────────────────────────────────────────────────
async def admin_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = query.from_user.id
    d     = load_data()

    if not is_admin(uid, d):
        await query.edit_message_text("🔒 Admins only.")
        return

    if query.data == "admin":
        await query.edit_message_text(
            f"🛠️ <b>Admin Panel — {dept_name()}</b>\n\n"
            f"👥 Members: {len(d['members'])}\n"
            f"✅ Approved: {len(d['approved'])}\n"
            f"⏳ Pending: {len(d['pending'])}\n"
            f"📂 Files: {len(d['files'])}\n"
            f"📣 Announcements: {len(d['announcements'])}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard(),
        )
        return

    action = query.data.split(":")[1]

    if action == "members":
        members = d["members"]
        if not members:
            await query.edit_message_text("No members yet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]))
            return
        text = f"👥 <b>Members ({len(members)})</b>\n\n"
        for uid_str, m in list(members.items())[:30]:
            s = "👑" if is_admin(int(uid_str), d) else ("✅" if is_approved(int(uid_str), d) else "👤")
            text += f"{s} {m.get('name','?')} — <code>{uid_str}</code>\n"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]))

    elif action == "pending":
        pending = d["pending"]
        if not pending:
            await query.edit_message_text("✅ No pending requests!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]))
            return
        for puid in pending:
            m = d["members"].get(str(puid), {})
            await ctx.bot.send_message(uid,
                f"⏳ <b>Pending:</b> {m.get('name','?')} — <code>{puid}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=approve_reject_kb(puid),
            )
        await query.edit_message_text(f"Showing {len(pending)} pending request(s) above.")

    elif action == "stats":
        stats = d["stats"]
        await query.edit_message_text(
            f"📊 <b>Stats — {dept_name()}</b>\n\n"
            f"👥 Members: {len(d['members'])}\n"
            f"📂 Files shared: {len(d['files'])}\n"
            f"📣 Announcements: {len(d['announcements'])}\n"
            f"🤖 AI questions: {stats.get('questions', 0)}\n"
            f"🚫 Banned: {len(d['banned'])}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]),
        )

    elif action == "banned":
        banned = d["banned"]
        if not banned:
            await query.edit_message_text("No banned users.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]))
            return
        text = "🚫 <b>Banned Users</b>\n\n"
        for buid in banned:
            m = d["members"].get(str(buid), {})
            text += f"• {m.get('name','?')} — <code>{buid}</code>\n"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]))

    elif action == "pin":
        await query.edit_message_text(
            "📌 Send the new pinned message text.\nThis replaces the current pinned info.",
        )
        ctx.user_data["setting_pin"] = True

    elif action == "admins":
        await query.edit_message_text(
            f"👑 Super Admin: <code>{SUPER_ADMIN_ID}</code>\n"
            f"Admins: {', '.join(str(a) for a in d['admins']) or 'None'}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin")]]),
        )


async def handle_set_pin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle setting pinned message from admin."""
    if not ctx.user_data.get("setting_pin"): return
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d): return

    d["pinned"] = update.message.text.strip()
    save_data(d)
    ctx.user_data.pop("setting_pin", None)
    await update.message.reply_text(
        "📌 Pinned info updated!",
        reply_markup=main_menu(True, True),
    )


# ── /ban, /unban, /broadcast (commands) ──────────────────────
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d): return
    try:
        target = int(ctx.args[0])
        if target not in d["banned"]: d["banned"].append(target)
        if target in d["approved"]:   d["approved"].remove(target)
        save_data(d)
        m = d["members"].get(str(target), {})
        await update.message.reply_text(f"🚫 {m.get('name', target)} banned.")
        try: await ctx.bot.send_message(target, "🚫 You have been banned from this department bot.")
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
        try: await ctx.bot.send_message(target, "✅ You have been unbanned.")
        except: pass
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban USER_ID")


AWAITING_BC = 50
async def broadcast_start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    d   = load_data()
    if not is_admin(uid, d):
        return ConversationHandler.END
    await update.message.reply_text(
        f"📡 Type message to send to ALL {len(d['members'])} members of {dept_name()}.\n/cancel to abort."
    )
    return AWAITING_BC


async def broadcast_send_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    d    = load_data()
    sent = 0
    for uid_str in d["members"]:
        tid = int(uid_str)
        if tid in d["banned"]: continue
        try:
            await ctx.bot.send_message(
                tid,
                f"📡 <b>{dept_name()} — Announcement</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except: pass
    await update.message.reply_text(f"✅ Sent to {sent} members.")
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    d   = load_data()
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )
    return ConversationHandler.END


async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.user_data.get("setting_pin"):
        await handle_set_pin(update, ctx)
        return
    uid = update.effective_user.id
    d   = load_data()
    if is_banned(uid, d):
        await update.message.reply_text("🚫 You are banned.")
        return
    if str(uid) not in d["members"]:
        await update.message.reply_text("Please /start first.")
        return
    await update.message.reply_text(
        "Use the buttons below 👇",
        reply_markup=main_menu(is_approved(uid, d), is_admin(uid, d)),
    )


# ── MAIN ──────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        log.error("❌ DEPT_BOT_TOKEN not set!")
        return
    if not DEPT_KEY:
        log.error("❌ DEPT_KEY not set! e.g. DEPT_KEY=computer_sci")
        return
    if not SCHOOL_KEY:
        log.error("❌ SCHOOL_KEY not set! e.g. SCHOOL_KEY=sict")
        return

    log.info(f"🤖 Starting {dept_name()} bot (dept={DEPT_KEY}, school={SCHOOL_KEY})")

    app = Application.builder().token(BOT_TOKEN).build()

    # AI conversation
    ai_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ai_start_cb, pattern="^ai_start$")],
        states={AI_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_question)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Share file conversation
    share_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(share_start_cb, pattern="^share_start$")],
        states={
            SHARE_TYPE: [CallbackQueryHandler(share_type_chosen, pattern=r"^(stype:|menu$)")],
            SHARE_FILE: [MessageHandler(
                filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
                share_file_got
            )],
            SHARE_CAP:  [MessageHandler(filters.TEXT & ~filters.COMMAND, share_cap_got)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Announcement conversation
    ann_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ann_start_cb, pattern="^ann_start$")],
        states={ANN_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_text_got)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Broadcast command conversation
    bc_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start_cmd)],
        states={AWAITING_BC: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send_msg)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   lambda u, c: view_help(u, c)))
    app.add_handler(CommandHandler("ban",    ban_cmd))
    app.add_handler(CommandHandler("unban",  unban_cmd))
    app.add_handler(ai_conv)
    app.add_handler(share_conv)
    app.add_handler(ann_conv)
    app.add_handler(bc_conv)

    # Inline callbacks
    app.add_handler(CallbackQueryHandler(menu_callback,        pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(browse_start,         pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(browse_type,          pattern=r"^browse_type:"))
    app.add_handler(CallbackQueryHandler(view_announcements,   pattern="^announcements$"))
    app.add_handler(CallbackQueryHandler(view_pinned,          pattern="^pinned$"))
    app.add_handler(CallbackQueryHandler(view_profile,         pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(view_help,            pattern="^help$"))
    app.add_handler(CallbackQueryHandler(request_access_cb,    pattern="^request_access$"))
    app.add_handler(CallbackQueryHandler(handle_approve,       pattern=r"^approve:"))
    app.add_handler(CallbackQueryHandler(handle_reject,        pattern=r"^reject:"))
    app.add_handler(CallbackQueryHandler(admin_cb,             pattern=r"^(admin|adm:)"))

    app.add_handler(MessageHandler(filters.ALL, unknown))

    log.info(f"✅ {dept_name()} Bot is RUNNING!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
