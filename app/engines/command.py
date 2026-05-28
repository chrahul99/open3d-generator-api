import json
import subprocess
from pathlib import Path

from pydantic import BaseModel

from app.engines.base import GenerationEngine
from app.schemas import EngineInfo, EnginePurpose, GenerationMode, OutputFormat


class CommandEngineConfig(BaseModel):
    name: str
    display_name: str
    description: str
    supports: list[GenerationMode]
    output_formats: list[OutputFormat]
    command: list[str]
    working_dir: str | None = None
    timeout_seconds: int = 1800
    purpose: EnginePurpose = EnginePurpose.quality
    quality_notes: str | None = None
    storage_notes: str | None = None


class CommandEngine(GenerationEngine):
    def __init__(self, config: CommandEngineConfig):
        self.config = config
        self.info = EngineInfo(
            name=config.name,
            display_name=config.display_name,
            description=config.description,
            supports=config.supports,
            output_formats=config.output_formats,
            purpose=config.purpose,
            quality_notes=config.quality_notes,
            storage_notes=config.storage_notes,
        )

    def generate(
        self,
        *,
        job_id: str,
        mode: GenerationMode,
        input_paths: list[Path],
        output_path: Path,
        output_format: OutputFormat,
    ) -> dict:
        inputs_dir = input_paths[0].parent
        replacements = {
            "{input}": str(input_paths[0]),
            "{inputs_dir}": str(inputs_dir),
            "{output}": str(output_path),
            "{format}": output_format.value,
            "{job_id}": job_id,
            "{mode}": mode.value,
        }
        command = [self._replace_tokens(part, replacements) for part in self.config.command]
        working_dir = (
            self._replace_tokens(self.config.working_dir, replacements)
            if self.config.working_dir
            else None
        )
        result = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Engine exited with {result.returncode}")
        if not output_path.exists():
            raise RuntimeError(f"Engine finished but did not create {output_path}")
        return {
            "engine": self.info.name,
            "command": command,
            "working_dir": working_dir,
            "stdout": result.stdout[-4000:],
        }

    @staticmethod
    def _replace_tokens(value: str, replacements: dict[str, str]) -> str:
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
        return value


def load_command_engines(path: Path | None) -> list[CommandEngine]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [CommandEngine(CommandEngineConfig.model_validate(item)) for item in payload.get("engines", [])]
