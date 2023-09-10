import dotenv
import os

import discord as d
from loguru import logger

dotenv.load_dotenv()

bot = d.Bot()
bot.load_extension('hestia.cogs.events')
with logger.catch():
    bot.run(os.getenv('HESTIA_DISCORD_TOKEN'))
