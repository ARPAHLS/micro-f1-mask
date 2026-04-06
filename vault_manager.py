import redis
import json
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARPA-Vault")

class VaultManager:
    """
    Manages the PII Vault via Redis for the ARPA F1 Mask Middleware.
    Handles bidirectional mapping (PII <-> Token) with session isolation.
    """
    def __init__(self, host="localhost", port=6379, db=0, ttl=7200):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = ttl  # Default 2 hours session life

    def _get_v2t_key(self, session_id):
        return f"arpa:f1:vault:{session_id}:v2t"

    def _get_t2v_key(self, session_id):
        return f"arpa:f1:vault:{session_id}:t2v"

    def _get_counter_key(self, session_id):
        return f"arpa:f1:vault:{session_id}:counters"

    def get_or_create_token(self, session_id: str, pii_type: str, pii_value: str) -> str:
        """
        Retrieves an existing token for a PII value or creates a new one.
        Ensures 'John Doe' always maps to the same suffix in the same session.
        """
        v2t_key = self._get_v2t_key(session_id)
        t2v_key = self._get_t2v_key(session_id)
        
        # 1. Check if we already have a token for this exact value
        existing_token = self.redis.hget(v2t_key, pii_value)
        if existing_token:
            return existing_token

        # 2. If not, generate a new token ID for this type in this session
        counter_key = self._get_counter_key(session_id)
        count = self.redis.hincrby(counter_key, pii_type, 1)
        
        new_token = f"[{pii_type}_{count}]"
        
        # 3. Store bidirectional mapping
        pipe = self.redis.pipeline()
        pipe.hset(v2t_key, pii_value, new_token)
        pipe.hset(t2v_key, new_token, pii_value)
        
        # 4. Refresh TTL for the session
        pipe.expire(v2t_key, self.ttl)
        pipe.expire(t2v_key, self.ttl)
        pipe.expire(counter_key, self.ttl)
        pipe.execute()
        
        logger.info(f"Vault: Assigned {new_token} to {pii_type} in session {session_id}")
        return new_token

    def reconstruct_text(self, session_id: str, text: str) -> str:
        """
        Scans text for [TYPE_ID] tokens and replaces them with original raw PII from the vault.
        """
        import re
        t2v_key = self._get_t2v_key(session_id)
        
        # Regex to find any token pattern like [INDIVIDUAL_1] or [FINANCIAL_3]
        token_pattern = r"\[(INDIVIDUAL|FINANCIAL|LOCATION|CONTACT|ACCESS|CORP)_\d+\]"
        
        def replace_match(match):
            token = match.group(0)
            original_value = self.redis.hget(t2v_key, token)
            return original_value if original_value else token

        return re.sub(token_pattern, replace_match, text)

    def clear_session(self, session_id: str):
        """Manually wipe a session vault."""
        self.redis.delete(self._get_v2t_key(session_id))
        self.redis.delete(self._get_t2v_key(session_id))
        self.redis.delete(self._get_counter_key(session_id))
