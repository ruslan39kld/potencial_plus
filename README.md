# HR Career Bot - Potencial Plus

Телеграм-бот карьерного консультанта для проекта Potencial Plus с интеграцией GigaChat API и гибридным поиском.

## 🎯 Возможности бота

### 5 AI-ассистентов:
1. **🎯 Карьерный помощник** - подбор профессий, треков, вакансий
2. **💰 Финансовый консультант** - расчет финансовой подушки, планирование накоплений
3. **🧠 Психолог** - работа со страхами, мотивация, уверенность
4. **⚖️ Юридический консультант** - трудовые вопросы, права работника
5. **🛡️ Эксперт по безопасности** - проверка вакансий, защита от мошенников

### Дополнительные функции:
- 📋 **Психологические тесты** (КОС, Томас, Герчикова)
- 📊 **Личная статистика** пользователя
- 🔍 **Гибридный поиск** (векторный + BM25)
- 💾 **История диалогов**
- ⏱️ **Лимиты использования** (бесплатно/premium)

## 📁 Структура проекта

```
hr_career_bot/
├── src/
│   ├── bot.py                    # Основной файл бота
│   ├── config.py                 # Конфигурация
│   ├── database.py               # База данных SQLite
│   ├── gigachat_service.py       # Интеграция с GigaChat
│   ├── hybrid_search.py          # Гибридный поиск
│   └── process_knowledge_base.py # Обработка базы знаний
├── data/
│   ├── knowledge_base/           # Исходные данные
│   ├── vector_index/             # Векторные индексы
│   ├── hr_bot.db                 # База данных
│   └── hr_bot.log                # Логи
├── requirements.txt              # Зависимости
├── .env.example                  # Шаблон переменных окружения
└── README.md                     # Этот файл
```

## 🚀 Установка и запуск

### 1. Клонируйте репозиторий
```bash
git clone <repository_url>
cd hr_career_bot
```

### 2. Создайте виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройте переменные окружения
Скопируйте `.env.example` в `.env` и заполните:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
GIGACHAT_CLIENT_SECRET=your_gigachat_secret_here
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
```

### 5. (Опционально) Подготовьте базу знаний

Если у вас есть файлы Excel с Q&A или документы PDF/DOCX:

1. Поместите Excel файлы в `data/excel_qa/`
2. Поместите инструкции в `data/instructions/`
3. Запустите обработку:
```bash
python src/process_knowledge_base.py
```

4. Создайте векторный индекс (используйте скрипт из EASUZ бота):
```bash
python build_index.py  # Если есть
```

### 6. Запустите бота
```bash
python src/bot.py
```

## 📋 Использование

### Команды бота:
- `/start` - Начать работу с ботом
- `/menu` - Открыть главное меню
- `/help` - Показать справку
- `/stats` - Статистика бота (для админа)

### Основной workflow:
1. Пользователь запускает бота `/start`
2. Выбирает нужного ассистента (карьерный, финансовый и т.д.)
3. Задает вопросы в чат
4. Получает ответы с учетом контекста из базы знаний
5. Может пройти психологические тесты
6. Смотрит свою статистику

## 🎛️ Конфигурация

### Лимиты (в `config.py`):
```python
FREE_QUESTIONS_PER_DAY = 10   # Бесплатных вопросов в день
FREE_QUESTIONS_PER_WEEK = 50  # Бесплатных вопросов в неделю
```

### Ссылки на тесты:
```python
TESTS_LINKS = {
    "kos": {...},      # Тест коммуникативных способностей
    "thomas": {...},   # Тест поведения в конфликтах
    "gerchikova": {...} # Тест мотивации
}
```

### Промпты для ассистентов:
Находятся в `config.SYSTEM_PROMPTS`, можно редактировать под свои задачи.

## 🔧 Как это работает

### 1. Гибридный поиск
```python
# Комбинация векторного (FAISS) и ключевого (BM25) поиска
docs = knowledge_base.search(query, top_k=3)
```

### 2. Формирование контекста
```python
# Топ-3 документа из базы знаний добавляются в промпт
context = _build_context_from_kb(docs)
prompt = system_prompt + context + user_question
```

### 3. Запрос к GigaChat
```python
with GigaChat(credentials=...) as giga:
    response = giga.chat(prompt)
    answer = response.choices[0].message.content
```

### 4. Сохранение истории
```python
database.save_message(user_id, assistant_type, question, answer, time)
database.increment_daily_usage(user_id)
```

## 📊 База данных

SQLite с 4 таблицами:
- `users` - Пользователи
- `messages` - История сообщений
- `usage_limits` - Лимиты использования
- `completed_tests` - Пройденные тесты

## 🛠️ Адаптация существующего бота

Этот бот создан на основе архитектуры EASUZ_BOT:
- ✅ Использует тот же `hybrid_search.py`
- ✅ Аналогичная структура `database.py`
- ✅ Совместим с `process_knowledge_base.py`
- ✅ Можно использовать существующий векторный индекс

### Миграция данных:
Если у вас уже есть EASUZ_BOT, можно переиспользовать:
1. Векторный индекс из `data/easuz_index/` → `data/vector_index/`
2. База знаний `data/structured_qa.json` и `data/chunks_data.json`

## 🌟 Особенности проекта Potencial Plus

### Целевая аудитория:
- Россияне с доходом до 100 000 руб/мес
- Массовые профессии (курьеры, строители, водители и т.д.)

### Ключевые принципы:
1. Вахтовая работа = инструмент формирования капитала
2. Финансовая подушка = основа уверенности
3. Карьерный рост = план + действия + поддержка
4. Международные возможности = вторая фаза развития

### Платформы:
- Основной сайт: https://potencial-plus.ru
- Вакансии: https://tempojob.org/
- Международные: https://www.russian.works/

## 📝 TODO / Дальнейшее развитие

- [ ] Добавить интеграцию с базой вакансий (tempojob.org API)
- [ ] Реализовать карьерные треки (маршруты развития)
- [ ] Добавить автоматическую оценку резюме
- [ ] Интегрировать калькулятор финансовой подушки
- [ ] Добавить уведомления о новых вакансиях
- [ ] Реализовать premium подписку (Stripe/ЮKassa)
- [ ] Мультиязычность (EN для international)
- [ ] A/B тестирование промптов

## 🐛 Отладка

### Логи:
Все логи пишутся в `data/hr_bot.log`

### Проверка компонентов:
```bash
# Проверка GigaChat
python -c "from gigachat import GigaChat; print('GigaChat OK')"

# Проверка базы знаний
python -c "from src.hybrid_search import HybridSearch; hs = HybridSearch('data/vector_index'); print(f'Docs: {hs.ntotal}')"
```

### Типичные ошибки:
1. **GIGACHAT_CLIENT_SECRET не установлен** - проверьте `.env`
2. **FileNotFoundError: index not found** - создайте индекс или уберите use_kb=False
3. **Markdown errors** - функция `sanitize_markdown()` автоматически исправляет

## 📞 Поддержка

Вопросы и предложения: [ваш контакт]

## 📄 Лицензия

[Ваша лицензия]
