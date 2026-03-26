from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ScriptStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ScriptCategory(str, Enum):
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    AUTOMATION = "automation"
    UTILITY = "utility"
    CUSTOM = "custom"


class ScriptMeta(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    version: str = "1.0.0"
    category: ScriptCategory = ScriptCategory.CUSTOM
    status: ScriptStatus = ScriptStatus.DRAFT
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    checksum: str = ""


class ScriptContent(BaseModel):
    meta: ScriptMeta
    code: str


class ScriptVersion(BaseModel):
    version: str
    code: str
    changelog: str = ""
    created_at: str = ""
    checksum: str = ""


class KnowledgeDoc(BaseModel):
    id: str = ""
    title: str
    category: str = "api"  # api, example, guide
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class OTAManifest(BaseModel):
    """Manifest for client OTA updates."""
    server_version: str
    scripts: list[ScriptMeta] = Field(default_factory=list)
    timestamp: str = ""


class ClientInfo(BaseModel):
    client_id: str
    hostname: str = ""
    username: str = ""
    orcad_version: str = ""
    last_sync: str = ""
    installed_scripts: list[str] = Field(default_factory=list)


class AgentMessage(BaseModel):
    role: str  # user / assistant
    content: str


class AgentSession(BaseModel):
    session_id: str = ""
    messages: list[AgentMessage] = Field(default_factory=list)
    generated_script: str = ""
