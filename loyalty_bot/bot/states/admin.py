from aiogram.fsm.state import State, StatesGroup


class AdminFSM(StatesGroup):
    """Универсальный FSM для админ-операций над бонусами.
    В data хранится action: 'accrue' | 'redeem'."""
    waiting_phone = State()
    waiting_amount = State()
    waiting_confirm = State()
