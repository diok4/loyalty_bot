from contextlib import suppress

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.keyboards.reply import main_menu_kb
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import UserRepository
from loyalty_bot.services.admin_auth import AdminAuth

router = Router(name="auth")
logger = get_logger(__name__)


@router.message(Command("login"))
async def login_admin(
    message: Message,
    command: CommandObject,
    auth: AdminAuth,
    session: AsyncSession,
) -> None:
    """/login <логин> <пароль> — вход в админ-режим."""

    # Удаляем сообщение с паролем СРАЗУ, чтобы не светить креды в чате.
    # Делаем это до проверки — даже при неуспехе пароль не должен висеть.
    with suppress(Exception):
        await message.delete()

    if not command.args:
        await message.answer(
            "Использование: <code>/login &lt;логин&gt; &lt;пароль&gt;</code>"
        )
        return

    parts = command.args.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(
            "Использование: <code>/login &lt;логин&gt; &lt;пароль&gt;</code>"
        )
        return

    username, password = parts[0].strip(), parts[1].strip()
    ok = await auth.login(message.from_user.id, username, password)

    if not ok:
        await message.answer("❌ Неверные данные.")
        return

    # Берём язык из профиля если есть, иначе ru
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    lang = user.language if user else "ru"

    await message.answer(
        "✅ <b>Вход выполнен.</b>\n\n"
        "Сессия активна 24 часа. В меню появилась кнопка <b>🛠 Админ</b>.",
        reply_markup=main_menu_kb(lang, is_admin=True),
    )
