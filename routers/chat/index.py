# routers/chat/index.py
import json
from fastapi import APIRouter, Depends, Query, Request
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


# 🚀 1. 新增：向前端提供可用模型列表的接口
@chat_router.get("/models")
def get_available_models():
    """获取系统支持的 AI 模型列表，供前端下拉框使用"""
    # 这里也可以做成查数据库配置，目前硬编码即可满足需求
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"id": "openai/gpt-5.4", "name": "GPT-5.4 (智能均衡)", "is_default": True},
            {"id": "openai/gpt-5.4-pro", "name": "GPT-5.4 Pro (最强推理)"},
            {"id": "openai/gpt-5.3-codex", "name": "GPT-5.3 Codex (代码/逻辑专精)"},
            {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash (极速/高性价比)"},
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro (超长上下文/全能)"},
            {"id": "xai/grok-3", "name": "Grok 3 (实时/无审查)"},
            {"id": "xai/grok-4", "name": "Grok 4 (前沿探索)"},
        ]
    }


# 🚀 极其关键：去掉了 response_model=TranslateResult，因为流式返回不走普通校验
@chat_router.post("/translate")
async def translate_text(
        params: TranslateParams,
        request: Request,  # 🚀 2. 在参数里注入 Request 对象
        session: Session = Depends(get_session),
        current_user: User = Depends(get_optional_current_user)
):
    original_text = params.text.strip()
    model_id = params.model_id  # 🚀 2. 获取前端指定的模型
    force_refresh = params.force_refresh  # 🚀 1. 提取刷新标志
    logger.info(f"收到翻译请求: '{original_text}', 指定模型: {model_id}")

    async def event_generator():
        try:
            # 🚀 2. 先把词典记录查出来，不管用不用缓存，后面存库时都要判断
            dict_record = session.exec(
                select(TranslationDict).where(TranslationDict.original_text == original_text)
            ).first()

            # 🚀 3. 如果有缓存，且【没有】要求强制刷新，才直接秒回缓存
            if dict_record and not force_refresh:
                logger.success(f"🎯 命中全局词典缓存！ID: {dict_record.id}")
                cached_data = {
                    "source_language": "cached",
                    "original_text": dict_record.original_text,
                    "translated_text": dict_record.translated_text,
                    "pronounce": dict_record.pronounce,
                    "pronounce_tips": dict_record.pronounce_tips,
                    "comment": dict_record.comment
                }
                if current_user:
                    history_stmt = select(UserHistory).where(
                        UserHistory.user_id == current_user.id,
                        UserHistory.translation_id == dict_record.id
                    )
                    if not session.exec(history_stmt).first():
                        new_history = UserHistory(user_id=current_user.id, translation_id=dict_record.id)
                        session.add(new_history)
                        session.commit()
                yield f"data: {json.dumps({'type': 'finish', 'result': cached_data}, ensure_ascii=False)}\n\n"
                return

            # 2. 缓存未命中，启动 AI 流式推理
            logger.info("⏳ 未命中缓存，请求 AI 流式生成中...")
            translation_id = None

            async for event in translate_stream(original_text, model_id):
                # 🚀 3. 核心护城河：每次准备给前端发数据前，先看一眼前端还在不在！
                if await request.is_disconnected():
                    logger.warning(f"🛑 客户端已主动掐断连接，立即终止 AI 生成！(原文: {original_text[:10]}...)")
                    break  # 直接 break 退出生成器，大模型的流式请求会自动被 Python 垃圾回收并终止

                # 如果收到思考过程或内容片段，直接实时推给前端
                if event["type"] in ["thinking", "content"]:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 如果收到完成信号，说明后端已经拼装并校验完毕，准备存库
                elif event["type"] == "finish":
                    parsed_result: AITranslateResult = event["result"]
                    logger.success("数据校验成功，正在持久化到数据库...")

                    # 🚀 5. 核心修改：智能覆盖或新增
                    if dict_record:
                        # 词典里本来就有这句英文，直接更新字段内容，绝不产生重复脏数据
                        dict_record.translated_text = parsed_result.translated_text
                        dict_record.pronounce = parsed_result.pronounce
                        dict_record.pronounce_tips = parsed_result.pronounce_tips
                        dict_record.comment = parsed_result.comment
                        session.add(dict_record)
                        session.commit()
                        translation_id = dict_record.id
                        logger.info(f"🔄 覆盖更新已有词典记录，ID: {translation_id}")
                    else:
                        # 词典里没有，是全新的一句话，正常插入
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
                        logger.info(f"✨ 插入全新词典记录，ID: {translation_id}")

                    # 存入用户历史
                        # 存入用户历史（防重处理）
                        if current_user:
                            history_stmt = select(UserHistory).where(
                                UserHistory.user_id == current_user.id,
                                UserHistory.translation_id == translation_id
                            )
                            if not session.exec(history_stmt).first():
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
