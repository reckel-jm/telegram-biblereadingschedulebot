import datetime
import logging
import csv
from dataclasses import dataclass
import os
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    filters, 
    ApplicationBuilder, 
    CommandHandler, 
    ConversationHandler, 
    ContextTypes, 
    MessageHandler, 
    PicklePersistence
)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Conversation States
SET_TIME, SET_LANGUAGE = range(2)

@dataclass
class BibleReadingScheduleEntry:
    """Represents a Bible reading schedule entry."""
    date: datetime.date
    ot_reading: str
    nt_reading: str


def get_todays_bible_reading(filename: str = 'schedule.csv') -> BibleReadingScheduleEntry:
    """Reads the Bible reading schedule from a file and returns today's entry.

    Args:
        filename (str, optional): The name of the file containing the schedule. Defaults to 'schedule.csv'.

    Returns:
        BibleReadingScheduleEntry: The Bible reading schedule entry for today.
    """
    # Get today's date
    today = datetime.date.today()
    
    # Read the schedule.csv file
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file, delimiter=',', quotechar='"')

        # Find the entry for today's date
        for row in csv_reader:
            date_str   = row[0]
            ot_reading = row[2]
            nt_reading = row[1]
            
            # This is necessary for the headline which we don't take into account
            try:
                this_date = datetime.datetime.strptime(date_str, "%m-%d-%y").date()
                if this_date == today:
                    return BibleReadingScheduleEntry(this_date, ot_reading, nt_reading)
            except:
                next
    
    # If no entry is found for today, return None
    return None

async def specific_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Activates the Bible study reminder with a specific argument given"""
    time_str = context.args[0].strip()
    time_parts = time_str.split(':')
    t = None
    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        t = datetime.time(hour, minute)
    except ValueError:
        await update.message.reply_text(text='Invalid time format. Please use the format HH:MM.')
        return SET_TIME
    
    context.job_queue.run_daily(remind_bible_study, 
                                t, 
                                days=(0, 1, 2, 3, 4, 5, 6),
                                chat_id=update.message.chat_id, 
                                name=str(update.message.chat_id)
                                )
    await update.message.reply_text(text=f'Activated Bible study reminder daily at {t.strftime("%H:%M")} UTC.')
    

async def create_bible_study_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(text='Hey, it is great that you want to read the Bible daily. I will help you with that.')
    await update.message.reply_text(text='Please enter the time when you want to receive the daily reminder in the format HH:MM. The timezone is UTC.')
    await update.message.reply_text(text="You can cancel this process by typing /cancel")
    return SET_TIME


async def activate_bible_study_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Activates the Bible study reminder.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    
    if update.message.text.strip() == '/cancel':
        return await cancel_reminder_creation(context, update)
    
    logger.info('Activating Bible study reminder for %s.', update.message.from_user.first_name)
    logger.info('The text was: %s', update.message.text)
    
    # Parse the time from the message (e.g., "08:00")
    time_str = update.message.text.strip()
    time_parts = time_str.split(':')
    t = None
    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        t = datetime.time(hour, minute)
    except ValueError:
        await update.message.reply_text(text='Invalid time format. Please use the format HH:MM.')
        return SET_TIME
    
    context.job_queue.run_daily(remind_bible_study, 
                                t, 
                                days=(0, 1, 2, 3, 4, 5, 6),
                                chat_id=update.message.chat_id, 
                                name=str(update.message.chat_id)
                                )
    await update.message.reply_text(text=f'Activated Bible study reminder daily at {t.strftime("%H:%M")} UTC.')    
    return ConversationHandler.END


async def cancel_reminder_creation(context: ContextTypes.DEFAULT_TYPE, update: Update) -> int:
    """Cancels the creation of a reminder.

    Args:
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
        update (Update): The update object from Telegram.

    Returns:
        int: The end of the conversation.
    """
    logger.info('Cancelled Bible study reminder creation.')
    await update.message.reply_text(text='Cancelled Bible study reminder creation.')
    return ConversationHandler.END


async def remind_bible_study(context: ContextTypes.DEFAULT_TYPE, update: Update = None) -> None:
    """Sends a reminder for Bible study.

    Args:
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
        update (Update, optional): The update object from Telegram. Defaults to None.
    """
    if update:
        this_chat_id = update.message.chat_id
    else:
        this_chat_id = context.job.chat_id
    await send_reminder(context, this_chat_id)


async def remind_bible_study_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a one-time reminder for Bible study.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    this_chat_id = update.message.chat_id
    await send_reminder(context, this_chat_id)
    
    
async def send_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str) -> None:
    """Sends a reminder message for Bible study.

    Args:
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
        chat_id (int | str): The chat ID to send the reminder to.
    """
    todays_bible_reading: BibleReadingScheduleEntry = get_todays_bible_reading()
    
    if todays_bible_reading:
        if context.user_data.get('language') == 'de':
            await context.bot.send_message(chat_id, parse_mode='HTML', text=f'''
            <b>Dies ist eine Erinnerung, die Bibel zu lesen.</b>
            
            AT: {todays_bible_reading.ot_reading}
            NT: {todays_bible_reading.nt_reading}
            ''')
        else:
            await context.bot.send_message(chat_id, parse_mode='HTML', text=f'''
            <b>This is a reminder to read the Bible.</b>
            
            OT: {todays_bible_reading.ot_reading}
            NT: {todays_bible_reading.nt_reading}
            ''')
    else:
        if context.user_data.get('language') == 'de':   
            await context.bot.send_message(chat_id, text='''
                Dies ist eine Erinnerung, die Bibel zu lesen.
            ''')
        else:
            await context.bot.send_message(chat_id, text='''
                This is a reminder to read the Bible.
            ''')
    if context.user_data.get('language') == 'de':
        await context.bot.send_poll(chat_id, question='Hast du heute schon die Bibel gelesen?', options=['Ja', 'Nein'], is_anonymous=False)
    else:
        await context.bot.send_poll(chat_id, question='Have you read the Bible today?', options=['Yes', 'No'], is_anonymous=False)


async def respond_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds with the chat ID.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    this_chat_id = update.message.chat_id
    await context.bot.send_message(this_chat_id, text=f'Hello, your Chat-ID is: {str(this_chat_id)}')


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes a reminder job.

    Args:
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
        job (Job): The job to delete.
    """
    # find job by name
    jobs = context.job_queue.get_jobs_by_name(str(update.message.chat_id))
    
    for j in jobs:
        j.schedule_removal()
    
    await context.bot.send_message(update.message.chat_id, text='Bible study reminder deactivated.')


