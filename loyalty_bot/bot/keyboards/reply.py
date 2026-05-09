from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

REMOVE = ReplyKeyboardRemove()


def phone_request_kb(text: str = "📱 Поделиться контактом") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb(lang: str = "ru", is_admin: bool = False) -> ReplyKeyboardMarkup:
    labels = {
        "ru": ["💳 Моя карта", "💰 Баланс", "👤 Профиль", "🛠 Админ"],
        "uz": ["💳 Mening kartam", "💰 Balans", "👤 Profil", "🛠 Admin"],
    }[lang]
    rows = [
        [KeyboardButton(text=labels[0])],
        [KeyboardButton(text=labels[1]), KeyboardButton(text=labels[2])],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=labels[3])])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# Тексты, которые проверяем в фильтрах (любой язык)
ADMIN_BTN_TEXTS = {"🛠 Админ", "🛠 Admin"}
CARD_BTN_TEXTS = {"💳 Моя карта", "💳 Mening kartam"}
BALANCE_BTN_TEXTS = {"💰 Баланс", "💰 Balans"}
PROFILE_BTN_TEXTS = {"👤 Профиль", "👤 Profil"}
