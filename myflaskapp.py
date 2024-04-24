import logging
import telebot
from telebot import types
from flask import Flask, request, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import pymongo
import json
from difflib import get_close_matches

data = json.load(open('data.json'))
token = ""
secret = ''
url = 'https://bot1..kz/' + secret


bot = telebot.TeleBot(token, threaded=False)
bot.remove_webhook()
bot.set_webhook(url=url)

uri = ""
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
db = client.telegram
collection = db.EnglishDic
user_state_collection = db.user_state
logging.basicConfig(level=logging.DEBUG)
collection.create_index([('chat_id', pymongo.DESCENDING)])

app = Flask(__name__)

def set_user_state(chat_id, state):
    user_state_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"state": state}},
        upsert=True
    )

def get_user_state(chat_id):
    user_state_document = user_state_collection.find_one({"chat_id": chat_id})
    return user_state_document.get("state", {}) if user_state_document else {}

@bot.message_handler(commands=['start'])
def key(message):
    chat_id = message.chat.id
    try:
        find = collection.find_one({"chat_id": str(chat_id)})
        if find is None:
            collection.insert_one({"chat_id": str(chat_id), "count_of_messages": 1})
            bot.send_message(chat_id, '''Hi there! 👋 I'm VocabExpandBot, your digital dictionary and word explorer. Simply type a word to get started, or use commands for more options. How can I assist you in discovering and understanding words today?''')
            bot.send_message(chat_id, "Enter a word: ")
        else:
            collection.update_one({"chat_id": str(chat_id)}, {"$inc": {"count_of_messages": 1}})
            bot.send_message(chat_id, '''Welcome back to VocabExpandBot! 👋 I'm here to help you explore and learn new words.''')
            bot.send_message(chat_id, "Enter a word: ")
    except Exception as e:
        bot.send_message(chat_id, "An error occurred: " + str(e))

def suggest_correction(word, chat_id):
    matches = get_close_matches(word, data.keys())
    if len(matches) > 0:
        suggested_word = matches[0]
        markup = types.InlineKeyboardMarkup(row_width=2)
        yes_button = types.InlineKeyboardButton("Yes", callback_data=f"yes_{suggested_word}")
        no_button = types.InlineKeyboardButton("No", callback_data="no")
        markup.add(yes_button, no_button)

        bot.send_message(chat_id, "Did you mean '%s' instead?" % suggested_word, reply_markup=markup)
        set_user_state(chat_id, {'waiting_for_correction': True, 'suggested_word': suggested_word})
    else:
        bot.send_message(chat_id, "The word does not exist. Please double check the word and try again.")


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_state = get_user_state(call.message.chat.id)
    if 'yes_' in call.data:
        suggested_word = call.data.split('_')[1]
        output = data.get(suggested_word, "No definition found.")
        if type(output) == list:
            for item in output:
                bot.send_message(call.message.chat.id, f"Answer: {item}")
        else:
            bot.send_message(call.message.chat.id, f"Answer: {output}")
    elif call.data == 'no':
        bot.send_message(call.message.chat.id, "The word does not exist. Please double check it and try again.")

    set_user_state(call.message.chat.id, {'waiting_for_correction': False})
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types='text')
def reply(message):
    current = {"chat_id": str(message.chat.id)}
    new_data = {"$inc": {"count_of_messages": 1}}
    collection.update_many(current, new_data)
    if message.text.lower() in data:
        output = data[message.text.lower()]
        if type(output) == list:
            for item in output:
                bot.send_message(message.chat.id, f"Answer: {item}")
        else:
            bot.send_message(message.chat.id, f"Answer: {output}")
    else:
        suggest_correction(message.text.lower(), message.chat.id)

@app.route('/'+secret, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)