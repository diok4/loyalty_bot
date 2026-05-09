from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.keyboards.inline import language_kb
from loyalty_bot.bot.keyboards.reply import main_menu_kb, phone_request_kb
from loyalty_bot.bot.states.registration import RegistrationFSM
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import UserRepository

router = Router(name="start")
logger = get_logger(__name__)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    is_admin: bool,
) -> None:
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(message.from_user.id)

    if user and user.card:
        await message.answer(
            f"С возвращением, {user.full_name}! 👋",
            reply_markup=main_menu_kb(user.language, is_admin=is_admin),
        )
        if user.card.barcode_path:
            await message.answer_photo(
                FSInputFile(user.card.barcode_path),
                caption=(
                    f"💳 Карта: <code>{user.card.card_number}</code>\n"
                    f"💰 Баланс: <b>{user.card.bonus_balance}</b>"
                ),
                parse_mode="HTML",
            )
        return

    await state.clear()
    await state.set_state(RegistrationFSM.waiting_language)
    await message.answer(
        "Добро пожаловать! Выберите язык / Tilni tanlang:",
        reply_markup=language_kb(),
    )


@router.callback_query(RegistrationFSM.waiting_language, lambda c: c.data and c.data.startswith("lang:"))
async def on_language(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split(":", 1)[1]
    await state.update_data(language=lang)
    await state.set_state(RegistrationFSM.waiting_phone)

    text = {
        "ru": "Поделитесь номером телефона или введите вручную (+998…/+7…):",
        "uz": "Telefon raqamingizni yuboring yoki qo'lda kiriting (+998…/+7…):",
    }[lang]
    btn = {"ru": "📱 Поделиться контактом", "uz": "📱 Kontaktni yuborish"}[lang]
    await call.message.answer(text, reply_markup=phone_request_kb(btn))
    await call.answer()
