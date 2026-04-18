# ai/chat_robot.py
import asyncio
import os
import httpx
from openai import AsyncOpenAI

# noinspection PyUnusedImports
import env_setup

from langchain_core.output_parsers import PydanticOutputParser
from common.logger import logger
from routers.chat.models import AITranslateResult

system_prompt = """
你是一位精通中美文化、极其地道的双语翻译专家，兼具资深美式英语发音教练的身份。

## 1. 核心任务 (Core Task)
请自动识别用户的输入语言，进行中英双向翻译：
- 如果输入是中文，请翻译成极其地道的美式英文。
- 如果输入是英文，请翻译成自然、符合母语者习惯的中文。

## 2. 翻译原则 (Translation Guidelines)
- **击碎机翻味**：绝对避免生硬的字面直译。
- **中译英 (CN->EN)**：大胆使用短语动词、当代美式俚语和高频惯用句型。适量加入填充词（如 you know, I mean, like）以还原真实对话感。
- **英译中 (EN->CN)**：准确传达英语的弦外之音和真实情绪，使用符合当代中国人表达习惯的口语。

## 3. 英语发音拆解 (Pronunciation & Phonetics)
无论输入还是输出，只要涉及到**英文**，你必须提取其中的高频词汇或短句，提供极其详细的**美式发音小贴士**写入 `pronounce_tips` 字段：
- **连读与变音**：重点标注 d+u/y 变音为 /dʒ/ (如 "Did you" -> "Di-jya")，t+u/y 变音为 /tʃ/ (如 "Don't you" -> "Don-cha") 等辅音连读现象。
- **闪音 (Flap T)**：准确标出 t 在两个元音之间发类似轻 d 的音 (如 water, better, letter)。
- **美音特色**：强调美音特有的 /r/ 卷舌音，以及介词/代词在句子中的弱读现象 (Schwa /ə/ 或 h 击穿现象)。
- 请用通俗易懂的文字描述发音细节。

## 4. 输出格式要求 (Strict Output Format)
你必须严格遵守以下 JSON 数据结构，绝对不要输出任何在这个 JSON 结构之外的说明文字或 Markdown 标记：
{format_instructions}

## 5. 思考过程约束 (Strict Thinking Constraints)
你的深度思考过程对用户是可见的。因此，在你的思考过程（Thinking Process）中：
1. **只专注**于推敲翻译的信达雅、选择地道的俚语、以及分析发音规律。
2. **严禁**提及“JSON”、“数据结构”、“字段”、“键值对”等代码术语。
3. **严禁**在思考中探讨如何格式化输出，把组装 JSON 当作你不假思索的本能动作，把思考算力全部留给语言学分析！
"""

# 保留 LangChain 极其好用的 JSON Schema 解析器
parser = PydanticOutputParser(pydantic_object=AITranslateResult)

# 从环境变量读取你的代理地址（如果没有配置，默认为空）
PROXY_URL = os.environ.get("PROXY_URL", None)

# 创建一个自带代理隧道的 HTTP 客户端
custom_http_client = httpx.AsyncClient(proxy=PROXY_URL) if PROXY_URL else None

# 🚀 统一收口：极其干净的原生客户端初始化
client = AsyncOpenAI(
    api_key=os.environ.get("API_KEY"),
    base_url=os.environ.get("BASE_URL"),
    http_client=custom_http_client,
    # 🚀 企业级容错：遇到 503/429 瞬间拥堵时，自动执行指数退避重试 3 次！
    max_retries=3,
    timeout=60.0
)


# 🚀 将默认模型降级为参数，允许 Router 动态传入
async def translate_stream(text: str, model_id: str = None):
    # 兜底逻辑：如果前端没传，就用环境变量里的，如果环境变量也没配，默认 openai/gpt-5.4
    actual_model = model_id or os.environ.get("MODEL_NAME", "openai/gpt-5.4")

    logger.info(f"🤖 正在呼叫 AI 翻译引擎处理(流式): '{text}', 使用模型: {actual_model}")

    # 手动组装 Messages，将 JSON 格式要求强行注入 system prompt
    formatted_system = system_prompt.replace("{format_instructions}", parser.get_format_instructions())
    messages = [
        {"role": "system", "content": formatted_system},
        {"role": "user", "content": f"请帮我翻译这句话，并进行发音拆解：\n\n{text}"}
    ]

    full_content = ""

    try:
        # 准备基础请求参数
        request_kwargs = {
            "model": actual_model,  # 🚀 使用动态传入的模型 ID
            "messages": messages,
            "temperature": 0.5,
            "stream": True,
        }

        # 建立一个“白名单”，只有这些支持强约束的模型才开启 JSON 模式
        json_supported_models = [
            "openai/gpt-5.4",
            "openai/gpt-5.4-pro",
            "openai/gpt-5.3-codex",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-pro",
            "xai/grok-3",
            "xai/grok-4",
        ]

        # 针对当前模型动态判断是否开启 JSON 约束
        if actual_model in json_supported_models:
            request_kwargs["response_format"] = {"type": "json_object"}
            logger.info(f"✨ 模型 {actual_model} 在白名单中，已开启底层 JSON 强制约束")

        # 使用原生客户端发起流式请求
        response = await client.chat.completions.create(**request_kwargs)

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # 🚀 核心破解：绕开各种限制，直接从底层的附加字典里抠出 thinking 内容
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning is None and hasattr(delta, "model_extra") and delta.model_extra:
                reasoning = delta.model_extra.get("reasoning_content")

            if reasoning:
                yield {"type": "thinking", "content": reasoning}

            content = delta.content
            if content:
                full_content += content
                yield {"type": "content", "content": content}

        logger.success("✅ AI 流式接收完毕，准备解析...")
        clean_content = full_content.strip()

        # 严密防守：处理可能包裹的 Markdown 代码块
        if clean_content.startswith("```"):
            start_idx = clean_content.find("{")
            end_idx = clean_content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                clean_content = clean_content[start_idx: end_idx + 1]

        try:
            parsed_result = parser.parse(clean_content)
            yield {"type": "finish", "result": parsed_result}
        except Exception as parse_err:
            logger.error(f"解析清洗后的 JSON 失败: {parse_err}\n内容为: {clean_content}")
            yield {"type": "error", "message": "JSON 结构解析失败，请尝试更换模型重试"}

    except Exception as e:
        logger.error(f"❌ AI 流式解析失败: {e}")
        yield {"type": "error", "message": f"模型调用失败: {str(e)}"}


async def main():
    print("⏳ 开始流式测试...")
    # 测试时也可以手动传入具体的模型名字进行验伤
    async for event in translate_stream("What are you doing later? I was thinking we could grab a bite.",
                                        model_id="xai/grok-3"):
        if event["type"] == "thinking":
            print(f"\033[90m{event['content']}\033[0m", end="", flush=True)
        elif event["type"] == "content":
            print(f"\033[92m{event['content']}\033[0m", end="", flush=True)
        elif event["type"] == "finish":
            print("\n\n🎉 最终解析结果:")
            print(event["result"].model_dump_json(indent=2))


if __name__ == '__main__':
    asyncio.run(main())
