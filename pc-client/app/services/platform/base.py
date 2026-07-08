from abc import ABC, abstractmethod


class PlatformClient(ABC):
    @abstractmethod
    def upload_telemetry(self, payload: dict) -> dict:
        raise NotImplementedError
