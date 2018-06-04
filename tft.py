# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '../ft')

import os
from flask import Flask
from flask_mail import Mail, Message
from passlib.hash import sha256_crypt
from werkzeug.utils import secure_filename
import requests, json
from pymongo import MongoClient
import telebot
from telebot import types
from datetime import datetime, timezone
import time
import random
import ft_functions
from keys import FLASK_SECRET_KEY, TG_TOKEN, DF_TOKEN, GOOGLE_MAPS_API_KEY, MAIL_PWD
from translations import L10N

print(' ')
print('########### Fellowtraveler Telegram Chatbot - New session ############')

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = FLASK_SECRET_KEY
bot = telebot.TeleBot(TG_TOKEN)

mail = Mail(app)
app.config.update(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=True,
    MAIL_USERNAME = 'mailvulgaris@gmail.com',
    MAIL_PASSWORD = MAIL_PWD
)
mail = Mail(app)

'''
    All commands can be entered either using InlineKeyboardButtons or by typing exact or close by meaning words.
    Correspondingly 2 main hadlers are used - one for InlineKeyboardButtons (@bot.callback_query_handler) and another
    for plain text input (@bot.message_handler(content_types = ['text'])). All text input is "fed" to Dialogflow to
    get intent and text responses. Conversation chains are controlled using a variable contexts (a list).

    P.s. Commands enteres via BotFather:
    start - Let's get acquainted
    help - Get help
    tell_your_story - Display this traveler's story
    you_got_fellowtraveler - Do you have it? Get info what to do next
    change_language - Change language  
'''

####################################### TG Bot INI START #######################################

OURTRAVELLER = 'Teddy'
PHOTO_DIR = '../ft/static/uploads/{}/'.format(OURTRAVELLER) # where photos from places visited are saved
SERVICE_IMG_DIR = '../ft/static/uploads/{}/service/'.format(OURTRAVELLER) # where 'general info' images are saved (summary map, secret code example etc)
SHORT_TIMEOUT = 1  # 2 # seconds, between messages for imitation of 'live' typing
MEDIUM_TIMEOUT = 2  # 4
LONG_TIMEOUT = 3  # 6
SUPPORT_EMAIL = 'iurii.dziuban@gmail.com'
USER_LANGUAGE = None

CONTEXTS = []   # holds last state
NEWLOCATION = {    # holds data for traveler's location before storing it to DB
    'author': None,
    'channel': 'Telegram',
    'user_id_on_channel': None,
    'longitude': None,
    'latitude': None,
    'formatted_address': None,
    'locality': None,
    'administrative_area_level_1': None,
    'country': None,
    'place_id': None,
    'comment': None,
    'photos': []
}

LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
    #'de': 'Deutsch',
    #'fr': 'Français',
    'uk': 'Українська'
}
####################################### TG Bot INI END #########################################

###################################### '/' Handlers START ######################################

@bot.message_handler(commands=['start'])
# Block 0
def start_handler(message):
    global CONTEXTS
    global USER_LANGUAGE
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    # Get user language from message
    if not USER_LANGUAGE:
        USER_LANGUAGE = get_language(message)

    if 'if_journey_info_needed' not in CONTEXTS:
        CONTEXTS.clear()
        # message0 = 'Hello'
        bot.send_message(message.chat.id, '{}, {}!'.format(L10N['message0'][USER_LANGUAGE], message.from_user.first_name))
        time.sleep(SHORT_TIMEOUT)
        travelers_story_intro(message.chat.id)
        if 'if_journey_info_needed' not in CONTEXTS:
            CONTEXTS.append('if_journey_info_needed')
    else:
        travelers_story_intro(message.chat.id)
        if 'if_journey_info_needed' not in CONTEXTS:
            CONTEXTS.append('if_journey_info_needed')
    # Console logging
    print()
    print('User entered "/start"')
    print('Contexts: {}'.format(CONTEXTS))


@bot.message_handler(commands=['tell_your_story'])
def tell_your_story(message):
    global CONTEXTS
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    travelers_story_intro(message.chat.id)
    if 'if_journey_info_needed' not in CONTEXTS:
        CONTEXTS.append('if_journey_info_needed')
    # Console logging
    print()
    print('User entered "/tell_your_story"')
    print('Contexts: {}'.format(CONTEXTS))


@bot.message_handler(commands=['help'])
def help(message):
    global CONTEXTS
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    get_help(message.chat.id)
    # Console logging
    print()
    print('User entered "/help"')
    print('Contexts: {}'.format(CONTEXTS))


@bot.message_handler(commands=['you_got_fellowtraveler'])
def you_got_fellowtraveler(message):
    global CONTEXTS
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    if 'code_correct' not in CONTEXTS:
        # message1 = 'Congratulations! That\'s a tiny adventure and some responsibility ;)'
        # message60 = 'To proceed please <b>enter the secret code</b> from the toy'
        bot.send_message(message.chat.id, '{}\n{}'.format(L10N['message1'][USER_LANGUAGE], L10N['message60'][USER_LANGUAGE]), parse_mode='html')
        secret_code_img = open(SERVICE_IMG_DIR + 'how_secret_code_looks_like.jpg', 'rb')
        bot.send_photo(message.chat.id, secret_code_img, reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
    else:
        # message6 = 'Ok'
        # message8 = 'What would you like to do next?'
        bot.send_message(message.chat_id,
                         '{}. {}'.format(L10N['message6'][USER_LANGUAGE], L10N['message8'][USER_LANGUAGE]),
                         parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
    # Console logging
    print()
    print('User entered "/you_got_fellowtraveler"')
    print('Contexts: {}'.format(CONTEXTS))


@bot.message_handler(commands=['change_language'])
def change_language(message):
    global USER_LANGUAGE

    if not USER_LANGUAGE:
        USER_LANGUAGE = get_language(message)

    # message81 = 'Please select your language'
    bot.send_message(message.chat.id,
                     L10N['message81'][USER_LANGUAGE], parse_mode='html', reply_markup=change_language_menu_kb(USER_LANGUAGE))
    print()
    print('User entered "/change_language"')
    print('Contexts: {}'.format(CONTEXTS))

###################################### '/' Handlers END ######################################

################################### 'Custom' handlers START ##################################


@bot.message_handler(content_types=['text'])
# Handling all text input (NLP using Dialogflow and then depending on recognised intent and contexts variable
def text_handler(message):
    global CONTEXTS
    global USER_LANGUAGE
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    # Get input data
    users_input = message.text
    chat_id = message.chat.id
    from_user = message.from_user

    if USER_LANGUAGE == None:
        USER_LANGUAGE = get_language(message)

    # And pass it to the main handler function [main_hadler()]
    main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=False, other_input=False)


@bot.callback_query_handler(func=lambda call: True)
# Handling clicks on different InlineKeyboardButtons
def button_click_handler(call):
    # All possible buttons (10)
    # Yes | No, thanks | Cancel | Help | You got Teddy? | Teddy's story | Next | Contact support | Instructions | Add location
    # Buttons | Instructions | Add location | are available only after entering secret code
    # Buttons | You got Teddy? | Teddy's story | Help | Contact Support | are activated irrespective of context,
    # Buttons | Instructions | Add location | are activated always in context 'code_correct',
    # other buttons ( Yes | No, thanks | Cancel | Next) - depend on context, if contexts==[] or irrelevant context - they
    # should return a response for a Fallback_Intent
    global CONTEXTS
    global USER_LANGUAGE
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    bot.answer_callback_query(call.id, text="")

    # Get input data
    users_input = call.data
    chat_id = call.message.chat.id
    from_user = call.from_user

    # Get user language from message
    if not USER_LANGUAGE:
        USER_LANGUAGE = get_language(call)

    # And pass it to the main handler function [main_hadler()]
    main_handler(users_input, chat_id, from_user, is_btn_click=True, geodata=None, media=False, other_input=False)


@bot.message_handler(content_types=['location'])
def location_handler(message):
    global CONTEXTS
    global NEWLOCATION
    global USER_LANGUAGE
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    # Get input data
    users_input = 'User posted location'
    chat_id = message.chat.id
    from_user = message.from_user
    lat = message.location.latitude
    lng = message.location.longitude

    if USER_LANGUAGE == None:
        USER_LANGUAGE = USER_LANGUAGE = get_language(message)

    # And pass it to the main handler function [main_hadler()]
    main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata={'lat': lat, 'lng': lng}, media=False, other_input=False)


