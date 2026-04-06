"""
ARPA Micro Series: F1 Mask — PII Detection Scenario Tests
Requires: Ollama with 'micro-f1-mask' model registered.

These tests verify that the trained model correctly detects PII
across various scenarios, entity types, and edge cases.
"""

import sys
import os
import json
import unittest
import httpx

# Ollama endpoint
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("F1_MASK_MODEL", "micro-f1-mask")


def query_f1_mask(text: str) -> dict:
    """Send a text to F1 Mask via Ollama and parse the response."""
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "format": "json",
    }
    try:
        response = httpx.post(OLLAMA_URL, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"\n[ERROR] Model '{MODEL_NAME}' not found in Ollama.")
            print(f"        Register it locally using: 'ollama create {MODEL_NAME} -f Ollama.Modelfile'")
        raise e
    
    result = response.json()

    content = result.get("message", {}).get("content", "{}")
    if isinstance(content, str):
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            data = json.loads(match.group(0)) if match else {}
    else:
        data = content

    return data


def get_entities(text: str) -> list:
    """Extract entities list from F1 Mask response."""
    data = query_f1_mask(text)
    return data.get("arguments", {}).get("entities", [])


def get_entity_types(entities: list) -> set:
    """Get the set of entity types from an entities list."""
    return {e["type"] for e in entities}


def get_entity_values(entities: list) -> set:
    """Get the set of entity values from an entities list."""
    return {e["val"] for e in entities}


# ──────────────────────────────────────────────────────────────
# Test: Individual Entity Types
# ──────────────────────────────────────────────────────────────

class TestIndividualDetection(unittest.TestCase):
    """Test detection of INDIVIDUAL entities (names, usernames)."""

    def test_full_name(self):
        entities = get_entities(
            "Hey, can you get John Smith on the phone?"
        )
        values = get_entity_values(entities)
        self.assertTrue(
            any("John Smith" in v for v in values),
            f"Expected 'John Smith' in {values}"
        )

    def test_username(self):
        entities = get_entities(
            "Yo jsmith42, can you push the latest build?"
        )
        types = get_entity_types(entities)
        self.assertIn("INDIVIDUAL", types)


class TestFinancialDetection(unittest.TestCase):
    """Test detection of FINANCIAL entities."""

    def test_ssn(self):
        entities = get_entities(
            "His social is 483-39-3838, verify it please."
        )
        values = get_entity_values(entities)
        self.assertTrue(
            any("483-39-3838" in v for v in values),
            f"Expected SSN in {values}"
        )

    def test_iban(self):
        entities = get_entities(
            "Wire the funds to GB29NWBK60161331926819 ASAP."
        )
        values = get_entity_values(entities)
        self.assertTrue(
            any("GB29NWBK" in v for v in values),
            f"Expected IBAN in {values}"
        )

    def test_credit_card(self):
        entities = get_entities(
            "Charge it to 4532015112830366, standard rate."
        )
        types = get_entity_types(entities)
        self.assertIn("FINANCIAL", types)


class TestLocationDetection(unittest.TestCase):
    """Test detection of LOCATION entities."""

    def test_full_address(self):
        entities = get_entities(
            "Ship it to 742 Evergreen Terrace, Springfield, IL 62704."
        )
        types = get_entity_types(entities)
        self.assertIn("LOCATION", types)

    def test_zipcode(self):
        entities = get_entities(
            "The office in 90210 needs the new monitors."
        )
        types = get_entity_types(entities)
        self.assertIn("LOCATION", types)


class TestContactDetection(unittest.TestCase):
    """Test detection of CONTACT entities."""

    def test_email(self):
        entities = get_entities(
            "Send it to john.doe@acmecorp.com for review."
        )
        values = get_entity_values(entities)
        self.assertTrue(
            any("john.doe@acmecorp.com" in v for v in values),
            f"Expected email in {values}"
        )

    def test_phone_number(self):
        entities = get_entities(
            "Call me back at (555) 123-4567 when you get a chance."
        )
        types = get_entity_types(entities)
        self.assertIn("CONTACT", types)


