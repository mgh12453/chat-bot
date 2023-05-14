from tinydb import Query
from models import get_or_create_connection, get_or_create_user, remove_connection, User, Admin, Connection, WaitList
import logging


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


async def send_user_message(context, users, text=None, message=None):
    for user in users:
        if message:
            await context.bot.send_message(chat_id=user.get('id'), text="A message from admin:")
            await message.copy(chat_id=user.get('id'))
        else:
            await context.bot.send_message(chat_id=user.get('id'), text=text)


def admin_required(func):
    async def wrapper(*args, **kwargs):
        update = args[0]
        username = update.effective_user.username
        if Admin.contains((Query().id == update.effective_user.id) | (Query().username == username)):
            return await func(*args, **kwargs)
        else:
            await update.message.reply_text("You don't have right access for it.")

    return wrapper


def login_required(func):
    async def wrapper(*args, **kwargs):
        update = args[0]
        chat_id = update.message.chat.id
        if User.contains(Query().id == chat_id):
            return await func(*args, **kwargs)
        else:
            await update.message.reply_text("You didn't signed in correctly. Please restart the bot.")

    return wrapper


def role_required(func):
    async def wrapper(*args, **kwargs):
        update = args[0]
        chat_id = update.message.chat.id
        if User.get(Query().id == chat_id).get('role') is not None:
            return await func(*args, **kwargs)
        else:
            await update.message.reply_text("Please select your role first.\n\n - put /teacher if you are a " +
                                            "teacher\n - put /student if you are a student")

    return wrapper


def connection_required(func):
    async def wrapper(*args, **kwargs):
        update = args[0]
        context = args[1]
        chat_id = update.message.chat.id
        if WaitList.contains(Query().chat_id == update.message.chat.id):
            try:
                users = []
                qs = WaitList.get(Query().chat_id == update.message.chat.id)
                for username in qs.get('contacts'):
                    users.append(User.get(Query().username == username))
                await send_user_message(context, users, message=update.message)
                await send_user_message(context, [User.get(Query().id == update.message.chat.id)],
                                        text="Message sent successfully.")
                WaitList.remove(doc_ids=[qs.doc_id])
            except Exception as e:
                await update.message.reply_text("Sorry, somthing went wrong\nPlease contact admin or restart the bot.")
        elif Connection.contains((Query().teacher == chat_id) | (Query().student == chat_id)):
            return await func(*args, **kwargs)
        else:
            await update.message.reply_text("Nobody hears you...\n\nYou dont have any active conversation.\nPut /connect for start one.")

    return wrapper
