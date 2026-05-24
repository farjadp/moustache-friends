from openai import AsyncOpenAI
from typing import Tuple, List
from datetime import datetime, timezone, timedelta
from app.config import settings
from app.rag.vector_store import similarity_search

client = AsyncOpenAI(api_key=settings.openai_api_key)


def _to_jalali(year: int, month: int, day: int) -> str:
    """Convert Gregorian date to Jalali (Solar Hijri) date string."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        g_days_in_month[1] = 29
    gy = year - 1600
    gm = month - 1
    gd = day - 1
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    g_day_no += gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    jm = 0
    for i, days in enumerate(j_days_in_month):
        if j_day_no < days:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= days
    month_names = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور',
                   'مهر','آبان','آذر','دی','بهمن','اسفند']
    return f"{jd} {month_names[jm-1]} {jy}"


def _get_system_prompt() -> str:
    now = datetime.now(tz=timezone(timedelta(hours=3, minutes=30)))
    jalali = _to_jalali(now.year, now.month, now.day)
    gregorian = now.strftime("%d %B %Y")
    return f"""تو یک دستیار هوشمند هستی که به سوالات کاربران پاسخ می‌دهی.
تاریخ امروز: {jalali} (شمسی) / {gregorian} (میلادی)
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

    messages = [{"role": "system", "content": _get_system_prompt()}]

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
