from discord.ext import commands
from colors import color
import random
import discord
import os,sys
import urllib.request
# ==================================================================================================================================================================
class debug(commands.Cog):
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
    @commands.command(aliases = ["sendimage"])
    async def command_sendimage(self,ctx):
        try:
            url = "https://static-cdn.jtvnw.net/previews-ttv/live_user_figaxshow-500x300.jpg"
            filename = str(random.randint(100000000000,999999999999))+'.jpg'
            filepath = os.getcwd().replace('\\','/')+'/images/temp/'+filename
            urllib.request.urlretrieve(url,filepath)
            file = discord.File(filepath, filename=filename)
            embed = discord.Embed()
            embed.set_image(url="attachment://"+filename)
            await ctx.channel.send(file=file, embed=embed)
            os.remove(filepath)
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
    @commands.command(aliases = ["emojilist"])
    async def command_emojilist(self,ctx):
        try:
            guild = ctx.guild
            emojis = guild.emojis
            emoji_dict = {'id':[],'name':[],'emoji':[]}
            for emoji in emojis:
                emoji_dict['id'].append(f'\<:{emoji.name}:{emoji.id}>')
                emoji_dict['name'].append(str(emoji.name))
                emoji_dict['emoji'].append(f'<:{emoji.name}:{emoji.id}>')
            embed=discord.Embed(title=':gear: debug_command_emojilist',description='current server emoji list',color=color['green'])
            embed.add_field(name=f'emoji', value='\n'.join(emoji_dict['emoji']), inline=True )
            embed.add_field(name=f'id', value='\n'.join(emoji_dict['id']), inline=True)
            embed.add_field(name=f'name', value='\n'.join(emoji_dict['name']), inline=True)
            await ctx.send(embed=embed)
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
    @commands.command(aliases = ["printemoji"])
    async def command_printemoji(self,ctx,emoji_id):
        try:
            emoji_name = self.bot.emoji[emoji_id]
            embed=discord.Embed(title='debug_command_printemoji',color=color['green'])
            embed.add_field(name=f':gear: result', value=f'{emoji_name}', inline=False)
            await ctx.send(embed=embed)
        except Exception as error:
            self.LLC.addlog(str(error),'error')
    # **************************************************************************************************************************************************************
    @commands.command(aliases = ["myroles"])
    async def command_myroles(self,ctx):
        guild = ctx.guild
        role = guild.get_role(871343148192903228)
        my_roles = ctx.author.roles
        for my_role in my_roles:
            print(my_role)
            if role == my_role: print('>>>')
    # **************************************************************************************************************************************************************
    @commands.command(aliases = ["cleartoken"])
    async def command_cleartoken(self,ctx):
        self.bot.roguewar_token = ''
        self.bot.LLC.addlog('token cleared')
        self.bot.LLC.addlog(f'{self.bot.roguewar_token}')
    # **************************************************************************************************************************************************************
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(debug(bot))