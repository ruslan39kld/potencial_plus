"""
HR Career Bot для проекта Potencial Plus
Основной файл бота с интеграцией GigaChat и гибридным поиском
"""
import asyncio
import logging
import sys
import re
import os
from pathlib import Path
from dotenv import load_dotenv

# ⭐ ЗАГРУЗКА .env ФАЙЛА
# Определяем путь к .env (он в корне проекта)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Проверяем что токены загружены
print(f"🔍 Проверка переменных окружения:")
print(f"TELEGRAM_BOT_TOKEN: {'✅ Найден' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ НЕ НАЙДЕН'}")
print(f"GIGACHAT_CLIENT_SECRET: {'✅ Найден' if os.getenv('GIGACHAT_CLIENT_SECRET') else '❌ НЕ НАЙДЕН'}")
print(f".env файл: {env_path}")
print(f".env существует: {'✅ Да' if env_path.exists() else '❌ НЕТ'}\n")

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.exceptions import TelegramBadRequest

import config
from database import Database
from gigachat_service import GigaChatService
from hybrid_search import HybridSearch

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Глобальные компоненты
_components = {}
user_assistant = {}  # Выбранный ассистент для каждого пользователя


def sanitize_markdown(text: str) -> str:
    """Очистка Markdown для Telegram"""
    text = re.sub(r'<[^>]+>', '', text)
    
    if text.count('**') % 2 != 0:
        text = text.replace('**', '')
    
    temp_text = text.replace('**', '__BOLD__')
    if temp_text.count('*') % 2 != 0:
        text = text.replace('*', '')
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


async def init_components():
    """Инициализация всех компонентов бота"""
    global _components
    
    try:
        logging.info("🔄 Начало инициализации компонентов...")
        
        # База данных
        logging.info("📊 Инициализация базы данных...")
        database = Database(config.DB_PATH)
        
        # GigaChat сервис
        logging.info("🤖 Инициализация GigaChat сервиса...")
        gigachat_service = GigaChatService()
        
        # Гибридный поиск (опционально, если есть индекс)
        knowledge_base = None
        if config.INDEX_DIR.exists():
            try:
                logging.info("🔍 Инициализация системы поиска...")
                knowledge_base = HybridSearch(index_dir=str(config.INDEX_DIR))
                logging.info(f"✅ База знаний загружена: {knowledge_base.ntotal} документов")
            except Exception as e:
                logging.warning(f"⚠️ База знаний не загружена: {e}")
                logging.info("Бот будет работать без базы знаний")
        else:
            logging.warning("⚠️ Индекс не найден. Бот будет работать без базы знаний")
        
        _components.update({
            'database': database,
            'gigachat_service': gigachat_service,
            'knowledge_base': knowledge_base
        })
        
        # Тестовый запрос
        logging.info("🧪 Тестовый запрос к GigaChat...")
        try:
            test_answer, test_time = await gigachat_service.ask(
                "Привет, как дела?", 
                assistant_type='career',
                knowledge_base=knowledge_base,
                use_kb=False
            )
            logging.info(f"✅ Тест пройден: {test_time}ms")
        except Exception as e:
            logging.error(f"❌ Тестовый запрос не выполнен: {e}")
            return False
        
        logging.info("✅ Все компоненты инициализированы успешно")
        return True
        
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации: {e}", exc_info=True)
        return False


# ============================================================
# ГЛАВНОЕ МЕНЮ (ОБНОВЛЁННОЕ С 2 КОЛОНКАМИ)
# ============================================================

def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота (2 столбца как в AI Инженере)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Карьерный помощник", callback_data="menu_career"),
            InlineKeyboardButton(text="💰 Финансовый план", callback_data="assistant_finance"),
        ],
        [
            InlineKeyboardButton(text="🧠 Поддержка", callback_data="menu_support"),
            InlineKeyboardButton(text="📊 Инструменты", callback_data="menu_tools"),
        ],
        [
            InlineKeyboardButton(text="❓ Что ты можешь?", callback_data="about_bot"),
        ]
    ])
    return keyboard