class TestAccessDetection(unittest.TestCase):
    """Test detection of ACCESS entities (keys, passwords)."""

    def test_api_key(self):
        entities = get_entities(
            "The staging API key is sk_test_4eC39HqLyjWDarjtT1zdp7dc."
        )
        values = get_entity_values(entities)
        self.assertTrue(
            any("sk_test_" in v for v in values),
            f"Expected API key in {values}"
        )

    def test_password(self):
        entities = get_entities(
            "Reset his password to P@ssw0rd!2024, it's temporary."
        )
        types = get_entity_types(entities)
        self.assertIn("ACCESS", types)


class TestCorpDetection(unittest.TestCase):
    """Test detection of CORP entities."""

    def test_company_name(self):
        entities = get_entities(
            "The invoice from Henderson & Associates is overdue."
        )
        types = get_entity_types(entities)
        self.assertIn("CORP", types)

    def test_project_codename(self):
        entities = get_entities(
            "Project Phoenix deliverables are due Friday."
        )
        types = get_entity_types(entities)
        self.assertIn("CORP", types)


# ──────────────────────────────────────────────────────────────
# Test: Complex Scenarios
# ──────────────────────────────────────────────────────────────

class TestMultiEntityDetection(unittest.TestCase):
    """Test detection of multiple entities in a single message."""

    def test_mixed_pii(self):
        entities = get_entities(
            "Hey Mark, the invoice for GB29NWBK60161331926819 was sent "
            "to 742 Elm Street. Call the vendor at (555) 987-6543."
        )
        types = get_entity_types(entities)
        self.assertTrue(
            len(entities) >= 2,
            f"Expected 2+ entities, got {len(entities)}: {entities}"
        )

    def test_dense_pii_message(self):
        entities = get_entities(
            "Yo team, jsmith42 just sent the invoice #483-39-3838 "
            "to john@example.com. Ship to 90210. The API key is "
            "sk_test_abc123xyz. This is for Project Phoenix at "
            "Acme Corp."
        )
        types = get_entity_types(entities)
        self.assertTrue(
            len(entities) >= 3,
            f"Expected 3+ entities, got {len(entities)}: {entities}"
        )


class TestMessyText(unittest.TestCase):
    """Test detection in messy, informal corporate communications."""

    def test_slack_style(self):
        entities = get_entities(
            "yo @markjohnson can u ping brenda at brenda@corp.io? "
            "need the Q3 report asap thx"
        )
        types = get_entity_types(entities)
        self.assertTrue(len(entities) >= 1, f"Expected entities: {entities}")

    def test_typos_and_slang(self):
        entities = get_entities(
            "ugh can someone reset the pw for dave? its "
            "Spr1ngT1me!2024 and its not workin. lmk"
        )
        types = get_entity_types(entities)
        self.assertIn("ACCESS", types)

    def test_nested_pii(self):
        """Test detecting PII inside code snippets or JSON strings."""
        entities = get_entities(
            "Code snippet: export AWS_SECRET_KEY='sk_test_4eC39HqLyjWDarjtT1zdp7dc'"
        )
        types = get_entity_types(entities)
        self.assertIn("ACCESS", types)

    def test_mixed_context(self):
        """Test detecting names that are also common words."""
        entities = get_entities(
            "Will will be joining the call tomorrow at 9 AM."
        )
        values = get_entity_values(entities)
        self.assertTrue(any("Will" in v for v in values), f"Expected 'Will' in {values}")


