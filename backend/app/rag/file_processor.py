import os
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)


async def extract_text_from_pdf(file_path: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_pdf_sync, file_path)


def _extract_pdf_sync(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


async def extract_text_from_docx(file_path: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_docx_sync, file_path)


def _extract_docx_sync(file_path: str) -> str:
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])


async def extract_text_from_txt(file_path: str) -> str:
    async with __import__("aiofiles").open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return await f.read()


async def extract_text_from_audio_video(file_path: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, file_path)


def _transcribe_sync(file_path: str) -> str:
    import whisper
    model = whisper.load_model(settings.whisper_model)
    result = model.transcribe(file_path)
    return result["text"]


async def process_file(file_path: str, original_name: str, doc_id: int) -> Tuple[List[str], List[dict]]:
    ext = Path(original_name).suffix.lower()

    if ext == ".pdf":
        text = await extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        text = await extract_text_from_docx(file_path)
    elif ext in (".txt", ".md", ".rst"):
        text = await extract_text_from_txt(file_path)
    elif ext in (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"):
        text = await extract_text_from_audio_video(file_path)
    elif ext in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
        text = await extract_text_from_audio_video(file_path)
    else:
        raise ValueError(f"فرمت فایل پشتیبانی نمی‌شود: {ext}")

    if not text.strip():
        raise ValueError("متنی از فایل استخراج نشد")

    chunks = text_splitter.split_text(text)
    metadatas = [
        {
            "document_id": doc_id,
            "filename": original_name,
            "chunk_index": i,
            "file_type": ext.lstrip("."),
        }
        for i in range(len(chunks))
    ]
    return chunks, metadatas


def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in (".docx", ".doc"):
        return "docx"
    elif ext in (".txt", ".md"):
        return "text"
    elif ext in (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"):
        return "audio"
    elif ext in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
        return "video"
    else:
        return "unknown"
