"""
ARPA Micro Series: F1 Mask — Vault Manager Unit Tests
Requires: Redis running on localhost:6379 (docker compose up -d)
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault_manager import VaultManager


class TestVaultTokenCreation(unittest.TestCase):
    """Tests for token creation and retrieval."""

    def setUp(self):
        self.vault = VaultManager(host="localhost", port=6379, ttl=60)
        self.session = "test-session-creation"
        self.vault.clear_session(self.session)

    def tearDown(self):
        self.vault.clear_session(self.session)

    def test_create_individual_token(self):
        token = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "John Doe"
        )
        self.assertEqual(token, "[INDIVIDUAL_1]")

    def test_create_financial_token(self):
        token = self.vault.get_or_create_token(
            self.session, "FINANCIAL", "483-39-3838"
        )
        self.assertEqual(token, "[FINANCIAL_1]")

    def test_create_location_token(self):
        token = self.vault.get_or_create_token(
            self.session, "LOCATION", "742 Evergreen Terrace"
        )
        self.assertEqual(token, "[LOCATION_1]")

    def test_create_contact_token(self):
        token = self.vault.get_or_create_token(
            self.session, "CONTACT", "john@example.com"
        )
        self.assertEqual(token, "[CONTACT_1]")

    def test_create_access_token(self):
        token = self.vault.get_or_create_token(
            self.session, "ACCESS", "sk_test_abc123"
        )
        self.assertEqual(token, "[ACCESS_1]")

    def test_create_corp_token(self):
        token = self.vault.get_or_create_token(
            self.session, "CORP", "Project Phoenix"
        )
        self.assertEqual(token, "[CORP_1]")


class TestVaultConsistency(unittest.TestCase):
    """Tests for idempotent token retrieval."""

    def setUp(self):
        self.vault = VaultManager(host="localhost", port=6379, ttl=60)
        self.session = "test-session-consistency"
        self.vault.clear_session(self.session)

    def tearDown(self):
        self.vault.clear_session(self.session)

    def test_same_value_returns_same_token(self):
        """Same PII value should always map to the same token in a session."""
        t1 = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "Jane Smith"
        )
        t2 = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "Jane Smith"
        )
        self.assertEqual(t1, t2)

    def test_different_values_get_different_tokens(self):
        """Different PII values of the same type get incrementing tokens."""
        t1 = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "John Doe"
        )
        t2 = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "Jane Smith"
        )
        self.assertEqual(t1, "[INDIVIDUAL_1]")
        self.assertEqual(t2, "[INDIVIDUAL_2]")

    def test_mixed_types_increment_independently(self):
        """Different PII types maintain separate counters."""
        t_ind = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "John Doe"
        )
        t_fin = self.vault.get_or_create_token(
            self.session, "FINANCIAL", "483-39-3838"
        )
        t_ind2 = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "Jane Smith"
        )
        self.assertEqual(t_ind, "[INDIVIDUAL_1]")
        self.assertEqual(t_fin, "[FINANCIAL_1]")
        self.assertEqual(t_ind2, "[INDIVIDUAL_2]")


class TestVaultSessionIsolation(unittest.TestCase):
    """Tests that different sessions are fully isolated."""

    def setUp(self):
        self.vault = VaultManager(host="localhost", port=6379, ttl=60)
        self.session_a = "test-session-iso-a"
        self.session_b = "test-session-iso-b"
        self.vault.clear_session(self.session_a)
        self.vault.clear_session(self.session_b)

    def tearDown(self):
        self.vault.clear_session(self.session_a)
        self.vault.clear_session(self.session_b)

    def test_sessions_are_isolated(self):
        """Same PII in different sessions gets independent tokens."""
        t_a = self.vault.get_or_create_token(
            self.session_a, "INDIVIDUAL", "John Doe"
        )
        t_b = self.vault.get_or_create_token(
            self.session_b, "INDIVIDUAL", "John Doe"
        )
        # Both should be [INDIVIDUAL_1] in their own sessions
        self.assertEqual(t_a, "[INDIVIDUAL_1]")
        self.assertEqual(t_b, "[INDIVIDUAL_1]")

    def test_clear_session_does_not_affect_other(self):
        """Clearing one session leaves other sessions intact."""
        self.vault.get_or_create_token(
            self.session_a, "INDIVIDUAL", "John Doe"
        )
        self.vault.get_or_create_token(
            self.session_b, "INDIVIDUAL", "Jane Smith"
        )
        self.vault.clear_session(self.session_a)

        # Session B should still work
        t = self.vault.get_or_create_token(
            self.session_b, "INDIVIDUAL", "Jane Smith"
        )
        self.assertEqual(t, "[INDIVIDUAL_1]")


class TestVaultReconstruction(unittest.TestCase):
    """Tests for text reconstruction (token → PII)."""

    def setUp(self):
        self.vault = VaultManager(host="localhost", port=6379, ttl=60)
        self.session = "test-session-recon"
        self.vault.clear_session(self.session)

    def tearDown(self):
        self.vault.clear_session(self.session)

    def test_single_token_reconstruction(self):
        self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "John Doe"
        )
        result = self.vault.reconstruct_text(
            self.session, "Hello [INDIVIDUAL_1], welcome!"
        )
        self.assertEqual(result, "Hello John Doe, welcome!")

    def test_multi_token_reconstruction(self):
        self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "John Doe"
        )
        self.vault.get_or_create_token(
            self.session, "FINANCIAL", "483-39-3838"
        )
        self.vault.get_or_create_token(
            self.session, "LOCATION", "742 Evergreen Terrace"
        )
        result = self.vault.reconstruct_text(
            self.session,
            "[INDIVIDUAL_1] at [LOCATION_1], SSN [FINANCIAL_1]"
        )
        self.assertEqual(
            result,
            "John Doe at 742 Evergreen Terrace, SSN 483-39-3838"
        )

    def test_unknown_token_preserved(self):
        """Tokens not in the vault should be left as-is."""
        result = self.vault.reconstruct_text(
            self.session, "Hello [INDIVIDUAL_99]!"
        )
        self.assertEqual(result, "Hello [INDIVIDUAL_99]!")

    def test_no_tokens_passthrough(self):
        """Text without tokens passes through unchanged."""
        original = "Hello world, no PII here."
        result = self.vault.reconstruct_text(self.session, original)
        self.assertEqual(result, original)

    def test_mixed_known_unknown_tokens(self):
        """Mix of real and unknown tokens."""
        self.vault.get_or_create_token(
            self.session, "CONTACT", "john@example.com"
        )
        result = self.vault.reconstruct_text(
            self.session,
            "Email [CONTACT_1] or [CONTACT_2] for support."
        )
        self.assertEqual(
            result,
            "Email john@example.com or [CONTACT_2] for support."
        )


class TestVaultEdgeCases(unittest.TestCase):
    """Edge cases and stress tests."""

    def setUp(self):
        self.vault = VaultManager(host="localhost", port=6379, ttl=60)
        self.session = "test-session-edge"
        self.vault.clear_session(self.session)

    def tearDown(self):
        self.vault.clear_session(self.session)

    def test_special_characters_in_pii(self):
        """PII with special chars should be stored and retrieved."""
        token = self.vault.get_or_create_token(
            self.session, "ACCESS", "sk_test_A!@#$%^&*()"
        )
        self.assertEqual(token, "[ACCESS_1]")

        result = self.vault.reconstruct_text(
            self.session, "Key: [ACCESS_1]"
        )
        self.assertEqual(result, "Key: sk_test_A!@#$%^&*()")

    def test_unicode_in_pii(self):
        """Unicode characters should be handled."""
        token = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", "José García"
        )
        self.assertEqual(token, "[INDIVIDUAL_1]")

    def test_empty_string_pii(self):
        """Empty string edge case."""
        token = self.vault.get_or_create_token(
            self.session, "INDIVIDUAL", ""
        )
        self.assertEqual(token, "[INDIVIDUAL_1]")

    def test_very_long_pii(self):
        """Very long PII value."""
        long_address = (
            "12345 Extremely Long Street Name Avenue Suite 999, "
            "Very Long City Name, State Of Confusion, ZZ 99999-1234"
        )
        token = self.vault.get_or_create_token(
            self.session, "LOCATION", long_address
        )
        self.assertEqual(token, "[LOCATION_1]")

        result = self.vault.reconstruct_text(
            self.session, "Ship to [LOCATION_1]"
        )
        self.assertEqual(result, f"Ship to {long_address}")

    def test_many_entities_same_type(self):
        """Stress test with many entities of the same type."""
        for i in range(20):
            token = self.vault.get_or_create_token(
                self.session, "INDIVIDUAL", f"Person_{i}"
            )
            self.assertEqual(token, f"[INDIVIDUAL_{i+1}]")

    def test_idempotency_complex(self):
        """Ensure repeated masking of the same text remains stable."""
        val = "John Doe"
        t1 = self.vault.get_or_create_token(self.session, "INDIVIDUAL", val)
        t2 = self.vault.get_or_create_token(self.session, "INDIVIDUAL", val)
        self.assertEqual(t1, t2)
        
        # Recon should still work after redundant calls
        self.assertEqual(self.vault.reconstruct_text(self.session, t1), val)

    def test_session_expiry_simulation(self):
        """Test behavior when underlying Redis keys are missing."""
        self.vault.get_or_create_token(self.session, "INDIVIDUAL", "John")
        self.vault.clear_session(self.session) # Simulate expiry
        
        # Reconstruction should return the token as-is if missing from vault
        res = self.vault.reconstruct_text(self.session, "[INDIVIDUAL_1]")
        self.assertEqual(res, "[INDIVIDUAL_1]")

    def test_token_pattern_overlap(self):
        """Ensure [TYPE_1] and [TYPE_10] don't clash during regex replacement."""
        v1 = "User_1"
        v10 = "User_10"
        self.vault.get_or_create_token(self.session, "INDIVIDUAL", v1) # [INDIVIDUAL_1]
        for i in range(2, 10):
            self.vault.get_or_create_token(self.session, "INDIVIDUAL", f"Extra_{i}")
        self.vault.get_or_create_token(self.session, "INDIVIDUAL", v10) # [INDIVIDUAL_10]
        
        text = "Hello [INDIVIDUAL_1] and [INDIVIDUAL_10]."
        recon = self.vault.reconstruct_text(self.session, text)
        self.assertEqual(recon, f"Hello {v1} and {v10}.")


if __name__ == "__main__":
    print("=" * 60)
    print("  ARPA F1 Mask — Vault Manager Tests")
    print("  Requires: Redis on localhost:6379")
    print("=" * 60)
    print()

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        r.ping()
        print("  [SUCCESS] Redis connection OK\n")
    except Exception as e:
        print(f"  [ERROR] Redis not available: {e}")
        print("  Start Redis: docker compose up -d")
        sys.exit(1)

    unittest.main(verbosity=2)
