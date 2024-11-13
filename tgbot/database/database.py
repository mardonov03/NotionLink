from sqlalchemy import BigInteger, String, Text, Boolean, TIMESTAMP, Integer, ForeignKey, UniqueConstraint, Column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os
import logging
from dotenv import load_dotenv
load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    userid = Column(BigInteger, primary_key=True)
    username = Column(Text, unique=True)
    fullname = Column(Text)
    token = Column(Text)
    notion_db_id = Column(Text)
    added = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated = Column(TIMESTAMP(timezone=True), server_default=func.now())
    waiting = Column(Boolean, default=False)

class Link(Base):
    __tablename__ = 'links'

    linkid = Column(BigInteger, primary_key=True, autoincrement=True)
    link = Column(Text, unique=True)
    title = Column(Text)
    category = Column(Text, default='other')
    priority = Column(Integer)
    source = Column(Text, default='other')
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class UserLink(Base):
    __tablename__ = 'userlinks'

    userlinkid = Column(BigInteger, primary_key=True, autoincrement=True)
    userid = Column(BigInteger, ForeignKey('users.userid'))
    linkid = Column(BigInteger, ForeignKey('links.linkid'))
    category = Column(Text, default='other')

    __table_args__ = (UniqueConstraint('userid', 'linkid'),)


class ForwardFrom(Base):
    __tablename__ = 'forward_from'

    userlinkid = Column(BigInteger, ForeignKey('userlinks.userlinkid'), primary_key=True)
    username = Column(Text)
    fullname = Column(Text)
    type = Column(Text)


async_engine = create_async_engine(os.getenv("DATABASE_URL"), echo=True)

AsyncSessionLocal = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


