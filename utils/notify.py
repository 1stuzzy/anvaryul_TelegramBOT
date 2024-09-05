from asyncio import sleep

from aiogram.utils.exceptions import ChatNotFound, BotBlocked, CantInitiateConversation
from aiogram import Dispatcher
from loguru import logger

from loader import config


async def on_startup_notify(dp: Dispatcher):
    text = '<b>Bot Started 🚀</b>'

    logger.info("Admins notify...")
    for admin_id in config.admins_id:
        try:
            await dp.bot.send_message(admin_id, text, disable_notification=True)
            logger.opt(colors=True).info(
                f"Notify message send to admin: [<green>{admin_id}</green>]"
            )
        except ChatNotFound:
            logger.warning("Chat with admin not found.")
        except BotBlocked:
            logger.warning("Admin blocked bot.")
        except CantInitiateConversation:
            logger.warning(f"Cant initiate conversation with admin: [{admin_id}]")
        except Exception as ex:
            logger.error(f"Admins notify exception: {ex}")

        await sleep(0.1)