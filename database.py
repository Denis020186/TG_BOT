import sqlite3
import os


class SQLiteDatabase:
    def __init__(self, db_file='english_bot.db'):
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        """Создает и возвращает соединение с базой данных"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_database(self):
        """Инициализирует базу данных"""
        if not os.path.exists(self.db_file):
            print("🗃️ Создание новой базы данных...")
            conn = self.get_connection()
            try:
                # Простая и надежная инициализация
                self._create_tables(conn)
                self._insert_default_data(conn)
                print("✅ База данных успешно создана")
            except Exception as e:
                print(f"❌ Ошибка при создании БД: {e}")
            finally:
                conn.close()
        else:
            print("✅ База данных уже существует")

    def _create_tables(self, conn):
        """Создает таблицы в базе данных"""
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_word TEXT UNIQUE NOT NULL,
                russian_translation TEXT NOT NULL,
                added_by INTEGER DEFAULT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_words (
                user_id INTEGER,
                word_id INTEGER,
                PRIMARY KEY (user_id, word_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (word_id) REFERENCES words(word_id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        print("✅ Таблицы созданы")

    def _insert_default_data(self, conn):
        """Добавляет начальные данные в базу"""
        cursor = conn.cursor()

        default_words = [
            ('red', 'красный'), ('blue', 'синий'), ('green', 'зеленый'),
            ('I', 'я'), ('you', 'ты'), ('he', 'он'), ('she', 'она'), ('it', 'оно'),
            ('cat', 'кот'), ('dog', 'собака'), ('house', 'дом'), ('book', 'книга'),
            ('water', 'вода'), ('food', 'еда'), ('friend', 'друг'),
            ('hello', 'привет'), ('goodbye', 'пока'), ('thank you', 'спасибо'),
            ('yes', 'да'), ('no', 'нет'), ('man', 'мужчина'), ('woman', 'женщина')
        ]

        for en_word, ru_word in default_words:
            cursor.execute(
                "INSERT OR IGNORE INTO words (english_word, russian_translation) VALUES (?, ?)",
                (en_word, ru_word)
            )

        conn.commit()
        print(f"✅ Добавлено {len(default_words)} базовых слов")

    def register_user(self, user_id, username, first_name):
        """Регистрирует нового пользователя в базе данных."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            user_exists = cursor.fetchone() is not None

            if not user_exists:
                cursor.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name)
                )

                # Добавляем пользователю все базовые слова
                cursor.execute('''
                    INSERT OR IGNORE INTO user_words (user_id, word_id)
                    SELECT ?, word_id FROM words WHERE added_by IS NULL
                ''', (user_id,))

                conn.commit()
                print(f"✅ Новый пользователь {user_id} зарегистрирован")
                return True
            else:
                print(f"ℹ️ Пользователь {user_id} уже существует")
                return True

        except Exception as e:
            print(f"❌ Ошибка при регистрации пользователя: {e}")
            return False
        finally:
            conn.close()

    def get_user_words(self, user_id):
        """Получает список слов (id, en, ru) для конкретного пользователя."""
        conn = self.get_connection()
        words = []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM words w
                INNER JOIN user_words uw ON w.word_id = uw.word_id
                WHERE uw.user_id = ?
                ORDER BY w.english_word
            ''', (user_id,))

            words = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
            print(f"📖 Пользователь {user_id} имеет {len(words)} слов")

        except Exception as e:
            print(f"❌ Ошибка при получении слов пользователя: {e}")
        finally:
            conn.close()
        return words

    def add_word_to_db(self, user_id, english_word, russian_translation):
        """Добавляет новое слово в БД и связывает с пользователем."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Добавляем слово
            cursor.execute(
                "INSERT OR IGNORE INTO words (english_word, russian_translation, added_by) VALUES (?, ?, ?)",
                (english_word, russian_translation, user_id)
            )

            # Получаем ID слова
            cursor.execute("SELECT word_id FROM words WHERE english_word = ?", (english_word,))
            result = cursor.fetchone()

            if result:
                word_id = result[0]
                # Связываем слово с пользователем
                cursor.execute(
                    "INSERT OR IGNORE INTO user_words (user_id, word_id) VALUES (?, ?)",
                    (user_id, word_id)
                )
                conn.commit()
                print(f"✅ Слово '{english_word}' добавлено для пользователя {user_id}")
                return True
            else:
                print(f"❌ Не удалось добавить слово '{english_word}'")
                return False

        except Exception as e:
            print(f"❌ Ошибка при добавлении слова: {e}")
            return False
        finally:
            conn.close()

    def delete_word_from_user(self, user_id, word_id):
        """Удаляет связь пользователь-слово."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT added_by FROM words WHERE word_id = ?", (word_id,))
            result = cursor.fetchone()
            added_by = result[0] if result else None

            cursor.execute(
                "DELETE FROM user_words WHERE user_id = ? AND word_id = ?",
                (user_id, word_id)
            )

            if added_by == user_id:
                cursor.execute("DELETE FROM words WHERE word_id = ?", (word_id,))

            conn.commit()
            print(f"✅ Слово {word_id} удалено для пользователя {user_id}")
            return True

        except Exception as e:
            print(f"❌ Ошибка при удалении слова: {e}")
            return False
        finally:
            conn.close()

    def get_word_count(self, user_id):
        """Возвращает количество слов у пользователя."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            count = result[0] if result else 0
            print(f"📊 Пользователь {user_id} имеет {count} слов")
            return count
        except Exception as e:
            print(f"❌ Ошибка при получении количества слов: {e}")
            return 0
        finally:
            conn.close()


# Создаем экземпляр базы данных
db_instance = SQLiteDatabase()


# Функции для совместимости
def register_user(user_id, username, first_name):
    return db_instance.register_user(user_id, username, first_name)


def get_user_words(user_id):
    return db_instance.get_user_words(user_id)


def add_word_to_db(user_id, english_word, russian_translation):
    return db_instance.add_word_to_db(user_id, english_word, russian_translation)


def delete_word_from_user(user_id, word_id):
    return db_instance.delete_word_from_user(user_id, word_id)


def get_word_count(user_id):
    return db_instance.get_word_count(user_id)