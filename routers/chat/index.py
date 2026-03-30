import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func

from ai.chat_robot import translate_stream  # 🚀 引入新的流式函数
from common.security import get_current_user, get_optional_current_user
from data.database import get_session
from data.models.history import TranslationDict, UserHistory
from data.models.user import User
from routers.chat.models import TranslateParams, AITranslateResult
from common.logger import logger

chat_router = APIRouter(
    prefix="/chat",
    tags=["AI"]
)


# 🚀 极其关键：去掉了 response_model=TranslateResult，因为流式返回不走普通校验
@chat_router.post("/translate")
async def translate_text(
        params: TranslateParams,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_optional_current_user)
):
    original_text = params.text.strip()
    logger.info(f"收到翻译请求: '{original_text}'")

    async def event_generator():
        try:
            # 1. 优先查缓存
            dict_record = session.exec(
                select(TranslationDict).where(TranslationDict.original_text == original_text)
            ).first()

            if dict_record:
                logger.success(f"🎯 命中全局词典缓存！ID: {dict_record.id}")
                # 缓存命中时，直接通过 finish 事件把完整数据秒发给前端，无需等待
                cached_data = {
                    "source_language": "cached",
                    "original_text": dict_record.original_text,
                    "translated_text": dict_record.translated_text,
                    "pronounce": dict_record.pronounce,
                    "pronounce_tips": dict_record.pronounce_tips,
                    "comment": dict_record.comment
                }

                # 记录用户历史
                if current_user:
                    history_stmt = select(UserHistory).where(
                        UserHistory.user_id == current_user.id,
                        UserHistory.translation_id == dict_record.id
                    )
                    if not session.exec(history_stmt).first():
                        new_history = UserHistory(user_id=current_user.id, translation_id=dict_record.id)
                        session.add(new_history)
                        session.commit()

                # 按照 SSE 规范发送数据
                yield f"data: {json.dumps({'type': 'finish', 'result': cached_data}, ensure_ascii=False)}\n\n"
                return

            # 2. 缓存未命中，启动 AI 流式推理
            logger.info("⏳ 未命中缓存，请求 AI 流式生成中...")
            translation_id = None

            async for event in translate_stream(original_text):
                # 如果收到思考过程或内容片段，直接实时推给前端
                if event["type"] in ["thinking", "content"]:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 如果收到完成信号，说明后端已经拼装并校验完毕，准备存库
                elif event["type"] == "finish":
                    parsed_result: AITranslateResult = event["result"]
                    logger.success("数据校验成功，正在持久化到数据库...")

                    # 存入全局词典
                    new_dict_record = TranslationDict(
                        original_text=original_text,
                        translated_text=parsed_result.translated_text,
                        pronounce=parsed_result.pronounce,
                        pronounce_tips=parsed_result.pronounce_tips,
                        comment=parsed_result.comment
                    )
                    session.add(new_dict_record)
                    session.commit()
                    session.refresh(new_dict_record)
                    translation_id = new_dict_record.id

                    # 存入用户历史
                    if current_user:
                        new_history = UserHistory(user_id=current_user.id, translation_id=translation_id)
                        session.add(new_history)
                        session.commit()

                    # 将最终的结构化数据发给前端收尾
                    yield f"data: {json.dumps({'type': 'finish', 'result': parsed_result.model_dump()}, ensure_ascii=False)}\n\n"

                elif event["type"] == "error":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception(f"流式接口异常: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': '服务端内部异常'}, ensure_ascii=False)}\n\n"

    # 🚀 返回 StreamingResponse，Content-Type 必须是 text/event-stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
