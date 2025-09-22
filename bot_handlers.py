import random
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import database

# Глобальная переменная для хранения состояния пользователей
user_states = {}


def get_user_state(user_id):
    """Возвращает состояние пользователя"""
    return user_states.get(user_id, {})


def set_user_state(user_id, state_data):
    """Устанавливает состояние пользователя"""
    user_states[user_id] = state_data


def clear_user_state(user_id):
    """Очищает состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]


def get_random_word_and_options(user_id):
    """Возвращает случайное слово для проверки и 4 варианта ответа."""
    user_words = database.get_user_words(user_id)
    print(f"📚 Найдено слов для пользователя {user_id}: {len(user_words)}")

    if not user_words:
        return None, [], []

    target_word = random.choice(user_words)
    target_id, en, ru = target_word
    print(f"🎯 Выбрано слово: {ru} -> {en}")

    other_words = [word for word in user_words if word[0] != target_id]
    wrong_options = random.sample(other_words, min(3, len(other_words)))
    wrong_answers = [word[1] for word in wrong_options]

    options = [en] + wrong_answers
    random.shuffle(options)
    print(f"📝 Варианты ответов: {options}")

    return (ru, options, en)


def send_welcome(message):
    """Обработчик команды /start."""
    from main import bot
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    print(f"👋 Приветствие для пользователя {user_id}")
    database.register_user(user_id, username, first_name)

    # Очищаем состояние при старте
    clear_user_state(user_id)

    welcome_text = """🎓 <b>Привет! Я бот для изучения английских слов!</b>

<b>Доступные команды:</b>
/start - Начать работу с ботом
/study - 🎯 Начать изучение слов
/add_word - ➕ Добавить новое слово
/delete_word - 🗑️ Удалить слово из списка
/stats - 📊 Показать статистику

