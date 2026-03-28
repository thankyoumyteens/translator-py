from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from common.security import get_password_hash, verify_password, create_access_token
from data.database import get_session
from data.models.user import User
from routers.auth.models import UserAuth

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@auth_router.post("/register")
def register_user(user_data: UserAuth, session: Session = Depends(get_session)):
    # 1. 检查用户名是否已存在
    statement = select(User).where(User.username == user_data.username)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该用户名已被注册")

    # 2. 对密码进行哈希加密
    hashed_pwd = get_password_hash(user_data.password)

    # 3. 首次落库：此时 MySQL 会自动生成 id, created_at, updated_at
    # created_by 和 updated_by 此时默认为 None
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_pwd
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)  # 刷新后，new_user 已经有了数据库生成的 id

    # 4. 补充审计字段：将刚生成的自增 ID 赋值给创建人和修改人
    new_user.created_by = new_user.id
    new_user.updated_by = new_user.id
    session.add(new_user)
    session.commit()

    return {
        "code": 200,
        "message": "注册成功",
        "user_id": new_user.id
    }


@auth_router.post("/login")
def login_user(user_data: UserAuth, session: Session = Depends(get_session)):
    # 1. 查找用户
    statement = select(User).where(User.username == user_data.username)
    user = session.exec(statement).first()

    # 2. 校验账号和密码
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 3. 签发 JWT Token
    access_token = create_access_token(data={"sub": user.username})

    return {
        "code": 200,
        "message": "登录成功",
        "access_token": access_token,
        "token_type": "bearer"
    }
