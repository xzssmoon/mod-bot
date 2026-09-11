# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import BOT_TOKEN, ADMIN_ID, BOT_USERNAME, BOT_NAME, LOG_CHANNEL
from database import (
    init_db, get_member, add_member, add_warn, reset_warns,
    add_rep, set_rank, add_log, get_logs, get_top_reps, get_all_admins
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ==================== ПРОВЕРКА ПРАВ ====================
async def is_admin(chat_id, user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "creator"]:
            return True
    except Exception:
        pass
    return False


async def is_owner(chat_id, user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status == "creator":
            return True
    except Exception:
        pass
    return False


async def send_log(text):
    if not LOG_CHANNEL:
        return
    try:
        await bot.send_message(LOG_CHANNEL, text, parse_mode="HTML")
    except Exception:
        pass


# ==================== /start ====================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    if message.chat.type == "private":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(
            "➕ Добавить в группу",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        ))
        await message.answer(
            f"👋 <b>{BOT_NAME}</b>\n\n"
            f"Я — бот-модератор для групп.\n\n"
            f"<b>Как использовать:</b>\n"
            f"1. Добавь меня в группу\n"
            f"2. Дай права администратора\n"
            f"3. Пиши команды с реплаем на сообщение\n\n"
            f"<b>Команды:</b>\n"
            f"/ban — забанить\n"
            f"/unban — разбанить\n"
            f"/warn — выговор (3 = автобан)\n"
            f"/unwarn — снять выговоры\n"
            f"/rep — +репутация\n"
            f"/promote — повысить\n"
            f"/demote — понизить\n"
            f"/admin — админ-панель\n"
            f"/logs — последние действия\n"
            f"/top — топ репутации\n"
            f"/admins — список админов",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    await message.reply(f"🛡 <b>{BOT_NAME}</b> активен.\nНапиши /admin", parse_mode="HTML")


# ==================== /admin ====================
@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if message.chat.type == "private":
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ Только для админов")
        return

    admins = get_all_admins(message.chat.id)

    text = (
        f"🛡 <b>Админ-панель</b>\n\n"
        f"<b>Модерация:</b>\n"
        f"/ban — забанить (reply)\n"
        f"/unban — разбанить (reply)\n"
        f"/warn — выговор (3 = автобан)\n"
        f"/unwarn — снять выговоры\n"
        f"/rep — +1 репутация (reply)\n"
        f"/promote — повысить (reply)\n"
        f"/demote — понизить (reply)\n\n"
        f"<b>Информация:</b>\n"
        f"/logs — последние действия\n"
        f"/top — топ репутации\n"
        f"/admins — список админов"
    )

    if admins:
        text += "\n\n<b>Назначенные админы:</b>\n"
        for uid, name, rank in admins[:10]:
            text += f"• {name} — {rank}\n"

    await message.reply(text, parse_mode="HTML")


# ==================== /ban ====================
@dp.message_handler(commands=["ban"])
async def cmd_ban(message: types.Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    if target.id == ADMIN_ID:
        await message.reply("❌ Нельзя забанить главного админа")
        return

    try:
        await bot.kick_chat_member(chat_id, target.id)
        add_log(chat_id, message.from_user.id, target.id, "ban")
        await message.reply(
            f"🚫 <b>{target.full_name}</b> забанен\n"
            f"👮 Админ: {message.from_user.full_name}",
            parse_mode="HTML"
        )
        await send_log(
            f"🚫 <b>BAN</b>\n"
            f"👮 Админ: {message.from_user.full_name}\n"
            f"🎯 Цель: {target.full_name} (<code>{target.id}</code>)\n"
            f"💬 Чат: {message.chat.title}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ==================== /unban ====================
@dp.message_handler(commands=["unban"])
async def cmd_unban(message: types.Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    try:
        await bot.unban_chat_member(chat_id, target.id, only_if_banned=True)
        add_log(chat_id, message.from_user.id, target.id, "unban")
        await message.reply(f"✅ <b>{target.full_name}</b> разбанен", parse_mode="HTML")
        await send_log(
            f"✅ <b>UNBAN</b>\n"
            f"👮 Админ: {message.from_user.full_name}\n"
            f"🎯 Цель: {target.full_name}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ==================== /warn ====================
@dp.message_handler(commands=["warn"])
async def cmd_warn(message: types.Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    add_member(chat_id, target.id, target.username or "", target.first_name or "")
    add_warn(chat_id, target.id)
    add_log(chat_id, message.from_user.id, target.id, "warn")

    member = get_member(chat_id, target.id)
    warns = member[4] if member else 1

    text = (
        f"⚠️ <b>{target.full_name}</b> получил выговор\n"
        f"👮 Админ: {message.from_user.full_name}\n"
        f"📊 Выговоров: <b>{warns}/3</b>"
    )

    if warns >= 3:
        try:
            await bot.kick_chat_member(chat_id, target.id)
            text += "\n\n🚫 <b>Автобан: 3 выговора!</b>"
            reset_warns(chat_id, target.id)
            add_log(chat_id, message.from_user.id, target.id, "autoban")
        except Exception:
            pass

    await message.reply(text, parse_mode="HTML")
    await send_log(
        f"⚠️ <b>WARN {warns}/3</b>\n"
        f"👮 Админ: {message.from_user.full_name}\n"
        f"🎯 Цель: {target.full_name}\n"
        f"💬 Чат: {message.chat.title}"
    )


# ==================== /unwarn ====================
@dp.message_handler(commands=["unwarn"])
async def cmd_unwarn(message: types.Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    reset_warns(chat_id, target.id)
    add_log(chat_id, message.from_user.id, target.id, "unwarn")

    await message.reply(
        f"✅ Выговоры <b>{target.full_name}</b> сброшены",
        parse_mode="HTML"
    )
    await send_log(
        f"✅ <b>UNWARN</b>\n"
        f"👮 Админ: {message.from_user.full_name}\n"
        f"🎯 Цель: {target.full_name}"
    )


# ==================== /rep ====================
@dp.message_handler(commands=["rep"])
async def cmd_rep(message: types.Message):
    if message.chat.type == "private":
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.reply("❌ Нельзя давать репутацию себе")
        return

    chat_id = message.chat.id
    add_member(chat_id, target.id, target.username or "", target.first_name or "")
    add_rep(chat_id, target.id)

    member = get_member(chat_id, target.id)
    reps = member[5] if member else 1

    await message.reply(
        f"⭐ <b>{target.full_name}</b> получил +1 репутацию\n"
        f"📊 Всего: <b>{reps}</b>",
        parse_mode="HTML"
    )


# ==================== /promote ====================
@dp.message_handler(commands=["promote"])
async def cmd_promote(message: types.Message):
    if not await is_owner(message.chat.id, message.from_user.id):
        await message.reply("❌ Только владелец чата может повышать")
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    try:
        await bot.promote_chat_member(
            chat_id, target.id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_invite_users=True
        )
        add_member(chat_id, target.id, target.username or "", target.first_name or "")
        set_rank(chat_id, target.id, "Модератор")
        add_log(chat_id, message.from_user.id, target.id, "promote")

        await message.reply(
            f"⬆️ <b>{target.full_name}</b> повышен до <b>Модератора</b>",
            parse_mode="HTML"
        )
        await send_log(
            f"⬆️ <b>PROMOTE</b>\n"
            f"👮 Кто: {message.from_user.full_name}\n"
            f"🎯 Цель: {target.full_name}\n"
            f"💬 Чат: {message.chat.title}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ==================== /demote ====================
@dp.message_handler(commands=["demote"])
async def cmd_demote(message: types.Message):
    if not await is_owner(message.chat.id, message.from_user.id):
        await message.reply("❌ Только владелец чата может понижать")
        return
    if not message.reply_to_message:
        await message.reply("❌ Ответь на сообщение юзера")
        return

    target = message.reply_to_message.from_user
    chat_id = message.chat.id

    try:
        await bot.promote_chat_member(
            chat_id, target.id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_invite_users=False,
            can_change_info=False
        )
        set_rank(chat_id, target.id, "Участник")
        add_log(chat_id, message.from_user.id, target.id, "demote")

        await message.reply(
            f"⬇️ <b>{target.full_name}</b> понижен до <b>Участника</b>",
            parse_mode="HTML"
        )
        await send_log(
            f"⬇️ <b>DEMOTE</b>\n"
            f"👮 Кто: {message.from_user.full_name}\n"
            f"🎯 Цель: {target.full_name}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ==================== /logs ====================
@dp.message_handler(commands=["logs"])
async def cmd_logs(message: types.Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return

    rows = get_logs(message.chat.id, 15)
    if not rows:
        await message.reply("📭 Логов пока нет")
        return

    text = "📜 <b>Последние действия:</b>\n\n"
    for admin_id, target_id, action, reason, dt in rows:
        text += f"• <b>{action}</b> — admin <code>{admin_id}</code> → цель <code>{target_id}</code>\n"

    await message.reply(text, parse_mode="HTML")


# ==================== /top ====================
@dp.message_handler(commands=["top"])
async def cmd_top(message: types.Message):
    if message.chat.type == "private":
        return

    rows = get_top_reps(message.chat.id, 10)
    if not rows:
        await message.reply("📭 Пока нет данных")
        return

    text = "🏆 <b>Топ по репутации:</b>\n\n"
    for i, (name, reps) in enumerate(rows, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {name or 'Аноним'} — <b>{reps}</b> ⭐\n"

    await message.reply(text, parse_mode="HTML")


# ==================== /admins ====================
@dp.message_handler(commands=["admins"])
async def cmd_admins(message: types.Message):
    if message.chat.type == "private":
        return

    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        text = "👮 <b>Админы чата:</b>\n\n"
        for a in admins:
            u = a.user
            tag = "👑" if a.status == "creator" else "🛡"
            text += f"{tag} {u.full_name}"
            if u.username:
                text += f" (@{u.username})"
            text += "\n"
        await message.reply(text, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ==================== ЗАПУСК ====================
async def on_startup(dp):
    init_db()
    me = await bot.get_me()
    print(f"🛡 {BOT_NAME} запущен")
    print(f"🤖 Username: @{me.username}")
    print(f"👑 ADMIN_ID: {ADMIN_ID}")


if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