def get_tests_menu() -> InlineKeyboardMarkup:
    """Меню с тестами"""
    tests = config.TESTS_LINKS
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📝 {tests['kos']['name']}", 
            url=tests['kos']['url']
        )],
        [InlineKeyboardButton(
            text=f"🤝 {tests['thomas']['name']}", 
            url=tests['thomas']['url']
        )],
        [InlineKeyboardButton(
            text=f"🎯 {tests['gerchikova']['name']}", 
            url=tests['gerchikova']['url']
        )],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")]
    ])
    return keyboard


# ============================================================
# ПОДМЕНЮ: КАРЬЕРНЫЙ ПОМОЩНИК (2 СТОЛБЦА)
# ============================================================

def get_career_submenu() -> InlineKeyboardMarkup:
    """Подменю Карьерного помощника (2 столбца)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Задать вопрос", callback_data="assistant_career"),
            InlineKeyboardButton(text="📋 Пройти диагностику", callback_data="career_diagnostics"),
        ],
        [
            InlineKeyboardButton(text="📝 Усилить резюме", callback_data="career_resume"),
            InlineKeyboardButton(text="🎯 Получить план", callback_data="career_plan"),
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu"),
        ]
    ])
    return keyboard


def get_support_submenu() -> InlineKeyboardMarkup:
    """Подменю Поддержки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧠 Психолог", callback_data="assistant_psychology"),
        ],
        [
            InlineKeyboardButton(text="⚖️ Юрист", callback_data="assistant_legal"),
        ],
        [
            InlineKeyboardButton(text="🛡️ Безопасность", callback_data="assistant_safety"),
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu"),
        ]
    ])
    return keyboard


