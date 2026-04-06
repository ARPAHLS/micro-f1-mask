# ARPA Micro Series: F1 Mask — API Reference

This document provides a technical specification for the FastAPI Bridge proxy, serving as a zero-latency PII scrubbing middleware.

## Request Interface

- **Endpoint**: `/v1/chat/completions` (OpenAI Compatible)
- **Method**: POST
- **Payload Schema**:

```json
{
    "model": "gpt-4",
    "session_id": "unique-session-id-001",
    "messages": [
        {"role": "user", "content": "Send it to john.doe@acme.com for review."}
    ],
    "temperature": 0.7,
    "stream": false
}
```

## API Behavior

1.  **PII Extraction**: The Bridge sends the user content to the `micro-f1-mask` model in Ollama.
2.  **Vault Storage**: Detected PII (e.g., `john.doe@acme.com`) is stored in Redis under the `session_id`.
3.  **Scrubbing**: The user content is masked (e.g., `Send it to [CONTACT_1] for review.`).
4.  **Cloud Forwarding**: The masked prompt is sent to the `CLOUD_LLM_URL` (OpenAI, Claude, etc.).
5.  **Reconstruction**: The Cloud LLM response is scanned for tokens (e.g., `[CONTACT_1]`) and replaced with original values.
6.  **Response**: The user receives the full reconstructed response.

## Session Management

- **Persistence**: Mapping is stored in Redis.
- **Isolation**: Each `session_id` has a unique namespace.
- **Consistency**: Within a session, the same PII value always maps to the same token.
- **TTL**: Default expiration is 7,200 seconds (2 hours).

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_URL | http://localhost:11434/api/chat | Endpoint for PII detection. |
| F1_MASK_MODEL | micro-f1-mask | Ollama model name. |
| CLOUD_LLM_URL | https://api.openai.com/v1/chat/completions | Target cloud API. |
| REDIS_HOST | localhost | Redis host. |

---
Built & Maintained by ARPA Hellenic Logical Systems
