from openai import AsyncOpenAI
from typing import Tuple, List
from datetime import datetime, timezone, timedelta
import re
from app.config import settings
from app.rag.vector_store import similarity_search

client = AsyncOpenAI(api_key=settings.openai_api_key)

grok_client = AsyncOpenAI(
    api_key=settings.grok_api_key or "dummy",
    base_url="https://api.x.ai/v1",
) if settings.grok_api_key else None

_GROK_PREFIX = re.compile(
    r"^(grok|گروک|گراک)[:\s،,]?\s*",
    re.IGNORECASE,
)

_NEWS_KEYWORDS = re.compile(
    r"(خبر|اخبار|امروز|دیروز|این هفته|هفته.ی اخیر|هفته پیش|ماه جاری|اتفاق|رویداد"
    r"|جدید|آخرین|تازه|news|latest|today|this week|recent|current)",
    re.IGNORECASE,
)


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


async def _answer_with_web_search(question: str, system_prompt: str) -> str:
    """Use OpenAI Responses API with built-in web search for real-time questions."""
    response = await client.responses.create(
        model="gpt-4.1",
        tools=[{"type": "web_search_preview"}],
        instructions=system_prompt,
        input=question,
    )
    return response.output_text


async def _answer_with_grok(question: str, system_prompt: str, context: str) -> str:
    """Answer using Grok via xAI API."""
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "user", "content": f"اطلاعات مرتبط:\n\n{context}\n\n---\n\nسوال: {question}"})
    else:
        messages.append({"role": "user", "content": question})
    response = await grok_client.chat.completions.create(
        model="grok-3",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    return response.choices[0].message.content


async def answer_question(question: str, user_name: str = "") -> Tuple[str, List[str]]:
    use_grok = bool(_GROK_PREFIX.match(question)) and grok_client is not None
    if use_grok:
        question = _GROK_PREFIX.sub("", question).strip()

    relevant_docs = similarity_search(question, k=5)
    system_prompt = _get_system_prompt()

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

    if use_grok:
        try:
            answer = await _answer_with_grok(question, system_prompt, context)
            return answer, sources + ["🤖 Grok"]
        except Exception as e:
            pass

    needs_web = bool(_NEWS_KEYWORDS.search(question)) and not context

    if needs_web:
        try:
            answer = await _answer_with_web_search(question, system_prompt)
            return answer, ["🌐 جستجوی وب"]
        except Exception:
            pass

    messages = [{"role": "system", "content": system_prompt}]

    if context:
        messages.append({
            "role": "user",
            "content": f"اطلاعات مرتبط از پایگاه دانش:\n\n{context}\n\n---\n\nسوال: {question}"
        })
    else:
        messages.append({"role": "user", "content": question})

    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )

    answer = response.choices[0].message.content
    return answer, sources
