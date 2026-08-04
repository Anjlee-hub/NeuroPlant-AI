# NeuroPlant AI — AI / ML

Training pipelines, model artifacts and the versioned model registry.

```
ai/
├── training/      # data pipeline, augmentation, train/eval scripts (M2)
├── datasets/      # source datasets (gitignored, see datasets/README.md)
├── models/        # artifacts + label maps (gitignored, see models/README.md)
└── notebooks/     # dataset curation + EDA
```

Versioning: every trained artifact is registered in the `model_versions` table
with its `dataset_version` and metrics — see `docs/08-ai-pipeline.md`.
