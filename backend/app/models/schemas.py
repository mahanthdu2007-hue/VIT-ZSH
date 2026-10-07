from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    system1: str
    llm: Literal["groq", "gemini", "none"]
    demo_mode: bool
