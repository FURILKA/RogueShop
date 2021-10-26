from discord.ext import commands
from colors import color
import discord
import os,sys

# ==================================================================================================================================================================
class owner(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
    # **************************************************************************************************************************************************************
    # Проверка на владельца бота, возвращает True если инициатор команды владелец, возвращает False + пишет отбивку если нет
    async def isOwner(self,ctx):
        try:
            member_id = str(ctx.author.id)
            if member_id in self.bot.owners:
                return(True)
            else:
                self.LLC.addlog(f'Пользователь: "{ctx.author.name}" [id:{ctx.author.id}] не является админом сервера "{ctx.guild.name}"')
                msgtext  = 'У тебя нет прав для выполнения данной команды\n'
                msgtext += 'Данная команда доступна только для владельцев бота'
                embed = discord.Embed(description = msgtext, color = color['red'])
                await ctx.send(embed=embed)
                return(False)
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
    # Перезагрузка когов
    @commands.command(aliases = ["reload"])
    async def command_reload(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'reload'
            guild = ctx.guild
            member = ctx.author
            self.LLC.addlog(f'Новая команда "{self.bot.prefix}{command_name}" [сервер: "{guild.name}", пользователь: "{member.id}"]')
            if await self.isOwner(ctx) == False: return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            self.LLC.export()
            self.LLC.addlog('Перезагружаем коги')
            for filename in os.listdir(os.path.dirname(os.path.realpath(__file__))):
                if filename.endswith('.py'):
                    fn = f'cogs.{filename[:-3]}'
                    self.LLC.addlog(f'Загружаем: "{fn}"')
                    self.bot.unload_extension(fn)
                    self.bot.load_extension(fn)
            await ctx.send('Коги перезагружены')
            self.LLC.addlog('Коги перезагружены')
            self.LLC.export()
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
    # Перезагрузка всего бота
    @commands.command(aliases = ["reboot"])
    async def command_reboot(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            guild = ctx.guild
            member = ctx.author
            self.LLC.addlog(f'Новая команда "{self.bot.prefix}reboot" [сервер: "{guild.name}", пользователь: "{member.name}"]')
            if await self.isOwner(ctx) == False: return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            embed = discord.Embed(description = "Перезапускаем бота...", color = color['green'])
            self.LLC.addlog('Перезапускаем бота')
            self.LLC.export()
            await ctx.send(embed=embed)
            await os.execv(sys.executable, ["python"] + sys.argv)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(owner(bot))