---
license: apache-2.0
language:
- en
tags:
- zero-latency
- pii-scrubbing
- pii
- compliance
- privacy
- function-calling
- arpa
- micro-f1-mask
- micro-series
pipeline_tag: text-generation
library_name: transformers
base_model: google/gemma-3-270m-it
datasets:
- synthetic
model-index:
- name: micro-f1-mask
  results: []
---

<div align="center">

# ARPA MICRO SERIES: F1 MASK

**Zero-Latency PII Scrubbing - 270M Parameter Middleware**

<img src="https://img.shields.io/badge/base-Gemma_3_270M-bae6fd?style=flat-square" alt="Base Model">
<img src="https://img.shields.io/badge/task-PII_Scrubbing-efcefa?style=flat-square" alt="Task">
<img src="https://img.shields.io/badge/training-PEFT_LoRA-bbf7d0?style=flat-square" alt="Training">
<img src="https://img.shields.io/badge/license-Apache_2.0-fde68a?style=flat-square" alt="License">

</div>

---

**ARPA Micro Series: F1 Mask** is a high-performance fine-tuned model built to provide real-time identification and tokenization of Personally Identifiable Information (PII) for secure cloud computing. 

Developed by [ARPA Hellenic Logical Systems](https://arpacorp.net), it acts as a privacy firewall for incoming/outgoing LLM prompts.

**GitHub**: [arpahls/micro-f1-mask](https://github.com/arpahls/micro-f1-mask) — Full training pipeline, Redis vault, and infrastructure.

## Model Summary

F1 Mask is a specialized fine-tune of [Gemma 3 270M IT](https://huggingface.co/google/gemma-3-270m-it). It is trained exclusively to output structured `replace_pii` function calls, effectively mapping sensitive data to safe tokens before they reach cloud-based LLMs.

## Quick Start

### 1. Register with Ollama

```bash
# Direct SafeTensors registration
ollama create micro-f1-mask --from arpacorp/micro-f1-mask

# Run detection
ollama run micro-f1-mask "John Doe called from 555-0123 about invoice GB29NWBK60161331926819."
```

### 2. Python (Transformers)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("arpacorp/micro-f1-mask")
tokenizer = AutoTokenizer.from_pretrained("arpacorp/micro-f1-mask")

prompt = """<start_of_turn>user
You are Micro F1 Mask. Extract PII and output the 'replace_pii' function call.
Draft an email to Jane Smith at jane@example.com.<end_of_turn>
<start_of_turn>model
"""

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.0)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## Binary Mapping & Tokens

The model uses a deterministic tokenization scheme:

| Category | Token |
|----------|-------|
| INDIVIDUAL | [INDIVIDUAL_N] |
| FINANCIAL | [FINANCIAL_N] |
| LOCATION | [LOCATION_N] |
| CONTACT | [CONTACT_N] |
| ACCESS | [ACCESS_N] |
| CORP | [CORP_N] |

### Example Output

```json
{
  "name": "replace_pii",
  "arguments": {
    "entities": [
      {"type": "INDIVIDUAL", "val": "Jane Smith", "id": "[INDIVIDUAL_1]"},
      {"type": "CONTACT", "val": "jane@example.com", "id": "[CONTACT_1]"}
    ]
  }
}
```

## Training Methodology

- **Dataset**: 1,000 synthetic samples generated via high-entropy LLM workflows.
- **Method**: PEFT / LoRA (Rank 16, Alpha 32).
- **Epochs**: 3.
- **Accuracy**: 76.10% (token-level generation).
- **Latency**: Sub-50ms (inference on RTX 2070).

## Ethical Considerations

**Data Provenance**: No real PII was used in the training of this model. All examples were synthetically generated to mimic enterprise communication patterns.

**Intended Use**: This model is designed for middleware. It is not intended to be used as a conversational assistant. It is a one-way security gate that focuses exclusively on privacy enforcement.

---

<div align="center">

<img src="https://raw.githubusercontent.com/ARPAHLS/skillware/main/assets/arpalogo.png" width="50px">

Built by [ARPA Hellenic Logical Systems](https://arpacorp.net)

</div>
