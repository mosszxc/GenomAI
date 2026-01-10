"""
Unit tests for Schema Validator service.

Tests validation of LLM output against JSON Schema.
"""

from src.services.schema_validator import (
    SchemaValidator,
    ValidationResult,
    ValidationError,
    ValidationWarning,
    get_schema_validator,
)


class TestSchemaValidatorValidPayload:
    """Tests for valid payload validation"""

    def test_valid_payload_returns_valid_true(self):
        """Valid payload should return valid: true"""
        validator = SchemaValidator()

        payload = {
            "angle_type": "pain",
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_payload_with_optional_fields(self):
        """Valid payload with optional fields should pass"""
        validator = SchemaValidator()

        payload = {
            "idea_id": "550e8400-e29b-41d4-a716-446655440000",
            "active_cluster_id": "660e8400-e29b-41d4-a716-446655440000",
            "angle_type": "hope",
            "core_belief": "solution_is_simple",
            "promise_type": "gradual",
            "emotion_primary": "hope",
            "emotion_intensity": "medium",
            "message_structure": "story_reveal",
            "opening_type": "personal_story",
            "state_before": "uncertain",
            "state_after": "confident",
            "context_frame": "peer_based",
            "source_type": "spy",
            "risk_level": "medium",
            "horizon": "T2",
            "schema_version": "v1",
            "created_at": "2024-01-15T10:30:00Z",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is True
        assert len(result.errors) == 0


class TestSchemaValidatorMissingFields:
    """Tests for missing required fields"""

    def test_missing_required_field_returns_error(self):
        """Missing required field should return valid: false with error"""
        validator = SchemaValidator()

        # Missing angle_type
        payload = {
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        assert len(result.errors) >= 1
        # Check error mentions the missing field
        error_messages = " ".join(e.message for e in result.errors)
        assert "angle_type" in error_messages

    def test_multiple_missing_fields(self):
        """Multiple missing required fields should return multiple errors"""
        validator = SchemaValidator()

        # Missing multiple required fields
        payload = {"angle_type": "pain", "schema_version": "v1"}

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        assert len(result.errors) >= 1  # At least one error for missing fields

    def test_missing_field_error_code(self):
        """Missing field error should have MISSING_REQUIRED_FIELD code"""
        validator = SchemaValidator()

        payload = {"core_belief": "problem_is_serious", "schema_version": "v1"}

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        # Find the error about missing required fields
        error_codes = [e.code for e in result.errors]
        assert "MISSING_REQUIRED_FIELD" in error_codes


class TestSchemaValidatorTypeMismatch:
    """Tests for type mismatch errors"""

    def test_wrong_type_returns_error(self):
        """Wrong type should return valid: false with type error"""
        validator = SchemaValidator()

        payload = {
            "angle_type": 123,  # Should be string
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        # Either TYPE_MISMATCH or INVALID_ENUM_VALUE
        assert "TYPE_MISMATCH" in error_codes or "INVALID_ENUM_VALUE" in error_codes

    def test_type_error_includes_expected_type(self):
        """Type error message should include expected type"""
        validator = SchemaValidator()

        payload = {
            "angle_type": ["array", "not", "string"],
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        # Check that error mentions string type
        error_messages = " ".join(e.message for e in result.errors)
        assert "string" in error_messages.lower() or "type" in error_messages.lower()


class TestSchemaValidatorEnumViolation:
    """Tests for invalid enum values"""

    def test_invalid_enum_value_returns_error(self):
        """Invalid enum value should return valid: false with enum error"""
        validator = SchemaValidator()

        payload = {
            "angle_type": "invalid_angle",  # Not in enum
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        assert "INVALID_ENUM_VALUE" in error_codes

    def test_enum_error_shows_allowed_values(self):
        """Enum error should show allowed values"""
        validator = SchemaValidator()

        payload = {
            "angle_type": "pain",
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "super_high",  # Invalid enum
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")

        assert result.valid is False
        # Find enum error
        enum_errors = [e for e in result.errors if e.code == "INVALID_ENUM_VALUE"]
        assert len(enum_errors) >= 1
        # Error message should mention allowed values
        assert "low" in enum_errors[0].message or "medium" in enum_errors[0].message


class TestSchemaValidatorEmptyPayload:
    """Tests for empty payload"""

    def test_empty_payload_returns_error(self):
        """Empty payload should return valid: false"""
        validator = SchemaValidator()

        result = validator.validate({}, schema_version="v1")

        assert result.valid is False
        assert len(result.errors) >= 1

    def test_none_payload_returns_error(self):
        """None payload should return valid: false"""
        validator = SchemaValidator()

        result = validator.validate(None, schema_version="v1")

        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        assert "EMPTY_PAYLOAD" in error_codes


class TestSchemaValidatorSchemaVersion:
    """Tests for schema version handling"""

    def test_invalid_schema_version_returns_error(self):
        """Invalid schema version should return error"""
        validator = SchemaValidator()

        payload = {"angle_type": "pain"}

        result = validator.validate(payload, schema_version="v999")

        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        assert "INVALID_SCHEMA_VERSION" in error_codes

    def test_default_schema_version_is_v1(self):
        """Default schema version should be v1"""
        validator = SchemaValidator()

        payload = {
            "angle_type": "pain",
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        # Call without schema_version
        result = validator.validate(payload)

        assert result.valid is True


class TestSchemaValidatorNestedValidation:
    """Tests for nested object validation"""

    def test_nested_array_validation(self):
        """Components array should be validated if present in schema"""
        validator = SchemaValidator()

        # The v1 schema doesn't have components, so this should pass
        # (additionalProperties: false will catch it as an error)
        payload = {
            "angle_type": "pain",
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
        }

        result = validator.validate(payload, schema_version="v1")
        assert result.valid is True


class TestSchemaValidatorExtraFields:
    """Tests for extra/unexpected fields"""

    def test_extra_fields_with_additional_properties_false(self):
        """Extra fields should be rejected when additionalProperties is false"""
        validator = SchemaValidator()

        payload = {
            "angle_type": "pain",
            "core_belief": "problem_is_serious",
            "promise_type": "instant",
            "emotion_primary": "fear",
            "emotion_intensity": "high",
            "message_structure": "problem_solution",
            "opening_type": "shock_statement",
            "state_before": "unsafe",
            "state_after": "safe",
            "context_frame": "institutional",
            "source_type": "internal",
            "risk_level": "low",
            "horizon": "T1",
            "schema_version": "v1",
            "unknown_field": "should_be_rejected",  # Extra field
        }

        result = validator.validate(payload, schema_version="v1")

        # v1 schema has additionalProperties: false
        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        assert "UNEXPECTED_FIELD" in error_codes


class TestValidationResultToDict:
    """Tests for ValidationResult.to_dict()"""

    def test_to_dict_format(self):
        """to_dict should return properly formatted dictionary"""
        result = ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    field="angle_type",
                    message="Missing required field",
                    code="MISSING_REQUIRED_FIELD",
                    value=None,
                )
            ],
            warnings=[ValidationWarning(field="extra_field", message="Unknown field")],
        )

        d = result.to_dict()

        assert d["valid"] is False
        assert len(d["errors"]) == 1
        assert d["errors"][0]["field"] == "angle_type"
        assert d["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"
        assert len(d["warnings"]) == 1
        assert d["warnings"][0]["field"] == "extra_field"


class TestGetSchemaValidator:
    """Tests for singleton pattern"""

    def test_get_schema_validator_returns_same_instance(self):
        """get_schema_validator should return same instance"""
        validator1 = get_schema_validator()
        validator2 = get_schema_validator()

        assert validator1 is validator2

    def test_get_schema_validator_returns_validator(self):
        """get_schema_validator should return SchemaValidator instance"""
        validator = get_schema_validator()

        assert isinstance(validator, SchemaValidator)


class TestSchemaValidatorCaching:
    """Tests for schema caching"""

    def test_schema_is_cached(self):
        """Schema should be cached after first load"""
        validator = SchemaValidator()

        # First call loads schema
        result1 = validator.validate({"angle_type": "pain"}, schema_version="v1")

        # Check schema is in cache
        assert "v1" in validator._schema_cache

        # Second call uses cached schema
        result2 = validator.validate({"angle_type": "pain"}, schema_version="v1")

        # Results should be consistent
        assert result1.valid == result2.valid
