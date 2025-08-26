from __future__ import annotations

from telegram import Bot

from bot.constants import YELLOW_FILE_ID, VIDEO_FILE_ID
from bot.keyboards import MENU_KB


INSTRUCTION_TEXT: str = (
    "Итак, первым делом тебе нужно создать новый профиль в Instagram — это наш фундамент.\n\n"
    "Аватар — возьми мой жёлтый цвет (см. фото выше). Позже, достигнув целей, "
    "сможешь заменить аватар на свой.\n\n"
    "Имя профиля — сделай понятным, связанным с нашим контентом (например, @creatorofmotivation).\n"
    "Описание — добавь «упаковку» (пример: заряжайся мотивацией каждый день).\n\n"
    "И последнее — переключи аккаунт с личного на профессиональный, чтобы видеть статистику.\n"
    "Нажми кнопку ниже, чтобы получить инструкцию."
)


async def send_instruction_package(bot: Bot, user_id: int) -> None:

    await bot.send_photo(chat_id=user_id, photo=YELLOW_FILE_ID)
    await bot.send_message(chat_id=user_id, text=INSTRUCTION_TEXT, reply_markup=MENU_KB)
    await bot.send_video(chat_id=user_id, video=VIDEO_FILE_ID)
