# -*- coding:utf8 -*-
# !/usr/bin/env python
from __future__ import print_function

import json
import os
import random

import telegram
from future.standard_library import install_aliases
from telegram.ext.dispatcher import run_async

install_aliases()

import apiai

CLIENT_ACCESS_TOKEN = '114a4b10c66c46dca27ad6f63cdc2ced'


class USER:
    QUERY_STATUS = 'query_succ'
    LOCATION = 'last_location'
    LAST_D_ACTION = 'last_dialog_action'
    LAST_MSG = 'last_msg'


# [START import_libraries]
import uuid
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
###################DEFAULT PARAMETERS ###############
DEFAULT_LAT = "55.751571"
DEFAULT_LONG = "37.627049"
DEFAULT_NODATA = " "
DEFAULT_ADDR = " "

########################
MEMORY_DB = {'users_context': []}


# Structure
# 'user_id': user.id,
# 'session': session,
# 'timestamp': datetime.datetime.now(),
# 'lifetime': 30 * 60  # 30 min
# 'last_location': None

########################


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    session = get_user_session(update.message.from_user)
    resp = parse_query(bot, update.message.chat_id, session, update, 'шалом')
    print(resp)
    # send response from dialog flow
    update.message.reply_text(resp['result']['fulfillment']['speech'])
    ask_user_location(update.message.chat_id, bot, update)


def ask_user_location(chat_id, bot, update):
    get_user_session(update.message.from_user)
    location_keyboard = telegram.KeyboardButton(text="📌 Я здесь!", request_location=True)
    custom_keyboard = [[location_keyboard]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True, resize_keyboard=True)
    bot.send_message(chat_id=chat_id, text="Мы не знаем где ты :("
                                           " Тыкни на кнопочку, пожалуйста",
                     reply_markup=reply_markup)
    pass


################# BUTTONS DEFINITION ###############
MORE_BUTT = "ЕЩЕ! 👉"
MOST_CHEAP_BUTT = "Самые дешевые 💰"
MOST_LUX_BUTT = "Самые дорогие 💎"
AWESOMESS_BUTT = "Самые крутые 💖"


