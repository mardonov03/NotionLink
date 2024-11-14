import asyncio
import datetime
import logging
from notion_client import Client
import tldextract
import betterlogging as bl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from tgbot.database.database import User, UserLink, Link, ForwardFrom
from bs4 import BeautifulSoup
import aiohttp
import json
log_level = logging.INFO
bl.basic_colorized_config(level=log_level)
logger = logging.getLogger(__name__)


class Users:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __user_exists(self, user_id: int) -> bool:
        result = await self.session.execute(select(User).filter(User.userid == user_id))
        return result.scalar_one_or_none() is not None

    async def add_user(self, user) -> None:
        try:
            if await self.__user_exists(user.id):
                return
            new_user = User(userid=user.id, fullname=user.full_name, username=user.username or 'Пусто')
            self.session.add(new_user)
            await self.session.commit()
        except Exception as e:
            logger.error(f'error677357242: {e}')

    async def check_token_db(self, user):
        await self.add_user(user)
        try:
            result = await self.session.execute(select(User.token).filter(User.userid == user.id))
            token = result.scalar_one_or_none()
            return token
        except Exception as e:
            logger.error(f'error73567652: {e}')

    async def is_waiting(self, userid):
        try:
            result = await self.session.execute(select(User.waiting).filter(User.userid == userid))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f'error42685682: {e}')

    async def update_waiting(self, userid):
        try:
            status_now = await self.is_waiting(userid)
            new_status = not status_now
            user = await self.session.execute(select(User).filter(User.userid == userid))
            user = user.scalar_one_or_none()
            if user:
                user.waiting = new_status
                await self.session.commit()
        except Exception as e:
            logger.error(f'error2642462: {e}')

    async def get_user_categories(self, userid: int):
        try:
            result = await self.session.execute(select(UserLink.category).filter(UserLink.userid == userid))
            categories = result.fetchall()
            if categories:
                category_list = list({category.category for category in categories})
                return category_list
            return ['other']
        except Exception as e:
            logger.error(f'error2463467: {e}')
            return ['other']

    async def add_link(self, user, link: str, category: str, dispatcher, forward_from, priority):
        linkmodel = dispatcher['linkmodel']
        try:
            extracted = tldextract.extract(link)
            domain = extracted.domain + '.' + extracted.suffix if extracted.domain and extracted.suffix else None
            if domain:
                domain = domain.split('.')[0]
            metadata = await linkmodel.fetch_metadata(link)

            meta_title = metadata.get('title', 'Без названия')
            meta_category = metadata.get('category', 'other')
            meta_source = metadata.get('source', domain)
            existing_link = await self.session.execute(select(Link).where(Link.link == link))
            existing_link = existing_link.scalar()

            if existing_link is not None:
                return False, link

            new_link = Link(link=link, source=meta_source, added_at=datetime.datetime.now(), title= meta_title, category = meta_category)
            self.session.add(new_link)
            await self.session.commit()

            linkid = new_link.linkid
            print('categoryyyyyyyy')
            print(category)
            user_link = UserLink(userid=user.id, linkid=linkid, category=category, priority= priority)
            self.session.add(user_link)
            await self.session.commit()

            if forward_from:
                forward_info = ForwardFrom(
                    username=forward_from[0] or 'Отсутствует',
                    fullname=forward_from[1],
                    type=forward_from[2],
                    userlinkid=user_link.userlinkid
                )
                self.session.add(forward_info)
                await self.session.commit()

            token = await self.check_token_db(user)
            if token is None:
                return
            tokenmodel = dispatcher['tokenmodel']
            await tokenmodel.add_link_to_notion(user.id, link, category, meta_source, meta_title, priority)

            return True
        except Exception as e:
            logger.error(f"error325323677: {e}")
            return False, link

    async def get_user_links_with_info(self, userid, category):
        try:
            query = select(UserLink, Link).join(Link, Link.linkid == UserLink.linkid).filter(UserLink.userid == userid)
            if category != 'все':
                query = query.filter(UserLink.category == category)
            user_links = await self.session.execute(query)
            user_links = user_links.fetchall()

            if not user_links:
                return []

            link_data = []
            for user_link, link in user_links:
                user_info = await self.session.execute(select(ForwardFrom).filter(ForwardFrom.userlinkid == user_link.userlinkid))
                user_info = user_info.scalar_one_or_none()

                link_data.append({
                    'title': link.title,
                    'link': link.link,
                    'username': user_info.username if user_info else None,
                    'fullname': user_info.fullname if user_info else None,
                    'type': user_info.type if user_info else None
                })
            return link_data
        except Exception as e:
            logger.error(f'error03562456: {e}')
            return []

    async def refresh_data(self, user):
        token = await self.check_token_db(user)
        if token is None:
            return
        try:
            pass
        except Exception as e:
            logger.error(f'error7285662: {e}')

