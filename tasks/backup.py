import os
import subprocess
from datetime import datetime
from common.logger import logger


def backup_database():
    logger.info("🕒 开始执行定时任务：MySQL 数据库全量备份...")

    # 将备份文件保存在 logs/backups 目录下，这样能顺着 Docker 挂载直接同步到物理机
    backup_dir = os.path.join("logs", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # 生成带时间戳的文件名，例如: db_backup_20260329_000000.sql
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(backup_dir, f"db_backup_{timestamp}.sql")

    # 从环境变量中读取数据库配置 (兼容本地开发和 Docker 生产环境)
    host = os.environ.get("MYSQL_HOST")
    port = os.environ.get("MYSQL_PORT")
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")  # 本地测试时填入你的密码
    db_name = os.environ.get("MYSQL_DATABASE")

    # 构建 mysqldump 命令
    # --skip-extended-insert: 强制每条数据生成一个独立的 INSERT 语句（更易读）
    # --complete-insert: 包含列名（更严谨）
    cmd = [
        "mysqldump",
        f"-h{host}",
        f"-P{port}",
        f"-u{user}",
        f"-p{password}",
        "--protocol=tcp",
        "--ssl-mode=DISABLED",
        "--skip-extended-insert",
        "--complete-insert",
        "--default-character-set=utf8mb4",
        db_name
    ]

    try:
        # 使用 subprocess 执行命令，并将输出流 (stdout) 直接写入 .sql 文件
        with open(filepath, "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        # 检查是否报错
        if result.returncode == 0:
            logger.success(f"✅ 数据库备份成功！已保存至: {filepath}")
        else:
            logger.error(f"❌ 数据库备份失败！错误信息: {result.stderr}")

    except FileNotFoundError:
        logger.error("❌ 找不到 mysqldump 命令！如果你在 Docker 中运行，请确保镜像内安装了 mysql-client。")
    except Exception as e:
        logger.exception(f"❌ 备份过程中发生未知异常: {str(e)}")
