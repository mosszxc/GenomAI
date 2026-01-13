"""
Unit tests for activity input validators.

Tests validation functions in temporal/models/validators.py
to ensure proper validation of:
- UUID strings
- SHA256 hashes
- URLs
- Enums/status values
"""

import pytest


class TestValidateUUID:
    """Tests for validate_uuid function"""

    def test_valid_uuid(self):
        """Valid UUID should pass"""
        from temporal.models.validators import validate_uuid

        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = validate_uuid(valid_uuid, "test_id")
        assert result == valid_uuid

    def test_valid_uuid_uppercase(self):
        """Uppercase UUID should be normalized"""
        from temporal.models.validators import validate_uuid

        upper_uuid = "123E4567-E89B-12D3-A456-426614174000"
        result = validate_uuid(upper_uuid, "test_id")
        # uuid.UUID normalizes to lowercase
        assert result == "123e4567-e89b-12d3-a456-426614174000"

    def test_valid_uuid_no_dashes(self):
        """UUID without dashes should be accepted"""
        from temporal.models.validators import validate_uuid

        no_dash_uuid = "123e4567e89b12d3a456426614174000"
        result = validate_uuid(no_dash_uuid, "test_id")
        # uuid.UUID formats with dashes
        assert result == "123e4567-e89b-12d3-a456-426614174000"

    def test_invalid_uuid_format(self):
        """Invalid UUID format should raise ValueError"""
        from temporal.models.validators import validate_uuid

        with pytest.raises(ValueError) as exc_info:
            validate_uuid("not-a-uuid", "test_id")
        assert "test_id must be a valid UUID" in str(exc_info.value)

    def test_empty_uuid(self):
        """Empty string should raise ValueError"""
        from temporal.models.validators import validate_uuid

        with pytest.raises(ValueError) as exc_info:
            validate_uuid("", "test_id")
        assert "test_id cannot be empty" in str(exc_info.value)

    def test_invalid_uuid_short(self):
        """Too short UUID should raise ValueError"""
        from temporal.models.validators import validate_uuid

        with pytest.raises(ValueError) as exc_info:
            validate_uuid("123e4567", "test_id")
        assert "test_id must be a valid UUID" in str(exc_info.value)


class TestValidateSHA256Hash:
    """Tests for validate_sha256_hash function"""

    def test_valid_hash(self):
        """Valid SHA256 hash should pass"""
        from temporal.models.validators import validate_sha256_hash

        valid_hash = "a" * 64
        result = validate_sha256_hash(valid_hash, "canonical_hash")
        assert result == valid_hash

    def test_valid_hash_mixed_case(self):
        """Uppercase hash should be lowercased"""
        from temporal.models.validators import validate_sha256_hash

        upper_hash = "A" * 64
        result = validate_sha256_hash(upper_hash, "canonical_hash")
        assert result == "a" * 64

    def test_valid_hash_hex_chars(self):
        """Hash with all valid hex chars should pass"""
        from temporal.models.validators import validate_sha256_hash

        valid_hash = "0123456789abcdef" * 4
        result = validate_sha256_hash(valid_hash, "canonical_hash")
        assert result == valid_hash

    def test_invalid_hash_too_short(self):
        """Hash shorter than 64 chars should fail"""
        from temporal.models.validators import validate_sha256_hash

        with pytest.raises(ValueError) as exc_info:
            validate_sha256_hash("abc", "canonical_hash")
        assert "must be 64 characters" in str(exc_info.value)

    def test_invalid_hash_too_long(self):
        """Hash longer than 64 chars should fail"""
        from temporal.models.validators import validate_sha256_hash

        with pytest.raises(ValueError) as exc_info:
            validate_sha256_hash("a" * 65, "canonical_hash")
        assert "must be 64 characters" in str(exc_info.value)

    def test_invalid_hash_non_hex(self):
        """Hash with non-hex chars should fail"""
        from temporal.models.validators import validate_sha256_hash

        with pytest.raises(ValueError) as exc_info:
            validate_sha256_hash("g" * 64, "canonical_hash")
        assert "must contain only hex characters" in str(exc_info.value)

    def test_empty_hash(self):
        """Empty string should fail"""
        from temporal.models.validators import validate_sha256_hash

        with pytest.raises(ValueError) as exc_info:
            validate_sha256_hash("", "canonical_hash")
        assert "cannot be empty" in str(exc_info.value)


