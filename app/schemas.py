from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GenerationMode(str, Enum):
    single = "single"
    multi = "multi"


class OutputFormat(str, Enum):
    obj = "obj"
    glb = "glb"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class EnginePurpose(str, Enum):
    test = "test"
    lightweight = "lightweight"
    quality = "quality"


class EngineInfo(BaseModel):
    name: str
    display_name: str
    description: str
    supports: list[GenerationMode]
    output_formats: list[OutputFormat]
    purpose: EnginePurpose = EnginePurpose.quality
    quality_notes: str | None = None
    storage_notes: str | None = None


class GenerationJob(BaseModel):
    id: str
    status: JobStatus
    mode: GenerationMode
    engine: str
    output_format: OutputFormat
    input_count: int
    created_at: str
    updated_at: str
    artifact_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerationAccepted(BaseModel):
    id: str
    status: JobStatus
    poll_url: str
    artifact_url: str


class CleanupResult(BaseModel):
    deleted: int
    job_ids: list[str]


class StorageInfo(BaseModel):
    storage_dir: Path
    used_bytes: int
    max_bytes: int
    available_bytes: int
