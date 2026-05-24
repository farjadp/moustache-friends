import asyncio
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from app.config import settings
from app.database import init_db
from bot.handlers import (
    handle_mention,
    handle_private_message,
    cmd_start,
    cmd_help,
    cmd_list_docs,
    cmd_delete_doc,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    app = Application.builder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list_docs))
    app.add_handler(CommandHandler("delete", cmd_delete_doc))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & filters.Entity("mention"),
        handle_mention
    ))

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Document.ALL | filters.AUDIO | filters.VIDEO | filters.VOICE)
        & filters.ChatType.PRIVATE,
        handle_private_message
    ))

    logger.info("Bot is starting...")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