class TestValidateURL:
    """Tests for validate_url function"""

    def test_valid_https_url(self):
        """Valid HTTPS URL should pass"""
        from temporal.models.validators import validate_url

        url = "https://example.com/video.mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_valid_http_url(self):
        """Valid HTTP URL should pass"""
        from temporal.models.validators import validate_url

        url = "http://example.com/video.mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_valid_url_with_port(self):
        """URL with port should pass"""
        from temporal.models.validators import validate_url

        url = "https://example.com:8080/video.mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_valid_url_with_query(self):
        """URL with query string should pass"""
        from temporal.models.validators import validate_url

        url = "https://example.com/video?id=123&format=mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_valid_localhost_url(self):
        """Localhost URL should pass"""
        from temporal.models.validators import validate_url

        url = "http://localhost:8000/video.mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_valid_ip_url(self):
        """IP address URL should pass"""
        from temporal.models.validators import validate_url

        url = "http://192.168.1.1:8080/video.mp4"
        result = validate_url(url, "video_url")
        assert result == url

    def test_invalid_url_no_protocol(self):
        """URL without protocol should fail"""
        from temporal.models.validators import validate_url

        with pytest.raises(ValueError) as exc_info:
            validate_url("example.com/video.mp4", "video_url")
        assert "must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_invalid_url_ftp(self):
        """FTP URL should fail"""
        from temporal.models.validators import validate_url

        with pytest.raises(ValueError) as exc_info:
            validate_url("ftp://example.com/video.mp4", "video_url")
        assert "must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_empty_url(self):
        """Empty string should fail"""
        from temporal.models.validators import validate_url

        with pytest.raises(ValueError) as exc_info:
            validate_url("", "video_url")
        assert "cannot be empty" in str(exc_info.value)


class TestValidateOptionalUUID:
    """Tests for validate_optional_uuid function"""

    def test_none_returns_none(self):
        """None should return None"""
        from temporal.models.validators import validate_optional_uuid

        result = validate_optional_uuid(None, "buyer_id")
        assert result is None

    def test_valid_uuid_passes(self):
        """Valid UUID should pass through"""
        from temporal.models.validators import validate_optional_uuid

        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = validate_optional_uuid(valid_uuid, "buyer_id")
        assert result == valid_uuid

    def test_invalid_uuid_raises(self):
        """Invalid UUID should raise ValueError"""
        from temporal.models.validators import validate_optional_uuid

        with pytest.raises(ValueError) as exc_info:
            validate_optional_uuid("not-a-uuid", "buyer_id")
        assert "buyer_id must be a valid UUID" in str(exc_info.value)


class TestValidateEnum:
    """Tests for validate_enum function"""

    def test_valid_enum_value(self):
        """Valid enum value should pass"""
        from temporal.models.validators import validate_enum, CREATIVE_STATUSES

        result = validate_enum("processing", CREATIVE_STATUSES, "status")
        assert result == "processing"

    def test_all_creative_statuses(self):
        """All creative statuses should be valid"""
        from temporal.models.validators import validate_enum, CREATIVE_STATUSES

        for status in ["registered", "processing", "processed", "failed"]:
            result = validate_enum(status, CREATIVE_STATUSES, "status")
            assert result == status

    def test_invalid_enum_value(self):
        """Invalid enum value should fail"""
        from temporal.models.validators import validate_enum, CREATIVE_STATUSES

        with pytest.raises(ValueError) as exc_info:
            validate_enum("invalid_status", CREATIVE_STATUSES, "status")
        assert "must be one of" in str(exc_info.value)

    def test_empty_enum_value(self):
        """Empty string should fail"""
        from temporal.models.validators import validate_enum, CREATIVE_STATUSES

        with pytest.raises(ValueError) as exc_info:
            validate_enum("", CREATIVE_STATUSES, "status")
        assert "cannot be empty" in str(exc_info.value)


class TestValidateDictPayload:
    """Tests for validate_dict_payload function"""

    def test_valid_dict(self):
        """Valid dict should pass"""
        from temporal.models.validators import validate_dict_payload

        payload = {"key": "value", "nested": {"a": 1}}
        result = validate_dict_payload(payload, "payload")
        assert result == payload

    def test_empty_dict(self):
        """Empty dict should pass"""
        from temporal.models.validators import validate_dict_payload

        result = validate_dict_payload({}, "payload")
        assert result == {}

    def test_string_fails(self):
        """String should fail"""
        from temporal.models.validators import validate_dict_payload

        with pytest.raises(ValueError) as exc_info:
            validate_dict_payload("not a dict", "payload")
        assert "must be a dict" in str(exc_info.value)

    def test_list_fails(self):
        """List should fail"""
        from temporal.models.validators import validate_dict_payload

        with pytest.raises(ValueError) as exc_info:
            validate_dict_payload([1, 2, 3], "payload")
        assert "must be a dict" in str(exc_info.value)

    def test_none_fails(self):
        """None should fail"""
        from temporal.models.validators import validate_dict_payload

        with pytest.raises(ValueError) as exc_info:
            validate_dict_payload(None, "payload")
        assert "must be a dict" in str(exc_info.value)


