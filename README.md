# AI Translator Backend (FastAPI)

这是一个基于 **FastAPI** 和 **LangChain** 构建的企业级 AI 翻译后端服务。
项目集成了 JWT 鉴权、语义缓存（Semantic Cache）、全局异常处理、Loguru 规范化日志、APScheduler 数据库定时备份以及跨环境的 Docker 自动化部署方案。

## 🛠 技术栈

* **Web 框架:** FastAPI + Uvicorn
* **ORM & 数据库:** SQLModel + PyMySQL + MySQL
* **AI 编排:** LangChain-OpenAI
* **依赖管理:** Poetry (2.x)
* **工程化基建:** Loguru (日志), APScheduler (定时任务), Bcrypt (密码哈希), PyJWT (鉴权)

---

## 💻 本地开发指南

### 1. 环境准备
* 确保已安装 Python 3.11.15
* 确保已安装 [Poetry](https://python-poetry.org/) 依赖管理工具
* 本地运行一个 MySQL 服务，并创建一个空的数据库

### 2. 安装依赖
在项目根目录下，使用 Poetry 一键安装所有依赖（包含开发环境）：
```bash
poetry install
```

### 3. 环境变量配置
在项目根目录新建一个 `.env` 文件（本地开发用），填入以下内容：

```ini
# AI 模型配置
API_KEY = sk-xxxxxx
SECRET_KEY = xxxxxx

# 数据库配置
MYSQL_USER = root
MYSQL_PASSWORD = 123456
MYSQL_DATABASE = your_db_name
MYSQL_HOST = localhost
MYSQL_PORT = 3306
```

### 4. 启动服务
进入 Poetry 虚拟环境并启动 FastAPI 服务：
```bash
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
启动后，访问 `http://127.0.0.1:8000/docs` 即可查看并调试自动生成的 Swagger API 文档。

---

## 🚀 生产环境打包与部署

项目采用 Docker 进行全容器化部署，支持国内外服务器构建自动切换镜像源。

### 第一步：本地打包 (Local)
在本地终端执行定制的打包脚本，该脚本会自动过滤无用文件（如虚拟环境、缓存等）并生成纯净的 ZIP 包：
```bash
# 生成类似 translator_release_20260329_1200.zip 的文件
python pack.py
```

### 第二步：上传与准备 (Server)
1. 将生成的 `.zip` 包上传至云服务器。
2. 在服务器上解压文件并清理旧环境：

```shell
# 停止并删除旧容器
docker rm -f translator-backend

# 删除旧的代码目录和压缩包（按需执行）
rm -rf translator-backend/
rm translator_release_*.zip 

# 解压最新代码
unzip translator_release_*.zip
cd translator-backend/

# 创建宿主机日志与备份挂载目录
mkdir -p logs/backups
```

### 第三步：构建与运行 (Server)

根据你的服务器物理位置，选择对应的构建命令（国内服务器开启镜像源加速）：

```shell
# 选项 A: 在国内服务器上打包（开启 Aliyun 镜像加速）
docker build --build-arg USE_CHINA_MIRROR=true -t translator-api .

# 选项 B: 在国外服务器上打包（使用官方默认源）
docker build -t translator-api .
```

启动容器，并将日志目录挂载到宿主机以实现日志持久化：

```shell
docker run -d \
  --name translator-backend \
  -p 7152:8000 \
  -v $(pwd)/logs:/app/logs \
  --env-file .env.prod \
  --restart unless-stopped \
  translator-api
```

### 第四步：运维与监控

```shell
# 查看服务实时运行日志
docker logs -f translator-backend 

# 查看持久化落盘的业务日志
tail -f logs/app_*.log
```
*(注：系统每天凌晨 00:00 会自动执行 MySQL 全量备份，备份文件将存放在 `logs/backups/` 目录下。)*
