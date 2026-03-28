from pydantic import BaseModel, Field


# 用于接收前端注册/登录请求的参数模型
class UserAuth(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