def send_result_options_buttons(chat_id, bot):
    more_butt = telegram.KeyboardButton(text=MORE_BUTT)
    most_cheap = telegram.KeyboardButton(text=MOST_CHEAP_BUTT)
    most_expensive = telegram.KeyboardButton(text=MOST_LUX_BUTT)
    most_cool = telegram.KeyboardButton(text=AWESOMESS_BUTT)
    custom_keyboard = [[more_butt], [most_cheap, most_cool, most_expensive]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    bot.send_message(chat_id=chat_id, text="а еще есть кнопочки...", reply_markup=reply_markup)
    pass


def remove_session_from_db(user):
    # remove sessiion from DB
    MEMORY_DB['users_context'] = [x for x in MEMORY_DB['users_context'] if x['user_id'] != user.id]
    pass


def get_user_session(user):
    user_context = []
    session = None
    for user_context in MEMORY_DB['users_context']:
        if user_context['user_id'] == user.id:
            if datetime.datetime.now().timestamp() - user_context['timestamp'] <= user_context['lifetime']:
                return user_context['session']
            else:
                remove_session_from_db(user)

                break
    # create new session for DIALOGFLOW
    session = str(uuid.uuid4())
    # Write to in memory DB
    MEMORY_DB['users_context'].append({
        'user_id': user.id,
        'session': session,
        'timestamp': datetime.datetime.now().timestamp(),
        'lifetime': 30 * 60,  # 30 min
        'last_location': None,
        'last_msg': '',
        'last_action': None
    })
    return session


def check_user_context(user):
    for user_context in MEMORY_DB['users_context']:
        if user_context['user_id'] == user.id:
            if datetime.datetime.now().timestamp() - user_context['timestamp'] <= user_context['lifetime']:
                return user_context['session']
            else:
                remove_session_from_db(user)
                break
    return None


def get_user_last_location(user):
    for user_context in MEMORY_DB['users_context']:
        if user_context['user_id'] == user.id:
            if 'location' in user_context:
                return user_context['location']
            else:
                break
    logger.warning('failed to find user location')
    return None


def get_food_for_user_with_loc(bot, update, food, sort):
    session = check_user_context(update.message.from_user)
    if session is None:
        set_to_memory_DB(update.message.from_user, 'last_msg', update.message.text)
        ask_user_location(chat_id=update.message.chat_id, bot=bot, update=update)
        return None
    # should not be None
    user_location = get_from_memory_DB(update.message.from_user, 'last_location')

    payload = {'action': 'get_food_loc', 'token': MENUET_TOKEN,
               'user_id': update.message.from_user.id,
               'query': "".join(food),
               "loc_lng": user_location['longitude'],
               "loc_lat": user_location['latitude'],
               "sort": sort}
    # send query to backend
    headers = {'Content-type': 'application/json'}
    r = requests.post(MENUET_API, json.dumps(payload), verify=False, headers=headers)
    if r.status_code != 200:
        logger.warning(
            "we failed to get data from menuet for food " + food + " chat_id:" + str(update.message.chat_id) + str(
                r.content))
        return {'status': 'error', 'msg': 'menuet down'}
    elif r.status_code == 200:
        if len(r.content) == 0:
            return None
        else:
            # deprecated
            if r.content == b'no more':
                return {'status': 'ok', 'msg': 'no more'}
            else:
                data_received = json.loads(r.content.decode('utf-8'))
                return data_received

    elif r.status_code == 500:
        return {'msg': 500}
    test_data = {'items': []}
    for i in range(0, 3):
        test_data['items'].append({
            'item': random_word() + random_word(),
            'ingrs': [random_word() for _ in range(3)],
            'cost': "".join(random.choice('1234567890') for _ in range(int(random.choice('2345')))),
            'place': 'http://4sq.com/1zUuio6'})

    return test_data


def set_to_memory_DB(user, key, value):
    for item in MEMORY_DB['users_context']:
        if item['user_id'] == user.id:
            item[key] = value
            break
    pass


def get_from_memory_DB(user, key):
    for item in MEMORY_DB['users_context']:
        if item['user_id'] == user.id:
            return item.get(key)
    pass


def reply_nothing_found(update, bot):
    update.message.reply_text('Сорян, чет ничего найти не могу :( Может выберем что-то другое ?')
    set_to_memory_DB(update.message.from_user, USER.LAST_MSG, "")


def getDataWithDefault(list, key):
    value = list.get(key, "")
    value = "" if value is None else value
    if isinstance(value, str):
        if value == "" or len(value) == 0:
            if key == 'rest_addr':
                return DEFAULT_ADDR
            elif key == 'rest_name':
                return 'No Data'
            elif key == 'rest_long':
                return DEFAULT_LONG
            elif key == 'rest_lat':
                return DEFAULT_LAT
            elif key == 'foursquare_id':
                # TODO:redesign
                return ""
        else:
            return value
    else:
        return DEFAULT_NODATA


def find_and_post_food(update, bot, query, sort):
    try:  # do we know where user is ?
        location = get_from_memory_DB(update.message.from_user, USER.LOCATION)
        if location is None:
            ask_user_location(update.message.chat_id, bot, update)
            set_to_memory_DB(update.message.from_user, 'last_msg', update.message.text)
            return
        if query is None or len(query) == 0:
            update.message.reply_text("Чет мы не поняли твоего вопроса, скажи по-другому ?")
            return
        resp = get_food_for_user_with_loc(bot, update, query, sort)
        print(resp)
        if resp is None:  # not resp:
            reply_nothing_found(update, bot)
            return
        elif len(resp) == 0:
            reply_nothing_found(update, bot)
            # ALWAYS USE FUCKING GET!!!! not direct point to list name!!
            return

        elif resp.get('status') == 'error':
            logger.error(
                'MENUET RETURNED ERROR!!!! ' + str(get_from_memory_DB(update.message.from_user.id, 'last_msg')) +
                str(resp))
            update.message.reply_text("мэнуетт предатель, к оружию!" + str(resp))
            return

        else:
            # TODO: add response
            # expected structure
            # { item: <>
            # ingrs: []
            # cost: <>
            # place: link to addr
            #
            if len(resp) == 0:
                reply_nothing_found(update, bot)
            elif resp['msg'] == 'no more':
                update.message.reply_text('Больше ничего не нашли :(')
                return
            elif resp['msg'] == 500:
                reply_nothing_found(update, bot)
                update.message.reply_text('У нас тут все умерло :( Ща починим, погоди')
                return
            for x in resp['items']:
                print("we got resp from menuet" + str(x))
                item_name = x.get('item_name', "")
                item_price = str(x.get('item_price', ""))
                try:
                    item_ingrs = ",".join([y for y in x["item_ingrs"]['name']])
                except:
                    logger.warning("We failed to parse ingrs, %s", x['item_ingrs'])
                    item_ingrs = ""
                mesg = '*' + item_name + '*' + '    ' + '*' + item_price + '*' + '₽' + '\n' + \
                       '_' + item_ingrs + '_'
                print(" what we formed so far " + mesg)
                update.message.reply_markdown(mesg)
                bot.send_venue(chat_id=update.message.chat_id, longitude=getDataWithDefault(x, 'rest_long'),
                               latitude=getDataWithDefault(x, 'rest_lat'), title=getDataWithDefault(x, 'rest_name'),
                               address=getDataWithDefault(x, 'rest_addr'),
                               foursquare_id=getDataWithDefault(x, 'foursquare_id'))

            send_result_options_buttons(update.message.chat_id, bot)
    except Exception as e:
        logger.error("We failed to response!!!! %s", str(e))
        reply_nothing_found(update, bot)
        update.message.reply_markdown("я сломался от твоего вопроса ;( попробуй другой ? " + str(e))


def check_auth(id):
    awesome_ones = []
    if id not in awesome_ones:
        return False
    else:
        return True


@run_async
def process_request(bot, update):
    # secret zone
    if update.message.text == 'уебу':
        logger.error("Someone entered secret line, user:%s", str(update.message.from_user))
        update.message.reply_markdown("Анализирую....")
        if check_auth(update.message.from_user.id):
            logger.error("We gave all information to this user %s", str(update.message.from_user))
        else:
            update.message.reply_markdown("Go away infidel...*GO AWAAAYYY!!!*.\nAncients will rise again...")
    """parse query and return response to the user"""
    # Get users query
    query = update.message.text
    print('Current memory DB ' + str(MEMORY_DB))

    chat_id = update.message.chat_id
    logger.warning("User said to us: " + str(query))
    # First check if we have a session
    # Dont care about question ATM
    session = check_user_context(update.message.from_user)

    # create new session if not exist
    if session is None:
        session = get_user_session(update.message.from_user)
        set_to_memory_DB(user=update.message.from_user, key='last_msg', value=update.message.text)
        set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)

    # do we have msg from user or its a new request ?
    last_msg = update.message.text if update.message.text is not None else get_from_memory_DB(update.message.from_user,
                                                                                              'last_msg')
    last_action = get_from_memory_DB(update.message.from_user, 'last_action')

    # If its new request -no last msg - ask what he wants ? Or parse existing msg
    if (last_msg == '' or last_msg is None) and last_action == 'location':
        update.message.reply_text('Что бы ты хотел съесть ? Например, Ларису ивановну хо... салат с кунжутом хочу !')
        set_to_memory_DB(update.message.from_user, 'last_action', '')
        set_to_memory_DB(update.message.from_user, 'last_msg', '')

        # query ended
        set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)
        return

    if update.message.text == MORE_BUTT:
        find_again_with_sort(bot, update, None)
        return
    elif update.message.text == AWESOMESS_BUTT:
        find_again_with_sort(bot, update, 'awesome')
        return
    elif update.message.text == MOST_LUX_BUTT:
        find_again_with_sort(bot, update, 'lux')
        return
    elif update.message.text == MOST_CHEAP_BUTT:
        find_again_with_sort(bot, update, 'cheap')
        return

    #### PARSE QUESTION #######

    # do we already have a question ?
    # lets set query status to false = we are working on it
    set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, False)
    parse_response(bot, chat_id, last_msg, session, query, update)


