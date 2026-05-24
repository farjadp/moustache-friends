# 🤖 ربات تلگرام هوشمند با RAG

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

یک دستیار هوشمند برای گروه تلگرام که از پایگاه دانش شما یاد می‌گیرد.

## ✨ امکانات

- **منشن در گروه**: کاربران با منشن کردن ربات سوال می‌پرسند
- **RAG (Retrieval-Augmented Generation)**: جواب‌ها بر اساس فایل‌های آموزشی شما
- **پشتیبانی از فرمت‌های مختلف**: PDF، Word، TXT، MP3، MP4، ویدئو و...
- **تبدیل گفتار به متن**: فایل‌های صوتی و ویدئویی با Whisper پردازش می‌شوند
- **پنل مدیریت وب**: آپلود و مدیریت فایل‌ها از مرورگر
- **ادمین بات**: آپلود مستقیم از تلگرام توسط ادمین‌ها
- **لاگ سوالات**: مشاهده تمام سوالات و جواب‌ها

## 🚀 راه‌اندازی سریع

### ۱. پیش‌نیازها

- Docker و Docker Compose
- API Key از OpenAI
- توکن ربات تلگرام (از [@BotFather](https://t.me/BotFather))

### ۲. تنظیم متغیرها

```bash
cd backend
cp .env.example .env
```

فایل `.env` را ویرایش کنید:

```env
OPENAI_API_KEY=sk-...              # کلید API اوپن‌ای‌آی
TELEGRAM_BOT_TOKEN=123:ABC...      # توکن ربات
TELEGRAM_ADMIN_IDS=123456789       # آیدی عددی ادمین‌ها (با کاما جدا کنید)
BOT_USERNAME=your_bot_username     # یوزرنیم ربات (بدون @)
```

### ۳. اجرا با Docker

```bash
docker-compose up -d
```

- **Backend API**: http://localhost:8000
- **پنل مدیریت**: http://localhost:3000

### ۴. اجرای بدون Docker (توسعه)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Bot (در ترمینال جداگانه)
cd backend
python -m bot.run

# Admin Panel (در ترمینال جداگانه)
cd admin-panel
npm install
npm run dev
```

## 📁 ساختار پروژه

```
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── rag/          # RAG pipeline (vector store, file processor, QA chain)
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── bot/
│   │   ├── handlers.py   # Telegram handlers
│   │   └── run.py
│   ├── requirements.txt
│   └── .env.example
├── admin-panel/          # React + Tailwind admin UI
│   └── src/
│       ├── pages/
│       └── api.ts
└── docker-compose.yml
```

## 🤖 استفاده از ربات

### در گروه
```
@نام_ربات سوال خودت رو اینجا بنویس
```

### دستورات ادمین (در پیام خصوصی)
| دستور | توضیح |
|-------|-------|
| `/list` | لیست فایل‌های آموزشی |
| `/delete [id]` | حذف یک فایل |
| ارسال فایل مستقیم | آپلود و ایندکس خودکار |

### فرمت‌های پشتیبانی شده
- 📄 **اسناد**: PDF, DOCX, TXT, MD
- 🎵 **صوتی**: MP3, WAV, OGG, M4A, OPUS
- 🎬 **ویدئو**: MP4, MKV, AVI, MOV

## ⚙️ متغیرهای محیطی

| متغیر | توضیح | پیش‌فرض |
|-------|-------|---------|
| `OPENAI_API_KEY` | کلید API اوپن‌ای‌آی | **الزامی** |
| `TELEGRAM_BOT_TOKEN` | توکن ربات | **الزامی** |
| `TELEGRAM_ADMIN_IDS` | آیدی‌های ادمین (با کاما) | خالی |
| `BOT_USERNAME` | یوزرنیم ربات | خالی |
| `WHISPER_MODEL` | مدل Whisper: tiny/base/small/medium | `base` |
| `MAX_FILE_SIZE_MB` | حداکثر حجم فایل | `500` |

## 🔧 نکات مهم

1. **آیدی ادمین**: برای پیدا کردن آیدی عددی خود، به [@userinfobot](https://t.me/userinfobot) پیام بدید
2. **ربات را به گروه اضافه کنید** و دسترسی خواندن پیام‌ها را بدید
3. **ffmpeg** برای پردازش ویدئو نیاز است (در Dockerfile نصب می‌شود)
4. مدل Whisper `base` برای فارسی خوب کار می‌کند؛ برای دقت بیشتر از `small` استفاده کنید
