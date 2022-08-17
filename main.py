import logging
import hashlib
from aiogram import types
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle
from aiogram.utils.executor import start_webhook
from config import bot, dp, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT,SERVER_TDT
from db import database
import json
import requests



async def on_startup(dispatcher):
    await database.connect()
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


async def on_shutdown(dispatcher):
    await database.disconnect()
    await bot.delete_webhook()


async def save(user_id, text):
    await database.execute(f"INSERT INTO messages(telegram_id, text) "
                           f"VALUES (:telegram_id, :text)", values={'telegram_id': user_id, 'text': text})


async def read(user_id):
    results = await database.fetch_all('SELECT text '
                                       'FROM messages '
                                       'WHERE telegram_id = :telegram_id ',
                                       values={'telegram_id': user_id})
    return [next(result.values()) for result in results]

@dp.inline_handler()
async def inline_echo(inline_query: InlineQuery):
    # id affects both preview and content,
    # so it has to be unique for each result
    # (Unique identifier for this result, 1-64 Bytes)
    # you can set your unique id's
    # but for example i'll generate it based on text because I know, that
    # only text will be passed in this example
    text = inline_query.query or 'echo'

    items=[]
    if len(text)>3:
        answer=getModelByName(name=text)
        if answer:
            for models in getModelByName(name=text):
                if models:
                    items.append(InlineQueryResultArticle(
                        id=hashlib.md5(models.encode()).hexdigest(),
                        title=f'Result {models!r}',
                        input_message_content={'message_text':models},
                    ))
                # don't forget to set cache_time=1 for testing (default is 300s or 5m)
            await bot.answer_inline_query(inline_query.id, results=items, cache_time=300)


@dp.message_handler()
async def echo(message: types.Message):
    await save(message.from_user.id, message.text)
    messages = getModelByName(name=message.text)
    await message.answer(messages)



def getModelByName(name=''):
    if len(name)>3:
        session = requests.Session()
        response = session.get(
            (f'''http://{SERVER_TDT}/api/modelgoods/search/{name}''') ,
            params={
                'q': name,
                'format': 'json'
            }
        ).json()

        try:
            textarray = []
            for mod in response:
                print("mod",mod)
                for storage, model,vollink, vol, folders,image in mod:
                    print(storage, model,vollink, vol, folders,image)
                    image_url = image.get('imageurl')
                    text = model.get('name') + "\n" + storage.get('count') + "\n" + str(
                        round(storage.get('p2value'), 0)) + """рублей \n"""
                    textarray.append(text)
                    if not text:
                        print('no results')
                        continue
                    attachments = []
                    if image_url:
                        image = session.get(image_url, stream=True)
                        attachments.append(image_url
                                           # 'photo{}_{}'.format(photo['owner_id'], photo['id'])
                                           )
            return textarray

        except:
            return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )