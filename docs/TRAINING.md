# ARPA Micro Series: F1 Mask — Training Specification

This document provides technical details on the fine-tuning process for the F1 Mask model, ensuring transparency and reproducibility.

## Model Foundation

- **Base Model**: Google Gemma 3 270M Instruct
- **Parameters**: 271,895,168
- **Vocab Size**: 262,144
- **Precision**: 4-bit NF4 Quantization (bitsandbytes)

## Training Methodology

The model was fine-tuned using Supervised Fine-Tuning (SFT) via the HuggingFace PEFT and TRL libraries.

### Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Method | LoRA | Low-Rank Adaptation |
| Rank (r) | 16 | Rank of the update matrices |
| Alpha | 32 | Scaling factor for LoRA |
| Target Modules | All Linear | q_proj, k_proj, v_proj, o_proj, etc. |
| Dropout | 0.05 | Prevention of overfitting |
| Epochs | 3 | Total passes over the dataset |
| Batch Size | 8 | Effective batch (2 per device × 4 accumulation) |
| Learning Rate | 2e-4 | Cosine schedule with 10% warmup |
| Max Length | 2048 | Maximum sequence length |
| Optimizer | AdamW 8-bit | Optimized memory footprint |

## Dataset Specification

- **Type**: Synthetic PII scenarios.
- **Quantity**: 1,000 samples.
- **Provenance**: 100% synthetic generation via high-entropy LLM workflows (Gemini series).
- **Categories**: INDIVIDUAL, FINANCIAL, LOCATION, CONTACT, ACCESS, CORP.

## Hardware & Performance

- **GPU**: NVIDIA GeForce RTX 2070 (or equivalent with 8GB+ VRAM).
- **Training Time**: ~13 minutes for 3 epochs.
- **Memory Footprint**: ~5.8GB VRAM during training (4-bit).

## Metrics & Convergence

- **Final Loss**: 1.079
- **Token Accuracy**: 76.10%
- **Gradient Norm**: 0.29 (Stable convergence)

---
Built & Maintained by ARPA Hellenic Logical Systems
