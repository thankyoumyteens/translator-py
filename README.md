.env文件内容：

```ini
API_KEY = sk-xxxxxx
SECRET_KEY = xxxxxx
MYSQL_USER = root
MYSQL_PASSWORD = 123456
MYSQL_DATABASE = your_db_name
MYSQL_HOST = localhost
MYSQL_PORT = 3306
```

删除旧容器

```shell
docker rm -f translator-backend
```

执行 pack.py 把全部代码打包。

传到云服务器上。

在服务器的项目目录下，依次执行以下命令：

```shell
mkdir -p logs

docker build -t translator-api .

docker run -d \
  --name translator-backend \
  -p 7152:8000 \
  -v $(pwd)/logs:/app/logs \
  --env-file .env.prod \
  --restart unless-stopped \
  translator-api
```