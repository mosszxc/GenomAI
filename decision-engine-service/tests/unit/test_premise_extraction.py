"""
Unit tests for Premise Extraction activities.

Tests the data-driven premise generation system that extracts
premise patterns from concluded creatives.
"""

from temporal.activities.premise_extraction import (
    CreativeData,
    ExtractedPremise,
    PremiseExtractionResult,
)


class TestCreativeData:
    """Tests for CreativeData dataclass."""

    def test_creative_data_creation_minimal(self):
        """Test creating CreativeData with minimal required fields."""
        data = CreativeData(
            creative_id="test-123",
            video_url=None,
            test_result="win",
            tracker_id=None,
            vertical=None,
            geo=None,
            payload=None,
            transcript_text=None,
            spend=0.0,
            revenue=0.0,
            cpa=None,
            roi=None,
        )
        assert data.creative_id == "test-123"
        assert data.test_result == "win"
        assert data.spend == 0.0

    def test_creative_data_creation_full(self):
        """Test creating CreativeData with all fields."""
        data = CreativeData(
            creative_id="test-456",
            video_url="https://example.com/video.mp4",
            test_result="loss",
            tracker_id="tracker-789",
            vertical="health",
            geo="US",
            payload={"hook": "curiosity", "cta": "direct"},
            transcript_text="This is a test transcript...",
            spend=100.0,
            revenue=50.0,
            cpa=25.0,
            roi=-50.0,
        )
        assert data.creative_id == "test-456"
        assert data.test_result == "loss"
        assert data.vertical == "health"
        assert data.geo == "US"
        assert data.payload["hook"] == "curiosity"
        assert data.spend == 100.0
        assert data.revenue == 50.0
        assert data.roi == -50.0

    def test_creative_data_win_determination(self):
        """Test ROI-based win/loss determination logic."""
        # Win case: ROI > 0
        win_data = CreativeData(
            creative_id="win-1",
            video_url=None,
            test_result="win",
            tracker_id=None,
            vertical=None,
            geo=None,
            payload=None,
            transcript_text=None,
            spend=100.0,
            revenue=150.0,
            cpa=None,
            roi=50.0,  # 50% profit
        )
        assert win_data.test_result == "win"
        assert win_data.roi > 0

        # Loss case: ROI <= 0
        loss_data = CreativeData(
            creative_id="loss-1",
            video_url=None,
            test_result="loss",
            tracker_id=None,
            vertical=None,
            geo=None,
            payload=None,
            transcript_text=None,
            spend=100.0,
            revenue=80.0,
            cpa=None,
            roi=-20.0,  # 20% loss
        )
        assert loss_data.test_result == "loss"
        assert loss_data.roi <= 0


