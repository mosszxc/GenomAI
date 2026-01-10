"""
Unit tests for hashing utilities.

Tests canonical_hash (SHA256) and avatar_hash (MD5) to ensure
parity with the original JavaScript implementation in n8n.

TDD: These tests are written BEFORE the implementation.
"""

import hashlib


class TestCanonicalHash:
    """Tests for compute_canonical_hash function"""

    def test_canonical_hash_determinism(self):
        """Same payload should always produce same hash"""
        from src.utils.hashing import compute_canonical_hash

        payload = {
            "angle_type": "fear",
            "core_belief": "test_belief",
            "promise_type": "transformation",
            "emotion_primary": "anxiety",
            "emotion_intensity": "high",
            "schema_version": "v1",
        }

        hash1 = compute_canonical_hash(payload)
        hash2 = compute_canonical_hash(payload)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex = 64 chars

    def test_canonical_hash_order_independence(self):
        """Field order in input dict should not affect hash"""
        from src.utils.hashing import compute_canonical_hash

        payload1 = {"angle_type": "fear", "core_belief": "test", "schema_version": "v1"}

        payload2 = {"schema_version": "v1", "core_belief": "test", "angle_type": "fear"}

        assert compute_canonical_hash(payload1) == compute_canonical_hash(payload2)

    def test_canonical_hash_ignores_extra_fields(self):
        """Non-canonical fields should be ignored"""
        from src.utils.hashing import compute_canonical_hash

        payload_minimal = {"angle_type": "fear", "schema_version": "v1"}

        payload_extra = {
            "angle_type": "fear",
            "schema_version": "v1",
            "extra_field": "should_be_ignored",
            "another_extra": 12345,
        }

        assert compute_canonical_hash(payload_minimal) == compute_canonical_hash(
            payload_extra
        )

    def test_canonical_hash_only_includes_defined_fields(self):
        """Only fields with defined values should be included"""
        from src.utils.hashing import compute_canonical_hash

        # Payload with None values should exclude those fields
        payload_with_none = {
            "angle_type": "fear",
            "core_belief": None,
            "schema_version": "v1",
        }

        payload_without_none = {"angle_type": "fear", "schema_version": "v1"}

        # They should produce the same hash because None is excluded
        assert compute_canonical_hash(payload_with_none) == compute_canonical_hash(
            payload_without_none
        )

    def test_canonical_hash_js_parity(self):
        """
        Test parity with JavaScript implementation.

        JS code:
        const canonicalFields = ['angle_type', 'core_belief', ...];
        const sortedKeys = Object.keys(canonicalData).sort();
        const jsonString = JSON.stringify(sortedData);
        crypto.createHash('sha256').update(jsonString).digest('hex');
        """
        from src.utils.hashing import compute_canonical_hash

        # Known test case - compute expected hash manually
        payload = {"angle_type": "fear", "schema_version": "v1"}

        # Expected: sorted keys, JSON stringify, SHA256
        # {"angle_type":"fear","schema_version":"v1"}
        expected_json = '{"angle_type":"fear","schema_version":"v1"}'
        expected_hash = hashlib.sha256(expected_json.encode()).hexdigest()

        assert compute_canonical_hash(payload) == expected_hash

    def test_canonical_hash_all_fields(self):
        """Test with all canonical fields populated"""
        from src.utils.hashing import compute_canonical_hash

        payload = {
            "angle_type": "curiosity",
            "core_belief": "belief_value",
            "promise_type": "transformation",
            "emotion_primary": "hope",
            "emotion_intensity": "medium",
            "message_structure": "problem_solution",
            "opening_type": "question",
            "state_before": "frustrated",
            "state_after": "confident",
            "context_frame": "professional",
            "source_type": "original",
            "risk_level": "low",
            "horizon": "short",
            "schema_version": "v1",
        }

        result = compute_canonical_hash(payload)

        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_canonical_hash_empty_payload(self):
        """Empty payload should still produce valid hash"""
        from src.utils.hashing import compute_canonical_hash

        result = compute_canonical_hash({})

        # Empty object {} should hash
        expected = hashlib.sha256("{}".encode()).hexdigest()
        assert result == expected


