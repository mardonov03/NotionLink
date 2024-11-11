import asyncio
import datetime
import logging
import betterlogging as bl
from notion_client import Client
import tldextract


log_level = logging.INFO
bl.basic_colorized_config(level=log_level)
logger = logging.getLogger(__name__)

class Users:
    def __init__(self, db_pool):
        self.pool = db_pool

    async def __user_exists(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            user_record = await conn.fetch('SELECT userid FROM users WHERE userid = $1', user_id)
            return bool(user_record)

    async def add_user(self, user) -> None:
        try:
            if await self.__user_exists(user.id):
                return

            async with self.pool.acquire() as conn:
                await conn.execute('INSERT INTO users (userid, fullname, username) VALUES ($1, $2, $3)',user.id, user.full_name, user.username or 'Пусто')
        except Exception as e:
            logger.error(f'error677357242: {e}')


    async def check_token_db(self, user):
        await self.add_user(user)
        try:
            async with self.pool.acquire() as conn:
                token = await conn.fetchval('SELECT token FROM users WHERE userid = $1', user.id)
                return token
        except Exception as e:
            logger.error(f'error73567652: {e}')

    async def is_waiting(self, userid):
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval('SELECT waiting FROM users WHERE userid = $1', userid)
                return result
        except Exception as e:
            logger.error(f'error42685682: {e}')

    async def update_waiting(self, userid):
        status_now = await self.is_waiting(userid)
        new_status = not status_now
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('UPDATE users SET waiting = $1 WHERE userid =$2', new_status, userid)
        except Exception as e:
            logger.error(f'error2642462: {e}')

    async def get_user_categories(self, userid: int):
        try:
            async with self.pool.acquire() as conn:
                categories = await conn.fetch('SELECT category FROM userlinks WHERE userid = $1', userid)

                category_list = list({category['category'] for category in categories})

                return category_list
        except Exception as e:
            logger.error(f'error2463467: {e}')
            return []


class Tokens:
    def __init__(self, db_pool):
        self.pool = db_pool

    async def check_notion_token(self, token: str) -> bool:
        try:
            notion_result = await asyncio.to_thread(self._check_notion_token_sync, token)
            return notion_result
        except Exception as e:
            logger.error(f"Error while checking Notion token: {e}")
            return False

    def _check_notion_token_sync(self, token: str):
        notion = Client(auth=token)
        user_info = notion.users.me()
        print(user_info)
        return True

    async def add_token(self, userid: int, token: str) -> bool:
        is_token_valid = await self.check_notion_token(token)
        if not is_token_valid:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute('UPDATE users SET token=$1, updated=$2 WHERE userid=$3',token, datetime.datetime.now(), userid)
            return True
        except Exception as e:
            logger.error(f"Error updating token for user {userid}: {e}")
            return False


class Links:
    def __init__(self, db_pool):
        self.pool = db_pool

    async def add_link(self, user_id: int, link: str):
        try:
            extracted = tldextract.extract(link)
            domain = extracted.domain + '.' + extracted.suffix if extracted.domain and extracted.suffix else None

            async with self.pool.acquire() as conn:
                await conn.execute('INSERT INTO links (link, source, added_at) VALUES ($1, $2, $3) ON CONFLICT (link) DO NOTHING',link, domain, datetime.datetime.now())

                linkid = await conn.fetchval('SELECT linkid FROM links WHERE link = $1', link)
                if linkid is None:
                    logger.warning(f"Link '{link}' could not be added or retrieved from the database.")
                    return

                await conn.execute('INSERT INTO userlinks (userid, linkid) VALUES ($1, $2) ON CONFLICT (userid, linkid) DO NOTHING',user_id, linkid)

        except Exception as e:
            logger.error(f"Error saving link '{link}' for user {user_id}: {e}")