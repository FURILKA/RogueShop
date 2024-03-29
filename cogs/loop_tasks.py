from asyncio.tasks import sleep
from discord.ext import commands
from discord.ext import tasks
from colors import color
import discord
import threading
import requests
import json
# ==================================================================================================================================================================
class loop_tasks(commands.Cog):
    # **************************************************************************************************************************************************************
    def __init__(self,bot):
        self.bot = bot
        self.LLC = bot.LLC
        self.mysql = bot.mysql
        # **********************************************************************************************************************************************************
        def load_factions():
            try:
                factions = {}
                result = self.bot.mysql.execute("SELECT * FROM factions_list")
                for row in result:
                    name_short = row['name_short']
                    name_full = row['name_full']
                    factions[name_short]=name_full
                self.bot.factions = factions
            except Exception as error:
                self.LLC.addlog(str(error),'error')       
        # **********************************************************************************************************************************************************
        self.LLC.addlog('Loading factions')
        load_factions()
        self.LLC.addlog('Factions loaded')
        # ----------------------------------------------------------------------------------------------------------------------------------------------------------
        self.LLC.addlog(f'bot launch type: {self.bot.launch_type}')
        if self.bot.launch_type == 'main_build':
            self.LLC.addlog('Running RogueWar API-token update function')
            self.roguewar_token_update.start()
            self.LLC.addlog('Running Factions list update function')
            self.factions_list_update.start()
            self.LLC.addlog('Running Onlineshops update function')
            self.onlineshop_update.start()
            self.LLC.addlog('Running Blackmarkets update function')
            self.blackmarket_update.start()
            self.LLC.addlog('Running checking expiration of requests')
            self.check_for_expire_requests.start()
            self.LLC.addlog('Logger started')
            self.export_logs.start()
        else:
            self.LLC.addlog('This is dev build')
            self.LLC.addlog('RogueWar API-token update skipped')
            self.LLC.addlog('Factions list update skipped')
            self.LLC.addlog('Onlineshops update skipped')
            self.LLC.addlog('Blackmarkets update skipped')
            self.LLC.addlog('Сecking expiration of requests skipped')
        # ----------------------------------------------------------------------------------------------------------------------------------------------------------
        self.LLC.addlog('Running check for items in markets')
        self.check_for_items_in_markets.start()
    # **************************************************************************************************************************************************************
    # updating factions list
    @tasks.loop(count=1)
    async def factions_list_update(self):
        try:
            self.LLC.addlog('Updating factions list')
            url = self.bot.rogue_mainsite + '/api/factions'
            response = requests.get(url,headers={'Authorization':f'Bearer {self.bot.roguewar_token}'})
            values = []
            factions = {}
            if response.status_code == 200:
                json_Factions = json.loads(response.text)
                for faction in json_Factions['FactionList']:
                    if faction['ShopAvailable'] == True:
                        faction_short = faction['Name'].lower()
                        faction_full = faction['DisplayName']
                        values.append(f"('{faction_short}','{faction_full}')")
                        if not faction_short in factions:
                            factions[faction_short]=faction_full
            self.bot.mysql.execute('TRUNCATE TABLE factions_list')
            self.bot.mysql.execute("INSERT INTO factions_list (name_short,name_full) VALUES " + ','.join(values))
            self.LLC.addlog('Faction list updated succesfully')
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
    # update token for auth in Roguewar-API: http://roguewar.org/api/
    @tasks.loop(hours=1,reconnect=True)
    async def roguewar_token_update(self):
        try:
            url = self.bot.rogue_mainsite + 'api/botauth'
            response = requests.post(url,json={"botName":"RogueShop","botSecret":f"{self.bot.bot_api_secret}"})
            if str(response) == '<Response [200]>':
                token = json.loads(response.text)['access_token']
                self.bot.roguewar_token = token
            else:
                self.bot.LLC.addlog(f'botauth response = {response}',msg_type='error',location='api/botauth')
                self.bot.LLC.addlog(f'Cant update botauth token!',msg_type='error',location='api/botauth')
                self.bot.roguewar_token = ''
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error',location='api/botauth')
            self.bot.LLC.addlog(f'Cant update botauth token!',msg_type='error',location='api/botauth')
            self.bot.roguewar_token = ''
    # **************************************************************************************************************************************************************
    @tasks.loop(minutes=1,reconnect=True)
    async def onlineshop_update(self):
        # **********************************************************************************************************************************************************
        def onlineshop_update_thread(self):
            try:
                if self.bot.roguewar_token == '':
                    self.bot.LLC.addlog('roguewar access token is missing, aborting update shops info','error')
                    return
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # getting shop info for each faction
                #self.LLC.addlog('Updating onlineshop information')
                shops_info = {}
                for faction_short in self.bot.factions:
                    shops_info[faction_short]=[]
                    url = f'{self.bot.rogue_mainsite}api/shop/{faction_short}?blackMarket=0'
                    response = requests.get(url,headers={'Authorization':f'Bearer {self.bot.roguewar_token}'})
                    if response.status_code == 200:
                        json_OnlineShopData = json.loads(response.text)
                        for item in json_OnlineShopData['ShopContents']:
                            item_name = item['Name'].replace('\'','\\\'')
                            item_count = item['Count']
                            item_for_non_vets = item['AvailableToNonVets']
                            shops_info[faction_short].append(
                                {'item_name':item_name,
                                'item_count': item_count,
                                'faction_full':self.bot.factions[faction_short],
                                'for_non_vets': item_for_non_vets})
                    else:
                        self.bot.logger.addlog(f'cant update "{faction_short}" online shop info, server response code = {str(response.status_code)}')
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # creating query for inser all data
                if shops_info == {}: return
                values = []
                for faction_short in shops_info:
                    faction_shop = shops_info[faction_short]
                    for item_info in faction_shop:
                        faction_full = item_info['faction_full']
                        item_name = item_info['item_name']
                        item_count = item_info['item_count']
                        item_for_non_vets = item_info['for_non_vets']
                        values.append(f"('{faction_short}','{faction_full}','{item_name}',{item_count},{item_for_non_vets})")
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # inserting data
                if values == []: return
                self.bot.mysql.execute("TRUNCATE TABLE goods_onlineshop")
                query = "INSERT INTO goods_onlineshop (faction_short,faction_full,item_name,item_count,for_non_vets) VALUES " + ','.join(values)
                self.bot.mysql.execute(query)
                #self.LLC.addlog('Onlineshop information updated')
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
            except Exception as error:
                if url != 'url': print(f'{url=}')
                if response != '': print(f'{response=}')
                if response.text != '': print(f'{response.text=}')
                self.bot.logger.adderrorlog()
        # **********************************************************************************************************************************************************
        try:
            if self.bot.roguewar_token == '':
                self.bot.LLC.addlog('roguewar access token is missing!','warning')
                self.bot.LLC.addlog('trying to get new roguewar access token','warning')
                await self.roguewar_token_update()
                if self.bot.roguewar_token == '':
                    self.bot.LLC.addlog('roguewar access token still missing!','error')
                    return
                self.bot.LLC.addlog('roguewar access token updated succesfull','warning')
            thread = threading.Thread(target=onlineshop_update_thread,args=(self,))
            thread.start()
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
    @tasks.loop(minutes=1,reconnect=True)
    async def blackmarket_update(self):
        # **********************************************************************************************************************************************************
        def blackmarket_update_thread(self):
            try:
                if self.bot.roguewar_token == '':
                    self.bot.LLC.addlog('roguewar access token is missing, aborting update shops info','error')
                    return
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # getting shop info for each faction
                #self.LLC.addlog('Updating blackmarket information')
                shops_info = {}
                for faction_short in self.bot.factions:
                    shops_info[faction_short]=[]
                    url = f'{self.bot.rogue_mainsite}api/shop/{faction_short}?blackMarket=1'
                    response = requests.get(url,headers={'Authorization':f'Bearer {self.bot.roguewar_token}'})
                    if response.status_code == 200:
                        json_OnlineShopData = json.loads(response.text)
                        for item in json_OnlineShopData['ShopContents']:
                            item_name = item['Name'].replace('\'','\\\'')
                            item_count = item['Count']
                            item_for_non_vets = item['AvailableToNonVets']
                            shops_info[faction_short].append(
                                {'item_name':item_name,
                                'item_count': item_count,
                                'faction_full':self.bot.factions[faction_short],
                                'for_non_vets': item_for_non_vets})
                    else:
                        self.bot.logger.addlog(f'cant update "'+ self.bot.factions[faction_short] + '" blackmarket info, server response code = ' + str(response.status_code))
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # creating query for inser all data
                if shops_info == {}: return
                values = []
                for faction_short in shops_info:
                    faction_shop = shops_info[faction_short]
                    for item_info in faction_shop:
                        faction_full = item_info['faction_full']
                        item_name = item_info['item_name']
                        item_count = item_info['item_count']
                        item_for_non_vets = item_info['for_non_vets']
                        values.append(f"('{faction_short}','{faction_full}','{item_name}',{item_count},{item_for_non_vets})")
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
                # inserting data
                if values != []:
                    self.bot.mysql.execute("TRUNCATE TABLE goods_blackmarket")
                    query = "INSERT INTO goods_blackmarket (faction_short,faction_full,item_name,item_count,for_non_vets) VALUES " + ','.join(values)
                    self.bot.mysql.execute(query)
                #self.LLC.addlog('Blackmarket information updated')
                # ------------------------------------------------------------------------------------------------------------------------------------------------------
            except Exception as error:
                if url != 'url': print(f'{url=}')
                if response != '': print(f'{response=}')
                if response.text != '': print(f'{response.text=}')
                self.bot.logger.adderrorlog()
        # **********************************************************************************************************************************************************
        try:
            if self.bot.roguewar_token == '':
                self.bot.LLC.addlog('roguewar access token is missing!','warning')
                self.bot.LLC.addlog('trying to get new roguewar access token','warning')
                await self.roguewar_token_update()
                if self.bot.roguewar_token == '':
                    self.bot.LLC.addlog('roguewar access token still missing!','error')
                    return
                self.bot.LLC.addlog('roguewar access token updated succesfull','warning')
            thread = threading.Thread(target=blackmarket_update_thread,args=(self,))
            thread.start()
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
    @tasks.loop(minutes=3,reconnect=True)
    async def export_logs(self):
        try:
            self.bot.LLC.export()
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
    @tasks.loop(seconds=15,reconnect=True)
    async def check_for_items_in_markets(self):
        try:
            try:
                emoji_name = self.bot.emoji['coins']
            except:
                return
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            query_list = {}
            market_types = ['onlineshop','blackmarket']
            for market_type in market_types:
                query_non_vett_players = f"""
                    SELECT
                        request.id as 'row_id',
                        request.user_id,
                        request.user_name,
                        request.channel_id,
                        request.faction_name_full AS 'faction',
                        request.item_name AS 'request_item_name',
                        shop.item_name AS 'found_item_name',
                        shop.item_count
                    FROM 
                        goods_{market_type} shop,
                        requests request
                    WHERE 
                        shop.faction_short = request.faction_name_short
                    AND
                        LOWER(shop.item_name) LIKE CONCAT('%',request.item_name,'%')
                    AND
                        request.status = 'in progress'
                    AND
                        shop.item_count != '0'
                    AND
                        request.user_is_vetted = 0
                    AND
                        shop.for_non_vets = 1
                    AND
                        request.market_type = '{market_type}'
                    """
                query_vett_players = f"""
                    SELECT 
                        request.id as 'row_id',
                        request.user_id,
                        request.user_name,
                        request.channel_id,
                        request.faction_name_full AS 'faction',
                        request.item_name AS 'request_item_name',
                        shop.item_name AS 'found_item_name',
                        shop.item_count
                    FROM 
                        goods_{market_type} shop,
                        requests request
                    WHERE 
                        shop.faction_short = request.faction_name_short
                    AND
                        LOWER(shop.item_name) LIKE CONCAT('%',request.item_name,'%')
                    AND
                        request.status = 'in progress'
                    AND
                        shop.item_count != '0'
                    AND
                        request.user_is_vetted = 1
                    AND
                        request.market_type = '{market_type}'
                    """
                query_list[market_type] = [query_non_vett_players,query_vett_players]
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
            list_row_id_to_close_request = []
            for market_type in market_types:
                found_items_by_user_id = {}
                for query in query_list[market_type]:
                    result = self.bot.mysql.execute(query)
                    if result == [] or result == (): continue
                    for row in result:
                        user_name = row['user_name']
                        item_name = row['found_item_name']
                        self.LLC.addlog(
                            msg_text=f'[{user_name}] found item: {item_name}',
                            msg_type='info',
                            location='shop_check')
                        list_row_id_to_close_request.append(str(row['row_id']))
                        user_id = row['user_id']
                        if not user_id in found_items_by_user_id: found_items_by_user_id[user_id]=[]
                        found_items_by_user_id[user_id].append({
                            'channel_id': row['channel_id'],
                            'row_id': row['row_id'],
                            'request_item_name': row['request_item_name'],
                            'found_item_name': row['found_item_name'],
                            'item_count': row['item_count'],
                            'faction': row['faction']})
                for user_id in found_items_by_user_id:
                    rows_by_channel = {}
                    for row in found_items_by_user_id[user_id]:
                        channel_id = row['channel_id']
                        if channel_id not in rows_by_channel: rows_by_channel[channel_id] = []
                        rows_by_channel[channel_id].append({
                            'row_id': row['row_id'],
                            'request_item_name': row['request_item_name'],
                            'found_item_name': row['found_item_name'],
                            'item_count': row['item_count'],
                            'faction': row['faction']
                        })
                    for channel_id in rows_by_channel:
                        lng = self.bot.allow_channels[channel_id]
                        channel = self.bot.get_channel(channel_id)
                        list_i = []
                        list_request_item_name = []
                        list_found_item_name = []
                        list_item_count = []
                        list_faction = []
                        i = 1
                        for row in rows_by_channel[channel_id]:
                            list_i.append(str(i))
                            list_request_item_name.append(row['request_item_name'])
                            list_found_item_name.append('__'+row['found_item_name']+'__')
                            list_item_count.append(row['item_count'])
                            list_faction.append(row['faction'])
                            i+=1
                            if i == 26: break
                        # ==================================================================================================================================================
                        if lng == 'ru':
                            if market_type == 'onlineshop':
                                title = 'В онлайн-магазине найдены предметы по запросу'
                            if market_type == 'blackmarket':
                                title = 'На черном рынке найдены предметы по запросу'
                            embed = discord.Embed(title=title, color = color['yellow'])
                            if len(rows_by_channel[channel_id])>1:
                                embed.add_field(name='Результаты поиска', value='Предметов найдено: '+str(len(rows_by_channel[channel_id])), inline=False)
                            embed.add_field(name='Найдено', value='\n'.join(list_found_item_name), inline=True)
                            embed.add_field(name='Запрос', value='\n'.join(list_request_item_name), inline=True)
                            embed.add_field(name='Фракция', value='\n'.join(list_faction), inline=True)
                            if i == 26:
                                embed.add_field(name='Слишком много предметов найдено!', value='Конкретезируй запрос и повтори попытку', inline=False)
                        # ==================================================================================================================================================
                        if lng == 'en':
                            if market_type == 'onlineshop':
                                title = 'Items found on request in onlineshop'
                            if market_type == 'blackmarket':
                                title = 'Items found on request in blackmarket'
                            embed = discord.Embed(title=title, color = color['yellow'])
                            if len(rows_by_channel[channel_id]) > 1:
                                embed.add_field(name='Search result', value='Total items found count: '+str(len(rows_by_channel[channel_id])), inline=False)
                            embed.add_field(name='Item found', value='\n'.join(list_found_item_name), inline=True)
                            embed.add_field(name='Request', value='\n'.join(list_request_item_name), inline=True)
                            embed.add_field(name='Faction', value='\n'.join(list_faction), inline=True)
                            if i == 26:
                                embed.add_field(name='Too many items found!', value='Make your request more specific and try again', inline=False)
                        # ==================================================================================================================================================
                        emoji_id =''.join(i for i in emoji_name if i.isdigit())
                        emoji_obj = self.bot.get_emoji(int(emoji_id))
                        #embed.set_footer(text=footer_text)
                        embed.set_thumbnail(url=str(emoji_obj.url))
                        await channel.send(content=f'<@{user_id}>',embed=embed)
            if list_row_id_to_close_request != []:
                query = f"""UPDATE requests SET status = 'complete' WHERE id = {' or id = '.join(list_row_id_to_close_request)}"""
                self.bot.mysql.execute(query)
            # ------------------------------------------------------------------------------------------------------------------------------------------------------
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
    @tasks.loop(hours=1,reconnect=True)
    async def check_for_expire_requests(self):
        try:
            query = """
                UPDATE 
                    requests 
                SET 
                    status = 'expire'
                WHERE 
                        status = 'in progress' 
                    AND 
                        DATE_ADD(date_add,INTERVAL 3 DAY) < NOW()"""
            self.bot.mysql.execute(query)
        except Exception as error:
            self.bot.LLC.addlog(str(error),msg_type='error')
    # **************************************************************************************************************************************************************
# ==================================================================================================================================================================
def setup(bot):
    bot.add_cog(loop_tasks(bot))