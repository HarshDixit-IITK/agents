"""
Unit tests for filler detection module.

Run tests with:
    pytest test_filler_detector.py -v
"""

import pytest
from filler_detector import FillerDetectionConfig, FillerDetector, split_words


class TestFillerDetector:
    """Test suite for FillerDetector class."""
    
    def test_basic_filler_detection(self):
        """Test basic filler word detection."""
        config = FillerDetectionConfig(
            ignored_words=["uh", "um", "hmm"],
            min_real_words=1,
        )
        detector = FillerDetector(config)
        
        # Test filler-only utterance
        result = detector.analyze_transcript("uh um hmm")
        assert result.is_filler_only is True
        assert len(result.detected_fillers) == 3
        assert result.real_word_count == 0
        
        # Test mixed content
        result = detector.analyze_transcript("uh wait a second")
        assert result.is_filler_only is False
        assert "uh" in result.detected_fillers
        assert result.real_word_count == 3
    
    def test_agent_state_filtering(self):
        """Test that fillers are filtered based on agent state."""
        config = FillerDetectionConfig(ignored_words=["uh", "um"])
        detector = FillerDetector(config)
        
        # Agent speaking - fillers should be ignored
        result = detector.analyze_transcript("uh um", agent_state="speaking")
        assert result.is_filler_only is True
        assert result.should_interrupt is False
        assert "agent speaking" in result.reason.lower()
        
        # Agent quiet - fillers should be registered
        result = detector.analyze_transcript("uh um", agent_state="listening")
        assert result.is_filler_only is True
        assert result.should_interrupt is True
        assert "agent quiet" in result.reason.lower()
    
    def test_real_interruptions(self):
        """Test that real interruptions are always allowed."""
        config = FillerDetectionConfig(ignored_words=["uh", "um"])
        detector = FillerDetector(config)
        
        test_cases = [
            "wait",
            "stop",
            "no not that",
            "hold on",
            "uh wait a second",
            "um actually no",
        ]
        
        for text in test_cases:
            result = detector.analyze_transcript(text, agent_state="speaking")
            assert result.should_interrupt is True, f"Failed for: {text}"
            assert not result.is_filler_only, f"Incorrectly marked as filler: {text}"
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive filler matching."""
        config = FillerDetectionConfig(
            ignored_words=["uh", "um"],
            case_sensitive=False,
        )
        detector = FillerDetector(config)
        
        test_cases = ["uh", "UH", "Uh", "uH", "UM", "Um", "uM"]
        
        for text in test_cases:
            result = detector.analyze_transcript(text)
            assert result.is_filler_only is True, f"Failed for: {text}"
    
    def test_case_sensitive_matching(self):
        """Test case-sensitive filler matching."""
        config = FillerDetectionConfig(
            ignored_words=["uh"],
            case_sensitive=True,
        )
        detector = FillerDetector(config)
        
        # Should match
        result = detector.analyze_transcript("uh")
        assert result.is_filler_only is True
        
        # Should not match
        result = detector.analyze_transcript("UH")
        assert result.is_filler_only is False
    
    def test_whole_word_matching(self):
        """Test whole word vs substring matching."""
        config = FillerDetectionConfig(
            ignored_words=["um"],
            whole_word_match=True,
        )
        detector = FillerDetector(config)
        
        # Should match whole word
        result = detector.analyze_transcript("um")
        assert result.is_filler_only is True
        
        # Should not match as substring
        result = detector.analyze_transcript("umbrella")
        assert result.is_filler_only is False
        assert result.real_word_count == 1
    
    def test_substring_matching(self):
        """Test substring matching when enabled."""
        config = FillerDetectionConfig(
            ignored_words=["um"],
            whole_word_match=False,
        )
        detector = FillerDetector(config)
        
        # Should match even in substring
        result = detector.analyze_transcript("umbrella")
        # After removing "um", we get "brella" which is 1 word
        assert "um" in result.detected_fillers
    
    def test_confidence_threshold(self):
        """Test confidence threshold filtering."""
        config = FillerDetectionConfig(
            ignored_words=["uh"],
            confidence_threshold=0.7,
        )
        detector = FillerDetector(config)
        
        # Low confidence - should not process
        result = detector.analyze_transcript("uh", confidence=0.5)
        assert result.should_interrupt is False
        assert "confidence" in result.reason.lower()
        
        # High confidence - should process
        result = detector.analyze_transcript("uh", confidence=0.8)
        assert result.confidence == 0.8
    
    def test_min_real_words(self):
        """Test minimum real words requirement."""
        config = FillerDetectionConfig(
            ignored_words=["uh", "um"],
            min_real_words=2,  # Require at least 2 real words
        )
        detector = FillerDetector(config)
        
        # Only 1 real word - counts as filler-only
        result = detector.analyze_transcript("uh stop")
        assert result.is_filler_only is True
        assert result.real_word_count == 1
        
        # 2 real words - not filler-only
        result = detector.analyze_transcript("uh wait stop")
        assert result.is_filler_only is False
        assert result.real_word_count == 2
    
    def test_multilingual_fillers(self):
        """Test detection of multilingual filler words."""
        config = FillerDetectionConfig(
            ignored_words=[
                "uh", "um",  # English
                "haan", "achha",  # Hindi
                "嗯", "啊",  # Chinese
                "うん", "ええと",  # Japanese
            ],
        )
        detector = FillerDetector(config)
        
        test_cases = [
            ("uh um", True),
            ("haan achha", True),
            ("嗯 啊", True),
            ("うん ええと", True),
            ("haan wait", False),  # Mixed with real word
        ]
        
        for text, should_be_filler in test_cases:
            result = detector.analyze_transcript(text)
            assert result.is_filler_only == should_be_filler, f"Failed for: {text}"
    
    def test_dynamic_word_updates(self):
        """Test dynamic updates to ignored words."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        # Initial - only "uh" is ignored
        result = detector.analyze_transcript("uh okay")
        assert result.is_filler_only is False
        assert result.real_word_count == 1
        
        # Add "okay" to ignored list
        detector.add_ignored_words(["okay"])
        
        # Now both should be ignored
        result = detector.analyze_transcript("uh okay")
        assert result.is_filler_only is True
        assert result.real_word_count == 0
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        # Process some transcripts
        detector.analyze_transcript("uh", agent_state="speaking")
        detector.analyze_transcript("wait", agent_state="speaking")
        detector.analyze_transcript("uh", agent_state="listening")
        
        stats = detector.get_stats()
        assert stats["total_transcripts"] == 3
        assert stats["filler_only_detections"] == 2
        assert stats["valid_interruptions"] == 1
        assert stats["ignored_while_agent_speaking"] == 1
        assert stats["allowed_while_agent_quiet"] == 1
    
    def test_empty_transcript(self):
        """Test handling of empty transcripts."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("")
        assert result.real_word_count == 0
        assert result.is_filler_only is True
    
    def test_punctuation_handling(self):
        """Test that punctuation is handled correctly."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh, wait!")
        assert result.is_filler_only is False
        assert "uh" in result.detected_fillers
        # "wait!" should be counted as a real word
        assert result.real_word_count >= 1
    
    def test_disabled_detector(self):
        """Test that disabled detector passes everything through."""
        config = FillerDetectionConfig(
            ignored_words=["uh"],
            enabled=False,
        )
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh", agent_state="speaking")
        assert result.should_interrupt is True
        assert "disabled" in result.reason.lower()
    
    def test_filtered_text_output(self):
        """Test that filtered text correctly removes fillers."""
        config = FillerDetectionConfig(ignored_words=["uh", "um"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh wait um one second")
        assert "uh" not in result.filtered_text.lower()
        assert "um" not in result.filtered_text.lower()
        assert "wait" in result.filtered_text.lower()
        assert "second" in result.filtered_text.lower()


class TestSplitWords:
    """Test suite for split_words helper function."""
    
    def test_basic_splitting(self):
        """Test basic word splitting."""
        assert split_words("hello world") == ["hello", "world"]
        assert split_words("one two three") == ["one", "two", "three"]
    
    def test_empty_string(self):
        """Test empty string handling."""
        assert split_words("") == []
        assert split_words("   ") == []
    
    def test_character_splitting(self):
        """Test character-level splitting for CJK."""
        # Without character splitting
        result = split_words("你好", split_character=False)
        assert len(result) == 1
        
        # With character splitting
        result = split_words("你好", split_character=True)
        assert len(result) == 2


class TestFillerDetectionConfig:
    """Test suite for FillerDetectionConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = FillerDetectionConfig()
        assert len(config.ignored_words) > 0
        assert config.confidence_threshold == 0.5
        assert config.case_sensitive is False
        assert config.whole_word_match is True
        assert config.min_real_words == 1
        assert config.enabled is True
    
    def test_case_normalization(self):
        """Test that words are normalized based on case sensitivity."""
        config = FillerDetectionConfig(
            ignored_words=["UH", "UM"],
            case_sensitive=False,
        )
        # Should be lowercased
        assert all(word.islower() for word in config.ignored_words)
        
        config = FillerDetectionConfig(
            ignored_words=["UH", "UM"],
            case_sensitive=True,
        )
        # Should preserve case
        assert "UH" in config.ignored_words


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_long_transcript(self):
        """Test handling of very long transcripts."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        # Create a long transcript
        long_text = "uh " + " ".join(["word"] * 1000)
        result = detector.analyze_transcript(long_text)
        
        assert result.is_filler_only is False
        assert "uh" in result.detected_fillers
        assert result.real_word_count == 1000
    
    def test_repeated_fillers(self):
        """Test handling of repeated filler words."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh uh uh uh uh")
        assert result.is_filler_only is True
        assert len(result.detected_fillers) == 5
    
    def test_special_characters(self):
        """Test handling of special characters."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh @#$% wait")
        assert result.is_filler_only is False
        # Should still detect real words despite special chars
        assert result.real_word_count >= 1
    
    def test_numbers(self):
        """Test handling of numbers in transcripts."""
        config = FillerDetectionConfig(ignored_words=["uh"])
        detector = FillerDetector(config)
        
        result = detector.analyze_transcript("uh 123 456")
        assert result.is_filler_only is False
        assert result.real_word_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

