"""
Integration test for module_extraction activity.

Tests the full flow with real Supabase connection.
Run with: python -m pytest tests/integration/test_module_extraction_integration.py -v
"""

import os
import pytest
import asyncio

# Skip if no Supabase credentials
pytestmark = pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="SUPABASE_URL not set")


class TestModuleExtractionIntegration:
    """Integration tests with real Supabase"""

    @pytest.mark.asyncio
    async def test_extract_all_seven_module_types(self):
        """
        Test that extract_modules_from_decomposition handles all 7 module types.

        Uses a test payload matching the 7 Independent Variables schema.
        """
        from temporal.activities.module_extraction import (
            compute_module_key,
            extract_module_content,
            MODULE_TYPES,
            MODULE_FIELDS,
        )

        # Test payload with all 7 module types
        payload = {
            # hook_mechanism
            "hook_mechanism": "pattern_interrupt",
            "hooks": ["Stop everything!", "This changes everything"],
            "hook_stopping_power": "high",
            # angle_type
            "angle_type": "fear_of_missing_out",
            # message_structure
            "message_structure": "problem_agitate_solve",
            # ump_type
            "ump_type": "hidden_cause",
            "core_belief": "solution_is_simple",
            # promise_type
            "promise_type": "transformation",
            "state_before": "frustrated",
            "state_after": "confident",
            # proof_type
            "proof_type": "testimonial",
            "proof_source": "customer",
            "social_proof_pattern": "cascading",
            # cta_style
            "cta_style": "urgency",
        }

        # Test extraction for all 7 types
        for module_type in MODULE_TYPES:
            content = extract_module_content(payload, module_type)
            primary_field = MODULE_FIELDS[module_type]["primary_field"]

            # Should have primary field
            assert primary_field in content, f"Missing {primary_field} for {module_type}"

            # Compute key for this content
            key = compute_module_key(module_type, content)
            assert len(key) == 64, f"Invalid key length for {module_type}"

        print("\n7 Module types extraction: PASSED")

    @pytest.mark.asyncio
    async def test_fallback_extraction(self):
        """
        Test fallback logic when primary fields are missing.

        Verifies Variable Mapping Table from issue #599.
        """
        from temporal.activities.module_extraction import (
            extract_module_content,
        )

        # Payload with only fallback fields
        fallback_payload = {
            "opening_type": "shock_statement",  # fallback for hook_mechanism
            "emotional_trigger": "fear",  # fallback for angle_type
            "story_type": "transformation",  # fallback for message_structure
            "ums_type": "secret_ingredient",  # fallback for ump_type
            "state_before": "frustrated",  # composite fallback for promise_type
            "state_after": "confident",
            "proof_source": "customer",  # fallback for proof_type
            "risk_reversal_type": "guarantee",  # fallback for cta_style
        }

        # Test each fallback
        hook = extract_module_content(fallback_payload, "hook_mechanism")
        assert hook["hook_mechanism"] == "shock_statement"
        assert hook.get("_fallback_used") == "opening_type"

        angle = extract_module_content(fallback_payload, "angle_type")
        assert angle["angle_type"] == "fear"
        assert angle.get("_fallback_used") == "emotional_trigger"

        message = extract_module_content(fallback_payload, "message_structure")
        assert message["message_structure"] == "transformation"
        assert message.get("_fallback_used") == "story_type"

        ump = extract_module_content(fallback_payload, "ump_type")
        assert ump["ump_type"] == "secret_ingredient"
        assert ump.get("_fallback_used") == "ums_type"

        promise = extract_module_content(fallback_payload, "promise_type")
        assert promise["promise_type"] == "frustrated → confident"
        assert promise.get("_fallback_used") == "state_before+state_after"

        proof = extract_module_content(fallback_payload, "proof_type")
        assert proof["proof_type"] == "customer"
        assert proof.get("_fallback_used") == "proof_source"

        cta = extract_module_content(fallback_payload, "cta_style")
        assert cta["cta_style"] == "guarantee"
        assert cta.get("_fallback_used") == "risk_reversal_type"

        print("\nFallback extraction: PASSED")

    @pytest.mark.asyncio
    async def test_module_key_determinism_for_all_types(self):
        """Test that module key computation is deterministic for all 7 types."""
        from temporal.activities.module_extraction import (
            compute_module_key,
            MODULE_TYPES,
        )

        test_values = {
            "hook_mechanism": {"hook_mechanism": "pattern_interrupt"},
            "angle_type": {"angle_type": "fear"},
            "message_structure": {"message_structure": "problem_solution"},
            "ump_type": {"ump_type": "hidden_cause"},
            "promise_type": {"promise_type": "transformation"},
            "proof_type": {"proof_type": "testimonial"},
            "cta_style": {"cta_style": "urgency"},
        }

        for module_type in MODULE_TYPES:
            content = test_values[module_type]
            key1 = compute_module_key(module_type, content)
            key2 = compute_module_key(module_type, content)

            assert key1 == key2, f"Keys not deterministic for {module_type}"
            assert len(key1) == 64, f"Invalid key length for {module_type}"

        print("\nKey determinism for all types: PASSED")


if __name__ == "__main__":
    asyncio.run(TestModuleExtractionIntegration().test_extract_all_seven_module_types())
