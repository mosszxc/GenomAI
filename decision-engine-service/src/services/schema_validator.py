"""
Schema Validator Service — Validates LLM output against JSON Schema
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError


@dataclass
class ValidationError:
    """Represents a validation error"""

    field: str
    message: str
    code: str
    value: Optional[any] = None


@dataclass
class ValidationWarning:
    """Represents a validation warning"""

    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of schema validation"""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "valid": self.valid,
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                    "code": e.code,
                    "value": e.value,
                }
                for e in self.errors
            ],
            "warnings": [
                {"field": w.field, "message": w.message} for w in self.warnings
            ],
        }


class SchemaValidator:
    """
    Validates payloads against JSON Schema.
    Supports multiple schema versions.
    """

    # Schema directory relative to project root
    # __file__ = decision-engine-service/src/services/schema_validator.py
    # .parent (x4) = GenomAI/
    SCHEMA_DIR = (
        Path(__file__).parent.parent.parent.parent / "infrastructure" / "schemas"
    )

    # Schema file mapping
    SCHEMA_FILES = {
        "v1": "idea_schema_v1.json",
        "v2": "idea_schema_v2.json",
    }

    def __init__(self):
        """Initialize validator with schema cache"""
        self._schema_cache: dict = {}

    def _load_schema(self, schema_version: str) -> dict:
        """
        Load JSON schema from file.

        Args:
            schema_version: Schema version (v1, v2, etc.)

        Returns:
            dict: JSON Schema

        Raises:
            ValueError: If schema version not found
        """
        if schema_version in self._schema_cache:
            return self._schema_cache[schema_version]

        if schema_version not in self.SCHEMA_FILES:
            raise ValueError(
                f"Unknown schema version: {schema_version}. Available: {list(self.SCHEMA_FILES.keys())}"
            )

        schema_path = self.SCHEMA_DIR / self.SCHEMA_FILES[schema_version]

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, "r") as f:
            schema = json.load(f)

        self._schema_cache[schema_version] = schema
        return schema

    def _extract_field_path(self, error: JsonSchemaValidationError) -> str:
        """Extract field path from validation error"""
        if error.absolute_path:
            return ".".join(str(p) for p in error.absolute_path)
        # For required field errors, extract from message
        if "required property" in error.message:
            return error.message.split("'")[1] if "'" in error.message else "root"
        return "root"

    def _determine_error_code(self, error: JsonSchemaValidationError) -> str:
        """Determine error code based on validation error type"""
        validator = error.validator

        code_mapping = {
            "required": "MISSING_REQUIRED_FIELD",
            "type": "TYPE_MISMATCH",
            "enum": "INVALID_ENUM_VALUE",
            "format": "INVALID_FORMAT",
            "minLength": "VALUE_TOO_SHORT",
            "maxLength": "VALUE_TOO_LONG",
            "minimum": "VALUE_TOO_SMALL",
            "maximum": "VALUE_TOO_LARGE",
            "pattern": "PATTERN_MISMATCH",
            "additionalProperties": "UNEXPECTED_FIELD",
            "minItems": "ARRAY_TOO_SHORT",
            "maxItems": "ARRAY_TOO_LONG",
            "uniqueItems": "DUPLICATE_ITEMS",
        }

        return code_mapping.get(validator, "VALIDATION_ERROR")

    def _format_error_message(
        self, error: JsonSchemaValidationError, field: str
    ) -> str:
        """Format user-friendly error message"""
        validator = error.validator

        if validator == "required":
            missing = (
                list(error.validator_value)
                if hasattr(error.validator_value, "__iter__")
                else [error.validator_value]
            )
            return f"Missing required field(s): {', '.join(missing)}"

        if validator == "type":
            expected = error.validator_value
            actual = type(error.instance).__name__
            return f"Expected type '{expected}', got '{actual}'"

        if validator == "enum":
            allowed = error.validator_value
            return f"Invalid value. Allowed values: {allowed}"

        if validator == "additionalProperties":
            return f"Unexpected field: {field}"

        return error.message

    def validate(self, payload: dict, schema_version: str = "v1") -> ValidationResult:
        """
        Validate payload against JSON schema.

        Args:
            payload: LLM output to validate
            schema_version: Schema version to use (default: v1)

        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        # Handle empty payload
        if not payload:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        field="root",
                        message="Payload cannot be empty",
                        code="EMPTY_PAYLOAD",
                    )
                ],
            )

        # Load schema
        try:
            schema = self._load_schema(schema_version)
        except (ValueError, FileNotFoundError) as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        field="schema_version",
                        message=str(e),
                        code="INVALID_SCHEMA_VERSION",
                    )
                ],
            )

        # Create validator
        validator = Draft7Validator(schema)

        # Collect errors
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []

        for error in validator.iter_errors(payload):
            field = self._extract_field_path(error)
            code = self._determine_error_code(error)
            message = self._format_error_message(error, field)

            # Get the invalid value for context
            value = error.instance if error.absolute_path else None

            errors.append(
                ValidationError(field=field, message=message, code=code, value=value)
            )

        # Check for extra fields (warning, not error if additionalProperties is not false)
        if schema.get("additionalProperties") is not False:
            schema_props = set(schema.get("properties", {}).keys())
            payload_props = set(payload.keys()) if isinstance(payload, dict) else set()
            extra_props = payload_props - schema_props

            for prop in extra_props:
                warnings.append(
                    ValidationWarning(
                        field=prop, message=f"Field '{prop}' is not defined in schema"
                    )
                )

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )


# Singleton instance
_validator_instance: Optional[SchemaValidator] = None


def get_schema_validator() -> SchemaValidator:
    """Get or create singleton SchemaValidator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SchemaValidator()
    return _validator_instance
