from decimal import Decimal
from typing import Optional

import httpx

from loyalty_bot.core.config import settings
from loyalty_bot.core.exceptions import BitrixError
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.schemas import UserRead

logger = get_logger(__name__)

BITRIX_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class BitrixService:
    """
    Заглушка интеграции с Bitrix24.

    Когда подключите — структура запросов соответствует REST-методам:
      https://apidocs.bitrix24.com/api-reference/crm/contacts/index.html
    """

    def __init__(self, webhook_url: str = settings.BITRIX_WEBHOOK_URL) -> None:
        self.webhook_url = webhook_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=BITRIX_TIMEOUT)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def create_contact(
        self, user: UserRead, card_number: str
    ) -> Optional[str]:
        """Создание контакта в Bitrix24 → возвращает bitrix_contact_id."""
        if not settings.BITRIX_ENABLED:
            logger.info("bitrix_disabled", action="create_contact", user_id=str(user.id))
            return None

        payload = {
            "fields": {
                "NAME": user.full_name or "",
                "PHONE": [{"VALUE": user.phone, "VALUE_TYPE": "MOBILE"}],
                "UF_CARD_NUMBER": card_number,
                "UF_TELEGRAM_ID": user.telegram_id,
            },
            "params": {"REGISTER_SONET_EVENT": "Y"},
        }

        try:
            client = await self._http()
            response = await client.post(
                f"{self.webhook_url}/crm.contact.add.json", json=payload
            )
            response.raise_for_status()
            data = response.json()
            contact_id = str(data.get("result", ""))
            logger.info(
                "bitrix_contact_created",
                user_id=str(user.id),
                contact_id=contact_id,
            )
            return contact_id or None
        except httpx.HTTPError as exc:
            logger.exception("bitrix_create_contact_failed", user_id=str(user.id))
            raise BitrixError(str(exc)) from exc

    async def sync_bonuses(
        self, contact_id: str, card_number: str, balance: Decimal
    ) -> bool:
        """Обновление UF_BONUS_BALANCE контакта."""
        if not settings.BITRIX_ENABLED:
            logger.info(
                "bitrix_disabled", action="sync_bonuses", card_number=card_number
            )
            return False

        payload = {
            "id": contact_id,
            "fields": {
                "UF_BONUS_BALANCE": str(balance),
                "UF_CARD_NUMBER": card_number,
            },
        }

        try:
            client = await self._http()
            response = await client.post(
                f"{self.webhook_url}/crm.contact.update.json", json=payload
            )
            response.raise_for_status()
            ok = bool(response.json().get("result"))
            logger.info(
                "bitrix_bonuses_synced",
                contact_id=contact_id,
                balance=str(balance),
                ok=ok,
            )
            return ok
        except httpx.HTTPError as exc:
            logger.exception("bitrix_sync_bonuses_failed", contact_id=contact_id)
            raise BitrixError(str(exc)) from exc
