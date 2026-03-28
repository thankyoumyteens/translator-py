from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    custom_errors = []

    # exc.errors() 返回的是一个包含所有错误字典的列表
    for error in exc.errors():
        # 1. 获取出错的字段路径（例如 ["body", "user", "phone"] 转换成 "body -> user -> phone"）
        # 这对于嵌套的复杂 JSON 非常有用，能精准定位是哪里的字段报错
        loc_path = " -> ".join([str(x) for x in error["loc"]])

        # 获取最底层的具体字段名，方便做特定判断
        field_name = error["loc"][-1] if error["loc"] else "未知字段"

        # 2. 获取 Pydantic 给出的错误类型和上下文
        err_type = error.get("type")
        ctx = error.get("ctx", {})  # 上下文里会有 min_length, pattern 等详细数据

        # 3. 核心翻译机：根据不同的 type 给出对应的中文提示
        if err_type == "missing":
            error_msg = "该字段是必填项，不能漏掉或为空哦！"
        elif err_type == "string_pattern_mismatch":
            # 正则匹配失败。我们可以根据具体字段名定制，也可以给出通用提示
            if "phone" in str(field_name).lower():
                error_msg = "请输入正确的11位大陆手机号码！"
            else:
                # 还可以把写在 Field 里的正则规则 (ctx['pattern']) 打印出来给用户看
                error_msg = f"格式不符合要求，需要满足规则：{ctx.get('pattern')}"
        elif err_type == "string_too_short":
            error_msg = f"字符太短啦，至少需要 {ctx.get('min_length')} 个字符"
        elif err_type == "string_too_long":
            error_msg = f"字符太长啦，最多只能输入 {ctx.get('max_length')} 个字符"
        elif err_type == "int_parsing":
            error_msg = "数据类型错误，这里必须输入一个整数！"
        elif err_type == "greater_than_equal":
            error_msg = f"数值太小了，必须大于或等于 {ctx.get('ge')}"
        else:
            # 如果遇到我们还没翻译的罕见错误，兜底返回 Pydantic 自带的英文提示
            error_msg = error.get("msg", "参数校验失败")

        custom_errors.append({
            "定位": loc_path,
            "字段": field_name,
            "提示": error_msg
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 40001,  # 你可以自定义业务状态码
            "message": "提交的数据存在问题，请检查后重试",
            "details": custom_errors
        },
    )
