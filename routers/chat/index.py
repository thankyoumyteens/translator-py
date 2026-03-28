from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ai.chat_robot import translate
from common.security import get_current_user, get_optional_current_user
from data.database import get_session
from data.models.history import TranslationHistory
from data.models.user import User
from routers.chat.models import TranslateParams, TranslateResult

chat_router = APIRouter(
    prefix="/chat",
    tags=["AI"]
)


@chat_router.post("/translate", response_model=TranslateResult)
async def register_user(
        params: TranslateParams,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_optional_current_user)  # 🚀 注入可选用户
):
    try:
        result = await translate(params.text)
        print(result)

        # 🚀 落库逻辑：如果用户登录了，就记录到数据库
        if current_user:
            history = TranslationHistory(
                user_id=current_user.id,
                original_text=params.text,  # 前端传来的原文
                translated_text=result.translated_text,
                pronounce=result.pronounce,
                pronounce_tips=result.pronounce_tips,
                comment=result.comment
            )
            session.add(history)
            session.commit()

        return TranslateResult(code=200, message="翻译成功", translated_text=result)
    except Exception as e:
        print(e)
        return TranslateResult(code=500, message=str(e))


# 获取历史记录接口
@chat_router.get("/history")
def get_my_history(
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)  # 🚀 必须登录才能访问
):
    # 查询当前用户最近的 50 条翻译记录，按时间倒序
    statement = select(TranslationHistory).where(
        TranslationHistory.user_id == current_user.id
    ).order_by(TranslationHistory.created_at.desc()).limit(50)

    histories = session.exec(statement).all()

    return {
        "code": 200,
        "message": "success",
        "data": histories
    }
