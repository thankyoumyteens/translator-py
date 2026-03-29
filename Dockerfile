# Dockerfile (全球通用版)
FROM python:3.11-slim

WORKDIR /app

# 告诉 Poetry：不要在 Docker 里建虚拟环境，直接装在系统 Python 里！
ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=2.1.1

# 定义构建参数，默认值为 false（即默认使用官方源，适合国外服务器）
ARG USE_CHINA_MIRROR=false

# 动态判断是否替换 apt 源，并安装 MySQL 客户端
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        echo "🌍 检测到国内环境，正在启用阿里云 apt 镜像源..." && \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true ; \
    fi && \
    apt-get update && \
    apt-get install -y default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

# 安装 Poetry 本身
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        pip install "poetry==$POETRY_VERSION" -i https://mirrors.aliyun.com/pypi/simple/ ; \
    else \
        pip install "poetry==$POETRY_VERSION" ; \
    fi

# 拷贝并安装项目依赖（利用 Docker 缓存机制）
# 拷贝配置文件（注意：加了星号，意味着如果有 lock 就拷，没有拉倒）
COPY pyproject.toml poetry.lock* ./

RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        echo "🌍 启用阿里云 Poetry 镜像源..." && \
        poetry source add --priority=primary mirrors https://mirrors.aliyun.com/pypi/simple/ ; \
    fi && \
    poetry lock && \
    poetry install --no-root --only main

# 拷贝剩余的业务代码
COPY . .

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 启动命令：使用 Uvicorn 运行，去掉 --reload (生产环境不需要热更新)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]