async def send_all_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends all reminders to the user.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    
    jobs = context.job_queue.get_jobs_by_name(str(update.message.chat_id))
    
    if not jobs:
        await update.message.reply_text(text='You have no active reminders. Create one with /createbiblestudyreminder.')
    else:
        message: str = 'Your active reminders are:\n'
        for j in jobs:
            message += f'- Daily at {j.next_t.strftime("%H:%M")}\n'
        message += 'You can delete them with /deletebiblestudyreminder.'
        
        logger.info('Sending message: %s', message)
        await update.message.reply_text(text=message, parse_mode='Markdown')
        
        
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the bot.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    await update.message.reply_text(text='Hello! I am your Bible reading reminder bot. I can remind you daily to read the Bible. Use /createbiblestudyreminder to create a reminder.')


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sets the language for the bot.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    
    if update.message.text == 'English':
        context.user_data['language'] = 'en'
        await update.message.reply_text(text='Language set to English')
        return ConversationHandler.END
    elif update.message.text == 'German':
        context.user_data['language'] = 'de'
        await update.message.reply_text(text='Sprache auf Deutsch gesetzt')
        return ConversationHandler.END
    else:
        # Provide buttons for English and German
        keyboard = [['English', 'German']]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder='Please select your language:' # This is only for Telegram clients that support placeholders in the input field
        )
        
        await update.message.reply_text(text='Please select your language:', reply_markup=reply_markup)
        return SET_LANGUAGE


async def cancel_language_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the language setting.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    await update.message.reply_text(text='Cancelled language setting.')
    return ConversationHandler.END


def main() -> None:
    
    # Get Bot token from env
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError('TELEGRAM_BOT_TOKEN not set in environment variables.')
    
    """The main function to run the bot."""
    persistence = PicklePersistence(filepath='biblereadingbot_data');
    
    application = ApplicationBuilder().token(bot_token).persistence(persistence).build()

    application.bot.set_my_description('This is a bot to remind you to read the Bible daily.')

    application.persistence_enabled = True
    
    set_timer_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('createbiblestudyreminder', create_bible_study_reminder)],
        states={
            SET_TIME: [MessageHandler(None, activate_bible_study_reminder)],
        },
        fallbacks=[CommandHandler('cancel', cancel_reminder_creation)]
    )
    
    set_language_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('setlang', set_language)],
        states={
            SET_LANGUAGE: [MessageHandler(None, set_language)],
        },
        fallbacks=[CommandHandler('cancel', cancel_language_setting)]
    )
    
    application.add_handler(CommandHandler("start", start))   
    application.add_handler(CommandHandler("respondchatid", respond_chat_id))
    application.add_handler(CommandHandler("remindbiblestudy", remind_bible_study_once))
    application.add_handler(CommandHandler("deletebiblestudyreminder", delete_reminder))
    application.add_handler(CommandHandler("sst", specific_set_time)) 
    application.add_handler(set_timer_conversation_handler)
    application.add_handler(CommandHandler("myreminders", send_all_reminders))
    application.add_handler(set_language_conversation_handler)
    
    application.run_polling()


if __name__ == '__main__':
    main()