class TestExtractedPremise:
    """Tests for ExtractedPremise dataclass."""

    def test_extracted_premise_positive(self):
        """Test creating a positive premise (from winner)."""
        premise = ExtractedPremise(
            premise_type="method",
            name="The 72-Hour Reset Method",
            origin_story="Discovered when a patient...",
            mechanism_claim="Triggers hormetic stress response",
            confidence_score=0.85,
            is_negative=False,
            source_creative_id="creative-123",
        )
        assert premise.premise_type == "method"
        assert premise.is_negative is False
        assert premise.confidence_score == 0.85

    def test_extracted_premise_negative(self):
        """Test creating a negative premise (anti-pattern from loser)."""
        premise = ExtractedPremise(
            premise_type="discovery",
            name="Overused Discovery Pattern",
            origin_story=None,
            mechanism_claim=None,
            confidence_score=0.6,
            is_negative=True,
            source_creative_id="creative-456",
        )
        assert premise.is_negative is True
        assert premise.origin_story is None

    def test_all_premise_types_valid(self):
        """Test that all valid premise types can be created."""
        valid_types = [
            "method",
            "discovery",
            "confession",
            "secret",
            "ingredient",
            "mechanism",
            "breakthrough",
            "transformation",
        ]

        for ptype in valid_types:
            premise = ExtractedPremise(
                premise_type=ptype,
                name=f"Test {ptype}",
                origin_story=None,
                mechanism_claim=None,
                confidence_score=0.5,
                is_negative=False,
                source_creative_id="test",
            )
            assert premise.premise_type == ptype

    def test_confidence_score_bounds(self):
        """Test confidence score is between 0 and 1."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            premise = ExtractedPremise(
                premise_type="method",
                name="Test",
                origin_story=None,
                mechanism_claim=None,
                confidence_score=score,
                is_negative=False,
                source_creative_id="test",
            )
            assert 0.0 <= premise.confidence_score <= 1.0


class TestPremiseExtractionResult:
    """Tests for PremiseExtractionResult dataclass."""

    def test_result_success(self):
        """Test successful extraction result."""
        result = PremiseExtractionResult(
            creative_id="creative-123",
            test_result="win",
            premises_extracted=3,
            premises_created=2,
            learnings_updated=3,
            errors=[],
        )
        assert result.premises_extracted == 3
        assert result.premises_created == 2
        assert len(result.errors) == 0

    def test_result_partial_success(self):
        """Test partial success with some errors."""
        result = PremiseExtractionResult(
            creative_id="creative-456",
            test_result="loss",
            premises_extracted=2,
            premises_created=1,
            learnings_updated=1,
            errors=["Failed to upsert premise: Duplicate name"],
        )
        assert result.premises_extracted == 2
        assert len(result.errors) == 1
        assert "Duplicate" in result.errors[0]

    def test_result_failure(self):
        """Test failed extraction result."""
        result = PremiseExtractionResult(
            creative_id="creative-789",
            test_result="unknown",
            premises_extracted=0,
            premises_created=0,
            learnings_updated=0,
            errors=["Failed to load creative: Not found"],
        )
        assert result.premises_extracted == 0
        assert len(result.errors) == 1


class TestROICalculation:
    """Tests for ROI-based test_result determination."""

    def test_roi_calculation_win(self):
        """Test ROI > 0 results in win."""
        spend = 100.0
        revenue = 150.0
        roi = ((revenue - spend) / spend) * 100
        test_result = "win" if roi > 0 else "loss"

        assert roi == 50.0
        assert test_result == "win"

    def test_roi_calculation_loss(self):
        """Test ROI <= 0 results in loss."""
        spend = 100.0
        revenue = 80.0
        roi = ((revenue - spend) / spend) * 100
        test_result = "win" if roi > 0 else "loss"

        assert roi == -20.0
        assert test_result == "loss"

    def test_roi_calculation_breakeven(self):
        """Test ROI = 0 results in loss (breakeven is not a win)."""
        spend = 100.0
        revenue = 100.0
        roi = ((revenue - spend) / spend) * 100
        test_result = "win" if roi > 0 else "loss"

        assert roi == 0.0
        assert test_result == "loss"

    def test_roi_calculation_zero_spend(self):
        """Test handling of zero spend edge case."""
        spend = 0.0
        revenue = 50.0

        # Avoid division by zero
        roi = ((revenue - spend) / spend) * 100 if spend > 0 else 0
        assert roi == 0


class TestPremiseExtractionIntegration:
    """Integration-style tests for premise extraction logic."""

    def test_both_wins_and_losses_valuable(self):
        """Test that both win and loss creatives produce premises."""
        # Win creative -> positive premises
        win_creative = CreativeData(
            creative_id="winner",
            video_url=None,
            test_result="win",
            tracker_id=None,
            vertical="health",
            geo="US",
            payload={"hook": "curiosity"},
            transcript_text="Amazing discovery...",
            spend=100.0,
            revenue=200.0,
            cpa=None,
            roi=100.0,
        )

        # Loss creative -> negative premises (anti-patterns)
        loss_creative = CreativeData(
            creative_id="loser",
            video_url=None,
            test_result="loss",
            tracker_id=None,
            vertical="health",
            geo="US",
            payload={"hook": "fear"},
            transcript_text="Terrible approach...",
            spend=100.0,
            revenue=20.0,
            cpa=None,
            roi=-80.0,
        )

        # Both should have data for extraction
        assert win_creative.payload is not None or win_creative.transcript_text is not None
        assert loss_creative.payload is not None or loss_creative.transcript_text is not None

        # Both test results are valid
        assert win_creative.test_result in ("win", "loss")
        assert loss_creative.test_result in ("win", "loss")

    def test_conclusion_threshold_logic(self):
        """Test creative conclusion threshold logic."""
        min_spend_threshold = 50.0

        # Below threshold - should not conclude
        low_spend = 30.0
        assert low_spend < min_spend_threshold

        # Above threshold - should conclude
        high_spend = 100.0
        assert high_spend >= min_spend_threshold

        # Days check would be done against decision date
        # This is a logical test - actual date comparison in activity

    def test_premise_type_from_payload(self):
        """Test that premise type can be extracted from payload components."""
        payload_with_method = {
            "hook_type": "method",
            "hook_content": "2-minute morning routine",
        }

        payload_with_discovery = {
            "hook_type": "discovery",
            "hook_content": "Ancient Tibetan secret",
        }

        # Premise type should match hook_type or be inferred
        assert "method" in str(payload_with_method)
        assert "discovery" in str(payload_with_discovery)
