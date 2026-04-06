# ARPA Micro Series: F1 Mask — Testing & Quality Assurance

This document provides a guide for running the ARPA F1 Mask test suites to ensure both the model and the PII vault are functioning correctly.

## Test Infrastructure Requirements

| Component | Port | Description |
|-----------|------|-------------|
| Redis | 6379 | Redis is required for the PII Vault Manager. |
| Ollama | 11434 | Ollama is required for PII Detection Scenario tests. |
| Model | - | `micro-f1-mask` must be registered in Ollama. |

## Running the Unit Tests (Vault Manager)

These tests verify the logic of the Redis-backed vault, including token generation, session isolation, and reconstruction.

**Execution**:
```bash
python tests/test_vault_manager.py
```

- **Environment**: Requires Redis (e.g., `docker compose up -d`).
- **Success Criteria**: 20/20 tests passed.
- **Key Modules**: `get_or_create_token`, `reconstruct_text`, `clear_session`.

## Running the Scenario Tests (PII Detection)

These tests verify that the fine-tuned model identifies PII across various corporate communication scenarios.

**Execution**:
```bash
python tests/test_pii_scenarios.py
```

- **Environment**: Requires Ollama with `micro-f1-mask` registered.
- **Success Criteria**: 23/23 tests passed.
- **Key Categories**: INDIVIDUAL, FINANCIAL, LOCATION, CONTACT, ACCESS, CORP.

## Troubleshooting

### [ERROR] Model 'micro-f1-mask' not found in Ollama

If you encounter a `404 Not Found` error for the `/api/chat` endpoint, the model must be registered locally first. Run the following command:

```bash
ollama create micro-f1-mask -f Ollama.Modelfile
```

### [ERROR] Redis not available

Ensure the Redis container is running:

```bash
docker compose up -d
```

---
Built & Maintained by ARPA Hellenic Logical Systems
