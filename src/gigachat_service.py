"""
GigaChat Service для HR Career Bot
ВЕРСИЯ 2.3 - Агрессивное ограничение длины ответа + компактный промпт
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


QUESTION_TREES = {
    "поиск_работы": [
        "Какой доход хотите получать?",
        "В какой сфере есть опыт?",
        "Как срочно нужна работа?",
        "Готовы к вахте или только в своём городе?",
        "Есть ли финансовые обязательства (долги)?"
    ],
    "резюме": [
        "Есть ли уже резюме или делаем с нуля?",
        "Какая ваша профессия и опыт?",
        "Какие были достижения на работе?",
        "На какую должность хотите откликаться?"
    ],
    "финансы": [
        "Какой сейчас доход?",
        "Есть ли долги? Какая сумма?",
        "Сколько нужно в месяц на жизнь минимум?",
        "Какую цель по накоплениям ставите?"
    ],
    "психология": [
        "Что именно вас беспокоит больше всего?",
        "Как давно появилась эта тревога?",
        "Что мешает сделать первый шаг?"
    ],
    "юридическая": [
        "О каком именно документе или ситуации идёт речь?",
        "Уже есть подписанный договор или только предлагают?",
        "Что именно вызывает сомнения?"
    ],
    "общий": [
        "Расскажите подробнее о вашей ситуации.",
        "Какой результат вы хотите получить?",
        "Что уже пробовали сделать?"
    ]
}


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
        
        # 🚨 АГРЕССИВНЫЕ ТРЕБОВАНИЯ К ОТВЕТУ — УСИЛЕННЫЙ КОНТРОЛЬ ДЛИНЫ
        length_constraint = f"""
🚨 КРИТИЧЕСКИ ВАЖНО — ОГРАНИЧЕНИЕ ДЛИНЫ:

ТВОЙ ОТВЕТ ДОЛЖЕН БЫТЬ РОВНО {self.MIN_RESPONSE_LENGTH}-{self.MAX_RESPONSE_LENGTH} СИМВОЛОВ.
НЕ БОЛЬШЕ {self.MAX_RESPONSE_LENGTH} СИМВОЛОВ. ЭТО ЖЁСТКОЕ ОГРАНИЧЕНИЕ.

Если ответ получается длиннее — ОСТАНОВИ ГЕНЕРАЦИЮ НА {self.MAX_RESPONSE_LENGTH} СИМВОЛАХ.

СТРУКТУРА:
- Markdown: **жирный**, списки (•)
- Абзацы 2-3 предложения
- БЕЗ лишних пробелов

СТИЛЬ:
- Конкретно, с цифрами
- Без воды

ПРИМЕР (КОРОТКИЙ):
**Как преодолеть страх:**

**1. Подготовьтесь заранее**
Список вопросов, репетиция перед зеркалом.

**2. Используйте технику "переключения"**
Напомните себе: начальник тоже человек.

**3. Дышите уверенно**
Глубокое дыхание успокаивает нервную систему.

**Итого:** Подготовка + техника + дыхание = уверенность.

