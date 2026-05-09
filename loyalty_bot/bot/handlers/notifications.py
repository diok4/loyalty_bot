from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.bot.keyboards.inline import (
    admin_panel_kb,
    notify_back_kb,
    notify_confirm_kb,
    notify_panel_kb,
    notify_when_kb,
)
from loyalty_bot.bot.states.notifications import NotificationFSM
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.repositories import NotificationRepository
from loyalty_bot.services.notification_service import (
    NotificationBroadcaster,
    trigger_immediate,
)

router = Router(name="notifications")
logger = get_logger(__name__)

# Время админ вводит в локальной зоне Ташкента, в БД храним UTC.
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
DT_FORMAT = "%d.%m.%Y %H:%M"

STATUS_LABELS = {
    "pending": "⏳ Ждёт",
    "sending": "📤 Идёт",
    "sent": "✅ Отправлено",
    "failed": "❌ Сбой",
}


def _parse_local_datetime(raw: str) -> Optional[datetime]:
    """'15.05.2026 18:30' (Ташкент) → UTC-aware datetime."""
    try:
        naive = datetime.strptime(raw.strip(), DT_FORMAT)
    except ValueError:
        return None
    return naive.replace(tzinfo=TASHKENT_TZ).astimezone(timezone.utc)


def _fmt_local(dt: datetime) -> str:
    return dt.astimezone(TASHKENT_TZ).strftime(DT_FORMAT)


# ---------- открыть панель рассылок ----------

@router.callback_query(F.data == "admin:notify")
async def open_notify_panel(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("📢 <b>Рассылки</b>", reply_markup=notify_panel_kb())
    await call.answer()


@router.callback_query(F.data == "admin:back")
async def back_to_admin(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=admin_panel_kb())
    await call.answer()


# ---------- история рассылок ----------

@router.callback_query(F.data == "notify:history")
async def show_history(
    call: CallbackQuery, session: AsyncSession, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    items = await NotificationRepository(session).list_recent(limit=10)
    if not items:
        text_body = "📋 <b>История</b>\n\nПока нет рассылок."
    else:
        lines = ["📋 <b>История рассылок</b>", ""]
        for n in items:
            preview = n.text_body[:50].replace("\n", " ")
            if len(n.text_body) > 50:
                preview += "…"
            label = STATUS_LABELS.get(n.status, n.status)
            stats = ""
            if n.status == "sent":
                stats = f" (✓{n.sent_count}/✗{n.failed_count})"
            lines.append(
                f"{label} <i>{_fmt_local(n.scheduled_at)}</i>{stats}\n"
                f"   {preview}"
            )
        text_body = "\n".join(lines)

    await call.message.edit_text(text_body, reply_markup=notify_back_kb())
    await call.answer()


# ---------- создание новой рассылки ----------

@router.callback_query(F.data == "notify:new")
async def start_new(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    await state.set_state(NotificationFSM.waiting_text)
    await call.message.edit_text(
        "📝 Отправьте текст рассылки.\n\n"
        "Можно использовать HTML-теги: <code>&lt;b&gt;</code>, "
        "<code>&lt;i&gt;</code>, <code>&lt;a href&gt;</code>.",
    )
    await call.answer()


@router.message(NotificationFSM.waiting_text)
async def on_text(
    message: Message, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        return

    text_body = (message.text or "").strip()
    if len(text_body) < 1:
        await message.answer("❌ Текст пустой. Попробуйте ещё раз.")
        return
    if len(text_body) > 4000:
        await message.answer("❌ Слишком длинно. Максимум 4000 символов.")
        return

    await state.update_data(text_body=text_body)
    await state.set_state(NotificationFSM.waiting_when)
    await message.answer(
        "🕐 Когда отправить?",
        reply_markup=notify_when_kb(),
    )


@router.callback_query(NotificationFSM.waiting_when, F.data == "notify:when:now")
async def on_when_now(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    now_utc = datetime.now(timezone.utc)
    await state.update_data(scheduled_at=now_utc.isoformat())
    await state.set_state(NotificationFSM.waiting_confirm)
    await _show_preview(call, state)


@router.callback_query(NotificationFSM.waiting_when, F.data == "notify:when:later")
async def on_when_later(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return

    await state.set_state(NotificationFSM.waiting_datetime)
    now_local = datetime.now(TASHKENT_TZ).strftime(DT_FORMAT)
    await call.message.edit_text(
        "📅 Введите дату и время по Ташкенту в формате:\n"
        f"<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        f"Сейчас: <code>{now_local}</code>",
    )
    await call.answer()


@router.message(NotificationFSM.waiting_datetime)
async def on_datetime(
    message: Message, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        return

    parsed = _parse_local_datetime(message.text or "")
    if parsed is None:
        await message.answer("❌ Не понял формат. Пример: <code>15.05.2026 18:30</code>")
        return

    if parsed <= datetime.now(timezone.utc):
        await message.answer("❌ Время должно быть в будущем.")
        return

    await state.update_data(scheduled_at=parsed.isoformat())
    await state.set_state(NotificationFSM.waiting_confirm)
    await _show_preview_message(message, state)


async def _show_preview(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    scheduled = datetime.fromisoformat(data["scheduled_at"])
    when_str = (
        "🚀 <b>сейчас</b>"
        if (scheduled - datetime.now(timezone.utc)).total_seconds() < 60
        else f"🕐 <b>{_fmt_local(scheduled)}</b> (Ташкент)"
    )
    await call.message.edit_text(
        f"<b>Подтвердите рассылку</b>\n\n"
        f"Когда: {when_str}\n\n"
        f"<b>Текст:</b>\n{data['text_body']}",
        reply_markup=notify_confirm_kb(),
    )
    await call.answer()


async def _show_preview_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    scheduled = datetime.fromisoformat(data["scheduled_at"])
    when_str = f"🕐 <b>{_fmt_local(scheduled)}</b> (Ташкент)"
    await message.answer(
        f"<b>Подтвердите рассылку</b>\n\n"
        f"Когда: {when_str}\n\n"
        f"<b>Текст:</b>\n{data['text_body']}",
        reply_markup=notify_confirm_kb(),
    )


@router.callback_query(NotificationFSM.waiting_confirm, F.data == "notify:confirm")
async def on_confirm(
    call: CallbackQuery,
    state: FSMContext,
    broadcaster: NotificationBroadcaster,
    is_admin: bool,
) -> None:
    if not is_admin:
        await call.answer()
        return

    data = await state.get_data()
    scheduled = datetime.fromisoformat(data["scheduled_at"])
    text_body = data["text_body"]

    notif = await broadcaster.schedule(
        text_body=text_body,
        scheduled_at=scheduled,
        created_by_tg_id=call.from_user.id,
    )

    await state.clear()

    is_now = (scheduled - datetime.now(timezone.utc)).total_seconds() < 60
    if is_now:
        trigger_immediate(broadcaster)
        msg = "🚀 Рассылка запущена. Доставка пойдёт сейчас."
    else:
        msg = f"📅 Рассылка запланирована на <b>{_fmt_local(scheduled)}</b> (Ташкент)."

    await call.message.edit_text(
        f"{msg}\n\nID: <code>{notif.id}</code>",
        reply_markup=notify_panel_kb(),
    )
    await call.answer("Готово")


@router.callback_query(F.data == "notify:cancel")
async def on_cancel(
    call: CallbackQuery, state: FSMContext, is_admin: bool
) -> None:
    if not is_admin:
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("📢 <b>Рассылки</b>", reply_markup=notify_panel_kb())
    await call.answer()
