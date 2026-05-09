from aiogram import F, Router
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import UserRepository

router = Router(name="card")
logger = get_logger(__name__)


@router.message(F.text.in_({"💳 Моя карта", "💳 Mening kartam"}))
async def show_card(message: Message, session: AsyncSession) -> None:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user or not user.card:
        await message.answer("Карта не найдена. Отправьте /start для регистрации.")
        return

    card = user.card
    caption = (
        f"💳 <b>{card.card_number}</b>\n"
        f"👤 {user.full_name}\n"
        f"💰 Баланс: <b>{card.bonus_balance}</b>"
    )
    if card.barcode_path:
        await message.answer_photo(
            FSInputFile(card.barcode_path), caption=caption, parse_mode="HTML"
        )
    else:
        await message.answer(caption, parse_mode="HTML")
