import os
from dotenv import load_dotenv

# 1. 清理终端的代理
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(key, None)

# 2. 加载 .env 文件里的安全环境变量
load_dotenv()