def parse_response(bot, chat_id, last_msg, session, text, update):
    response = parse_query(bot, chat_id, session, update, last_msg if last_msg != '' else text)
    # From dialog flow get action
    print(str(response))
    action = None
    try:
        action = response['result']['action']
    except Exception as e:
        logger.error("Failed to get response from dialogflow, will try again " + str(e))
        response = parse_query(bot, chat_id, session, update, last_msg if last_msg != '' else text)
    try:
        action = response['result']['action']
    except Exception as e:
        logger.error("We failed to get response second time " + str(response) + " error was " + str(e))
    #### IS IT WELCOME REQUEST ?
    if get_from_memory_DB(update.message.from_user, USER.LAST_D_ACTION) == 'input.welcome':
        # since we parsed question - remove last msg
        set_to_memory_DB(update.message.from_user, 'last_msg', '')
    ##### IS IT A LOOP ? ######
    if action == 'input.welcome' and get_from_memory_DB(update.message.from_user,
                                                        USER.LAST_D_ACTION) == 'input.welcome':
        action = 'input.loop'
        update.message.reply_text('Что бы ты хотел съесть ? Например, Ларису ивановну хо... салат с кунжутом хочу !')
        # clean last D action because we used it
        set_to_memory_DB(update.message.from_user, USER.LAST_D_ACTION, 'None')
        set_to_memory_DB(update.message.from_user, 'last_action', 'None')

        # query ended
        set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)
        return
    if action == 'input.welcome':
        update.message.reply_text(response['result']['fulfillment']['speech'])
        set_to_memory_DB(update.message.from_user, 'last_action', str(action))
        set_to_memory_DB(update.message.from_user, USER.LAST_D_ACTION, str(action))

        location = get_from_memory_DB(update.message.from_user, USER.LOCATION)
        if location is None:
            ask_user_location(chat_id, bot, update)
            set_to_memory_DB(update.message.from_user, 'last_msg', text)

            # query ended
            set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)
            return
    elif action == 'get-food':
        find_and_post_food(update, bot, response['result']['parameters']['food'], None)
        set_to_memory_DB(update.message.from_user, 'last_query', last_msg)
    else:
        update.message.reply_text(response['result']['fulfillment']['speech'])
    # detect_intent_texts(
    #     PROJECT_ID, session, text, lang_code)
    # query ended
    set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)
    return True


