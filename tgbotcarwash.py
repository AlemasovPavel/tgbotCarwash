import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, Contact
import datetime
from telebot import types
import requests

# Здесь добавляем токен вашего бота
TOKEN = '7175653885:AAE6uLr3AckL728luQX_B3lqRSUcSzIRmKo'

# Здесь добавляем ваш chat_id
ADMIN_CHAT_ID = '611410247'

bot = telebot.TeleBot(TOKEN)

# Словарь для хранения номеров телефонов зарегистрированных пользователей
registered_users = {
    "+79028927245": "611410247"  # Ваш номер телефона и соответствующий chat_id
}

# Словарь для хранения информации о том, приняли ли пользователи правила
accepted_rules = {}

# Словарь для хранения состояния пользователей (приняли ли они правила)
user_states = {}

# Словарь для хранения резервов пользователей
user_reservations = {}

# Правила использования автомойки
RULES = """
Правила использования автомойки:

1. Запрещено оставлять мусор внутри мойки и на ее территории. Пожалуйста, вывозите мусор с собой.
2. Не используйте автомойку для мойки запрещенных вещей или транспортных средств, загрязненных опасными веществами.
3. Припарковывайте ваше транспортное средство на отведенном месте и соблюдайте правила очередности.
4. Пользуйтесь автомойкой бережно и осторожно, следите за оборудованием и соблюдайте инструкции по его использованию.
5. После завершения мойки, убедитесь, что вы освободили место для следующего пользователя.
"""


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    user_states[chat_id] = 'awaiting_contact'
    bot.send_message(message.chat.id, "Прежде чем продолжить, пожалуйста, отправьте свой контакт для регистрации.",
                     reply_markup=get_contact_button())


def get_contact_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton(text="Отправить контакт", request_contact=True))
    return markup


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = str(message.chat.id)
    phone_number = message.contact.phone_number
    if phone_number in registered_users:
        user_states[chat_id] = 'contact_received'
        bot.send_message(message.chat.id,
                         "Прежде чем продолжить, пожалуйста, ознакомьтесь с правилами использования автомойки и примите их, нажав кнопку ниже.")
        bot.send_message(message.chat.id, RULES, reply_markup=get_rules_confirmation_keyboard())
    else:
        bot.send_message(message.chat.id,
                         "Ваш контакт не найден в системе. Обратитесь к администратору для регистрации.")


def get_rules_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Принять правила", callback_data='accept_rules'))
    return keyboard


# Обработчик принятия правил
@bot.callback_query_handler(func=lambda call: call.data == 'accept_rules')
def accept_rules_callback(call):
    chat_id = str(call.message.chat.id)
    accepted_rules[chat_id] = True
    bot.send_message(chat_id, "Спасибо за принятие правил! Теперь вы можете пользоваться ботом.",
                     reply_markup=get_main_menu_keyboard())


# Функция для создания основного меню
def get_main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Запись на мойку", "Мои резервы", "Статистика")
    return keyboard


@bot.message_handler(func=lambda message: message.text == "Запись на мойку")
def handle_car_wash_booking(message):
    show_dates(message)


@bot.message_handler(func=lambda message: message.text == "Мои резервы")
def handle_reservations(message):
    chat_id = str(message.chat.id)
    if chat_id in user_reservations and user_reservations[chat_id]:
        reservations = user_reservations[chat_id]
        text = "Ваши текущие резервы:\n"
        for i, reservation in enumerate(reservations, 1):
            text += f"{i}. Дата: {reservation['date']}, Время: {reservation['time']}, Продолжительность: {reservation['duration']} минут\n"
        bot.send_message(message.chat.id, text, reply_markup=get_reservations_keyboard(reservations))
    else:
        bot.send_message(message.chat.id, "У вас нет активных резервов.")


def get_reservations_keyboard(reservations):
    keyboard = InlineKeyboardMarkup()
    for i, reservation in enumerate(reservations):
        keyboard.row(InlineKeyboardButton(f"Отменить резерв {i + 1}", callback_data=f"cancel_reservation:{i}"))
    return keyboard


@bot.message_handler(commands=['show_dates'])
def show_dates(message):
    dates = generate_dates()  # Генерируем даты на 15 дней вперёд
    markup = types.InlineKeyboardMarkup()  # Создаем клавиатуру
    row = []  # Создаем список для хранения кнопок в каждой строке
    for date in dates:
        button_text = date.strftime('%d.%m.%Y')
        callback_data = f"select_date:{date.strftime('%Y-%m-%d')}"
        button = types.InlineKeyboardButton(button_text, callback_data=callback_data)
        row.append(button)  # Добавляем кнопку в текущую строку
        if len(row) == 3:  # Если в строке уже 3 кнопки, добавляем ее в клавиатуру и создаем новую строку
            markup.row(*row)
            row = []
    if row:  # Добавляем оставшиеся кнопки в последнюю строку
        markup.row(*row)

    bot.send_message(message.chat.id, "Выберите дату записи на мойку:", reply_markup=markup)


def generate_dates():
    dates = []
    today = datetime.date.today()
    for i in range(30):
        date = today + datetime.timedelta(days=i)
        dates.append(date)
    return dates


