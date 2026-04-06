import os
import time

# noinspection PyUnusedImports
import env_setup

import subprocess
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from common.logger import logger


def clean_old_backups(local_dir: str, retention_days: int = 7):
    """清理本地超过 N 天的旧备份"""
    logger.info(f"🧹 开始清理本地超过 {retention_days} 天的旧备份...")
    now = time.time()
    cutoff = now - (retention_days * 86400)

    count = 0
    if os.path.exists(local_dir):
        for file in os.listdir(local_dir):
            file_path = os.path.join(local_dir, file)
            # 只处理 .sql 文件，防止误删
            if file.endswith(".sql") and os.path.getmtime(file_path) < cutoff:
                os.remove(file_path)
                logger.info(f"   🗑️ 已删除本地旧备份: {file}")
                count += 1
    logger.success(f"✅ 本地清理完成，共删除 {count} 个文件。")


def upload_to_cloud(filepath: str, filename: str):
    """将本地文件同步到 Cloudflare R2"""
    endpoint = os.environ.get("S3_ENDPOINT_URL")
    ak = os.environ.get("S3_ACCESS_KEY")
    sk = os.environ.get("S3_SECRET_KEY")
    bucket = os.environ.get("S3_BUCKET_NAME")

    if not all([endpoint, ak, sk, bucket]):
        logger.warning("⚠️ 未配置完整的 R2 云盘参数，跳过云端同步。")
        return

    logger.info("☁️ 正在将备份文件同步至 Cloudflare R2...")
    try:
        # 🚀 针对 R2 的专属初始化配置
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name='auto',  # R2 必填占位符
            config=Config(signature_version='s3v4')  # R2 强制要求使用 v4 签名
        )

        cloud_key = f"backups/{datetime.now().strftime('%Y-%m')}/{filename}"

        s3_client.upload_file(filepath, bucket, cloud_key)
        logger.success(f"✅ 云端同步成功！文件已保存至 R2: {cloud_key}")

    except ClientError as e:
        logger.error(f"❌ R2 同步失败，厂商返回错误: {e}")
    except Exception as e:
        logger.error(f"❌ R2 同步发生未知异常: {e}")


def backup_database():
    logger.info("🕒 开始执行定时任务：MySQL 数据库全量备份...")

    backup_dir = os.path.join("logs", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"db_backup_{timestamp}.sql"
    filepath = os.path.join(backup_dir, filename)

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
            # 🚀 核心新增：本地备份成功后，立刻触发云端同步！
            upload_to_cloud(filepath, filename)
            # 🚀 核心新增：备份结束后，清理 7 天前的旧数据
            clean_old_backups(backup_dir, retention_days=7)
        else:
            logger.error(f"❌ 数据库备份失败！错误信息: {result.stderr}")

    except FileNotFoundError:
        logger.error("❌ 找不到 mysqldump 命令！请确保运行环境中安装了 mysql-client。")
    except Exception as e:
        logger.exception(f"❌ 备份过程中发生未知异常: {str(e)}")
