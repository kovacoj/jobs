from abc import ABC, abstractmethod

from scraper.models import SourceResult


class JobSource(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> SourceResult:
        raise NotImplementedError
