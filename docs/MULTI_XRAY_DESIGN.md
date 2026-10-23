# MedTruth AI — Multi-X-ray Design

## Product goal

MedTruth AI is planned as one application for four specialized X-ray pathways: chest, bones and joints, spine, and dental. It combines image-specific model outputs with the existing report-text analysis, retrieval, explanation, and verification pipeline.

**Status:** This document defines the target architecture. It does not mean all four models are implemented or clinically validated. The current repository and configured dependencies must be checked before enabling a specialty.

## User workflow

1. Select the X-ray specialty and supported view.
2. Upload a supported image.
3. Validate the file, image dimensions, format, and quality; reject unreadable or unsupported input.
4. Route the image only to a model whose documented scope supports that anatomy, view, and task.
5. Normalize model outputs into a structured finding schema.
6. Generate a clearly labelled AI draft and a plain-language explanation using only supported findings and vetted evidence.
7. Show limitations, uncertainty, model/version provenance, and clinician-review status.

## Specialty pathways

| Pathway | Initial scope | Research starting point | Important boundary |
|---|---|---|---|
| Chest | Selected chest radiographic findings | Chest-specific pretrained models, evaluated against their current model cards and access terms | A chest model is not a general X-ray interpreter. |
| Bones and joints | Start with supported upper-extremity studies and a narrow classification task | Stanford MURA as a research dataset | MURA normal/abnormal labels do not make a model a universal fracture detector. |
| Spine | Choose one region and one defined task before selecting a model | Dataset/model selection is pending task definition | Do not reuse a general bone model without evidence it supports the spinal task. |
| Dental | Start with panoramic OPG images and selected findings | DentalOPG-1550 as a research candidate | Confirm data licensing, annotation quality, and suitability; do not claim all dental conditions are supported. |

These are research directions, not endorsements or claims of clinical performance. Verify model availability, licenses, intended use, data rights, preprocessing requirements, and model cards before integration.

## Target architecture

```text
React + Vite interface
  └─ Dashboard, upload, image viewer, findings, report studio
       ↓
FastAPI API layer
  └─ Authentication/authorization, validation, request IDs, job status
       ↓
Image ingestion and quality control
  └─ Safe decoding, format/dimension limits, metadata handling, quality warnings
       ↓
Model registry and specialty router
  ├─ Chest inference adapter
  ├─ Bone/joint inference adapter
  ├─ Spine inference adapter
  └─ Dental inference adapter
       ↓
Normalized finding schema
       ↓
Existing MedTruth AI agents
  ├─ Analysis
  ├─ Evidence retrieval
  ├─ Explanation
  └─ Verification
       ↓
AI-generated draft report → clinician review workflow
```

Keep each model behind a common adapter interface, but preserve model-specific preprocessing and output semantics. The router must fail closed when the requested specialty, view, or task is unsupported.

## Normalized finding contract

Each result should contain, where available:

- Study/request ID and specialty/anatomy.
- Model identifier, version, and task.
- Model-produced finding label and anatomical location.
- Raw score and its documented meaning; do not label a score as a calibrated probability unless calibration has been demonstrated.
- Localization only when the model supports it.
- Image-quality warnings, uncertainty/limitations, and review status.
- Source provenance linking report text to image-model output or external evidence.

Do not invent findings or populate missing model outputs with language-model guesses. The explanation model may explain supported predictions but must not independently diagnose from the image.

## Suggested API surface

- `GET /api/health` — service health.
- `GET /api/models` — enabled models, versions, intended tasks, and supported inputs.
- `POST /api/image/analyze?modality=chest|bone|spine|dental&view=...` — validate and analyze a supported image.
- `GET /api/image/jobs/{job_id}` — job status and permitted results, if asynchronous inference is used.
- `POST /api/report/draft` — create a structured draft from available analysis results.
- Preserve existing report-text endpoints such as `POST /api/analyze` and `POST /api/extract`.

Use authenticated access, upload size limits, safe file decoding, request timeouts, rate limits, and access-controlled result retrieval. Avoid logging raw images or unnecessary patient identifiers.

## Report layout

1. **Examination information:** selected anatomy, view, file details, and quality warnings.
2. **AI-generated observations:** only model-supported findings and appropriately described scores.
3. **Plain-language explanation:** explain the output without strengthening its certainty.
4. **Evidence and traceability:** model/version, source provenance, and applicable limitations.
5. **Review status:** clearly mark the output as an AI-generated draft until an authorized clinician reviews it. Never imply that a clinician approved an unreviewed result.

## Implementation phases

1. **Foundation:** confirm the current repository state, add image intake validation, define the finding schema, and implement the model registry/router contract.
2. **First pathway:** integrate one chest-specific model and demonstrate the full upload-to-draft workflow with approved test data.
3. **Bone/joint:** add one supported anatomy/task, then evaluate independently.
4. **Spine:** define a specific spinal task and data source before model selection and implementation.
5. **Dental:** start with panoramic OPG and a narrowly scoped model/dataset.
6. **Release gates:** run technical, model, report-integrity, security, and clinical review checks for each specialty separately.

Do not treat a module as enabled just because its UI option exists. Expose an explicit “model unavailable / unsupported input” state when inference is not configured.

## Validation and safety gates

- Split data at patient level and prevent duplicate/leakage between training and evaluation.
- Use a held-out, representative dataset and report task-appropriate metrics, confidence intervals, and subgroup performance.
- Evaluate across institutions, devices, image quality, and relevant populations where possible.
- Test wrong modality, unsupported anatomy/view, corrupted files, low quality, and ambiguous outputs.
- Have qualified clinicians review omissions, false positives, false negatives, anatomy errors, negation/uncertainty, and misleading explanations.
- Track model/data versions, evaluation results, known limitations, and changes that trigger revalidation.
- Establish data permissions, de-identification, privacy/security controls, retention rules, and ethics review before using real patient data.
- Determine applicable medical-device regulations and approvals before any clinical deployment.

This project should remain a research/educational prototype and must not be presented as a validated diagnostic device without the appropriate evidence, oversight, and authorization.

## Definition of done

A specialty is ready for a research demonstration only when its model is configured, its supported input scope is documented, automated tests pass, results are clearly marked as AI-generated, unsupported cases fail safely, and a task-specific evaluation report is recorded. Clinical deployment requires additional validation and regulatory review.
