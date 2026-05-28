import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.schemas import GenerationJob, GenerationMode, JobStatus, OutputFormat


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, settings: Settings):
        self.root = settings.storage_dir
        self.jobs_dir = self.root / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def create(self, mode: GenerationMode, engine: str, output_format: OutputFormat, input_count: int) -> GenerationJob:
        now = utc_now()
        job = GenerationJob(
            id=uuid4().hex,
            status=JobStatus.queued,
            mode=mode,
            engine=engine,
            output_format=output_format,
            input_count=input_count,
            created_at=now,
            updated_at=now,
        )
        self.job_dir(job.id).mkdir(parents=True, exist_ok=True)
        self.save(job)
        return job

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def inputs_dir(self, job_id: str) -> Path:
        path = self.job_dir(job_id) / "inputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_path(self, job_id: str, output_format: OutputFormat) -> Path:
        return self.job_dir(job_id) / f"model.{output_format.value}"

    def metadata_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def get(self, job_id: str) -> GenerationJob | None:
        path = self.metadata_path(job_id)
        if not path.exists():
            return None
        return GenerationJob.model_validate_json(path.read_text(encoding="utf-8"))

    def list_jobs(self) -> list[GenerationJob]:
        jobs: list[GenerationJob] = []
        for path in self.jobs_dir.glob("*/job.json"):
            try:
                jobs.append(GenerationJob.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return jobs

    def save(self, job: GenerationJob) -> None:
        job.updated_at = utc_now()
        path = self.metadata_path(job.id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def used_bytes(self) -> int:
        if not self.root.exists():
            return 0
        total = 0
        for path in self.root.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total

    def available_bytes(self, max_storage_bytes: int) -> int:
        return max(0, max_storage_bytes - self.used_bytes())

    def delete(self, job_id: str) -> bool:
        path = self.job_dir(job_id)
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def cleanup_completed(self, max_age_hours: int) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        deleted: list[str] = []
        for job in self.list_jobs():
            if job.status not in {JobStatus.succeeded, JobStatus.failed}:
                continue
            updated_at = datetime.fromisoformat(job.updated_at)
            if updated_at <= cutoff and self.delete(job.id):
                deleted.append(job.id)
        return deleted

    async def save_uploads(self, job_id: str, uploads: list[UploadFile], max_bytes: int) -> list[Path]:
        saved: list[Path] = []
        for index, upload in enumerate(uploads, start=1):
            suffix = Path(upload.filename or "").suffix.lower() or ".img"
            path = self.inputs_dir(job_id) / f"image_{index:02d}{suffix}"
            total = 0
            with path.open("wb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"{upload.filename or 'upload'} exceeds the upload size limit")
                    handle.write(chunk)
            saved.append(path)
        return saved