def find_again_with_sort(bot, update, sort):
    last_query = get_from_memory_DB(update.message.from_user, 'last_query')
    find_and_post_food(update, bot, last_query, sort)
    logger.info("we repeating query " + str(last_query))
    #### REMEMBER OUR QUERY ####
    set_to_memory_DB(update.message.from_user, 'last_msg', last_query)


def parse_query(bot, chat_id, session, update, msg):
    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)
    request = ai.text_request()
    request.lang = 'ru'  # optional, default value equal 'en'
    request.session_id = session
    request.query = msg
    print(request.query)
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    response = request.getresponse()
    response = json.loads(response.read().decode('utf-8'))
    set_to_memory_DB(update.message.from_user, USER.LAST_D_ACTION, response["result"]["action"])
    return response


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
    # get or create user session
    get_user_session(update.message.from_user)
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    set_to_memory_DB(update.message.from_user, 'last_location', user_location)
    update.message.reply_text('Отлично!')
    if not save_user_location(update.message.chat_id, user, user_location):
        logger.error("Failed to save data to menuet")
    set_to_memory_DB(update.message.from_user, 'last_action', 'location')

    set_to_memory_DB(update.message.from_user, USER.QUERY_STATUS, True)
    process_request(bot, update)
    return BIO


def nothing_to_say(update, bot):
    update.message.reply_text("Мой разум...покой... Что хочешь смертный ?")
    return


def HALP(bot, update):
    update.message.reply_markdown(
        "Я могу подсказать где найти твою любимую еду!\n "
        "\nПросто отправь мне свое местоположение и запрос - я все найду для тебя!"
        "\nА если захочешь задонатить - [button]")
    return


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("534041755:AAF8uLqAWAFsOY7jqPRwaT_LyFUoFdNogbY")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', HALP))

    dp.add_handler(MessageHandler(Filters.location, location))
    # on noncommand i.e message - parse request the message on Telegram
    dp.add_handler(MessageHandler(Filters.all, process_request))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')

    updater.idle()


if __name__ == '__main__':
    try:
        main()
    except:
        logger.error("We got error in Main")
