# Model artifacts

Trained artifacts are **not** committed to git. In CI/CD they are built by the
training pipeline and shipped in the API Docker image (M2) or stored in
object storage (R2/S3) behind the `model_versions` registry.

Expected artifacts (per version): `model.keras` (or `saved_model/`),
`label_map.json`, `preprocess.json`, `metrics.json`, `tflite/model.tflite`
(offline on-device variant). See `docs/08-ai-pipeline.md`.
