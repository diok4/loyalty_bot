import re
from typing import Any, Dict

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.filters.phone import PhoneFilter
from loyalty_bot.bot.keyboards.inline import cities_kb, confirm_kb, gender_kb
from loyalty_bot.bot.keyboards.reply import REMOVE, main_menu_kb, phone_request_kb
from loyalty_bot.bot.states.registration import RegistrationFSM
from loyalty_bot.core.exceptions import UserAlreadyExistsError
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import (
    CardRepository,
    CityRepository,
    UserRepository,
)
from loyalty_bot.domain.schemas import UserCreate
from loyalty_bot.services.barcode_service import BarcodeService
from loyalty_bot.services.bitrix_service import BitrixService
from loyalty_bot.services.card_service import CardService
from loyalty_bot.services.user_service import UserService

router = Router(name="registration")
logger = get_logger(__name__)

NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ' \-]{2,50}$")


def _build_user_service(session: AsyncSession) -> UserService:
    user_repo = UserRepository(session)
    card_repo = CardRepository(session)
    barcode = BarcodeService()
    card_service = CardService(card_repo, barcode)
    bitrix = BitrixService()
    return UserService(user_repo, card_service, bitrix)


@router.message(RegistrationFSM.waiting_phone, PhoneFilter())
async def on_phone(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    phone: str,
    verified: bool,
    is_admin: bool,
) -> None:
    user_repo = UserRepository(session)
    existing = await user_repo.get_by_phone(phone)

    if existing and existing.card:
        same_tg = existing.telegram_id == message.from_user.id

        # Чужой Telegram пытается войти под существующим номером — пропускаем
        # ТОЛЬКО если контакт пришёл через кнопку "Поделиться" (Telegram сам
        # прикрепил реальный номер отправителя). Это блокирует угон по
        # ручному вводу чужого телефона.
        if not same_tg and not verified:
            logger.warning(
                "relink_attempt_blocked",
                phone=phone,
                attacker_tg_id=message.from_user.id,
                victim_user_id=str(existing.id),
            )
            await message.answer(
                "🔒 Этот номер уже зарегистрирован.\n\n"
                "Чтобы войти под ним, нажмите кнопку "
                "<b>«📱 Поделиться контактом»</b> — Telegram подтвердит, что "
                "номер действительно ваш. Ручной ввод чужого номера не "
                "принимается из соображений безопасности.",
                reply_markup=phone_request_kb(),
                parse_mode="HTML",
            )
            return

        # same_tg == True — обычный возврат. same_tg == False + verified —
        # переустановка Telegram, перепривязываем.
        if not same_tg:
            existing.telegram_id = message.from_user.id
            await session.flush()
            logger.info(
                "telegram_id_relinked",
                user_id=str(existing.id),
                new_tg_id=message.from_user.id,
            )

        await state.clear()
        await message.answer(
            f"С возвращением, {existing.full_name}! 👋",
            reply_markup=main_menu_kb(existing.language, is_admin=is_admin),
        )
        if existing.card.barcode_path:
            await message.answer_photo(
                FSInputFile(existing.card.barcode_path),
                caption=(
                    f"💳 <code>{existing.card.card_number}</code>\n"
                    f"💰 Баланс: <b>{existing.card.bonus_balance}</b>"
                ),
                parse_mode="HTML",
            )
        return

    await state.update_data(phone=phone)
    await state.set_state(RegistrationFSM.waiting_city)

    cities = await CityRepository(session).get_all()
    if not cities:
        await message.answer("⚠️ Список городов пуст. Обратитесь к администратору.")
        await state.clear()
        return

    await message.answer("Спасибо!", reply_markup=REMOVE)
    await message.answer("🏙 Выберите город:", reply_markup=cities_kb(cities))


@router.message(RegistrationFSM.waiting_phone)
async def on_phone_invalid(message: Message) -> None:
    await message.answer(
        "❌ Неверный формат. Введите номер: +998XXXXXXXXX или +7XXXXXXXXXX"
    )


@router.callback_query(RegistrationFSM.waiting_city, F.data.startswith("city:"))
async def on_city(call: CallbackQuery, state: FSMContext) -> None:
    city_id = int(call.data.split(":", 1)[1])
    await state.update_data(city_id=city_id)
    await state.set_state(RegistrationFSM.waiting_gender)
    data = await state.get_data()
    await call.message.edit_text(
        "👤 Укажите пол:", reply_markup=gender_kb(data.get("language", "ru"))
    )
    await call.answer()


@router.callback_query(RegistrationFSM.waiting_gender, F.data.startswith("gender:"))
async def on_gender(call: CallbackQuery, state: FSMContext) -> None:
    gender = call.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    await state.set_state(RegistrationFSM.waiting_full_name)
    await call.message.edit_text("✏️ Введите ваше имя (2–50 символов):")
    await call.answer()


@router.message(RegistrationFSM.waiting_full_name)
async def on_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not NAME_RE.match(name):
        await message.answer("❌ Имя должно быть 2–50 символов, только буквы.")
        return

    await state.update_data(full_name=name)
    await state.set_state(RegistrationFSM.waiting_confirm)

    data = await state.get_data()
    summary = (
        "<b>Проверьте данные:</b>\n"
        f"👤 Имя: {data['full_name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🏙 Город ID: {data['city_id']}\n"
        f"⚥ Пол: {data['gender']}\n"
        f"🌐 Язык: {data['language']}"
    )
    await message.answer(
        summary,
        parse_mode="HTML",
        reply_markup=confirm_kb(data.get("language", "ru")),
    )


@router.callback_query(RegistrationFSM.waiting_confirm, F.data == "reg:restart")
async def on_restart(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "Регистрация отменена. Отправьте /start чтобы начать заново."
    )
    await call.answer()


@router.callback_query(RegistrationFSM.waiting_confirm, F.data == "reg:confirm")
async def on_confirm(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    is_admin: bool,
) -> None:
    data: Dict[str, Any] = await state.get_data()
    payload = UserCreate(
        telegram_id=call.from_user.id,
        phone=data["phone"],
        full_name=data["full_name"],
        gender=data["gender"],
        city_id=data["city_id"],
        language=data.get("language", "ru"),
    )

    service = _build_user_service(session)
    try:
        user = await service.register(payload)
    except UserAlreadyExistsError:
        await call.message.edit_text("⚠️ Этот номер уже зарегистрирован.")
        await state.clear()
        await call.answer()
        return

    await state.clear()
    card = user.card  # подгружено через selectinload в репозитории
    await call.message.edit_text(
        f"🎉 Регистрация завершена!\n💳 Номер карты: <code>{card.card_number}</code>",
        parse_mode="HTML",
    )
    if card.barcode_path:
        await call.message.answer_photo(
            FSInputFile(card.barcode_path),
            caption="Покажите этот штрихкод на кассе.",
            reply_markup=main_menu_kb(payload.language, is_admin=is_admin),
        )
    await call.answer("Готово!")