<b>Просто выбери команду из меню или введи ее вручную!</b>"""

    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')


def start_study(message):
    """Начинает урок с выбором слова."""
    from main import bot
    user_id = message.from_user.id
    print(f"🎓 Начало изучения для пользователя {user_id}")

    # Очищаем предыдущее состояние
    clear_user_state(user_id)

    question, options, correct_answer = get_random_word_and_options(user_id)

    if not question:
        bot.send_message(message.chat.id,
                         "📭 <b>Ваш словарь пуст!</b>\n"
                         "Добавьте слова с помощью /add_word",
                         parse_mode='HTML')
        return

    # Сохраняем состояние изучения
    set_user_state(user_id, {
        'mode': 'study',
        'correct_answer': correct_answer,
        'question': question
    })

    # Создаем клавиатуру с вариантами ответов
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    # Распределяем кнопки по 2 в ряд
    buttons = [KeyboardButton(option) for option in options]
    for i in range(0, len(buttons), 2):
        row = buttons[i:i + 2]
        markup.row(*row)

    # Добавляем кнопку отмены
    markup.row(KeyboardButton("❌ Отменить изучение"))

    bot.send_message(message.chat.id,
                     f"<b>Как переводится слово</b> 🔤 <code>{question}</code>?",
                     reply_markup=markup,
                     parse_mode='HTML')


def handle_text_message(message):
    """Обрабатывает все текстовые сообщения."""
    from main import bot
    user_id = message.from_user.id
    text = message.text.strip()

    user_state = get_user_state(user_id)
    current_mode = user_state.get('mode', '')

    print(f"💬 Сообщение от {user_id}: '{text}' (режим: {current_mode})")

    # Обработка команды отмены
    if text.lower() in ['отмена', 'отменить', 'cancel', '❌ отменить изучение']:
        handle_cancel(message)
        return

    # Обработка в зависимости от режима
    if current_mode == 'study':
        handle_study_answer(message)
    elif current_mode == 'add_word_step1':
        handle_add_word_step1(message)
    elif current_mode == 'add_word_step2':
        handle_add_word_step2(message)
    else:
        # Если не в активном режиме, предлагаем команды
        bot.send_message(message.chat.id,
                         "🤔 <b>Не понимаю команду</b>\n"
                         "Используйте /start для просмотра доступных команд",
                         parse_mode='HTML')


def handle_cancel(message):
    """Обрабатывает отмену операции."""
    from main import bot
    user_id = message.from_user.id

    clear_user_state(user_id)

    # Создаем основную клавиатуру
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("/study"), KeyboardButton("/add_word"))
    markup.row(KeyboardButton("/stats"), KeyboardButton("/delete_word"))

    bot.send_message(message.chat.id,
                     "✅ <b>Операция отменена</b>\n"
                     "Выберите новую команду:",
                     reply_markup=markup,
                     parse_mode='HTML')


def handle_study_answer(message):
    """Обрабатывает ответ во время изучения."""
    from main import bot
    user_id = message.from_user.id
    user_answer = message.text.strip()

    user_state = get_user_state(user_id)
    correct_answer = user_state.get('correct_answer', '')
    question = user_state.get('question', '')

    # Проверяем ответ
    if user_answer == correct_answer:
        response_text = "✅ <b>Правильно! Отлично!</b> 🎉"
    else:
        response_text = f"❌ <b>Неправильно.</b> Правильный ответ: <code>{correct_answer}</code>"

    bot.send_message(message.chat.id, response_text, parse_mode='HTML')

    # Пауза перед следующим словом
    time.sleep(2)

    # Запускаем следующее слово
    start_study(message)


def add_word_step_1(message):
    """Начинает процесс добавления слова."""
    from main import bot
    user_id = message.from_user.id
    print(f"➕ Добавление слова для пользователя {user_id}")

    # Устанавливаем состояние
    set_user_state(user_id, {'mode': 'add_word_step1'})

    # Создаем клавиатуру с кнопкой отмены
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("❌ Отмена"))

    bot.send_message(message.chat.id,
                     "📝 <b>Введите слово на английском:</b>\n"
                     "<i>Или нажмите '❌ Отмена' для отмены</i>",
                     reply_markup=markup,
                     parse_mode='HTML')


def handle_add_word_step1(message):
    """Обрабатывает первый шаг добавления слова."""
    from main import bot
    user_id = message.from_user.id
    english_word = message.text.strip().lower()

    # Проверяем валидность слова
    if not english_word or not all(c.isalpha() or c.isspace() for c in english_word):
        bot.send_message(message.chat.id,
                         "❌ <b>Слово должно содержать только буквы!</b>\n"
                         "Попробуйте еще раз:",
                         parse_mode='HTML')
        return

    # Переходим к следующему шагу
    set_user_state(user_id, {
        'mode': 'add_word_step2',
        'english_word': english_word
    })

    bot.send_message(message.chat.id,
                     f"🌍 <b>Отлично! Слово:</b> <code>{english_word}</code>\n"
                     "<b>Теперь введите перевод на русский:</b>",
                     parse_mode='HTML')


def handle_add_word_step2(message):
    """Обрабатывает второй шаг добавления слова."""
    from main import bot
    user_id = message.from_user.id
    russian_translation = message.text.strip()

    user_state = get_user_state(user_id)
    english_word = user_state.get('english_word', '')

    if not english_word:
        bot.send_message(message.chat.id,
                         "❌ <b>Ошибка процесса добавления.</b>\n"
                         "Начните заново с /add_word",
                         parse_mode='HTML')
        clear_user_state(user_id)
        return

    print(f"💾 Сохранение слова: {english_word} -> {russian_translation} для пользователя {user_id}")

    # Сохраняем слово в базу
    success = database.add_word_to_db(user_id, english_word, russian_translation)

    # Восстанавливаем основную клавиатуру
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("/study"), KeyboardButton("/add_word"))
    markup.row(KeyboardButton("/stats"), KeyboardButton("/delete_word"))

    if success:
        words_count = database.get_word_count(user_id)
        bot.send_message(message.chat.id,
                         f"✅ <b>Слово '{english_word}' успешно добавлено!</b>\n"
                         f"📊 <b>Теперь вы изучаете {words_count} слов.</b>",
                         reply_markup=markup,
                         parse_mode='HTML')
    else:
        bot.send_message(message.chat.id,
                         "❌ <b>Произошла ошибка при добавлении слова.</b>\n"
                         "Возможно, такое слово уже существует.",
                         reply_markup=markup,
                         parse_mode='HTML')

    # Очищаем состояние
    clear_user_state(user_id)


def delete_word_list(message):
    """Показывает список слов пользователя для удаления."""
    from main import bot
    user_id = message.from_user.id
    words = database.get_user_words(user_id)

    if not words:
        bot.send_message(message.chat.id, "📭 <b>Ваш словарь пуст.</b>", parse_mode='HTML')
        return

    markup = InlineKeyboardMarkup()
    for word_id, en_word, ru_translation in words:
        callback_data = f"delete_{word_id}"
        # Ограничиваем длину текста кнопки
        button_text = f"❌ {en_word} - {ru_translation}"
        if len(button_text) > 40:
            button_text = f"❌ {en_word} - {ru_translation[:15]}..."
        btn = InlineKeyboardButton(button_text, callback_data=callback_data)
        markup.add(btn)

    bot.send_message(message.chat.id,
                     "🗑️ <b>Выберите слово для удаления:</b>",
                     reply_markup=markup,
                     parse_mode='HTML')


def handle_delete_query(call):
    """Обрабатывает нажатие на кнопку удаления."""
    from main import bot
    user_id = call.from_user.id
    word_id = int(call.data.split('_')[1])

    success = database.delete_word_from_user(user_id, word_id)

    if success:
        bot.answer_callback_query(call.id, "✅ Слово удалено!")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ <b>Слово удалено.</b>\nНажмите /delete_word для управления другими словами.",
            parse_mode='HTML'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Не удалось удалить слово.")


def show_stats(message):
    """Показывает количество слов, которые изучает пользователь."""
    from main import bot
    user_id = message.from_user.id
    words_count = database.get_word_count(user_id)

    if words_count == 0:
        bot.send_message(message.chat.id,
                         "📭 <b>Ваш словарь пуст.</b>\n"
                         "Добавьте слова с помощью /add_word",
                         parse_mode='HTML')
    else:
        bot.send_message(message.chat.id,
                         f"📊 <b>Вы изучаете {words_count} слов.</b>\n"
                         "Начните изучение: /study",
                         parse_mode='HTML')


def cancel_operation(message):
    """Универсальная функция отмены."""
    from main import bot
    user_id = message.from_user.id

    clear_user_state(user_id)

    bot.send_message(message.chat.id,
                     "✅ <b>Операция отменена.</b>\n"
                     "Используйте /start для просмотра команд.",
                     parse_mode='HTML')