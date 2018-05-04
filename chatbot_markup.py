from telebot import types

OURTRAVELLER = 'Teddy'

# All possible buttons: Yes, No, Next, FAQ, <Traveler>'s story, You got traveler

intro_menu = types.InlineKeyboardMarkup()
intro_menu_mystory = types.InlineKeyboardButton("{}\'s story".format(OURTRAVELLER), callback_data="Tell your story")
intro_menu_help = types.InlineKeyboardButton("FAQ", callback_data="FAQ")
intro_menu_gotteddy = types.InlineKeyboardButton("You got {}?".format(OURTRAVELLER), callback_data="You got fellowtraveler")
intro_menu.row(intro_menu_mystory, intro_menu_help, intro_menu_gotteddy)

yes_no_gotteddy_menu = types.InlineKeyboardMarkup()
yes_no_gotteddy_menu_yes = types.InlineKeyboardButton("Yes", callback_data="Yes")
yes_no_gotteddy_menu_no = types.InlineKeyboardButton("No, thanks", callback_data="No")
yes_no_gotteddy_menu_gotteddy = types.InlineKeyboardButton("You got {}?".format(OURTRAVELLER), callback_data="You got fellowtraveler")
yes_no_gotteddy_menu.row(yes_no_gotteddy_menu_yes, yes_no_gotteddy_menu_no, yes_no_gotteddy_menu_gotteddy)

yes_no_help_menu = types.InlineKeyboardMarkup()
yes_no_help_menu_yes = types.InlineKeyboardButton("Yes", callback_data="Yes")
yes_no_help_menu_no = types.InlineKeyboardButton("No, thanks", callback_data="No")
yes_no_help_menu_help = types.InlineKeyboardButton("FAQ", callback_data="FAQ")
yes_no_help_menu.row(yes_no_help_menu_yes, yes_no_help_menu_no, yes_no_help_menu_help)

next_or_help_menu = types.InlineKeyboardMarkup()
next_or_help_menu_next = types.InlineKeyboardButton("Next", callback_data="Next")
next_or_help_menu_help = types.InlineKeyboardButton("FAQ", callback_data="FAQ")
next_or_help_menu.row(next_or_help_menu_next, next_or_help_menu_help)

cancel_help_contacts_menu = types.InlineKeyboardMarkup()
cancel_help_contacts_menu_cancel =  types.InlineKeyboardButton("Cancel", callback_data="Cancel")
cancel_help_contacts_menu_help = types.InlineKeyboardButton("FAQ", callback_data="FAQ")
cancel_help_contacts_menu_contacts = types.InlineKeyboardButton("Contact support", callback_data="Contact support")
cancel_help_contacts_menu.row(cancel_help_contacts_menu_cancel, cancel_help_contacts_menu_help, cancel_help_contacts_menu_contacts)

you_got_teddy_menu = types.InlineKeyboardMarkup()
you_got_teddy_menu_instructions = types.InlineKeyboardButton("Instructions", callback_data="Get instructions")
you_got_teddy_menu_add_place = types.InlineKeyboardButton("Add location", callback_data="Add location")
you_got_teddy_menu_contacts = types.InlineKeyboardButton("Contact support", callback_data="Contact support")
you_got_teddy_menu.row(you_got_teddy_menu_instructions, you_got_teddy_menu_add_place, you_got_teddy_menu_contacts)

share_location = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
share_location_button = types.KeyboardButton('Share your location', request_location=True)
share_location.add(share_location_button)

next_reset_instructions_menu = types.InlineKeyboardMarkup()
next_reset_instructions_menu_next = types.InlineKeyboardButton("Next", callback_data="Next")
next_reset_instructions_menu_reset = types.InlineKeyboardButton("Reset", callback_data="Reset")
next_reset_instructions_menu_instructions = types.InlineKeyboardButton("Instructions", callback_data="Get instructions")
next_reset_instructions_menu.row(next_reset_instructions_menu_next, next_reset_instructions_menu_reset, next_reset_instructions_menu_instructions)

cancel_or_instructions_menu = types.InlineKeyboardMarkup()
cancel_or_instructions_menu_cancel = types.InlineKeyboardButton("Cancel", callback_data="Cancel")
cancel_or_instructions_menu_instructions = types.InlineKeyboardButton("Instructions", callback_data="Get instructions")
cancel_or_instructions_menu.row(cancel_or_instructions_menu_cancel, cancel_or_instructions_menu_instructions)

submit_reset_menu = types.InlineKeyboardMarkup()
submit_reset_menu_submit = types.InlineKeyboardButton("Submit", callback_data="Submit")
submit_reset_menu_reset = types.InlineKeyboardButton("Reset", callback_data="Reset")
submit_reset_menu.row(submit_reset_menu_submit, submit_reset_menu_reset)