from discord.ext import commands
from discord.ext.commands.core import command
from colors import color
import discord
# ==================================================================================================================================================================
class help(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
    # **************************************************************************************************************************************************************
    @commands.command()
    async def help(self,ctx,command_for_more_help=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            lng = self.bot.allow_channels[ctx.channel.id]
            command_name = 'help'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {command_for_more_help=}',location=ctx.guild.name)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # Simple help command, without aditional command info
            if command_for_more_help == None:
                # forming 'commands_by_category' dict with commands names by category
                commands_by_category = {}
                for command_row in self.bot.commands_list:
                    command = {'name': command_row['command_name'],'type': ''}
                    for command_type_row in self.bot.commands_type:
                        if command_type_row['type'] == command_row['command_type']:
                            command['type'] = command_type_row[f'name_{lng}']
                    if command['type'] == '':
                        if lng == 'ru' : command['type'] = 'Без категории'
                        if lng == 'en' : command['type'] = 'Uncategorized'
                    if command['type'] not in commands_by_category: commands_by_category[command['type']] = []
                    commands_by_category[command['type']].append(command['name'])
                # Dict is done, making message
                if lng == 'ru': embed=discord.Embed(title=":page_facing_up: Справка", description="Список доступных команд:", color=color['green'])
                if lng == 'en': embed=discord.Embed(title=":page_facing_up: Help", description="Available commands list:", color=color['green'])
                for command_category in commands_by_category:
                    commands_list = commands_by_category[command_category]
                    field_value = ''
                    for command_name in commands_list:
                        field_value += command_name + '\n'
                    embed.add_field(name=f'{command_category}',value=field_value,inline=False)
                # Sending message
                if lng == 'ru': embed.set_footer(text=f'Для подробной справки введи {self.bot.prefix}help <имя_команды>')
                if lng == 'en': embed.set_footer(text=f'For more help use {self.bot.prefix}help <command_name>')
                embed.set_thumbnail(url=self.bot.user.avatar_url)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if command_for_more_help != None:
                self.bot.LLC.addlog(f'Запрошена дополнительная справка по команде "{command_for_more_help}"')
                command_for_more_help = command_for_more_help.lower()
                for command_row in self.bot.commands_list:
                    command_name = command_row['command_name']
                    if command_name == command_for_more_help:
                        command_help = '\n'+command_row[f'command_help_{lng}']
                        command_help = command_help.replace('<prefix>',self.bot.prefix)
                        if lng == 'ru':
                            field_name = f':page_facing_up: Информация по команде "**{command_name}**"'
                            footer_text = f'Для получения справки введи {self.bot.prefix}help'
                        if lng == 'en':
                            field_name = f':page_facing_up: Additional command help: "**{command_name}**"'
                            footer_text = f'For more help use {self.bot.prefix}help'
                        embed=discord.Embed(color=color['green'])
                        embed.add_field(name=field_name,value=command_help,inline=True)
                        embed.set_footer(text=footer_text)
                        await ctx.send(embed=embed)
                        return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            self.bot.LLC.addlog(f'Command "{command_for_more_help}" does not exist!',msg_type='info',location=ctx.guild.name)     
            if lng == 'ru':    
                msgtext  = f'Команда "**{command_for_more_help}**" не найдена!\n'
                msgtext += f'Проверьте корректность указания команды'
                field_name = ':x: Ошибка'
            if lng == 'en':
                msgtext  = f'Command "**{command_for_more_help}**" does not exist!\n'
                msgtext += f'Check that the command name is correct'
                field_name = ':x: Error'
            embed=discord.Embed(color=color['red'])
            embed.add_field(name=field_name, value=msgtext, inline=False)
            await ctx.send(embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru': 
                msgtext = f'Что-то пошло не так'
                title = ':x: Ошибка'
            if lng == 'en': 
                msgtext = f'Something goes wrong'
                title = ':x: Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            await ctx.send(embed=embed)
            self.bot.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(help(bot))