# ARPA Micro Series: F1 Mask — Evaluation & Performance

This document provides a summary of the performance metrics and ethical considerations for the F1 Mask fine-tuned model.

## Accuracy & Precision

The model's performance was evaluated based on its ability to generate structured function calls that correctly map PII to their respective classes.

### Case Detection Metrics

| Category | Detection Rate | Reliability |
|----------|----------------|-------------|
| INDIVIDUAL | 98.4% | High accuracy for full names and usernames. |
| FINANCIAL | 97.8% | Robust with IBANs and SSNs alike. |
| LOCATION | 92.1% | High for zipcodes; slightly context-dependent for short addresses. |
| CONTACT | 99.1% | Excellent with emails and varied phone formats. |
| ACCESS | 96.5% | Very reliable for API keys and structured secrets. |
| CORP | 91.5% | Good for company names and project codenames. |

## End-to-End Latency

The F1 Mask is designed for **zero-latency** operation, ensuring minimal impact on the user's conversation flow.

- **Detection Time**: < 50ms per prompt (256 tokens) on a local GPU.
- **Vault Overhead**: < 5ms (Redis hash-set operations).
- **Total Overhead**: Sub-100ms for the full PII scrubbing pipeline.

## Data Ethics & Privacy

### Synthetic Data Provenance

The ARPA Micro Series is trained on **100% synthetic data**. No real human data or PII was used during any stage of development. The scenarios were generated using high-entropy LLM workflows to mimic authentic, messy corporate communication patterns without risking data privacy during training.

### Zero-Leaking Architecture

The model is hosted **locally**. At no point does the raw, unscrubbed prompt containing real PII leave your infrastructure. Only the tokenized and sanitized version is forwarded to third-party cloud services.

## Known Limitations

- **Adversarial Names**: Very short, common-word names (e.g., "Will", "Hope") can sometimes be missed if the context is highly ambiguous.
- **Code Payne**: PII nested inside complex code blocks or non-standard JSON may require additional rule-based pre-processing for maximum safety.

---
Built & Maintained by ARPA Hellenic Logical Systems
