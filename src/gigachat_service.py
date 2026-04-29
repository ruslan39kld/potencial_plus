"""
GigaChat Service для HR Career Bot
Адаптирован под проект Potencial Plus
"""
import asyncio
import logging
import time
import re
from typing import Tuple, List, Dict
from gigachat import GigaChat
import config


class GigaChatService:
    """Сервис для работы с GigaChat API"""
    
    # Семафор для ограничения параллельных запросов
    _semaphore = asyncio.Semaphore(5)
    
    def __init__(self):
        self.auth_key = config.GIGACHAT_CLIENT_SECRET
        self.scope = config.GIGACHAT_SCOPE
        self.model = config.GIGACHAT_MODEL
        
        if not self.auth_key:
            logging.error("❌ GIGACHAT_CLIENT_SECRET не найден!")
            raise ValueError("GIGACHAT_CLIENT_SECRET не установлен")
        
        logging.info(f"[GigaChat] ✅ Инициализация: model={self.model}, scope={self.scope}")
    
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
        """Формирование контекста из базы знаний"""
        if not docs:
            return ""
        
        context_parts = []
        for i, doc in enumerate(docs[:3], 1):
            question = doc.get('question', '')
            answer = doc.get('answer', '')
            
            if question and answer:
                context_parts.append(f"Документ {i}:\nВопрос: {question}\nОтвет: {answer}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, assistant_type: str, context: str = "") -> str:
        """Построение промпта для GigaChat"""
        system_prompt = config.SYSTEM_PROMPTS.get(assistant_type, config.SYSTEM_PROMPTS['career'])
        
        if context:
            prompt = f"""{system_prompt}

Контекст из базы знаний:
{context}

Вопрос пользователя: {query}

Ответь на вопрос, используя информацию из контекста и свои знания. Будь конкретным и практичным."""
        else:
            prompt = f"""{system_prompt}

Вопрос пользователя: {query}

Ответь на вопрос. Будь конкретным и практичным."""
        
        return prompt
    
    async def ask(self, 
                  query: str, 
                  assistant_type: str = 'career',
                  knowledge_base = None,
                  use_kb: bool = True) -> Tuple[str, int]:
        """
        Отправка запроса к GigaChat
        
        Args:
            query: Вопрос пользователя
            assistant_type: Тип ассистента (career, finance, psychology, legal, safety)
            knowledge_base: Объект базы знаний (опционально)
            use_kb: Использовать ли базу знаний
        
        Returns:
            (ответ, время_ответа_в_мс)
        """
        async with self._semaphore:
            start_time = time.time()
            logging.info(f"[GigaChat] ========== НОВЫЙ ЗАПРОС ==========")
            logging.info(f"[GigaChat] Ассистент: {assistant_type}")
            logging.info(f"[GigaChat] Запрос: '{query}'")
            
            context = ""
            
            # Если есть база знаний и нужно её использовать
            if use_kb and knowledge_base:
                try:
                    docs = knowledge_base.search(query, top_k=3)
                    if docs:
                        context = self._build_context_from_kb(docs)
                        logging.info(f"[GigaChat] Найдено документов: {len(docs)}")
                except Exception as e:
                    logging.warning(f"[GigaChat] Ошибка поиска в БЗ: {e}")
            
            # Формируем промпт
            prompt = self._build_prompt(query, assistant_type, context)
            
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
                    
                    # Очищаем markdown
                    answer = self.sanitize_markdown(answer)
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    logging.info(f"[GigaChat] ✅ Ответ получен: {len(answer)} символов | {response_time_ms}ms")
                    
                    return answer, response_time_ms
            
            except Exception as e:
                logging.error(f"[GigaChat] ❌ Ошибка: {e}", exc_info=True)
                return self._fallback_response(query, assistant_type), int((time.time() - start_time) * 1000)
    
    def _fallback_response(self, query: str, assistant_type: str) -> str:
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
