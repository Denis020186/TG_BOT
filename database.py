import psycopg2
import psycopg2.extras
import sys
import os

from config import DATABASE_URL

class PostgreSQLDatabase:
    @classmethod
    def get_connection(cls):
        """Создает и возвращает соединение с базой данных"""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            # Устанавливаем кодировку для соединения
            conn.set_client_encoding('UTF8')
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
            raise

    @classmethod
    def execute_sql_file(cls, filename):
        """Выполняет SQL файл для инициализации базы данных"""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            # Проверяем существование файла
            if not os.path.exists(filename):
                print(f"❌ Файл {filename} не найден")
                return False

            # Пробуем разные кодировки
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']

            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as file:
                        sql_script = file.read()

                    # Выполняем SQL скрипт
                    cursor.execute(sql_script)
                    conn.commit()
                    print(f"✅ SQL файл {filename} выполнен успешно (кодировка: {encoding})")
                    return True

                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"❌ Ошибка при выполнении SQL файла {filename} с кодировкой {encoding}: {e}")
                    conn.rollback()
                    continue

            # Если ни одна кодировка не сработала
            print(f"❌ Не удалось прочитать файл {filename} ни в одной кодировке")
            return False

        except Exception as e:
            print(f"❌ Общая ошибка при выполнении SQL файла {filename}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @classmethod
    def check_and_init_database(cls):
        """Проверяет и при необходимости инициализирует базу данных"""
        print("🔍 Проверка базы данных...")

        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            # Проверяем существование таблиц
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            tables_exist = cursor.fetchone()[0]

            if not tables_exist:
                print("🔄 Таблицы не найдены, инициализация базы данных...")
                # Сначала создаем таблицы
                if cls.execute_sql_file('create_tables.sql'):
                    # Затем добавляем начальные данные
                    cls.execute_sql_file('initial_data.sql')
                print("✅ База данных успешно инициализирована")
            else:
                print("✅ База данных уже инициализирована")

        except Exception as e:
            print(f"❌ Ошибка при проверке базы данных: {e}")
            raise  # Пробрасываем исключение дальше
        finally:
            conn.close()

    # Остальные методы остаются без изменений
    @classmethod
    def register_user(cls, user_id, username, first_name):
        """Регистрирует нового пользователя в базе данных."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name",
                (user_id, username, first_name)
            )

            # Добавляем пользователю все базовые слова
            cursor.execute('''
                INSERT INTO user_words (user_id, word_id)
                SELECT %s, word_id FROM words WHERE added_by IS NULL
                ON CONFLICT (user_id, word_id) DO NOTHING
            ''', (user_id,))

            conn.commit()
            return True

        except Exception as e:
            print(f"❌ Ошибка при регистрации пользователя: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @classmethod
    def get_random_word_and_options(cls, user_id):
        """Получает случайное слово и 3 случайных варианта ответа через БД."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            # Получаем случайное слово пользователя
            cursor.execute('''
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM words w
                INNER JOIN user_words uw ON w.word_id = uw.word_id
                WHERE uw.user_id = %s
                ORDER BY RANDOM()
                LIMIT 1
            ''', (user_id,))

            target_word = cursor.fetchone()
            if not target_word:
                return None, [], []

            target_id, en, ru = target_word

            # Получаем 3 случайных неправильных варианта
            cursor.execute('''
                SELECT w.english_word
                FROM words w
                INNER JOIN user_words uw ON w.word_id = uw.word_id
                WHERE uw.user_id = %s AND w.word_id != %s
                ORDER BY RANDOM()
                LIMIT 3
            ''', (user_id, target_id))

            wrong_answers = [row[0] for row in cursor.fetchall()]

            # Формируем варианты ответов
            options = [en] + wrong_answers

            # Если недостаточно неправильных вариантов, добавляем заглушки
            while len(options) < 4:
                options.append(f"word_{len(options)}")

            # Перемешиваем варианты
            import random
            random.shuffle(options)

            return (ru, options, en)

        except Exception as e:
            print(f"❌ Ошибка при получении случайного слова: {e}")
            return None, [], []
        finally:
            conn.close()

    @classmethod
    def get_user_words(cls, user_id):
        """Получает список слов для конкретного пользователя."""
        conn = cls.get_connection()
        words = []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM words w
                INNER JOIN user_words uw ON w.word_id = uw.word_id
                WHERE uw.user_id = %s
                ORDER BY w.english_word
            ''', (user_id,))

            words = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
            return words

        except Exception as e:
            print(f"❌ Ошибка при получении слов пользователя: {e}")
            return []
        finally:
            conn.close()

    @classmethod
    def add_word_to_db(cls, user_id, english_word, russian_translation):
        """Добавляет новое слово в БД и связывает с пользователем."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            # Добавляем слово
            cursor.execute(
                "INSERT INTO words (english_word, russian_translation, added_by) VALUES (%s, %s, %s) ON CONFLICT (english_word) DO NOTHING RETURNING word_id",
                (english_word, russian_translation, user_id)
            )

            result = cursor.fetchone()
            if result:
                word_id = result[0]
                # Связываем слово с пользователем
                cursor.execute(
                    "INSERT INTO user_words (user_id, word_id) VALUES (%s, %s) ON CONFLICT (user_id, word_id) DO NOTHING",
                    (user_id, word_id)
                )
            else:
                # Если слово уже существует, получаем его ID
                cursor.execute("SELECT word_id FROM words WHERE english_word = %s", (english_word,))
                result = cursor.fetchone()
                if result:
                    word_id = result[0]
                    cursor.execute(
                        "INSERT INTO user_words (user_id, word_id) VALUES (%s, %s) ON CONFLICT (user_id, word_id) DO NOTHING",
                        (user_id, word_id)
                    )

            conn.commit()
            return True

        except Exception as e:
            print(f"❌ Ошибка при добавлении слова: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @classmethod
    def delete_word_from_user(cls, user_id, word_id):
        """Удаляет связь пользователь-слово."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT added_by FROM words WHERE word_id = %s", (word_id,))
            result = cursor.fetchone()
            added_by = result[0] if result else None

            cursor.execute("DELETE FROM user_words WHERE user_id = %s AND word_id = %s", (user_id, word_id))

            if added_by == user_id:
                cursor.execute("DELETE FROM words WHERE word_id = %s", (word_id,))

            conn.commit()
            return True

        except Exception as e:
            print(f"❌ Ошибка при удалении слова: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @classmethod
    def get_word_count(cls, user_id):
        """Возвращает количество слов у пользователя."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"❌ Ошибка при получении количества слов: {e}")
            return 0
        finally:
            conn.close()

    @classmethod
    def set_user_state(cls, user_id, state_data):
        """Устанавливает состояние пользователя в БД."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            import json
            state_json = json.dumps(state_data)
            cursor.execute(
                "UPDATE users SET user_state = %s WHERE user_id = %s",
                (state_json, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при установке состояния: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @classmethod
    def get_user_state(cls, user_id):
        """Получает состояние пользователя из БД."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_state FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                import json
                return json.loads(result[0])
            return {}
        except Exception as e:
            print(f"❌ Ошибка при получении состояния: {e}")
            return {}
        finally:
            conn.close()

    @classmethod
    def clear_user_state(cls, user_id):
        """Очищает состояние пользователя в БД."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET user_state = '{}' WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка при очистке состояния: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()