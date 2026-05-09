from aiogram.fsm.state import State, StatesGroup


class NotificationFSM(StatesGroup):
    """Создание новой рассылки админом."""
    waiting_text = State()
    waiting_when = State()       # сейчас или запланировать
    waiting_datetime = State()   # ввод даты/времени (Asia/Tashkent)
    waiting_confirm = State()