@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    '''
        The problem is that user may upload several photos, each one is proccessed separately and thus
        we get duplicate responses for every image (plus if updating contexts [delete 'media_input', append
        'if_comments'] after the 1st image then the 2nd and so on images trigger Fallback)
        Possible solution is to respond only to the 1st image and to save in contexts that the last input was image
        (plus not remove 'media_input' context)
        Then on the next input:
        if image - process it but don't respond,
        else - respond as usual, remove from contexts 'media_input' and the flag indicating that the last input was image
    '''
    global NEWLOCATION
    global CONTEXTS
    global USER_LANGUAGE

    # Get input data
    chat_id = message.chat.id
    from_user = message.from_user

    if USER_LANGUAGE == None:
        USER_LANGUAGE = get_language(message)

    # Get, check, save photos, add paths to NEWLOCATION['photos]
    if 'media_input' in CONTEXTS:
        file = bot.get_file(message.photo[-1].file_id)
        image_url = 'https://api.telegram.org/file/bot{0}/{1}'.format(TG_TOKEN, file.file_path)
        image_name = image_url.split("/")[-1]
        try:
            photo_filename = secure_filename(image_name)
            if ft_functions.valid_url_extension(photo_filename) and ft_functions.valid_url_mimetype(photo_filename):
                file_name_wo_extension = 'fellowtravelerclub-{}'.format(OURTRAVELLER)
                file_extension = os.path.splitext(photo_filename)[1]
                current_datetime = datetime.now().strftime("%d%m%y%H%M%S")
                random_int = random.randint(100, 999)
                path4db = file_name_wo_extension + '-' + current_datetime + str(random_int) + file_extension
                path = PHOTO_DIR + path4db

                r = requests.get(image_url, timeout=0.5)
                if r.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(r.content)
                NEWLOCATION['photos'].append(path4db)
                users_input = 'User posted a photo'

                # Contexts - indicate that last input was an image
                if 'last_input_media' not in CONTEXTS:
                    CONTEXTS.append('last_input_media')
                    users_input = 'User uploaded an image'
                    main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=True, other_input=False)
        except Exception as e:
            print('photo_handler() exception: {}'.format(e))
            #send_email('Logger', 'photo_handler() exception: {}'.format(e))
            users_input = 'File has invalid image extension or invalid image format'
            main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=False, other_input=False)
    else:
        if 'last_input_media' not in CONTEXTS:
            CONTEXTS.append('last_input_media')
            users_input = 'Nice image ;)'
            print('Really true!')
            print('CONTEXTS: {}'.format(CONTEXTS))
            main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=True, other_input=False)


@bot.message_handler(content_types=['audio', 'document', 'sticker', 'video', 'video_note', 'voice', 'contact', 'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created', 'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message'])
def other_content_types_handler(message):
    global CONTEXTS
    global NEWLOCATION
    global USER_LANGUAGE
    # A fix intended not to respond to every image uploaded (if several)
    respond_to_several_photos_only_once()

    # Get input data
    users_input = ';)' #User entered something different from text, button_click, photo or location
    chat_id = message.chat.id
    from_user = message.from_user

    if USER_LANGUAGE == None:
        USER_LANGUAGE = get_language(message)

    # And pass it to the main handler function [main_hadler()]
    main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=False, other_input=True)


################################### 'Custom' handlers END ##################################

####################################### Functions START ####################################


def dialogflow(query, chat_id, lang_code='en'):
    '''
        Function to communicate with Dialogflow for NLP
    '''
    URL = 'https://api.dialogflow.com/v1/query?v=20170712'
    print('USER_LANGUAGE: ' + lang_code)
    HEADERS = {'Authorization': 'Bearer ' + DF_TOKEN, 'content-type': 'application/json'}
    payload = {'query': query, 'sessionId': chat_id, 'lang': lang_code}
    r = requests.post(URL, data=json.dumps(payload), headers=HEADERS).json()
    print('#####')
    print('Request from DF: ')
    print(r)
    print('#####')
    intent = r.get('result').get('metadata').get('intentName')
    speech = r.get('result').get('fulfillment').get('speech')
    status = r.get('status').get('code')
    output = {
        'status': status,
        'intent': intent,
        'speech': speech
    }
    return output


