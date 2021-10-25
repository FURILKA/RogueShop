from logger import LocalLogCollector
from discord.ext import commands
from configurator import configurator
from mysqlconnector import mySQLConnector
import discord
import os
# ==================================================================================================================================================================
config = configurator(os.path.dirname(os.path.realpath(__file__))+"\config\config.ini")
prefix = config.get(section='bot',setting='prefix')
token  = config.get(section='bot',setting='token')
owners = config.get(section='bot',setting='owners')
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=prefix,intents=intents)
bot.remove_command('help')
bot.prefix = prefix
bot.LLC = LocalLogCollector()
bot.owners = owners.split(';')
mysql_host=config.get(section='mySQL',setting='host')
mysql_user=config.get(section='mySQL',setting='user')
mysql_pwrd=config.get(section='mySQL',setting='pass')
mysql_base=config.get(section='mySQL',setting='base')
bot.mysql = mySQLConnector(host=mysql_host,user=mysql_user,pwrd=mysql_pwrd,base=mysql_base,LLC = bot.LLC)
bot.rogue_mainsite = config.get(section='RogueWar',setting='rogue_mainsite')
bot.bot_api_secret = config.get(section='RogueWar',setting='bot_api_secret')
bot.rogue_guild_id = int(config.get(section='RogueWar',setting='rogue_guild_id'))
bot.vetted_role_id = int(config.get(section='RogueWar',setting='vetted_role_id'))
bot.roguewar_token = ''
bot.emoji = {}
bot.allow_channels = {} 
# ==================================================================================================================================================================
# cogs load order
cogs_list = [
    'on_ready.py',
    'on_errors.py',
    'commands_help.py',
    'commands_owner.py',
    'commands_common.py',
    'commands_debug.py',
    'loop_tasks.py']
# ==================================================================================================================================================================
# cogs load function
def load_cogs(reload=False):
    bot.LLC.addlog('Laoding cogs')
    for filename in cogs_list:
        if filename.endswith('.py'):
            fn = f'cogs.{filename[:-3]}'
            if reload==True:
                bot.unload_extension(fn)
            bot.LLC.addlog(f'Loading: "{fn}"')
            bot.load_extension(fn)
    bot.LLC.addlog('Cogs loaded')
# ==================================================================================================================================================================
# starting bot
bot.LLC.addlog('Starting bot')
load_cogs()
bot.IsOnlineNow = False
bot.run(token)