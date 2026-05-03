#!/usr/bin/env python3
"""
Telegram To-Do / Task Manager Bot
Render.com deploy-এর জন্য Webhook mode ব্যবহার করা হয়েছে
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Environment Variables (Render Dashboard থেকে সেট করবেন) ────────────────
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]   # e.g. https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 8443))

# ─── In-memory storage ───────────────────────────────────────────────────────
user_tasks: dict[int, list[dict]] = {}


def get_tasks(user_id: int) -> list[dict]:
    return user_tasks.setdefault(user_id, [])


# ─── Helpers ──────────────────────────────────────────────────────────────────
def render_task_list(tasks: list[dict]) -> str:
    if not tasks:
        return "📭 কোনো task নেই। /add দিয়ে task যোগ করুন!"
    lines = []
    for i, t in enumerate(tasks, 1):
        status = "✅" if t["done"] else "🔲"
        lines.append(f"{status} {i}. {t['text']}")
    return "\n".join(lines)


def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    tasks = get_tasks(user_id)
    buttons = []
    for i, t in enumerate(tasks, 1):
        label = f"↩️ Undo {i}" if t["done"] else f"✅ Done {i}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"toggle:{i}")])
    for i in range(1, len(tasks) + 1):
        buttons.append([InlineKeyboardButton(f"🗑 Delete {i}", callback_data=f"delete:{i}")])
    buttons.append([InlineKeyboardButton("🧹 Clear completed", callback_data="clear")])
    return InlineKeyboardMarkup(buttons)


# ─── Command Handlers ─────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *To-Do Bot-এ স্বাগতম!*\n\n"
        "এই bot দিয়ে আপনি সহজেই task manage করতে পারবেন।\n\n"
        "📌 *Commands:*\n"
        "/add <task> — নতুন task যোগ করুন\n"
        "/list — সব task দেখুন\n"
        "/done <number> — task সম্পন্ন করুন\n"
        "/delete <number> — task মুছুন\n"
        "/clear — সম্পন্ন tasks পরিষ্কার করুন\n"
        "/help — সাহায্য",
        parse_mode="Markdown",
    )


async def add_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text("⚠️ ব্যবহার: /add <আপনার task>")
        return
    task_text = " ".join(ctx.args)
    tasks = get_tasks(user_id)
    tasks.append({"text": task_text, "done": False})
    await update.message.reply_text(
        f"✅ Task যোগ হয়েছে:\n*{task_text}*\n\n{render_task_list(tasks)}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id),
    )


async def list_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    await update.message.reply_text(
        f"📋 *আপনার Task List:*\n\n{render_task_list(tasks)}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id) if tasks else None,
    )


async def done_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("⚠️ ব্যবহার: /done <task number>")
        return
    idx = int(ctx.args[0]) - 1
    if idx < 0 or idx >= len(tasks):
        await update.message.reply_text("❌ এই নম্বরের task নেই!")
        return
    tasks[idx]["done"] = True
    await update.message.reply_text(
        f"🎉 Task সম্পন্ন!\n\n{render_task_list(tasks)}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id),
    )


async def delete_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("⚠️ ব্যবহার: /delete <task number>")
        return
    idx = int(ctx.args[0]) - 1
    if idx < 0 or idx >= len(tasks):
        await update.message.reply_text("❌ এই নম্বরের task নেই!")
        return
    removed = tasks.pop(idx)
    await update.message.reply_text(
        f"🗑 Task মুছা হয়েছে: *{removed['text']}*\n\n{render_task_list(tasks)}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id) if tasks else None,
    )


async def clear_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    before = len(tasks)
    user_tasks[user_id] = [t for t in tasks if not t["done"]]
    after = len(user_tasks[user_id])
    await update.message.reply_text(
        f"🧹 {before - after}টি সম্পন্ন task মুছা হয়েছে।\n\n"
        f"{render_task_list(user_tasks[user_id])}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id) if user_tasks[user_id] else None,
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🆘 *Help - To-Do Bot*\n\n"
        "/add <task> — নতুন task যোগ করুন\n"
        "   উদাহরণ: `/add বাজার করা`\n\n"
        "/list — সব task দেখুন\n\n"
        "/done <number> — task সম্পন্ন করুন\n"
        "   উদাহরণ: `/done 2`\n\n"
        "/delete <number> — task মুছুন\n"
        "   উদাহরণ: `/delete 3`\n\n"
        "/clear — সম্পন্ন সব task মুছুন\n\n"
        "অথবা task list-এর button ব্যবহার করুন! 👆",
        parse_mode="Markdown",
    )


# ─── Inline Button Handler ────────────────────────────────────────────────────
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_tasks(user_id)
    data = query.data

    if data.startswith("toggle:"):
        idx = int(data.split(":")[1]) - 1
        if 0 <= idx < len(tasks):
            tasks[idx]["done"] = not tasks[idx]["done"]
    elif data.startswith("delete:"):
        idx = int(data.split(":")[1]) - 1
        if 0 <= idx < len(tasks):
            tasks.pop(idx)
    elif data == "clear":
        user_tasks[user_id] = [t for t in tasks if not t["done"]]

    tasks = get_tasks(user_id)
    await query.edit_message_text(
        f"📋 *আপনার Task List:*\n\n{render_task_list(tasks)}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id) if tasks else None,
    )


# ─── Main — Webhook mode for Render ──────────────────────────────────────────
def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done_task))
    app.add_handler(CommandHandler("delete", delete_task))
    app.add_handler(CommandHandler("clear", clear_done))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info(f"Webhook mode চালু হচ্ছে → {WEBHOOK_URL}")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
    )


if __name__ == "__main__":
    main()
