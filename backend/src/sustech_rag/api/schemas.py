from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatOptions(BaseModel):
    temperature: float | None = None
    top_k: int | None = None
    enable_think: bool | None = None
    enable_tools: bool | None = None


class ChatCompletionRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[ChatMessage]
    knowledge_base_ids: list[str] | None = None
    model: str | None = None
    stream: bool = False
    options: ChatOptions | None = None


class ChatCancelRequest(BaseModel):
    conversation_id: str
    message_id: str


class KnowledgeBaseItem(BaseModel):
    id: str
    name: str
    doc_count: int = 0


class KnowledgeBasesResponse(BaseModel):
    items: list[KnowledgeBaseItem] = Field(default_factory=list)


class IdentityResponse(BaseModel):
    identity_id: str
