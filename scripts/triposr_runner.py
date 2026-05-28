"""Stable command wrapper for TripoSR.

TripoSR is installed separately. This wrapper lets the API call a consistent
command while keeping model files out of this repository.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a 3D asset with TripoSR.")
    parser.add_argument("--repo-path", required=True, help="Path to a local TripoSR checkout.")
    parser.add_argument("--images", required=True, help="Directory of input images or one image path.")
    parser.add_argument("--output", required=True, help="Target .obj or .glb file.")
    parser.add_argument("--format", choices=["obj", "glb"], default="obj")
    parser.add_argument("--python", default=sys.executable, help="Python executable for the TripoSR environment.")
    parser.add_argument("--device", default="cpu", help="TripoSR device, such as cpu or cuda:0.")
    parser.add_argument("--mc-resolution", type=int, default=128)
    parser.add_argument("--foreground-ratio", type=float, default=0.85)
    parser.add_argument("--no-remove-bg", action="store_true")
    parser.add_argument("--bake-texture", action="store_true")
    parser.add_argument("--texture-resolution", type=int, default=1024)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()
    output_path = Path(args.output).resolve()
    run_py = repo_path / "run.py"
    image_paths = find_images(Path(args.images))

    if not run_py.exists():
        raise SystemExit(f"TripoSR run.py not found: {run_py}")
    if not image_paths:
        raise SystemExit(f"No input images found at: {args.images}")
    if output_path.suffix.lower().lstrip(".") != args.format:
        raise SystemExit("--output extension must match --format")

    work_dir = output_path.parent / "triposr_output"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    command = [
        args.python,
        str(run_py),
        str(image_paths[0]),
        "--output-dir",
        str(work_dir),
        "--device",
        args.device,
        "--mc-resolution",
        str(args.mc_resolution),
        "--foreground-ratio",
        str(args.foreground_ratio),
        "--model-save-format",
        args.format,
    ]
    if args.no_remove_bg:
        command.append("--no-remove-bg")
    if args.bake_texture:
        command.extend(["--bake-texture", "--texture-resolution", str(args.texture_resolution)])

    result = subprocess.run(command, cwd=str(repo_path), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"TripoSR exited with {result.returncode}")

    generated = newest_generated_file(work_dir, args.format)
    if generated is None:
        raise SystemExit(f"TripoSR finished but no .{args.format} file was found in {work_dir}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(generated, output_path)
    print(f"Wrote {output_path}")
    return 0


def find_images(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
        return [path]
    if path.is_dir():
        return sorted(item for item in path.iterdir() if item.suffix.lower() in IMAGE_SUFFIXES)
    return []


def newest_generated_file(output_dir: Path, output_format: str) -> Path | None:
    candidates = [path for path in output_dir.rglob(f"*.{output_format}") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


if __name__ == "__main__":
    raise SystemExit(main())
