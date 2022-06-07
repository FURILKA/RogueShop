import datetime
from configurator import configurator
import traceback
import pymysql
import inspect
import random
import os
import traceback
import random
import string
import inspect
import json
import time
import sys
# ==================================================================================================================================================================
# Класс "LocalLogCollector" (сокращенно LLC)
# При создании генерирует рандомный ID сиссии, далее собирает локальную коллекцию логов. Каждый элемент коллекции содержит:
# 1) Время события
# 2) Рандомный ID сессии в виде ХХХХ-ХХХХ-ХХХХ-ХХХХ (где Х рандомная цифра 0-9), генерируется при запуске бота и действует всё время до перезапуска
# 3) Тип события. По умолчанию 'info', может быть 'error', 'warning' и т.д.
# 4) Тест сообщения/лога
# 5) Название функции-отправителя лога
# 6) Название модуля-отправителя лога
# После сбора коллекции её необходимо отправить на сервер. Если этого не сделать - логи будут потеряны
# Автоматически отправляет логи на сервер в том случае, если в коллекции собирается 100+ событий ИЛИ если type == 'error'
# ==================================================================================================================================================================
class LocalLogCollector(object):
    # **************************************************************************************************************************************************************
    """Класс для локальной агрегации логов работы скрипта и последующем экспорте логов на сервер"""
    def __init__(self):
        """Инициализация класса"""
        self.logs_collection = []
        self.SessionID = str(random.random())[2:6]+'-'+str(random.random())[2:6]+'-'+str(random.random())[2:6]
    # **************************************************************************************************************************************************************
    def addlog(self, msg_text='',msg_type='info',location='general'):
        """Добавление лога в коллекцию"""
        try:
            current_frame = inspect.currentframe()
            caller_frame = current_frame.f_back
            code_obj = caller_frame.f_code
            function_name = code_obj.co_name  
            lib_name = code_obj.co_filename.split('\\')[-1]
            msg_id = self.SessionID
            self.logs_collection.append(
                {
                'id': msg_id,
                'message': msg_text,
                'location': location,
                'type': msg_type,
                'date': str(datetime.datetime.now())[0:19],
                'lib_name': lib_name,
                'function_name': function_name
                })
            val = msg_text
            if type(val) != str: val = str(val)
            now = str(datetime.datetime.now())[0:19].replace('-','.')
            if msg_type == 'info':
                if location == 'general':
                    print(f'[{now}] [{self.SessionID}] [info] {val}')
                else:
                    print(f'[{now}] [{self.SessionID}] [info] [loc:"{location}"] {val}')
            else:
                print(f'[{now}] [{self.SessionID}] [{msg_type}] [loc:"{location}"] [lib:"{lib_name}"] [fnc:"{function_name}"] {val}')
            if msg_type != 'info' or len(self.logs_collection)>20:
                self.export()
        except Exception as ex:
            print(str(ex))
    # **************************************************************************************************************************************************************
    def export(self):
        """Экспорт локальных логов на сервер логирования"""
        try:
            if len(self.logs_collection)>0:
                rows_to_delete = []
                values = ''
                for row in self.logs_collection:
                    rows_to_delete.append(row)
                    msg_text = row['message']
                    msg_text = msg_text.replace("'","\\'")
                    values += "('"+row['id']+"','"+str(row['date'])+"','"+row['location']+"','"+row['type']+"','"+row['lib_name']+"','"+row['function_name']+"','"+msg_text+"'),"
                values = values[0:-1]
                config = configurator(os.path.dirname(os.path.realpath(__file__))+"\config\config.ini")
                sqlCon = pymysql.connect(
                    host = config.get(section='mySQL',setting='host'),
                    user = config.get(section='mySQL',setting='user'),
                    password = config.get(section='mySQL',setting='pass'),
                    db = config.get(section='mySQL',setting='base'),
                    cursorclass = pymysql.cursors.DictCursor
                    )
                sqlCur = sqlCon.cursor()
                query = 'INSERT INTO bot_logs(session_id,date,location,type,library,function,message) VALUES ' + values
                sqlCur.execute(query)
                sqlCon.commit()
                sqlCon.close()
                for row in rows_to_delete:
                    self.logs_collection.remove(row)
        except Exception as ex:
            print(str(ex))
    def adderrorlog(self):
        str_traceback = str(traceback.format_exc())
        if str_traceback == '' or str_traceback == None: return
        list_traceback = str_traceback.split('\n')
        code_obj = inspect.currentframe().f_back.f_code
        fnc_name = code_obj.co_name  
        lib_name = code_obj.co_filename.split('\\')[len(code_obj.co_filename.split('\\'))-1].split('/')[-1]
        list_traceback.remove('')
        str_error = list_traceback[-1]
        log_message = self.__create_log_message__(
            msg_text=str_error,
            msg_type='error',
            lib_name=lib_name,
            fnc_name=fnc_name)
        self.__add_log_to_collection__(log_message)
        self.__print_log__(log_message)
        for line_traceback in list_traceback:
            log_message = self.__create_log_message__(
                msg_text=line_traceback,
                msg_type='traceback',
                lib_name=lib_name,
                fnc_name=fnc_name)
            self.__add_log_to_collection__(log_message)
            self.__print_log__(log_message)
