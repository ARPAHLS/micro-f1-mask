<div align="center">

# ARPA MICRO SERIES: F1 MASK

**Zero-Latency PII Scrubbing Middleware for Enterprise Cloud Compliance**

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-efcefa?style=flat-square" alt="License"></a>
<a href="https://arpacorp.net"><img src="https://img.shields.io/badge/series-ARPA_Micro-bae6fd?style=flat-square" alt="Series"></a>
<a href="#pii-categories"><img src="https://img.shields.io/badge/task-PII_Scrubbing-bbf7d0?style=flat-square" alt="Task"></a>
<a href="https://ollama.com/arpacorp/micro-f1-mask"><img src="https://img.shields.io/badge/inference-Ollama-fde68a?style=flat-square" alt="Inference"></a>
<a href="https://redis.io/"><img src="https://img.shields.io/badge/vault-Redis-fecaca?style=flat-square" alt="Vault"></a>
<a href="https://www.python.org/downloads/release/python-3100/"><img src="https://img.shields.io/badge/python-3.10+-bae6fd?style=flat-square" alt="Python"></a>

<br><br>

<a href="#mission">Mission</a> •
<a href="#documentation">Documentation</a> •
<a href="#quick-start">Quick Start</a> •
<a href="#data-generation">Data Generation</a> •
<a href="#pii-categories">PII Categories</a> •
<a href="#deployment">Deployment</a> •
<a href="#contact">Contact</a>

</div>

---

## Mission

ARPA Micro Series: F1 Mask is a purpose-built privacy bridge designed to intercept outgoing LLM prompts, detect and tokenize Personally Identifiable Information (PII) using a high-efficiency 270M parameter model, and forward only sanitized content to cloud APIs. 

The core philosophy is **Privacy by Architecture**: sensitive data never leaves your infrastructure. 

> "Privacy is not something that I'm merely entitled to, it's an absolute prerequisite." — Marlon Brando

