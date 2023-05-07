import settings
import openai
import telebot
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, inspect
from sqlalchemy.orm import declarative_base
from telebot import types



openai.api_key = settings.OPENAI_API_KEY
bot = telebot.TeleBot(settings.BOT_API_KEY)



models = {
    'gpt3.5': 'gpt-3.5-turbo',
    'dav3': 'text-davinci-003'
}

Base = declarative_base()



class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    user_message = Column(String)
    bot_message = Column(String)



def save_conversation_db(user_id, user_message, bot_message):
    table_name = f"data/conversation_{user_id}"

    table = Table(
        table_name,
        metadata,
        Column('id', Integer, primary_key=True),
        Column('user_message', String),
        Column('bot_message', String),
        extend_existing=True  # Add this line to redefine options and columns
    )

    metadata.create_all(bind=engine)

    ins = table.insert().values(user_message=user_message, bot_message=bot_message)
    with engine.begin() as conn:
        conn.execute(ins)



def get_user_conversations_db(user_id):
    table_name = f"conversation_{user_id}"
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return []

    table = Table(
        table_name,
        metadata,
        autoload=True,
        autoload_with=engine
    )

    select_query = table.select().order_by(table.c.id)
    with engine.connect() as connection:
        result = connection.execute(select_query)
        conversations = result.fetchall()

    return conversations



engine = create_engine('sqlite:///conversations.db')
metadata = MetaData()



def settings(user_id, model='gpt3.5', style=''):
    engine = create_engine('sqlite:///settings.db')
    metadata = MetaData()
    table_name = f"settings_{user_id}"

    table = Table(
        table_name,
        metadata,
        Column('id', Integer, primary_key=True),
        Column('model', String),
        Column('style', String),
        extend_existing=True  # Add this line to redefine options and columns
    )

    metadata.create_all(bind=engine, tables=[table])

    with engine.begin() as conn:
        # Получаем первую строку таблицы
        stmt = table.select().limit(1)
        result = conn.execute(stmt)
        row = result.fetchone()

        if row is not None:
            # Обновляем значение model только в первой строке
            stmt = table.update().where(table.c.id == row[table.c.id]).values(model=model, style=style)
            conn.execute(stmt)
        else:
            # Если таблица пуста, вставляем новую строку
            stmt = table.insert().values(id=1, model=model, style=style)
            conn.execute(stmt)



def clear_table(table, database_connection_string="sqlite:///conversations.db"):
    engine = table.bind
    connection = engine.connect()
    connection.execute(table.delete())



@bot.message_handler(commands=['clear'])
def clear_data_db(message):
    user_id = message.from_user.id
    table = select_table(f"conversation_{user_id}")
    clear_table(table)
    bot.send_message(message.chat.id, "История очищена.")



def select_table(table_name, database_connection_string="sqlite:///conversations.db"):
    engine = create_engine(database_connection_string)
    metadata = MetaData()
    metadata.bind = engine
    metadata.reflect()
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
        return table
    else:
        return False



def model_from_settings(table):
    engine = table.bind
    connection = engine.connect()

    # Получение столбцов таблицы
    columns = table.columns

    # Выполнение запроса SELECT для получения данных
    select_query = table.select()
    result = connection.execute(select_query)
    row = result.fetchone()
    user_model = row[columns['model']]
    return user_model



def get_model(table_name, database_connection_string="sqlite:///settings.db"):
    tabel = select_table(table_name, database_connection_string)
    return model_from_settings(tabel)


def style_from_settings(table):
    engine = table.bind
    connection = engine.connect()

    # Получение столбцов таблицы
    columns = table.columns

    # Выполнение запроса SELECT для получения данных
    select_query = table.select()
    result = connection.execute(select_query)
    row = result.fetchone()
    user_model = row[columns['style']]
    return user_model


def fetch_conversation_data(table):
    engine = table.bind
    connection = engine.connect()

    # Получение столбцов таблицы
    columns = table.columns

    # Выполнение запроса SELECT для получения данных
    select_query = table.select()
    result = connection.execute(select_query)

    # Формирование списка словарей в требуемом формате
    conversation_data = []
    for row in result:
        user_message = row[columns['user_message']]
        assistant_message = row[columns['bot_message']]
        conversation_data.append({"role": "user", "content": user_message})
        conversation_data.append({"role": "assistant", "content": assistant_message})

    connection.close()

    return conversation_data



