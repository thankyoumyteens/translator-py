from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from common.exceptions import custom_validation_exception_handler
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
