import asyncpg
import logging
import os

async def create_pool():
    try:
        pool = await asyncpg.create_pool(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            host=os.getenv('DB_HOST'),
            min_size=int(1),
            max_size=int(10)
        )
        return pool
    except Exception as e:
        logging.error(f'error7669804: {e}')


async def init_db(pool):
    try:
        async with pool.acquire() as conn:

            await conn.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            userid BIGINT PRIMARY KEY,
                            username TEXT UNIQUE,
                            fullname TEXT,
                            token TEXT,
                            added TIMESTAMP DEFAULT now(),
                            updated TIMESTAMP DEFAULT now(),
                            waiting BOOLEAN DEFAULT FALSE
                        );
                    """)

            await conn.execute("""
                        CREATE TABLE IF NOT EXISTS links (
                            linkid BIGSERIAL PRIMARY KEY,
                            link TEXT UNIQUE,
                            title TEXT,
                            category TEXT DEFAULT 'other',
                            priority INTEGER,
                            source TEXT DEFAULT 'other',
                            added_at TIMESTAMP DEFAULT now()
                        );
                    """)

            await conn.execute("""
                        CREATE TABLE IF NOT EXISTS userlinks (
                            userid BIGINT REFERENCES users(userid),
                            linkid BIGINT REFERENCES links(linkid),
                            category TEXT DEFAULT 'other', -- если будет NULL берем глобальный
                            UNIQUE (userid, linkid)
                        );
                    """)
    except Exception as e:
        logging.error(f'error984962: {e}')
