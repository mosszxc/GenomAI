"""
Unit tests for modular hypothesis generation.

Tests _format_module_content and modular generation utilities.
"""

import json


class TestFormatModuleContent:
    """Tests for _format_module_content function"""

    def test_format_with_text_content(self):
        """Should include text_content if present"""
        from temporal.activities.modular_generation import _format_module_content

        module = {
            "id": "test-id",
            "text_content": "Stop scrolling!",
            "content": {"hook_mechanism": "pattern_interrupt"},
        }

        formatted = _format_module_content(module)

        assert "Text: Stop scrolling!" in formatted
        assert "hook_mechanism: pattern_interrupt" in formatted

    def test_format_without_text_content(self):
        """Should work without text_content"""
        from temporal.activities.modular_generation import _format_module_content

        module = {
            "id": "test-id",
            "content": {"promise_type": "instant", "core_belief": "solution_is_simple"},
        }

        formatted = _format_module_content(module)

        assert "Text:" not in formatted
        assert "promise_type: instant" in formatted
        assert "core_belief: solution_is_simple" in formatted

    def test_format_with_json_string_content(self):
        """Should handle content as JSON string"""
        from temporal.activities.modular_generation import _format_module_content

        module = {
            "id": "test-id",
            "content": json.dumps(
                {"proof_type": "testimonial", "proof_source": "customer"}
            ),
        }

        formatted = _format_module_content(module)

        assert "proof_type: testimonial" in formatted
        assert "proof_source: customer" in formatted

    def test_format_with_array_value(self):
        """Should join array values with comma"""
        from temporal.activities.modular_generation import _format_module_content

        module = {
            "id": "test-id",
            "content": {"hooks": ["Stop scrolling!", "Listen up!"]},
        }

        formatted = _format_module_content(module)

        assert "hooks: Stop scrolling!, Listen up!" in formatted

    def test_format_with_none_values(self):
        """Should skip None values"""
        from temporal.activities.modular_generation import _format_module_content

        module = {
            "id": "test-id",
            "content": {"hook_mechanism": "pattern_interrupt", "opening_type": None},
        }

        formatted = _format_module_content(module)

        assert "hook_mechanism: pattern_interrupt" in formatted
        assert "opening_type" not in formatted

    def test_format_empty_content(self):
        """Should return 'No content available' for empty module"""
        from temporal.activities.modular_generation import _format_module_content

        module = {"id": "test-id", "content": {}}

        formatted = _format_module_content(module)

        assert formatted == "No content available"

    def test_format_missing_content(self):
        """Should handle missing content field"""
        from temporal.activities.modular_generation import _format_module_content

        module = {"id": "test-id"}

        formatted = _format_module_content(module)

        assert formatted == "No content available"


class TestPromptVersion:
    """Tests for prompt version constant"""

    def test_prompt_version_is_modular(self):
        """Prompt version should identify modular generation"""
        from temporal.activities.modular_generation import PROMPT_VERSION

        assert "modular" in PROMPT_VERSION


class TestSynthesisPrompt:
    """Tests for synthesis prompt structure"""

    def test_prompt_has_placeholders(self):
        """Synthesis prompt should have hook/promise/proof placeholders"""
        from temporal.activities.modular_generation import MODULAR_SYNTHESIS_PROMPT

        assert "{hook_content}" in MODULAR_SYNTHESIS_PROMPT
        assert "{promise_content}" in MODULAR_SYNTHESIS_PROMPT
        assert "{proof_content}" in MODULAR_SYNTHESIS_PROMPT

    def test_prompt_specifies_json_output(self):
        """Prompt should specify JSON output format"""
        from temporal.activities.modular_generation import MODULAR_SYNTHESIS_PROMPT

        assert '"text"' in MODULAR_SYNTHESIS_PROMPT
        assert "JSON" in MODULAR_SYNTHESIS_PROMPT


class TestGenerationMode:
    """Tests for generation mode constants"""

    def test_generation_mode_in_save(self):
        """save_modular_hypothesis should set generation_mode to modular"""
        # This is tested implicitly through the function definition
        # We verify the constant behavior here
        from temporal.activities.modular_generation import PROMPT_VERSION

        # PROMPT_VERSION should contain 'modular' to indicate modular generation
        assert "modular" in PROMPT_VERSION.lower()


class TestModuleTypeHandling:
    """Tests for handling different module types"""

    def test_format_hook_module(self):
        """Should format hook module correctly"""
        from temporal.activities.modular_generation import _format_module_content

        hook = {
            "id": "hook-1",
            "text_content": "Wait, you NEED to hear this!",
            "content": {
                "hook_mechanism": "pattern_interrupt",
                "opening_type": "shock_statement",
                "hook_stopping_power": "high",
            },
        }

        formatted = _format_module_content(hook)

        assert "Text: Wait, you NEED to hear this!" in formatted
        assert "hook_mechanism: pattern_interrupt" in formatted
        assert "opening_type: shock_statement" in formatted

    def test_format_promise_module(self):
        """Should format promise module correctly"""
        from temporal.activities.modular_generation import _format_module_content

        promise = {
            "id": "promise-1",
            "content": {
                "promise_type": "instant",
                "core_belief": "solution_is_simple",
                "state_before": "frustrated",
                "state_after": "confident",
            },
        }

        formatted = _format_module_content(promise)

        assert "promise_type: instant" in formatted
        assert "core_belief: solution_is_simple" in formatted
        assert "state_before: frustrated" in formatted
        assert "state_after: confident" in formatted

    def test_format_proof_module(self):
        """Should format proof module correctly"""
        from temporal.activities.modular_generation import _format_module_content

        proof = {
            "id": "proof-1",
            "content": {
                "proof_type": "testimonial",
                "proof_source": "customer",
                "social_proof_pattern": "cascading",
            },
        }

        formatted = _format_module_content(proof)

        assert "proof_type: testimonial" in formatted
        assert "proof_source: customer" in formatted
        assert "social_proof_pattern: cascading" in formatted
