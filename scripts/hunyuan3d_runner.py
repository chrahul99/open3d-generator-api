"""Stable command wrapper for Tencent Hunyuan3D.

This script is intentionally thin. Hunyuan3D and its model weights should be
installed separately, then this wrapper gives Open 3D Generator API a stable
command interface.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a 3D asset with Hunyuan3D.")
    parser.add_argument("--repo-path", required=True, help="Path to a local Hunyuan3D checkout.")
    parser.add_argument("--images", required=True, help="Directory of input images or one image path.")
    parser.add_argument("--output", required=True, help="Target .obj or .glb file.")
    parser.add_argument("--format", choices=["obj", "glb"], default="glb")
    parser.add_argument("--model-path", default="tencent/Hunyuan3D-2.1")
    parser.add_argument("--device", default=None, help="Optional device hint, such as cuda or cpu.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--texture", action="store_true", help="Run Hunyuan3D-Paint after shape generation.")
    parser.add_argument("--texture-resolution", type=int, default=512)
    parser.add_argument("--max-texture-views", type=int, default=6)
    parser.add_argument(
        "--multi-image-policy",
        choices=["first"],
        default="first",
        help="How to handle multiple uploaded images. Current Hunyuan wrapper uses the first image.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()
    output_path = Path(args.output).resolve()
    image_paths = find_images(Path(args.images))

    if not repo_path.exists():
        raise SystemExit(f"Hunyuan3D repo path does not exist: {repo_path}")
    if not image_paths:
        raise SystemExit(f"No input images found at: {args.images}")
    if output_path.suffix.lower().lstrip(".") != args.format:
        raise SystemExit("--output extension must match --format")

    configure_import_paths(repo_path)
    configure_seed(args.seed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh_path = generate_shape(
        image_path=image_paths[0],
        output_path=output_path if not args.texture else output_path.with_suffix(".shape.obj"),
        model_path=args.model_path,
        device=args.device,
    )

    if args.texture:
        generate_texture(
            mesh_path=mesh_path,
            image_path=image_paths[0],
            output_path=output_path,
            model_path=args.model_path,
            resolution=args.texture_resolution,
            max_num_view=args.max_texture_views,
        )
    elif mesh_path != output_path:
        mesh_path.replace(output_path)

    if not output_path.exists():
        raise SystemExit(f"Hunyuan3D did not create output file: {output_path}")

    print(f"Wrote {output_path}")
    return 0


def find_images(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
        return [path]
    if path.is_dir():
        return sorted(item for item in path.iterdir() if item.suffix.lower() in IMAGE_SUFFIXES)
    return []


def configure_import_paths(repo_path: Path) -> None:
    candidates = [
        repo_path,
        repo_path / "hy3dshape",
        repo_path / "hy3dpaint",
        repo_path / "api_server",
    ]
    for candidate in candidates:
        if candidate.exists():
            sys.path.insert(0, str(candidate))


def configure_seed(seed: int | None) -> None:
    if seed is None:
        return
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def generate_shape(*, image_path: Path, output_path: Path, model_path: str, device: str | None) -> Path:
    try:
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    except ImportError as exc:
        raise SystemExit(
            "Could not import Hunyuan3D shape pipeline. Install Hunyuan3D requirements "
            "and pass --repo-path to the local checkout."
        ) from exc

    pipeline_kwargs: dict[str, Any] = {}
    if device:
        pipeline_kwargs["device"] = device

    try:
        pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path, **pipeline_kwargs)
    except TypeError:
        pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)
    result = pipeline(image=str(image_path))
    mesh = result[0] if isinstance(result, (list, tuple)) else result
    export_mesh(mesh, output_path)
    return output_path


def generate_texture(
    *,
    mesh_path: Path,
    image_path: Path,
    output_path: Path,
    model_path: str,
    resolution: int,
    max_num_view: int,
) -> None:
    try:
        from textureGenPipeline import Hunyuan3DPaintConfig, Hunyuan3DPaintPipeline
    except ImportError as exc:
        raise SystemExit(
            "Could not import Hunyuan3D paint pipeline. Install Hunyuan3D paint requirements "
            "or run without --texture."
        ) from exc

    config = Hunyuan3DPaintConfig(max_num_view=max_num_view, resolution=resolution)
    pipeline = Hunyuan3DPaintPipeline(config)
    try:
        result = pipeline(str(mesh_path), image_path=str(image_path), output_path=str(output_path), model_path=model_path)
    except TypeError:
        result = pipeline(str(mesh_path), image_path=str(image_path))
    if output_path.exists():
        return
    mesh = result[0] if isinstance(result, (list, tuple)) else result
    export_mesh(mesh, output_path)


def export_mesh(mesh: Any, output_path: Path) -> None:
    if hasattr(mesh, "export"):
        mesh.export(str(output_path))
        return
    if hasattr(mesh, "save"):
        mesh.save(str(output_path))
        return
    raise SystemExit(f"Hunyuan3D returned an unsupported mesh object: {type(mesh)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
