# TripoSR Integration

TripoSR is the recommended first lightweight real backend for this API. It is free/open-source and designed for single-image 3D reconstruction.

This repository does not include TripoSR source code, dependencies, or model weights. Install TripoSR separately, then connect it through `scripts/triposr_runner.py`.

## Why TripoSR first

- Free and open-source.
- Simpler than Hunyuan3D.
- Single-image to 3D output.
- Good first real backend for laptops and GitHub contributors.

The official TripoSR README says the default options take about 6GB VRAM for a single image, so this wrapper defaults to CPU and lower marching-cubes resolution for a safer laptop starting point. CPU generation may be slow.

## Expected local layout

Example only:

```text
D:/models/TripoSR/
  run.py
  requirements.txt
  tsr/
```

Keep this outside `D:/maker` so the API repo stays small.

## Configure the API

Copy the example engine config:

```powershell
Copy-Item config\engines.example.json config\engines.local.json
$env:OPEN3D_ENGINES_CONFIG="D:\maker\config\engines.local.json"
```

Then edit the `triposr.command` array so `--repo-path` points to your local TripoSR checkout.

## Wrapper command

The API will call:

```powershell
python scripts\triposr_runner.py `
  --repo-path D:\models\TripoSR `
  --images data\jobs\<job_id>\inputs `
  --output data\jobs\<job_id>\model.obj `
  --format obj `
  --device cpu
```

Use `--device cuda:0` only if your GPU has enough VRAM.

## Quality notes

TripoSR is useful and fast compared with heavier systems, but it is not magic. For better output:

- Use one clear object.
- Keep the full object visible.
- Use a clean or removed background.
- Avoid humans, thin transparent objects, reflective objects, and heavy occlusion.
