import asyncio
import datetime
import logging
import betterlogging as bl
from notion_client import Client
import tldextract
import aiohttp

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
                if categories:
                    category_list = list({category['category'] for category in categories})
                    return category_list
                return ['other']
        except Exception as e:
            logger.error(f'error2463467: {e}')
            return ['other']

    async def add_link(self, user, link: str, category: str, deispatcher):
        try:
            extracted = tldextract.extract(link)
            domain = extracted.domain + '.' + extracted.suffix if extracted.domain and extracted.suffix else None

            async with self.pool.acquire() as conn:
                await conn.execute('INSERT INTO links (link, source, added_at) VALUES ($1, $2, $3) ON CONFLICT (link) DO NOTHING', link, domain, datetime.datetime.now())

                linkid = await conn.fetchval('SELECT linkid FROM links WHERE link = $1', link)
                if linkid is None:
                    logger.warning(f"Link '{link}' could not be added or retrieved from the database.")
                    return

                await conn.execute('INSERT INTO userlinks (userid, linkid, category) VALUES ($1, $2, $3) ON CONFLICT (userid, linkid) DO NOTHING', user.id, linkid, category)

                token = await self.check_token_db(user)
                if token is None:
                    return
                tokenmodel = deispatcher['tokenmodel']
                await tokenmodel.add_link_to_notion(user.id, link, category, domain)
        except Exception as e:
            logger.error(f"Error saving link '{link}' for user {user.id}: {e}")

    async def get_user_links(self, userid, category):
        try:
            async with self.pool.acquire() as conn:
                if category == 'все':
                    res = await conn.fetch('SELECT linkid FROM userlinks WHERE userid = $1', userid)
                else:
                    res = await conn.fetch('SELECT linkid FROM userlinks WHERE userid = $1 AND category = $2',userid,category)

                link_ids = [row['linkid'] for row in res]

                if not link_ids:
                    return []

                links = await conn.fetch('SELECT title, link FROM links WHERE linkid = ANY($1::bigint[])', link_ids)

                return links
        except Exception as e:
            logger.error(f'error03562456: {e}')
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
            notion = Client(auth=token)
            database_id = await self.get_or_create_notion_db(notion)
            if database_id is None:
                return False
            await asyncio.to_thread(self._update_user_token_in_db, userid, token, database_id)
            return True
        except Exception as e:
            logger.error(f"Error updating token for user {userid}: {e}")
            return False

    def _update_user_token_in_db(self, userid, token, database_id):
        try:
            with self.pool.acquire() as conn:
                conn.execute('UPDATE users SET token=$1, notion_db_id=$2, updated=$3 WHERE userid=$4',
                             token, database_id, datetime.datetime.now(), userid)
        except Exception as e:
            logger.error(f"Error updating user token in DB: {e}")

    async def add_link_to_notion(self, userid, link, category, source):
        try:
            database_id = await asyncio.to_thread(self._get_database_id_from_db, userid)
            if not database_id:
                logger.error(f"User {userid} does not have a valid Notion database ID.")
                return

            notion = Client(auth=await self.get_user_token(userid))

            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "link": {"title": [{"text": {"content": link}}]},
                    "category": {"rich_text": [{"text": {"content": category}}]},
                    "source": {"rich_text": [{"text": {"content": source}}]},
                }
            )
        except Exception as e:
            logger.error(f"Error adding link '{link}' to Notion: {e}")

    def _get_database_id_from_db(self, userid):
        try:
            with self.pool.acquire() as conn:
                database_id = conn.fetchval('SELECT notion_db_id FROM users WHERE userid = $1', userid)
                return database_id
        except Exception as e:
            logger.error(f"Error retrieving database ID from DB: {e}")
            return None

    async def get_user_token(self, userid: int) -> str:
        try:
            token = await asyncio.to_thread(self._get_user_token_from_db, userid)
            if token:
                return token
            else:
                raise ValueError("No token found for user")
        except Exception as e:
            logger.error(f"Error retrieving token for user {userid}: {e}")

    def _get_user_token_from_db(self, userid):
        try:
            with self.pool.acquire() as conn:
                token = conn.fetchval('SELECT token FROM users WHERE userid = $1', userid)
                return token
        except Exception as e:
            logger.error(f"Error retrieving token from DB: {e}")
            return None

    async def create_and_get_page_id(self, notion) -> str:
        try:
            pages = await asyncio.to_thread(notion.search, filter={"property": "object", "value": "page"})
            for pg in pages['results']:
                if 'properties' in pg and 'title' in pg['properties'] and pg['properties']['title']['title']:
                    if pg['properties']['title']['title'][0]['text']['content'] == 'botlinks':
                        page_id = pg['id']
                        return page_id
        except Exception as e:
            logger.error(f"Error creating botlinks page: {e}")

    async def get_or_create_notion_db(self, notion) -> str:
        databases = await asyncio.to_thread(notion.search, filter={"property": "object", "value": "database"})
        database_id = None

        for db in databases['results']:
            if 'title' in db and db['title'] and db['title'][0]['text']['content'] == 'linksinbot':
                database_id = db['id']
                return database_id

        if not database_id:
            page_id = await self.create_and_get_page_id(notion)

            if page_id is None:
                return None

            new_database = await asyncio.to_thread(notion.databases.create,
                parent={"page_id": page_id},
                title=[{"type": "text", "text": {"content": "linksinbot"}}],
                properties={
                    "link": {"type": "title", "title": {}},
                    "category": {"type": "rich_text", "rich_text": {}},
                    "source": {"type": "rich_text", "rich_text": {}}
                }
            )
            database_id = new_database['id']

        return database_id