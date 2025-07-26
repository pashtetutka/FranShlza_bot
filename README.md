<h1 align="center">🚀 Motivation Reels Bot</h1>
<p align="center">
  Телеграм‑бот для продажи мотивационных рилсов и управления партнёрской (50 %) реферальной программой.
</p>

<div align="center">
  
[Основной канал поддержки](https://t.me/your_channel) •
[Открыть демо‑бота](https://t.me/your_bot)

</div>

---

## ✨  Возможности

| 🎯 | Описание |
|----|-----------|
| **Продажа подписки** | Принимает оплату (сейчас вручную/карта → в будущем Lava API) и выдаёт доступ навсегда или к подписке |
| **Реферальная система 50 %** | Бот отслеживает, кто пригласил друга, и отдаёт половину платежа «родителю» |
| **Гибкие цены** | Для «старичков» (опытных блогеров) админ назначает индивидуальную цену |
| **Авто‑таблицы** | В админ‑чате бот рисует ASCII‑таблицы пользователей и статистики |
| **Медиа‑интро** | При старте бот присылает набор картинок и видео‑инструкцию |
| **Поддержка в диалоге** | Пользователь пишет вопрос → бот шлёт его админу → админ отвечает командой `/reply` |

---

## 🗂️  Структура проекта (после рефакторинга)
```
motivation_bot/
├── bot/
│ ├── main.py # точка входа
│ ├── config.py # Pydantic‑настройки из .env
│ ├── keyboards.py # все кнопки
│ ├── media.py # ID фото / видео
│ ├── utils.py # send_long, fmt_table …
│ ├── db/
│ │ └── queries.py # весь SQL
│ └── handlers/ # логика бота разбита по файлам
│ ├── common.py
│ ├── onboarding.py
│ ├── payments.py
│ ├── admin.py
│ └── support.py
├── requirements.txt
├── .env.sample
└── README.md
```
---

## ⚙️  Быстрый старт

```bash
git clone https://github.com/<YOU>/motivation_bot.git
cd motivation_bot

# 1. Создаём виртуальное окружение
python -m venv .venv
source .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate

# 2. Ставим зависимости
`pip install -r requirements.txt`

# 3. Заполняем переменные окружения
cp .env.sample .env
# BOT_TOKEN=...  (токен бота от @BotFather)
# ADMIN_ID=...   (ваш Telegram ID)

# 4. Запуск
python -m bot.main
```