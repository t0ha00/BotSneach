from aiogram.utils.helper import Helper, HelperMode, ListItem


class UserStates(Helper):
    mode = HelperMode.snake_case

    USER_STATE_0 = ListItem()