class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_no_pii(self):
        """Text with no PII should return empty or minimal entities."""
        entities = get_entities(
            "The quarterly report looks good. Ship it."
        )
        # Should have 0 or very few entities
        self.assertTrue(
            len(entities) <= 1,
            f"Expected 0-1 entities for clean text, got {len(entities)}"
        )

    def test_function_call_format(self):
        """Verify the model outputs proper replace_pii function format."""
        data = query_f1_mask(
            "John Doe called from 555-0123 about his account 483-39-3838."
        )
        # Should have the replace_pii structure
        self.assertIn("arguments", data)
        self.assertIn("entities", data["arguments"])
        self.assertIsInstance(data["arguments"]["entities"], list)

    def test_entity_structure(self):
        """Verify each entity has required fields."""
        entities = get_entities(
            "Email sarah@company.com about the delivery to 90210."
        )
        for entity in entities:
            self.assertIn("type", entity, f"Missing 'type' in {entity}")
            self.assertIn("val", entity, f"Missing 'val' in {entity}")
            self.assertIn("id", entity, f"Missing 'id' in {entity}")


# ──────────────────────────────────────────────────────────────
# Test: Full Pipeline (Mask → Vault → Reconstruct)
# ──────────────────────────────────────────────────────────────

class TestFullPipeline(unittest.TestCase):
    """
    End-to-end test: F1 Mask detection → Vault storage → Reconstruction.
    Requires both Redis and Ollama.
    """

    def setUp(self):
        try:
            sys.path.insert(
                0,
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            from vault_manager import VaultManager
            self.vault = VaultManager(host="localhost", port=6379, ttl=60)
            self.session = "test-pipeline-session"
            self.vault.clear_session(self.session)
            self.vault_available = True
        except Exception:
            self.vault_available = False

    def tearDown(self):
        if self.vault_available:
            self.vault.clear_session(self.session)

    def test_mask_and_reconstruct(self):
        """Full cycle: detect PII → store in vault → reconstruct."""
        if not self.vault_available:
            self.skipTest("Redis not available")

        original_text = (
            "Hey, call John Doe at (555) 123-4567 about his account."
        )

        # Step 1: Detect PII via F1 Mask
        entities = get_entities(original_text)
        self.assertTrue(len(entities) >= 1, "No entities detected")

        # Step 2: Store entities in vault and mask the text
        masked_text = original_text
        entities.sort(key=lambda x: len(x['val']), reverse=True)

        for ent in entities:
            token = self.vault.get_or_create_token(
                self.session, ent['type'], ent['val']
            )
            masked_text = masked_text.replace(ent['val'], token)

        # Verify masking worked
        self.assertNotIn("John Doe", masked_text)
        self.assertIn("[", masked_text)

        # Step 3: Simulate cloud response with tokens
        cloud_response = masked_text  # Pretend cloud echoes back

        # Step 4: Reconstruct
        final = self.vault.reconstruct_text(self.session, cloud_response)

        # Verify reconstruction
        for ent in entities:
            self.assertIn(
                ent['val'], final,
                f"'{ent['val']}' not reconstructed in: {final}"
            )


if __name__ == "__main__":
    print("=" * 60)
    print("  ARPA F1 Mask — PII Detection Scenario Tests")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Ollama: {OLLAMA_URL}")
    print("=" * 60)
    print()

    # Check Ollama availability
    try:
        r = httpx.get(
            OLLAMA_URL.replace("/api/chat", "/api/tags"), timeout=5.0
        )
        models = [m["name"] for m in r.json().get("models", [])]
        if MODEL_NAME in models or any(MODEL_NAME in m for m in models):
            print(f"  [SUCCESS] Model '{MODEL_NAME}' found in Ollama\n")
        else:
            print(f"  [WARNING] Model '{MODEL_NAME}' not found locally. Available: {models}")
            print(f"  Register it: ollama create {MODEL_NAME} -f Ollama.Modelfile\n")
    except Exception as e:
        print(f"  [ERROR] Ollama infrastructure not detected: {e}")
        print("  Ensure Ollama is running and accessible at " + OLLAMA_URL)
        sys.exit(1)

    unittest.main(verbosity=2)