**Model Weights**: [arpacorp/micro-f1-mask](https://huggingface.co/arpacorp/micro-f1-mask)
**Source Code**: Training pipeline, middleware proxy, Redis vault, and specialized deployment tools.

## Documentation

Full technical reference library:

- **[Training Specification](docs/TRAINING.md)**: Hardware, hyperparameters, and convergence logs.
- **[Testing & QA Guide](docs/TESTING.md)**: Unit and scenario test execution.
- **[API Reference](docs/API.md)**: FastAPI Bridge endpoint and payload schemas.
- **[Evaluation & Ethics](docs/EVALUATION.md)**: Accuracy, latency, and data provenance.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT / AGENT                            │
│                     "Call John Doe at 555-0123"                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  PHASE A: THE MASK                                               │
│  ┌─────────────┐    ┌───────────────┐    ┌────────────────────┐  │
│  │  F1 Mask    │───▶│  PII Detect   │───▶│  Redis Vault       │  │
│  │  (Ollama)   │    │  replace_pii  │    │  John → [IND_1]    │  │
│  └─────────────┘    └───────────────┘    │  555  → [CON_1]    │  │
│                                          └────────────────────┘  │
│  Scrubbed: "Call [INDIVIDUAL_1] at [CONTACT_1]"                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  PHASE B: THE CLOUD                                              │
│  GPT-4 / Claude / Gemini receives ONLY tokenized text.           │
│  No real PII leaves your network.                                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  PHASE C: THE REVEAL                                             │
│  Cloud response tokens are reconstructed from the Redis Vault.   │
│  "[INDIVIDUAL_1] prefers email" → "John Doe prefers email"       │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
git clone https://github.com/arpahls/micro-f1-mask.git
cd micro-f1-mask

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install project dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Model Registration (Ollama)

```bash
# Register the model from the local merged directory
ollama create micro-f1-mask -f Ollama.Modelfile

# Optional: Register with 4-bit quantization for performance
ollama create micro-f1-mask --quantize q4_K_M -f Ollama.Modelfile
```

### 3. Start Infrastructure

```bash
# Start Redis Vault
docker compose up -d

# Start F1 Mask Bridge (FastAPI Proxy)
python micro_f1_mask_bridge.py
```

## Data Generation

To maintain the privacy of the original 1000-sample dataset, we provide a high-entropy synthetic generator. Users can create their own training data using the provided script.

### Configuration

Modify `synthetic_generator.py` to adjust:
- **Model**: Default is `gemini-2.0-flash-lite` (high speed/low cost).
- **Quantity**: Change the loop range to generate thousands of unique scenarios.
- **Diversity**: Adjust the system prompt to introduce specific industry jargon or PII formats.

```bash
# Generate a new synthetic dataset
python synthetic_generator.py
```

## Production Optimization Roadmap

While this repository provides a fully functional 1,000-sample prototype, reaching 95%+ enterprise accuracy requires the following architectural optimizations:

### 1. Hard-Negative Mining (Re-training)
To push accuracy into the high 90s, the model must iteratively learn from its mistakes:
1. **Scale**: Use the synthetic generator to produce 10,000 - 50,000 highly diverse samples tailored to your industry.
2. **Evaluate**: Run `evaluation.py` continuously against samples of your real-world traffic.
3. **Mine Edge Cases**: Every time the model misses a PII token (a "hard negative"), extract that sentence, generate 500 synthetic variations of that specific edge-case structure, and re-run the LoRA fine-tuning pipeline.

### 2. Human-In-The-Loop (HITL) Workflows
For mission-critical data, we recommend extending the FastAPI Bridge to include human oversight:

- **Pre-Cloud Quarantine (Maximum Security):** Modify the endpoint so that when F1 Mask detects PII, the API payload pauses. The UI highlights the detected entities to the user (e.g., "We found [John Doe]. Click to approve."). The user manually verifies the masking *before* it is authorized to hit the cloud.
- **Post-Reconstruction Review (Quality Control):** Allow the fully automated process to finish. Before the final reconstructed cloud response is saved to a database or emailed to a client, route it to an admin dashboard where a human can manually verify the reconstructed grammar.

## PII Categories

F1 Mask detects and tokenizes 6 core entity categories:

| Category | Token | Examples |
|----------|-------|----------|
| INDIVIDUAL | [INDIVIDUAL_N] | Full names, usernames, aliases |
| FINANCIAL | [FINANCIAL_N] | SSNs, credit cards, IBANs, account IDs |
| LOCATION | [LOCATION_N] | Physical addresses, GPS coords, zip codes |
| CONTACT | [CONTACT_N] | Email addresses, phone numbers |
| ACCESS | [ACCESS_N] | Passwords, API keys, JWT tokens |
| CORP | [CORP_N] | Company names, internal project codenames |

## Deployment

### Multi-Turn Session Management

The Redis Vault ensures that PII mappings remain consistent across a conversation:
- **Idempotency**: The same PII value always yields the same token within a session.
- **Isolation**: Each `session_id` has a unique, protected namespace.
- **Lifecycle**: Sessions auto-expire after a configurable TTL (default: 2 hours).

### Production Checklist

- [ ] Enable Redis password authentication.
- [ ] Configure TLS for the Bridge API endpoint.
- [ ] Set log level to `WARNING` to prevent PII leakage in system logs.
- [ ] Ensure the model is running on local hardware for maximum security.

## Ethics & Responsible Use

### Design Principles

1.  **Privacy by Architecture**: Data protection is enforced at the network layer.
2.  **Minimalist Scope**: 270M parameters focused strictly on scrubbing, avoiding general-purpose LLM risks.
3.  **Synthetic Provenance**: The model was trained exclusively on synthetic data. No real human data was used.

### Usage Disclosure

F1 Mask is designed for enterprise data protection and compliance. It should not be used as a substitute for comprehensive security audits or as a primary defense against targeted adversarial extraction.

## Enterprise Solutions

The public release of **ARPA F1 Mask** serves as a lightweight demonstration of how the *Function One (F1)* architecture can be fine-tuned for structured privacy enforcement. 

For mission-critical infrastructure, ARPA offers an actively maintained, highly robust enterprise tier. Organizations can deploy our gated version out-of-the-box and completely offload the burden of continuous maintenance, bespoke fine-tuning, concept drift avoidance, and rigorous scenario evaluations. 

For enterprise licensing or to discuss tailoring the F1 model to your proprietary data schemas, reach out to: **[input@arpacorp.net](mailto:input@arpacorp.net)**

## Contact

- **Commercial**: [input@arpacorp.net](mailto:input@arpacorp.net)
- **Security**: security@arpacorp.net
- **Issues**: [GitHub Issues](https://github.com/arpahls/micro-f1-mask/issues)
- **Organization**: [ARPA Hellenic Logical Systems](https://arpacorp.net)

---

<div align="center">

<img src="https://raw.githubusercontent.com/ARPAHLS/skillware/main/assets/arpalogo.png" width="50px">

Built & Maintained by ARPA Hellenic Logical Systems

</div>
