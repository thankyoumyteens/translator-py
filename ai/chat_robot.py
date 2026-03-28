import asyncio
import os

# noinspection PyUnusedImports
import env_setup

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from routers.chat.models import AITranslateResult

system_prompt = """
# Role
你是一位精通中美流行文化和日常交际的双语翻译专家。你的核心能力是将任何死板的文本，转化为极其自然、地道、口语化的母语表达。

# Task
将用户的输入在中文和英文之间进行翻译。你的终极目标是“传意”而非“译字”，让译文听起来完全就像是美国街头、咖啡馆或中国日常生活中母语者会脱口而出的话。

# Guidelines
1. 击碎“机翻味”：绝对避免生硬的词对词直译。大胆使用短语动词、当代俚语和高频惯用句型。
2. 锁定美式语境：英文输出请始终默认使用地道的美式英语词汇和表达习惯。
3. 情绪与语气：敏锐捕捉原句的情绪，在英文中适量加入填充词（如 you know, I mean），还原真实的对话感。
4. 美语发音拆解：对于日常交际的高频短句，请在翻译后附带“口语/发音小贴士”。必须以美式发音为准，重点标注母语者语速较快时产生的连读、变音（例如：d + y/u 变音为 /dʒ/）以及美音特有的卷舌音（/r/）和闪音（Flap T），帮助用户掌握最真实的语音语调。

# Output Format
{format_instructions}
"""
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "请帮我翻译这句话：{text}")
])

model = ChatOpenAI(
    api_key=os.environ.get("API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
    model="Pro/moonshotai/Kimi-K2.5",
    temperature=0.5,
)

parser = PydanticOutputParser(pydantic_object=AITranslateResult)
chain = prompt | model | parser


async def translate(text: str):
    result = await chain.ainvoke({
        "text": text,
        "format_instructions": parser.get_format_instructions()
    })

    return result


async def main():
    result = await translate("I'm going to the store.")
    print(result)


if __name__ == '__main__':
    # 将 async 函数作为程序的统一入口
    asyncio.run(main())
