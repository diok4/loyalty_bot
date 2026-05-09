from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.keyboards.reply import PROFILE_BTN_TEXTS
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import UserRepository

router = Router(name="profile")
logger = get_logger(__name__)

GENDER_LABELS = {"male": "Мужской", "female": "Женский"}


@router.message(F.text.in_(PROFILE_BTN_TEXTS))
async def show_profile(message: Message, session: AsyncSession) -> None:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден. Отправьте /start.")
        return

    city_name = user.city.name if user.city else "—"
    await message.answer(
        "<b>👤 Ваш профиль</b>\n\n"
        f"Имя: <b>{user.full_name or '—'}</b>\n"
        f"Телефон: <code>{user.phone}</code>\n"
        f"Город: {city_name}\n"
        f"Пол: {GENDER_LABELS.get(user.gender or '', '—')}\n"
        f"Язык: {user.language.upper()}\n"
        f"Регистрация: {user.created_at:%d.%m.%Y}",
        parse_mode="HTML",
    )
