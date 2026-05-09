from decimal import Decimal


class LoyaltyBotError(Exception):
    """Корневое исключение приложения."""


class DomainError(LoyaltyBotError):
    """Нарушение бизнес-правил."""


class UserNotFoundError(DomainError):
    def __init__(self, identifier: str | int) -> None:
        super().__init__(f"User not found: {identifier}")
        self.identifier = identifier


class UserAlreadyExistsError(DomainError):
    def __init__(self, phone: str) -> None:
        super().__init__(f"User with phone {phone} already exists")
        self.phone = phone


class CardNotFoundError(DomainError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Loyalty card not found: {identifier}")
        self.identifier = identifier


class CardAlreadyExistsError(DomainError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"Card already exists for user {user_id}")
        self.user_id = user_id


class InvalidPhoneError(DomainError):
    def __init__(self, phone: str) -> None:
        super().__init__(f"Invalid phone format: {phone}")
        self.phone = phone


class InsufficientBonusesError(DomainError):
    def __init__(self, available: Decimal, requested: Decimal) -> None:
        super().__init__(
            f"Insufficient bonuses: available={available}, requested={requested}"
        )
        self.available = available
        self.requested = requested


class InfrastructureError(LoyaltyBotError):
    """Сбой внешней системы (БД, Redis, Bitrix, файловое хранилище)."""


class BitrixError(InfrastructureError):
    pass


class BarcodeGenerationError(InfrastructureError):
    pass
