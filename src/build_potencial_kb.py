"""
Скрипт для обработки Excel файлов проекта Potencial Plus
Извлекает данные о сегментах аудитории и создает базу знаний
"""
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict


class PotencialPlusKnowledgeProcessor:
    """Обработчик знаний для проекта Potencial Plus"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.knowledge_base_dir = self.data_dir / "knowledge_base"
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_file = self.knowledge_base_dir / "potencial_plus_kb.json"
    
    def process_segments_file(self, file_path: str) -> List[Dict]:
        """
        Обработка файла с сегментами аудитории
        """
        print(f"\n📊 Обработка файла: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
            print(f"Размер таблицы: {df.shape}")
            print(f"Колонки: {list(df.columns)[:5]}")
            
            segments = []
            
            # Обрабатываем каждую строку как потенциальный сегмент
            for idx, row in df.iterrows():
                # Извлекаем информацию о сегменте
                segment_data = {}
                
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() and str(val) != 'nan':
                        segment_data[str(col)] = str(val).strip()
                
                if segment_data:
                    segments.append({
                        "type": "segment",
                        "data": segment_data,
                        "source": Path(file_path).name
                    })
            
            print(f"✅ Извлечено сегментов: {len(segments)}")
            return segments
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return []
    
    def process_description_file(self, file_path: str) -> List[Dict]:
        """
        Обработка текстового файла с описанием проекта
        """
        print(f"\n📝 Обработка описания проекта: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбиваем по секциям
            sections = content.split('________________________________________')
            
            knowledge_items = []
            
            for section in sections:
                section = section.strip()
                if len(section) < 100:
                    continue
                
                # Извлекаем заголовок (первая строка)
                lines = section.split('\n')
                title = lines[0].strip() if lines else "Без названия"
                body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else section
                
                knowledge_items.append({
                    "type": "project_info",
                    "title": title,
                    "content": body,
                    "source": Path(file_path).name
                })
            
            print(f"✅ Извлечено секций: {len(knowledge_items)}")
            return knowledge_items
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return []
    
    def create_qa_pairs_from_project_info(self, project_info: List[Dict]) -> List[Dict]:
        """
        Создание Q&A пар из информации о проекте
        """
        print("\n🔄 Создание Q&A пар из описания проекта...")
        
        qa_pairs = []
        
        # Список вопросов на основе структуры проекта
        question_templates = {
            "Миссия проекта": [
                "Какая миссия у проекта Potencial Plus?",
                "В чем суть проекта?",
                "Чем занимается Potencial Plus?"
            ],
            "Основная идея проекта": [
                "В чем основная идея проекта?",
                "Почему вахтовая работа?",
                "Как вахта помогает росту?"
            ],
            "Кому нужен проект": [
                "Кто целевая аудитория?",
                "Для кого этот проект?",
                "Кому подходит Potencial Plus?"
            ],
            "AI-ассистентов": [
                "Какие есть AI-ассистенты?",
                "Как работают ассистенты?",
                "Какая помощь от ботов?"
            ],
            "Вахтовая модель": [
                "Почему именно вахта?",
                "Как вахта помогает накопить?",
                "Преимущества вахтовой работы?"
            ],
            "Финансовый": [
                "Что такое финансовая подушка?",
                "Как накопить деньги?",
                "Сколько нужно накопить?"
            ]
        }
        
        for item in project_info:
            title = item.get('title', '')
            content = item.get('content', '')
            
            # Ищем подходящие вопросы
            questions = []
            for keyword, templates in question_templates.items():
                if keyword.lower() in title.lower():
                    questions = templates
                    break
            
            if not questions:
                # Создаем базовый вопрос из заголовка
                questions = [f"Расскажи про: {title}"]
            
            for question in questions:
                qa_pairs.append({
                    "type": "qa",
                    "question": question,
                    "answer": content,
                    "category": "project_info",
                    "source": item.get('source', 'описание.txt')
                })
        
        print(f"✅ Создано Q&A пар: {len(qa_pairs)}")
        return qa_pairs
    
    def save_knowledge_base(self, all_data: List[Dict]):
        """Сохранение базы знаний в JSON"""
        print(f"\n💾 Сохранение базы знаний в {self.output_file}")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total_items": len(all_data),
                "items": all_data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Сохранено: {len(all_data)} элементов")
    
    def process_all(self, excel_files: List[str] = None, text_files: List[str] = None):
        """
        Обработка всех файлов
        """
        print("="*60)
        print("🚀 ОБРАБОТКА БАЗЫ ЗНАНИЙ POTENCIAL PLUS")
        print("="*60)
        
        all_knowledge = []
        
        # Обработка Excel файлов
        if excel_files:
            for file_path in excel_files:
                segments = self.process_segments_file(file_path)
                all_knowledge.extend(segments)
        
        # Обработка текстовых файлов
        if text_files:
            for file_path in text_files:
                project_info = self.process_description_file(file_path)
                
                # Добавляем как есть
                all_knowledge.extend(project_info)
                
                # Создаем Q&A пары
                qa_pairs = self.create_qa_pairs_from_project_info(project_info)
                all_knowledge.extend(qa_pairs)
        
        # Сохраняем все
        self.save_knowledge_base(all_knowledge)
        
        print("\n" + "="*60)
        print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
        print("="*60)
        print(f"📊 Всего элементов: {len(all_knowledge)}")
        print(f"📁 Файл: {self.output_file}")
        print("="*60)


def main():
    """Главная функция"""
    processor = PotencialPlusKnowledgeProcessor()
    
    # Укажите пути к вашим файлам
    excel_files = [
        # "path/to/Николай_Каплунов_Потенциал___-_проработка_ДЗ.xlsx",
        # "path/to/потенциал__сгмент_-спринт.xlsx"
    ]
    
    text_files = [
        # "path/to/описание.txt",
        # "path/to/инфо.txt"
    ]
    
    # Если файлы в uploads
    import os
    uploads_dir = "/mnt/user-data/uploads"
    if os.path.exists(uploads_dir):
        for file in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, file)
            if file.endswith('.xlsx'):
                excel_files.append(file_path)
            elif file.endswith('.txt'):
                text_files.append(file_path)
    
    processor.process_all(excel_files, text_files)


if __name__ == "__main__":
    main()
