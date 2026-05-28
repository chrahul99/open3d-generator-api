# Model Support

This project separates the API/UI from the actual image-to-3D model backends. The API does not download model weights automatically and does not include model weights in this repository.

## Current Status

| Engine | Purpose | Status | Real generation verified locally? | Notes |
| --- | --- | --- | --- | --- |
| `mock` | Test engine | Tested | Yes | Generates a tiny placeholder OBJ so API, UI, storage, cleanup, and download flows can be tested without a GPU or model download. |
| `triposr` | Lightweight real backend | Wrapper ready | No | Free/open-source single-image backend. Requires separate TripoSR install outside this repo. |
| `hunyuan3d` | Quality real backend | Wrapper ready | No | Higher-quality target backend. Requires separate Hunyuan3D install and much stronger hardware. |
| `stable-fast-3d` | Lightweight textured backend | Config example only | No | Included as an adapter example. Check upstream license terms before use. |

## What Has Been Tested

- FastAPI startup.
- Built-in web UI.
- Image upload endpoint.
- Single-image and multi-image job creation.
- Async job polling.
- Placeholder OBJ artifact generation with `mock`.
- Artifact download.
- Job deletion.
- Completed-job cleanup.
- Runtime storage cap.
- Hunyuan3D wrapper help command.
- TripoSR wrapper help command.

## What Has Not Been Tested Yet

- Real TripoSR model generation.
- Real Hunyuan3D model generation.
- Real Stable Fast 3D model generation.
- GPU performance.
- CPU-only generation time for real models.
- Quality/accuracy of generated meshes from real models.

## Publishing Rule

Do not claim real model generation is verified until at least one full image-to-3D run has been completed with that backend and documented here.

When a backend is verified, update the table with:

- hardware used
- operating system
- model version or commit
- output format
- approximate runtime
- notes about quality and limitations
