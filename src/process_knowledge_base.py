# Упрощенная версия БЕЗ машинного обучения
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import PyPDF2
import docx

class Config:
    # Автоматическое определение путей
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    EXCEL_DIR = DATA_DIR / "excel_qa"
    INSTRUCTIONS_DIR = DATA_DIR / "instructions"
    QA_JSON = DATA_DIR / "structured_qa.json"
    CHUNKS_JSON = DATA_DIR / "chunks_data.json"

def process_excel_files():
    """Обработка Excel файлов"""
    print("\n📊 Обработка Excel файлов...")
    
    excel_files = list(Config.EXCEL_DIR.glob("*.xlsx"))
    print(f"Найдено {len(excel_files)} файлов")
    
    qa_pairs = []
    processed_files = 0
    
    for file in tqdm(excel_files, desc="Обработка"):
        file_count = 0
        try:
            # Читаем Excel БЕЗ заголовков
            df = pd.read_excel(file, header=None)
            
            print(f"\n📄 {file.name}")
            print(f"   Строк: {len(df)}, Колонок: {len(df.columns)}")
            
            if df.empty or len(df.columns) < 3:
                print(f"   ⚠️ Пропущен: мало колонок")
                continue
            
            # Находим строку с заголовками
            header_row = None
            question_col = None
            answer_col = None
            
            for idx, row in df.iterrows():
                row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
                if 'вопрос' in row_str and 'ответ' in row_str:
                    header_row = idx
                    for col_idx, val in enumerate(row):
                        val_str = str(val).lower()
                        if 'вопрос' in val_str:
                            question_col = col_idx
                        if 'ответ' in val_str:
                            answer_col = col_idx
                    break
            
            # Если не нашли, используем стандарт
            if question_col is None or answer_col is None:
                question_col = 1
                answer_col = 2
                header_row = 0
            
            print(f"   Вопрос: колонка {question_col}, Ответ: колонка {answer_col}")
            print(f"   Заголовок в строке: {header_row}")
            
            # Обрабатываем строки
            start_row = header_row + 1 if header_row is not None else 1
            
            for idx in range(start_row, len(df)):
                try:
                    q = str(df.iloc[idx, question_col]).strip()
                    a = str(df.iloc[idx, answer_col]).strip()
                    
                    if (q and a and 
                        q not in ['nan', 'None', '', 'NaT'] and 
                        a not in ['nan', 'None', '', 'NaT'] and
                        not q.isdigit() and
                        len(q) > 5 and len(a) > 10):
                        
                        qa_pairs.append({
                            "id": f"qa_{len(qa_pairs)+1:04d}",
                            "question": q.lower(),
                            "answer": a,
                            "source": file.name,
                            "keywords": [w for w in q.lower().split() if len(w) > 3]
                        })
                        file_count += 1
                except (IndexError, KeyError) as e:
                    continue
            
            print(f"   ✅ Извлечено: {file_count} пар")
            processed_files += 1
                        
        except Exception as e:
            print(f"\n❌ Ошибка в {file.name}: {e}")
    
    print(f"\n✅ ИТОГО: {len(qa_pairs)} пар Q&A из {processed_files} файлов")
    
    with open(Config.QA_JSON, 'w', encoding='utf-8') as f:
        json.dump({"qa_pairs": qa_pairs}, f, ensure_ascii=False, indent=2)
    
    return qa_pairs

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except:
        return ""

def extract_text_from_word(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n\n".join([para.text for para in doc.paragraphs])
        return text
    except:
        return ""

def process_instructions():
    """Обработка инструкций"""
    print("\n📚 Обработка инструкций...")
    
    pdf_files = list(Config.INSTRUCTIONS_DIR.glob("*.pdf"))
    word_files = list(Config.INSTRUCTIONS_DIR.glob("*.docx"))
    all_files = pdf_files + word_files
    
    print(f"Найдено {len(all_files)} файлов")
    
    chunks = []
    
    for file in tqdm(all_files, desc="Обработка"):
        try:
            if file.suffix == '.pdf':
                text = extract_text_from_pdf(file)
            else:
                text = extract_text_from_word(file)
            
            if text:
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                for i, para in enumerate(paragraphs):
                    if len(para) > 50:
                        chunks.append({
                            "id": f"chunk_{len(chunks)+1:05d}",
                            "text": para,
                            "source": file.name,
                            "keywords": list(set(para.lower().split()))[:20]
                        })
        except Exception as e:
            print(f"Ошибка в {file.name}: {e}")
    
    with open(Config.CHUNKS_JSON, 'w', encoding='utf-8') as f:
        json.dump({"chunks": chunks}, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Создано {len(chunks)} chunks")
    return chunks

def main():
    print("="*60)
    print("🚀 ОБРАБОТКА БАЗЫ ЗНАНИЙ ЕАСУЗ (упрощенная версия)")
    print("="*60)
    
    qa_pairs = process_excel_files()
    chunks = process_instructions()
    
    print("\n" + "="*60)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("="*60)
    print(f"📊 Q&A пар: {len(qa_pairs)}")
    print(f"📚 Chunks: {len(chunks)}")
    print("="*60)

if __name__ == "__main__":
    main()