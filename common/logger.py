import sys
import logging
from loguru import logger

# 1. 移除 Loguru 默认的配置，准备完全接管
logger.remove()

# 2. 类似 ConsoleAppender：控制台输出（带颜色高亮）
logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    enqueue=True  # 开启异步写入，不阻塞主线程
)

# 3. 类似 RollingFileAppender：全量业务日志，每天凌晨滚动，保留 30 天，历史压缩
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    level="INFO",
    rotation="00:00",  # 每天凌晨 0 点切割
    # rotation="500 MB",   # 你也可以换成按大小切割
    retention="30 days",  # 最多保留 30 天
    compression="zip",  # 历史日志自动 zip 压缩省空间
    encoding="utf-8",
    enqueue=True
)

# 4. 类似 LevelFilter：把 ERROR 级别的日志单独剥离到一个文件，方便排查报错
logger.add(
    "logs/error.log",
    level="ERROR",
    rotation="10 MB",  # 错误日志达到 10MB 切割
    retention="30 days",
    encoding="utf-8",
    enqueue=True
)


# 🚀 黑魔法：日志劫持器
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 尝试获取对应 Loguru 的日志等级
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 寻找触发日志的调用堆栈深度，保证 Loguru 能打印出正确的代码行号
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # 将拦截到的日志转发给 Loguru
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# 导出这个配置好的 logger
__all__ = ["logger", "InterceptHandler"]
