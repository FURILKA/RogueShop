from discord.ext import commands
from discord.ext.commands import errors
from colors import color
import discord
# ==================================================================================================================================================================
class errors(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
    # **************************************************************************************************************************************************************
    @commands.Cog.listener()
    async def on_command_error(self,ctx, err):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            if ctx.message.content.find('!!')>=0: return
            lng = self.bot.allow_channels[ctx.channel.id]
            # ******************************************************************************************************************************************************
            if lng == 'ru':
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                if type(err) == discord.ext.commands.errors.CommandNotFound:
                    command_name = str(ctx.message.content).split(' ')[0].lower()
                    msg_text = f"Команда __**{command_name}**__ не существует\nМожет быть в названии команды опечатка?"
                    self.LLC.addlog(f'[{ctx.author.name}] Wrong command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.BotMissingPermissions:
                    msg_text = f"У бота отсутствуют права: {' '.join(err.missing_perms)}\nВыдайте их ему для полного функционирования бота"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.MissingPermissions:
                    msg_text=f"У вас недостаточно прав для запуска этой команды!"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.UserInputError:
                    msg_text=f"Правильное использование команды {ctx.command}({ctx.command.brief}): `{ctx.command.usage}`"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.CommandOnCooldown:
                    msg_text=f"У вас еще не прошел кулдаун на команду {ctx.command}!\nПодождите еще {err.retry_after:.2f}"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.MissingAnyRole:
                    msg_text=f"Для запуска команды **{self.bot.prefix}{ctx.command.aliases[0]}** необходимо обладать ролью: **{'**, **'.join(err.missing_roles)}**"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                else:
                    msg_text=f"Произошла неизвестная ошибка:\n[*{err}*]\nПожалуйста, свяжитесь с разработчиками для исправления этой ошибки"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
            # ******************************************************************************************************************************************************
            if lng == 'en':
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                if type(err) == discord.ext.commands.errors.CommandNotFound:
                    command_name = str(ctx.message.content).split(' ')[0].lower()
                    msg_text = f"Command __**{command_name}**__ does not exist\nCheck command name and try again"
                    self.LLC.addlog(f'[{ctx.author.name}] Wrong command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.BotMissingPermissions:
                    msg_text = f"Bot dont have enough access right: {' '.join(err.missing_perms)}"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.MissingPermissions:
                    msg_text=f"You don't have enough access right to execute this command"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.UserInputError:
                    msg_text=f"Wrong command usage: {ctx.command}({ctx.command.brief}): `{ctx.command.usage}`"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.CommandOnCooldown:
                    msg_text=f"Please wait cooldown for use command {ctx.command} again!\nYou need to wait about {err.retry_after:.2f}"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                elif type(err) == discord.ext.commands.errors.MissingAnyRole:
                    msg_text=f"For execute command **{self.bot.prefix}{ctx.command.aliases[0]}** you need to have roles: **{'**, **'.join(err.missing_roles)}**"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                else:
                    msg_text=f"Something goes wrong:\n[*{err}*]\nPlease, contact FURILKA#5953"
                # --------------------------------------------------------------------------------------------------------------------------------------------------
            # ******************************************************************************************************************************************************
            embed=discord.Embed(color=color['red'])
            if lng == 'ru': embed.add_field(name=f':x: Ошибка', value=msg_text, inline=False)
            if lng == 'en': embed.add_field(name=f':x: Error', value=msg_text, inline=False)
            await ctx.send(content=ctx.author.mention,embed=embed)
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error')
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(errors(bot))