class TestAvatarHash:
    """Tests for compute_avatar_hash function"""

    def test_avatar_hash_format(self):
        """Avatar hash should be 32-char MD5 hex string"""
        from src.utils.hashing import compute_avatar_hash

        result = compute_avatar_hash(
            vertical="nutra",
            geo="RU",
            deep_desire_type="health",
            primary_trigger="pain",
            awareness_level="problem_aware",
        )

        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hex = 32 chars
        assert all(c in "0123456789abcdef" for c in result)

    def test_avatar_hash_determinism(self):
        """Same inputs should always produce same hash"""
        from src.utils.hashing import compute_avatar_hash

        hash1 = compute_avatar_hash("nutra", "RU", "health", "pain", "aware")
        hash2 = compute_avatar_hash("nutra", "RU", "health", "pain", "aware")

        assert hash1 == hash2

    def test_avatar_hash_js_parity(self):
        """
        Test parity with JavaScript implementation.

        JS code (Issue #194: geo added):
        const avatarHashInput = [vertical, geo, deepDesireType, primaryTrigger, awarenessLevel].join('|');
        crypto.createHash('md5').update(avatarHashInput).digest('hex');
        """
        from src.utils.hashing import compute_avatar_hash

        vertical = "nutra"
        geo = "RU"
        deep_desire_type = "health_improvement"
        primary_trigger = "pain_relief"
        awareness_level = "solution_aware"

        # Expected: "nutra|RU|health_improvement|pain_relief|solution_aware"
        expected_input = (
            f"{vertical}|{geo}|{deep_desire_type}|{primary_trigger}|{awareness_level}"
        )
        expected_hash = hashlib.md5(expected_input.encode()).hexdigest()

        result = compute_avatar_hash(
            vertical, geo, deep_desire_type, primary_trigger, awareness_level
        )

        assert result == expected_hash

    def test_avatar_hash_different_inputs(self):
        """Different inputs should produce different hashes"""
        from src.utils.hashing import compute_avatar_hash

        hash1 = compute_avatar_hash("nutra", "RU", "health", "pain", "aware")
        hash2 = compute_avatar_hash("crypto", "KZ", "wealth", "fomo", "unaware")

        assert hash1 != hash2

    def test_avatar_hash_returns_none_for_missing_fields(self):
        """Should return None if any required field is missing/None"""
        from src.utils.hashing import compute_avatar_hash

        # All None (vertical and geo can be None, but deep_desire, trigger, awareness required)
        assert compute_avatar_hash(None, None, None, None, None) is None

        # Some None - deep_desire, trigger, awareness are required
        assert compute_avatar_hash("nutra", "RU", None, "pain", "aware") is None
        assert compute_avatar_hash("nutra", "RU", "health", None, "aware") is None
        assert compute_avatar_hash("nutra", "RU", "health", "pain", None) is None

    def test_avatar_hash_empty_strings(self):
        """Empty strings should be treated as valid values"""
        from src.utils.hashing import compute_avatar_hash

        # Empty strings are falsy in JS but we might want to handle differently
        # Based on JS: if (deepDesireType && primaryTrigger && awarenessLevel)
        # Empty string is falsy, so should return None
        result = compute_avatar_hash("nutra", "RU", "", "pain", "aware")
        assert result is None

    def test_avatar_hash_geo_affects_hash(self):
        """Different geo should produce different hash (Issue #194)"""
        from src.utils.hashing import compute_avatar_hash

        hash_ru = compute_avatar_hash("nutra", "RU", "health", "pain", "aware")
        hash_kz = compute_avatar_hash("nutra", "KZ", "health", "pain", "aware")

        assert hash_ru != hash_kz

    def test_avatar_hash_unknown_geo(self):
        """None geo should default to 'unknown'"""
        from src.utils.hashing import compute_avatar_hash

        # None geo defaults to 'unknown'
        hash_none = compute_avatar_hash("nutra", None, "health", "pain", "aware")

        # Expected: "nutra|unknown|health|pain|aware"
        expected_input = "nutra|unknown|health|pain|aware"
        expected_hash = hashlib.md5(expected_input.encode()).hexdigest()

        assert hash_none == expected_hash


class TestHashingParity:
    """
    Integration tests to verify parity with existing database hashes.
    These tests require known good data from the database.
    """

    def test_known_hash_example_1(self):
        """
        Test against a known canonical_hash from the database.
        This ensures our implementation matches the JS implementation exactly.

        To add real test cases:
        1. Query ideas table for a canonical_hash
        2. Query decomposed_creatives for the payload
        3. Add the payload and expected hash here
        """
        from src.utils.hashing import compute_canonical_hash

        # Example payload (replace with real data from DB)
        payload = {
            "angle_type": "fear",
            "core_belief": "health_is_wealth",
            "promise_type": "transformation",
            "emotion_primary": "anxiety",
            "emotion_intensity": "high",
            "message_structure": "problem_agitation_solution",
            "opening_type": "hook_question",
            "state_before": "suffering",
            "state_after": "relieved",
            "context_frame": "personal",
            "source_type": "ugc",
            "risk_level": "medium",
            "horizon": "short",
            "schema_version": "v1",
        }

        result = compute_canonical_hash(payload)

        # This is a placeholder - replace with actual hash from DB
        # For now just verify it produces a valid hash
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
