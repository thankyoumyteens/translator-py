from pydantic import BaseModel, Field


class TranslateParams(BaseModel):
    text: str = Field(..., description="待翻译的文本")


class AITranslateResult(BaseModel):
    translated_text: str = Field(...,
                                 description="翻译结果的地道表达：（给出 1-2 个最自然、最 Native 的翻译版本，用分号分隔）")
    pronounce: str = Field(..., description="美式英语的音标")
    comment: str = Field(..., description="为什么这么翻：（一句话解释用了什么地道词汇或俚语）")
    pronounce_tips: str = Field(..., description="2.发音与连读技巧：（剖析该句在美式口语中的发音细节、变音或吞音现象）")


class TranslateResult(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field(..., description="提示信息")
    translated_text: AITranslateResult = Field(None, description="翻译结果")
