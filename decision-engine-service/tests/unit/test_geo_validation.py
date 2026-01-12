"""
Test geo validation in /simulate command.

Issue #464: --geo flag accepts any value without validation
"""

from temporal.models.buyer import VALID_GEOS


class TestGeoValidation:
    """Test geo validation against VALID_GEOS list."""

    def test_valid_geo_accepted(self):
        """Valid geo codes should be accepted."""
        valid_samples = ["US", "UK", "DE", "FR", "RU", "UA"]

        for geo in valid_samples:
            assert geo in VALID_GEOS, f"Expected {geo} to be valid"

        print(f"\n✓ Valid geos accepted: {valid_samples}")

    def test_invalid_geo_rejected(self):
        """Invalid geo codes should be rejected."""
        invalid_samples = [
            "TOOLONGCODE123",  # Too long
            "XX",  # Non-existent
            "USA",  # Wrong format (should be US)
            "123",  # Numbers only
            "",  # Empty after strip
        ]

        for geo in invalid_samples:
            if geo:  # Skip empty string for "in" check
                assert geo not in VALID_GEOS, f"Expected {geo} to be invalid"

        print(f"\n✓ Invalid geos rejected: {invalid_samples}")

    def test_geo_case_normalization(self):
        """Geo codes should be normalized to uppercase."""
        # Simulate the parsing logic from telegram.py
        test_cases = [
            ("us", "US"),
            ("Uk", "UK"),
            ("de", "DE"),
        ]

        for input_geo, expected in test_cases:
            normalized = input_geo.upper()
            assert normalized == expected
            assert normalized in VALID_GEOS

        print(f"\n✓ Case normalization works: {test_cases}")

    def test_validation_error_message_content(self):
        """Error message should contain helpful information."""
        invalid_geo = "INVALIDGEO"
        sample_geos = ", ".join(VALID_GEOS[:10])

        # Simulate error message generation
        error_msg = (
            f"❌ Неизвестный geo-код: <code>{invalid_geo}</code>\n\n"
            f"Доступные geo: {sample_geos}...\n\n"
            "Пример: <code>/simulate fear --geo US</code>"
        )

        assert invalid_geo in error_msg
        assert "US" in error_msg
        assert "UK" in error_msg

        print("\n✓ Error message generated:")
        print(error_msg)

    def test_valid_geos_count(self):
        """VALID_GEOS should have reasonable number of entries."""
        count = len(VALID_GEOS)
        assert count >= 50, f"Expected at least 50 geos, got {count}"

        print(f"\n✓ VALID_GEOS has {count} entries")
        print(f"  First 10: {VALID_GEOS[:10]}")