@bot.message_handler(commands=['model', 'models'])
def models(message):
    user_id = message.from_user.id
    if select_table(f'settings_{user_id}', "sqlite:///settings.db") == False:
        settings(user_id)

    table = select_table(f'settings_{user_id}', "sqlite:///settings.db")
    model = model_from_settings(table)
    markup = types.InlineKeyboardMarkup(row_width=2)
    model_1 = types.InlineKeyboardButton('📕 gpt-3.5', callback_data='gpt3.5')
    model_2 = types.InlineKeyboardButton('davinci-3 📗', callback_data='dav3')
    markup.add(model_1, model_2)
    bot.send_message(message.chat.id, f"""
    У данного бота есть две модели:
    
📕️ - gpt-3.5-turbo более мощная и быстрая модель.
📗 - davinci-3 Менее мощная, но более креативная модель.

На данный момент используется {model} модель. """
                     , reply_markup=markup)



@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    if call.message:
        if call.data == 'gpt3.5':
            settings(user_id, 'gpt3.5')
            bot.send_message(call.message.chat.id, 'Модель успешно изменена на gpt3.5')
        elif call.data == 'dav3':
            settings(user_id, 'dav3')
            bot.send_message(call.message.chat.id, 'Модель успешно изменена на dav3')



@bot.message_handler(commands=['style'])
def style(message):
    user_id = message.from_user.id
    model = get_model(f'settings_{user_id}')
    settings(user_id, model, message.text[7:])
    bot.send_message(message.chat.id, f'Стиль успешно применен')



@bot.message_handler(commands=['reset_style'])
def reset_style(message):
    user_id = message.from_user.id
    model = get_model(f'settings_{user_id}')
    settings(user_id, model, '')
    bot.send_message(message.chat.id, f'Стиль сброшен')



@bot.message_handler(commands=['start'])
def starts(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn1 = types.KeyboardButton("⚠️ Сборсить диалог")
    btn2 = types.KeyboardButton("✅ Изменить модель")
    btn3 = types.KeyboardButton("❌ Сбросить стиль")
    markup.add(btn1, btn3, btn2)
    bot.send_message(message.chat.id,
                     text="""Привет, {0.first_name}! Я беслатный gpt бот. Вот список моих команд:
/clear - очищает историю диалога.
/model - выбрать модель бота.
/style - установить настройки бота.
/reset_style - сбросить стиль бота.
Чтобы задать вопрос, просто напиши его в чате.""".format(
                         message.from_user), reply_markup=markup)



@bot.message_handler(func=lambda _: True)
def handle_message(message):
    if message.text == "⚠️ Сборсить диалог":
        clear_data_db(message)
    elif message.text == "✅ Изменить модель":
        models(message)
    elif message.text == "❌ Сбросить стиль":
        reset_style(message)
    else:
        messages = []
        user_id = message.from_user.id
        try:
            table = select_table(f"conversation_{user_id}")
            messages = fetch_conversation_data(table)
        except:
            pass

        if select_table(f'settings_{user_id}', "sqlite:///settings.db") == False:
            settings(user_id, 'dav3')

        table = select_table(f'settings_{user_id}', "sqlite:///settings.db")
        model = model_from_settings(table)

        style = style_from_settings(table)

        messages.insert(0, {"role": "system",
                            "content": f"{style}"})

        user_message = message.text
        try:
            if model == 'gpt3.5':
                message_dict = {"role": "user", "content": message.text}
                messages.append(message_dict)
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                reply = response.choices[0].message.content
                bot.send_message(chat_id=message.from_user.id, text=reply)
            elif model == 'dav3':
                response = openai.Completion.create(
                    model="text-davinci-003",
                    prompt=message.text,
                    temperature=0.8,
                    max_tokens=1000,
                    top_p=1,
                    frequency_penalty=0.0,
                    presence_penalty=0.6,
                    stop=[" Human:", " AI:"]
                )
                reply = response['choices'][0]['text']
                bot.send_message(chat_id=message.from_user.id, text=reply)

            # Save the conversation data to the user's table
            save_conversation_db(user_id, user_message, reply)

            # Fetch previous conversations from the database
            previous_conversations = get_user_conversations_db(user_id)
        except openai.error.RateLimitError:
            bot.send_message(message.chat.id, "Не так быстро...")


bot.polling()
