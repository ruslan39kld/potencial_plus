"""
База данных для HR Career Bot
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logging.info(f"[Database] Инициализирована: {self.db_path}")
    
    def _init_db(self):
        """Создание таблиц"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_premium INTEGER DEFAULT 0,
                    selected_assistant TEXT DEFAULT 'career'
                )
            """)
            
            # Таблица истории сообщений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    assistant_type TEXT,
                    question TEXT,
                    answer TEXT,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица лимитов (для бесплатных пользователей)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_limits (
                    user_id INTEGER,
                    date DATE,
                    questions_count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица пройденных тестов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS completed_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    test_name TEXT,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица состояний диалога
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    current_topic TEXT,
                    dialog_level INTEGER DEFAULT 0,
                    last_request_type TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица истории чата (отдельные сообщения)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            conn.commit()

    def register_user(self, user_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None):
        """Регистрация нового пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            conn.commit()
    
    def save_message(self, user_id: int, assistant_type: str, 
                    question: str, answer: str, response_time_ms: int):
        """Сохранение сообщения в историю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (user_id, assistant_type, question, answer, response_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, assistant_type, question, answer, response_time_ms))
            conn.commit()
    
    def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получение истории сообщений пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT assistant_type, question, answer, created_at
                FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def check_daily_limit(self, user_id: int, max_questions: int) -> tuple[bool, int]:
        """
        Проверка дневного лимита
        Returns: (can_ask, remaining_questions)
        """
        today = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем premium статус
            cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                return True, 999  # Premium пользователь - безлимит
            
            # Получаем количество вопросов за сегодня
            cursor.execute("""
                SELECT questions_count FROM usage_limits
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            
            result = cursor.fetchone()
            current_count = result[0] if result else 0
            
            remaining = max_questions - current_count
            can_ask = current_count < max_questions
            
            return can_ask, max(0, remaining)
    
    def increment_daily_usage(self, user_id: int):
        """Увеличение счетчика использования"""
        today = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_limits (user_id, date, questions_count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) 
                DO UPDATE SET questions_count = questions_count + 1
            """, (user_id, today))
            conn.commit()
    
    def get_weekly_usage(self, user_id: int) -> int:
        """Получение количества вопросов за неделю"""
        week_ago = datetime.now().date() - timedelta(days=7)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(questions_count), 0)
                FROM usage_limits
                WHERE user_id = ? AND date >= ?
            """, (user_id, week_ago))
            return cursor.fetchone()[0]
    
    def set_selected_assistant(self, user_id: int, assistant_type: str):
        """Установка выбранного ассистента"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET selected_assistant = ?
                WHERE user_id = ?
            """, (assistant_type, user_id))
            conn.commit()
    
    def get_selected_assistant(self, user_id: int) -> str:
        """Получение выбранного ассистента"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT selected_assistant FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 'career'
    
    def mark_test_completed(self, user_id: int, test_name: str):
        """Отметка о прохождении теста"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO completed_tests (user_id, test_name)
                VALUES (?, ?)
            """, (user_id, test_name))
            conn.commit()
    
    def get_completed_tests(self, user_id: int) -> List[str]:
        """Получение списка пройденных тестов"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT test_name FROM completed_tests
                WHERE user_id = ?
                ORDER BY completed_at DESC
            """, (user_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Статистика по боту"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Активные пользователи за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM messages
                WHERE created_at >= ?
            """, (week_ago,))
            active_users = cursor.fetchone()[0]
            
            # Всего сообщений
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Среднее время ответа
            cursor.execute("SELECT AVG(response_time_ms) FROM messages")
            avg_response_time = cursor.fetchone()[0] or 0
            
            return {
                "total_users": total_users,
                "active_users_7d": active_users,
                "total_messages": total_messages,
                "avg_response_time_ms": int(avg_response_time)
            }

    def save_conversation_message(self, user_id: int, role: str, content: str):
        """Сохраняет одно сообщение (user или assistant) в историю чата"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_messages (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, role, content))
            conn.commit()

    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Возвращает историю чата в формате [{role, content}, ...]"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content FROM conversation_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
        # Возвращаем в хронологическом порядке
        return [dict(row) for row in reversed(rows)]

    def update_dialog_level(self, user_id: int, level: int):
        """Обновляет уровень диалога пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_states (user_id, dialog_level)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    dialog_level = excluded.dialog_level,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, level))
            conn.commit()

    def get_dialog_level(self, user_id: int) -> int:
        """Возвращает текущий уровень диалога"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT dialog_level FROM user_states WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
        return result[0] if result else 0
