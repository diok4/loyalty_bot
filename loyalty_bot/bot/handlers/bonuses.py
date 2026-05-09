from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import CardRepository, UserRepository

router = Router(name="bonuses")
logger = get_logger(__name__)


@router.message(F.text.in_({"💰 Баланс", "💰 Balans"}))
async def show_balance(message: Message, session: AsyncSession) -> None:
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user or not user.card:
        await message.answer("Карта не найдена. Отправьте /start.")
        return

    txs = await CardRepository(session).list_transactions(user.card.id, limit=10)
    history_lines = ["📜 <b>Последние операции:</b>"]
    if not txs:
        history_lines.append("— пока нет —")
    else:
        for tx in txs:
            sign = "+" if tx.type == "accrual" else "−"
            history_lines.append(
                f"{tx.created_at:%d.%m.%Y} {sign}{tx.amount} "
                f"({tx.description or tx.type})"
            )

    await message.answer(
        f"💰 <b>{user.card.bonus_balance}</b> бонусов\n\n" + "\n".join(history_lines),
        parse_mode="HTML",
    )
