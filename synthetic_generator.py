"""
ARPA Micro Series: F1 Mask — Synthetic Data Generator
-----------------------------------------------------
Author: ARPA Hellenic Logical Systems
License: Apache 2.0

This script generates high-entropy synthetic training data for PII scrubbing. 
It uses the Google GenAI platform (Gemini) to create authentic, messy, 
corporate communication snippets containing injected PII entities.

CONFIGURATION:
- MODEL_ID: Default is "gemini-2.5-flash-lite" (optimal for speed/cost).
- num_samples: Adjust the generate_dataset call at the bottom to set quantity.
- PII_MAPPING: Modify the Faker-based generators to introduce new PII types.
- temperature: Set to 1.2 in GenerateContentConfig for maximum output diversity.

PREREQUISITES:
- pip install faker google-genai python-dotenv
- A valid GEMINI_API_KEY in your .env file.
"""

import json
import random
from faker import Faker
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

# --- USER CONFIGURABLE PARAMETERS ---
# Select the model for generation (Gemini options: gemini-2.0-flash, gemini-1.5-pro, etc.)
MODEL_ID = "gemini-2-flash-lite"

# Target file for the training dataset
OUTPUT_FILE = "synthetic_pii_dataset.jsonl"

# Number of samples to generate for a full training session
TARGET_SAMPLES = 1000
# -----------------------------------

client = genai.Client()
fake = Faker()

# PII Ontology and Generation logic using Faker
PII_MAPPING = {
    "INDIVIDUAL": lambda: random.choice([fake.name(), fake.user_name()]),
    "FINANCIAL": lambda: random.choice([fake.ssn(), fake.credit_card_number(), fake.iban()]),
    "LOCATION": lambda: random.choice([fake.address().replace("\n", ", "), fake.zipcode()]),
    "CONTACT": lambda: random.choice([fake.email(), fake.phone_number()]),
    "ACCESS": lambda: random.choice([fake.password(length=16), f"sk_test_{fake.password(length=24)}"]),
    "CORP": lambda: random.choice([fake.company(), f"Project {fake.catch_phrase().split()[0]}"])
}

def generate_sample():
    """Generates a single synthetic PII detection sample using the LLM."""
    # Randomly select between 1 and 4 PII entities to inject
    num_pii = random.randint(1, 4)
    target_piis = []
    
    for i in range(num_pii):
        pii_type = random.choice(list(PII_MAPPING.keys()))
        pii_val = PII_MAPPING[pii_type]()
        token_id = f"[{pii_type}_{i+1}]"
        
        target_piis.append({
            "type": pii_type,
            "val": pii_val,
            "id": token_id
        })
        
    system_instruction = f"""You are a synthetic data generator for an enterprise compliance pipeline.
Create a very authentic, messy, short corporate communication (like a slack message, email snippet, customer service log, or Jira ticket).

You MUST seamlessly inject the following exact PII values into the text:
{json.dumps(target_piis, indent=2)}

RULES:
1. Output MUST be highly authentic human communication, including occasional typos, jargon, or corporate abbreviations.
2. VARY THE TERMINOLOGY! If a financial value is provided, call it "account", "ID", "reference #", or just drop it in.
3. Output EXACTLY a JSON document with two keys:
   - "raw_text": The messy text containing the PII.
   - "tool_call": A valid json representation of the replace_pii function target.

Example Output:
{{
  "raw_text": "Team, run a check on Jane Doe. Her social is 483-39-3838.",
  "tool_call": {{"name": "replace_pii", "arguments": {{"entities": [{{"type": "INDIVIDUAL", "val": "Jane Doe", "id": "[INDIVIDUAL_1]"}}, {{"type": "FINANCIAL", "val": "483-39-3838", "id": "[FINANCIAL_1]"}}]}}}}
}}
"""
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=system_instruction,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=1.2
            )
        )
        return response.text
    except Exception as e:
        print(f"Generation error: {e}")
        return None

def generate_dataset(num_samples=TARGET_SAMPLES, output_file=OUTPUT_FILE):
    """Orchestrates the generation of a full dataset file in JSONL format."""
    print(f"Initializing ARPA Data Generation Pipeline...")
    print(f"Target: {num_samples} samples | Model: {MODEL_ID}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        success_count = 0
        
        while success_count < num_samples:
            sample_str = generate_sample()
            
            if sample_str:
                try:
                    sample_data = json.loads(sample_str)
                    f.write(json.dumps(sample_data) + '\n')
                    success_count += 1
                    
                    if success_count % 50 == 0:
                        print(f"Progress: {success_count}/{num_samples} samples generated.")
                        
                except json.JSONDecodeError:
                    continue

if __name__ == "__main__":
    generate_dataset()
