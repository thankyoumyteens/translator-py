import os
import zipfile
from datetime import datetime

# 1. 配置项
PROJECT_ROOT = "."  # 当前目录
TOP_LEVEL_DIR = "translator-backend"  # 压缩包内的顶层目录名

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

# 定义要忽略的基础文件
IGNORE_FILES = {
    ".env",
    ".DS_Store",
    "pack.py"
}


# 🚀 新增：清理旧包的专属函数
def clean_old_builds():
    print("🧹 开始清理历史部署包...")
    count = 0
    # 遍历根目录下的文件
    for file in os.listdir(PROJECT_ROOT):
        # 精准匹配我们自己生成的 zip 包命名格式
        if file.startswith("translator_release_") and file.endswith(".zip"):
            file_path = os.path.join(PROJECT_ROOT, file)
            os.remove(file_path)
            print(f"   🗑️ 已删除: {file}")
            count += 1

    if count == 0:
        print("   ✨ 目录很干净，没有发现旧包。")
    else:
        print(f"   ✅ 成功清理了 {count} 个历史文件！\n")


def create_deploy_zip(target_env_file: str, variant_name: str):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    zip_filename = f"translator_release_{variant_name}_{timestamp}.zip"

    print(f"\n📦 正在构建 [{variant_name}] 专属包...")

    file_count = 0

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                if file.endswith('.zip'):
                    continue

                if file in IGNORE_FILES:
                    continue

                if file.startswith('.env.'):
                    if file != target_env_file:
                        continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, PROJECT_ROOT)
                arcname = os.path.join(TOP_LEVEL_DIR, rel_path)

                zipf.write(file_path, arcname)
                file_count += 1

    print(f"✅ [{variant_name}] 打包完成！共压缩 {file_count} 个文件。")
    print(f"💾 产物路径: ./{zip_filename}")


if __name__ == "__main__":
    print("🚀 启动自动化多环境构建流水线...\n")

    # 0. 🚀 执行打包前，先全自动清理现场
    clean_old_builds()

    # 1. 打出 Gemini 专属包 (仅包含 .env.gemini)
    create_deploy_zip(target_env_file=".env.gemini", variant_name="gemini")

    # 2. 打出 SiliconFlow 专属包 (仅包含 .env.siliconflow)
    create_deploy_zip(target_env_file=".env.siliconflow", variant_name="siliconflow")

    print("\n🎉 全部打包任务已彻底完成！")
