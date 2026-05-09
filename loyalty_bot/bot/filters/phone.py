import re
from typing import Optional, Union

from aiogram.filters import BaseFilter
from aiogram.types import Message

# Узбекистан: +998 + 9 цифр; РФ: +7 + 10 цифр.
PHONE_RE = re.compile(r"^\+(998\d{9}|7\d{10})$")


def normalize_phone(raw: str) -> Optional[str]:
    """Приводим номер к E.164. None — формат не наш."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    # 8XXXXXXXXXX → +7XXXXXXXXXX
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    # Узбекские мобильные без кода страны (9XXXXXXXX)
    if len(digits) == 9 and digits.startswith("9"):
        digits = "998" + digits

    candidate = "+" + digits
    return candidate if PHONE_RE.match(candidate) else None


class PhoneFilter(BaseFilter):
    """
    Принимает Message с .contact или валидным номером в .text.
    Возвращает в data:
      - phone: нормализованный номер (E.164)
      - verified: True только если контакт пришёл через кнопку "Поделиться"
        и contact.user_id == from_user.id (Telegram-верифицированный номер).
    """

    async def __call__(self, message: Message) -> Union[bool, dict]:
        raw: Optional[str] = None
        verified = False

        if message.contact and message.contact.phone_number:
            raw = message.contact.phone_number
            if not raw.startswith("+"):
                raw = "+" + raw
            # Контакт верифицирован, только если это СВОЙ номер отправителя.
            # Если переслали чужой контакт — contact.user_id будет другой.
            verified = message.contact.user_id == message.from_user.id
        elif message.text:
            raw = message.text.strip()

        normalized = normalize_phone(raw or "")
        if normalized is None:
            return False
        return {"phone": normalized, "verified": verified}
