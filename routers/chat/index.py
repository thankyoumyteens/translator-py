from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from ai.chat_robot import translate
from common.security import get_current_user, get_optional_current_user
from data.database import get_session
from data.models.history import TranslationDict, UserHistory
from data.models.user import User
from routers.chat.models import TranslateParams, TranslateResult, AITranslateResult
from common.logger import logger

chat_router = APIRouter(
    prefix="/chat",
    tags=["AI"]
)


@chat_router.post("/translate", response_model=TranslateResult)
async def translate_text(
        params: TranslateParams,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_optional_current_user)  # 🚀 注入可选用户
):
    try:
        logger.info(f"收到翻译请求: '{params.text}'")
        original_text = params.text.strip()

        # 1. 去【全局词典库】里查有没有这句话
        dict_record = session.exec(
            select(TranslationDict).where(TranslationDict.original_text == original_text)
        ).first()

        if dict_record:
            logger.success(f"🎯 命中全局词典缓存！ID: {dict_record.id}")
            translation_id = dict_record.id
            result = AITranslateResult(
                translated_text=dict_record.translated_text,
                pronounce=dict_record.pronounce,
                comment=dict_record.comment,
                pronounce_tips=dict_record.pronounce_tips
            )
        else:
            logger.info("⏳ 未命中缓存，请求 AI 中...")
            result = await translate(original_text)
            logger.success(f"翻译结果: {result}")
            new_dict_record = TranslationDict(
                original_text=params.text,  # 前端传来的原文
                translated_text=result.translated_text,
                pronounce=result.pronounce,
                pronounce_tips=result.pronounce_tips,
                comment=result.comment
            )
            session.add(new_dict_record)
            session.commit()
            session.refresh(new_dict_record)  # 获取数据库刚刚分配的自增 ID
            translation_id = new_dict_record.id

        # 2. 如果用户登录了，仅仅往【用户历史表】里塞一个绑定关系
        if current_user:
            history_stmt = select(UserHistory).where(
                UserHistory.user_id == current_user.id,
                UserHistory.translation_id == translation_id
            )
            if not session.exec(history_stmt).first():
                new_history = UserHistory(user_id=current_user.id, translation_id=translation_id)
                session.add(new_history)
                session.commit()

        return TranslateResult(code=200, message="翻译成功", translated_text=result)
    except Exception as e:
        logger.exception(f"翻译接口发生异常: {str(e)}")
        return TranslateResult(code=500, message=str(e))


# 获取历史记录接口
@chat_router.get("/history")
def get_my_history(
        page: int = Query(1, ge=1, description="当前页码，从 1 开始"),
        page_size: int = Query(20, ge=1, le=100, description="每页条数，最大 100"),
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    # 1. 🚀 先查询该用户的总记录数 (前端分页组件必须的数据)
    count_statement = select(func.count(UserHistory.id)).where(UserHistory.user_id == current_user.id)
    total_count = session.exec(count_statement).one()

    # 2. 🚀 计算偏移量 (offset)
    offset = (page - 1) * page_size

    # 3. 🚀 执行原有的优雅联表查询，加上 offset 和 limit
    statement = (
        select(UserHistory, TranslationDict)
        .join(TranslationDict, UserHistory.translation_id == TranslationDict.id)
        .where(UserHistory.user_id == current_user.id)
        .order_by(UserHistory.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    results = session.exec(statement).all()

    # 4. 组装回前端需要的扁平格式
    history_list = []
    for user_hist, dict_data in results:
        history_list.append({
            "id": user_hist.id,
            "original_text": dict_data.original_text,
            "translated_text": dict_data.translated_text,
            "pronounce": dict_data.pronounce,
            "pronounce_tips": dict_data.pronounce_tips,
            "comment": dict_data.comment,
            "created_at": user_hist.created_at
        })

    # 5. 🚀 返回标准的带分页元数据的结构
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": history_list,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size  # 顺手帮前端把总页数算好
        }
    }