# ==================================================================================================================================================================

# =====================================================================================================================================================================
class botlogger(object):
    # Локальный коллектор логов, отправка собранной коллекции логов с RabbitMQ
    '''
    Класс для логирования событий и отправки логов в хранилище (БД "ClickHouse") через RabbitMQ или напрямую
    
    При создании экземпляра класса следует передать следующие аргументы:
    
    > dict_creds_rabbit
    > dict_creds_clickhouse
    > send_method

    "dict_creds_rabbit" : словарь, содержащий креды для доступа к RabbitMQ
    > если не указать - при попытке отправки сообщения в RabbitMQ будет выведено сообщение об ошибке, логи не будут отправлены
    > должен содержать следующие ключи (и их значения:)
        - host
        - port
        - username
        - password
        - virtual_host
        - exchange_name
        - exchange_type

    "dict_creds_clickhouse" : словарь, содержащий креды для доступа к ClickHouse
    > если не указать - при попытке отправки сообщения в ClickHouse будет выведено сообщение об ошибке, логи не будут отправлены
    > должен содержать следующие ключи (и их значения:)
        - host
        - port
        - username
        - password
        - database
        - table

    "send_method" : метод отправки логов в хранилище
    > опционально, по-умолчанию == None (логи в хранилище отправляться не будут)
    > может содержать одно из нижеуказанных значений типа string:
        1) "rabbit": логи будут отправляться ТОЛЬКО в RabbitMQ
        2) "clickhouse": логи будут отправляться ТОЛЬКО в ClickHouse
        3) "rabbit+clickhouse": логи будут сначала отправляться в RabbitMQ, а в случае ошибки напрямую в ClickHouse
    > для каждого метода отправки нужно указывать соответствующие креды
    '''
    # *****************************************************************************************************************************************************************
    def __init__(self,session_id = None):
        self.session_id = self.__generate_session_id__() if session_id == None else session_id
        self.logs_collection = []
        self.logs_index = 0
    # *****************************************************************************************************************************************************************
    # Генерация ID текущей сессии логов: запускается 1 раз в момент инициализации класса
    def __generate_session_id__(self):
        try:
            # Генерируем session_id состоящий из 8 латинских символов в верхнем регистре и 4 цифр, всего 3 блока символов по 4шт, разделенных через "-"
            # Пример сгенерированного id: NUIV-DUXW-3825
            session_id = '-'.join([''.join([random.choice(string.ascii_uppercase) for y in range(4)]) for y in range(2)])+'-'+str(random.random())[2:6]
            return(session_id)
        except Exception as error:
            print(f'session id generation error: {error}')
    # *****************************************************************************************************************************************************************
    # Создание словоря с сообщением лога
    def __create_log_message__(self,msg_text,msg_type,lib_name,fnc_name):
        dt = datetime.datetime
        tz = datetime.timezone
        td = datetime.timedelta
        dt_now = dt.now(tz=tz(td(hours=3),name='Europe/Moscow'))
        dt_now_ydm = dt_now.strftime('%Y-%m-%d %H:%M:%S')
        dt_now_dmy = dt_now.strftime('%d.%m.%Y %H:%M:%S')
        uts = round(dt_now.timestamp() * 10**3)
        log_message = {
            'is_sent': 0,
            'uts': uts,
            'session_id': self.session_id,
            'date_now': dt_now,
            'date_ymd': dt_now_ydm,
            'date_dmy': dt_now_dmy,
            'msg_text': msg_text,
            'msg_type': msg_type,
            'lib_name': lib_name,
            'fnc_name': fnc_name}
        return(log_message)
    # *****************************************************************************************************************************************************************
    # Принтует переданное сообщение в консоль
    def __print_log__(self,log_message):
        date_dmy = log_message['date_dmy']
        msg_type = log_message['msg_type']
        msg_text = log_message['msg_text']
        lib_name = log_message['lib_name']
        fnc_name = log_message['fnc_name']
        print(f'[{date_dmy}] [{self.session_id}] [{msg_type}] {msg_text} [fnc="{fnc_name}"][lib="{lib_name}"]')
    # *****************************************************************************************************************************************************************
    # Добавляет переданное сообщение в коллекцию логов
    def __add_log_to_collection__(self,log_message):
        self.logs_index += 1
        logs_index = self.logs_index
        log_message['index'] = logs_index
        self.logs_collection.append(log_message)
        time.sleep(0.000001)
    # *****************************************************************************************************************************************************************
    # Создание нового лога (создаёт сообщение лога + добавляет его в коллекцию + принтует в консоль)
    def addlog(self,msg_text='',msg_type='info',print_msg=True):
        code_obj = inspect.currentframe().f_back.f_code
        fnc_name = code_obj.co_name  
        lib_name = code_obj.co_filename.split('\\')[len(code_obj.co_filename.split('\\'))-1].split('/')[-1]
        msg_text = str(msg_text)
        log_message = self.__create_log_message__(
            msg_text=msg_text,
            msg_type=msg_type,
            lib_name=lib_name,
            fnc_name=fnc_name)
        self.__add_log_to_collection__(log_message)
        if print_msg == True:
            self.__print_log__(log_message)
    # *****************************************************************************************************************************************************************
    # Добавляет в логи сообщения о текущих ошибках (если они есть), использовать в секции Except...
    def adderrorlog(self,result={}):
        str_traceback = str(traceback.format_exc())
        if str_traceback == '' or str_traceback == None: return
        list_traceback = str_traceback.split('\n')
        code_obj = inspect.currentframe().f_back.f_code
        fnc_name = code_obj.co_name  
        lib_name = code_obj.co_filename.split('\\')[len(code_obj.co_filename.split('\\'))-1].split('/')[-1]
        list_traceback.remove('')
        str_error = list_traceback[-1]
        log_message = self.__create_log_message__(
            msg_text=str_error,
            msg_type='error',
            lib_name=lib_name,
            fnc_name=fnc_name)
        self.__add_log_to_collection__(log_message)
        self.__print_log__(log_message)
        for line_traceback in list_traceback:
            log_message = self.__create_log_message__(
                msg_text=line_traceback,
                msg_type='traceback',
                lib_name=lib_name,
                fnc_name=fnc_name)
            self.__add_log_to_collection__(log_message)
            self.__print_log__(log_message)
        if 'result' in result: result['result']='error'
        if 'errors' in result: result['errors'].append(str_error)
        if result != {}: return(result)
    # *****************************************************************************************************************************************************************
    # Возвращает текущую (последнюю) ошибку
    def geterrortext(self):
        str_traceback = str(traceback.format_exc())
        if str_traceback == '' or str_traceback == None: return
        list_traceback = str_traceback.split('\n')
        if list_traceback == [] or list_traceback == None: return
        list_traceback.remove('')
        str_error = list_traceback[-1]
        return(str_error)
    # *****************************************************************************************************************************************************************
    def getlogs(self,log_index):
        result_list = []
        if int(log_index) <= 0: return([])
        for message in self.logs_collection:
            if message['index'] > int(log_index):
                result_list.append(message)
        return(result_list)
    # *****************************************************************************************************************************************************************
    # Декоратор для функций: логирует начало и окончание работы функции, аргументы функции (если они переданы), а так же время работы функции
    def log_function(self,log_args=False,log_result=False):
        def decorator(function):
            def wrapper(**kwargs):
                # Получаем инфу о том, откуда (какой либы и функции) вызван декоратор
                code_obj = inspect.currentframe().f_back.f_code
                fnc_name = function.__name__
                lib_name = code_obj.co_filename.split('\\')[len(code_obj.co_filename.split('\\'))-1].split('/')[-1]
                # Создаём лог о том, что функция стартует + засекаем время старта
                log_text = f'function "{fnc_name}" started'
                if kwargs == {} and log_args == True: log_text += ' with no args'
                if kwargs != {} and log_args == True: log_text += ' with args'
                log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                self.__add_log_to_collection__(log_message)
                self.__print_log__(log_message)
                # Если требуется логировать в т.ч. аргументы функции (и они есть) сделаем это
                if log_args == True:
                    for arg_name in kwargs:
                        arg_type = str(type(kwargs[arg_name])).replace("<class '",'"')[0:-2]+'"'
                        arg_value_str = str(kwargs[arg_name])
                        log_text = f'arg "{arg_name}" (type={arg_type}) == "{arg_value_str}"'
                        log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                        self.__add_log_to_collection__(log_message)
                        self.__print_log__(log_message)
                # Начинаем отсчет времени работы функции
                d1 = datetime.datetime.now()
                # Запускаем декорируемую (логируемую) функцию
                function_result = function(**kwargs)
                # Завершаем отсчет времени работы функции
                d2 = datetime.datetime.now()
                # Получаем разницу (время работы функции)
                dd = d2-d1
                # Если там есть микросекунды (6 знаков после ",") - округляем их до милисекунд (3 знака после ",")
                ddstr = str(dd)[0:len(str(dd))-3] if '.' in str(dd) else str(dd)
                # Логируем завершение работы функции + время на выполнение функции
                log_text = f'function "{fnc_name}" done for {ddstr}'
                log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                self.__add_log_to_collection__(log_message)
                self.__print_log__(log_message)
                # Логируем результат выполнения функции:
                if log_result == True:
                    result_type_str = str(type(function_result)).replace("<class '",'')[0:-2]
                    result_text_str = str(function_result)
                    log_text = f'function "{fnc_name}" result (type="{result_type_str}") == "{result_text_str}"'
                    log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                    self.__add_log_to_collection__(log_message)
                    self.__print_log__(log_message)
                # Возвращаем результат работы функции
                return(function_result)
            return(wrapper)
        return(decorator)
    # *****************************************************************************************************************************************************************
    # Декоратор для "главной" функции модуля: логирует начало и окончание работы модуля, а так же общее время работы модуля
    def log_module(self):
        def decorator(function):
            def wrapper(**kwargs):
                code_obj = inspect.currentframe().f_back.f_code
                fnc_name = function.__name__
                lib_name = code_obj.co_filename.split('\\')[len(code_obj.co_filename.split('\\'))-1].split('/')[-1]
                log_text = f'module "{lib_name}" started'
                log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                self.__add_log_to_collection__(log_message)
                self.__print_log__(log_message)
                # Начинаем отсчет времени работы модуля
                d1 = datetime.datetime.now()
                # Запускаем декорируемую функцию
                function_result = function(**kwargs)
                # Завершаем отсчет времени работы функции
                d2 = datetime.datetime.now()
                # Получаем разницу (время работы модуля)
                dd = d2-d1
                # Если там есть микросекунды (6 знаков после ",") - округляем их до милисекунд (3 знака после ",")
                ddstr = str(dd)[0:len(str(dd))-3] if '.' in str(dd) else str(dd)
                # Логируем завершение работы функции + время на выполнение функции
                log_text = f'module "{lib_name}" done for {ddstr}'
                log_message = self.__create_log_message__(msg_text=log_text,msg_type='info',lib_name=lib_name,fnc_name=fnc_name)
                self.__add_log_to_collection__(log_message)
                self.__print_log__(log_message)
                return(function_result)
            return(wrapper)
        return(decorator)
    # *****************************************************************************************************************************************************************
    # Отправка логов в хранилище
    def export_logs(self,sendall=False):
        result = {'result':[],'errors':[]}
        try:
            # =========================================================================================================================================================
            # Проверяем, задан ли метод отправки логов. Если не задан: сообщим об ошибке
            if self.__send_method__ == None:
                error_text = 'unable to export logs: sending method not definded ("send_method" param == None)'
                self.addlog(msg_text=error_text,msg_type='error')
                result['result']='error'
                result['errors'].append(error_text)
                return(result)
            # =========================================================================================================================================================
            # Проверяем, указан ли КОРРЕКТНЫЙ метод отправки логов, если нет: сообщим об ошибке
            if str(self.__send_method__).lower() not in self.__available_sending_methods__:
                str_available_sending_methods = ', '.join(self.__available_sending_methods__)
                error_text = f'wrong logs sending method: {str(self.__send_method__).lower()}'
                self.addlog(msg_text=error_text,msg_type='error')
                self.addlog(msg_text=f'available sending methods: {str_available_sending_methods}',msg_type='error')
                result['result']='error'
                result['errors'].append(error_text)
                return(result)
            # =========================================================================================================================================================
            logs_collection_to_send = []
            for message in self.logs_collection:
                if sendall == False:
                    if message['is_sent'] != 1 and message['session_id'] == self.session_id:
                        logs_collection_to_send.append(message)
                else:
                    if message['is_sent'] != 1:
                        logs_collection_to_send.append(message)
            if logs_collection_to_send == []: 
                result['result']='nothing to export'
                return(result)
        # ========================================================================================================================================================
        # Обработка ошибок
        except Exception as error:
            result['result']='error'
            result['errors'].append(str(error))
            self.addlog(msg_text=str(error),msg_type='error')
            for traceback_line in str(traceback.format_exc()).split('\n'):
                if traceback_line != '': self.addlog(msg_text=traceback_line,msg_type='traceback')
            return(result)
# *********************************************************************************************************************************************************************

if __name__ == "__main__":
    pass