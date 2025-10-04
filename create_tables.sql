-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL,
    user_state TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы слов
CREATE TABLE IF NOT EXISTS words (
    word_id SERIAL PRIMARY KEY,
    english_word TEXT UNIQUE NOT NULL,
    russian_translation TEXT NOT NULL,
    added_by BIGINT DEFAULT NULL
);

-- Создание таблицы связи пользователей и слов
CREATE TABLE IF NOT EXISTS user_words (
    user_id BIGINT,
    word_id INTEGER,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES words(word_id) ON DELETE CASCADE
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_user_words_user_id ON user_words(user_id);
CREATE INDEX IF NOT EXISTS idx_user_words_word_id ON user_words(word_id);
CREATE INDEX IF NOT EXISTS idx_words_english ON words(english_word);
CREATE INDEX IF NOT EXISTS idx_words_added_by ON words(added_by);