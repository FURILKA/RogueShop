from discord.ext import commands
from colors import color
import discord
import os,sys
import asyncio
# ==================================================================================================================================================================
class owner(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
    # **************************************************************************************************************************************************************
    @commands.Cog.listener()
    async def on_ready(self):
        # **********************************************************************************************************************************************************
        # Загрузка эмодзи
        def load_emoji():
            try:
                result = self.bot.mysql.execute(f"SELECT emoji_name, emoji_text FROM emojis")
                emojis = {}
                for row in result:
                    emoji_name = row['emoji_name']
                    emoji_text = row['emoji_text']
                    emojis[emoji_name] = emoji_text
                self.bot.emoji = emojis
            except Exception as error:
                self.LLC.addlog(str(error),'error')
        # **********************************************************************************************************************************************************
        # Загрузка команд
        def load_commands():
            try:
                self.bot.commands_type = self.bot.mysql.execute(f"SELECT * FROM commands_types")
                self.bot.commands_list = self.bot.mysql.execute(f"SELECT * FROM commands")
            except Exception as error:
                self.LLC.addlog(str(error),'error')
        # **********************************************************************************************************************************************************
        self.bot.LLC.addlog('Loading commands')
        load_commands()
        self.bot.LLC.addlog('Loading emoji')
        load_emoji()
        self.bot.LLC.addlog('Bot is online and ready to serve')
        self.bot.IsOnlineNow = True
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(owner(bot))