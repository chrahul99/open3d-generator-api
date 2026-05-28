# Open 3D Generator API

Open-source FastAPI service for generating 3D assets from one image or multiple images. The API is model-agnostic: it ships with a tiny built-in test engine and can call locally installed open-source generators through configurable command adapters.

## Supported workflow

- Single image to 3D model
- Multi image to 3D model
- Async job creation, polling, and artifact download
- Pluggable local engines with no paid API dependency

## Open-source model targets

Good local engines to wire behind this API:

- `hunyuan3d`: recommended quality backend for single and multi-view image-to-3D generation.
- `triposr`: fast single-image reconstruction from Tripo AI and Stability AI.
- `stable-fast-3d`: fast textured single-image mesh reconstruction from Stability AI.

Install those projects separately according to their upstream instructions, then point `config/engines.example.json` commands at your local scripts.

See [MODEL_SUPPORT.md](MODEL_SUPPORT.md) for the honest support matrix. Currently, the `mock` engine is fully tested; real model wrappers are ready but still need local generation verification.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

The built-in web UI is available at `http://127.0.0.1:8000/ui/`.

## Environment

Copy the example environment file when you want local overrides:

```powershell
Copy-Item .env.example .env
```

Important settings:

- `OPEN3D_STORAGE_DIR`: where jobs, uploads, and generated artifacts are stored.
- `OPEN3D_ENGINES_CONFIG`: path to your local engine command config.
- `OPEN3D_MAX_IMAGES`: maximum images per generation request.
- `OPEN3D_MAX_UPLOAD_MB`: maximum size per uploaded image.
- `OPEN3D_MAX_STORAGE_MB`: runtime storage limit for uploads, jobs, and generated artifacts.
- `OPEN3D_CLEANUP_MAX_AGE_HOURS`: default age for deleting completed jobs.
- `OPEN3D_CORS_ORIGINS`: comma-separated origins for a future web UI.

## Generate from one image

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/generations/image-to-3d `
  -F "images=@chair.png" `
  -F "engine=mock" `
  -F "output_format=obj"
```

## Generate from multiple images

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/generations/image-to-3d `
  -F "images=@front.png" `
  -F "images=@side.png" `
  -F "images=@back.png" `
  -F "engine=mock" `
  -F "output_format=obj"
```

Poll the returned job:

```powershell
curl.exe http://127.0.0.1:8000/v1/generations/<job_id>
```

Download the artifact:

```powershell
curl.exe -L -o model.obj http://127.0.0.1:8000/v1/generations/<job_id>/artifact
```

Delete the job and all files when you are done:

```powershell
curl.exe -X DELETE http://127.0.0.1:8000/v1/generations/<job_id>
```

Clean up completed jobs older than the configured age:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/maintenance/cleanup
```

Check local runtime storage:

```powershell
curl.exe http://127.0.0.1:8000/v1/storage
```

## Configure real engines

Copy the example config:

```powershell
Copy-Item config\engines.example.json config\engines.local.json
$env:OPEN3D_ENGINES_CONFIG="D:\maker\config\engines.local.json"
```

Each command is executed without a shell. Available template variables:

- `{input}`: first uploaded image path
- `{inputs_dir}`: directory containing all uploaded images
- `{output}`: desired output artifact path
- `{format}`: requested output format, currently `obj` or `glb`
- `{job_id}`: generation job id

Keep generated files under `data/` unless you deliberately configure another writable storage path.

## Disk usage

This repository does not include model weights, generated meshes, or uploaded images. Runtime files live under `data/`, which is ignored by git.

To keep laptop storage low:

- Keep `OPEN3D_MAX_STORAGE_MB` conservative. The default is `512`.
- Delete jobs after downloading artifacts with `DELETE /v1/generations/{job_id}`.
- Run `POST /v1/maintenance/cleanup` regularly.
- Keep model repositories and weights outside this repo, for example on an external drive.
- Lower `OPEN3D_MAX_UPLOAD_MB` and `OPEN3D_MAX_IMAGES` for stricter local limits.

The API never downloads model weights automatically.

## Output quality

Output accuracy depends on the selected engine and input image quality. The built-in `mock` engine is only for testing the API. For real generation, use a real backend such as Hunyuan3D for higher quality or a lighter local model for lower hardware requirements.

For best results:

- Use a sharp image with the whole object visible.
- Prefer a clean background or pre-removed background.
- Avoid heavy occlusion, cropped objects, strong motion blur, and extreme perspective.
- Use multiple views when the backend supports them.
- Use Hunyuan3D or another quality backend when accuracy matters most.

## Hunyuan3D

Hunyuan3D is the recommended high-quality backend for this project. See [docs/hunyuan3d.md](docs/hunyuan3d.md) for the integration shape.

This repo includes `scripts/hunyuan3d_runner.py`, a thin wrapper around a separate local Hunyuan3D checkout. The wrapper gives this API a stable command interface:

```powershell
python scripts\hunyuan3d_runner.py `
  --repo-path D:\models\Hunyuan3D-2.1 `
  --images data\jobs\<job_id>\inputs `
  --output data\jobs\<job_id>\model.glb `
  --format glb
```

## TripoSR

TripoSR is the recommended first lightweight real backend. See [docs/triposr.md](docs/triposr.md).

## Docker

The Docker image runs the API, but real model backends still need to be installed or mounted separately:

```powershell
docker build -t open3d-generator-api .
docker run --rm -p 8000:8000 -v ${PWD}\data:/app/data open3d-generator-api
```

## Development checks

```powershell
pytest
```

## License

MIT. See [LICENSE](LICENSE).
