"""
Unit tests for module extraction utilities.

Tests compute_module_key (SHA256) and extract_module_content
to ensure correct module extraction and deduplication logic.
"""

import hashlib
import json


class TestComputeModuleKey:
    """Tests for compute_module_key function"""

    def test_module_key_determinism(self):
        """Same content should always produce same key"""
        from temporal.activities.module_extraction import compute_module_key

        content = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock_statement",
        }

        key1 = compute_module_key("hook", content)
        key2 = compute_module_key("hook", content)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex = 64 chars

    def test_module_key_order_independence(self):
        """Field order should not affect key"""
        from temporal.activities.module_extraction import compute_module_key

        content1 = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock_statement",
        }
        content2 = {
            "opening_type": "shock_statement",
            "hook_mechanism": "pattern_interrupt",
        }

        assert compute_module_key("hook", content1) == compute_module_key("hook", content2)

    def test_module_key_ignores_extra_fields(self):
        """Only key_fields should be used for hash"""
        from temporal.activities.module_extraction import compute_module_key

        # Hook key_fields are: hook_mechanism, opening_type
        content_minimal = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock_statement",
        }
        content_extra = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock_statement",
            "hooks": ["Stop scrolling!", "Wait..."],
            "hook_stopping_power": "high",
        }

        assert compute_module_key("hook", content_minimal) == compute_module_key(
            "hook", content_extra
        )

    def test_module_key_different_types_different_keys(self):
        """Same content with different module_type should produce different keys"""
        from temporal.activities.module_extraction import compute_module_key

        # Using fields that exist in multiple types won't produce same key
        # because key_fields are different per type
        hook_content = {"hook_mechanism": "pattern_interrupt", "opening_type": "shock"}
        promise_content = {
            "promise_type": "instant",
            "core_belief": "solution_is_simple",
        }

        hook_key = compute_module_key("hook", hook_content)
        promise_key = compute_module_key("promise", promise_content)

        assert hook_key != promise_key

    def test_module_key_sha256_format(self):
        """Key should be valid SHA256 hex string"""
        from temporal.activities.module_extraction import compute_module_key

        content = {"hook_mechanism": "test", "opening_type": "test"}
        key = compute_module_key("hook", content)

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_module_key_manual_verification(self):
        """Verify hash computation matches expected output"""
        from temporal.activities.module_extraction import compute_module_key

        content = {"hook_mechanism": "pattern_interrupt", "opening_type": "shock"}

        # Manual computation: key_fields for hook are [hook_mechanism, opening_type]
        canonical = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock",
        }
        canonical_str = json.dumps(canonical, sort_keys=True)
        expected = hashlib.sha256(canonical_str.encode()).hexdigest()

        assert compute_module_key("hook", content) == expected


class TestExtractModuleContent:
    """Tests for extract_module_content function"""

    def test_extract_hook_content(self):
        """Should extract only hook fields from payload"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "hooks": ["Stop scrolling!", "Listen up!"],
            "hook_mechanism": "pattern_interrupt",
            "hook_stopping_power": "high",
            "opening_type": "shock_statement",
            "promise_type": "instant",  # Not a hook field
            "core_belief": "solution_is_simple",  # Not a hook field
        }

        content = extract_module_content(payload, "hook")

        assert "hooks" in content
        assert "hook_mechanism" in content
        assert "hook_stopping_power" in content
        assert "opening_type" in content
        assert "promise_type" not in content
        assert "core_belief" not in content

    def test_extract_promise_content(self):
        """Should extract only promise fields from payload"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "promise_type": "instant",
            "core_belief": "solution_is_simple",
            "state_before": "frustrated",
            "state_after": "confident",
            "ump_type": "hidden_cause",
            "ums_type": "secret_ingredient",
            "hook_mechanism": "pattern_interrupt",  # Not a promise field
        }

        content = extract_module_content(payload, "promise")

        assert "promise_type" in content
        assert "core_belief" in content
        assert "state_before" in content
        assert "state_after" in content
        assert "ump_type" in content
        assert "ums_type" in content
        assert "hook_mechanism" not in content

    def test_extract_proof_content(self):
        """Should extract only proof fields from payload"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "proof_type": "testimonial",
            "proof_source": "customer",
            "social_proof_pattern": "cascading",
            "story_type": "transformation",
            "hook_mechanism": "pattern_interrupt",  # Not a proof field
        }

        content = extract_module_content(payload, "proof")

        assert "proof_type" in content
        assert "proof_source" in content
        assert "social_proof_pattern" in content
        assert "story_type" in content
        assert "hook_mechanism" not in content

    def test_extract_missing_fields(self):
        """Missing fields should not appear in result"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "hook_mechanism": "pattern_interrupt",
            # opening_type is missing
        }

        content = extract_module_content(payload, "hook")

        assert "hook_mechanism" in content
        assert "opening_type" not in content

    def test_extract_empty_payload(self):
        """Empty payload should return empty dict"""
        from temporal.activities.module_extraction import extract_module_content

        content = extract_module_content({}, "hook")
        assert content == {}


class TestGetTextContent:
    """Tests for get_text_content function"""

    def test_text_content_from_hooks_array(self):
        """Should join array hooks into string"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hooks": ["Stop scrolling!", "Listen up!"]}
        text = get_text_content(payload, "hook")

        assert text == "Stop scrolling!; Listen up!"

    def test_text_content_from_single_hook(self):
        """Should handle single-item array"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hooks": ["Only one hook"]}
        text = get_text_content(payload, "hook")

        assert text == "Only one hook"

    def test_text_content_none_for_promise(self):
        """Promise has no text_field, should return None"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"promise_type": "instant"}
        text = get_text_content(payload, "promise")

        assert text is None

    def test_text_content_none_for_proof(self):
        """Proof has no text_field, should return None"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"proof_type": "testimonial"}
        text = get_text_content(payload, "proof")

        assert text is None

    def test_text_content_missing_field(self):
        """Missing hooks field should return None"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hook_mechanism": "pattern_interrupt"}
        text = get_text_content(payload, "hook")

        assert text is None


class TestModuleFieldsDefinition:
    """Tests for MODULE_FIELDS constant"""

    def test_all_module_types_defined(self):
        """All three module types should be defined"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        assert "hook" in MODULE_FIELDS
        assert "promise" in MODULE_FIELDS
        assert "proof" in MODULE_FIELDS

    def test_hook_has_key_fields(self):
        """Hook should have key_fields defined"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        assert "key_fields" in MODULE_FIELDS["hook"]
        assert "hook_mechanism" in MODULE_FIELDS["hook"]["key_fields"]
        assert "opening_type" in MODULE_FIELDS["hook"]["key_fields"]

    def test_promise_has_key_fields(self):
        """Promise should have key_fields defined"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        assert "key_fields" in MODULE_FIELDS["promise"]
        assert "promise_type" in MODULE_FIELDS["promise"]["key_fields"]
        assert "core_belief" in MODULE_FIELDS["promise"]["key_fields"]

    def test_proof_has_key_fields(self):
        """Proof should have key_fields defined"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        assert "key_fields" in MODULE_FIELDS["proof"]
        assert "proof_type" in MODULE_FIELDS["proof"]["key_fields"]
        assert "proof_source" in MODULE_FIELDS["proof"]["key_fields"]
