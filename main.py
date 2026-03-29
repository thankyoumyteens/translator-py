import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from common.exceptions import custom_validation_exception_handler
from common.logger import InterceptHandler
from data.database import create_db_and_tables
from routers.auth.index import auth_router
from routers.chat.index import chat_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时创建 MySQL 表 (如果已存在则跳过)
    create_db_and_tables()
    yield


app = FastAPI(title="翻译器", lifespan=lifespan)

# ==========================================
# 🚀 全局日志劫持配置 (黑魔法激活)
# ==========================================
# 1. 拦截 Uvicorn 的标准日志和错误日志
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]

# 2. 拦截 FastAPI 内部的日志
logging.getLogger("fastapi").handlers = [InterceptHandler()]

# 3. 拦截 SQLAlchemy 的底层 SQL 打印日志 (这样连 SQL 语句都会被写进文件里)
logging.getLogger("sqlalchemy.engine.Engine").handlers = [InterceptHandler()]

# 4. 强制接管 root logger，防止任何漏网之鱼
logging.getLogger().handlers = [InterceptHandler()]
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)

app.include_router(auth_router)
app.include_router(chat_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
