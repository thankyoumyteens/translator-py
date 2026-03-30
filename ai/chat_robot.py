import asyncio
import os
from openai import AsyncOpenAI  # 🚀 直接引入底层的 OpenAI 原生异步客户端

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
无论输入还是输出，只要涉及到**英文**，你必须提取其中的高频词汇或短句，提供极其详细的**美式发音小贴士**写入 `pronunciation_tips` 字段：
- **连读与变音**：重点标注 d+u/y 变音为 /dʒ/ (如 "Did you" -> "Di-jya")，t+u/y 变音为 /tʃ/ (如 "Don't you" -> "Don-cha") 等辅音连读现象。
- **闪音 (Flap T)**：准确标出 t 在两个元音之间发类似轻 d 的音 (如 water, better, letter)。
- **美音特色**：强调美音特有的 /r/ 卷舌音，以及介词/代词在句子中的弱读现象 (Schwa /ə/ 或 h 击穿现象)。
- 请用通俗易懂的文字描述发音细节。

## 4. 输出格式要求 (Strict Output Format)
你必须严格遵守以下 JSON 数据结构，绝对不要输出任何在这个 JSON 结构之外的说明文字或 Markdown 标记：
{format_instructions}
"""

# 保留 LangChain 极其好用的 JSON Schema 解析器
parser = PydanticOutputParser(pydantic_object=AITranslateResult)

# 🚀 绕过 LangChain 的 ChatOpenAI，直接初始化原生客户端
client = AsyncOpenAI(
    api_key=os.environ.get("API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
)


async def translate_stream(text: str):
    logger.info(f"🤖 正在呼叫 AI 翻译引擎处理(流式): '{text}'")

    # 1. 手动组装 Messages，将 JSON 格式要求强行注入 system prompt
    formatted_system = system_prompt.replace("{format_instructions}", parser.get_format_instructions())
    messages = [
        {"role": "system", "content": formatted_system},
        {"role": "user", "content": f"请帮我翻译这句话，并进行发音拆解：\n\n{text}"}
    ]

    full_content = ""

    try:
        # 2. 使用原生客户端发起流式请求 (不经过 LangChain 的拦截层)
        response = await client.chat.completions.create(
            model="Pro/moonshotai/Kimi-K2.5",
            messages=messages,
            temperature=0.5,
            stream=True
        )

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

        # 3. 数据流接收完毕后，依然利用 LangChain 的 Parser 进行严谨的 JSON 反序列化
        logger.success("✅ AI 流式接收完毕，准备解析...")
        parsed_result = parser.parse(full_content)

        yield {"type": "finish", "result": parsed_result}

    except Exception as e:
        logger.error(f"❌ AI 流式解析失败: {e}")
        yield {"type": "error", "message": str(e)}


async def main():
    print("⏳ 开始流式测试...")
    async for event in translate_stream("What are you doing later? I was thinking we could grab a bite."):
        if event["type"] == "thinking":
            # 灰色打印思考过程
            print(f"\033[90m{event['content']}\033[0m", end="", flush=True)
        elif event["type"] == "content":
            # 绿色打印 JSON 输出
            print(f"\033[92m{event['content']}\033[0m", end="", flush=True)
        elif event["type"] == "finish":
            print("\n\n🎉 最终解析结果:")
            print(event["result"].model_dump_json(indent=2))


if __name__ == '__main__':
    asyncio.run(main())