def get_tools_submenu() -> InlineKeyboardMarkup:
    """Подменю Инструментов (без Моя статистика)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Пройти тесты", callback_data="show_tests"),
        ],
        [
            InlineKeyboardButton(text="📊 Вакансии", url=config.PLATFORMS['jobs']),
            InlineKeyboardButton(text="🌍 Международные", url=config.PLATFORMS['international']),
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu"),
        ]
    ])
    return keyboard


# ============================================================
# КОМАНДЫ БОТА
# ============================================================

async def cmd_start(message: types.Message):
    """Команда /start"""
    user_id = message.from_user.id
    database = _components['database']
    
    # Регистрируем пользователя
    database.register_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    await message.answer(
        "👋 **Карьерный консультант**\n\n"
        "Я помогу вам:\n"
        "• Построить карьерный план\n"
        "• Сформировать финансовую подушку\n"
        "• Найти вахтовую или международную работу\n"
        "• Преодолеть страх перемен\n"
        "• Разобраться в трудовых вопросах\n\n"
        "Выберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


async def cmd_help(message: types.Message):
    """Команда /help"""
    await message.answer(
        "📖 **Как пользоваться ботом:**\n\n"
        "**1. Выберите раздел**\n"
        "Навигация через меню:\n"
        "• 🎯 Карьерный помощник — подбор профессий и планов\n"
        "• 💰 Финансовый план — расчет накоплений и подушки\n"
        "• 🧠 Поддержка — психолог, юрист, безопасность\n"
        "• 📊 Инструменты — тесты, вакансии, статистика\n\n"
        "**2. Задавайте вопросы**\n"
        "Просто напишите свой вопрос в чат после выбора ассистента\n\n"
        "**3. Проходите тесты**\n"
        "Узнайте свои сильные стороны и тип карьеры\n\n"
        "Используйте /menu для вызова главного меню",
        parse_mode="Markdown"
    )


async def cmd_menu(message: types.Message):
    """Команда /menu"""
    await message.answer(
        "Выберите раздел:",
        reply_markup=get_main_menu()
    )


async def cmd_stats(message: types.Message):
    """Команда /stats (для администратора)"""
    database = _components['database']
    stats = database.get_stats()
    
    await message.answer(
        f"📊 **Статистика бота:**\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🔥 Активных за 7 дней: {stats['active_users_7d']}\n"
        f"💬 Всего сообщений: {stats['total_messages']}\n"
        f"⚡ Среднее время ответа: {stats['avg_response_time_ms']}ms",
        parse_mode="Markdown"
    )


# ============================================================
# ОБРАБОТЧИКИ CALLBACK: ОСНОВНЫЕ
# ============================================================

async def handle_assistant_selection(callback: CallbackQuery):
    """Выбор ассистента (прямой вызов)"""
    user_id = callback.from_user.id
    assistant_type = callback.data.replace("assistant_", "")
    
    user_assistant[user_id] = assistant_type
    
    # Сохраняем в БД
    database = _components['database']
    database.set_selected_assistant(user_id, assistant_type)
    
    assistant_names = {
        'career': '🎯 Карьерный помощник',
        'finance': '💰 Финансовый консультант',
        'psychology': '🧠 Психолог',
        'legal': '⚖️ Юридический консультант',
        'safety': '🛡️ Эксперт по безопасности'
    }
    
    assistant_descriptions = {
        'career': 'Помогу найти карьерный путь, подобрать профессию и вырасти в доходе',
        'finance': 'Помогу рассчитать финансовую подушку и составить план накоплений',
        'psychology': 'Помогу справиться со страхами и укрепить уверенность',
        'legal': 'Помогу разобраться в трудовых вопросах и правах работника',
        'safety': 'Помогу проверить вакансию и избежать мошенников'
    }
    
    await callback.message.edit_text(
        f"✅ Выбран: **{assistant_names[assistant_type]}**\n\n"
        f"{assistant_descriptions[assistant_type]}\n\n"
        "💬 Задавайте ваши вопросы в чат!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад в меню", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    
    await callback.answer()


async def handle_show_tests(callback: CallbackQuery):
    """Показ тестов"""
    tests_info = "📋 **Психологические тесты**\n\n" \
                 "Пройдите тесты, чтобы лучше понять себя:\n\n"
    
    for key, test in config.TESTS_LINKS.items():
        tests_info += f"**{test['name']}**\n{test['description']}\n\n"
    
    tests_info += "Нажмите на кнопку ниже, чтобы перейти к тесту ⬇️"
    
    await callback.message.edit_text(
        tests_info,
        reply_markup=get_tests_menu(),
        parse_mode="Markdown"
    )
    
    await callback.answer()


async def handle_my_stats(callback: CallbackQuery):
    """Моя статистика — заглушка (функция сохранена для совместимости)"""
    await callback.message.edit_text(
        "📈 **Статистика**\n\n"
        "Этот раздел временно отключен.\n"
        "Свяжитесь с администратором для получения детальной статистики.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "👋 **Карьерный консультант**\n\n"
        "Я помогу вам:\n"
        "• Построить карьерный план\n"
        "• Сформировать финансовую подушку\n"
        "• Найти вахтовую или международную работу\n"
        "• Преодолеть страх перемен\n"
        "• Разобраться в трудовых вопросах\n\n"
        "Выберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ОБРАБОТЧИКИ НОВЫХ МЕНЮ (ИЕРАРХИЯ)
# ============================================================

async def handle_menu_career(callback: CallbackQuery):
    """Открытие меню Карьерного помощника"""
    await callback.message.edit_text(
        "🎯 **Карьерный помощник**\n\n"
        "Я помогу вам:\n"
        "• Определить ваш тип и сегмент (Выживание/Стабилизация/Рост)\n"
        "• Построить карьерный план на 14-30 дней с конкретными шагами\n"
        "• Усилить резюме и подготовиться к собеседованиям\n"
        "• Найти работу с ростом дохода до 200 000+ руб/мес\n\n"
        "Выберите действие:",
        reply_markup=get_career_submenu(),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_menu_support(callback: CallbackQuery):
    """Открытие меню Поддержки"""
    await callback.message.edit_text(
        "🧠 **Поддержка**\n\n"
        "Выберите специалиста:\n\n"
        "🧠 **Психолог** — работа со страхами, мотивацией и тревогой перед переменами\n"
        "⚖️ **Юрист** — трудовые вопросы, проверка договоров, права работника\n"
        "🛡️ **Безопасность** — проверка вакансий на мошенничество, красные флаги",
        reply_markup=get_support_submenu(),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_menu_tools(callback: CallbackQuery):
    """Открытие меню Инструментов"""
    await callback.message.edit_text(
        "📊 **Инструменты**\n\n"
        "Дополнительные возможности:\n"
        "• 📋 Психологические тесты (Кос, Томас, Герчикова)\n"
        "• 📊 Платформы вакансий (TempoJob, Russian.Works)\n"
        "• 📈 Ваша статистика и прогресс",
        reply_markup=get_tools_submenu(),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_about_bot(callback: CallbackQuery):
    """Кнопка 'Что ты можешь?'"""
    about_text = """🤖 **POTENCIAL PLUS — AI-КОНСУЛЬТАНТ**

