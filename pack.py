import os
import zipfile
from datetime import datetime

# 1. 配置项
PROJECT_ROOT = "."  # 当前目录
# 🚀 新增：压缩包内的顶层目录名
TOP_LEVEL_DIR = "translator-backend"
# 生成的压缩包名称
ZIP_FILENAME = f"translator_release_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"

# 定义要忽略的目录（防止打包 node_modules, 虚拟环境等）
IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "venv",
    "env",
    "miniconda3",
    "node_modules",
    "dist",
    "logs"
}

# 定义要忽略的文件
IGNORE_FILES = {
    ".env",
    ".DS_Store",
    "pack.py",
    ZIP_FILENAME
}


def create_deploy_zip():
    print(f"📦 开始打包项目代码...")
    print(f"🚫 自动过滤以下目录: {', '.join(IGNORE_DIRS)}")

    file_count = 0

    with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # 动态修改 dirs，排除不需要遍历的目录
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                # 🚀 核心修复：直接忽略所有 .zip 后缀的文件！
                if file.endswith('.zip'):
                    continue

                if file in IGNORE_FILES:
                    continue

                # 拼接本地文件的绝对路径
                file_path = os.path.join(root, file)

                # 计算原本的相对路径
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)

                # 🚀 核心修改：在 zip 包里的路径前，硬塞一个顶层目录
                arcname = os.path.join(TOP_LEVEL_DIR, rel_path)

                # 写入 zip
                zipf.write(file_path, arcname)
                file_count += 1

    print(f"✅ 打包完成！共压缩了 {file_count} 个文件。")
    print(f"📂 解压后将生成独立目录: {TOP_LEVEL_DIR}/")
    print(f"💾 产物路径: ./{ZIP_FILENAME}")


if __name__ == "__main__":
    create_deploy_zip()
