import logging
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from common.logger import logger
from common.exceptions import custom_validation_exception_handler
from common.logger import InterceptHandler
from data.database import create_db_and_tables
from routers.auth.index import auth_router
from routers.chat.index import chat_router
from fastapi.middleware.cors import CORSMiddleware

from tasks.backup import backup_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动时的逻辑: 建表
    create_db_and_tables()

    # 2. 🚀 初始化并启动定时任务
    scheduler = BackgroundScheduler()
    # 测试用：每隔 1 分钟执行一次
    # scheduler.add_job(backup_database, 'interval', minutes=1)
    # 每天凌晨 00:00 执行一次
    scheduler.add_job(backup_database, 'cron', hour=0, minute=0)
    scheduler.start()
    logger.info("⏰ 定时任务调度器已启动 (配置: 每天凌晨 00:00 备份数据库)")

    yield

    # 3. 关闭时的逻辑: 优雅地停止定时器
    scheduler.shutdown()
    logger.info("🛑 定时任务调度器已关闭")


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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)


@app.get("/ping")
async def health_check():
    return {"status": "ok", "message": "pong！后端服务运行正常"}


app.include_router(auth_router)
app.include_router(chat_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
