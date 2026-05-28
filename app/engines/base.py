from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas import EngineInfo, GenerationMode, OutputFormat


class GenerationEngine(ABC):
    info: EngineInfo

    def can_run(self, mode: GenerationMode, output_format: OutputFormat) -> bool:
        return mode in self.info.supports and output_format in self.info.output_formats

    @abstractmethod
    def generate(
        self,
        *,
        job_id: str,
        mode: GenerationMode,
        input_paths: list[Path],
        output_path: Path,
        output_format: OutputFormat,
    ) -> dict:
        """Generate a 3D model and write it to output_path."""
