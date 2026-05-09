from aiogram.fsm.state import State, StatesGroup


class RegistrationFSM(StatesGroup):
    waiting_language = State()
    waiting_phone = State()
    waiting_city = State()
    waiting_gender = State()
    waiting_full_name = State()
    waiting_confirm = State()
