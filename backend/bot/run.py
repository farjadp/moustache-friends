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
    cmd_sync_drive,
)
from app.rag.drive_sync import start_drive_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await init_db()
    logger.info("Database initialized. Bot is ready.")
    if settings.google_drive_folder_id and settings.google_service_account_json:
        admin_ids = settings.admin_ids
        notify_id = admin_ids[0] if admin_ids else None
        asyncio.create_task(start_drive_scheduler(app.bot, notify_id))
        logger.info("Google Drive scheduler started.")


def main():
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list_docs))
    app.add_handler(CommandHandler("delete", cmd_delete_doc))
    app.add_handler(CommandHandler("sync_drive", cmd_sync_drive))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & filters.Entity("mention"),
        handle_mention
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & filters.REPLY,
        handle_mention
    ))

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Document.ALL | filters.AUDIO | filters.VIDEO | filters.VOICE)
        & filters.ChatType.PRIVATE,
        handle_private_message
    ))

    logger.info("Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
