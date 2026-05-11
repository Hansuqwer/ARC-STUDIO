"""ARC Extension base class."""
import abc
from pathlib import Path


class ArcExtension(abc.ABC):
    @property
    @abc.abstractmethod
    def extension_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def extension_name(self) -> str: ...

    @abc.abstractmethod
    def detect(self, workspace: Path) -> bool: ...

    def inspect(self, workspace: Path) -> dict: ...
