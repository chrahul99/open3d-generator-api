# Hunyuan3D Integration

Hunyuan3D is the recommended quality backend for this API. This repository does not include model weights or vendor code; users install Hunyuan3D separately and connect it through a command adapter.

## Why Hunyuan3D

- Stronger visual quality than lightweight starter models.
- Good fit for single-image and multi-view image-to-3D workflows.
- Keeps this API useful for people with different hardware because the backend is configurable.

## Expected local layout

Example only:

```text
D:/models/Hunyuan3D-2.1/
  hy3dshape/
  hy3dpaint/
  checkpoints/
```

Your local script can have any name as long as `config/engines.local.json` points to it.

## Configure the API

Copy the example engine file:

```powershell
Copy-Item config\engines.example.json config\engines.local.json
```

Then edit the `hunyuan3d.command` array so `--repo-path` points to your local Hunyuan checkout.

Example command adapter:

```json
{
  "name": "hunyuan3d",
  "display_name": "Hunyuan3D",
  "description": "Recommended high-quality open-source single and multi-view image-to-3D backend.",
  "supports": ["single", "multi"],
  "output_formats": ["obj", "glb"],
  "command": [
    "python",
    "scripts/hunyuan3d_runner.py",
    "--repo-path",
    "D:/models/Hunyuan3D-2.1",
    "--images",
    "{inputs_dir}",
    "--output",
    "{output}",
    "--format",
    "{format}"
  ],
  "timeout_seconds": 3600
}
```

The wrapper currently runs shape generation by default. Add `--texture` to the command array only after Hunyuan3D-Paint is installed and working on your hardware.

## Template variables

- `{input}`: first uploaded image path.
- `{inputs_dir}`: directory containing all uploaded images.
- `{output}`: target artifact path the engine must create.
- `{format}`: requested output format, such as `obj` or `glb`.
- `{job_id}`: API job id.
- `{mode}`: `single` or `multi`.

## Low-VRAM note

Hunyuan3D can be heavy. On machines with small GPUs, prefer a smaller Hunyuan variant, CPU/offload settings, or a remote worker. The API does not care where the actual generation happens as long as the command writes the requested output file.

The official Hunyuan3D-2.1 README currently lists approximately 10GB VRAM for shape generation, 21GB for texture generation, and 29GB for shape plus texture together, so low-VRAM laptops should start with shape-only or a remote worker.
