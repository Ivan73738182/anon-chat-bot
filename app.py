import asyncio
import logging
import os
import threading
from flask import Flask

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import (
    init_db, get_user, set_user, clear_user, get_waiting,
    add_all_user, count_all_users, count_waiting, count_chatting
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_ID = 7435486390

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

search_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Найти собеседника", callback_data="search")],
    [InlineKeyboardButton(text="❌ Выйти из чата", callback_data="leave")],
])

chat_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔄 Следующий", callback_data="next"),
        InlineKeyboardButton(text="❌ Выйти", callback_data="leave"),
    ]
])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    try:
        add_all_user(message.from_user.id)
        await message.answer(
            "Привет! 👋\nЯ бот анонимных знакомств! 🎉\n\n"
            "Нажми кнопку ниже, чтобы найти собеседника.",
            reply_markup=search_kb
        )
    except Exception as e:
        logging.error(f"Ошибка /start: {e}")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Эта команда только для админа.")
        return

    total = count_all_users()
    waiting = count_waiting()
    chatting = count_chatting()

    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"💬 В чате сейчас: <b>{chatting // 2}</b> пар\n"
        f"⏳ В очереди: <b>{waiting}</b>"
    )


@dp.callback_query(F.data == "search")
async def cb_search(callback: CallbackQuery):
    uid = callback.from_user.id
    me = get_user(uid)

    if me and me["status"] == "chatting" and me["partner_id"]:
        await callback.answer("Ты уже в чате. Нажми «❌ Выйти».", show_alert=True)
        return

    await try_match(uid, callback)


@dp.callback_query(F.data == "next")
async def cb_next(callback: CallbackQuery):
    uid = callback.from_user.id
    me = get_user(uid)

    if me and me["status"] == "chatting" and me["partner_id"]:
        other = me["partner_id"]
        clear_user(uid)
        clear_user(other)
        try:
            await bot.send_message(
                other,
                "🔄 Собеседник ищет нового. Подожди немного...",
                reply_markup=search_kb
            )
        except Exception:
            pass

    await callback.answer("Ищем нового...")
    await try_match(uid, callback)


@dp.callback_query(F.data == "leave")
async def cb_leave(callback: CallbackQuery):
    uid = callback.from_user.id
    me = get_user(uid)

    if not me:
        await callback.answer("Ты и так не в чате.")
        try:
            await bot.send_message(uid, "Ты не в чате. Нажми /start.", reply_markup=search_kb)
        except Exception:
            pass
        return

    if me["status"] == "waiting":
        clear_user(uid)
        await callback.answer("Вышел из очереди")
        await bot.send_message(uid, "Ты вышел из очереди.", reply_markup=search_kb)
        return

    other = me["partner_id"]
    clear_user(uid)
    if other:
        clear_user(other)
        try:
            await bot.send_message(
                other,
                "Собеседник вышел из чата. /start — найти нового.",
                reply_markup=search_kb
            )
        except Exception:
            pass

    await callback.answer("Вышел из чата")
    await bot.send_message(uid, "Ты вышел из чата.", reply_markup=search_kb)


async def try_match(uid: int, callback: CallbackQuery):
    waiting = get_waiting()

    if waiting and waiting != uid:
        set_user(uid, partner_id=waiting, status="chatting")
        set_user(waiting, partner_id=uid, status="chatting")

        await callback.answer("Нашли! 🎉")
        await bot.send_message(
            uid,
            "✅ Собеседник найден! Пиши сообщение — я перешлю анонимно.",
            reply_markup=chat_kb
        )
        await bot.send_message(
            waiting,
            "✅ Собеседник найден! Пиши сообщение — я перешлю анонимно.",
            reply_markup=chat_kb
        )
    else:
        set_user(uid, partner_id=None, status="waiting")
        await callback.answer("Ищем...")
        await bot.send_message(uid, "🔍 Ищем собеседника... Подожди немного.")


@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    uid = message.from_user.id
    me = get_user(uid)

    if not me:
        await message.answer("Ты сейчас ни с кем не общаешься.", reply_markup=search_kb)
        return

    if me["status"] == "waiting":
        clear_user(uid)
        await message.answer("Ты вышел из очереди.", reply_markup=search_kb)
        return

    other = me["partner_id"]
    clear_user(uid)
    if other:
        clear_user(other)
        try:
            await bot.send_message(
                other,
                "Собеседник вышел из чата. /start — найти нового.",
                reply_markup=search_kb
            )
        except Exception:
            pass
    await message.answer("Ты вышел из чата.", reply_markup=search_kb)


@dp.message(F.text)
async def relay_message(message: Message):
    uid = message.from_user.id
    me = get_user(uid)

    if not me or me["status"] != "chatting" or not me["partner_id"]:
        await message.answer(
            "Ты не в чате. Нажми /start, чтобы найти собеседника.",
            reply_markup=search_kb
        )
        return

    other = me["partner_id"]
    try:
        await bot.send_message(other, f"👤 Собеседник:\n{message.text}")
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")
        await message.answer("Не удалось отправить. Попробуй ещё раз.")


async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot, handle_signals=False)


# ==================== FLASK ДЛЯ RENDER ====================

flask_app = Flask(__name__)


@flask_app.route("/")
def index():
    return "Bot is running"


@flask_app.route("/health")
def health():
    return "OK"


def run_bot():
    asyncio.run(main())


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
