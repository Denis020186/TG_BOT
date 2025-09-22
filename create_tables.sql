-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы слов
CREATE TABLE IF NOT EXISTS words (
    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    english_word TEXT UNIQUE NOT NULL,
    russian_translation TEXT NOT NULL,
    added_by INTEGER DEFAULT NULL
);

-- Создание таблицы связи пользователей и слов
CREATE TABLE IF NOT EXISTS user_words (
    user_id INTEGER,
    word_id INTEGER,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES words(word_id) ON DELETE CASCADE
);