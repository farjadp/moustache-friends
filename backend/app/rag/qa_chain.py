from openai import AsyncOpenAI
from typing import Tuple, List
from app.config import settings
from app.rag.vector_store import similarity_search

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """تو یک دستیار هوشمند هستی که به سوالات کاربران پاسخ می‌دهی.
اگر اطلاعات مرتبطی در پایگاه دانش وجود دارد، از آن استفاده کن و به منبع اشاره کن.
اگر اطلاعاتی در پایگاه دانش نیست، از دانش عمومی خودت پاسخ بده و صادق باش.
پاسخ‌ها باید مختصر، مفید و به فارسی باشند (مگر اینکه سوال به زبان دیگری باشد).
"""


async def answer_question(question: str, user_name: str = "") -> Tuple[str, List[str]]:
    relevant_docs = similarity_search(question, k=5)

    context = ""
    sources = []
    if relevant_docs:
        context_parts = []
        for doc in relevant_docs:
            context_parts.append(f"[منبع: {doc['metadata'].get('filename', 'نامشخص')}]\n{doc['content']}")
            source = doc["metadata"].get("filename", "")
            if source and source not in sources:
                sources.append(source)
        context = "\n\n---\n\n".join(context_parts)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "user",
            "content": f"اطلاعات مرتبط از پایگاه دانش:\n\n{context}\n\n---\n\nسوال: {question}"
        })
    else:
        messages.append({"role": "user", "content": question})

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )

    answer = response.choices[0].message.content
    return answer, sources
