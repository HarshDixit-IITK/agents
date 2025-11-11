"""
Filler Detection Module for LiveKit Agents

This module provides intelligent filler word detection to prevent false interruptions
during agent speech. It distinguishes meaningful user interruptions from irrelevant
filler sounds like "uh", "umm", "hmm", etc.

Key Features:
- Configurable filler word list
- Language-agnostic design
- Real-time filtering based on agent state
- Confidence threshold support
- Comprehensive logging for debugging
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Literal, Pattern

logger = logging.getLogger("filler_detector")
logger.setLevel(logging.DEBUG)


@dataclass
class FillerDetectionConfig:
    """Configuration for filler word detection.
    
    Attributes:
        ignored_words: List of filler words/phrases to ignore when agent is speaking.
        confidence_threshold: Minimum STT confidence (0-1) to process transcripts.
        case_sensitive: Whether to match filler words case-sensitively.
        whole_word_match: If True, only match complete words, not substrings.
        min_real_words: Minimum non-filler words required to register as valid speech.
        enabled: Master switch to enable/disable filler detection.
        log_all_detections: Log every filler detection for debugging.
    """
    ignored_words: list[str] = field(
        default_factory=lambda: [
            "uh", "um", "umm", "hmm", "hm", "ah", "eh", "er", "err",
            "haan", "haan", "haan ji", "han", "achha", "acha",  # Hindi/Urdu
            "うん", "ええと", "えーと",  # Japanese
            "嗯", "啊", "呃",  # Chinese
            "euh", "hein",  # French
            "äh", "ähm",  # German
            "э", "эм",  # Russian
            "esto", "pues",  # Spanish
        ]
    )
    confidence_threshold: float = 0.5
    case_sensitive: bool = False
    whole_word_match: bool = True
    min_real_words: int = 1
    enabled: bool = True
    log_all_detections: bool = True

    def __post_init__(self):
        """Normalize filler words based on configuration."""
        if not self.case_sensitive:
            self.ignored_words = [word.lower() for word in self.ignored_words]


@dataclass
class FillerDetectionResult:
    """Result of filler detection analysis.
    
    Attributes:
        is_filler_only: True if the transcript contains only filler words.
        original_text: The original transcript text.
        filtered_text: Transcript with filler words removed.
        detected_fillers: List of filler words found in transcript.
        real_word_count: Count of non-filler words.
        confidence: STT confidence score (if available).
        should_interrupt: Whether this should trigger an interruption.
        reason: Human-readable reason for the decision.
    """
    is_filler_only: bool
    original_text: str
    filtered_text: str
    detected_fillers: list[str]
    real_word_count: int
    confidence: float | None
    should_interrupt: bool
    reason: str
    timestamp: float = field(default_factory=time.time)


class FillerDetector:
    """Intelligent filler word detector for LiveKit Agents.
    
    This class analyzes transcripts in real-time to distinguish meaningful
    user interruptions from filler sounds, preventing false interruptions
    during agent speech.
    """
    
    def __init__(self, config: FillerDetectionConfig | None = None):
        """Initialize the filler detector.
        
        Args:
            config: Configuration for filler detection. Uses defaults if None.
        """
        self.config = config or FillerDetectionConfig()
        self._filler_patterns: list[Pattern] = []
        self._compile_patterns()
        
        # Statistics tracking
        self.stats = {
            "total_transcripts": 0,
            "filler_only_detections": 0,
            "valid_interruptions": 0,
            "ignored_while_agent_speaking": 0,
            "allowed_while_agent_quiet": 0,
        }
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient filler word matching."""
        self._filler_patterns = []
        for word in self.config.ignored_words:
            escaped = re.escape(word)
            if self.config.whole_word_match:
                # Match whole words only, with word boundaries
                pattern = rf'\b{escaped}\b'
            else:
                # Match anywhere in text
                pattern = escaped
            
            flags = 0 if self.config.case_sensitive else re.IGNORECASE
            self._filler_patterns.append(re.compile(pattern, flags))
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        text = text.strip()
        if not self.config.case_sensitive:
            text = text.lower()
        return text
    
    def _extract_words(self, text: str) -> list[str]:
        """Extract words from text, handling multiple languages."""
        # Handle CJK characters (Chinese, Japanese, Korean)
        # and standard word boundaries
        text = self._normalize_text(text)
        
        # Split on whitespace and common punctuation
        words = re.findall(r'\S+', text)
        return words
    
    def _identify_fillers(self, text: str) -> list[str]:
        """Identify all filler words in the text.
        
        Args:
            text: The text to analyze.
            
        Returns:
            List of filler words found.
        """
        text = self._normalize_text(text)
        detected = []
        
        for pattern in self._filler_patterns:
            matches = pattern.findall(text)
            detected.extend(matches)
        
        return detected
    
    def _remove_fillers(self, text: str) -> str:
        """Remove filler words from text.
        
        Args:
            text: The text to filter.
            
        Returns:
            Text with filler words removed.
        """
        result = text
        for pattern in self._filler_patterns:
            result = pattern.sub('', result)
        
        # Clean up extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        return result
    
    def analyze_transcript(
        self,
        text: str,
        confidence: float | None = None,
        agent_state: str | None = None,
    ) -> FillerDetectionResult:
        """Analyze a transcript to determine if it's filler-only.
        
        Args:
            text: The transcript text to analyze.
            confidence: STT confidence score (0-1), if available.
            agent_state: Current agent state (speaking/listening/etc).
            
        Returns:
            FillerDetectionResult with analysis details.
        """
        self.stats["total_transcripts"] += 1
        
        if not self.config.enabled:
            return FillerDetectionResult(
                is_filler_only=False,
                original_text=text,
                filtered_text=text,
                detected_fillers=[],
                real_word_count=len(self._extract_words(text)),
                confidence=confidence,
                should_interrupt=True,
                reason="Filler detection disabled",
            )
        
        # Check confidence threshold
        if confidence is not None and confidence < self.config.confidence_threshold:
            return FillerDetectionResult(
                is_filler_only=False,
                original_text=text,
                filtered_text=text,
                detected_fillers=[],
                real_word_count=0,
                confidence=confidence,
                should_interrupt=False,
                reason=f"Confidence {confidence:.2f} below threshold {self.config.confidence_threshold}",
            )
        
        # Identify fillers
        detected_fillers = self._identify_fillers(text)
        filtered_text = self._remove_fillers(text)
        
        # Count real words (words remaining after filler removal)
        real_words = self._extract_words(filtered_text)
        real_word_count = len(real_words)
        
        # Determine if this is filler-only
        is_filler_only = real_word_count < self.config.min_real_words
        
        # Decide whether to interrupt based on agent state
        should_interrupt = True
        reason = ""
        
        if is_filler_only:
            self.stats["filler_only_detections"] += 1
            
            if agent_state == "speaking":
                # Agent is speaking - ignore fillers
                should_interrupt = False
                self.stats["ignored_while_agent_speaking"] += 1
                reason = f"Filler-only utterance ignored (agent speaking): detected {detected_fillers}"
            else:
                # Agent is quiet - register as valid speech
                should_interrupt = True
                self.stats["allowed_while_agent_quiet"] += 1
                reason = f"Filler-only utterance registered (agent quiet): detected {detected_fillers}"
        else:
            # Contains real words - always interrupt
            self.stats["valid_interruptions"] += 1
            should_interrupt = True
            reason = f"Valid interruption with {real_word_count} real word(s): '{filtered_text}'"
        
        result = FillerDetectionResult(
            is_filler_only=is_filler_only,
            original_text=text,
            filtered_text=filtered_text,
            detected_fillers=detected_fillers,
            real_word_count=real_word_count,
            confidence=confidence,
            should_interrupt=should_interrupt,
            reason=reason,
        )
        
        # Log if configured
        if self.config.log_all_detections or (is_filler_only and agent_state == "speaking"):
            logger.info(
                f"Filler detection: {result.reason}",
                extra={
                    "original": text,
                    "filtered": filtered_text,
                    "fillers": detected_fillers,
                    "agent_state": agent_state,
                    "should_interrupt": should_interrupt,
                    "confidence": confidence,
                },
            )
        
        return result
    
    def update_ignored_words(self, words: list[str]) -> None:
        """Dynamically update the list of ignored filler words.
        
        Args:
            words: New list of filler words to ignore.
        """
        self.config.ignored_words = words
        if not self.config.case_sensitive:
            self.config.ignored_words = [word.lower() for word in words]
        self._compile_patterns()
        logger.info(f"Updated ignored words: {self.config.ignored_words}")
    
    def add_ignored_words(self, words: list[str]) -> None:
        """Add words to the ignored list without replacing existing ones.
        
        Args:
            words: Words to add to the ignored list.
        """
        for word in words:
            normalized = word if self.config.case_sensitive else word.lower()
            if normalized not in self.config.ignored_words:
                self.config.ignored_words.append(normalized)
        self._compile_patterns()
        logger.info(f"Added ignored words. Total: {len(self.config.ignored_words)}")
    
    def get_stats(self) -> dict:
        """Get detection statistics.
        
        Returns:
            Dictionary of statistics.
        """
        return {
            **self.stats,
            "ignored_words_count": len(self.config.ignored_words),
            "config": {
                "confidence_threshold": self.config.confidence_threshold,
                "min_real_words": self.config.min_real_words,
                "enabled": self.config.enabled,
            },
        }


def split_words(text: str, split_character: bool = False) -> list[str]:
    """Split text into words, optionally splitting on character boundaries.
    
    This is a helper function that mimics the behavior expected by LiveKit's
    word counting logic.
    
    Args:
        text: Text to split.
        split_character: If True, split CJK characters as individual words.
        
    Returns:
        List of words.
    """
    if not text:
        return []
    
    if split_character:
        # Split on whitespace and treat each character as potential word
        # This is for CJK language support
        words = []
        for part in text.split():
            if any('\u4e00' <= c <= '\u9fff' or  # CJK Unified Ideographs
                   '\u3040' <= c <= '\u309f' or  # Hiragana
                   '\u30a0' <= c <= '\u30ff' or  # Katakana
                   '\uac00' <= c <= '\ud7af'     # Hangul
                   for c in part):
                # Treat each character as a word for CJK
                words.extend(list(part))
            else:
                words.append(part)
        return words
    else:
        return text.split()

