import os
import sys

# Установка UTF-8 кодировки для Windows
if sys.platform == "win32":
    os.system('chcp 65001 > nul')

import telebot
from config import BOT_TOKEN
import bot_handlers as handlers
from database import PostgreSQLDatabase as database

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)


# Регистрация обработчиков команд
@bot.message_handler(commands=['start', 'начать'])
def handle_start(message):
    print(f"Команда /start от пользователя {message.from_user.id}")
    handlers.send_welcome(message)


@bot.message_handler(commands=['study', 'учить', 'обучение'])
def handle_study(message):
    print(f"Команда /study от пользователя {message.from_user.id}")
    handlers.start_study(message)


@bot.message_handler(commands=['add_word', 'добавить', 'новое слово'])
def handle_add_word(message):
    print(f"Команда /add_word от пользователя {message.from_user.id}")
    handlers.add_word_step_1(message)


@bot.message_handler(commands=['delete_word', 'удалить', 'удалить слово'])
def handle_delete_word(message):
    print(f"Команда /delete_word от пользователя {message.from_user.id}")
    handlers.delete_word_list(message)


@bot.message_handler(commands=['stats', 'статистика', 'слова'])
def handle_stats(message):
    print(f"Команда /stats от пользователя {message.from_user.id}")
    handlers.show_stats(message)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    print(f"Callback от пользователя {call.from_user.id}: {call.data}")
    if call.data.startswith('delete_'):
        handlers.handle_delete_query(call)
    else:
        bot.answer_callback_query(call.id, "Неизвестная команда")


# Обработчик текстовых сообщений (для изучения слов)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"Текстовое сообщение от {message.from_user.id}: {message.text}")
    # Проверяем, не является ли сообщение командой
    if message.text.startswith('/'):
        handle_unknown(message)
    else:
        # Это может быть ответ во время изучения слов
        # Передаем обработку в bot_handlers
        handlers.handle_text_message(message)


# Обработчик неизвестных команд
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    if message.text.startswith('/'):
        print(f"Неизвестная команда: {message.text} от пользователя {message.from_user.id}")
        bot.reply_to(message, "Неизвестная команда. Используйте /start для просмотра доступных команд.")


def initialize_database():
    # Инициализирует базу данных при запуске бота
    print("🔄 Проверка и инициализация базы данных...")
    try:
        database.check_and_init_database()
        print("✅ База данных готова к работе!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")
        return False

# Запуск бота
if __name__ == '__main__':
    print("=" * 50)
    print("Запуск English Learning Bot...")
    print("=" * 50)

    # Инициализация базы данных
    if not initialize_database():
        print("❌ Не удалось инициализировать базу данных. Завершение работы.")
        sys.exit(1)

    print("Бот запущен и готов к работе!")
    print("Ожидание сообщений...")
    print("=" * 50)

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка в работе бота: {e}")