def generate_time_slots():
    slots = []
    start_time = datetime.time(0, 0)  # Начало рабочего дня
    end_time = datetime.time(23, 45)  # Конец рабочего дня
    current_time = start_time
    while current_time < end_time:
        slots.append(current_time)
        current_time = (datetime.datetime.combine(datetime.date.today(), current_time) + datetime.timedelta(
            minutes=15)).time()
    return slots


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_date:'))
def select_date(call):
    selected_date = call.data.split(':')[1]  # Получаем выбранную дату из данных обратного вызова
    # Удаляем сообщение с кнопками дат
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Вы выбрали дату записи на мойку: {selected_date}")

    # Генерируем кнопки с временными слотами
    time_slots = generate_time_slots()
    markup = types.InlineKeyboardMarkup()  # Создаем клавиатуру
    row = []  # Создаем список для хранения кнопок в каждой строке
    for slot in time_slots:
        button_text = slot.strftime('%H:%M')
        callback_data = f"select_time:{selected_date}:{slot.strftime('%H:%M')}"
        button = types.InlineKeyboardButton(button_text, callback_data=callback_data)
        row.append(button)  # Добавляем кнопку в текущую строку
        if len(row) == 4:  # Если в строке уже 4 кнопки, добавляем ее в клавиатуру и создаем новую строку
            markup.row(*row)
            row = []
    if row:  # Добавляем оставшиеся кнопки в последнюю строку
        markup.row(*row)

    bot.send_message(call.message.chat.id, "Выберите время записи на мойку:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_time:'))
def select_time(call):
    data_parts = call.data.split(':')
    selected_date = data_parts[1]  # Получаем выбранную дату
    selected_hour = data_parts[2]  # Получаем выбранный час)
    selected_min = data_parts[3]  # Получаем выбранные минуты)


    # Удаляем предыдущие кнопки с выбором времени
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    message_text = f"Вы выбрали дату записи на мойку: {selected_date} и время: {selected_hour}:{selected_min}. Выберите продолжительность мойки:"

    # Создаем клавиатуру с кнопками продолжительности
    markup = types.InlineKeyboardMarkup()
    durations = [15, 30, 45, 60]
    for duration in durations:
        button = types.InlineKeyboardButton(f"{duration} минут",
                                            callback_data=f"select_duration:{selected_date}:{selected_hour}:{selected_min}:{duration}")
        markup.row(button)

    # Отправляем сообщение с клавиатурой
    bot.send_message(call.message.chat.id, message_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_duration:'))
def select_duration(call):
    data_parts = call.data.split(':')
    selected_date = data_parts[1]
    selected_hour = data_parts[2]
    selected_min = data_parts[3]
    selected_duration = data_parts[4]

    # Удаляем кнопки выбора продолжительности
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    message_text = f"Вы выбрали дату записи на мойку: {selected_date}, время: {selected_hour}:{selected_min} и продолжительность: {selected_duration} минут. Вы подтверждаете данную запись?"

    # Создаем клавиатуру с кнопками подтверждения и отмены
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("Подтверждаю",
                                                callback_data=f"confirm_booking:{selected_date}:{selected_hour}:{selected_min}:{selected_duration}")
    cancel_button = types.InlineKeyboardButton("Отмена", callback_data="cancel_booking")
    markup.row(confirm_button, cancel_button)  # Используем row для добавления кнопок в одну строку

    # Отправляем сообщение с клавиатурой
    bot.send_message(call.message.chat.id, message_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_booking:'))
def confirm_booking(call):
    data_parts = call.data.split(':')
    selected_date = data_parts[1]
    selected_hour = data_parts[2]
    selected_min = data_parts[3]
    selected_duration = data_parts[4]
    chat_id = str(call.message.chat.id)

    # Сохраняем резерв пользователя
    if chat_id not in user_reservations:
        user_reservations[chat_id] = []
    user_reservations[chat_id].append({
        'date': selected_date,
        'time': f"{selected_hour}:{selected_min}",
        'duration': selected_duration
    })

    # Отправляем сообщение о подтверждении записи с клавиатурой
    message_text = f"Запись на мойку {selected_date} в {selected_hour}:{selected_min} на {selected_duration} минут успешно подтверждена!"
    markup = get_main_menu_keyboard()
    bot.send_message(call.message.chat.id, message_text, reply_markup=markup)

    # Показываем пользователю, что что-то происходит
    bot.send_chat_action(call.message.chat.id, 'typing')

    # Удаляем кнопки подтверждения и отмены
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def cancel_booking(call):
    bot.send_message(call.message.chat.id, "Запись на мойку отменена.")

    # Удаляем кнопки подтверждения и отмены
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_reservation:'))
def cancel_reservation(call):
    chat_id = str(call.message.chat.id)
    reservation_index = int(call.data.split(':')[1])

    # Удаляем резерв пользователя
    if chat_id in user_reservations and len(user_reservations[chat_id]) > reservation_index:
        user_reservations[chat_id].pop(reservation_index)
        bot.send_message(chat_id, "Резерв успешно отменен.", reply_markup=get_main_menu_keyboard())
    else:
        bot.send_message(chat_id, "Ошибка при отмене резерва. Попробуйте снова.")

    # Удаляем кнопки отмены резерва
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)


# Обработчик запуска бота
if __name__ == "__main__":
    bot.polling()


