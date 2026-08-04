"""Model registry: capability → classifier provider.

A capability is a label for an analysis type ("disease" today; pest, soil,
yield later). The registry is the seam that lets a model swap be a registry
promotion instead of a code change (docs/08-ai-pipeline.md). Adapters
register themselves at import time or are wired by the app's composition root.
"""

from app.ai.types import DiseaseClassifier, InferenceError


class CapabilityNotRegisteredError(InferenceError):
    pass


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, DiseaseClassifier] = {}

    def register(self, capability: str, classifier: DiseaseClassifier) -> None:
        self._providers[capability] = classifier

    def unregister(self, capability: str) -> None:
        self._providers.pop(capability, None)

    def get(self, capability: str) -> DiseaseClassifier:
        try:
            return self._providers[capability]
        except KeyError:
            raise CapabilityNotRegisteredError(
                f"no classifier registered for capability: {capability}"
            ) from None

    def is_available(self, capability: str) -> bool:
        return capability in self._providers

    def available(self) -> list[str]:
        return sorted(self._providers)


registry = ModelRegistry()
