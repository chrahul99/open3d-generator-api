from app.config import Settings
from app.engines.base import GenerationEngine
from app.engines.command import load_command_engines
from app.engines.mock import MockEngine


class EngineRegistry:
    def __init__(self, settings: Settings):
        engines: list[GenerationEngine] = [MockEngine()]
        engines.extend(load_command_engines(settings.engines_config))
        self._engines = {engine.info.name: engine for engine in engines}

    def list(self):
        return [engine.info for engine in self._engines.values()]

    def get(self, name: str) -> GenerationEngine | None:
        return self._engines.get(name)
