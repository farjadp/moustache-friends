import os
import uuid
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db, Document
from app.rag.file_processor import process_file, get_file_type
from app.rag.vector_store import add_documents, delete_document
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

os.makedirs(settings.upload_dir, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md",
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus",
    ".mp4", ".mkv", ".avi", ".mov", ".webm"
}


async def _process_document(file_path: str, original_name: str, doc_id: int, db_session_factory):
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            chunks, metadatas = await process_file(file_path, original_name, doc_id)
            chunk_count = add_documents(chunks, metadatas, doc_id)

            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "ready"
                doc.chunk_count = chunk_count
                await db.commit()
        except Exception as e:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "error"
                doc.error_message = str(e)
                await db.commit()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    uploaded_by: str = "web",
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"فرمت {ext} پشتیبانی نمی‌شود")

    file_size = 0
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.upload_dir, unique_name)

    async with aiofiles.open(file_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.max_file_size_mb * 1024 * 1024:
                await out.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail="حجم فایل بیش از حد مجاز است")
            await out.write(chunk)

    doc = Document(
        filename=unique_name,
        original_name=file.filename or unique_name,
        file_type=get_file_type(file.filename or ""),
        file_size=file_size,
        status="processing",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_process_document, file_path, file.filename or unique_name, doc.id, None)

    return {"id": doc.id, "filename": doc.original_name, "status": "processing"}


@router.get("/")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.original_name,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "error_message": d.error_message,
            "uploaded_by": d.uploaded_by,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
async def delete_doc(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="سند یافت نشد")

    file_path = os.path.join(settings.upload_dir, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    delete_document(doc_id)

    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()

    return {"message": "سند حذف شد"}


@router.get("/{doc_id}/status")
async def get_status(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="سند یافت نشد")
    return {"id": doc.id, "status": doc.status, "chunk_count": doc.chunk_count, "error_message": doc.error_message}