class TestSourceTypes:
    """Tests for SOURCE_TYPES enum"""

    def test_all_source_types_valid(self):
        """All defined source types should be valid"""
        from temporal.models.validators import validate_enum, SOURCE_TYPES

        for source in ["telegram", "keitaro", "historical", "spy", "user"]:
            result = validate_enum(source, SOURCE_TYPES, "source_type")
            assert result == source


class TestValidateSafeString:
    """Tests for validate_safe_string function - URL injection prevention"""

    def test_valid_alphanumeric(self):
        """Alphanumeric strings should pass"""
        from temporal.models.validators import validate_safe_string

        result = validate_safe_string("RU", "geo")
        assert result == "RU"

    def test_valid_with_underscore(self):
        """Strings with underscores should pass"""
        from temporal.models.validators import validate_safe_string

        result = validate_safe_string("angle_type", "component_type")
        assert result == "angle_type"

    def test_valid_with_hyphen(self):
        """Strings with hyphens should pass"""
        from temporal.models.validators import validate_safe_string

        result = validate_safe_string("hook-mechanism", "component_type")
        assert result == "hook-mechanism"

    def test_valid_mixed(self):
        """Mixed alphanumeric, underscore, hyphen should pass"""
        from temporal.models.validators import validate_safe_string

        result = validate_safe_string("test_value-123", "field")
        assert result == "test_value-123"

    def test_invalid_sql_injection(self):
        """SQL injection attempt should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("RU'; DROP TABLE premises; --", "geo")
        assert "contains unsafe characters" in str(exc_info.value)

    def test_invalid_url_injection(self):
        """URL manipulation attempt should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("value&other_param=eq.attack", "field")
        assert "contains unsafe characters" in str(exc_info.value)

    def test_invalid_postgrest_operator(self):
        """PostgREST operator injection should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("value.neq.other", "field")
        assert "contains unsafe characters" in str(exc_info.value)

    def test_invalid_spaces(self):
        """Strings with spaces should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("value with spaces", "field")
        assert "contains unsafe characters" in str(exc_info.value)

    def test_invalid_special_chars(self):
        """Special characters should fail"""
        from temporal.models.validators import validate_safe_string

        for char in ["=", "&", "?", "/", "\\", "'", '"', ";", "(", ")"]:
            with pytest.raises(ValueError):
                validate_safe_string(f"value{char}test", "field")

    def test_empty_string_fails(self):
        """Empty string should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("", "field")
        assert "cannot be empty" in str(exc_info.value)

    def test_max_length_exceeded(self):
        """String exceeding max length should fail"""
        from temporal.models.validators import validate_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_safe_string("a" * 101, "field", max_length=100)
        assert "exceeds maximum length" in str(exc_info.value)

    def test_custom_max_length(self):
        """Custom max length should be respected"""
        from temporal.models.validators import validate_safe_string

        # Should pass with custom length
        result = validate_safe_string("a" * 50, "field", max_length=50)
        assert result == "a" * 50

        # Should fail with custom length
        with pytest.raises(ValueError):
            validate_safe_string("a" * 51, "field", max_length=50)


class TestValidateOptionalSafeString:
    """Tests for validate_optional_safe_string function"""

    def test_none_returns_none(self):
        """None should return None"""
        from temporal.models.validators import validate_optional_safe_string

        result = validate_optional_safe_string(None, "geo")
        assert result is None

    def test_valid_string_passes(self):
        """Valid string should pass through"""
        from temporal.models.validators import validate_optional_safe_string

        result = validate_optional_safe_string("RU", "geo")
        assert result == "RU"

    def test_invalid_string_raises(self):
        """Invalid string should raise ValueError"""
        from temporal.models.validators import validate_optional_safe_string

        with pytest.raises(ValueError) as exc_info:
            validate_optional_safe_string("RU&attack=true", "geo")
        assert "contains unsafe characters" in str(exc_info.value)
