"""
GigaChat Service для HR Career Bot
ВЕРСИЯ 2.2 - Оптимизированная длина ответа + компактный промпт
Адаптирован под проект Potencial Plus
"""
import asyncio
import logging
import time
import re
from typing import Tuple, List, Dict, Optional
from gigachat import GigaChat
import config

# ⭐ ИМПОРТ НОВОЙ БАЗЫ ЗНАНИЙ
from knowledge_base import get_system_prompt


class GigaChatService:
    """Сервис для работы с GigaChat API с новой базой знаний"""
    
    # Семафор для ограничения параллельных запросов
    _semaphore = asyncio.Semaphore(5)
    
    # ⭐ ОГРАНИЧЕНИЕ ДЛИНЫ ОТВЕТА (символы) — СТРОГО
    MIN_RESPONSE_LENGTH = 800
    MAX_RESPONSE_LENGTH = 1500
    
    def __init__(self):
        self.auth_key = config.GIGACHAT_CLIENT_SECRET
        self.scope = config.GIGACHAT_SCOPE
        self.model = config.GIGACHAT_MODEL
        
        if not self.auth_key:
            logging.error("❌ GIGACHAT_CLIENT_SECRET не найден!")
            raise ValueError("GIGACHAT_CLIENT_SECRET не установлен")
        
        # ⭐ ЗАГРУЖАЕМ НОВУЮ БАЗУ ЗНАНИЙ
        logging.info("📚 Загрузка базы знаний...")
        try:
            self.system_prompt = get_system_prompt()
            logging.info(f"✅ База знаний загружена: {len(self.system_prompt)} символов")
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки базы знаний: {e}")
            self.system_prompt = self._get_fallback_prompt()
            logging.warning("⚠️ Используется резервный промт")
        
        logging.info(f"[GigaChat] ✅ Инициализация: model={self.model}, scope={self.scope}")
    
    def _get_fallback_prompt(self) -> str:
        """Резервный промт если база знаний не загрузилась"""
        return """Ты — AI-карьерный консультант проекта Potencial Plus.

Твоя задача — помогать людям с доходом до 100,000₽ в месяц:
• Построить карьерный план
• Найти работу с ростом дохода
• Сформировать финансовую подушку
• Использовать вахту для быстрого накопления
• Преодолеть страх перемен

Отвечай конкретно, практично, по-человечески. Без канцелярита."""
    
    def sanitize_markdown(self, text: str) -> str:
        """Очистка и валидация Markdown"""
        # Удаляем HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Проверка **
        if text.count('**') % 2 != 0:
            text = text.replace('**', '')
        
        # Проверка *
        temp = text.replace('**', '__TEMP__')
        if temp.count('*') % 2 != 0:
            text = text.replace('*', '')
        
        # Убираем множественные переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ограничение длины (Telegram лимит)
        if len(text.encode('utf-8')) > 4096:
            text = text[:4000] + "\n\n... (сообщение обрезано)"
        
        return text.strip()
    
    def _build_context_from_kb(self, docs: List[Dict]) -> str:
        """Формирование контекста из старой базы знаний (Excel)"""
        if not docs:
            return ""
        
        context_parts = []
        for i, doc in enumerate(docs[:3], 1):
            question = doc.get('question', '')
            answer = doc.get('answer', '')
            
            if question and answer:
                context_parts.append(f"Пример {i}:\nВопрос: {question}\nОтвет: {answer}")
        
        return "\n\n".join(context_parts)
    
    def _get_role_context(self, assistant_type: str) -> str:
        """
        Получить контекст роли для текущего ассистента
        
        Args:
            assistant_type: career, finance, psychology, legal, safety
        
        Returns:
            str: Описание текущей роли
        """
        roles = {
            'career': """
╔═══════════════════════════════════════════════════════════════╗
║  РЕЖИМ РАБОТЫ: КАРЬЕРНЫЙ ПОМОЩНИК                             ║
╚═══════════════════════════════════════════════════════════════╝

Ты работаешь в режиме Карьерного помощника.

Твои специализации:
• Диагностика текущей ситуации клиента
• Определение типа клиента (Выживание/Стабилизация/Рост)
• Построение карьерных планов на 14-30-90 дней
• Подбор вакансий и стратегий роста
• Усиление резюме и подготовка к собеседованиям
• Работа с метриками поиска работы

Используй ВСЮ базу знаний ниже для работы с клиентом.
""",
            'finance': """
╔═══════════════════════════════════════════════════════════════╗
║  РЕЖИМ РАБОТЫ: ФИНАНСОВЫЙ ПОМОЩНИК                            ║
╚═══════════════════════════════════════════════════════════════╝

Ты работаешь в режиме Финансового помощника.

Твои специализации:
• Расчёт финансовой подушки
• Планирование накоплений
• Стратегии использования вахты для быстрого капитала
• Выход из долговой ямы
• Финансовое планирование на основе дохода клиента

Используй раздел "Финансовый AI-ассистент" из базы знаний.
""",
            'psychology': """
╔═══════════════════════════════════════════════════════════════╗
║  РЕЖИМ РАБОТЫ: ПСИХОЛОГИЧЕСКИЙ ПОМОЩНИК                       ║
╚═══════════════════════════════════════════════════════════════╝

Ты работаешь в режиме Психологического помощника.

Твои специализации:
• Работа со страхом перемен
• Снижение тревожности перед трудоустройством
• Поддержка мотивации
• Возвращение в действие
• Усиление уверенности и внутренней устойчивости

Используй раздел "Психологический AI-ассистент" из базы знаний.
""",
            'legal': """
╔═══════════════════════════════════════════════════════════════╗
║  РЕЖИМ РАБОТЫ: ЮРИДИЧЕСКИЙ ПОМОЩНИК                           ║
╚═══════════════════════════════════════════════════════════════╝

Ты работаешь в режиме Юридического помощника.

Твои специализации:
• Базовые трудовые вопросы
• Понимание документов и условий работы
• Типовые риски при трудоустройстве
• Когда нужно обращаться к юристу

Используй раздел "Юридический AI-ассистент" из базы знаний.
""",
            'safety': """
╔═══════════════════════════════════════════════════════════════╗
║  РЕЖИМ РАБОТЫ: ПОМОЩНИК ПО БЕЗОПАСНОСТИ                       ║
╚═══════════════════════════════════════════════════════════════╝

Ты работаешь в режиме Помощника по безопасности.

Твои специализации:
• Оценка рисков вакансий
• Проверка на мошенничество
• Красные флаги в предложениях о работе
• Безопасное поведение при трудоустройстве

Используй раздел "AI-ассистент по безопасности" из базы знаний.
"""
        }
        
        return roles.get(assistant_type, roles['career'])
    
    def _build_prompt(self, 
                     query: str, 
                     assistant_type: str, 
                     old_kb_context: str = "") -> str:
        """
        Построение полного промпта для GigaChat
        
        Args:
            query: Вопрос пользователя
            assistant_type: Тип ассистента
            old_kb_context: Контекст из старой базы знаний (опционально)
        
        Returns:
            str: Полный промпт для отправки в GigaChat
        """
        # Получаем контекст роли
        role_context = self._get_role_context(assistant_type)
        
        # ⭐ КОМПАКТНЫЕ ТРЕБОВАНИЯ К ОТВЕТУ
        length_constraint = f"""
❗ ТРЕБОВАНИЯ К ОТВЕТУ:

1. ДЛИНА: {self.MIN_RESPONSE_LENGTH}-{self.MAX_RESPONSE_LENGTH} символов СТРОГО
   - Длиннее → сократи
   - Короче → добавь примеры

2. СТРУКТУРА (обязательно):
   - Markdown: **жирный**, списки (1. 2. 3. или •)
   - Абзацы по 2-3 предложения
   - Подзаголовки для сложных тем
   - БЕЗ лишних пустых строк между разделами

3. СТИЛЬ:
   - Конкретно, с цифрами и примерами
   - Действия и шаги
   - Без воды

ПРИМЕР:
**Основные методики:**

**1. Преобразуйте обязанности в достижения**
Вместо "работал" → "увеличил продажи на 25%"

**2. Добавьте ключевые слова**
CRM (Битрикс24, amoCRM), управление командой, KPI

**3. Структурируйте разделы**
2-4 пункта на каждую должность, акцент на цифрах

**Итого:** 1-2 страницы, читается за 30 секунд
"""
        
        # Формируем финальный промпт (УЛЬТРА-КОМПАКТНАЯ ВЕРСИЯ)
        parts = [
            role_context,
            length_constraint,
            "",
            self.system_prompt,  # База знаний без лишних заголовков
            "",
        ]
        
        # Добавляем вопрос пользователя
        parts.extend([
            "",
            f"ВОПРОС: {query}",
            "",
            "ТВОЙ СТРУКТУРИРОВАННЫЙ ОТВЕТ:"
        ])
        
        return "\n".join(parts)
    
    async def ask(self, 
                  query: str, 
                  assistant_type: str = 'career',
                  knowledge_base = None,
                  use_kb: bool = True) -> Tuple[str, int]:
        """
        Отправка запроса к GigaChat с новой базой знаний
        
        Args:
            query: Вопрос пользователя
            assistant_type: Тип ассистента (career, finance, psychology, legal, safety)
            knowledge_base: Объект старой базы знаний Excel (опционально)
            use_kb: Использовать ли старую базу знаний
        
        Returns:
            (ответ, время_ответа_в_мс)
        """
        async with self._semaphore:
            start_time = time.time()
            logging.info(f"[GigaChat] ========== НОВЫЙ ЗАПРОС ==========")
            logging.info(f"[GigaChat] Ассистент: {assistant_type}")
            logging.info(f"[GigaChat] Запрос: '{query[:100]}...'")
            
            old_kb_context = ""
            
            # Если есть старая база знаний (Excel) — используем как примеры
            if use_kb and knowledge_base:
                try:
                    docs = knowledge_base.search(query, top_k=3)
                    if docs:
                        old_kb_context = self._build_context_from_kb(docs)
                        logging.info(f"[GigaChat] Найдено примеров: {len(docs)}")
                except Exception as e:
                    logging.warning(f"[GigaChat] Ошибка поиска в старой БЗ: {e}")
            
            # Формируем промпт (НОВАЯ БАЗА ЗНАНИЙ + роль + примеры + ограничение длины)
            prompt = self._build_prompt(query, assistant_type, old_kb_context)
            
            # Логируем размер промпта
            logging.info(f"[GigaChat] Размер промпта: {len(prompt)} символов")
            
            try:
                logging.info("[GigaChat] → Отправка запроса к GigaChat API...")
                
                # Используем официальную библиотеку GigaChat
                with GigaChat(
                    credentials=self.auth_key,
                    scope=self.scope,
                    model=self.model,
                    verify_ssl_certs=False
                ) as giga:
                    response = giga.chat(prompt)
                    answer = response.choices[0].message.content
                    
                    # ⭐ СТРОГАЯ ПРОВЕРКА ДЛИНЫ ОТВЕТА
                    if len(answer) > self.MAX_RESPONSE_LENGTH:
                        logging.warning(f"[GigaChat] Ответ превышает лимит ({len(answer)} симв.), обрезаем...")
                        # Обрезаем по последней точке в пределах лимита
                        truncated = answer[:self.MAX_RESPONSE_LENGTH - 50]  # -50 для запаса
                        last_period = truncated.rfind('.')
                        
                        if last_period > self.MIN_RESPONSE_LENGTH:
                            answer = truncated[:last_period + 1]
                            # Без текста "продолжение сокращено" — просто обрезаем
                        else:
                            # Обрезаем по последнему слову
                            answer = truncated.rsplit(' ', 1)[0] + '.'
                    
                    # Очищаем markdown
                    answer = self.sanitize_markdown(answer)
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    logging.info(f"[GigaChat] ✅ Ответ получен: {len(answer)} символов | {response_time_ms}ms")
                    
                    return answer, response_time_ms
            
            except Exception as e:
                logging.error(f"[GigaChat] ❌ Ошибка: {e}", exc_info=True)
                return self._fallback_response(assistant_type), int((time.time() - start_time) * 1000)
    
    def _fallback_response(self, assistant_type: str) -> str:
        """Резервный ответ при ошибке API"""
        fallback_messages = {
            'career': """К сожалению, сейчас у меня технические трудности с ответом. 

Но вот что я могу посоветовать:
• Изучите массовые профессии на платформе tempojob.org
• Рассмотрите вахтовые варианты для быстрого накопления
• Сформируйте финансовую подушку 3-6 месячных расходов

Попробуйте задать вопрос чуть позже или выберите другого ассистента.""",
            
            'finance': """Извините, сейчас у меня проблемы с подключением.

Базовые принципы финансового планирования:
• Финансовая подушка = 3-6 месячных расходов
• Вахта позволяет копить быстрее (минимум трат + высокий доход)
• Начните с малого - откладывайте 10% дохода

Попробуйте задать вопрос позже.""",
            
            'psychology': """Прошу прощения, сейчас я не могу дать полноценный ответ.

Базовые рекомендации:
• Страх перемен - это нормально
• Разбивайте большие цели на маленькие шаги
• Отмечайте даже малые достижения

Попробуйте обратиться позже.""",
            
            'legal': """К сожалению, сейчас возникли технические проблемы.

Базовые права работника:
• Трудовой договор обязателен
• Все условия должны быть прописаны
• При сомнениях - консультация юриста

Попробуйте задать вопрос позже.""",
            
            'safety': """Извините, сейчас не могу дать подробный ответ.

Базовые правила безопасности:
• Никогда не платите за трудоустройство
• Требуйте официальное оформление
• Проверяйте компанию перед выходом

Попробуйте обратиться позже."""
        }
        
        return fallback_messages.get(assistant_type, fallback_messages['career'])