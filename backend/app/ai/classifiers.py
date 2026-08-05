"""Disease classifier adapters behind the :class:`DiseaseClassifier` protocol.

Two providers ship with the app:

- :class:`RuleBaselineClassifier` — a deterministic fallback that maps each
  scan to a catalog disease from a stable hash of the image bytes. It lets the
  whole detection pipeline run end-to-end in dev/tests *without* a trained
  artifact and is clearly marked ``provider="baseline"`` so callers (and the
  UI) can tell rule output apart from model-backed output.
- :class:`LocalTensorFlowClassifier` — the production provider. Both the
  ``tensorflow`` import and the model-artifact load are deferred to first
  :meth:`predict`, so the base install and an artifact-free checkout stay
  importable. Missing TF/artifact raises :class:`ModelUnavailableError`,
  letting :func:`build_disease_classifier` fall back to the baseline.

The label→class index comes from a :class:`DiseaseCatalog`, so every prediction
is traceable to the exact label space it was trained/served against
(docs/08-ai-pipeline.md).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.ai.datasets import DiseaseCatalog
from app.ai.gradcam import RuleBaselineSaliency, TensorFlowGradCAM
from app.ai.preprocess import ImageValidationError, get_preprocessor
from app.ai.types import (
    ClassifierPrediction,
    DiseaseClassifier,
    ExplainabilityProvider,
    ImageData,
    InferenceError,
    ModelInfo,
    ModelUnavailableError,
    PredictedDisease,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Confidence used for rule-baseline output — deliberately below the model
# threshold so consumers can distinguish "best-effort" from real model output.
BASELINE_CONFIDENCE = 0.6

# Number of ranked candidates returned by the local TF provider (Task 5.2
# stores the full top-5 as confidence metadata).
TOP_K = 5


class RuleBaselineClassifier:
    """Deterministic, artifact-free disease classifier (provider="baseline")."""

    capability = "disease"

    def __init__(
        self,
        catalog: DiseaseCatalog,
        *,
        version: str = "baseline-v1",
    ) -> None:
        self._catalog = catalog
        self._index_to_name = {i: name for name, i in catalog.label_map.items()}
        # Task 5.2 — deterministic saliency (no model required).
        self.explainer: ExplainabilityProvider = RuleBaselineSaliency()
        self.model_info = ModelInfo(
            name="rule-baseline",
            capability="disease",
            provider="baseline",
            version=version,
        )

    def predict(self, image: ImageData) -> ClassifierPrediction:
        if self._catalog.class_count == 0:
            raise InferenceError("disease catalog is empty; seed the catalog first")
        # Stable pick: same bytes → same disease (testable, demoable).
        digest = hashlib.sha256(image.image_bytes).digest()
        index = digest[0] % self._catalog.class_count
        name = self._index_to_name[index]
        top = PredictedDisease(
            disease_name=name,
            confidence=BASELINE_CONFIDENCE,
            disease_id=self._catalog.disease_ids.get(name),
            crop_id=self._catalog.disease_crops.get(name),
        )
        return ClassifierPrediction(top=top, model=self.model_info)


class LocalTensorFlowClassifier:
    """Keras/TensorFlow classifier that loads its artifact lazily.

    Importing this class never touches ``tensorflow``; the module and the
    artifact are both pulled in on the first :meth:`predict`. Absent TF or a
    missing/corrupt artifact raises :class:`ModelUnavailableError` instead of
    crashing the process, so composition can degrade to the baseline.
    """

    capability = "disease"

    def __init__(
        self,
        catalog: DiseaseCatalog,
        artifact_path: str,
        *,
        name: str = "efficientnet-baseline",
        version: str = "v1",
    ) -> None:
        self._catalog = catalog
        self._artifact_path = Path(artifact_path)
        self._model: Any = None  # keras Model, populated lazily by _load()
        self._tensorflow: Any = None  # module reference, set by _load()
        self._explainer: ExplainabilityProvider | None = None  # built lazily
        self._index_to_name = {i: name for name, i in catalog.label_map.items()}
        self.model_info = ModelInfo(
            name=name,
            capability="disease",
            provider="local_tf",
            version=version,
        )

    @property
    def is_available(self) -> bool:
        return self._artifact_path.exists()

    @property
    def explainer(self) -> ExplainabilityProvider | None:
        """Grad-CAM built from the loaded model (Task 5.2).

        Lazily loads the artifact (raising :class:`ModelUnavailableError` when
        TensorFlow or the artifact is missing) and caches the provider, so the
        heatmap always targets the exact model that produced the prediction.
        ``None`` is never returned once available — access after a failed load
        raises instead, so callers degrade explicitly rather than silently.
        """
        if self._explainer is None:
            self._load()
            self._explainer = TensorFlowGradCAM(
                self._model,
                get_preprocessor("default"),
                self._catalog.label_map,
            )
        return self._explainer

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import tensorflow as tf
        except ImportError as exc:  # pragma: no cover - exercised in CI envs
            raise ModelUnavailableError(
                "tensorflow is not installed (pip install -r requirements-ml.txt)"
            ) from exc
        if not self._artifact_path.exists():
            raise ModelUnavailableError(f"model artifact not found: {self._artifact_path}")
        try:
            self._model = tf.keras.models.load_model(str(self._artifact_path))
            self._tensorflow = tf
            logger.info(
                "model_loaded",
                path=str(self._artifact_path),
                version=self.model_info.version,
            )
        except Exception as exc:
            raise ModelUnavailableError(
                f"failed to load model artifact {self._artifact_path}: {exc}"
            ) from exc

    def predict(self, image: ImageData) -> ClassifierPrediction:
        self._load()
        try:
            import numpy as np

            tf = self._tensorflow
            assert tf is not None
            preprocessor = get_preprocessor("default")
            tensor = preprocessor.preprocess(image)  # (H, W, 3) float32
            batch = np.expand_dims(tensor, axis=0)  # (1, H, W, 3)
            logits = self._model(batch, training=False)  # (1, C)
            probs = tf.nn.softmax(logits[0]).numpy()
            order = np.argsort(probs)[::-1][:TOP_K]
            predictions: list[PredictedDisease] = []
            for idx in order:
                name = self._index_to_name.get(int(idx))
                if name is None:
                    continue
                predictions.append(
                    PredictedDisease(
                        disease_name=name,
                        confidence=float(probs[idx]),
                        disease_id=self._catalog.disease_ids.get(name),
                        crop_id=self._catalog.disease_crops.get(name),
                    )
                )
            if not predictions:
                raise InferenceError("model output did not map to any catalog disease")
            return ClassifierPrediction(
                top=predictions[0],
                rankings=tuple(predictions[1:]),
                model=self.model_info,
            )
        except ImageValidationError:
            raise
        except InferenceError:
            raise
        except Exception as exc:
            raise InferenceError(f"prediction failed: {exc}") from exc


def build_disease_classifier(catalog: DiseaseCatalog) -> DiseaseClassifier:
    """Compose the serving classifier: TF artifact when present, else baseline.

    Logs which provider won so scans record it faithfully (provider is part of
    the scan row, and the UI labels baseline output accordingly).
    """
    settings = get_settings()
    tf_model = LocalTensorFlowClassifier(
        catalog,
        settings.disease_model_path,
        version=settings.disease_model_version,
    )
    if tf_model.is_available:
        logger.info(
            "disease_classifier=local_tensorflow",
            path=settings.disease_model_path,
            version=settings.disease_model_version,
        )
        return tf_model
    logger.warning(
        "disease_model_missing; using rule baseline",
        path=settings.disease_model_path,
    )
    return RuleBaselineClassifier(catalog)