**🎯 КАРЬЕРНЫЙ ПОМОЩНИК**
- Диагностика за 5 вопросов (тип: Выживание/Стабилизация/Рост)
- Персональные планы на 14-30 дней с конкретными шагами
- Усиление резюме: обязанности → достижения с цифрами
- Отслеживание воронки: отклики → собеседования → офферы

**💰 ФИНАНСОВЫЙ ПЛАН**
- Расчёт финансовой подушки (3-6 месяцев расходов)
- Стратегии выхода из долгов
- Вахта как инструмент быстрых накоплений
- Планирование роста дохода по этапам

**🧠 ПСИХОЛОГИЧЕСКАЯ ПОДДЕРЖКА**
- Работа со страхом перемен и синдромом самозванца
- Снижение тревожности перед собеседованиями
- Возвращение мотивации после неудач

**⚖️ ЮРИДИЧЕСКАЯ ПОМОЩЬ**
- Базовые трудовые права по ТК РФ
- Проверка договоров ГПХ и трудовых
- Когда действительно нужен живой юрист

**🛡️ БЕЗОПАСНОСТЬ**
- Проверка вакансий на мошенничество
- Красные флаги в предложениях работы

**📊 СИСТЕМА РАБОТЫ**
- 10 детальных сегментов клиентов
- Деревья решений для выбора стратегии
- Метрики и протоколы проверки прогресса

**🌍 ПЛАТФОРМЫ:**
potencial-plus.ru | tempojob.org | russian.works

