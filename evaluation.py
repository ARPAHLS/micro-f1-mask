import time
import json
import httpx
import statistics
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("F1_MASK_MODEL", "arpacorp/micro-f1-mask")

def run_evaluation(num_samples=50):
    print(f"==================================================")
    print(f"  ARPA F1 Mask — Zero-Latency Evaluation")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Samples: {num_samples}")
    print(f"==================================================\n")

    test_prompts = [
        "Hey, call John Doe at (555) 123-4567 about his account.",
        "Ship the package to 742 Evergreen Terrace, Springfield.",
        "My SSN is 483-39-3838, please update my file.",
        "Wire the funds to GB29NWBK60161331926819 ASAP.",
        "The staging API key is sk_test_4eC39HqLyjWDarjtT1zdp7dc."
    ]

    # Repeat prompts to get enough samples
    prompts = (test_prompts * (num_samples // len(test_prompts) + 1))[:num_samples]

    latencies = []
    successes = 0

    try:
        # Warm-up request
        httpx.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Warmup prompt"}],
            "stream": False,
            "format": "json"
        }, timeout=30.0)
    except Exception as e:
        print(f"[ERROR] Could not connect to Ollama. Ensure the model is running: {e}")
        return

    print("Running evaluation...")
    
    for i, prompt in enumerate(prompts):
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json"
        }
        
        start_time = time.perf_counter()
        response = httpx.post(OLLAMA_URL, json=payload, timeout=10.0)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            successes += 1

    if not latencies:
        print("No successful evaluations.")
        return

    avg_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]

    print("\n[SUCCESS] Evaluation Complete")
    print(f"Success Rate: {successes}/{num_samples} ({(successes/num_samples)*100:.1f}%)")
    print(f"Average Latency: {avg_latency:.2f} ms")
    print(f"Median Latency:  {median_latency:.2f} ms")
    print(f"P95 Latency:     {p95_latency:.2f} ms")

if __name__ == "__main__":
    run_evaluation()
