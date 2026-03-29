from pydantic import BaseModel, Field


class TranslateParams(BaseModel):
    text: str = Field(..., description="待翻译的文本")


class AITranslateResult(BaseModel):
    source_language: str = Field(default=None, description="识别出的源语言，'zh' 代表中文，'en' 代表英文")
    original_text: str = Field(default=None, description="用户输入的原文")
    translated_text: str = Field(description="翻译后的译文（极其地道的表达）")
    pronounce: str = Field(description="针对英文部分（无论是原文还是译文）的美式发音的音标")
    pronounce_tips: str = Field(
        description="针对英文部分（无论是原文还是译文）的美式发音拆解贴士，包括连读、变音(d+u变j等)、闪音和卷舌音的详细指导。可使用多行文本。"
    )
    comment: str = Field(description="简单解释一下为什么这么翻译，用到了哪些地道的俚语或短语动词")


class TranslateResult(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field(..., description="提示信息")
    translated_text: AITranslateResult = Field(None, description="翻译结果")
