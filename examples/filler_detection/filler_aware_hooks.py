"""
Filler-Aware Recognition Hooks for LiveKit Agents

This module provides custom recognition hooks that intercept VAD and STT events
to implement intelligent filler detection. This is where the core interruption
filtering logic is implemented.

The hooks integrate with LiveKit's internal agent activity system without
modifying the SDK itself.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from livekit.agents import stt, vad
from livekit.agents.voice.audio_recognition import RecognitionHooks

# Use absolute imports when running as script, relative when imported as package
try:
    from .filler_detector import FillerDetector, split_words
except ImportError:
    from filler_detector import FillerDetector, split_words

if TYPE_CHECKING:
    from livekit.agents.voice import AgentSession

logger = logging.getLogger("filler_aware_hooks")
logger.setLevel(logging.DEBUG)


class FillerAwareRecognitionHooks(RecognitionHooks):
    """Custom recognition hooks with filler detection.
    
    This class wraps the standard recognition hooks and adds filler detection
    logic to prevent false interruptions. It intercepts VAD and STT events
    before they trigger interruptions.
    """
    
    def __init__(
        self,
        wrapped_hooks: RecognitionHooks,
        filler_detector: FillerDetector,
        session: AgentSession,
    ):
        """Initialize filler-aware hooks.
        
        Args:
            wrapped_hooks: The original recognition hooks to wrap.
            filler_detector: The filler detector to use for filtering.
            session: The agent session for state access.
        """
        self._wrapped = wrapped_hooks
        self._filler_detector = filler_detector
        self._session = session
        
        # Track the current user transcript being built
        self._current_transcript = ""
        self._last_interim_time = 0.0
        
        # Statistics
        self._vad_events_processed = 0
        self._vad_events_blocked = 0
        self._stt_events_processed = 0
        self._stt_events_blocked = 0
    
    def on_start_of_speech(self, ev: vad.VADEvent | None) -> None:
        """Handle start of speech VAD event.
        
        We always pass this through - it's important to detect when user starts speaking.
        """
        logger.debug("Start of speech detected")
        self._current_transcript = ""
        self._wrapped.on_start_of_speech(ev)
    
    def on_end_of_speech(self, ev: vad.VADEvent | None) -> None:
        """Handle end of speech VAD event.
        
        We always pass this through - it marks the end of user utterance.
        """
        logger.debug(
            f"End of speech detected, final transcript: '{self._current_transcript}'"
        )
        self._wrapped.on_end_of_speech(ev)
        # Reset transcript for next utterance
        self._current_transcript = ""
    
    def on_vad_inference_done(self, ev: vad.VADEvent) -> None:
        """Handle VAD inference done event.
        
        This is where interruptions are triggered by VAD. We check if we have
        enough transcript context to determine if this is a filler-only utterance.
        
        If we have STT enabled and have received interim transcripts, we use
        those to filter. Otherwise, we rely on speech duration thresholds.
        """
        self._vad_events_processed += 1
        
        # If we have interim transcript, use it for filler detection
        if self._current_transcript:
            result = self._filler_detector.analyze_transcript(
                text=self._current_transcript,
                confidence=None,
                agent_state=self._session.agent_state,
            )
            
            if result.is_filler_only and self._session.agent_state == "speaking":
                # Block this VAD event from causing an interruption
                self._vad_events_blocked += 1
                logger.info(
                    f"Blocked VAD interruption (filler-only): '{self._current_transcript}'",
                    extra={
                        "transcript": self._current_transcript,
                        "agent_state": self._session.agent_state,
                        "speech_duration": ev.speech_duration,
                    },
                )
                return
        
        # Pass through to original handler
        logger.debug(
            f"Allowing VAD interruption",
            extra={
                "transcript": self._current_transcript,
                "agent_state": self._session.agent_state,
                "speech_duration": ev.speech_duration,
            },
        )
        self._wrapped.on_vad_inference_done(ev)
    
    def on_interim_transcript(
        self, ev: stt.SpeechEvent, *, speaking: bool | None
    ) -> None:
        """Handle interim transcript from STT.
        
        This is where we intercept transcripts and apply filler detection
        before they trigger interruptions.
        
        The key logic:
        - Update our current transcript
        - Analyze for filler words
        - Block the event if it's filler-only and agent is speaking
        - Pass through otherwise
        """
        self._stt_events_processed += 1
        
        if not ev.alternatives or not ev.alternatives[0].text:
            # No text, pass through
            self._wrapped.on_interim_transcript(ev, speaking=speaking)
            return
        
        transcript = ev.alternatives[0].text
        self._current_transcript = transcript
        self._last_interim_time = time.time()
        
        # Analyze the transcript
        result = self._filler_detector.analyze_transcript(
            text=transcript,
            confidence=ev.alternatives[0].confidence if ev.alternatives else None,
            agent_state=self._session.agent_state,
        )
        
        # Determine if we should allow this to trigger an interruption
        should_block = (
            result.is_filler_only 
            and self._session.agent_state == "speaking"
            and not result.should_interrupt
        )
        
        if should_block:
            self._stt_events_blocked += 1
            logger.info(
                f"Blocked STT interruption (filler-only): '{transcript}'",
                extra={
                    "original": transcript,
                    "filtered": result.filtered_text,
                    "fillers": result.detected_fillers,
                    "agent_state": self._session.agent_state,
                    "speaking": speaking,
                },
            )
            
            # Still pass through for transcription display, but modify to prevent interruption
            # We do this by calling the wrapped handler but ensuring the text won't trigger
            # the min_interruption_words check
            # Actually, we should just not call the wrapped handler at all for interim
            # transcripts that are filler-only when agent is speaking
            return
        
        # Pass through to original handler
        logger.debug(
            f"Allowing STT interruption: '{transcript}'",
            extra={
                "real_words": result.real_word_count,
                "agent_state": self._session.agent_state,
                "speaking": speaking,
            },
        )
        self._wrapped.on_interim_transcript(ev, speaking=speaking)
    
    def on_final_transcript(self, ev: stt.SpeechEvent) -> None:
        """Handle final transcript from STT.
        
        Final transcripts are always passed through - they're needed for
        the conversation context and shouldn't trigger false interruptions
        since they come after the user has finished speaking.
        """
        if ev.alternatives and ev.alternatives[0].text:
            transcript = ev.alternatives[0].text
            logger.debug(f"Final transcript: '{transcript}'")
        
        self._wrapped.on_final_transcript(ev)
    
    def retrieve_chat_ctx(self):
        """Retrieve chat context from wrapped hooks."""
        return self._wrapped.retrieve_chat_ctx()
    
    def on_preemptive_generation(self, info) -> None:
        """Handle preemptive generation if supported."""
        if hasattr(self._wrapped, 'on_preemptive_generation'):
            self._wrapped.on_preemptive_generation(info)
    
    def get_stats(self) -> dict:
        """Get statistics about filtered events.
        
        Returns:
            Dictionary with event processing statistics.
        """
        return {
            "vad_events": {
                "processed": self._vad_events_processed,
                "blocked": self._vad_events_blocked,
                "pass_through_rate": (
                    1 - (self._vad_events_blocked / self._vad_events_processed)
                    if self._vad_events_processed > 0
                    else 1.0
                ),
            },
            "stt_events": {
                "processed": self._stt_events_processed,
                "blocked": self._stt_events_blocked,
                "pass_through_rate": (
                    1 - (self._stt_events_blocked / self._stt_events_processed)
                    if self._stt_events_processed > 0
                    else 1.0
                ),
            },
            "filler_detector": self._filler_detector.get_stats(),
        }

