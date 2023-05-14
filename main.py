import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, ApplicationBuilder, filters, CallbackContext
from telegram import Message, Update, Bot
from tinydb import Query
from models import get_or_create_connection, get_or_create_user, remove_connection, User, Connection, Admin, WaitList
from decorators import login_required, admin_required, role_required, connection_required

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


async def send_admin_message(context: CallbackContext, admins: list = [], text: str = '', message: Message = None, caption: str = ''):
    admins = Admin.all() if admins == [] else admins
    if message:
        for admin in admins:
            if admin.get('chat_id', 0) == 0:
                continue
            if len(caption):
                await message.copy(chat_id=admin.get('chat_id'), caption=caption, parse_mode='markdown')
            else:
                msg = await message.copy(chat_id=admin.get('chat_id'))
                await context.bot.send_message(chat_id=admin.get('chat_id'), text=text, reply_to_message_id=msg.message_id, parse_mode='markdown')
    else:
        for admin in admins:
            if admin.get('chat_id', 0) == 0:
                continue
            await context.bot.send_message(chat_id=admin.get('chat_id'), text=text, parse_mode='markdown')


async def send_user_message(context, users, text, message: Message = None):
    for user in users:
        if message:
            await message.copy(chat_id=user.get('id'))
        else:
            await context.bot.send_message(chat_id=user.get('id'), text=text)


async def start(update, context):
    """Send a message when the command /start is issued."""
    logger.warning(f'User {update.effective_user.username}-{update.effective_user.id} in chat {update.message.chat.id} has started the bot.')
    chat_id = update.message.chat.id
    username = update.effective_user.username
    get_or_create_user(id=chat_id, username=username)
    if Connection.contains((Query().teacher == chat_id) | (Query().student == chat_id)):
        await update.message.reply_text("Sorry, You can not restart the bot while you are in a connection.\n\nPlease " +
                                        "keep giong or endup the connection.")
    else:
        await update.message.reply_text("Hi.\n\nPlease select your Role first:\n - put /teacher if you are a " +
                                        "teacher\n - put /student if you are a student\n\nYou can see /help for more " +
                                        "information.\n")

    if Admin.contains((Query().id == update.effective_user.id) | (Query().username == username)):
        logger.warning(f'Admin refreshing data {update.effective_user.username}-{update.effective_user.id}.')
        Admin.update({'chat_id': update.message.chat.id}, (Query().id == update.effective_user.id) | (Query().username == username))


async def help(update, context):
    """Send a message when the command /help is issued."""
    await update.message.reply_text('* This bot connects you to an expert teacher in your wanted subjects for helping' +
                                    ' in exams or your questions\n\n* Also if you are an expert we connect you to a ' +
                                    'needed student.\n\nPleas put /start for beginning.\n\nPlease put /connect for ' +
                                    'connecting to a Teacher or Student.')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@login_required
async def set_role_teacher(update, context):
    try:
        User.update({'role': 'teacher'}, Query().id == update.message.chat.id)
        await update.message.reply_text('You are a Teacher now.\nIf you wanna start a conversation put /connect')
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@login_required
async def set_role_student(update, context):
    try:
        User.update({'role': 'student'}, Query().id == update.message.chat.id)
        await update.message.reply_text('You are a Student now.\nIf you wanna start a conversation put /connect')
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@login_required
async def connect(update, context):
    user = User.get(Query().id == update.message.chat.id)
    username = update.effective_user.username
    fullname = update.effective_user.full_name
    try:
        await send_admin_message(context, text=f"User {fullname} - @{username} has been sent request for connecting " +
                                               f"as a {user.get('role')}")
        await update.message.reply_text("Your request has been sent to our admin successfully.\n\nPlease wait for " +
                                        "confirmation.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@admin_required
@login_required
async def connect_confirmation(update, context):
    try:
        input_mex = update.message.text
        p1, p2 = input_mex.split(' ')[1][1:], input_mex.split(' ')[2][1:]
        p1, p2 = User.get(Query().username == p1), User.get(Query().username == p2)
        if p1.get('role') == 'student' and p2.get('role') == 'teacher':
            get_or_create_connection(student=int(p1.get('id')), teacher=int(p2.get('id')))
        elif p2.get('role') == 'student' and p1.get('role') == 'teacher':
            get_or_create_connection(student=int(p2.get('id')), teacher=int(p1.get('id')))
        else:
            await update.message.reply_text("Failed. this two user have incorrect roles.\n\n - First user is " +
                                      f"{p1.get('role')}\n - Second one is {p2.get('role')}.")
        await send_user_message(context, [p1, p2], "Your connection confirmed.\n\n start talking with your connected user.")
        await send_admin_message(context, text=f"A session between @{p1['username']} and @{p2['username']} started.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@admin_required
@login_required
async def set_admin(update, context):
    try:
        input_mex = update.message.text
        input_args = input_mex.split('/new_admin ')[1]
        Admin.insert({'id': 0, 'username': input_args[1:], 'chat_id': 0})
        await update.message.reply_text(f"Admin {input_args} added successfully.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@admin_required
@login_required
async def remove_admin(update, context):
    try:
        input_mex = update.message.text
        input_args = input_mex.split(' ')[1]
        if not Admin.contains(Query().username == input_args[1:]):
            await update.message.reply_text(f"User {input_args} is not an admin.")
            return
        Admin.remove(Query().username == input_args[1:])
        await update.message.reply_text(f"Admin {input_args} removed successfully.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


@admin_required
@login_required
async def send_message_from_admin(update: Update, context: CallbackContext):
    input_mex = update.message.text
    input_args = [arg[1:] for arg in input_mex.split(' ')[1:]]
    WaitList.insert({'chat_id': update.message.chat.id, 'contacts': input_args})
    await send_user_message(context, [User.get(Query().id == update.message.chat.id)], text="Pleas enter your message:")


@connection_required
async def command_handler(update: Update, context: CallbackContext):
    try:
        chat_id = update.message.chat.id
        user = User.get(Query().id == chat_id)
        con = Connection.get((Query().teacher == chat_id) | (Query().student == chat_id))
        await update.message.copy(chat_id=con.get('teacher' if user['role'] == 'student' else 'student'))
        if update.message.caption:
            caption = f"@{user['username']} : ({user['role']} - session `{con.doc_id}`)\n" + update.message.caption
            await send_admin_message(context, message=update.message, caption=caption)
        elif update.message.text:
            text = f"@{user['username']} : ({user['role']} - session `{con.doc_id}`)\n" + update.message.text
            await send_admin_message(context, text=text)
        else:
            text = f"@{user['username']} : ({user['role']} - session `{con.doc_id}`)\n"
            await send_admin_message(context, message=update.message, text=text)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")


def main():
    logger.warning("start app")
    assert (bot_token := os.environ.get('TOKEN'))
    application = ApplicationBuilder().token(bot_token).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('connect', connect))
    application.add_handler(CommandHandler('confirm', connect_confirmation))
    application.add_handler(CommandHandler('teacher', set_role_teacher))
    application.add_handler(CommandHandler('student', set_role_student))
    application.add_handler(CommandHandler('add_admin', set_admin))
    application.add_handler(CommandHandler('del_admin', remove_admin))
    application.add_handler(CommandHandler('admin_message', send_message_from_admin))

    application.add_handler(MessageHandler(filters.ALL, command_handler))

    application.run_polling()
    logger.info("end app")


if __name__ == '__main__':
    main()
