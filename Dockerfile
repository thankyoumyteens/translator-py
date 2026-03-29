# 使用官方轻量级 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 防止 Python 缓冲标准输出和错误（能及时在控制台看到日志）
ENV PYTHONUNBUFFERED=1

# 安装系统底层的 mysql-client，提供 mysqldump 工具
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
# 使用阿里云镜像源加速安装（国内服务器必备，国外服务器可删去 -i 部分）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制整个项目代码到容器内
COPY . .

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 启动命令：使用 Uvicorn 运行，去掉 --reload (生产环境不需要热更新)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]