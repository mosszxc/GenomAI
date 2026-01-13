"""
Unit tests for module extraction utilities.

Tests compute_module_key (SHA256), extract_module_content with fallback logic,
and get_text_content to ensure correct module extraction for all 7 variables.

7 Variables (from VISION.md and issue #596):
1. hook_mechanism
2. angle_type
3. message_structure
4. ump_type
5. promise_type
6. proof_type
7. cta_style
"""

import hashlib
import json


class TestModuleTypes:
    """Tests for MODULE_TYPES and MODULE_FIELDS constants"""

    def test_seven_module_types_defined(self):
        """All 7 module types should be defined"""
        from temporal.activities.module_extraction import MODULE_TYPES, MODULE_FIELDS

        expected_types = [
            "hook_mechanism",
            "angle_type",
            "message_structure",
            "ump_type",
            "promise_type",
            "proof_type",
            "cta_style",
        ]

        assert MODULE_TYPES == expected_types
        for mt in expected_types:
            assert mt in MODULE_FIELDS, f"Missing MODULE_FIELDS for {mt}"

    def test_all_types_have_required_fields(self):
        """Each module type should have required config fields"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        for module_type, config in MODULE_FIELDS.items():
            assert "primary_field" in config, f"{module_type} missing primary_field"
            assert "key_fields" in config, f"{module_type} missing key_fields"
            assert "text_field" in config, f"{module_type} missing text_field"
            assert "related_fields" in config, f"{module_type} missing related_fields"


class TestComputeModuleKey:
    """Tests for compute_module_key function"""

    def test_module_key_determinism(self):
        """Same content should always produce same key"""
        from temporal.activities.module_extraction import compute_module_key

        content = {"hook_mechanism": "pattern_interrupt"}

        key1 = compute_module_key("hook_mechanism", content)
        key2 = compute_module_key("hook_mechanism", content)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex = 64 chars

    def test_module_key_uses_primary_field_only(self):
        """Only primary_field should be used for hash, not related fields"""
        from temporal.activities.module_extraction import compute_module_key

        content_minimal = {"hook_mechanism": "pattern_interrupt"}
        content_extra = {
            "hook_mechanism": "pattern_interrupt",
            "hooks": ["Stop scrolling!", "Wait..."],
            "hook_stopping_power": "high",
            "_fallback_used": "opening_type",
        }

        assert compute_module_key("hook_mechanism", content_minimal) == compute_module_key(
            "hook_mechanism", content_extra
        )

    def test_module_key_different_types_same_value(self):
        """Same value but different types should produce different keys"""
        from temporal.activities.module_extraction import compute_module_key

        # If somehow the same value appears in different types
        # the key should still be different due to field name
        hook_content = {"hook_mechanism": "dramatic"}
        angle_content = {"angle_type": "dramatic"}

        hook_key = compute_module_key("hook_mechanism", hook_content)
        angle_key = compute_module_key("angle_type", angle_content)

        assert hook_key != angle_key

    def test_module_key_sha256_format(self):
        """Key should be valid SHA256 hex string"""
        from temporal.activities.module_extraction import compute_module_key

        content = {"angle_type": "fear"}
        key = compute_module_key("angle_type", content)

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_module_key_manual_verification(self):
        """Verify hash computation matches expected output"""
        from temporal.activities.module_extraction import compute_module_key

        content = {"hook_mechanism": "pattern_interrupt"}

        # Manual computation
        canonical = {"hook_mechanism": "pattern_interrupt"}
        canonical_str = json.dumps(canonical, sort_keys=True)
        expected = hashlib.sha256(canonical_str.encode()).hexdigest()

        assert compute_module_key("hook_mechanism", content) == expected


class TestExtractModuleContent:
    """Tests for extract_module_content function with fallback logic"""

    def test_extract_with_primary_field(self):
        """Should extract primary field when present"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "hook_mechanism": "pattern_interrupt",
            "opening_type": "shock_statement",  # fallback, should be ignored
        }

        content = extract_module_content(payload, "hook_mechanism")

        assert content["hook_mechanism"] == "pattern_interrupt"
        assert "_fallback_used" not in content

    def test_extract_with_fallback_field(self):
        """Should use fallback field when primary is missing"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "opening_type": "shock_statement",  # fallback for hook_mechanism
        }

        content = extract_module_content(payload, "hook_mechanism")

        # Value stored under primary field name
        assert content["hook_mechanism"] == "shock_statement"
        assert content["_fallback_used"] == "opening_type"

    def test_extract_angle_type_with_emotional_trigger_fallback(self):
        """angle_type should fallback to emotional_trigger"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {"emotional_trigger": "fear"}

        content = extract_module_content(payload, "angle_type")

        assert content["angle_type"] == "fear"
        assert content["_fallback_used"] == "emotional_trigger"

    def test_extract_message_structure_with_story_type_fallback(self):
        """message_structure should fallback to story_type"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {"story_type": "transformation"}

        content = extract_module_content(payload, "message_structure")

        assert content["message_structure"] == "transformation"
        assert content["_fallback_used"] == "story_type"

    def test_extract_ump_type_with_ums_type_fallback(self):
        """ump_type should fallback to ums_type"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "ums_type": "secret_ingredient",
            "core_belief": "solution_is_simple",  # related field
        }

        content = extract_module_content(payload, "ump_type")

        assert content["ump_type"] == "secret_ingredient"
        assert content["_fallback_used"] == "ums_type"
        assert content["core_belief"] == "solution_is_simple"

    def test_extract_promise_type_with_composite_fallback(self):
        """promise_type should use state_before + state_after as composite fallback"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "state_before": "frustrated",
            "state_after": "confident",
        }

        content = extract_module_content(payload, "promise_type")

        assert content["promise_type"] == "frustrated → confident"
        assert content["_fallback_used"] == "state_before+state_after"
        # Related fields also included
        assert content["state_before"] == "frustrated"
        assert content["state_after"] == "confident"

    def test_extract_proof_type_with_proof_source_fallback(self):
        """proof_type should fallback to proof_source"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {"proof_source": "customer"}

        content = extract_module_content(payload, "proof_type")

        assert content["proof_type"] == "customer"
        assert content["_fallback_used"] == "proof_source"

    def test_extract_cta_style_with_risk_reversal_fallback(self):
        """cta_style should fallback to risk_reversal_type"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {"risk_reversal_type": "guarantee"}

        content = extract_module_content(payload, "cta_style")

        assert content["cta_style"] == "guarantee"
        assert content["_fallback_used"] == "risk_reversal_type"

    def test_extract_includes_related_fields(self):
        """Should include related_fields in content"""
        from temporal.activities.module_extraction import extract_module_content

        payload = {
            "hook_mechanism": "pattern_interrupt",
            "hooks": ["Stop scrolling!"],
            "hook_stopping_power": "high",
        }

        content = extract_module_content(payload, "hook_mechanism")

        assert content["hook_mechanism"] == "pattern_interrupt"
        assert content["hooks"] == ["Stop scrolling!"]
        assert content["hook_stopping_power"] == "high"

    def test_extract_empty_payload(self):
        """Empty payload should return empty dict"""
        from temporal.activities.module_extraction import extract_module_content

        content = extract_module_content({}, "hook_mechanism")
        assert content == {}

    def test_extract_all_seven_types(self):
        """Should be able to extract all 7 module types"""
        from temporal.activities.module_extraction import (
            extract_module_content,
            MODULE_TYPES,
        )

        # Full payload with all fields
        payload = {
            "hook_mechanism": "pattern_interrupt",
            "hooks": ["Stop!"],
            "angle_type": "fear",
            "message_structure": "problem_solution",
            "ump_type": "hidden_cause",
            "core_belief": "simple_solution",
            "promise_type": "transformation",
            "state_before": "frustrated",
            "state_after": "confident",
            "proof_type": "testimonial",
            "social_proof_pattern": "cascading",
            "cta_style": "urgency",
        }

        for module_type in MODULE_TYPES:
            content = extract_module_content(payload, module_type)
            primary_field = module_type  # primary_field same as module_type
            assert primary_field in content, f"Missing {primary_field} for {module_type}"


class TestGetTextContent:
    """Tests for get_text_content function"""

    def test_text_content_from_hooks_array(self):
        """Should join array hooks into string"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hooks": ["Stop scrolling!", "Listen up!"]}
        text = get_text_content(payload, "hook_mechanism")

        assert text == "Stop scrolling!; Listen up!"

    def test_text_content_from_single_hook(self):
        """Should handle single-item array"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hooks": ["Only one hook"]}
        text = get_text_content(payload, "hook_mechanism")

        assert text == "Only one hook"

    def test_text_content_none_for_types_without_text_field(self):
        """Types without text_field should return None"""
        from temporal.activities.module_extraction import get_text_content, MODULE_TYPES

        payload = {
            "angle_type": "fear",
            "message_structure": "problem_solution",
        }

        # All types except hook_mechanism have text_field=None
        for module_type in MODULE_TYPES:
            if module_type == "hook_mechanism":
                continue
            text = get_text_content(payload, module_type)
            assert text is None, f"Expected None for {module_type}"

    def test_text_content_missing_hooks_field(self):
        """Missing hooks field should return None"""
        from temporal.activities.module_extraction import get_text_content

        payload = {"hook_mechanism": "pattern_interrupt"}
        text = get_text_content(payload, "hook_mechanism")

        assert text is None


class TestFallbackMapping:
    """Tests to verify fallback mapping from Variable Mapping Table (issue #599)"""

    def test_all_fallbacks_defined(self):
        """Verify all fallback fields are correctly defined per issue #599"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        expected_fallbacks = {
            "hook_mechanism": "opening_type",
            "angle_type": "emotional_trigger",
            "message_structure": "story_type",
            "ump_type": "ums_type",
            "promise_type": None,  # Uses composite fallback
            "proof_type": "proof_source",
            "cta_style": "risk_reversal_type",
        }

        for module_type, expected_fallback in expected_fallbacks.items():
            actual = MODULE_FIELDS[module_type].get("fallback_field")
            assert actual == expected_fallback, (
                f"{module_type}: expected fallback '{expected_fallback}', got '{actual}'"
            )

    def test_promise_type_composite_fallback(self):
        """promise_type should have composite fallback of state_before + state_after"""
        from temporal.activities.module_extraction import MODULE_FIELDS

        config = MODULE_FIELDS["promise_type"]
        assert config.get("fallback_composite") == ["state_before", "state_after"]
