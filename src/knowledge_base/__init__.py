"""
Модуль базы знаний для HR Career Bot
Загружает промты и предоставляет их для использования в боте
"""

from .loader import (
    KnowledgeBaseLoader,
    get_loader,
    get_system_prompt
)

__all__ = [
    'KnowledgeBaseLoader',
    'get_loader', 
    'get_system_prompt'
]