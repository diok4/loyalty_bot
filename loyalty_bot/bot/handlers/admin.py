from decimal import Decimal, InvalidOperation
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.filters.phone import normalize_phone
from loyalty_bot.bot.keyboards.inline import (
    admin_cancel_kb,
    admin_confirm_kb,
    admin_panel_kb,
)
from loyalty_bot.bot.keyboards.reply import ADMIN_BTN_TEXTS, main_menu_kb
from loyalty_bot.bot.states.admin import AdminFSM
from loyalty_bot.core.exceptions import InsufficientBonusesError
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import LoyaltyCard, User
from loyalty_bot.domain.repositories import CardRepository, UserRepository
from loyalty_bot.services.admin_auth import AdminAuth
from loyalty_bot.services.barcode_service import BarcodeService
from loyalty_bot.services.card_service import CardService

router = Router(name="admin")
logger = get_logger(__name__)


def _build_card_service(session: AsyncSession) -> CardService:
    return CardService(CardRepository(session), BarcodeService())


# ---------- открытие админ-панели по reply-кнопке ----------

@router.message(F.text.in_(ADMIN_BTN_TEXTS))
async def open_admin_panel(
    message: Message, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        return  # молча игнорируем
    await state.clear()
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_panel_kb())


# ---------- статистика ----------

@router.callback_query(F.data == "admin:stats")
async def on_admin_stats(
    call: CallbackQuery, session: AsyncSession, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    users_total = await session.scalar(select(func.count(User.id)))
    cards_total = await session.scalar(select(func.count(LoyaltyCard.id)))
    bonuses_total = await session.scalar(
        select(func.coalesce(func.sum(LoyaltyCard.bonus_balance), 0))
    )

    await call.message.edit_text(
        "📊 <b>Статистика</b>\n"
        f"👥 Пользователей: <b>{users_total}</b>\n"
        f"💳 Карт: <b>{cards_total}</b>\n"
        f"💰 Сумма бонусов: <b>{bonuses_total}</b>",
        reply_markup=admin_panel_kb(),
    )
    await call.answer()


# ---------- начисление / списание ----------

@router.callback_query(F.data.in_({"admin:accrue", "admin:redeem"}))
async def on_admin_action(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    action = call.data.split(":", 1)[1]
    await state.set_state(AdminFSM.waiting_phone)
    await state.update_data(action=action)

    title = "Начисление" if action == "accrue" else "Списание"
    await call.message.edit_text(
        f"<b>{title} бонусов</b>\n\nОтправьте телефон клиента (+998… или +7…):",
        reply_markup=admin_cancel_kb(),
    )
    await call.answer()


@router.message(AdminFSM.waiting_phone)
async def on_admin_phone(
    message: Message, state: FSMContext, session: AsyncSession, is_admin: bool
) -> None:
    if not is_admin:
        return

    phone = normalize_phone(message.text or "")
    if phone is None:
        await message.answer(
            "❌ Неверный формат. Пример: +998901234567",
            reply_markup=admin_cancel_kb(),
        )
        return

    user = await UserRepository(session).get_by_phone(phone)
    if not user or not user.card:
        await message.answer(
            f"❌ Пользователь {phone} не найден или без карты.",
            reply_markup=admin_cancel_kb(),
        )
        return

    await state.update_data(
        phone=phone,
        user_id=str(user.id),
        card_id=str(user.card.id),
        card_number=user.card.card_number,
        full_name=user.full_name,
        current_balance=str(user.card.bonus_balance),
    )
    await state.set_state(AdminFSM.waiting_amount)

    data = await state.get_data()
    title = "начисления" if data["action"] == "accrue" else "списания"
    await message.answer(
        f"👤 <b>{user.full_name}</b>\n"
        f"💳 <code>{user.card.card_number}</code>\n"
        f"💰 Баланс: <b>{user.card.bonus_balance}</b>\n\n"
        f"Введите сумму {title} (число > 0):",
        reply_markup=admin_cancel_kb(),
    )


@router.message(AdminFSM.waiting_amount)
async def on_admin_amount(
    message: Message, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        return

    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer(
            "❌ Сумма должна быть положительным числом.",
            reply_markup=admin_cancel_kb(),
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AdminFSM.waiting_confirm)

    data = await state.get_data()
    verb = "Начислить" if data["action"] == "accrue" else "Списать"
    sign = "+" if data["action"] == "accrue" else "−"
    await message.answer(
        f"<b>Подтвердите операцию:</b>\n\n"
        f"👤 {data['full_name']}\n"
        f"💳 <code>{data['card_number']}</code>\n"
        f"{verb}: <b>{sign}{amount}</b>\n"
        f"Баланс до: {data['current_balance']}",
        reply_markup=admin_confirm_kb(),
    )


@router.callback_query(AdminFSM.waiting_confirm, F.data == "admin:confirm")
async def on_admin_confirm(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    is_admin: bool,
) -> None:
    if not is_admin:
        await call.answer()
        return

    data = await state.get_data()
    card_id = UUID(data["card_id"])
    amount = Decimal(data["amount"])
    action = data["action"]

    service = _build_card_service(session)
    try:
        if action == "accrue":
            await service.accrue(card_id, amount, description="manual admin")
            verb = "начислено"
        else:
            await service.redeem(card_id, amount, description="manual admin")
            verb = "списано"
    except InsufficientBonusesError as e:
        await call.message.edit_text(
            f"❌ Недостаточно бонусов: {e.available} < {e.requested}",
            reply_markup=admin_panel_kb(),
        )
        await state.clear()
        await call.answer()
        return

    repo = CardRepository(session)
    card = await repo.get(card_id)

    await state.clear()
    await call.message.edit_text(
        f"✅ Успешно {verb} <b>{amount}</b>\n"
        f"💳 <code>{data['card_number']}</code>\n"
        f"💰 Новый баланс: <b>{card.bonus_balance if card else '—'}</b>",
        reply_markup=admin_panel_kb(),
    )
    await call.answer("Готово")


# ---------- закрыть / отменить ----------

@router.callback_query(F.data == "admin:cancel")
async def on_admin_cancel(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("🛠 Закрыто. Откройте «🛠 Админ» при необходимости.")
    await call.answer()


# ---------- выход из админки ----------

@router.callback_query(F.data == "admin:logout")
async def on_admin_logout(
    call: CallbackQuery,
    state: FSMContext,
    auth: AdminAuth,
    session: AsyncSession,
) -> None:
    # Не проверяем is_admin — если уже не админ, всё равно очищаем сессию.
    await auth.logout(call.from_user.id)
    await state.clear()

    user = await UserRepository(session).get_by_telegram_id(call.from_user.id)
    lang = user.language if user else "ru"

    await call.message.edit_text("🚪 Вы вышли из админ-режима.")
    await call.message.answer(
        "Меню обновлено.",
        reply_markup=main_menu_kb(lang, is_admin=False),
    )
    await call.answer()
