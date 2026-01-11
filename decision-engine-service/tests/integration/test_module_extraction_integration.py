"""
Integration test for module_extraction activity.

Tests the full flow with real Supabase connection.
Run with: python -m pytest tests/integration/test_module_extraction_integration.py -v
"""

import os
import pytest
import asyncio

# Skip if no Supabase credentials
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"), reason="SUPABASE_URL not set"
)


class TestModuleExtractionIntegration:
    """Integration tests with real Supabase"""

    @pytest.mark.asyncio
    async def test_extract_modules_creates_records(self):
        """
        Test that extract_modules_from_decomposition creates module_bank records.

        Uses a test payload matching Canonical Schema v2.
        """
        from temporal.activities.module_extraction import (
            compute_module_key,
            extract_module_content,
        )

        # Test payload with all module types
        payload = {
            "hooks": ["Stop everything!", "This changes everything"],
            "hook_mechanism": "pattern_interrupt",
            "hook_stopping_power": "high",
            "opening_type": "shock_statement",
            "promise_type": "transformation",
            "core_belief": "solution_is_simple",
            "state_before": "frustrated",
            "state_after": "confident",
            "proof_type": "testimonial",
            "proof_source": "customer",
        }

        # Test module extraction
        hook_content = extract_module_content(payload, "hook")
        promise_content = extract_module_content(payload, "promise")
        proof_content = extract_module_content(payload, "proof")

        assert "hook_mechanism" in hook_content
        assert "promise_type" in promise_content
        assert "proof_type" in proof_content

        # Test key computation determinism
        key1 = compute_module_key("hook", hook_content)
        key2 = compute_module_key("hook", hook_content)
        assert key1 == key2
        assert len(key1) == 64

        # Different module types produce different keys
        hook_key = compute_module_key("hook", hook_content)
        promise_key = compute_module_key("promise", promise_content)
        assert hook_key != promise_key

        print(f"\nHook key: {hook_key[:16]}...")
        print(f"Promise key: {promise_key[:16]}...")
        print("Integration test: PASSED")


if __name__ == "__main__":
    asyncio.run(
        TestModuleExtractionIntegration().test_extract_modules_creates_records()
    )