**Версия 2.0 | База знаний: 200 000+ символов**
"""
    
    await callback.message.edit_text(
        about_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ОБРАБОТЧИКИ: ДИАГНОСТИКА / РЕЗЮМЕ / ПЛАН (ОБНОВЛЁННЫЕ)
# ============================================================

async def handle_career_diagnostics(callback: CallbackQuery):
    """Диагностика типа клиента"""
    user_id = callback.from_user.id
    
    # АВТОМАТИЧЕСКИ ВЫБИРАЕМ КАРЬЕРНОГО ПОМОЩНИКА
    user_assistant[user_id] = 'career'
    database = _components['database']
    database.set_selected_assistant(user_id, 'career')
    
    await callback.message.edit_text(
        "📋 **Диагностика типа клиента**\n\n"
        "Задайте вопрос в формате:\n"
        "• «Какой у меня тип: Выживание, Стабилизация или Рост?»\n"
        "• «Помоги определить мой карьерный сегмент»\n"
        "• «Я [описание ситуации] — что мне делать?»\n\n"
        "💬 **Напишите ваш вопрос в чат ниже** ⬇️",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_career")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_career_resume(callback: CallbackQuery):
    """Усиление резюме"""
    user_id = callback.from_user.id
    
    # АВТОМАТИЧЕСКИ ВЫБИРАЕМ КАРЬЕРНОГО ПОМОЩНИКА
    user_assistant[user_id] = 'career'
    database = _components['database']
    database.set_selected_assistant(user_id, 'career')
    
    await callback.message.edit_text(
        "📝 **Усиление резюме**\n\n"
        "Отправьте текст вашего резюме.\n"
        "Я помогу:\n"
        "• Переформулировать обязанности в достижения с цифрами\n"
        "• Добавить ключевые слова для ATS-систем\n"
        "• Усилить раздел «О себе» под целевые вакансии\n"
        "• Проверить структуру и читаемость\n\n"
        "💬 **Напишите текст резюме в чат ниже** ⬇️",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_career")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_career_plan(callback: CallbackQuery):
    """Получить план"""
    user_id = callback.from_user.id
    
    # АВТОМАТИЧЕСКИ ВЫБИРАЕМ КАРЬЕРНОГО ПОМОЩНИКА
    user_assistant[user_id] = 'career'
    database = _components['database']
    database.set_selected_assistant(user_id, 'career')
    
    await callback.message.edit_text(
        "🎯 **Получить персональный план**\n\n"
        "Опишите:\n"
        "• Вашу текущую ситуацию (доход, опыт, навыки)\n"
        "• Цель (желаемый доход, сфера, формат работы)\n"
        "• Ограничения (время, локация, семейные обстоятельства)\n\n"
        "Я составлю пошаговый план на 14-30 дней с метриками контроля.\n\n"
        "💬 **Напишите описание вашей ситуации в чат ниже** ⬇️",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_career")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

async def handle_text_message(message: types.Message):
    """Обработка текстового сообщения"""
    user_id = message.from_user.id
    query = message.text
    
    database = _components['database']
    gigachat_service = _components['gigachat_service']
    knowledge_base = _components.get('knowledge_base')
    
    # ❌ БЛОК ПРОВЕРКИ ЛИМИТОВ УДАЛЁН — вопросы без ограничений
    
    # Определяем выбранного ассистента
    assistant_type = user_assistant.get(user_id)
    if not assistant_type:
        assistant_type = database.get_selected_assistant(user_id)
        user_assistant[user_id] = assistant_type
    
    # Если ассистент не выбран — предлагаем выбрать
    if not assistant_type:
        await message.answer(
            "🎯 Сначала выберите помощника в меню выше ⬆️",
            reply_markup=get_main_menu()
        )
        return
    
    # Отправляем сообщение о процессе
    processing_msg = await message.answer("⏳ Обрабатываю ваш вопрос...")
    
    try:
        # Получаем ответ от GigaChat
        answer, response_time = await gigachat_service.ask(
            query=query,
            assistant_type=assistant_type,
            knowledge_base=knowledge_base,
            use_kb=True
        )
        
        # Сохраняем в БД (без инкремента лимитов)
        database.save_message(user_id, assistant_type, query, answer, response_time)
        # database.increment_daily_usage(user_id)  # ← закомментировано: лимиты отключены
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # ✅ Отправляем ответ БЕЗ футера с лимитами
        await message.answer(
            sanitize_markdown(answer),
            parse_mode="Markdown"
        )
        
    except TelegramBadRequest as e:
        logging.warning(f"Telegram API error: {e}")
        await processing_msg.edit_text(
            "⚠️ Ошибка форматирования ответа. Попробуйте задать вопрос иначе."
        )
    except Exception as e:
        logging.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
        await processing_msg.edit_text(
            "😔 Произошла ошибка при обработке вопроса. Попробуйте еще раз."
        )


# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def main():
    """Главная функция"""
    # Инициализация компонентов
    if not await init_components():
        logging.error("❌ Не удалось инициализировать компоненты")
        return
    
    # Создание бота
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация команд
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_menu, Command("menu"))
    dp.message.register(cmd_stats, Command("stats"))
    
    # Регистрация callback обработчиков: ОСНОВНЫЕ
    dp.callback_query.register(
        handle_assistant_selection, 
        F.data.startswith("assistant_")
    )
    dp.callback_query.register(handle_show_tests, F.data == "show_tests")
    dp.callback_query.register(handle_my_stats, F.data == "my_stats")  # сохранён для совместимости
    dp.callback_query.register(handle_back_to_menu, F.data == "back_to_menu")
    
    # Регистрация обработчиков: НОВЫЕ МЕНЮ (ИЕРАРХИЯ)
    dp.callback_query.register(handle_menu_career, F.data == "menu_career")
    dp.callback_query.register(handle_menu_support, F.data == "menu_support")
    dp.callback_query.register(handle_menu_tools, F.data == "menu_tools")
    dp.callback_query.register(handle_about_bot, F.data == "about_bot")
    
    # Регистрация обработчиков: ПОДМЕНЮ КАРЬЕРНОГО ПОМОЩНИКА (ОБНОВЛЁННЫЕ)
    dp.callback_query.register(handle_career_diagnostics, F.data == "career_diagnostics")
    dp.callback_query.register(handle_career_resume, F.data == "career_resume")
    dp.callback_query.register(handle_career_plan, F.data == "career_plan")
    
    # Регистрация обработчика текстовых сообщений
    dp.message.register(handle_text_message, F.text)
    
    # Установка команд в меню бота (только /start)
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Начать работу"),
    ])
    
    logging.info("✅ Бот запущен с иерархическим меню (лимиты отключены)!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logging.critical(f"❌ Критическая ошибка запуска: {e}", exc_info=True)