import os
import shutil
from aiogram import Bot, types, Dispatcher, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils import UserStates
import aioschedule
import asyncio
import mariadb
from deepface import DeepFace

TOKEN = ''
PHOTO_DIR = "\\\\192.168.100.144\\surveillance\\@Snapshot\\"
NEW_DIR = "C:\\PhotoRepos\\"
Neraspr_dir = "C:\\NerasprDir\\"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
conn = mariadb.connect(user="anton",
                       password="2Azxcvbnm",
                       host="192.168.2.2",
                       port=3307,
                       database="bot_hr")
cur = conn.cursor()


async def main_work():
    print("Okay lets go")
    # Проверяем директорию на доступность
    if not os.path.exists(PHOTO_DIR):
        print("Директория недоступна!")
        return

    for root, dirs, files in os.walk(PHOTO_DIR):
        for file in files:
            # Удаляем файлы где нет лиц
            try:
                embedding = DeepFace.represent(img_path=PHOTO_DIR + file)

                for root, dirs, files in os.walk(NEW_DIR):
                    for dir in dirs:
                        # Берем файлы по порядку и проходимся по всем папкам с известным нам людям
                        df = DeepFace.find(img_path=PHOTO_DIR + file, db_path=NEW_DIR + dir, model_name="Facenet")
                        # Если есть совпадения по фото
                        if len(df.values.tolist()) > 0:
                            # Если в папке всего одно фото
                            if len([f for f in os.listdir(NEW_DIR + dir) if
                                    os.path.isfile(os.path.join(NEW_DIR + dir, f))]) == 1:
                                newname = dir + '!' + file
                                os.rename(PHOTO_DIR + file, PHOTO_DIR + newname)
                                shutil.move(PHOTO_DIR + newname, Neraspr_dir)
                                break
                            # Если половина или больше фото совпадают перемещаем фото туда
                            elif len(df.values.tolist()) >= len([f for f in os.listdir(NEW_DIR + dir) if
                                                                 os.path.isfile(os.path.join(NEW_DIR + dir, f))]) / 2:
                                datetime = file[9:17] + file[18:24]
                                newname = dir + '!' + file
                                os.rename(PHOTO_DIR + file, PHOTO_DIR + newname)
                                shutil.move(PHOTO_DIR + newname, Neraspr_dir)
                                cur.execute("Insert into Fotos (ID, Time, Worker) values (?, ?, ?)", (newname, datetime, dir))
                                conn.commit()
                                break
                shutil.move(PHOTO_DIR + file, Neraspr_dir)
            except Exception as err:
                print(err)
                os.remove(PHOTO_DIR + file)


#Распределяем фотографии
@dp.message_handler(commands=['raspr'], state='*')
async def raspr_photos(message: types.Message):
    for root, dirs, files in os.walk(Neraspr_dir):
        if not files:
            await bot.send_message(message.from_user.id, "Нет нераспределенных фотографий")
            break
        for file in files:
            state = dp.current_state(user=message.from_user.id)
            await state.set_state(UserStates.all()[0])
            await bot.send_message(message.from_user.id, text=f"Всего {len(files)}")
            button = InlineKeyboardButton('Правильно',
                                          callback_data=file)
            button1 = InlineKeyboardButton('Неправильно', callback_data='photo_not_right')
            kb = InlineKeyboardMarkup().add(button).add(button1)
            await bot.send_photo(message.from_user.id, photo=open(Neraspr_dir + file, 'rb'))
            await bot.send_message(message.from_user.id, text=file,
                                   reply_markup=kb)
            break


