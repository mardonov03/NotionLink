from aiogram.fsm.state import State, StatesGroup

class UserStages(StatesGroup):
    start = State()
    token = State()
    link_selection = State()
    category_selection = State()
    new_category = State()
    get_category = State()
    yes_no = State()
