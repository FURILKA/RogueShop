from datetime import datetime, timedelta, date
from discord.ext import commands
from colors import color
import discord
import math
# ==================================================================================================================================================================
class commands_common(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
    # ==============================================================================================================================================================
    # functions used by commands
    # ==============================================================================================================================================================
    def is_player_vetted(self,ctx):
        try:
            guild = self.bot.get_guild(self.bot.rogue_guild_id)
            role = guild.get_role(self.bot.vetted_role_id)
            member = guild.get_member(ctx.author.id)
            if member == None: return False
            for member_role in member.roles:
                if member_role == role: return(True)
            return(False)
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error')
            return(False)
    # **************************************************************************************************************************************************************
    async def find_by_market_type(self,ctx,faction_name=None,item_name=None,market_type=None):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            titles = {
                'ru':{
                    'error': self.bot.emoji['error']+' Ошибка',
                    'stop': self.bot.emoji['stop']+' Не удалось выполнить',
                    'success': ':white_check_mark: Запрос на поиск добавлен'
                    },
                'en':{
                    'error': self.bot.emoji['error']+' Error',
                    'stop': self.bot.emoji['stop']+" Can`t execute",
                    'success': self.bot.emoji['success'] + ' New find request added'
                    }
            }
            if market_type == 'onlineshop':
                command_name = 'osfind'
                if lng == 'ru': market_type_name = 'онлайн магазин'
                if lng == 'en': market_type_name = 'onlineshop'
            if market_type == 'blackmarket':
                command_name = 'bmfind'
                if lng == 'ru': market_type_name = 'черный рынок'
                if lng == 'en': market_type_name = 'blackmarket'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # if faction name not specified
            if faction_name == None:
                query = f"SELECT * FROM factions_default WHERE channel_id = {ctx.channel.id} AND user_id = {ctx.author.id}"
                result_faction_by_user = self.bot.mysql.execute(query)
                if result_faction_by_user != [] and result_faction_by_user != (): 
                    faction_name = result_faction_by_user[0]['faction_name_short']
                else:
                    if lng == 'ru': msgtext  = f'Имя фракции не указано!\n'
                    if lng == 'en': msgtext  = f'Faction name dont specified!\n'
                    embed=discord.Embed(color=color['red'])
                    embed.add_field(name=titles[lng]['error'], value=msgtext, inline=False)
                    embed.set_footer(text=footer_text)
                    await ctx.message.add_reaction('❌')
                    await ctx.send(embed=embed)
                    return
            else:
                faction_name = faction_name.lower()
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # check - is faction name correct?
            if faction_name not in self.bot.factions:
                if lng == 'ru': msgtext  = f'Имя фракции указано некорректно: "{faction_name}"\n'
                if lng == 'en': msgtext  = f'Wrong faction name: "{faction_name}"\n'
                embed=discord.Embed(color=color['red'])
                embed.add_field(name=titles[lng]['error'], value=msgtext, inline=False)
                embed.set_footer(text=footer_text)
                await ctx.message.add_reaction('❌')
                await ctx.send(embed=embed)
                return
            else:
                faction_short = faction_name
                faction_full = self.bot.factions[faction_short]
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # if item name not specified?
            if item_name == None:
                if lng == 'ru': msgtext  = f'Имя предмета для создания поискового запроса не указано!\n'
                if lng == 'en': msgtext  = f'item name for find request dont specified!\n'
                embed=discord.Embed(color=color['red'])
                embed.add_field(name=titles[lng]['error'], value=msgtext, inline=False)
                embed.set_footer(text=footer_text)
                await ctx.message.add_reaction('❌')
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # check if request for search this item name is already exist?
            query = f"""
                SELECT *, DATE_ADD(date_add, INTERVAL 3 DAY) as date_expire  FROM requests 
                    WHERE 
                            status = 'in progress' 
                        AND
                            market_type = '{market_type}'
                        AND
                            user_id = {ctx.author.id}
                        AND
                            guild_id = {ctx.guild.id}
                        AND
                            channel_id = {ctx.channel.id}
                        AND
                            LOWER(item_name) = LOWER('{item_name}')
                        AND
                            status = 'in progress'
            """
            result = self.bot.mysql.execute(query)
            if result != [] and result != ():
                date_add = result[0]['date_add'].strftime('%d.%m.%Y %H:%M:%S')
                date_expire = result[0]['date_expire'].strftime('%d.%m.%Y %H:%M:%S')
                if lng == 'ru':
                    msgtext  = f'У тебя уже есть такой запрос на поиск\n'
                    msgtext += f'Тип магазина: **{market_type_name}**\n'
                    msgtext += f'Имя предмета: **{item_name}**\n'
                    msgtext += f'Фракция: **{faction_full}**\n'
                    msgtext += f'Срок действия запроса: **{date_expire}**'
                if lng == 'en':
                    msgtext  = f'You already have find request for this\n'
                    msgtext += f'Market type: **{market_type_name}**\n'
                    msgtext += f'Item name: **{item_name}**\n'
                    msgtext += f'Faction: **{faction_full}**\n'
                    msgtext += f'Request expire date: **{date_expire}**'
                embed=discord.Embed(color=color['red'])
                embed.add_field(name=titles[lng]['stop'], value=msgtext, inline=False)
                embed.set_footer(text=footer_text)
                await ctx.message.add_reaction('🚫')
                await ctx.send(content=ctx.author.mention,embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # Getting member vetted status
            vetted_status = self.is_player_vetted(ctx)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # inserting new request row to requests-table
            user_name = ctx.author.name.replace("'","\\'").replace(";","\\;")
            item_name_to_insert = item_name.replace("'","\\'").replace(";","\\;")
            columns = [
                'status',
                'market_type',
                'guild_id',
                'guild_name',
                'channel_id',
                'channel_name',
                'user_id',
                'user_name',
                'user_is_vetted',
                'faction_name_short',
                'faction_name_full',
                'item_name'
            ]
            values = [
                "'in progress'", # status
                f"'{market_type}'", # market_type
                f"{ctx.guild.id}", # guild_id
                f"'{ctx.guild.name}'", # guild_name
                f"{ctx.channel.id}", # channel_id
                f"'{ctx.channel.name}'", # channel_name
                f"{ctx.author.id}", # user_id
                f"'{user_name}'", # user_name
                f'{vetted_status}', # user_is_vetted
                f"'{faction_short}'", # faction_name_short
                f"'{faction_full}'", # faction_name_full
                f"'{item_name_to_insert}'" # item_name
            ]
            query = f'INSERT INTO requests ({",".join(columns)}) VALUES ({",".join(values)})'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            date_expire = datetime.now() + timedelta(days=3)
            date_expire = date_expire.strftime('%d.%m.%Y %H:%M:%S')
            if lng == 'ru':
                title = 'Запрос на поиск добавлен'
                embed_name = 'Детали запроса'
                embed_value  = f'Тип магазина: **{market_type_name}**\n'
                embed_value += f'Имя предмета: **{item_name}**\n'
                embed_value += f'Фракция: **{faction_full}**\n'
                embed_value += f'Срок действия запроса: **{date_expire}**\n'
                if vetted_status == True: 
                    embed_value += f'Статус карьеры: **Подтвержденный**'
                    footer_text = 'Вы обладаете полным доступом к онлайн-магазину'
                if vetted_status == False:
                    embed_value += f'Статус карьеры: __**не подтвержденный**__'
                    footer_text = 'Не подтвержденный статус означает ограниченный доступ к онлайн-магазину'  
            if lng == 'en':
                title = 'New find request added'
                embed_name = 'Request details'
                embed_value  = f'Market type: **{market_type_name}**\n'
                embed_value += f'Item name: **{item_name}**\n'
                embed_value += f'Faction: **{faction_full}**\n'
                embed_value += f'Request expire: **{date_expire}**\n'
                if vetted_status == True: 
                    embed_value += f'Career status: **vetted**'
                    footer_text = 'Vetted career status means full access to onlineshops'
                if vetted_status == False:
                    embed_value += f'Career status: __**non vetted**__'
                    footer_text = 'Non vetted career status means limited access to onlineshops'  
            emoji_name = self.bot.emoji['success']
            emoji_id =''.join(i for i in emoji_name if i.isdigit())
            emoji_obj = self.bot.get_emoji(int(emoji_id))
            embed = discord.Embed(title=title, color = color['green'])
            embed.add_field(name=embed_name, value=embed_value, inline=False)
            embed.set_footer(text=footer_text)
            embed.set_thumbnail(url=str(emoji_obj.url))
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            await ctx.message.add_reaction('👍')
            self.bot.mysql.execute(query)
            await ctx.send(content=ctx.author.mention,embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    async def list_by_market_type(self,ctx,market_type):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            if market_type == 'onlineshop':  command_name = 'oslist'
            if market_type == 'blackmarket': command_name = 'bmlist'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            # check - if member have any find requests with this market type?
            query = f"""
                SELECT * 
                FROM requests 
                WHERE
                    market_type = '{market_type}'
                AND
                    channel_id = {ctx.channel.id}
                AND
                    user_id = {ctx.author.id}
                AND
                    status = 'in progress'
                """
            result = self.bot.mysql.execute(query)
            if result == [] or result == ():
                if lng == 'ru':
                    title = 'У тебя пока нет ни одного поискового запроса'
                    embed = discord.Embed(title=title, color = color['gray'])
                    embed.set_footer(text=footer_text)
                if lng == 'en':
                    title = 'You don`t have any find requests yet'
                    embed = discord.Embed(title=title, color = color['gray'])
                    embed.set_footer(text=footer_text)
                await ctx.send(content=ctx.author.mention,embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            i = 1
            items_list = []
            if lng == 'ru':
                title = 'Информация о текущих запросах на поиск'
                embed_name = 'Список запросов:'
            if lng == 'en':
                title = 'Information about current find requests'
                embed_name = 'Requests list:'
            embed = discord.Embed(title=title, color = color['blue'])
            for row in result:
                item_name = row['item_name']
                faction_name_full = row['faction_name_full']
                items_list.append(f'#{str(i)} [{faction_name_full}] **{item_name}**')
                i += 1
            embed_value = '\n'.join(items_list)
            if market_type == 'onlineshop':  emoji_name = self.bot.emoji['shoppingcart']
            if market_type == 'blackmarket': emoji_name = self.bot.emoji['pirateflag']
            emoji_id =''.join(i for i in emoji_name if i.isdigit())
            emoji_obj = self.bot.get_emoji(int(emoji_id))
            embed.set_thumbnail(url=str(emoji_obj.url))
            embed.add_field(name=embed_name, value=embed_value, inline=False)
            embed.set_footer(text=footer_text)    
            await ctx.send(content=ctx.author.mention,embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    async def clear_by_market_type(self,ctx,market_type):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            if market_type == 'onlineshop':  command_name = 'osclear'
            if market_type == 'blackmarket': command_name = 'bmclear'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            query = f"""
                SELECT * 
                FROM requests 
                WHERE
                    market_type = '{market_type}'
                AND
                    channel_id = {ctx.channel.id}
                AND
                    user_id = {ctx.author.id}
                AND
                    status = 'in progress'
                """
            result = self.bot.mysql.execute(query)
            if result == [] or result == ():
                if lng == 'ru':
                    title = 'У тебя пока нет ни одного поискового запроса'
                    embed = discord.Embed(title=title, color = color['gray'])
                    embed.set_footer(text=footer_text)
                if lng == 'en':
                    title = 'You don`t have any find requests yet'
                    embed = discord.Embed(title=title, color = color['gray'])
                    embed.set_footer(text=footer_text)
                await ctx.send(content=ctx.author.mention,embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            query = f"""
                UPDATE requests 
                SET status = 'deleted'
                WHERE
                    market_type = '{market_type}'
                AND
                    channel_id = {ctx.channel.id}
                AND
                    user_id = {ctx.author.id}
                AND
                    status = 'in progress'
                """
            if lng == 'ru': title = 'Текущий список запросов на поиск очищен'
            if lng == 'en': title = 'Current find requests list cleared'
            embed = discord.Embed(title=title, color = color['blue'])
            embed.set_footer(text=footer_text)    
            await ctx.send(content=ctx.author.mention,embed=embed)
            self.bot.mysql.execute(query)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    async def del_by_market_type(self,ctx,market_type,item_index):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            if market_type == 'onlineshop':
                command_name = 'osfind'
                if lng == 'ru': market_type_name = 'онлайн магазин'
                if lng == 'en': market_type_name = 'onlineshop'
            if market_type == 'blackmarket':
                command_name = 'bmfind'
                if lng == 'ru': market_type_name = 'черный рынок'
                if lng == 'en': market_type_name = 'blackmarket'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if item_index == None:
                if market_type == 'onlineshop':  command_prefix = 'os'
                if market_type == 'blackmarket': command_prefix = 'bm'
                if lng == 'ru':
                    msgtext  = f'Не указан # (номер) запроса для удаления!\n'
                    msgtext += f'Для получения # запроса используй: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'Для удаления __всех__ запросов используй: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Number (#) of request for deletion is not specified!\n'
                    msgtext += f'To get the request # use: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'To delete __all__ requests use: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            item_index = item_index.replace('#','')
            if item_index.isdigit() == False or int(item_index) <= 0:
                if market_type == 'onlineshop':  command_prefix = 'os'
                if market_type == 'blackmarket': command_prefix = 'bm'
                if lng == 'ru':
                    msgtext  = f'Некорректный # (номер) запроса для удаления!\n'
                    msgtext += f'Для получения # запроса используй: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'Для удаления __всех__ запросов используй: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Wrong # (number) of request for deletion!\n'
                    msgtext += f'To get the request # use: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'To delete __all__ requests use: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            item_index = int(item_index)
            query = f"""
                SELECT * 
                FROM requests 
                WHERE
                    market_type = '{market_type}'
                AND
                    channel_id = {ctx.channel.id}
                AND
                    user_id = {ctx.author.id}
                AND
                    status = 'in progress'
                """
            result = self.bot.mysql.execute(query)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if len(result) < item_index:
                if market_type == 'onlineshop':  command_prefix = 'os'
                if market_type == 'blackmarket': command_prefix = 'bm'
                if lng == 'ru':
                    msgtext  = f'Запрос под номером #{item_index} не найден!\n'
                    msgtext += f'Общее количество твоих запросов: {len(result)}\n'
                    msgtext += f'Для получения # запроса используй: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'Для удаления __всех__ запросов используй: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Request with number of #{item_index} not found!\n'
                    msgtext += f'You got only {len(result)} requests for now\n'
                    msgtext += f'To get the request # use: **{self.bot.prefix}{command_prefix}list**\n'
                    msgtext += f'To delete __all__ requests use: **{self.bot.prefix}{command_prefix}clear**'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            row = result[item_index-1]
            row_id = row['id']
            item_name = row['item_name']
            faction_full = row['faction_name_full']
            query = f"UPDATE requests SET status = 'deleted' WHERE id = {row_id}"
            if lng == 'ru':
                title = 'Запрос на поиск удален'
                embed_name = 'Детали удаленного запроса'
                embed_value  = f'Тип магазина: **{market_type_name}**\n'
                embed_value += f'Имя предмета: **{item_name}**\n'
                embed_value += f'Фракция: **{faction_full}**\n'
            if lng == 'en':
                title = 'Find request deleted'
                embed_name = 'Request details'
                embed_value  = f'Market type: **{market_type_name}**\n'
                embed_value += f'Item name: **{item_name}**\n'
                embed_value += f'Faction: **{faction_full}**\n'
            emoji_name = self.bot.emoji['success']
            emoji_id =''.join(i for i in emoji_name if i.isdigit())
            emoji_obj = self.bot.get_emoji(int(emoji_id))
            embed = discord.Embed(title=title, color = color['green'])
            embed.add_field(name=embed_name, value=embed_value, inline=False)
            embed.set_footer(text=footer_text)
            embed.set_thumbnail(url=str(emoji_obj.url))
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            await ctx.message.add_reaction('👍')
            self.bot.mysql.execute(query)
            await ctx.send(content=ctx.author.mention,embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    async def set_faction_by_market_type(self,ctx,market_type,faction_name):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            if market_type == 'onlineshop':
                command_name = 'setfactionos'
                market_type_short = 'os'
                if lng == 'ru': market_type_name = 'онлайн магазин'
                if lng == 'en': market_type_name = 'onlineshop'
            if market_type == 'blackmarket':
                command_name = 'setfactionbm'
                market_type_short = 'bm'
                if lng == 'ru': market_type_name = 'черный рынок'
                if lng == 'en': market_type_name = 'blackmarket'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            query = f"""
                SELECT *
                FROM factions_default
                WHERE
                    user_id = {ctx.author.id}
                AND
                    channel_id = {ctx.channel.id}
                AND
                    market_type = '{market_type}'
            """
            result = self.bot.mysql.execute(query)
            if faction_name == None:
                if result == [] or result == ():
                    if lng == 'ru':
                        msgtext  = f'Фракция по-умолчанию не задана!\n'
                        msgtext += f'Что бы задать фракцию введи команду:\n'
                        msgtext += f'**{self.bot.prefix}setfaction{market_type_short} <имя_фракции>**'
                        title = self.bot.emoji['error']+' Ошибка'
                    if lng == 'en':
                        msgtext  = f'Default faction is not set yet!\n'
                        msgtext += f'To set faction by default use:\n'
                        msgtext += f'**{self.bot.prefix}setfaction{market_type_short} <faction_name>**'
                        title = self.bot.emoji['error']+' Error'
                    embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                    embed.set_footer(text=footer_text)
                    await ctx.send(embed=embed)
                    return
                else:
                    embed = discord.Embed(color = color['blue'])
                    faction_name = result[0]['faction_name_full']
                    if lng == 'ru':
                        embed.add_field(name='Твоя текущая фракция:',value=f'__{faction_name}__')
                    if lng == 'en':
                        embed.add_field(name='Your current faction:',value=f'__{faction_name}__')
                    embed.set_footer(text=footer_text)
                    await ctx.send(embed=embed)
                    return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if faction_name.lower() not in self.bot.factions:
                if lng == 'ru':
                    msgtext  = f'Фракция "{faction_name}" не существует!\n'
                    msgtext += f'Что бы проверить имя фракции веди команду:\n'
                    msgtext += f'**{self.bot.prefix}factionslist**'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Faction "{faction_name}" does not exist!\n'
                    msgtext += f'To check faction name use command:\n'
                    msgtext += f'**{self.bot.prefix}factionslist**'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if faction_name.lower() in self.bot.factions:
                faction_name_short = faction_name.lower()
                faction_name_full = self.bot.factions[faction_name_short]
                if result == [] or result == ():
                    query = f"""
                        INSERT INTO factions_default
                            (
                                market_type,
                                channel_id,
                                channel_name,
                                user_id,
                                user_name,
                                user_mention,
                                faction_name_short,
                                faction_name_full
                            )
                        VALUES
                            (
                                '{market_type}',
                                {ctx.channel.id},
                                '{ctx.channel.name}',
                                {ctx.author.id},
                                '{ctx.author.name}',
                                '{ctx.author.mention}',
                                '{faction_name_short}',
                                '{faction_name_full}'
                            )
                    """
                    if lng == 'ru':
                        title = 'Фракция установлена'
                        embed_name = 'Текущая фракция:'
                    if lng == 'en': 
                        title = 'Faction by default added'
                        embed_name = 'Current faction name:'
                else:
                    if result[0]['faction_name_full'] == faction_name_full:
                        if lng == 'ru':
                            msgtext  = f'Невозможно изменить текущую фракцию!\n'
                            msgtext += f'Твоей фракцией __уже__ является "{faction_name_full}"'
                            title = self.bot.emoji['error']+' Ошибка'
                        if lng == 'en':
                            msgtext  = f'Unable to update your current faction!\n'
                            msgtext += f'Your current faction is __already__ "{faction_name_full}"'
                            title = self.bot.emoji['error']+' Error'
                        embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                        embed.set_footer(text=footer_text)
                        await ctx.send(embed=embed)
                        return
                    query = f"""
                        UPDATE factions_default
                        SET
                            faction_name_short = '{faction_name_short}',
                            faction_name_full = '{faction_name_full}'
                        WHERE
                            channel_id = {ctx.channel.id}
                            AND
                            user_id = {ctx.author.id}
                    """
                    if lng == 'ru' :
                        title = 'Фракция обновлена'
                        embed_name = 'Текущее имя фракции:'
                    if lng == 'en' :
                        title = 'Faction by default updated'
                        embed_name = 'Current faction name:'
            emoji_name = self.bot.emoji['success']
            emoji_id =''.join(i for i in emoji_name if i.isdigit())
            emoji_obj = self.bot.get_emoji(int(emoji_id))
            embed = discord.Embed(title=title, color = color['green'])
            embed.add_field(name=embed_name, value=faction_name_full, inline=False)
            embed.set_footer(text=footer_text)
            embed.set_thumbnail(url=str(emoji_obj.url))
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            await ctx.message.add_reaction('👍')
            self.bot.mysql.execute(query)
            await ctx.send(content=ctx.author.mention,embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    async def del_faction_by_market_type(self,ctx,market_type):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            if market_type == 'onlineshop':
                command_name = 'setfactionos'
                market_type_short = 'os'
                if lng == 'ru': market_type_name = 'онлайн магазин'
                if lng == 'en': market_type_name = 'onlineshop'
            if market_type == 'blackmarket':
                command_name = 'setfactionbm'
                market_type_short = 'bm'
                if lng == 'ru': market_type_name = 'черный рынок'
                if lng == 'en': market_type_name = 'blackmarket'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use {self.bot.prefix}help {command_name}'
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            query = f"""
                SELECT *
                FROM factions_default
                WHERE
                    user_id = {ctx.author.id}
                AND
                    channel_id = {ctx.channel.id}
                AND
                    market_type = '{market_type}'
            """
            result = self.bot.mysql.execute(query)
            if result == [] or result == ():
                if lng == 'ru':
                    msgtext  = f'Невозможно удалить фракцию по-умолчанию\n'
                    msgtext += f'Фракция по-умолчанию не задана\n'
                    msgtext += f'Что бы задать фракцию введи команду:\n'
                    msgtext += f'**{self.bot.prefix}setfaction{market_type_short} <имя_фракции>**'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Unable to delete faction by default\n'
                    msgtext += f'Default faction is not set yet\n'
                    msgtext += f'To set faction by default use:\n'
                    msgtext += f'**{self.bot.prefix}setfaction{market_type_short} <имя_фракции>**'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            else:
                if lng == 'ru' :
                    title = 'Фракция обновлена'
                    embed_name = 'Текущее имя фракции:'
                    faction_name_full = 'Нет'
                if lng == 'en' :
                    title = 'Faction by default updated'
                    embed_name = 'Current faction name:'
                    faction_name_full = 'None'
                emoji_name = self.bot.emoji['success']
                emoji_id =''.join(i for i in emoji_name if i.isdigit())
                emoji_obj = self.bot.get_emoji(int(emoji_id))
                embed = discord.Embed(title=title, color = color['green'])
                embed.add_field(name=embed_name, value=faction_name_full, inline=False)
                embed.set_footer(text=footer_text)
                embed.set_thumbnail(url=str(emoji_obj.url))
                query = f"""
                    DELETE FROM factions_default
                    WHERE
                        user_id = {ctx.author.id}
                    AND
                        channel_id = {ctx.channel.id}
                    AND
                        market_type = '{market_type}'
                """
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            await ctx.message.add_reaction('👍')
            self.bot.mysql.execute(query)
            await ctx.send(content=ctx.author.mention,embed=embed)
            return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    # Commands
    # **************************************************************************************************************************************************************
    @commands.command()
    async def osfind(self,ctx,faction_name=None,*,item_name=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'osfind'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {faction_name=} {item_name=}',location=ctx.guild.name)
            await self.find_by_market_type(ctx=ctx,faction_name=faction_name,item_name=item_name,market_type='onlineshop')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def bmfind(self,ctx,faction_name=None,*,item_name=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'bmfind'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {faction_name=} {item_name=}',location=ctx.guild.name)
            await self.find_by_market_type(ctx=ctx,faction_name=faction_name,item_name=item_name,market_type='blackmarket')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def oslist(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'oslist'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.list_by_market_type(ctx=ctx,market_type='onlineshop')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def bmlist(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'bmlist'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.list_by_market_type(ctx=ctx,market_type='blackmarket')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def osclear(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'osclear'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.clear_by_market_type(ctx=ctx,market_type='onlineshop')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def bmclear(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'bmclear'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.clear_by_market_type(ctx=ctx,market_type='blackmarket')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def osdel(self,ctx,item_index=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'osdel'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {item_index=}',location=ctx.guild.name)
            await self.del_by_market_type(ctx=ctx,market_type='onlineshop',item_index=item_index)
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def bmdel(self,ctx,item_index=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'bmdel'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {item_index=}',location=ctx.guild.name)
            await self.del_by_market_type(ctx=ctx,market_type='blackmarket',item_index=item_index)
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def bmfindall(self,ctx,item_name=None):
        try:
            lng = self.bot.allow_channels[ctx.channel.id]
            command_name = 'bmfindall'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {item_name=}',location=ctx.guild.name)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if item_name == None:
                if lng == 'ru':
                    msgtext  = f'Имя предмета для поиска не указано!'
                    title = self.bot.emoji['error']+' Ошибка'
                if lng == 'en':
                    msgtext  = f'Item name is not specified!\n'
                    title = self.bot.emoji['error']+' Error'
                embed = discord.Embed(title=title, description = msgtext, color = color['red'])
                embed.set_footer(text=footer_text)
                await ctx.send(embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            vetted_status = self.is_player_vetted(ctx)
            if vetted_status == False: query = f"SELECT * FROM goods_blackmarket WHERE LOWER(item_name) LIKE LOWER('%{item_name}%') AND for_non_vets = 1"
            if vetted_status == True:  query = f"SELECT * FROM goods_blackmarket WHERE LOWER(item_name) LIKE LOWER('%{item_name}%')"
            result_blackmarket_good = self.bot.mysql.execute(query)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if result_blackmarket_good == [] or result_blackmarket_good == ():
                if lng == 'ru':
                    title = 'Поиск предмета на черных рынках всех фракций'
                    embed = discord.Embed(title=title, color = color['green'])
                    embed_name = 'Детали запроса'
                    embed_value = f'Имя предмета: **{item_name}**\n'
                    if vetted_status == True: 
                        embed_value += f'Статус карьеры: **Подтвержденный**'
                        footer_text = 'Вы обладаете полным доступом к онлайн-магазину'
                    if vetted_status == False:
                        embed_value += f'Статус карьеры: __**не подтвержденный**__'
                        footer_text = 'Не подтвержденный статус означает ограниченный доступ к онлайн-магазину'  
                    embed.add_field(name=embed_name, value=embed_value, inline=False)
                    embed.add_field(name='Результат', value='Ничего не найдено', inline=False)
                if lng == 'en':
                    title = 'New find request added'
                    embed = discord.Embed(title=title, color = color['green'])
                    embed_name = 'Request details'
                    embed_value = f'Item name: **{item_name}**\n'
                    if vetted_status == True: 
                        embed_value += f'Career status: **vetted**'
                        footer_text = 'Vetted career status means full access to onlineshops'
                    if vetted_status == False:
                        embed_value += f'Career status: __**non vetted**__'
                        footer_text = 'Non vetted career status means limited access to onlineshops'
                    embed.add_field(name=embed_name, value=embed_value, inline=False)
                    embed.add_field(name='Result', value='Nothing found', inline=False)
                emoji_name = self.bot.emoji['piratethonk']
                emoji_id =''.join(i for i in emoji_name if i.isdigit())
                emoji_obj = self.bot.get_emoji(int(emoji_id))
                embed.set_footer(text=footer_text)
                embed.set_thumbnail(url=str(emoji_obj.url))
                await ctx.message.add_reaction(emoji_obj)
                await ctx.send(content=ctx.author.mention,embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if result_blackmarket_good != [] and result_blackmarket_good != ():
                # ==================================================================================================================================================
                if lng == 'ru':
                    title = 'Поиск предмета на черных рынках всех фракций'
                    embed = discord.Embed(title=title, color = color['green'])
                    embed_name = 'Детали запроса'
                    embed_value = f'Имя предмета: **{item_name}**\n'
                    if vetted_status == True: 
                        embed_value += f'Статус карьеры: **Подтвержденный**'
                        footer_text = 'Вы обладаете полным доступом к онлайн-магазину'
                    if vetted_status == False:
                        embed_value += f'Статус карьеры: __**не подтвержденный**__'
                        footer_text = 'Не подтвержденный статус означает ограниченный доступ к онлайн-магазину'  
                    embed.add_field(name=embed_name, value=embed_value, inline=False)
                    list_items = []
                    list_factions = []
                    list_i = []
                    i = 1
                    for row in result_blackmarket_good:
                        item_name = row['item_name']
                        faction = row['faction_full']
                        list_i.append(str(i))
                        list_items.append(item_name)
                        list_factions.append(faction)
                        i+=1
                        if i == 26: break
                    embed.add_field(name='Результаты выполнения запроса', value='Предметов найдено: '+str(len(result_blackmarket_good)), inline=False)
                    embed.add_field(name='#', value='\n'.join(list_i), inline=True)
                    embed.add_field(name='Имя предмета', value='\n'.join(list_items), inline=True)
                    embed.add_field(name='Фракция', value='\n'.join(list_factions), inline=True)
                    if i == 26:
                        embed.add_field(name='Слишком много предметов найдено!', value='Конкретезируй запрос и повтори попытку', inline=False)
                # ==================================================================================================================================================
                if lng == 'en':
                    title = 'Search for item in blackmarkets of all factions'
                    embed = discord.Embed(title=title, color = color['green'])
                    embed_name = 'Request details'
                    embed_value = f'Item name: **{item_name}**\n'
                    if vetted_status == True: 
                        embed_value += f'Career status: **vetted**'
                        footer_text = 'Vetted career status means full access to onlineshops'
                    if vetted_status == False:
                        embed_value += f'Career status: __**non vetted**__'
                        footer_text = 'Non vetted career status means limited access to onlineshops'  
                    embed.add_field(name=embed_name, value=embed_value, inline=False)
                    list_items = []
                    list_factions = []
                    list_i = []
                    i = 1
                    for row in result_blackmarket_good:
                        item_name = row['item_name']
                        faction = row['faction_full']
                        list_i.append(str(i))
                        list_items.append(item_name)
                        list_factions.append(faction)
                        i+=1
                        if i == 26: break
                    embed.add_field(name='Search result', value='Total items found count: '+str(len(result_blackmarket_good)), inline=False)
                    embed.add_field(name='#', value='\n'.join(list_i), inline=True)
                    embed.add_field(name='Item name', value='\n'.join(list_items), inline=True)
                    embed.add_field(name='Faction name', value='\n'.join(list_factions), inline=True)
                    if i == 26:
                        embed.add_field(name='Too many items found!', value='Make your request more specific and try again', inline=False)
                # ==================================================================================================================================================
                emoji_name = self.bot.emoji['piratethonk']
                emoji_id =''.join(i for i in emoji_name if i.isdigit())
                emoji_obj = self.bot.get_emoji(int(emoji_id))
                embed.set_footer(text=footer_text)
                embed.set_thumbnail(url=str(emoji_obj.url))
                await ctx.message.add_reaction(emoji_obj)
                await ctx.send(content=ctx.author.mention,embed=embed)
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def setfactionos(self,ctx,faction_name=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'setfactionos'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {faction_name=}',location=ctx.guild.name)
            await self.set_faction_by_market_type(ctx=ctx,market_type='onlineshop',faction_name=faction_name)
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def setfactionbm(self,ctx,faction_name=None):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'setfactionbm'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}" {faction_name=}',location=ctx.guild.name)
            await self.set_faction_by_market_type(ctx=ctx,market_type='blackmarket')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def delfactionos(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'delfactionos'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.del_faction_by_market_type(ctx=ctx,market_type='onlineshop')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def delfactionbm(self,ctx):
        try:
            if ctx.channel.id not in self.bot.allow_channels: return
            command_name = 'delfactionbm'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            await self.del_faction_by_market_type(ctx=ctx,market_type='blackmarket')
        except Exception as error:
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
    @commands.command()
    async def factionslist(self,ctx):
        try:
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            def list_chunks(lst):
                n = math.ceil(len(lst)/3)
                for x in range(0, len(lst), n):
                    e_c = lst[x : n + x]
                    if len(e_c) == n:
                        e_c = e_c + [None for y in range(n - len(e_c))]
                    yield e_c
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            lng = self.bot.allow_channels[ctx.channel.id]
            command_name = 'bmfindall'
            if lng == 'ru': footer_text = f'Для вызова справки по команде введи {self.bot.prefix}help {command_name}'
            if lng == 'en': footer_text = f'For additional help by command use  {self.bot.prefix}help {command_name}'
            self.LLC.addlog(f'[{ctx.author.name}] new command "{self.bot.prefix}{command_name}"',location=ctx.guild.name)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            if lng == 'ru':
                title = 'Список текущих игровых фракций'
                embed = discord.Embed(title=title, color = color['gray'])
                embed.set_footer(text=f'Используй короткое название для команд типа {self.bot.prefix}osfind')
            if lng == 'en':
                title = 'Current factions list'
                embed = discord.Embed(title=title, color = color['gray'])
                embed.set_footer(text=f'Use short faction name for commands like {self.bot.prefix}osfind')
            factions = []
            for short_name in self.bot.factions:
                factions.append({short_name:self.bot.factions[short_name]})
            list_short_names = list(list_chunks(factions))
            for short_names in list_short_names:
                lst_short = []
                lst_full = []
                lst_faction = []
                for faction_short in short_names:
                    for short in faction_short:
                        lst_short.append(short)
                        lst_full.append(faction_short[short])
                        faction_str = f'__{faction_short[short]}__\n{short}'
                        lst_faction.append(faction_str)
                if lng == 'ru':
                    embed.add_field(name='---', value='\n'.join(lst_faction) , inline=True)
                if lng == 'en':
                    embed.add_field(name='---', value='\n'.join(lst_faction), inline=True)
            await ctx.message.add_reaction('👍')
            await ctx.send(content=ctx.author.mention,embed=embed)
            return  
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            if lng == 'ru':
                msgtext  = f'Что-то пошло не так\n'
                msgtext += f'Если ошибка повторится свяжитесь с FURILKA#5953'
                title = self.bot.emoji['error']+' Ошибка'
            if lng == 'en':
                msgtext  = f'Something goes wrong\n'
                msgtext += f'If error persists please contact FURILKA#5953'
                title = self.bot.emoji['error']+' Error'
            embed = discord.Embed(title=title, description = msgtext, color = color['red'])
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            self.LLC.addlog(str(error),msg_type='error',location=ctx.guild.name)
    # **************************************************************************************************************************************************************
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(commands_common(bot))