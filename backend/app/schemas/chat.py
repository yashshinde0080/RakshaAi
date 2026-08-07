"""Chat Schemas"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.9, ge=0, le=1)
    stream: bool = False
    use_rag: bool = False
    # enable_thinking: for reasoning models (e.g. Qwen3.5) this is passed to
    # the chat template — True turns on <think>...</think> reasoning output,
    # False disables it. None leaves the template default.
    enable_thinking: Optional[bool] = None


class Choice(BaseModel):
    index: int
    message: Optional[Dict[str, str]] = None
    delta: Optional[Dict[str, str]] = None
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class StreamChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    choices: List[Dict[str, Any]]