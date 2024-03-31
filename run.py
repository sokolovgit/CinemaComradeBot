import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from app.handlers.user_private import user_private_router
from app.database.engine import create_db, drop_db
from config import TOKEN


async def main():
    await drop_db()
    await create_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(user_private_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                            stream=sys.stdout)
        asyncio.run(main())
    except KeyboardInterrupt or SystemExit:
        print('Exit')















# import tmdbsimple as tmdb
#
# tmdb.API_KEY = 'e8aed00ef863e2222c14a8009d6272a6'
#
# search = tmdb.Search()
#
# response = search.movie(query='Матриця', language='uk-UA')
#
#
# for movie in response['results']:
#     print(movie['title'], movie['id'])
#
# movie = tmdb.Movies(id=603)
# movie_info = movie.info(language='uk-UA')
#
# print(movie_info['title'], movie_info['overview'], movie_info['release_date'])
#
#
#
