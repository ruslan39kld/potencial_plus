"""
Загрузчик базы знаний для HR Career Bot
Загружает все промт-файлы из папки prompts/
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Загрузчик базы знаний из текстовых файлов"""
    
    # Порядок загрузки файлов (важно!)
    PROMPT_FILES = [
        "DIALOG_MODE_PROMT.txt",                    # 1. КАК говорить
        "PROMT_AI_CAREER_CONSULTANT_V2.txt",        # 2. База знаний
        "DECISION_TREES_AND_ALGORITHMS.txt",        # 3. Деревья решений
        "METRICS_AND_TRACKING.txt",                 # 4. Метрики
        "TEMPLATES_AND_ADVANCED_SCRIPTS.txt"        # 5. Шаблоны
    ]
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Инициализация загрузчика
        
        Args:
            prompts_dir: Путь к папке с промтами. 
                        Если None, использует src/knowledge_base/prompts/
        """
        if prompts_dir is None:
            # Определяем путь относительно этого файла
            self.prompts_dir = Path(__file__).parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        self.prompts: Dict[str, str] = {}
        self.combined_prompt: str = ""
        
        logger.info(f"📁 Путь к промтам: {self.prompts_dir}")
    
    def load_all(self) -> bool:
        """
        Загружает все промт-файлы
        
        Returns:
            bool: True если загрузка успешна, False если ошибка
        """
        if not self.prompts_dir.exists():
            logger.error(f"❌ Папка {self.prompts_dir} не найдена!")
            return False
        
        logger.info("🔄 Начинаю загрузку базы знаний...")
        
        loaded_count = 0
        
        for filename in self.PROMPT_FILES:
            filepath = self.prompts_dir / filename
            
            if not filepath.exists():
                logger.warning(f"⚠️  Файл не найден: {filename}")
                continue
            
            try:
                # Читаем файл
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Сохраняем
                self.prompts[filename] = content
                loaded_count += 1
                
                logger.info(f"✅ Загружен: {filename} ({len(content)} символов)")
                
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {filename}: {e}")
                return False
        
        if loaded_count == 0:
            logger.error("❌ Не загружено ни одного промт-файла!")
            return False
        
        # Объединяем все промты в один
        self._combine_prompts()
        
        logger.info(f"✅ База знаний загружена: {loaded_count}/{len(self.PROMPT_FILES)} файлов")
        logger.info(f"📊 Общий размер: {len(self.combined_prompt)} символов")
        
        return True
    
    def _combine_prompts(self):
        """Объединяет все промты в один большой промт"""
        parts = []
        
        for filename in self.PROMPT_FILES:
            if filename in self.prompts:
                parts.append(self.prompts[filename])
                parts.append("\n\n")  # Разделитель между файлами
        
        self.combined_prompt = "".join(parts)
    
    def get_combined_prompt(self) -> str:
        """
        Возвращает объединённый промт для использования в AI
        
        Returns:
            str: Полный промт со всей базой знаний
        """
        return self.combined_prompt
    
    def get_prompt(self, filename: str) -> Optional[str]:
        """
        Возвращает содержимое конкретного промт-файла
        
        Args:
            filename: Имя файла (например, "DIALOG_MODE_PROMT.txt")
        
        Returns:
            str или None: Содержимое файла или None если не найден
        """
        return self.prompts.get(filename)
    
    def get_stats(self) -> Dict[str, any]:
        """
        Возвращает статистику загруженной базы знаний
        
        Returns:
            dict: Статистика (количество файлов, размеры и т.д.)
        """
        return {
            'total_files': len(self.prompts),
            'expected_files': len(self.PROMPT_FILES),
            'total_characters': len(self.combined_prompt),
            'total_words': len(self.combined_prompt.split()),
            'files_loaded': list(self.prompts.keys())
        }


# Глобальный экземпляр (создаётся при первом импорте)
_loader = None


def get_loader() -> KnowledgeBaseLoader:
    """
    Возвращает глобальный экземпляр загрузчика (singleton)
    
    Returns:
        KnowledgeBaseLoader: Загрузчик базы знаний
    """
    global _loader
    
    if _loader is None:
        _loader = KnowledgeBaseLoader()
        _loader.load_all()
    
    return _loader


def get_system_prompt() -> str:
    """
    Возвращает полный системный промт для AI
    Удобная функция для быстрого использования
    
    Returns:
        str: Системный промт
    """
    loader = get_loader()
    return loader.get_combined_prompt()


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("ТЕСТ ЗАГРУЗЧИКА БАЗЫ ЗНАНИЙ")
    print("="*60 + "\n")
    
    # Создаём загрузчик
    loader = KnowledgeBaseLoader()
    
    # Загружаем файлы
    if loader.load_all():
        print("\n✅ ЗАГРУЗКА УСПЕШНА!\n")
        
        # Показываем статистику
        stats = loader.get_stats()
        print("📊 СТАТИСТИКА:")
        print(f"   Файлов загружено: {stats['total_files']}/{stats['expected_files']}")
        print(f"   Символов: {stats['total_characters']:,}")
        print(f"   Слов: {stats['total_words']:,}")
        print(f"\n📄 Загруженные файлы:")
        for filename in stats['files_loaded']:
            print(f"   ✓ {filename}")
        
        # Показываем начало промта
        prompt = loader.get_combined_prompt()
        print(f"\n📝 НАЧАЛО ПРОМТА (первые 500 символов):")
        print("-" * 60)
        print(prompt[:500])
        print("-" * 60)
        
    else:
        print("\n❌ ОШИБКА ЗАГРУЗКИ!\n")