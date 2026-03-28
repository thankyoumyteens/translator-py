from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import text


# 1. 核心词典表（绝对唯一，无数据冗余）
class TranslationDict(SQLModel, table=True):
    __tablename__ = "translation_dict"

    id: Optional[int] = Field(default=None, primary_key=True)
    original_text: str = Field(unique=True, index=True, max_length=500, description="原文")
    translated_text: str = Field(max_length=2000, description="翻译结果")
    pronounce: Optional[str] = Field(default=None, max_length=500, description="音标")
    pronounce_tips: Optional[str] = Field(default=None, max_length=2000, description="发音提示")
    comment: Optional[str] = Field(default=None, max_length=2000, description="解析")


# 2. 用户历史关联表（极其轻量）
class UserHistory(SQLModel, table=True):
    __tablename__ = "user_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    translation_id: int = Field(index=True)  # 仅仅记录一个指向词典表的 ID

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )


class TranslationHistory(SQLModel, table=True):
    __tablename__ = "translation_history"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 关联的用户ID (加上 index=True 提升查询速度)
    user_id: int = Field(index=True, description="关联的用户ID")

    # 翻译内容
    original_text: str = Field(max_length=1000, description="原文")
    translated_text: str = Field(max_length=2000, description="翻译结果")
    pronounce: Optional[str] = Field(default=None, max_length=500, description="音标")
    pronounce_tips: Optional[str] = Field(default=None, max_length=2000, description="发音提示")
    comment: Optional[str] = Field(default=None, max_length=2000, description="解析")

    # 创建时间
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP")
        },
        description="翻译时间"
    )
