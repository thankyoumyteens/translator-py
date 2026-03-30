# CREATE DATABASE translator_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

import os
import urllib

# noinspection PyUnusedImports
import env_setup

from sqlmodel import SQLModel, create_engine, Session

mysql_user = os.environ.get("MYSQL_USER")
mysql_password = os.environ.get("MYSQL_PASSWORD")
mysql_database = os.environ.get("MYSQL_DATABASE")
msql_host = os.environ.get("MYSQL_HOST")
mysql_port = int(os.environ.get("MYSQL_PORT", 3306))

# 🚀 核心修复：对密码进行 URL 安全编码，防止特殊字符破坏连接字符串
if mysql_password:
    encoded_password = urllib.parse.quote_plus(mysql_password)
else:
    encoded_password = ""

DATABASE_URL = f"mysql+pymysql://{mysql_user}:{encoded_password}@{msql_host}:{mysql_port}/{mysql_database}"

# 加上防断连双保险）：
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 生产环境建议关掉 echo，不然日志会被 SQL 语句撑爆
    pool_pre_ping=True,  # 🌟 核心修复1：每次从池子里拿连接前，先发个"SELECT 1"试探一下，如果死了就自动重连！
    pool_recycle=3600,  # 🌟 核心修复2：每隔 3600 秒（1小时），强行回收并重建一次连接池里的连接。
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
