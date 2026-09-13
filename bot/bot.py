from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, MenuButtonWebApp, Message, ReplyKeyboardMarkup, WebAppInfo

TOKEN = os.environ.get("BOT_TOKEN", "000000:changeme")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://localhost:8080")


def token_looks_real(token: str) -> bool:
    if not token or "changeme" in token or token.startswith("000000"):
        return False
    parts = token.split(":", 1)
    return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) > 20


async def idle() -> None:
    logging.warning(
        "BOT_TOKEN не задано або це заглушка — бот чекає. "
        "API і Mini App на %s уже доступні без Telegram.",
        WEBAPP_URL,
    )
    while True:
        await asyncio.sleep(3600)


async def run_bot() -> None:
    bot = Bot(TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Відкрити цілі", web_app=WebAppInfo(url=WEBAPP_URL))]],
            resize_keyboard=True,
        )
        await message.answer(
            "Цільник — спільні цілі команди: фриланс, будівництво, будь-який проєкт.\n\n"
            "Головний заводить ціль і закриває етапи після перевірки доказів.\n"
            "Виконавець ділить ціль на етапи з вагою % і завантажує фото/відео + примітку, що все працює.",
            reply_markup=kb,
        )
        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="Цілі", web_app=WebAppInfo(url=WEBAPP_URL)),
        )

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Цілі", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except Exception as exc:  # noqa: BLE001
        logging.warning("Menu button: %s", exc)

    logging.info("Бот запущено, WEBAPP_URL=%s", WEBAPP_URL)
    await dp.start_polling(bot)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not token_looks_real(TOKEN):
        await idle()
        return
    try:
        await run_bot()
    except Exception as exc:  # noqa: BLE001
        logging.error("Бот зупинився: %s. Чекаємо токен.", exc)
        await idle()


if __name__ == "__main__":
    asyncio.run(main())
