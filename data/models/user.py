from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import text


# 对应数据库里的表
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, description="用户 ID")
    username: str = Field(unique=True, index=True, max_length=50, description="用户名")
    hashed_password: str = Field(description="密码")

    # --- 新增的审计字段 ---

    # 1. 创建时间：交由 MySQL 自动设置为 CURRENT_TIMESTAMP
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP")
        },
        description="创建时间"
    )

    # 2. 修改时间：创建时自动设置，且每次更新该行时 MySQL 会自动刷新
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        },
        description="修改时间"
    )

    # 3. 创建人：存用户 ID，允许为空
    created_by: Optional[int] = Field(
        default=None,
        description="创建人(用户ID)"
    )

    # 4. 修改人：存用户 ID，允许为空
    updated_by: Optional[int] = Field(
        default=None,
        description="修改人(用户ID)"
    )
