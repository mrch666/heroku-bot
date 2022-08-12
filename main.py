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
    input_content = InputTextMessageContent(text)
    result_id: str = hashlib.md5(text.encode()).hexdigest()
    items=[]
    for models in getModelByName(name=text):
        items.append (InlineQueryResultArticle(
            id=result_id,
            title=f'Result {models!r}',
            input_message_content=models,
        ))
        # don't forget to set cache_time=1 for testing (default is 300s or 5m)
    await bot.answer_inline_query(inline_query.id, results=items, cache_time=1)


@dp.message_handler()
async def echo(message: types.Message):
    await save(message.from_user.id, message.text)
    messages = await read(message.from_user.id)
    await message.answer(messages)



def getModelByName(name=''):
    session = requests.Session()
    response = session.get(
        (f'''http://{SERVER_TDT}/modelgoods/search/{name}''') ,
        params={
            'q': name,
            'format': 'json'
        }
    ).json()
    print(('''http://''' + SERVER_TDT + '''/modelgoods/search/%s''') % name.split()[0])
    try:
        textarray = []
        # for model in response.get('_embedded').get('modelgoods'):
        for model in response:
            print(model.get('name'))
            image_url = '''https://spec-instrument.ru/img/big/''' + model.get('image')
            text = model.get('name') + "\n" + model.get('count') + "\n" + str(
                round(model.get('price'), 0)) + """рублей \n""" + image_url
            textarray.append(text)
            if not text:
                # return False
                print('no results')
                continue
            attachments = []
            if image_url:
                image = session.get(image_url, stream=True)
                # photo = upload.photo_messages(photos=image.raw)[0]

                attachments.append(image_url
                                   # 'photo{}_{}'.format(photo['owner_id'], photo['id'])
                                   )

            # vk_session.get_api().messages.send(
            #     user_id=event.user_id,
            #     attachment=','.join(attachments),
            #     random_id=get_random_id(),
        return textarray
        # )
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