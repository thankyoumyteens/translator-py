import asyncio
import os

# noinspection PyUnusedImports
import env_setup

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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

# 初始化解析器
parser = PydanticOutputParser(pydantic_object=AITranslateResult)

# 构建 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "请帮我翻译这句话，并进行发音拆解：\n\n{text}")
])

# 初始化大模型 (使用硅基流动 Kimi 接口)
model = ChatOpenAI(
    api_key=os.environ.get("API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
    model="Pro/moonshotai/Kimi-K2.5",
    temperature=0.5,
    # 如果模型支持强制 JSON 模式，可以加上这个参数提升稳定性
    # model_kwargs={"response_format": {"type": "json_object"}},
)

# 构建 LangChain 处理链路
chain = prompt | model | parser


async def translate(text: str) -> AITranslateResult:
    """
    异步调用大模型进行翻译和发音解析
    """
    logger.info(f"🤖 正在呼叫 AI 翻译引擎处理: '{text}'")
    try:
        result = await chain.ainvoke({
            "text": text,
            "format_instructions": parser.get_format_instructions()
        })
        logger.success("✅ AI 翻译并解析成功！")
        return result
    except Exception as e:
        logger.error(f"❌ AI 解析失败，可能的原因是输出格式不匹配或网络超时: {e}")
        raise


async def main():
    # 测试 1: 中译英
    print("\n" + "=" * 40)
    cn_text = "你打算去商店买点水吗？顺便帮我带杯咖啡吧。"
    res1 = await translate(cn_text)
    print(res1.model_dump_json(indent=2))

    # 测试 2: 英译中
    print("\n" + "=" * 40)
    en_text = "What are you doing later? I was thinking we could grab a bite."
    res2 = await translate(en_text)
    print(res2.model_dump_json(indent=2))


if __name__ == '__main__':
    asyncio.run(main())
