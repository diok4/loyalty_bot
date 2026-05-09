from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from loyalty_bot.domain.models import City


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
        ]]
    )


def cities_kb(cities: Sequence[City]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=c.name, callback_data=f"city:{c.id}")]
        for c in cities
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gender_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {"ru": ("Мужской", "Женский"), "uz": ("Erkak", "Ayol")}[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=labels[0], callback_data="gender:male"),
            InlineKeyboardButton(text=labels[1], callback_data="gender:female"),
        ]]
    )


def confirm_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": ("✅ Подтвердить", "✏️ Изменить"),
        "uz": ("✅ Tasdiqlash", "✏️ O'zgartirish"),
    }[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=labels[0], callback_data="reg:confirm"),
            InlineKeyboardButton(text=labels[1], callback_data="reg:restart"),
        ]]
    )


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="➕ Начислить бонусы", callback_data="admin:accrue")],
        [InlineKeyboardButton(text="➖ Списать бонусы", callback_data="admin:redeem")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:notify")],
        [InlineKeyboardButton(text="🚪 Выйти из админки", callback_data="admin:logout")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:cancel")],
    ])


def notify_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая рассылка", callback_data="notify:new")],
        [InlineKeyboardButton(text="📋 История рассылок", callback_data="notify:history")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
    ])


def notify_when_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить сейчас", callback_data="notify:when:now")],
        [InlineKeyboardButton(text="🕐 Запланировать", callback_data="notify:when:later")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="notify:cancel")],
    ])


def notify_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Отправить", callback_data="notify:confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="notify:cancel"),
    ]])


def notify_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:notify"),
    ]])


def admin_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")],
    ])


def admin_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin:confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel"),
    ]])