#Распределяем фотографии
@dp.callback_query_handler(lambda c: c.data == 'raspr_photo_next', state='*')
async def raspr_photos_next(query: types.CallbackQuery):
    for root, dirs, files in os.walk(Neraspr_dir):
        if not files:
            await bot.send_message(query.message.chat.id, "Нет нераспределенных фотографий")
            break
        for file in files:
            await bot.send_message(query.message.chat.id, text=f"Всего {len(files)}")
            button = InlineKeyboardButton('Правильно',
                                          callback_data='photo_right')
            button1 = InlineKeyboardButton('Неправильно', callback_data='photo_not_right')
            kb = InlineKeyboardMarkup().add(button).add(button1)
            await bot.send_photo(query.message.chat.id, photo=open(Neraspr_dir + file, 'rb'))
            await bot.send_message(query.message.chat.id, text=file,
                                   reply_markup=kb)
            break

# -----Команда старт
@dp.message_handler(commands=['start'], state='*')
async def start_command(message: types.Message):
    button = InlineKeyboardButton('Добавить меня в список рассылки', callback_data='add_user_admin_list_button')
    button1 = InlineKeyboardButton('Настройки', callback_data='/settings')
    button2 = InlineKeyboardButton('Кто во сколько сегодня пришел', callback_data='today_come_time_list')
    kb = InlineKeyboardMarkup().add(button).add(button1).add(button2)
    print(message.from_user.id)
    await bot.send_message(message.from_user.id,
                           "Бот крыса на связи 🐀\nУчусь палить всех, кто во сколько придет.\nЕще и записываю это",
                           reply_markup=kb)


# -----Добавляем или удаляем из списка рассылки
@dp.callback_query_handler(lambda c: c.data == 'add_user_admin_list_button', state='*')
async def add_user_admin_list_command(query: types.CallbackQuery):
    try:
        cur.execute("select * from admins where id=?", (query.message.chat.id,))
        #Проверяем есть ли пользователь в списке рассылки
        if cur.fetchone() == None:
            cur.execute("insert into admins (id, notifications) values (?, ?)", (query.message.chat.id, 0))
            conn.commit()
            #Изменяем предыдущее сообщение
            button2 = InlineKeyboardButton('Удалить из списка рассылки', callback_data='add_user_admin_list_button')
            button3 = InlineKeyboardButton('Включить уведомления', callback_data='admin_notification')
            kb2 = InlineKeyboardMarkup().add(button2).add(button3)
            await query.message.edit_text(reply_markup=kb2, text="Добавил в список рассылки, по умолчанию уведомления выключены. Включить?")
        else:
            cur.execute("delete from admins where id=?", (query.message.chat.id,))
            conn.commit()
            button = InlineKeyboardButton('Добавить меня в список рассылки', callback_data='add_user_admin_list_button')
            kb = InlineKeyboardMarkup().add(button)
            await query.message.edit_text(reply_markup=kb, text="Удалил вас из списка рассылки")
    except Exception as err:
        print(err)
        await bot.send_message(query.message.chat.id,
                               "Ошибка подключения к базе данных, попробуйте позже")


#Включаем или выключаем уведомления
@dp.callback_query_handler(lambda c: c.data == 'admin_notification', state='*')
async def admin_notification_command(query: types.CallbackQuery):
    try:
        cur.execute("select * from admins where id=?", (query.message.chat.id,))
        button = InlineKeyboardButton('Удалить из списка рассылки', callback_data='add_user_admin_list_button')
        kb = InlineKeyboardMarkup()
        if cur.fetchone()[0] == 1:
            cur.execute("update admins set notifications = 0 where id=?", (query.message.chat.id,))
            conn.commit()
            button2 = InlineKeyboardButton('Включить уведомления', callback_data='admin_notification')
        else:
            cur.execute("update admins set notifications = 1 where id=?", (query.message.chat.id,))
            conn.commit()
            button2 = InlineKeyboardButton('Выключить уведомления', callback_data='admin_notification')
        kb.add(button).add(button2)
        await query.message.edit_text(reply_markup=kb, text="Выберите, что хотите сделать")
    except Exception as err:
        print(err)
        await bot.send_message(query.message.chat.id,
                               "Ошибка подключения к базе данных, попробуйте позже")


