import os
import json
import logging
import asyncio
import tempfile
from typing import List, Dict

from app.config import settings
from app.rag.file_processor import get_file_type, process_file
from app.rag.vector_store import add_documents, delete_document
from app.database import AsyncSessionLocal, Document
from sqlalchemy import select

logger = logging.getLogger(__name__)

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
}

_synced_drive_ids: set = set()


def _build_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not settings.google_service_account_json or not settings.google_drive_folder_id:
        return None

    try:
        creds_info = json.loads(settings.google_service_account_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Drive auth error: {e}")
        return None


def _list_drive_files(service) -> List[Dict]:
    results = []
    page_token = None
    query = f"'{settings.google_drive_folder_id}' in parents and trashed=false"

    while True:
        resp = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return results


async def sync_drive(notify_chat_id: int = None, bot=None) -> Dict:
    service = _build_drive_service()
    if not service:
        return {"error": "Google Drive پیکربندی نشده"}

    files = _list_drive_files(service)
    new_count = 0
    skipped = 0
    errors = []

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(Document).where(Document.uploaded_by.like("gdrive:%"))
        )
        existing_drive_ids = {
            d.uploaded_by.replace("gdrive:", "")
            for d in existing.scalars().all()
        }

    for f in files:
        drive_id = f["id"]
        name = f["name"]
        mime = f.get("mimeType", "")

        if drive_id in existing_drive_ids:
            skipped += 1
            continue

        ext = SUPPORTED_MIME_TYPES.get(mime)
        if not ext:
            file_type = get_file_type(name)
            if file_type == "unknown":
                skipped += 1
                continue
            ext = os.path.splitext(name)[1] or ".bin"

        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io

            request = service.files().get_media(fileId=drive_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            fh.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(fh.read())
                tmp_path = tmp.name

            async with AsyncSessionLocal() as db:
                doc = Document(
                    filename=os.path.basename(tmp_path),
                    original_name=name,
                    file_type=get_file_type(name),
                    file_size=os.path.getsize(tmp_path),
                    status="processing",
                    uploaded_by=f"gdrive:{drive_id}",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                doc_id = doc.id

            chunks, metadatas = await process_file(tmp_path, name, doc_id)
            chunk_count = add_documents(chunks, metadatas, doc_id)

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Document).where(Document.id == doc_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "ready"
                    doc.chunk_count = chunk_count
                    await db.commit()

            os.unlink(tmp_path)
            new_count += 1
            logger.info(f"Drive sync: indexed '{name}' ({chunk_count} chunks)")

        except Exception as e:
            errors.append(f"{name}: {str(e)}")
            logger.error(f"Drive sync error for '{name}': {e}")

    result = {"new": new_count, "skipped": skipped, "errors": errors}

    if bot and notify_chat_id:
        msg = f"🔄 *Google Drive Sync*\n✅ فایل جدید: {new_count}\n⏭ قبلاً ایندکس شده: {skipped}"
        if errors:
            msg += f"\n❌ خطا: {len(errors)}"
        await bot.send_message(chat_id=notify_chat_id, text=msg, parse_mode="Markdown")

    return result


async def start_drive_scheduler(bot, admin_chat_id: int):
    """Run drive sync every drive_sync_interval_hours hours."""
    interval = settings.drive_sync_interval_hours * 3600
    logger.info(f"Drive scheduler started — sync every {settings.drive_sync_interval_hours}h")
    while True:
        await asyncio.sleep(interval)
        logger.info("Running scheduled Drive sync...")
        await sync_drive(notify_chat_id=admin_chat_id, bot=bot)
