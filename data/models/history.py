from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import text


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
