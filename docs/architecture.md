# Architecture

The API separates request handling from model execution.

## Flow

1. Client uploads one or more images to `/v1/generations/image-to-3d`.
2. The API creates a job folder under `data/jobs/<job_id>`.
3. Uploaded images are saved under `inputs/`.
4. A background worker runs the selected engine.
5. The engine writes `model.obj` or `model.glb`.
6. Client polls `/v1/generations/<job_id>` and downloads from `/artifact`.
7. Client deletes the job, or maintenance cleanup removes completed jobs later.

## Storage

Runtime storage is intentionally disposable. Uploaded images, job metadata, and generated artifacts live under `data/jobs/` by default. The `data/` folder is ignored by git.

Use `DELETE /v1/generations/{job_id}` to remove one job and `POST /v1/maintenance/cleanup` to remove old completed jobs.

The API also enforces a configurable storage cap with `OPEN3D_MAX_STORAGE_MB`. Use `GET /v1/storage` to inspect current runtime storage usage.

Model repositories and weights are never downloaded automatically and should live outside this repository.

## Engine adapters

Engines implement a small interface:

- name and capability metadata
- supported modes: `single`, `multi`
- supported output formats: `obj`, `glb`
- a `generate` method that writes the artifact

The generic command adapter lets local open-source models run without adding their heavy dependencies to this API package.
