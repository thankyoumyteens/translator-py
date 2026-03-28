# CREATE DATABASE translator_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

import os
import urllib

# noinspection PyUnusedImports
import env_setup

from sqlmodel import SQLModel, create_engine, Session

app_env = os.environ.get("APP_ENV")
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

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