#Команда настройки
@dp.message_handler(commands=['settings'], state='*')
async def settings_command(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    await state.reset_state()
    try:
        cur.execute("select * from admins where id=?", (message.from_user.id,))
        kb = InlineKeyboardMarkup()
        button = InlineKeyboardButton('Запустить распознование', callback_data='start_function')
        kb.add(button)
        data = cur.fetchone()
        #Проверяем есть ли пользователь в списке рассылки
        if data == None:
            button = InlineKeyboardButton('Добавить меня в список рассылки', callback_data='add_user_admin_list_button')
            kb.add(button)
        else:
            button = InlineKeyboardButton('Удалить из списка рассылки', callback_data='add_user_admin_list_button')
            kb.add(button)
            if data[0] == 1:
                button2 = InlineKeyboardButton('Выключить уведомления', callback_data='admin_notification')
                kb.add(button2)
            else:
                button2 = InlineKeyboardButton('Включить уведомления', callback_data='admin_notification')
                kb.add(button2)
        await bot.send_message(message.from_user.id,
                               "Выберите, что хотите сделать",
                               reply_markup=kb)
    except Exception as err:
        print(err)
        await bot.send_message(message.from_user.id,
                               "Ошибка подключения к базе данных, попробуйте позже")


@dp.callback_query_handler(lambda c: c.data == 'test', state='*')
async def button_right_command(query: types.CallbackQuery):
    cur.execute("select * from admins where notifications=1")
    for i in cur:
        button = InlineKeyboardButton('Правильно',
                                      callback_data='photo_right')
        button1 = InlineKeyboardButton('Неправильно', callback_data='photo_not_right')
        kb = InlineKeyboardMarkup().add(button).add(button1)
        await bot.send_message(i[1], text="file!dirrection",
                               reply_markup=kb)


#Кнопка когда правильно
@dp.callback_query_handler(lambda c: c.data == 'photo_right', state='*')
async def button_right_command(query: types.CallbackQuery):
    dirr = query.message.text.split('!')[0]
    shutil.move(Neraspr_dir + query.message.text, NEW_DIR + dirr)
    state = dp.current_state(user=query.from_user.id)
    button = InlineKeyboardButton('Дальше', callback_data='raspr_photo_next')
    kb = InlineKeyboardMarkup().add(button)
    await state.reset_state()
    await query.message.edit_text(text="Спасибо! Переместил в папку", reply_markup=kb)


#Кнопка когда неправильно
@dp.callback_query_handler(lambda c: c.data == 'photo_not_right', state='*')
async def button_not_right_command(query: types.CallbackQuery):
    state = dp.current_state(user=query.from_user.id)
    kb = InlineKeyboardMarkup()
    for root, dirs, files in os.walk(NEW_DIR):
        for dir in dirs:
            button = InlineKeyboardButton(text=dir, callback_data=query.message.text)
            kb.add(button)
    await state.set_state(UserStates.all()[0])
    await query.message.edit_text(text="Выберите кто:", reply_markup=kb)


@dp.callback_query_handler(state=UserStates.USER_STATE_0)
async def choose_right(query: types.CallbackQuery):
    dirr = query.data.split('!')[0]
    shutil.move(Neraspr_dir + query.data, NEW_DIR + dirr)
    state = dp.current_state(user=query.from_user.id)
    button = InlineKeyboardButton('Дальше', callback_data='raspr_photo_next')
    kb = InlineKeyboardMarkup().add(button)
    await state.reset_state()
    await query.message.edit_text(text="Спасибо! Переместил в папку", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == 'start_function', state='*')
async def start_command(query: types.CallbackQuery):
    await bot.send_message(query.message.chat.id,
                           "Начато выполнение команды")
    await main_work()


async def noon_print():
    cur.execute("select * from admins where notifications=1")
    for i in cur:
        await bot.send_message(i[1], "123")


async def scheduler():

    aioschedule.every(30).minutes.do(main_work)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dispatcher):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    executor.start_polling(dispatcher=dp, skip_updates=True, on_startup=on_startup)
    #executor.start_polling(dispatcher=dp, skip_updates=True)
