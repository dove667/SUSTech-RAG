from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条对话消息。"""

    role: str = Field(description="消息角色，例如 user、assistant。", examples=["user"])
    content: str = Field(description="消息文本内容。", examples=["南科大有哪些学院？"])


class ChatOptions(BaseModel):
    """聊天请求的可选参数。"""

    temperature: float | None = Field(
        default=None,
        description="采样温度。当前后端主要以 YAML 配置为准，此字段保留给前端兼容和后续扩展。",
        examples=[0.3],
    )
    top_k: int | None = Field(
        default=None,
        description="检索候选数。当前后端主要以 YAML 配置为准。",
        examples=[5],
    )
    enable_think: bool | None = Field(
        default=None,
        description="是否开启推理过程展示。当前是否生效取决于具体模型后端。",
        examples=[True],
    )
    enable_tools: bool | None = Field(
        default=None,
        description="是否允许工具调用。当前接口保留该字段，但后端未主动产生工具事件。",
        examples=[True],
    )


class ChatCompletionRequest(BaseModel):
    """流式问答请求体。"""

    conversation_id: str | None = Field(
        default=None,
        description="会话 ID。为空时由服务端自动分配。",
        examples=["c_demo_001"],
    )
    messages: list[ChatMessage] = Field(description="按顺序排列的会话消息列表。")
    model: str | None = Field(
        default=None,
        description="模型标识。当前后端主要读取配置文件中的模型设置。",
        examples=["default"],
    )
    stream: bool = Field(
        default=False,
        description="是否启用 SSE 流式输出。当前接口要求必须为 true。",
        examples=[True],
    )
    options: ChatOptions | None = Field(default=None, description="可选推理参数。")


class ChatCancelRequest(BaseModel):
    """取消生成请求体。"""

    message_id: str = Field(
        description="待取消的消息 ID，应使用 SSE start 事件中返回的 message_id。",
        examples=["m_demo_001"],
    )


class IdentityResponse(BaseModel):
    """身份 ID 分配响应。"""

    identity_id: str = Field(
        description="浏览器身份 ID。前端可持久化后通过 X-Identity-ID 请求头回传。",
        examples=["7f0fd2d186df4e84ad2c7f1d0306e37d"],
    )


class ErrorResponse(BaseModel):
    """通用错误响应。"""

    code: str = Field(description="错误码。", examples=["bad_request"])
    message: str = Field(description="错误信息。", examples=["stream must be true"])


class CancelResponse(BaseModel):
    """取消请求响应。"""

    code: Literal["cancelled"] = Field(description="取消结果状态。", examples=["cancelled"])
    message: str = Field(description="结果说明。", examples=["ok"])


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: Literal["ready", "error"] = Field(description="后端整体状态。", examples=["ready"])
    message: str | None = Field(
        default=None,
        description="状态补充说明。服务未就绪或启动失败时通常会返回该字段。",
        examples=["components not ready"],
    )
    components: dict[str, str] = Field(
        default_factory=dict,
        description="组件状态映射，例如 retrieval、llm。",
        examples=[{"retrieval": "ok", "llm": "ok"}],
    )