def main_handler(users_input, chat_id, from_user, is_btn_click=False, geodata=None, media=False, other_input=False):
    '''
        Main handler. Function gets input from user (typed text OR callback_data from button clicks), 'feeds' it
        to Dialogflow for NLP, receives intent and speech, and then depending on intent and context responds to user.
        users_input - typed text or callback_data from button, 'dummy' text in case location/photo/other content_types input
        chat_id - chat ID (call.message.chat.id or message.chat.id)
        from_user - block of data about user (containing his/her 1st name, id etc)
        is_btn_click - whether it's callback_data from button (True) or manual text input (False, default)
        geodata - dictionary with latitude/longitude or None (default)
        media - if it's a photo (by default = False)
        other_input - any other content type besides text, button click, location or photo (by default = False)
    '''
    global CONTEXTS
    global NEWLOCATION

    if geodata:
        # message2 = 'Nice place ;)'
        # message3 = 'That\'s interesting ;)'
        # message4 = 'Hm..'
        short_reaction_variants = [';)', L10N['message2'][USER_LANGUAGE], L10N['message3'][USER_LANGUAGE], L10N['message4'][USER_LANGUAGE]]
        speech = random.choice(short_reaction_variants)
        intent = 'location_received'
    elif media:
        # message5 = 'Nice image ;)'
        short_reaction_variants = [';)', L10N['message5'][USER_LANGUAGE], L10N['message3'][USER_LANGUAGE], L10N['message4'][USER_LANGUAGE]]
        speech = random.choice(short_reaction_variants)
        intent = 'media_received'
    elif other_input:
        # message6 = 'Ok'
        # message7 = 'Okay'
        # messag8 = 'What would you like to do next?'
        short_reaction_variants = [';)', L10N['message6'][USER_LANGUAGE], L10N['message7'][USER_LANGUAGE], L10N['message4'][USER_LANGUAGE]]
        reaction = random.choice(short_reaction_variants)
        speech = '{}\n{}'.format(reaction, L10N['message8'][USER_LANGUAGE])
        intent = 'other_content_types'
    else:
        # Text input and callback_data from button clicks is 'fed' to Dialogflow for NLP
        dialoflows_response = dialogflow(users_input, chat_id, USER_LANGUAGE)
        speech = dialoflows_response['speech']
        intent = dialoflows_response['intent']

    # Block 0. User clicked/typed "Contact support" and the next text input should be sent to support email
    if 'contact_support' in CONTEXTS:
        # Text input is supposed or button clicks, other content types will be rejected
        if not is_btn_click:
            if not media \
                and not geodata \
                and not other_input:
                # Remove 'contact_support' from contexts
                CONTEXTS.remove('contact_support')
                # Redirect user's message to SUPPORT_EMAIL
                if send_email(from_user.id, users_input):
                    # Report about successfull operation to user
                    # messag9 = 'Your message was successfully sent to my author\n(<b>iurii.dziuban@gmail.com</b>).\nWhat would you like to do next?'
                    bot.send_message(chat_id, L10N['message9'][USER_LANGUAGE],
                                 parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
                else:
                    # Report about unsuccessfull operation to user
                    # message10 = 'Some problems occured when trying to send your message to my author (<b>iurii.dziuban@gmail.com</b>). Could you please write to his email yourself? Sorry for that..'
                    bot.send_message(chat_id, L10N['message10'][USER_LANGUAGE],
                                 parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
            else:
                # message11 = 'Sorry but I can send only text. Please type something ;)'
                bot.send_message(chat_id, L10N['message11'][USER_LANGUAGE],
                                 parse_mode='html', reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
        else:
            # Button clicks
            # If user cancels sending message to support
            if intent == 'smalltalk.confirmation.cancel':
                CONTEXTS.remove('contact_support')
                # message12 = 'Cancelled\nWhat would you like to do next?'
                bot.send_message(chat_id, L10N['message12'][USER_LANGUAGE], reply_markup=intro_menu_kb(USER_LANGUAGE))
            # All other button clicks
            else:
                # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
                if not always_triggered(chat_id, intent, speech):
                    # All other text inputs/button clicks
                    default_fallback(chat_id, intent, speech)

    # Block 1. Traveler's story
    # Block 1-1. Reply to typing/clocking_buttons 'Yes'/'No' displayed after the intro block asking
    # if user want's to know more about T. journey
    # On exit of block if user enters 'Yes' - context 'journey_next_info', if 'No' or he/she clicks buttons of
    # previous blocks - contexts[] is cleared
    elif 'if_journey_info_needed' in CONTEXTS:
        if intent == 'smalltalk.confirmation.no':
            time.sleep(SHORT_TIMEOUT)
            if 'if_journey_info_needed' in CONTEXTS:
                CONTEXTS.remove('if_journey_info_needed')
            # message13 = 'Ok. Than we can just talk ;)\nJust in case here\'s my menu'
            bot.send_message(chat_id, L10N['message13'][USER_LANGUAGE],
                             reply_markup=intro_menu_kb(USER_LANGUAGE))
        elif intent == 'smalltalk.confirmation.yes':
            journey_intro(chat_id, OURTRAVELLER)
            if 'if_journey_info_needed' in CONTEXTS:
                CONTEXTS.remove('if_journey_info_needed')
            CONTEXTS.append('journey_next_info')
        # If user is clicking buttons under previous blocks (for eg., buttons 'FAQ', <Traveler>'s story, You got traveler)
        # call classifier() with cleaned contexts
        else:
            # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
            if not always_triggered(chat_id, intent, speech):
                # All other text inputs/button clicks
                default_fallback(chat_id, intent, speech)

    # Block 1-2. Reply to entering/clicking buttons 'Next/Help' after block#1 showing overall map of traveler's journey;
    # on entry - context 'journey_next_info',
    # on exit of block if user clicks/types
    # 1) 'Next' and
    # a) if only 1 place was visited - contexts[] is cleared
    # b) if several places were visited - 2 contexts are added:
    # 'journey_summary_presented' and {'location_shown': None, 'total_locations': total_locations}
    # 2) 'Help' or clicks buttons of previous blocks - contexts[] is cleared
    elif 'journey_next_info' in CONTEXTS:
        if intent == 'next_info':
            total_locations = journey_begins(chat_id, OURTRAVELLER)
            time.sleep(SHORT_TIMEOUT)
            if total_locations == 0:
                # message14 = 'My journey hasn\'nt started yet. Will you add my first location?'
                bot.send_message(chat_id,
                                 L10N['message14'][USER_LANGUAGE],
                                 reply_markup=intro_menu_kb(USER_LANGUAGE))
            # If there's only 1 location, show it and present basic menu ("Teddy's story/Help/You got Teddy?")
            elif total_locations == 1:
                the_1st_place(chat_id, OURTRAVELLER, False)
                # message15 = 'And that\'s all my journey so far ;)\n\nWhat would you like to do next? We can just talk or use this menu:'
                bot.send_message(chat_id,
                                 L10N['message15'][USER_LANGUAGE],
                                 reply_markup=intro_menu_kb(USER_LANGUAGE))
                if 'journey_next_info' in CONTEXTS:
                    CONTEXTS.remove('journey_next_info')
            # If there are >1 visited places, ask user if he wants to see them ("Yes/No/Help")
            else:
                # message16 = 'Would you like to see all places that I have been to?'
                bot.send_message(chat_id, L10N['message16'][USER_LANGUAGE],
                                 reply_markup=yes_no_help_menu_kb(USER_LANGUAGE))
                if 'journey_next_info' in CONTEXTS:
                    CONTEXTS.remove('journey_next_info')
                CONTEXTS.append('journey_summary_presented')
                CONTEXTS.append({'location_shown': None, 'total_locations': total_locations})
        elif intent == 'show_faq':
            if 'journey_next_info' in CONTEXTS:
                CONTEXTS.remove('journey_next_info')
            get_help(chat_id)
        # If user is clicking buttons under previous blocks - call classifier() with cleaned contexts
        else:
            # Buttons | You got Teddy? | Teddy's story are activated irrespective of context
            if not always_triggered(chat_id, intent, speech):
                # All other text inputs/button clicks
                default_fallback(chat_id, intent, speech)

    # Block 1-3. Reply to entering/clicking buttons 'Yes/No,thanks/Help' displayed after the prevoius block with journey summary;
    # on entry - 2 contexts 'journey_summary_presented' and {'location_shown': None, 'total_locations': total_locations},
    # on exit:
    # 1) if user types/clicks 'Yes' - 2 contexts 'locations_iteration' and {'location_shown': 0, 'total_locations': total_locations}
    # 2) if user types/clicks 'No/Help' or clicks buttons of previous blocks - contexts[] is cleared
    elif 'journey_summary_presented' in CONTEXTS:
        if intent == 'smalltalk.confirmation.yes':  # "Yes" button is available if >1 places were visited
            the_1st_place(chat_id, OURTRAVELLER, True)
            if 'journey_summary_presented' in CONTEXTS:
                CONTEXTS.remove('journey_summary_presented')
            if 'locations_iteration' not in CONTEXTS:
                CONTEXTS.append('locations_iteration')
            for context in CONTEXTS:
                if 'location_shown' in context:
                    context['location_shown'] = 0
        elif intent == 'smalltalk.confirmation.no':
            time.sleep(SHORT_TIMEOUT)
            if 'journey_summary_presented' in CONTEXTS:
                CONTEXTS.remove('journey_summary_presented')
            # message13 = 'Ok. Than we can just talk ;)\nJust in case here\'s my menu'
            bot.send_message(chat_id, L10N['message13'][USER_LANGUAGE],
                             reply_markup=intro_menu_kb(USER_LANGUAGE))
        elif intent == 'show_faq':
            if 'journey_summary_presented' in CONTEXTS:
                CONTEXTS.remove('journey_summary_presented')
            get_help(chat_id)
        # If user is clicking buttons under previous blocks - call classifier() with cleaned contexts
        else:
            # Buttons | You got Teddy? | Teddy's story are activated irrespective of context
            if not always_triggered(chat_id, intent, speech):
                # All other text inputs/button clicks
                default_fallback(chat_id, intent, speech)

    # Block 1-4. Reply to entering/clicking buttons 'Next/Help' after block#3 showing the 1st place among several visited;
    # is executed in cycle
    # on entry - 2 contexts: 'locations_iteration' and {'location_shown': X, 'total_locations': Y}
    # (where X = the serial number of place visited, for eg. 0 - the 1st place, 2 - the 3rd place),
    # on exit:
    # 1) if user types/clicks 'Yes' and
    # a) if the last place visited is shown - contexts[] is cleared
    # b) if places to show remain - 2 contexts: 'locations_iteration' and {'location_shown': X+1, 'total_locations': Y}
    # 2) types/ckicks button 'Help' or buttons of previous blocks - contexts[] is cleared
    elif 'locations_iteration' in CONTEXTS:
        if intent == 'next_info':
            location_shown = 0
            total_locations = 1
            for context in CONTEXTS:
                if 'location_shown' in context:
                    location_shown = context['location_shown']
                    total_locations = context['total_locations']
            if total_locations - (location_shown + 1) == 1:
                if 'locations_iteration' in CONTEXTS:
                    CONTEXTS.remove('locations_iteration')
                every_place(chat_id, OURTRAVELLER, location_shown + 1, False)
                # message15 = 'And that\'s all my journey so far ;)\n\nWhat would you like to do next? We can just talk or use this menu:'
                bot.send_message(chat_id,
                                 L10N['message15'][USER_LANGUAGE],
                                 reply_markup=intro_menu_kb(USER_LANGUAGE))
            elif total_locations - (location_shown + 1) > 1:
                every_place(chat_id, OURTRAVELLER, location_shown + 1, True)
                for context in CONTEXTS:
                    if 'location_shown' in context:
                        context['location_shown'] += 1
        elif intent == 'show_faq':
            if 'locations_iteration' in CONTEXTS:
                CONTEXTS.remove('locations_iteration')
            get_help(chat_id)
        # If user is clicking buttons under previous blocks - call classifier() with cleaned contexts
        else:
            # Buttons | You got Teddy? | Teddy's story are activated irrespective of context
            if not always_triggered(chat_id, intent, speech):
                # All other text inputs/button clicks
                default_fallback(chat_id, intent, speech)

    # Block 2. If you got a fellow traveler
    # Block 2-1. User clicked button/typed 'You got Teddy?' and was prompted to enter the secret code
    elif 'enters_code' in CONTEXTS:
        # If user enters 'Cancel' or smth similar after entering invalid secret_code - update contexts
        if intent == 'smalltalk.confirmation.cancel':
            if 'enters_code' in CONTEXTS:
                CONTEXTS.remove('enters_code')
            # message6, message8 = 'Ok. What would you like to do next?'
            bot.send_message(chat_id, '{}. {}'.format(L10N['message6'][USER_LANGUAGE], L10N['message8'][USER_LANGUAGE]),
                         reply_markup=intro_menu_kb(USER_LANGUAGE))
        elif intent == 'contact_support':
            if 'enters_code' in CONTEXTS:
                CONTEXTS.remove('enters_code')
            CONTEXTS.append('contact_support')
            # message17 = 'Any problems, questions, suggestions, remarks, proposals etc? Please enter them below or write to my author\'s email <b>iurii.dziuban@gmail.com</b>\n\n You may also consider visiting <a href="https://iuriid.github.io">iuriid.github.io</a>.'
            bot.send_message(chat_id, L10N['message17'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
        # If user enters whatever else, not == intent 'smalltalk.confirmation.cancel'
        else:
            if not is_btn_click:
                secret_code_entered = users_input
                if secret_code_validation(secret_code_entered):
                    if 'enters_code' in CONTEXTS:
                        CONTEXTS.remove('enters_code')
                    CONTEXTS.append('code_correct')
                    # message18 = 'Code correct, thanks! Sorry for formalities'
                    bot.send_message(chat_id, L10N['message18'][USER_LANGUAGE])
                    ''' message19 =  As I might have said, my goal is to see the world.'
                                     '\n\n And as your fellow traveler I will kindly ask you for 2 things:'
                                     '\n- Please show me some nice places of your city/country or please take me with you if you are traveling somewhere. '
                                     'Please document where I have been using the button "<b>Add location</b>".'
                                     '\n - After some time please pass me to somebody else ;)'
                                     '\n\n For more detailed instructions - please click "<b>Instructions</b>"'
                                     '\n\nIf you\'ve got some problems, you can also write to my author (button "<b>Contact support</b>")
                    '''
                    bot.send_message(chat_id, L10N['message19'][USER_LANGUAGE],
                                     parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
                else:
                    # message20 = 'Incorrect secret code. Please try again'
                    bot.send_message(chat_id, L10N['message20'][USER_LANGUAGE],
                                     reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
            else:
                # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
                if not always_triggered(chat_id, intent, speech):
                    # All other text inputs/button clicks
                    default_fallback(chat_id, intent, speech)

    # Block 2-2. User entered correct password and now can get 'priviledged' instructions, add location or contact support
    # Context 'code_correct' is being cleared after adding a new location, clicking 'Contact support' or if user enters
    # commands outside of of block that is displayed after entering secret code
    elif 'code_correct' in CONTEXTS:
        if intent == 'contact_support':
            CONTEXTS.clear()
            CONTEXTS.append('code_correct')
            CONTEXTS.append('contact_support')
            # message17 = 'Any problems, questions, suggestions, remarks, proposals etc? Please enter them below or write to my author\'s email <b>iurii.dziuban@gmail.com</b>\n\n You may also consider visiting <a href="https://iuriid.github.io">iuriid.github.io</a>.'
            bot.send_message(chat_id, L10N['message17'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
        elif intent == 'show_instructions':
            CONTEXTS.clear()
            CONTEXTS.append('code_correct')
            # message21 = 'Here are our detailed instructions for those who got'
            bot.send_message(chat_id, '{} {}'.format(L10N['message21'][USER_LANGUAGE], OURTRAVELLER),
                             parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
        elif intent == 'add_location':
            # message22 = 'First please tell <i>where</i>'
            # message23 = '<i>is now</i> (you may use the button \"<b>Share your location</b>\" below) \n\nor \n\n<i>where he was</i> photographed (to enter address which differs from your current location please <b>attach >> Location</b> and drag the map to desired place)'
            bot.send_message(chat_id, '{} {} {}'.format(L10N['message22'][USER_LANGUAGE], OURTRAVELLER, L10N['message23'][USER_LANGUAGE]),
                             parse_mode='html', reply_markup=share_location_kb(USER_LANGUAGE))
            if 'location_input' not in CONTEXTS:
                CONTEXTS.append('location_input')
        else:
            # Block 2-3. User enters location ('location_input' in contexts)
            # It can be either his/her current location shared using Telegram's location sharing function or a plain text input
            # from text_handler() which should be processed using Google Maps Geocoding API
            if 'location_input' in CONTEXTS:
                # And user shared his/her location
                if intent == 'location_received':  # sharing or current location
                    # Reverse geocode lat/lng to geodata
                    # Also as this is the 1st data for new locations, fill the fields 'author', 'channel' and 'user_id_on_channel'
                    NEWLOCATION['author'] = from_user.first_name
                    NEWLOCATION['user_id_on_channel'] = from_user.id
                    NEWLOCATION['channel'] = 'Telegram'
                    NEWLOCATION['longitude'] = geodata['lng']
                    NEWLOCATION['latitude'] = geodata['lat']
                    # Erase the remaining fields of NEWLOCATION in case user restarts
                    NEWLOCATION['formatted_address'] = None
                    NEWLOCATION['locality'] = None
                    NEWLOCATION['administrative_area_level_1'] = None
                    NEWLOCATION['country'] = None
                    NEWLOCATION['place_id'] = None
                    NEWLOCATION['comment'] = None
                    NEWLOCATION['photos'] = []

                    gmaps_geocoder(geodata['lat'], geodata['lng'])
                    CONTEXTS.remove('location_input')
                    # Ready for the next step - adding photos
                    CONTEXTS.append('media_input')
                    # message24 = 'Thanks! Now could you please upload some photos with'
                    # message25 = 'from this place?\nSelfies with'
                    # message26 = 'are also welcome ;)'
                    bot.send_message(chat_id,
                                     '{0} {1} {2} {1} {3}'.format(L10N['message24'][USER_LANGUAGE], OURTRAVELLER, L10N['message25'][USER_LANGUAGE], L10N['message26'][USER_LANGUAGE]), parse_mode='html',
                                     reply_markup=next_reset_instructions_menu_kb(USER_LANGUAGE))

                # User cancels location entry - leave 'code_correct' context, remove 'location_input'
                elif intent == 'smalltalk.confirmation.cancel':
                    CONTEXTS.remove('location_input')
                    # message6, message8 = 'Ok. What would you like to do next?'
                    bot.send_message(chat_id,
                                     '{}. {}'.format(L10N['message6'][USER_LANGUAGE], L10N['message8'][USER_LANGUAGE]),
                                     parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))

                # User wants detailed instructions - contexts unchanged
                elif intent == 'show_instructions':
                    # message21 = 'Here are the detailed instructions for those who got'
                    bot.send_message(chat_id,
                                     '{} {}'.format(L10N['message6'][USER_LANGUAGE], OURTRAVELLER),
                                     parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))

                # User should be entering location but he/she types smth or clicks other buttons besides 'Cancel' or
                # 'Instructions'
                else:
                    # message27 = 'That doesn\'t look like a valid location. Please try once again'
                    bot.send_message(chat_id,
                                     L10N['message27'][USER_LANGUAGE],
                                     parse_mode='html', reply_markup=cancel_or_instructions_menu_kb(USER_LANGUAGE))

            # Block 2-4. User should be uploading a/some photo/-s.
            elif 'media_input' in CONTEXTS:
                # User did upload some photos - thank him/her and ask for a comment
                if intent == 'media_received':
                    # If user uploaded several images - respond only to the 1st one
                    if 'last_media_input' not in CONTEXTS:
                        if 'any_comments' not in CONTEXTS:
                            CONTEXTS.append('any_comments')
                        # message28 = 'Thank you!'
                        # message29 = 'Any comments (how did you get'
                        # message30 = ', what did you feel, any messages for future'
                        # message31 = '\'s fellow travelers)?'
                        bot.send_message(chat_id,
                                         '{0}\n{1} {2}{3} {2}{4}'.format(L10N['message28'][USER_LANGUAGE], L10N['message29'][USER_LANGUAGE], OURTRAVELLER, L10N['message30'][USER_LANGUAGE], L10N['message31'][USER_LANGUAGE]),
                                         parse_mode='html', reply_markup=next_reset_instructions_menu_kb(USER_LANGUAGE))

                # User refused to upload photos, clicked 'Next' - ask him/her for a comment
                elif intent == 'next_info':
                    CONTEXTS.clear()
                    CONTEXTS.append('code_correct')
                    CONTEXTS.append('any_comments')
                    # message6 = 'Ok'
                    # message29 = 'Any comments (how did you get'
                    # message30 = ', what did you feel, any messages for future'
                    # message31 = '\'s fellow travelers)?'
                    bot.send_message(chat_id,
                                     '{0}\n{1} {2}{3} {2}{4}'.format(
                                         L10N['message6'][USER_LANGUAGE],  L10N['message29'][USER_LANGUAGE], OURTRAVELLER, L10N['message30'][USER_LANGUAGE], L10N['message31'][USER_LANGUAGE]),
                                     parse_mode='html', reply_markup=next_reset_instructions_menu_kb(USER_LANGUAGE))

                # User resets location entry
                elif intent == 'reset':
                    CONTEXTS.clear()
                    CONTEXTS.append('code_correct')
                    # message32 = 'Ok, let\'s try once again'
                    bot.send_message(chat_id,
                                     L10N['message32'][USER_LANGUAGE],
                                     parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))

                else:
                    # User should be uploading photos but he/she didn't and also didn't click 'Cancel' but
                    # enters/clicks something else
                    # Buttons | You got Teddy? | Teddy's story | Help | etc are activated irrespective of context
                    if not always_triggered(chat_id, intent, speech):
                        # All other text inputs/button clicks
                        default_fallback(chat_id, intent, speech)

            # Block 2-5. User was prompted to leave a comment
            # He/she might enter text (Ok), click buttons under the prev. block (Next/Reset/Instructions) or enter
            # other input types (for eg., a sticker, photo, location etc) (not Ok)
            elif 'any_comments' in CONTEXTS \
                    and 'last_media_input' not in CONTEXTS: # that is last input was not a photo, photo/-s input in prev. block finished
                # Button clicks
                if is_btn_click:
                    # User doesn't want to give a comment
                    if intent == 'next_info':
                        NEWLOCATION['comment'] = ''
                        CONTEXTS.remove('any_comments')
                        CONTEXTS.append('ready_for_submit')
                        # Resume up user's input (location, photos, comment) and ask to confirm or reset
                        time.sleep(SHORT_TIMEOUT)
                        # message33 = 'In total your input will look like this:'
                        bot.send_message(chat_id,
                                         L10N['message33'][USER_LANGUAGE], parse_mode='html')
                        if new_location_summary(chat_id, from_user):
                            # message34 = 'Is that Ok? If yes, please click \"<b>Submit</b>\".\nOtherwise click \"<b>Reset</b>\" to start afresh'
                            bot.send_message(chat_id,
                                         L10N['message34'][USER_LANGUAGE],
                                         parse_mode='html', reply_markup=submit_reset_menu_kb(USER_LANGUAGE))
                        else:
                            # message35 = 'Hmm.. Some error occured. Could you please try again?'
                            bot.send_message(chat_id,
                                         L10N['message35'][USER_LANGUAGE],
                                         parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
                    elif intent == 'reset':
                        CONTEXTS.clear()
                        CONTEXTS.append('code_correct')
                        # message36 = 'Ok, let\'s try once again'
                        bot.send_message(chat_id,
                                         L10N['message36'][USER_LANGUAGE],
                                         parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
                    else:
                        # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
                        if not always_triggered(chat_id, intent, speech):
                            # All other text inputs/button clicks
                            default_fallback(chat_id, intent, speech)
                # Impropriate input (stickers, photo, location etc)
                elif geodata or media or other_input:
                    # message37 = 'Sorry but only text is accepted as a comment. Could you please enter a text message?'
                    bot.send_message(chat_id,
                                     L10N['message37'][USER_LANGUAGE], parse_mode='html', reply_markup=next_reset_instructions_menu_kb(USER_LANGUAGE))
                # Text input
                else:
                    # Update contexts - leave only 'code_correct' and 'any_comments'
                    CONTEXTS.clear()
                    CONTEXTS.append('code_correct')
                    CONTEXTS.append('ready_for_submit')

                    # Show user what he/she has entered as a comment
                    # message38 = 'Ok. So we\'ll treat the following as your comment:'
                    bot.send_message(chat_id,
                                     '{}\n<i>{}</i>'.format(L10N['message38'][USER_LANGUAGE], users_input),
                                     parse_mode='html')

                    # Save user's comment to NEWLOCATION
                    NEWLOCATION['comment'] = users_input

                    # Resume up user's input (location, photos, comment) and ask to confirm or reset
                    time.sleep(LONG_TIMEOUT)
                    # message33 = 'In total your input will look like this:'
                    bot.send_message(chat_id,
                                     L10N['message33'][USER_LANGUAGE], parse_mode='html')
                    if new_location_summary(chat_id, from_user):
                        time.sleep(SHORT_TIMEOUT)
                        # message34 = 'Is that Ok? If yes, please click \"<b>Submit</b>\".\nOtherwise click \"<b>Reset</b>\" to start afresh'
                        bot.send_message(chat_id,
                                         L10N['message34'][USER_LANGUAGE],
                                         parse_mode='html', reply_markup=submit_reset_menu_kb(USER_LANGUAGE))
                    else:
                        # message35 = 'Hmm.. Some error occured. Could you please try again?'
                        bot.send_message(chat_id,
                                         L10N['message35'][USER_LANGUAGE],
                                         parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))

            # Block 2-6. Submitting new location - user clicked 'Submit'
            elif 'ready_for_submit' in CONTEXTS:
                if intent == 'submit':
                    # Clear all contexts
                    CONTEXTS.clear()

                    # Save location and get the new secret code
                    location_submitted = submit_new_location(OURTRAVELLER)
                    new_code_generated = ft_functions.code_regenerate(OURTRAVELLER)

                    if location_submitted and new_code_generated:
                        # message40 = 'New location added!\n\nSecret code for adding the next location:
                        # message41 = 'Please save it somewhere or don\'t delete this message.\nIf you are going to pass'
                        # message42 = 'to somebody please write this code similar to how you received it'
                        bot.send_message(chat_id,
                                         '{0} <code>{1}</code>\n\n{2} {3} {4}'.format(
                                            L10N['message40'][USER_LANGUAGE], new_code_generated, L10N['message41'][USER_LANGUAGE], OURTRAVELLER, L10N['message42'][USER_LANGUAGE]),
                                         parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
                    else:
                        # message43 = 'Hmm... Sorry, but for some reason I failed to save your data to database.\nI informed my author (<b>iurii.dziuban@gmail.com</b>) about this and hope that he finds the reason soon.\nSorry for inconveniences..'
                        bot.send_message(chat_id,
                                             L10N['message43'][USER_LANGUAGE],
                                             parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
                elif intent == 'reset':
                    CONTEXTS.clear()
                    CONTEXTS.append('code_correct')
                    # message36 = 'Ok, let\'s try once again'
                    bot.send_message(chat_id,
                                     L10N['message36'][USER_LANGUAGE],
                                     parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
                else:
                    # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
                    if not always_triggered(chat_id, intent, speech):
                        # All other text inputs/button clicks
                        default_fallback(chat_id, intent, speech)

            else:
                # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
                if not always_triggered(chat_id, intent, speech):
                    # All other text inputs/button clicks
                    default_fallback(chat_id, intent, speech)

    # General endpoint - if user typed/clicked something and contexts[] is empty
    else:
        # Buttons | You got Teddy? | Teddy's story | Help | are activated irrespective of context
        if not always_triggered(chat_id, intent, speech):
            # All other text inputs/button clicks
            default_fallback(chat_id, intent, speech)

    # Console logging
    print('')
    if is_btn_click:
        input_type = 'button click'
    elif media:
        input_type = 'media upload'
    elif geodata:
        input_type = 'location input'
    elif other_input:
        input_type = 'other content types'
    else:
        input_type = 'entered manually'
    #print('User\'s input: {} ({})'.format(users_input, input_type))
    #print('Intent: {}, speech: {}'.format(intent, speech))
    #print('Contexts: {}'.format(CONTEXTS))


def always_triggered(chat_id, intent, speech):
    '''
        Buttons | You got Teddy? | Teddy's story | Help | are activated always, irrespective of context
        Buttons | Instructions | Add location | are activated always in context 'code_correct'
    '''
    global CONTEXTS
    global USER_LANGUAGE

    # User typed 'Help' or similar
    if intent == 'show_faq':
        get_help(chat_id)
        return True

    # User typed 'Teddy's story' or similar
    elif intent == 'tell_your_story':
        traveler_photo = open(SERVICE_IMG_DIR + OURTRAVELLER + '.jpg', 'rb')
        # message57 = 'My name is'
        # message58 = 'I\'m a traveler.\nMy dream is to see the world'
        bot.send_photo(chat_id, traveler_photo,
                       caption='{} <strong>{}</strong>. {}'.format(
                           L10N['message57'][USER_LANGUAGE], OURTRAVELLER, L10N['message58'][USER_LANGUAGE]), parse_mode='html')
        time.sleep(SHORT_TIMEOUT)
        # message59 = 'Do you want to know more about my journey?'
        bot.send_message(chat_id, L10N['message59'][USER_LANGUAGE],
                         reply_markup=yes_no_gotteddy_menu_kb(USER_LANGUAGE))
        if 'if_journey_info_needed' not in CONTEXTS:
            CONTEXTS.append('if_journey_info_needed')
        return True

    # User typed "You got Teddy" or similar
    elif intent == 'you_got_fellowtraveler':
        if 'code_correct' not in CONTEXTS:
            # message1 = 'Congratulations! That\'s a tiny adventure and some responsibility ;)'
            # message60 = 'To proceed please <b>enter the secret code</b> from the toy'
            bot.send_message(chat_id, '{}\n{}'.format(L10N['message1'][USER_LANGUAGE], L10N['message60'][USER_LANGUAGE]), parse_mode='html')
            # Image with an example of secret code
            secret_code_img = open(SERVICE_IMG_DIR + 'how_secret_code_looks_like.jpg', 'rb')
            bot.send_photo(chat_id, secret_code_img, reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
            CONTEXTS.clear()
            CONTEXTS.append('enters_code')
        else:
            # message6 = 'Ok'
            # message8 = 'What would you like to do next?'
            bot.send_message(chat_id,
                             '{}. {}'.format(L10N['message6'][USER_LANGUAGE], L10N['message8'][USER_LANGUAGE]),
                             parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
        return True

    # User clicks/types "Contact support"
    elif intent == 'contact_support':
        if 'contact_support' not in CONTEXTS:
            CONTEXTS.append('contact_support')
            # message17 = 'Any problems, questions, suggestions, remarks, proposals etc? Please enter them below or write to my author\'s email <b>iurii.dziuban@gmail.com</b>\n\n You may also consider visiting <a href="https://iuriid.github.io">iuriid.github.io</a>.'
            bot.send_message(chat_id, L10N['message17'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
        return True

    # Switch language buttons
    elif intent == 'change_language':
        # message81 = 'Please select your language'
        bot.send_message(chat_id,
                         L10N['message81'][USER_LANGUAGE], parse_mode='html',
                         reply_markup=change_language_menu_kb(USER_LANGUAGE))
        return True

    # Switch to English
    elif intent == 'language_to_english':
        USER_LANGUAGE = 'en'
        # message82 = 'Language was changed to <b>English</b>'
        bot.send_message(chat_id, L10N['message82'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
        return True

    # Switch to Russian
    elif intent == 'language_to_russian':
        USER_LANGUAGE = 'ru'
        # message82 = 'Language was changed to <b>English</b>'
        bot.send_message(chat_id, L10N['message82'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
        return True

    # Switch to Ukrainian
    elif intent == 'language_to_ukrainian':
        USER_LANGUAGE = 'uk'
        # message82 = 'Language was changed to <b>English</b>'
        bot.send_message(chat_id, L10N['message82'][USER_LANGUAGE],
                         parse_mode='html', reply_markup=intro_menu_kb(USER_LANGUAGE))
        return True

    # Buttons | Instructions | Add location | are activated always in context 'code_correct'
    if 'code_correct' in CONTEXTS:
        if intent == 'show_instructions':
            # message21 = 'Here are the detailed instructions for those who got'
            bot.send_message(chat_id, '{} {}'.format(L10N['message21'][USER_LANGUAGE], OURTRAVELLER),
                             parse_mode='html', reply_markup=you_got_teddy_menu_kb(USER_LANGUAGE))
            return True

        elif intent == 'add_location':
            # message22 = 'First please tell <i>where</i>'
            # message23 = '<i>is now</i> (you may use the button \"<b>Share your location</b>\" below) \n\nor \n\n<i>where he was</i> photographed (to enter address which differs from your current location please <b>attach >> Location</b> and drag the map to desired place)'
            bot.send_message(chat_id, '{} {} {}'.format(L10N['message22'][USER_LANGUAGE], OURTRAVELLER, L10N['message23'][USER_LANGUAGE]),
                             parse_mode='html', reply_markup=share_location_kb(USER_LANGUAGE))
            if 'location_input' not in CONTEXTS:
                CONTEXTS.append('location_input')
            return True

    else:
        return False


def default_fallback(chat_id, intent, speech):
    '''
        Response for all inputs (manual entry or button clicks) which are irrelevant to current context
    '''
    global CONTEXTS

    code_correct_flag, location_input_flag, last_input_media_flag = False, False, False
    if 'code_correct' in CONTEXTS:
        code_correct_flag = True
    if 'location_input' in CONTEXTS:
        location_input_flag = True
    if 'last_input_media' in CONTEXTS:
        last_input_media_flag = True
    CONTEXTS.clear()
    if code_correct_flag:
        CONTEXTS.append('code_correct')
    if location_input_flag:
        CONTEXTS.append('location_input')
    if last_input_media_flag:
        CONTEXTS.append('last_input_media')

    if intent == 'add_location':
        if 'code_correct' not in CONTEXTS:
            if 'enters_code' not in CONTEXTS:
                CONTEXTS.append('enters_code')
            # message60 = 'To proceed please <b>enter the secret code</b> from the toy'
            bot.send_message(chat_id,
                             L10N['message60'][USER_LANGUAGE],
                             parse_mode='html')
            secret_code_img = open(SERVICE_IMG_DIR + 'how_secret_code_looks_like.jpg', 'rb')
            bot.send_photo(chat_id, secret_code_img, reply_markup=cancel_help_contacts_menu_kb(USER_LANGUAGE))
        else:
            bot.send_message(chat_id, speech)
            time.sleep(SHORT_TIMEOUT)
            # message8 = 'What would you like to do next?'
            bot.send_message(chat_id, L10N['message8'][USER_LANGUAGE], reply_markup=intro_menu_kb(USER_LANGUAGE))
    else:
        bot.send_message(chat_id, speech)
        time.sleep(SHORT_TIMEOUT)
        # message8 = 'What would you like to do next?'
        bot.send_message(chat_id, L10N['message8'][USER_LANGUAGE], reply_markup=intro_menu_kb(USER_LANGUAGE))


def travelers_story_intro(chat_id):
    '''
        Traveler presents him/herself, his/her goal and asks if user would like to know more about traveler's journey
    '''
    # Traveler's photo
    traveler_photo = open(SERVICE_IMG_DIR + OURTRAVELLER + '.jpg', 'rb')
    # message57 = 'My name is'
    # message58 = 'I\'m a traveler.\nMy dream is to see the world'
    bot.send_photo(chat_id, traveler_photo,
                   caption='{} <strong>{}</strong>. {}'.format(L10N['message57'][USER_LANGUAGE],
                       OURTRAVELLER, L10N['message58'][USER_LANGUAGE]), parse_mode='html', reply_markup=change_language_button_menu_kb(USER_LANGUAGE))
    time.sleep(SHORT_TIMEOUT)
    # message59 = 'Do you want to know more about my journey?'
    bot.send_message(chat_id, L10N['message59'][USER_LANGUAGE],
                     reply_markup=yes_no_gotteddy_menu_kb(USER_LANGUAGE))


def journey_intro(chat_id, traveller):
    '''
        Displays short general 'intro' information about traveller's origin (for eg., 'I came from Cherkasy city,
        Ukraine, from a family with 3 nice small kids'), generates and presents an image from the map with all
        visited locations with a link to web-map and then user has a choice to click 'Next', 'Help' or just to
        talk about something
    '''
    time.sleep(SHORT_TIMEOUT)
    # message61 = 'Ok, here is my story'
    bot.send_message(chat_id, L10N['message61'][USER_LANGUAGE])
    time.sleep(MEDIUM_TIMEOUT)
    if save_static_map(traveller):
        # message62 = 'I came from <a href="'
        # message63 = '">Cherkasy</a> city, Ukraine, from a family with 3 nice small kids'
        bot.send_message(chat_id,
                         '{}{}{}'.format(L10N['message62'][USER_LANGUAGE],
                             'https://www.google.com/maps/place/Черкассы,+Черкасская+область,+18000/@50.5012899,25.9683426,6z', L10N['message63'][USER_LANGUAGE]),
                         parse_mode='html', disable_web_page_preview=True)
        biography_photo = open(SERVICE_IMG_DIR + 'biography.jpg', 'rb')
        bot.send_photo(chat_id, biography_photo)
        time.sleep(LONG_TIMEOUT)
        # message64 = 'So far the map of my journey looks as follows:'
        bot.send_message(chat_id,
                         L10N['message64'][USER_LANGUAGE],
                         parse_mode='html')
        bot.send_chat_action(chat_id, action='upload_photo')
        static_summary_map = open(PHOTO_DIR + OURTRAVELLER + '_summary_map.png', 'rb')
        # message65 = 'Open map in browser'
        bot.send_photo(chat_id, static_summary_map,
                             caption='<a href="{}">{}</a>'.format(
                                 'https://fellowtraveler.club/#journey_map', L10N['message65'][USER_LANGUAGE]), parse_mode='html',
                             reply_markup=next_or_help_menu_kb(USER_LANGUAGE))
    else:
        # message62 = 'I came from <a href="'
        # message63 = '">Cherkasy</a> city, Ukraine, from a family with 3 nice small kids'
        bot.send_message(chat_id,
                         '{}{}{}'.format(L10N['message62'][USER_LANGUAGE],
                             'https://www.google.com/maps/place/Черкассы,+Черкасская+область,+18000/@50.5012899,25.9683426,6z', L10N['message63'][USER_LANGUAGE]),
                         parse_mode='html', disable_web_page_preview=True, reply_markup=next_or_help_menu_kb(USER_LANGUAGE))
        biography_photo = open(SERVICE_IMG_DIR + 'biography.jpg', 'rb')
        bot.send_photo(chat_id, biography_photo)


def journey_begins(chat_id, traveller):
    '''
        Block 2.
        Retrieves journey summary for a given traveller from DB and presents it (depending on quantity of places
        visited, the only one can be also shown or user may be asked if he want's to see the places)
    '''
    speech = ''
    total_locations = 0

    travelled_so_far = ft_functions.get_journey_summary(traveller)
    if not travelled_so_far:
        speech = ''
    else:
        total_countries = travelled_so_far['total_countries']
        total_locations = travelled_so_far['total_locations']
        total_distance = travelled_so_far['total_distance']
        journey_duration = travelled_so_far['journey_duration']
        distance_from_home = travelled_so_far['distance_from_home']
        countries_visited_codes = travelled_so_far['countries_visited']
        countries_visited = ft_functions.translate_countries(countries_visited_codes, USER_LANGUAGE)
        countries_list = (', ').join(countries_visited)

        if total_countries == 1:
            # message95 = 'country'
            countries_form = L10N['message95'][USER_LANGUAGE]
        else:
            # message96 = 'countries'
            countries_form = L10N['message96'][USER_LANGUAGE]

        if journey_duration == 1:
            # message97 = 'day'
            day_or_days = L10N['message97'][USER_LANGUAGE]
        else:
            # message98 = 'days'
            day_or_days = L10N['message98'][USER_LANGUAGE]
            # message89 = 'So far I\'ve checked in'
            # message90 = 'places located in'
            # message91 = 'and have been traveling for'
            # message92 = 'I covered about'
            # message93 = 'km it total and currently I\'m nearly'km from home
            # message94 = 'km from home'
            speech = '{} <b>{}</b> {} <b>{}</b> {} ({}) {} <b>{}</b> {}.\n\n' \
                          '{} <b>{}</b> {} <b>{}</b> {}'.format(
                L10N['message89'][USER_LANGUAGE],
            total_locations, L10N['message90'][USER_LANGUAGE], total_countries, countries_form, countries_list, L10N['message91'][USER_LANGUAGE], journey_duration, day_or_days,
                L10N['message92'][USER_LANGUAGE], total_distance, L10N['message93'][USER_LANGUAGE], distance_from_home, L10N['message94'][USER_LANGUAGE])

    bot.send_message(chat_id, speech, parse_mode='html')
    return total_locations


def the_1st_place(chat_id, traveller, if_to_continue):
    '''
        Block 3 and also inside block 2
        Shows the place our traveller came from. Is used either directly after journey summary (if only 1 or 2 places
        were visited so far) or as the first place in cycle showing all places visited
    '''
    print()
    #print('the_1st_place - if_to_continue: {}'.format(if_to_continue))
    client = MongoClient()
    db = client.TeddyGo

    # Message: I started my journey in ... on ...
    if db[traveller].find().count() != 0:
        the_1st_location = db[traveller].find()[0]
        formatted_address = the_1st_location['formatted_address']
        lat = the_1st_location['latitude']
        long = the_1st_location['longitude']
        start_date = '{}'.format(the_1st_location['_id'].generation_time.date())
        time_passed = ft_functions.time_passed(traveller)
        if time_passed == 0:
            # message73 = 'today'
            day_or_days = L10N['message73'][USER_LANGUAGE]
        elif time_passed == 1:
            # message74 = '1 day ago'
            day_or_days = L10N['message74'][USER_LANGUAGE]
        else:
            # message75 = 'days ago'
            day_or_days = '{} {}'.format(time_passed, L10N['message75'][USER_LANGUAGE])
        # message66 = '<strong>Place #1</strong>\nI started my journey on'
        # message67 = 'from'
        message1 = '{} {} ({}) {} \n<i>{}</i>'.format(L10N['message66'][USER_LANGUAGE], start_date, day_or_days, L10N['message67'][USER_LANGUAGE], formatted_address)
        bot.send_message(chat_id, message1, parse_mode='html')
        #print('starting location lat/long: {}, {}'.format(lat, long))
        bot.send_location(chat_id, latitude=lat, longitude=long)
        photos = the_1st_location['photos']
        if len(photos) > 0:
            for photo in photos:
                #print(photo)
                every_photo = open(PHOTO_DIR + photo, 'rb')
                bot.send_photo(chat_id, every_photo)
        author = the_1st_location['author']
        comment = the_1st_location['comment']
        # message68 = 'That was the 1st place'
        message2 = L10N['message68'][USER_LANGUAGE]
        if comment != '':
            if author == 'Anonymous':
                # message69 = '(who decided to remain anonymous)'
                author = L10N['message69'][USER_LANGUAGE]
            else:
                author = '<b>{}</b>'.format(author)
            # message70 = 'My new friend'
            # message71 = 'wrote:'
            message2 = '{} {} {}\n<i>{}</i>'.format(L10N['message70'][USER_LANGUAGE], author, L10N['message71'][USER_LANGUAGE], comment)
        else:
            if author != 'Anonymous':
                # message72 = 'I got acquainted with a new friend - '
                message2 = '{} <b>{}</b> :)'.format(L10N['message72'][USER_LANGUAGE], author)
        if if_to_continue:
            bot.send_message(chat_id, message2, parse_mode='html', reply_markup=next_or_help_menu_kb(USER_LANGUAGE))
            #print('Here')
        else:
            bot.send_message(chat_id, message2, parse_mode='html')
            #print('There')
    else:
        pass


def every_place(chat_id, traveller, location_to_show, if_to_continue):
    '''
        Block 4
        Shows the 2nd and further visited places
    '''
    client = MongoClient()
    db = client.TeddyGo

    # Message: I started my journey in ... on ...
    location = db[traveller].find()[location_to_show]

    formatted_address = location['formatted_address']
    lat = location['latitude']
    long = location['longitude']
    location_date = '{}'.format(location['_id'].generation_time.date())
    location_date_service = location['_id'].generation_time
    time_passed = time_from_location(location_date_service)
    if time_passed == 0:
        # message73 = 'today'
        day_or_days = L10N['message73'][USER_LANGUAGE]
    elif time_passed == 1:
        # message74 = '1 day ago'
        day_or_days = L10N['message74'][USER_LANGUAGE]
    else:
        # message75 = 'days ago'
        day_or_days = '{} {}'.format(time_passed, L10N['message75'][USER_LANGUAGE])
    # message76 = 'Place #'
    # message77 = '\nOn'
    # message78 = 'I was in'
    message1 = '<strong>{}{}</strong>{} {} ({}) {} \n<i>{}</i>'.format(L10N['message76'][USER_LANGUAGE], location_to_show + 1, L10N['message77'][USER_LANGUAGE],
                                                                                             location_date, day_or_days, L10N['message78'][USER_LANGUAGE],
                                                                                             formatted_address)
    bot.send_message(chat_id, message1, parse_mode='html')
    bot.send_location(chat_id, latitude=lat, longitude=long)
    photos = location['photos']
    if len(photos) > 0:
        for photo in photos:
            #print(photo)
            every_photo = open(PHOTO_DIR + photo, 'rb')
            bot.send_photo(chat_id, every_photo)
    author = location['author']
    comment = location['comment']
    # message79 = 'That was the place #'
    message2 = '{}{}'.format(L10N['message79'][USER_LANGUAGE], location_to_show + 1)
    if comment != '':
        if author == 'Anonymous':
            # message69 = '(who decided to remain anonymous)'
            author = L10N['message69'][USER_LANGUAGE]
        else:
            author = '<b>{}</b>'.format(author)

        # message70 = 'My new friend'
        # message71 = 'wrote:'
        message2 = '{} {} {}\n<i>{}</i>'.format(L10N['message70'][USER_LANGUAGE], author, L10N['message71'][USER_LANGUAGE], comment)
    else:
        if author != 'Anonymous':
            # message72 = 'I got acquainted with a new friend - '
            message2 = '{}<b>{}</b> :)'.format(L10N['message72'][USER_LANGUAGE], author)
    if if_to_continue:
        bot.send_message(chat_id, message2, parse_mode='html', reply_markup=next_or_help_menu_kb(USER_LANGUAGE))
    else:
        bot.send_message(chat_id, message2, parse_mode='html')


def get_help(chat_id):
    '''
        Displays FAQ/help
    '''
    global CONTEXTS

    CONTEXTS.clear()
    # message80 = 'Here\'s our FAQ'
    bot.send_message(chat_id, L10N['message80'][USER_LANGUAGE])
    # message8 = 'What would you like to do next?'
    bot.send_message(chat_id, L10N['message8'][USER_LANGUAGE],
                     reply_markup=intro_menu_kb(USER_LANGUAGE))


def secret_code_validation(secret_code_entered):
    '''
        Validates the secret code entered by user against the one in DB
        If code valid - updates contexts (remove 'enters_code', append 'code_correct')
        If code invalid - suggests to enter it again + inline button 'Cancel' (to remove context 'enters_code')
    '''
    client = MongoClient()
    db = client.TeddyGo
    collection_travellers = db.travellers
    teddys_sc_should_be = collection_travellers.find_one({"name": OURTRAVELLER})['secret_code']
    if not sha256_crypt.verify(secret_code_entered, teddys_sc_should_be):
        return False
    else:
        return True


def gmaps_geocoder(lat, lng):
    '''
    Google Maps - reverse geocoding (https://developers.google.com/maps/documentation/geocoding/start#reverse)
    Getting geodata (namely 'formatted_address', 'locality', 'administrative_area_level_1', 'country' and 'place_id')
    for coordinates received after location sharing in Telegram
    '''
    global NEWLOCATION

    URL = 'https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}'.format(lat, lng, GOOGLE_MAPS_API_KEY)
    try:
        r = requests.get(URL).json().get('results')

        if r[0]:
            formatted_address = r[0].get('formatted_address')
            address_components = r[0].get('address_components')
            locality, administrative_area_level_1, country, place_id = None, None, None, None
            for address_component in address_components:
                types = address_component.get('types')
                short_name = address_component.get('short_name')
                # print("type: {}, short name: {}".format(types, short_name))
                if 'locality' in types:
                    locality = short_name
                elif 'administrative_area_level_1' in types:
                    administrative_area_level_1 = short_name
                elif 'country' in types:
                    country = short_name
            place_id = r[0].get('place_id')

            NEWLOCATION['formatted_address'] = formatted_address
            NEWLOCATION['locality'] = locality
            NEWLOCATION['administrative_area_level_1'] = administrative_area_level_1
            NEWLOCATION['country'] = country
            NEWLOCATION['place_id'] = place_id

        return True
    except Exception as e:
        print('gmaps_geocoder() exception: {}'.format(e))
        #send_email('Logger', 'gmaps_geocoder() exception: {}'.format(e))
        return False


def submit_new_location(traveller):
    '''
        Saves new location (NEWLOCATION) to DB
        Updates journey summary
    '''
    global NEWLOCATION
    try:
        # Logging
        print('')
        print('Saving location to DB...')
        #print('NEWLOCATION: {}'.format(NEWLOCATION))

        client = MongoClient()
        db = client.TeddyGo
        collection_teddy = db[traveller]
        NEWLOCATION.pop('_id', None)
        collection_teddy.insert_one(NEWLOCATION)

        # Update journey summary
        ft_functions.summarize_journey(OURTRAVELLER)

        print('Done')
        return True
    except Exception as e:
        print('submit_new_location() exception: {}'.format(e))
        #send_email('Logger', 'gmaps_geocoder() exception: {}'.format(e))
        return False


def time_from_location(from_date):
    '''
        Function calculates time elapsed from the date when traveler was in specific location (from_date) to now
    '''
    current_datetime = datetime.now(timezone.utc)
    difference = (current_datetime - from_date).days
    return difference


def new_location_summary(chat_id, from_user):
    '''
        Functions sums up data on new location (held in NEWLOCATION variable) before saving the new location to DB
    '''
    try:
        location_date = datetime.now().strftime('%Y-%m-%d')
        message1 = 'On {} I ({}) was in \n<i>{}</i>'.format(location_date, OURTRAVELLER, NEWLOCATION['formatted_address'])
        bot.send_message(chat_id, message1, parse_mode='html')
        bot.send_location(chat_id, NEWLOCATION['latitude'], NEWLOCATION['longitude'])
        photos = NEWLOCATION['photos']
        if len(photos) > 0:
            for photo in photos:
                location_photo = open(PHOTO_DIR + photo, 'rb')
                bot.send_photo(chat_id, location_photo)
        author = '<b>{}</b>'.format(from_user.first_name)
        comment = NEWLOCATION['comment']
        if comment != '':
            # message70 = 'My new friend'
            # message71 = 'wrote:'
            message2 = '{} {} {}\n<i>{}</i>'.format(L10N['message70'][USER_LANGUAGE], author,
                                                    L10N['message71'][USER_LANGUAGE], comment)
        else:
            # message72 = 'I got acquainted with a new friend - '
            message2 = '{}<b>{}</b> :)'.format(L10N['message72'][USER_LANGUAGE], author)
        bot.send_message(chat_id, message2, parse_mode='html')
        return True
    except Exception as e:
        print('new_location_summary() exception: {}'.format(e))
        return False


def send_email(from_user_id, users_input):
    with app.app_context():
        try:
            msg = Message("Fellowtraveler.club - message from Telegram user #{}".format(from_user_id),
                          sender="mailvulgaris@gmail.com", recipients=[SUPPORT_EMAIL])
            msg.html = "Telegram user ID<b>{}</b> wrote:<br><i>{}</i>".format(from_user_id, users_input)
            mail.send(msg)
            return True
        except Exception as e:
            print('send_email() exception: {}'.format(e))
            return False

def save_static_map(traveller):
    '''
    https://developers.google.com/maps/documentation/static-maps/intro
    Requests a list of places visited by traveller from DB and draws a static (png) map
    '''
    try:
        markers = ft_functions.get_location_history(traveller, PHOTO_DIR)['mymarkers'][::-1]
        latlongparams = ''
        for index, marker in enumerate(markers):
            latlongparams += '&markers=color:green%7Clabel:{}%7C{},{}'.format(index + 1, marker['lat'], marker['lng'])
        query = 'https://maps.googleapis.com/maps/api/staticmap?size=700x400&maptype=roadmap{}&key={}'.format(latlongparams, GOOGLE_MAPS_API_KEY)

        path = PHOTO_DIR + traveller + '_summary_map.png'

        r = requests.get(query, timeout=0.5)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
        return True
    except Exception as e:
        print('save_static_map() exception: {}'.format(e))
        #send_email('Logger', 'save_static_map() exception: {}'.format(e))
        return False

def respond_to_several_photos_only_once():
    '''
        User may upload several photos for a location and each one triggers the corresponding handler
        We needn't respond to every photo so we'll respond only to the 1st one (though our response
        will be displayed after all photos)
    '''
    global CONTEXTS
    if 'last_input_media' in CONTEXTS:
        CONTEXTS.remove('last_input_media')
        if 'media_input' in CONTEXTS:
            CONTEXTS.remove('media_input')


def get_language(message):
    '''
        Retrieves from message and returns user's language code
    '''
    if message.from_user.language_code != None:
        lang = message.from_user.language_code.split('-')[0]
        if lang not in LANGUAGES.keys():
            language = 'en'
        else:
            language = lang
    return language
####################################### Functions END ####################################

####################################### Markup START #####################################
def intro_menu_kb(USER_LANGUAGE):
    intro_menu = types.InlineKeyboardMarkup()
    # message44 = "My story"
    # message84 = "Tell your story"
    intro_menu_mystory = types.InlineKeyboardButton(L10N['message44'][USER_LANGUAGE], callback_data=L10N['message84'][USER_LANGUAGE])
    # message45 = "FAQ"
    intro_menu_help = types.InlineKeyboardButton(L10N['message45'][USER_LANGUAGE], callback_data=L10N['message45'][USER_LANGUAGE])
    # message46 = "You got"
    # message85 = "You got fellowtraveler"
    intro_menu_gotteddy = types.InlineKeyboardButton("{} {}?".format(L10N['message46'][USER_LANGUAGE], OURTRAVELLER), callback_data=L10N['message85'][USER_LANGUAGE])
    intro_menu.row(intro_menu_mystory, intro_menu_help, intro_menu_gotteddy)
    return intro_menu


def yes_no_gotteddy_menu_kb(USER_LANGUAGE):
    yes_no_gotteddy_menu = types.InlineKeyboardMarkup()
    # message47 = "Yes"
    yes_no_gotteddy_menu_yes = types.InlineKeyboardButton(L10N['message47'][USER_LANGUAGE], callback_data=L10N['message47'][USER_LANGUAGE])
    # message48 = "No, thanks"
    yes_no_gotteddy_menu_no = types.InlineKeyboardButton(L10N['message48'][USER_LANGUAGE], callback_data=L10N['message48'][USER_LANGUAGE])
    # message46 = "You got"
    yes_no_gotteddy_menu_gotteddy = types.InlineKeyboardButton("{} {}?".format(L10N['message46'][USER_LANGUAGE], OURTRAVELLER), callback_data=L10N['message85'][USER_LANGUAGE])
    yes_no_gotteddy_menu.row(yes_no_gotteddy_menu_yes, yes_no_gotteddy_menu_no, yes_no_gotteddy_menu_gotteddy)
    return yes_no_gotteddy_menu


def yes_no_help_menu_kb(USER_LANGUAGE):
    yes_no_help_menu = types.InlineKeyboardMarkup()
    # message47 = "Yes"
    yes_no_help_menu_yes = types.InlineKeyboardButton(L10N['message47'][USER_LANGUAGE], callback_data=L10N['message47'][USER_LANGUAGE])
    # message48 = "No, thanks"
    yes_no_help_menu_no = types.InlineKeyboardButton(L10N['message48'][USER_LANGUAGE], callback_data=L10N['message48'][USER_LANGUAGE])
    # message45 = "FAQ"
    yes_no_help_menu_help = types.InlineKeyboardButton(L10N['message45'][USER_LANGUAGE], callback_data=L10N['message45'][USER_LANGUAGE])
    yes_no_help_menu.row(yes_no_help_menu_yes, yes_no_help_menu_no, yes_no_help_menu_help)
    return yes_no_help_menu


def next_or_help_menu_kb(USER_LANGUAGE):
    next_or_help_menu = types.InlineKeyboardMarkup()
    # message49 = "Next"
    next_or_help_menu_next = types.InlineKeyboardButton(L10N['message49'][USER_LANGUAGE], callback_data=L10N['message49'][USER_LANGUAGE])
    # message45 = "FAQ"
    next_or_help_menu_help = types.InlineKeyboardButton(L10N['message45'][USER_LANGUAGE], callback_data=L10N['message45'][USER_LANGUAGE])
    next_or_help_menu.row(next_or_help_menu_next, next_or_help_menu_help)
    return next_or_help_menu


def cancel_help_contacts_menu_kb(USER_LANGUAGE):
    cancel_help_contacts_menu = types.InlineKeyboardMarkup()
    # message50 = "Cancel"
    cancel_help_contacts_menu_cancel =  types.InlineKeyboardButton(L10N['message50'][USER_LANGUAGE], callback_data=L10N['message50'][USER_LANGUAGE])
    # message45 = "FAQ"
    cancel_help_contacts_menu_help = types.InlineKeyboardButton(L10N['message45'][USER_LANGUAGE], callback_data=L10N['message45'][USER_LANGUAGE])
    # message51 = "Contact support"
    cancel_help_contacts_menu_contacts = types.InlineKeyboardButton(L10N['message51'][USER_LANGUAGE], callback_data=L10N['message51'][USER_LANGUAGE])
    cancel_help_contacts_menu.row(cancel_help_contacts_menu_cancel, cancel_help_contacts_menu_help, cancel_help_contacts_menu_contacts)
    return cancel_help_contacts_menu


def you_got_teddy_menu_kb(USER_LANGUAGE):
    you_got_teddy_menu = types.InlineKeyboardMarkup()
    # message52 = "Instructions"
    you_got_teddy_menu_instructions = types.InlineKeyboardButton(L10N['message52'][USER_LANGUAGE], callback_data=L10N['message52'][USER_LANGUAGE])
    # message53 = "Add location"
    you_got_teddy_menu_add_place = types.InlineKeyboardButton(L10N['message53'][USER_LANGUAGE], callback_data=L10N['message53'][USER_LANGUAGE])
    # message51 = "Contact support"
    you_got_teddy_menu_contacts = types.InlineKeyboardButton(L10N['message51'][USER_LANGUAGE], callback_data=L10N['message51'][USER_LANGUAGE])
    you_got_teddy_menu.row(you_got_teddy_menu_instructions, you_got_teddy_menu_add_place, you_got_teddy_menu_contacts)
    return you_got_teddy_menu


def share_location_kb(USER_LANGUAGE):
    share_location = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # message53 = "Share your location"
    share_location_button = types.KeyboardButton(L10N['message54'][USER_LANGUAGE], request_location=True)
    share_location.add(share_location_button)
    return share_location


def next_reset_instructions_menu_kb(USER_LANGUAGE):
    next_reset_instructions_menu = types.InlineKeyboardMarkup()
    # message49 = "Next"
    next_reset_instructions_menu_next = types.InlineKeyboardButton(L10N['message49'][USER_LANGUAGE], callback_data=L10N['message49'][USER_LANGUAGE])
    # message55 = "Reset"
    next_reset_instructions_menu_reset = types.InlineKeyboardButton(L10N['message55'][USER_LANGUAGE], callback_data=L10N['message55'][USER_LANGUAGE])
    # message52 = "Instructions"
    next_reset_instructions_menu_instructions = types.InlineKeyboardButton(L10N['message52'][USER_LANGUAGE], callback_data=L10N['message52'][USER_LANGUAGE])
    next_reset_instructions_menu.row(next_reset_instructions_menu_next, next_reset_instructions_menu_reset, next_reset_instructions_menu_instructions)
    return next_reset_instructions_menu


def cancel_or_instructions_menu_kb(USER_LANGUAGE):
    cancel_or_instructions_menu = types.InlineKeyboardMarkup()
    # message50 = "Cancel"
    cancel_or_instructions_menu_cancel = types.InlineKeyboardButton(L10N['message50'][USER_LANGUAGE], callback_data=L10N['message50'][USER_LANGUAGE])
    # message52 = "Instructions"
    cancel_or_instructions_menu_instructions = types.InlineKeyboardButton(L10N['message52'][USER_LANGUAGE], callback_data=L10N['message52'][USER_LANGUAGE])
    cancel_or_instructions_menu.row(cancel_or_instructions_menu_cancel, cancel_or_instructions_menu_instructions)
    return cancel_or_instructions_menu


def submit_reset_menu_kb(USER_LANGUAGE):
    submit_reset_menu = types.InlineKeyboardMarkup()
    # message56 = "Submit"
    submit_reset_menu_submit = types.InlineKeyboardButton(L10N['message56'][USER_LANGUAGE], callback_data=L10N['message56'][USER_LANGUAGE])
    # message55 = "Reset"
    submit_reset_menu_reset = types.InlineKeyboardButton(L10N['message55'][USER_LANGUAGE], callback_data=L10N['message55'][USER_LANGUAGE])
    submit_reset_menu.row(submit_reset_menu_submit, submit_reset_menu_reset)
    return submit_reset_menu

def change_language_menu_kb(USER_LANGUAGE):
    change_language_menu = types.InlineKeyboardMarkup()
    # message86 = 'Change language to English'
    change_language_menu_en = types.InlineKeyboardButton('English', callback_data=L10N['message86'][USER_LANGUAGE])
    # message87 = 'Change language to Russian'
    change_language_menu_ru = types.InlineKeyboardButton('Русский', callback_data=L10N['message87'][USER_LANGUAGE])
    # message88 = 'Change language to Ukrainian'
    change_language_menu_uk = types.InlineKeyboardButton('Українська', callback_data=L10N['message88'][USER_LANGUAGE])
    change_language_menu.row(change_language_menu_en, change_language_menu_ru, change_language_menu_uk)
    return change_language_menu


def change_language_button_menu_kb(USER_LANGUAGE):
    change_language_button_menu = types.InlineKeyboardMarkup()
    # message83 = "Change language"
    change_language_button_menu_change_it = types.InlineKeyboardButton(L10N['message83'][USER_LANGUAGE], callback_data=L10N['message83'][USER_LANGUAGE])
    change_language_button_menu.row(change_language_button_menu_change_it)
    return change_language_button_menu

######################################### Markup END #####################################

while True:
    try:
        bot.polling(none_stop=True, timeout=1)
    except Exception as e:
        print('bot.polling() exception: {}'.format(e))
        send_email('Logger', 'bot.polling() exception: {}'.format(e))
        time.sleep(15)
