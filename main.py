# -*- coding:utf8 -*-
# !/usr/bin/env python
from __future__ import print_function

import json
import random

import os
import telegram
from future.standard_library import install_aliases

install_aliases()

import apiai

CLIENT_ACCESS_TOKEN = '114a4b10c66c46dca27ad6f63cdc2ced'
# [START import_libraries]
import uuid
import requests
import dialogflow
import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
from flask import Flask


app = Flask(__name__)
import requests


@app.route('/', methods=['POST, GET'])
def index():
    return "Forbidden"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

LOCATION, BIO = range(2)

################### MENUET INTEGRATION ###########
MENUET_API = "https://scorpa.ml/menuet/bot/api"
MENUET_TOKEN = "ya29.c.El97BacMtcOVmFuQGwApUY-EikgCG8YtGI2C6oAt73Gd9AsHFBntwabQElx-9ZIQJSRvIBprUaRqDvHo2JHZCOTW8Z80u2FH8k9XlsL1Lqeg"
##################################################
### DIALOGFLOW ####
# CLIENT_ACCESS_TOKEN = "ya29.c.El97BacMtcOVmFuQGwApUY-EikgCG8YtGI2C6oAt73Gd9AsHFBn \
# twabQElx-9ZIQJSRvIBprUaRqDvHo2JHZCOTW8Z80u2FH8k9XlsL1Lqeg"
PROJECT_ID = "menuet-bf2b5"

########################
MEMORY_DB = {'users_context': []}


########################

# [START dialogflow_detect_intent_text]

def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversaion."""
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    for text in texts:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(
            session=session, query_input=query_input)

        print('=' * 20)
        print('Query text: {}'.format(response.query_result.query_text))
        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))
        print('Fulfillment text: {}\n'.format(
            response.query_result.fulfillment_text))


# [END dialogflow_detect_intent_text]

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def get_user_location(chat_id, bot, update):
    location_keyboard = telegram.KeyboardButton(text="📌 Я здесь!", request_location=True, )
    custom_keyboard = [[location_keyboard]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True, resize_keyboard=True)
    bot.send_message(chat_id=chat_id, text="Тыкни на кнопочку",
                     reply_markup=reply_markup)
    pass


def send_result_options_buttons(chat_id, bot):
    more_butt = telegram.KeyboardButton(text="ЕЩЕ! 👉")
    most_cheap = telegram.KeyboardButton(text="Самые дешевые 💰")
    most_expensive = telegram.KeyboardButton(text="Самые дорогие 💎")
    most_cool = telegram.KeyboardButton(text="Самые крутые 💖")
    custom_keyboard = [[more_butt], [most_cheap, most_cool, most_expensive]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    bot.send_message(chat_id=chat_id, text="и есть еще...", reply_markup=reply_markup)
    pass


def get_user_session(user):
    user_context = []
    session = None
    for user_context in MEMORY_DB['users_context']:
        if user_context['user_id'] == user.id:
            if datetime.datetime.now().timestamp() - user_context['timestamp'] <= user_context['lifetime']:
                return user_context['session']
            else:
                break
    # create new session for DIALOGFLOW
    session = str(uuid.uuid4())
    # Write to in memory DB
    MEMORY_DB['users_context'].append({
        'user_id': user.id,
        'session': session,
        'timestamp': datetime.datetime.now().timestamp(),
        'lifetime': 30 * 60  # 30 min
    })
    return session


def get_food_for_user_with_loc(update, food):
    user_location = 'test'
    payload = {'action': 'get_food_loc', 'token': MENUET_TOKEN,
               'user_id': update.message.from_user.id,
               'query': food}
    # send to backend
    r = requests.post(MENUET_API, json.dumps(payload), verify=False)
    if r.status_code != 200:
        logger.warning("we failed to get data from menuet for food " + update.message.text + " chat_id:" + str(
            update.message.chat_id) + " " + str(
            update.message.from_user) + "user location is " + str(user_location))
        return False
    pass


def echo(bot, update):
    """Echo the user message."""
    text = update.message.text
    session = get_user_session(update.message.from_user)
    print('Current memory DB ' + str(MEMORY_DB))
    chat_id = update.message.chat_id
    logger.warning(text)
    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

    request = ai.text_request()

    request.lang = 'ru'  # optional, default value equal 'en'

    request.session_id = session

    request.query = update.message.text
    print(request.query)
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    response = request.getresponse()
    response = json.loads(response.read())
    update.message.reply_text(response['result']['fulfillment']['speech'])
    # From dialog flow
    action = response['result']['action']
    if action == 'input.welcome':
        get_user_location(chat_id, bot, update)
    elif action == 'get-food':
        # resp = get_food_for_user_with_loc(update, response['result']['parameters'])
        if 1 != 1:  # not resp:
            update.message.reply_text('Сорян, чет ничего найти не могу :( Попробуй снова ?')
        else:
            # TODO: add response
            # expected structure
            # { item: <>
            # ingrs: []
            # cost: <>
            # place: link to addr
            #
            test_date = {'items': []}
            for i in range(0, 3):
                test_date['items'].append({
                    'item': random_word() + random_word(),
                    'ingrs': [random_word() for _ in range(3)],
                    'cost': "".join(random.choice('1234567890') for _ in range(int(random.choice('2345')))),
                    'place': 'http://4sq.com/1zUuio6'})

            for x in test_date['items']:
                update.message.reply_markdown('*' + x['item'] + '*' + '    ' + '₽ ' + '*' + x['cost'] + '*' + '\n' +
                                              '_' + ",".join([y for y in x['ingrs']]) + '_' + '\n' +
                                              x['place'])
            send_result_options_buttons(chat_id, bot)

    # detect_intent_texts(
    #     PROJECT_ID, session, text, lang_code)


def random_word():
    return "".join(random.choice('abcdertyulkzmxpoiqwv') for _ in range(int(random.choice('456789'))))


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def save_user_location(chat_id, user, user_location):
    payload = {'action': 'save_user_loc', 'token': MENUET_TOKEN, 'chat_id': chat_id, 'user_first_name': user.first_name,
               'location': user_location, 'user_id': user.id,
               'username': user.username}
    r = requests.post(MENUET_API, payload, verify=False)
    if r.status_code != 200:
        logger.warning("we failed to save data to menuet " + "chat_id:" + str(chat_id) + " " + str(
            user) + "user location is " + str(user_location))
        return False
    return True


def location(bot, update):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    update.message.reply_text('Отлично!')
    if not save_user_location(update.message.chat_id, user, user_location):
        logger.error("Failed to save data to menuet")
    update.message.reply_text("Что бы ты хотел съесть ? Например, Ларису ивановну хо... салат с кунжутом хочу !")
    return BIO


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("534041755:AAF8uLqAWAFsOY7jqPRwaT_LyFUoFdNogbY")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.location, location))
    # on noncommand i.e message - echo the message on Telegram

    dp.add_handler(MessageHandler(Filters.all, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
    main()
