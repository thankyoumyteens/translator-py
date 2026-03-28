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

把全部代码（包括 Dockerfile 和 .env.prod）传到云服务器上。

在服务器的项目目录下，依次执行以下两条命令：

```shell
docker build -t translator-api .

docker run -d \
  --name translator-backend \
  -p 8000:8000 \
  --env-file .env.prod \
  --restart unless-stopped \
  translator-api
```