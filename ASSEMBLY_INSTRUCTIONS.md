# 📦 ИНСТРУКЦИЯ ПО СБОРКЕ HR CAREER BOT

## 🎯 Все файлы загружены по отдельности

### Список файлов (скачайте все):

**Основные файлы Python (папка src/):**
1. `1_bot.py` → переименуйте в `bot.py`
2. `2_config.py` → переименуйте в `config.py`
3. `3_database.py` → переименуйте в `database.py`
4. `4_gigachat_service.py` → переименуйте в `gigachat_service.py`
5. `5_hybrid_search.py` → переименуйте в `hybrid_search.py`
6. `6_build_potencial_kb.py` → переименуйте в `build_potencial_kb.py`

**Конфигурация:**
7. `7_requirements.txt` → переименуйте в `requirements.txt`
8. `8_env_example.txt` → переименуйте в `.env.example`

**Документация:**
9. `9_README.md` → переименуйте в `README.md`
10. `10_QUICKSTART.md` → переименуйте в `QUICKSTART.md`
11. `11_DEPLOYMENT.md` → переименуйте в `DEPLOYMENT.md`
12. `12_ASSEMBLY_INSTRUCTIONS.md` → этот файл

---

## 📁 Создайте структуру проекта:

```
hr_career_bot/
├── src/
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   ├── gigachat_service.py
│   ├── hybrid_search.py
│   └── build_potencial_kb.py
├── data/
│   ├── knowledge_base/
│   └── vector_index/
├── requirements.txt
├── .env.example
├── README.md
├── QUICKSTART.md
└── DEPLOYMENT.md
```

---

## 🛠️ Пошаговая сборка:

### Шаг 1: Создайте папки
```bash
mkdir -p hr_career_bot/src
mkdir -p hr_career_bot/data/knowledge_base
mkdir -p hr_career_bot/data/vector_index
cd hr_career_bot
```

### Шаг 2: Переместите файлы

**В папку `src/`:**
- `1_bot.py` → `src/bot.py`
- `2_config.py` → `src/config.py`
- `3_database.py` → `src/database.py`
- `4_gigachat_service.py` → `src/gigachat_service.py`
- `5_hybrid_search.py` → `src/hybrid_search.py`
- `6_build_potencial_kb.py` → `src/build_potencial_kb.py`

**В корень проекта:**
- `7_requirements.txt` → `requirements.txt`
- `8_env_example.txt` → `.env.example`
- `9_README.md` → `README.md`
- `10_QUICKSTART.md` → `QUICKSTART.md`
- `11_DEPLOYMENT.md` → `DEPLOYMENT.md`

### Шаг 3: Установите зависимости
```bash
pip install -r requirements.txt
```

### Шаг 4: Настройте .env
```bash
cp .env.example .env
nano .env  # или любой редактор
```

Заполните:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
GIGACHAT_CLIENT_SECRET=ваш_ключ_GigaChat
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
```

### Шаг 5: Запустите бота
```bash
python src/bot.py
```

---

## ✅ Проверка установки

После запуска вы должны увидеть:
```
2024-04-29 10:00:00 - root - INFO - 🔄 Начало инициализации компонентов...
2024-04-29 10:00:00 - root - INFO - 📊 Инициализация базы данных...
2024-04-29 10:00:01 - root - INFO - 🤖 Инициализация GigaChat сервиса...
2024-04-29 10:00:01 - root - INFO - ✅ Все компоненты инициализированы успешно
2024-04-29 10:00:02 - root - INFO - ✅ Бот запущен!
```

---

## 🔧 Если что-то не работает:

### Ошибка: "No module named 'gigachat'"
```bash
pip install gigachat
```

### Ошибка: "TELEGRAM_BOT_TOKEN not found"
Проверьте файл `.env` - он должен быть в корне проекта

### Ошибка: "GIGACHAT_CLIENT_SECRET not found"
Добавьте ключ GigaChat в `.env`

### База знаний не работает
Это нормально! Бот работает и без неё. Для добавления базы знаний:
```bash
python src/build_potencial_kb.py
```

---

## 📚 Дополнительная информация:

- **DEPLOYMENT.md** - полный обзор проекта
- **README.md** - техническая документация
- **QUICKSTART.md** - быстрый старт

---

## 🎉 Готово!

После выполнения всех шагов бот готов к работе!

Откройте Telegram и напишите вашему боту `/start`

**Проект полностью функционален! 🚀**
