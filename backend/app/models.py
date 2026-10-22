from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Zone = Literal["global", "personal", "work", "health", "finance"]
Rule = Literal["forever", "temporary", "zone_only", "one_time", "session"]
Category = Literal[
    "preference",
    "identity",
    "relationship",
    "schedule",
    "location",
    "work",
    "health",
    "finance",
    "secret",
    "job_search",
    "other",
]
Sensitivity = Literal["low", "medium", "high"]
Command = str


class CandidateFact(BaseModel):
    content: str
    short: str
    category: Category = "other"
    sensitivity: Sensitivity = "low"
    confidence: float = Field(ge=0, le=1, default=0.8)
    is_about_user: bool = True
    is_temporary: bool = False
    expires_in_hours: Optional[int] = None
    suggested_zone: Zone = "global"
    sensitive_span: Optional[str] = None


class ExtractionResult(BaseModel):
    command: Command = "none"
    command_target: Optional[str] = None
    facts: list[CandidateFact] = Field(default_factory=list)


class AnswerResult(BaseModel):
    text: str
    used_memory_ids: list[int] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    zone: Zone = "personal"
    message: str = Field(min_length=1, max_length=10000)


class AnswerRequest(BaseModel):
    choice: Literal["forever", "zone_only", "session", "decline"]
    zone: Optional[Zone] = None
    visibility: Optional[Literal["open", "sensitive"]] = None


class MemoryPatch(BaseModel):
    rule: Optional[Rule] = None
    zone: Optional[Zone] = None
    expires_at: Optional[str] = None
    visibility: Optional[Literal["open", "sensitive", "custom"]] = None
    apps: Optional[list[int]] = None


class PreferenceUpdate(BaseModel):
    behavior: Literal["auto_forever", "zone_only", "session", "never", "ask", "use_once"]
    zone: Optional[Zone] = None


class VerifyDeletionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


AppZone = Literal["personal", "work", "health", "finance"]


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    zones: list[AppZone] = Field(default_factory=lambda: ["personal"])
    can_write: bool = True
    zone: Optional[AppZone] = None  # older clients sent a single zone


class ConnectionUpdate(BaseModel):
    zones: Optional[list[AppZone]] = None
    can_write: Optional[bool] = None


class MCPRecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class MCPFact(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    short: str = Field(min_length=1, max_length=80)
    category: Category
    sensitivity: Sensitivity = "low"
    confidence: float = Field(ge=0, le=1, default=0.8)
    is_temporary: bool = False
    expires_in_hours: Optional[int] = None
    suggested_zone: Optional[Literal["global", "personal", "work", "health", "finance"]] = None


class MCPRememberRequest(BaseModel):
    fact: MCPFact


class ManualMemoryCreate(MCPFact):
    zone: Literal["global", "personal", "work", "health", "finance"] = "personal"
    visibility: Optional[Literal["open", "sensitive"]] = None


class MCPImportRequest(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    facts: list[MCPFact] = Field(min_length=1, max_length=50)
