# Output Quality

This project can expose high-quality image-to-3D models, but it cannot make every image produce an accurate asset. Accuracy depends on the backend model, the image, and the hardware setup.

## Engine expectations

- `mock`: test engine only. It does not reconstruct the image.
- `hunyuan3d`: recommended quality target for users with enough hardware.
- `triposr`: lightweight starter backend, useful when hardware or disk space is limited.
- `stable-fast-3d`: fast textured single-image option, subject to upstream license terms.

## Input recommendations

- Use high-resolution, sharp images.
- Keep the whole object visible.
- Prefer clean backgrounds or background-removed images.
- Avoid cropped objects, transparent glass-like objects, motion blur, and heavy shadows.
- Use multiple views when the selected backend supports them.

## Storage rule

The API should stay small. Do not commit generated assets, model weights, or uploaded images. Keep model files outside the repo and rely on the storage cap plus cleanup endpoints for local runtime files.
