# Security Policy

## Supported Versions

Specifically for the ARPA Micro Series: F1 Mask, we provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < v1.0  | :x:                |

## Reporting a Vulnerability

We take the security of PII-handling middleware seriously. If you find a vulnerability, please do NOT open a public issue. Instead, follow these steps:

1.  **Email Disclosure**: Send a detailed report to security@arpacorp.net.
2.  **Acknowledgment**: You will receive an acknowledgment within 48 hours.
3.  **Correction**: We will work on a fix and release it as a security advisory.
4.  **Public Disclosure**: Once the fix is released, we will publicly disclose the vulnerability (if appropriate).

## Best Practices for PII Handling

When deploying ARPA Micro Series: F1 Mask, always follow these guidelines:

1.  **Isolated Redis**: Run Redis in a protected network environment. Use a strong password and TLS if possible.
2.  **Audit Logging**: Enable logging on the Bridge, but ensure the log level is set to `WARNING` or higher to avoid logging the raw prompts containing PII.
3.  **Session TTL**: Configure the Redis TTL (`REDIS_TTL`) to the minimum required for your business case (default is 2 hours).
4.  **TLS Everywhere**: Always use HTTPS/TLS for the FastAPI Bridge endpoint to protect data in transit.
5.  **Rotate Keys**: Regularly rotate any API keys stored in your `.env` file.
6.  **Local Execution**: Ensure the model is running on local infrastructure (Ollama/Local GPU) to maintain the "PII never leaves the network" guarantee.
