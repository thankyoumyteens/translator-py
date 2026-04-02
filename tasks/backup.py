import os
import subprocess
from datetime import datetime
from common.logger import logger


def backup_database():
    logger.info("🕒 开始执行定时任务：MySQL 数据库全量备份...")

    backup_dir = os.path.join("logs", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(backup_dir, f"db_backup_{timestamp}.sql")

    host = os.environ.get("MYSQL_HOST")
    port = os.environ.get("MYSQL_PORT")
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    db_name = os.environ.get("MYSQL_DATABASE")

    # 🚀 核心大招：克隆当前环境变量，并悄悄塞入 MYSQL_PWD
    # 这样既不会污染全局环境，又能让 mysqldump 安全地拿到密码
    run_env = os.environ.copy()
    if password:
        run_env["MYSQL_PWD"] = password

    # 构建命令：彻底删掉那个烦人的 -p 参数！
    cmd = [
        "mysqldump",
        f"-h{host}",
        f"-P{port}",
        f"-u{user}",
        # 注意：这里绝对没有 -p 了！
        "--protocol=tcp",
        "--skip-ssl",
        "--skip-extended-insert",
        "--complete-insert",
        "--default-character-set=utf8mb4",
        db_name
    ]

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # 🚀 核心：将携带了 MYSQL_PWD 的环境传给 subprocess
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=run_env)

        if result.returncode == 0:
            logger.success(f"✅ 数据库备份成功！已保存至: {filepath}")
        else:
            logger.error(f"❌ 数据库备份失败！错误信息: {result.stderr}")

    except FileNotFoundError:
        logger.error("❌ 找不到 mysqldump 命令！请确保运行环境中安装了 mysql-client。")
    except Exception as e:
        logger.exception(f"❌ 备份过程中发生未知异常: {str(e)}")
