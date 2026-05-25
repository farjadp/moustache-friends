import os
import uuid
import logging
import aiofiles
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from app.rag.qa_chain import answer_question
from app.rag.file_processor import get_file_type, process_file
from app.rag.vector_store import add_documents, delete_document
from app.database import AsyncSessionLocal, Document, ChatLog
from app.config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    bot_username = context.bot.username
    if not bot_username:
        return

    mention = f"@{bot_username}"
    text = message.text
    bot_id = context.bot.id

    is_mention = mention.lower() in text.lower()
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user is not None
        and message.reply_to_message.from_user.id == bot_id
    )

    if not is_mention and not is_reply_to_bot:
        return

    question = text.replace(mention, "").replace(mention.lower(), "").strip()
    if not question:
        await message.reply_text("سوالت رو بنویس تا جواب بدم 😊")
        return

    user = message.from_user
    user_name = user.username or user.first_name or str(user.id)

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    try:
        answer, sources = await answer_question(question, user_name)
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        await message.reply_text("متأسفم، مشکلی پیش اومد. لطفاً دوباره امتحان کن.")
        return

    reply_text = answer
    if sources:
        sources_text = "\n".join([f"• {s}" for s in sources])
        reply_text += f"\n\n📚 منابع:\n{sources_text}"

    await message.reply_text(reply_text)

    async with AsyncSessionLocal() as db:
        log = ChatLog(
            telegram_user_id=str(user.id),
            telegram_username=user.username,
            chat_id=str(message.chat_id),
            question=question,
            answer=answer,
            sources_used=", ".join(sources) if sources else None,
        )
        db.add(log)
        await db.commit()


async def _is_group_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is a member of the allowed group."""
    if not settings.allowed_group_id:
        return True
    try:
        member = await context.bot.get_chat_member(
            chat_id=settings.allowed_group_id, user_id=user_id
        )
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user = message.from_user
    if not user:
        return

    if not is_admin(user.id) and not await _is_group_member(user.id, context):
        await message.reply_text("⛔ فقط اعضای گروه می‌توانند از این ربات استفاده کنند.")
        return

    if message.text:
        question = message.text.strip()
        if question.startswith("/"):
            return

        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
        try:
            answer, sources = await answer_question(question, user.username or str(user.id))
        except Exception as e:
            logger.error(f"Error: {e}")
            await message.reply_text("مشکلی پیش اومد. دوباره امتحان کن.")
            return

        reply_text = answer
        if sources:
            sources_text = "\n".join([f"• {s}" for s in sources])
            reply_text += f"\n\n📚 منابع:\n{sources_text}"

        await message.reply_text(reply_text)

    elif message.document or message.audio or message.video or message.voice:
        if not is_admin(user.id):
            await message.reply_text("⛔ فقط ادمین‌ها می‌توانند فایل آپلود کنند.")
            return
        await _handle_file_upload(message, context)


async def _handle_file_upload(message: Message, context: ContextTypes.DEFAULT_TYPE):
    file_obj = message.document or message.audio or message.video or message.voice
    if not file_obj:
        return

    if message.document:
        original_name = message.document.file_name or "file"
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
    elif message.audio:
        original_name = message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
        file_id = message.audio.file_id
        file_size = message.audio.file_size or 0
    elif message.video:
        original_name = message.video.file_name or f"video_{message.video.file_id}.mp4"
        file_id = message.video.file_id
        file_size = message.video.file_size or 0
    elif message.voice:
        original_name = f"voice_{message.voice.file_id}.ogg"
        file_id = message.voice.file_id
        file_size = message.voice.file_size or 0
    else:
        return

    file_type = get_file_type(original_name)
    if file_type == "unknown":
        await message.reply_text("❌ این فرمت فایل پشتیبانی نمی‌شود.")
        return

    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        await message.reply_text(f"❌ حجم فایل بیش از {settings.max_file_size_mb}MB است.")
        return

    status_msg = await message.reply_text("⏳ در حال دانلود و پردازش فایل...")

    try:
        tg_file = await context.bot.get_file(file_id)
        ext = os.path.splitext(original_name)[1].lower() or ".bin"
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(settings.upload_dir, unique_name)

        await tg_file.download_to_drive(file_path)

        async with AsyncSessionLocal() as db:
            doc = Document(
                filename=unique_name,
                original_name=original_name,
                file_type=file_type,
                file_size=file_size,
                status="processing",
                uploaded_by=f"telegram:{message.from_user.username or message.from_user.id}",
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            doc_id = doc.id

        await status_msg.edit_text("⏳ در حال خواندن و ایندکس کردن محتوا...")

        chunks, metadatas = await process_file(file_path, original_name, doc_id)
        chunk_count = add_documents(chunks, metadatas, doc_id)

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "ready"
                doc.chunk_count = chunk_count
                await db.commit()

        await status_msg.edit_text(
            f"✅ فایل با موفقیت اضافه شد!\n"
            f"📄 نام: {original_name}\n"
            f"🔢 تعداد بخش‌ها: {chunk_count}"
        )

    except Exception as e:
        logger.error(f"File upload error: {e}")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "error"
                doc.error_message = str(e)
                await db.commit()
        await status_msg.edit_text(f"❌ خطا در پردازش فایل:\n{str(e)}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    name = user.first_name or "کاربر"
    await update.message.reply_text(
        f"سلام {name}! 👋\n\n"
        "من یک دستیار هوشمند هستم.\n\n"
        "📌 در گروه: منشنم کن و سوالت رو بنویس\n"
        "💬 در پیام خصوصی: مستقیم سوالت رو بنویس\n"
        "📁 ادمین‌ها می‌توانند فایل، صوت یا ویدئو آموزشی ارسال کنند"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_section = ""
    if user and is_admin(user.id):
        admin_section = (
            "\n\n🔑 *دستورات ادمین:*\n"
            "/list - لیست فایل‌های آموزشی\n"
            "/delete [id] - حذف یک فایل\n"
            "📎 ارسال فایل مستقیم برای آپلود"
        )

    await update.message.reply_text(
        "📖 *راهنما:*\n\n"
        "در گروه: @بات سوالت\n"
        "در پیام خصوصی: مستقیم بنویس"
        + admin_section,
        parse_mode="Markdown"
    )


async def cmd_list_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).order_by(Document.created_at.desc()).limit(20)
        )
        docs = result.scalars().all()

    if not docs:
        await update.message.reply_text("📭 هیچ فایلی آپلود نشده.")
        return

    text = "📚 *فایل‌های آموزشی:*\n\n"
    for d in docs:
        status_emoji = {"ready": "✅", "processing": "⏳", "error": "❌"}.get(d.status, "❓")
        text += f"{status_emoji} `[{d.id}]` {d.original_name}\n"
        text += f"    نوع: {d.file_type} | بخش‌ها: {d.chunk_count}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_delete_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("استفاده: /delete [id]")
        return

    doc_id = int(args[0])

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()

        if not doc:
            await update.message.reply_text("❌ فایل یافت نشد.")
            return

        file_path = os.path.join(settings.upload_dir, doc.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        delete_document(doc_id)
        await db.delete(doc)
        await db.commit()

    await update.message.reply_text(f"✅ فایل `{doc.original_name}` حذف شد.", parse_mode="Markdown")