ПОМНИ: МАКСИМУМ {self.MAX_RESPONSE_LENGTH} СИМВОЛОВ!
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

    def classify_request(self, message: str) -> str:
        """Определяет тип запроса пользователя"""
        message_lower = message.lower()
        if any(w in message_lower for w in ["работ", "вакан", "трудоустр", "найти работу", "ищу работу"]):
            return "поиск_работы"
        elif any(w in message_lower for w in ["резюме", "cv", "портфолио"]):
            return "резюме"
        elif any(w in message_lower for w in ["где смотреть", "где искать", "платформ", "сайт", "hh", "superjob", "tempojob"]):
            return "вакансии_ссылки"
        elif any(w in message_lower for w in ["деньг", "долг", "финанс", "копить", "накоп", "бюджет"]):
            return "финансы"
        elif any(w in message_lower for w in ["страшно", "боюсь", "тревож", "страх", "нервничаю"]):
            return "психология"
        elif any(w in message_lower for w in ["договор", "права", "юрид", "тк рф", "трудовой"]):
            return "юридическая"
        else:
            return "общий"

    def _build_deep_support_prompt(self, request_type: str, dialog_level: int, history: list) -> str:
        """Создаёт промпт с инструкциями для глубокого сопровождения"""
        base_prompt = """Ты — карьерный консультант проекта Potencial Plus.

ВАЖНО:
1. Отвечай коротко (до 1000 символов)
2. Задавай уточняющие вопросы постепенно — по одному за раз
3. Давай конкретные советы, а не общие фразы
4. Веди диалог до конкретного плана действий
5. Реагируй на эмоции пользователя с поддержкой

СТРУКТУРА ОТВЕТА:
1. Краткий совет или реакция (2-3 предложения)
2. Один уточняющий вопрос (если нужно)
3. Предложение следующего шага
"""
        if request_type == "вакансии_ссылки":
            base_prompt += """\n\nПОЛЕЗНЫЕ РЕСУРСЫ:
- tempojob.org — вахтовые вакансии
- russian.works — международные возможности
- hh.ru, SuperJob — основные площадки

Дай ссылки и спроси, что именно ищет человек."""

        if dialog_level == 0:
            base_prompt += "\n\nЭто первое сообщение — установи тёплый контакт, задай 1-2 уточняющих вопроса."
        elif dialog_level < 5:
            base_prompt += f"\n\nУровень диалога: {dialog_level}. Продолжай уточнять детали, не торопись с советами."
        else:
            base_prompt += "\n\nДостаточно информации — дай конкретный пошаговый план действий."

        return base_prompt

    async def gigachat_api_call(self, system_prompt: str, user_message: str, history: list) -> str:
        """Вызов GigaChat API с учётом истории диалога"""
        history_context = ""
        if history:
            recent = history[-6:]
            parts = []
            for msg in recent:
                role_label = "Пользователь" if msg.get("role") == "user" else "Ассистент"
                content = msg.get("content", "")[:300]
                parts.append(f"{role_label}: {content}")
            history_context = "\n\nИСТОРИЯ ДИАЛОГА:\n" + "\n".join(parts)

        full_prompt = system_prompt + history_context + f"\n\nПОЛЬЗОВАТЕЛЬ: {user_message}\n\nОТВЕТ:"

        with GigaChat(
            credentials=self.auth_key,
            scope=self.scope,
            model=self.model,
            verify_ssl_certs=False
        ) as giga:
            response = giga.chat(full_prompt)
            return response.choices[0].message.content

    async def get_context_aware_response(self, user_message: str, history: list, user_id: int) -> str:
        """Генерирует ответ с глубоким сопровождением и уточняющими вопросами"""
        async with self._semaphore:
            start_time = time.time()
            request_type = self.classify_request(user_message)
            dialog_level = len(history)

            logging.info(f"[GigaChat] context_aware: type={request_type}, level={dialog_level}, user={user_id}")

            system_prompt = self._build_deep_support_prompt(request_type, dialog_level, history)

            if dialog_level < 5:
                clarifying = QUESTION_TREES.get(request_type, QUESTION_TREES["общий"])
                system_prompt += f"\n\nУточняющие вопросы (задай один из них при необходимости): {clarifying}"
            else:
                system_prompt += "\n\nТеперь дай конкретный план действий на основе собранной информации."

            try:
                response = await self.gigachat_api_call(system_prompt, user_message, history)

                if len(response) > 1000:
                    truncated = response[:950]
                    last_period = truncated.rfind('.')
                    if last_period > 500:
                        response = truncated[:last_period + 1]
                    else:
                        response = truncated.rsplit(' ', 1)[0] + '.'

                response = self.sanitize_markdown(response)
                ms = int((time.time() - start_time) * 1000)
                logging.info(f"[GigaChat] context_aware done: {len(response)} chars, {ms}ms")
                return response

            except Exception as e:
                logging.error(f"[GigaChat] get_context_aware_response error: {e}", exc_info=True)
                return self._fallback_response('career')