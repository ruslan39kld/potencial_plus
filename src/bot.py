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
# ГЛАВНОЕ МЕНЮ
# ============================================================

def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Карьерный помощник", callback_data="assistant_career"),
        ],
        [
            InlineKeyboardButton(text="💰 Финансовый план", callback_data="assistant_finance"),
        ],
        [
            InlineKeyboardButton(text="🧠 Психолог", callback_data="assistant_psychology"),
        ],
        [
            InlineKeyboardButton(text="⚖️ Юрист", callback_data="assistant_legal"),
            InlineKeyboardButton(text="🛡️ Безопасность", callback_data="assistant_safety"),
        ],
        [
            InlineKeyboardButton(text="📋 Пройти тесты", callback_data="show_tests"),
        ],
        [
            InlineKeyboardButton(text="📊 Вакансии", url=config.PLATFORMS['jobs']),
            InlineKeyboardButton(text="🌍 Международные", url=config.PLATFORMS['international']),
        ],
        [
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about_project"),
            InlineKeyboardButton(text="📈 Моя статистика", callback_data="my_stats"),
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
        "👋 **Добро пожаловать в Potencial Plus!**\n\n"
        "Я помогу вам:\n"
        "• Построить карьерный план\n"
        "• Сформировать финансовую подушку\n"
        "• Найти вахтовую или международную работу\n"
        "• Преодолеть страх перемен\n"
        "• Разобраться в трудовых вопросах\n\n"
        "**Выберите помощника ниже ⬇️**",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


async def cmd_help(message: types.Message):
    """Команда /help"""
    await message.answer(
        "📖 **Как пользоваться ботом:**\n\n"
        "**1. Выберите ассистента**\n"
        "Каждый ассистент специализируется на своей области:\n"
        "• 🎯 Карьерный - подбор профессий и треков\n"
        "• 💰 Финансовый - расчет накоплений\n"
        "• 🧠 Психолог - работа со страхами\n"
        "• ⚖️ Юрист - трудовые вопросы\n"
        "• 🛡️ Безопасность - проверка вакансий\n\n"
        "**2. Задавайте вопросы**\n"
        "Просто напишите свой вопрос в чат\n\n"
        "**3. Проходите тесты**\n"
        "Узнайте свои сильные стороны\n\n"
        "**Лимиты:**\n"
        f"• Бесплатно: {config.FREE_QUESTIONS_PER_DAY} вопросов/день\n"
        f"• Всего в неделю: {config.FREE_QUESTIONS_PER_WEEK} вопросов\n\n"
        "Используйте /menu для вызова меню",
        parse_mode="Markdown"
    )


async def cmd_menu(message: types.Message):
    """Команда /menu"""
    await message.answer(
        "Выберите действие:",
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
# ОБРАБОТЧИКИ CALLBACK
# ============================================================

async def handle_assistant_selection(callback: CallbackQuery):
    """Выбор ассистента"""
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


async def handle_about_project(callback: CallbackQuery):
    """О проекте"""
    about_text = (
        "🎯 **Potencial Plus** — федеральный проект карьерного роста\n\n"
        "**Мы помогаем:**\n"
        "• Выйти из низкодоходного хаоса\n"
        "• Построить четкий карьерный план\n"
        "• Сформировать финансовую подушку\n"
        "• Использовать вахту как инструмент роста\n"
        "• Выйти на международный рынок труда\n\n"
        "**Наши платформы:**\n"
        f"• Основной сайт: {config.PLATFORMS['main']}\n"
        f"• Вакансии: {config.PLATFORMS['jobs']}\n"
        f"• Международные: {config.PLATFORMS['international']}\n\n"
        "**Целевая аудитория:**\n"
        "Россияне с доходом до 100 000 руб/мес\n\n"
        "**Приоритетные профессии:**\n"
    )
    
    for prof in config.TARGET_PROFESSIONS:
        about_text += f"• {prof}\n"
    
    await callback.message.edit_text(
        about_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    await callback.answer()


async def handle_my_stats(callback: CallbackQuery):
    """Моя статистика"""
    user_id = callback.from_user.id
    database = _components['database']
    
    # Проверяем лимиты
    can_ask, remaining = database.check_daily_limit(user_id, config.FREE_QUESTIONS_PER_DAY)
    weekly_usage = database.get_weekly_usage(user_id)
    
    # История
    history = database.get_user_history(user_id, limit=5)
    
    # Пройденные тесты
    completed_tests = database.get_completed_tests(user_id)
    
    stats_text = (
        f"📈 **Ваша статистика**\n\n"
        f"**Использование:**\n"
        f"• Осталось сегодня: {remaining} вопросов\n"
        f"• За неделю: {weekly_usage} вопросов\n"
        f"• Всего диалогов: {len(history)}\n\n"
        f"**Пройдено тестов:** {len(completed_tests)}\n"
    )
    
    if completed_tests:
        stats_text += "\n".join([f"✅ {test}" for test in completed_tests[:3]])
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    
    await callback.answer()


async def handle_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_main_menu()
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
    
    # Проверяем лимиты
    can_ask, remaining = database.check_daily_limit(user_id, config.FREE_QUESTIONS_PER_DAY)
    
    if not can_ask:
        await message.answer(
            f"😔 Вы достигли дневного лимита вопросов.\n\n"
            f"Бесплатный лимит: {config.FREE_QUESTIONS_PER_DAY} вопросов/день\n\n"
            "Приходите завтра или оформите Premium для безлимитного доступа!",
            parse_mode="Markdown"
        )
        return
    
    # Определяем выбранного ассистента
    assistant_type = user_assistant.get(user_id)
    if not assistant_type:
        assistant_type = database.get_selected_assistant(user_id)
        user_assistant[user_id] = assistant_type
    
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
        
        # Сохраняем в БД
        database.save_message(user_id, assistant_type, query, answer, response_time)
        database.increment_daily_usage(user_id)
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # Отправляем ответ
        footer = f"\n\n💡 Осталось вопросов сегодня: {remaining - 1}"
        
        await message.answer(
            sanitize_markdown(answer) + footer,
            parse_mode="Markdown"
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
    
    # Регистрация callback обработчиков
    dp.callback_query.register(
        handle_assistant_selection, 
        F.data.startswith("assistant_")
    )
    dp.callback_query.register(handle_show_tests, F.data == "show_tests")
    dp.callback_query.register(handle_about_project, F.data == "about_project")
    dp.callback_query.register(handle_my_stats, F.data == "my_stats")
    dp.callback_query.register(handle_back_to_menu, F.data == "back_to_menu")
    
    # Регистрация обработчика текстовых сообщений
    dp.message.register(handle_text_message, F.text)
    
    # Установка команд в меню бота
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="help", description="❓ Помощь"),
    ])
    
    logging.info("✅ Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен")