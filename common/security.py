import os
from typing import Optional

# noinspection PyUnusedImports
import env_setup
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt

from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from fastapi import Depends, HTTPException, status
from data.database import get_session
from data.models.user import User

# FastAPI 自带的 OAuth2 规范工具
# 它会自动去 HTTP Request Header 里提取 Authorization: Bearer <token>
# tokenUrl 只是为了给 Swagger UI 生成测试界面的按钮用的, 写哪个都行
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# JWT 配置
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token 默认有效期设为 7 天


def get_password_hash(password: str) -> str:
    # bcrypt 运算需要 bytes 类型，所以先编码
    pwd_bytes = password.encode('utf-8')
    # 生成随机盐并进行哈希
    hashed_bytes = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    # 解码为普通字符串存入 MySQL
    return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 验证时同样需要全部转为 bytes
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 🚀 核心校验函数：相当于其他框架里的"拦截器核心逻辑"
def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 无效或已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        # 捕获所有 JWT 错误（如 token 被篡改、已过期等）
        raise credentials_exception

    # 2. 去数据库校验这个用户是否还真实存在（防止账号被删除了但 Token 还没过期）
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()

    if user is None:
        raise credentials_exception

    # 3. 校验通过，把当前用户对象返回给下游的接口
    return user


# auto_error=False 代表如果没有传 Token，不要直接拦截报错，而是放行并传回 None
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_optional_current_user(
        token: str = Depends(oauth2_scheme_optional),
        session: Session = Depends(get_session)
) -> Optional[User]:
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None

        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        return user
    except Exception:
        # 任何 Token 异常都不报错，直接当做未登录（游客）处理
        return None
