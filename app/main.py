from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.engines import EngineRegistry
from app.schemas import CleanupResult, EngineInfo, GenerationAccepted, GenerationMode, JobStatus, OutputFormat, StorageInfo
from app.storage import JobStore

settings = get_settings()
app = FastAPI(
    title="Open 3D Generator API",
    version="0.1.0",
    summary="Open-source API for image-to-3D generation with pluggable local model engines.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
executor = ThreadPoolExecutor(max_workers=2)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
if WEB_DIR.exists():
    app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return JobStore(settings)


def get_registry(settings: Settings = Depends(get_settings)) -> EngineRegistry:
    return EngineRegistry(settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {
        "name": "Open 3D Generator API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "ui_url": "/ui",
        "models_url": "/v1/models",
    }


@app.get("/v1/models", response_model=list[EngineInfo])
def list_models(registry: EngineRegistry = Depends(get_registry)):
    return registry.list()


@app.get("/v1/storage", response_model=StorageInfo)
def get_storage(settings: Settings = Depends(get_settings), store: JobStore = Depends(get_store)):
    max_bytes = settings.max_storage_mb * 1024 * 1024
    used_bytes = store.used_bytes()
    return StorageInfo(
        storage_dir=settings.storage_dir,
        used_bytes=used_bytes,
        max_bytes=max_bytes,
        available_bytes=max(0, max_bytes - used_bytes),
    )


@app.post("/v1/generations/image-to-3d", response_model=GenerationAccepted, status_code=202)
async def create_image_to_3d_generation(
    images: list[UploadFile] = File(...),
    engine: str = Form("mock"),
    output_format: OutputFormat = Form(OutputFormat.obj),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_store),
    registry: EngineRegistry = Depends(get_registry),
):
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    if len(images) > settings.max_images:
        raise HTTPException(status_code=400, detail=f"At most {settings.max_images} images are allowed")
    max_storage_bytes = settings.max_storage_mb * 1024 * 1024
    if store.available_bytes(max_storage_bytes) < settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=507,
            detail="Storage limit reached. Delete jobs or run cleanup before generating more models.",
        )
    invalid_uploads = [
        upload.filename or "unnamed upload"
        for upload in images
        if upload.content_type not in ALLOWED_IMAGE_TYPES
    ]
    if invalid_uploads:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type for: {', '.join(invalid_uploads)}. Use PNG, JPEG, or WebP.",
        )

    mode = GenerationMode.single if len(images) == 1 else GenerationMode.multi
    selected_engine = registry.get(engine)
    if selected_engine is None:
        raise HTTPException(status_code=404, detail=f"Unknown engine: {engine}")
    if not selected_engine.can_run(mode, output_format):
        raise HTTPException(
            status_code=400,
            detail=f"Engine {engine} does not support {mode.value} image-to-3D with {output_format.value} output",
        )

    job = store.create(mode=mode, engine=engine, output_format=output_format, input_count=len(images))
    try:
        input_paths = await store.save_uploads(job.id, images, settings.max_upload_mb * 1024 * 1024)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    executor.submit(run_generation, job.id, input_paths, settings)
    return GenerationAccepted(
        id=job.id,
        status=job.status,
        poll_url=f"/v1/generations/{job.id}",
        artifact_url=f"/v1/generations/{job.id}/artifact",
    )


@app.get("/v1/generations/{job_id}")
def get_generation(job_id: str, store: JobStore = Depends(get_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


@app.get("/v1/generations/{job_id}/artifact")
def get_generation_artifact(job_id: str, store: JobStore = Depends(get_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status != JobStatus.succeeded or job.artifact_path is None:
        raise HTTPException(status_code=409, detail=f"Artifact is not ready; job status is {job.status.value}")
    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing")
    return FileResponse(path, filename=path.name)


@app.delete("/v1/generations/{job_id}", status_code=204)
def delete_generation(job_id: str, store: JobStore = Depends(get_store)) -> None:
    if not store.delete(job_id):
        raise HTTPException(status_code=404, detail="Generation job not found")


@app.post("/v1/maintenance/cleanup", response_model=CleanupResult)
def cleanup_completed_jobs(
    max_age_hours: int | None = None,
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_store),
):
    age_hours = max_age_hours if max_age_hours is not None else settings.cleanup_max_age_hours
    if age_hours < 0:
        raise HTTPException(status_code=400, detail="max_age_hours must be zero or greater")
    deleted = store.cleanup_completed(age_hours)
    return CleanupResult(deleted=len(deleted), job_ids=deleted)


def run_generation(job_id: str, input_paths: list[Path], settings: Settings) -> None:
    store = JobStore(settings)
    registry = EngineRegistry(settings)
    job = store.get(job_id)
    if job is None:
        return

    job.status = JobStatus.running
    store.save(job)

    try:
        engine = registry.get(job.engine)
        if engine is None:
            raise RuntimeError(f"Unknown engine: {job.engine}")
        artifact_path = store.artifact_path(job.id, job.output_format)
        metadata = engine.generate(
            job_id=job.id,
            mode=job.mode,
            input_paths=input_paths,
            output_path=artifact_path,
            output_format=job.output_format,
        )
        job.status = JobStatus.succeeded
        job.artifact_path = artifact_path
        job.metadata.update(metadata)
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
    finally:
        store.save(job)
