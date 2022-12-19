import requests
from time import sleep
from dataclasses import dataclass
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, JobQueue

OK = 0
FAIL = 1


class Bot:
    def __init__(self):
        self.token = "5733782224:AAEXJ9cyCJYoH60FXXbovWXWVNb40XFuQtA"
        self.b_logic = LogicProcessor()
        self.interval = 60
        self.b_logic.tanks_count_threshold = 200

    # regular commands block

    # function to handle the /start command
    def start(self, update, context):
        update.message.reply_text('Hey! For help press to /help command')

    # function to handle the /help command
    def help(self, update, context):
        update.message.reply_text('/start')
        update.message.reply_text('/help')
        update.message.reply_text(f'/auto - subscribe to automessaging. 1 check in {self.interval} seconds. Count threshold is {self.b_logic.tanks_count_threshold} tanks')
        update.message.reply_text('/stop - unsubscribe.')
        update.message.reply_text('/all_tanks - show all accessible tanks in auction.')

    # function to handle errors occured in the dispatcher
    # def error(self, update, context):
    #     update.message.reply_text('an error occured')

    # function to handle normal text
    # def text(self, update, context):
    #     text_received = update.message.text
    #     update.message.reply_text(f'did you said "{text_received}" ?')

    # scheduled jobs block
    def callback_task(self, context):
        self.b_logic.update_tanks()
        client_id = context.job.context
        string_added = False
        for message in self.b_logic.get_under_threshold_tanks_info():
            context.bot.send_message(chat_id=client_id, text=message)
            string_added = True
        if string_added:
            context.bot.send_message(chat_id=client_id, text='-'*20)

    def get_all_tanks(self, update, context):
        self.b_logic.update_tanks()
        chat_id = update.message.chat_id
        for message in self.b_logic.get_all_tanks_info():
            update.message.reply_text(message)
        update.message.reply_text('-'*20)
    # main control methods block

    def start_auto_messaging(self, update, context):
        chat_id = update.message.chat_id
        update.message.reply_text('you subscribe to automessaging.To stop press /stop.')
        context.job_queue.run_repeating(self.callback_task, self.interval, context=chat_id, name=str(chat_id))

    def stop_notify(self, update, context):
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id, text='Stopping automatic messages!')
        job = context.job_queue.get_jobs_by_name(str(chat_id))
        job[0].schedule_removal()

    def run(self):

        # create the updater, that will automatically create also a dispatcher and a queue to
        # make them dialogue
        updater = Updater(self.token, use_context=True)
        dispatcher = updater.dispatcher

        # handlers for regular commands
        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(CommandHandler("all_tanks", self.get_all_tanks))
        dispatcher.add_handler(CommandHandler("help", self.help))
        # dispatcher.add_handler(MessageHandler(Filters.text, self.text))
        # dispatcher.add_error_handler(self.error)

        # handlers for scheduler
        dispatcher.add_handler(CommandHandler("auto", self.start_auto_messaging))
        dispatcher.add_handler(CommandHandler("stop", self.stop_notify))

        # start your shiny new bot
        updater.start_polling()

        # run the bot until Ctrl-C
        updater.idle()


class Tank:
    def __init__(self, tank_data):
        self.user_string = str(tank_data['entity']['user_string'])
        self.image_url = str(tank_data['entity']['image_url'])
        self.current_count = int(tank_data['current_count'])
        self.price = int(tank_data['price']['value'])

    def report_message(self):
        return f'{self.user_string}:{self.current_count} - {self.price} gold'


class Auction:

    @staticmethod
    def get_data():
        try:
            url = "https://eu.wotblitz.com/en/api/events/items/auction/?page_size=50&type%5B%5D=vehicle&saleable=true"
            result = requests.get(url).json()
        except requests.exceptions.RequestException:
            return {}
        return result


class LogicProcessor:
    def __init__(self):
        self.tanks_count_threshold = 200
        self.tanks = []

    def update_tanks(self):
        auction_data = Auction.get_data()
        self.tanks.clear()
        if 'results' not in auction_data:
            return FAIL
        for item in auction_data['results']:
            if item['available']:
                self.tanks.append(Tank(item))
        return OK

    def get_under_threshold_tanks_info(self):
        for tank in self.tanks:
            if tank.current_count < self.tanks_count_threshold and tank.current_count != 0:
                yield tank.report_message()

    def get_all_tanks_info(self):
        for tank in self.tanks:
            yield tank.report_message()


if __name__ == "__main__":
    bot = Bot()
    bot.run()

