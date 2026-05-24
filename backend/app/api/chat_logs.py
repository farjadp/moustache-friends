from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db, ChatLog

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/")
async def get_logs(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatLog).order_by(ChatLog.created_at.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "user_id": l.telegram_user_id,
            "username": l.telegram_username,
            "chat_id": l.chat_id,
            "question": l.question,
            "answer": l.answer,
            "sources": l.sources_used,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(ChatLog.id)))
    total = total_result.scalar()

    unique_users_result = await db.execute(select(func.count(func.distinct(ChatLog.telegram_user_id))))
    unique_users = unique_users_result.scalar()

    return {"total_questions": total, "unique_users": unique_users}
