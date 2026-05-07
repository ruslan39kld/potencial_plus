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
from aiogram.types import BotCommand
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
bot_instance = None
# user_assistant removed — bot uses context-aware routing without explicit selection


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
# КОМАНДЫ БОТА
# ============================================================

async def cmd_start(message: types.Message):
    """Команда /start"""
    user_id = message.from_user.id
    database = _components['database']

    database.register_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    await message.answer(
        '👋 Добро пожаловать на интеллектуальную платформу "Карьерный консультант"\n\n'
        'Я помогу вам:\n'
        '- Построить карьерный план\n'
        '- Сформировать финансовую подушку\n'
        '- Найти вахтовую или международную работу\n'
        '- Преодолеть страх перемен\n'
        '- Разобраться в трудовых вопросах\n\n'
        '💬 Чем могу Вам помочь?'
    )


async def cmd_help(message: types.Message):
    """Команда /help"""
    await message.answer(
        '📖 Как пользоваться ботом:\n\n'
        'Просто напишите свой вопрос в чат. Я умею помогать с:\n'
        '• Поиском работы и карьерным планированием\n'
        '• Составлением и усилением резюме\n'
        '• Финансовым планированием и выходом из долгов\n'
        '• Психологической поддержкой при смене работы\n'
        '• Трудовыми вопросами и проверкой вакансий\n\n'
        'Начните с /start или просто задайте вопрос!'
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
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

async def handle_message(message: types.Message):
    """Обработка текстового сообщения с глубоким сопровождением"""
    user_id = message.from_user.id
    user_message = message.text

    database = _components['database']
    gigachat_service = _components['gigachat_service']

    await bot_instance.send_chat_action(message.chat.id, "typing")

    history = database.get_conversation_history(user_id, limit=10)

    response = await gigachat_service.get_context_aware_response(
        user_message=user_message,
        history=history,
        user_id=user_id
    )

    database.save_conversation_message(user_id, "user", user_message)
    database.save_conversation_message(user_id, "assistant", response)

    current_level = database.get_dialog_level(user_id)
    database.update_dialog_level(user_id, current_level + 1)

    await message.answer(sanitize_markdown(response), parse_mode="Markdown")


# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def main():
    """Главная функция"""
    global bot_instance

    if not await init_components():
        logging.error("❌ Не удалось инициализировать компоненты")
        return

    bot_instance = Bot(token=config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(handle_message, F.text & ~F.text.startswith('/'))

    await bot_instance.set_my_commands([
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="help", description="📖 Помощь"),
    ])

    logging.info("✅ Бот запущен (режим глубокого сопровождения, без кнопок)!")

    try:
        await dp.start_polling(bot_instance)
    finally:
        await bot_instance.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logging.critical(f"❌ Критическая ошибка запуска: {e}", exc_info=True)