class Tokens:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_notion_token(self, token: str) -> bool:
        try:
            notion_result = await asyncio.to_thread(self._check_notion_token_sync, token)
            return notion_result
        except Exception as e:
            logger.error(f"error9249482: {e}")
            return False

    def _check_notion_token_sync(self, token: str):
        notion = Client(auth=token)
        user_info = notion.users.me()
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
            await self._update_user_token_in_db(userid, token, database_id)

            return True
        except Exception as e:
            logger.error(f"Error updating token for user {userid}: {e}")
            return False

    async def _update_user_token_in_db(self, userid, token, database_id):
        try:
            user = await self.session.execute(select(User).filter(User.userid == userid))
            user = user.scalar_one_or_none()
            if user:
                user.token = token
                user.notion_db_id = database_id
                user.updated = datetime.datetime.now()
                await self.session.commit()
        except Exception as e:
            logger.error(f"error8248512: {e}")

    async def add_link_to_notion(self, userid, link, category, source, title, priority):
        try:

            token = await self.get_user_token(userid)
            if not token:
                logger.error(f"User {userid} does not have a valid Notion token.")
                return

            notion = Client(auth=token)

            database_id = await self._get_database_id_from_db(userid)
            if not database_id:
                logger.error(f"User {userid} does not have a valid Notion database ID.")
                return
            print(22222222222222)
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "title": {"title": [{"text": {"content": title if title else ""}}]},
                    "link": {"url": link if link else ""},
                    "category": {"rich_text": [{"text": {"content": category if category else ""}}]},
                    "source": {"rich_text": [{"text": {"content": source if source else ""}}]},
                    "priority": {"number": priority if priority is not None else 0}
                }
            )

        except Exception as e:
            logger.error(f"error2567891911: {e}")

    async def _get_database_id_from_db(self, userid):
        try:
            result = await self.session.execute(select(User.notion_db_id).filter(User.userid == userid))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving database ID from DB: {e}")
            return None

    async def get_user_token(self, userid: int) -> str:
        try:
            token = await self._get_user_token_from_db(userid)
            if token:
                return token
            else:
                raise ValueError("No token found for user")
        except Exception as e:
            logger.error(f"error85858582: {e}")
            return None

    async def _get_user_token_from_db(self, userid):
        try:
            result = await self.session.execute(select(User.token).filter(User.userid == userid))
            token = result.scalar_one_or_none()
            return token
        except Exception as e:
            logger.error(f"error3287462: {e}")
            return None

    async def create_and_get_page_id(self, notion) -> str:
        try:

            pages = await asyncio.to_thread(notion.search, filter={"property": "object", "value": "page"})

            for pg in pages.get('results', []):
                properties = pg.get('properties', {})
                title = properties.get('title', {}).get('title', [])

                for item in title:
                    content = item.get('text', {}).get('content')
                    if content and content.strip() == 'linksinbot':
                        page_id = pg['id']
                        return page_id
        except Exception as e:
            logger.error(f"error02480485312: {e}")


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
                "title": {"type": "title", "title": {}},
                "link": {"type": "url", "url": {}},
                "category": {"type": "rich_text", "rich_text": {}},
                "source": {"type": "rich_text", "rich_text": {}},
                "priority": {"type": "number", "number": {}}})
            database_id = new_database['id']

        return database_id


class Links:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_metadata(self, url: str) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            title = soup.title.string if soup.title else 'Неизвестно'
            category = None
            source = url

            for meta in soup.find_all('meta'):
                if meta.get('property', '').lower() == 'og:title':
                    title = meta.get('content', title)

                if meta.get('property', '').lower() == 'og:type':
                    category = meta.get('content', category)

                if meta.get('name', '').lower() == 'twitter:title':
                    title = meta.get('content', title)

                if meta.get('name', '').lower() == 'category':
                    category = meta.get('content', category)

                if meta.get('name', '').lower() == 'source':
                    source = meta.get('content', source)

            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict) and 'category' in json_data:
                        category = json_data.get('category', category)
                except Exception as e:
                    logger.error(f"Ошибка при обработке JSON-LD: {e}")

            return {
                'title': title,
                'category': category,
                'source': source
            }

        except Exception as e:
            logger.error(f"Ошибка при получении мета-данных: {e}")
            return {}
