"""
Integration layer for filler-aware agents.

This module provides the glue code to integrate filler detection into LiveKit
agents without modifying the SDK. It uses careful wrapping and monkeypatching
to intercept the recognition hooks at the right level.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypeVar

from livekit.agents import llm, stt, tts, vad
from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.agents.voice import Agent, AgentSession

# Import type hints if available, otherwise use Any
try:
    from livekit.agents.voice import TurnDetectionMode  # type: ignore
except ImportError:
    TurnDetectionMode = Any  # type: ignore

# MCP is optional
try:
    from livekit.agents import mcp
except ImportError:
    mcp = None  # type: ignore

# Use absolute imports when running as script, relative when imported as package
try:
    from .filler_aware_hooks import FillerAwareRecognitionHooks
    from .filler_detector import FillerDetectionConfig, FillerDetector
except ImportError:
    from filler_aware_hooks import FillerAwareRecognitionHooks
    from filler_detector import FillerDetectionConfig, FillerDetector

logger = logging.getLogger("filler_integration")
logger.setLevel(logging.DEBUG)

Userdata_T = TypeVar("Userdata_T")


class IntegratedFillerSession(AgentSession[Userdata_T]):
    """Enhanced AgentSession with deep filler detection integration.
    
    This session integrates filler detection at the recognition hooks level,
    ensuring that filler-only utterances don't trigger false interruptions
    when the agent is speaking.
    
    Usage:
        ```python
        from integration import IntegratedFillerSession, FillerDetectionConfig
        
        config = FillerDetectionConfig(
            ignored_words=["uh", "um", "hmm", "haan"],
            confidence_threshold=0.5,
        )
        
        session = IntegratedFillerSession(
            filler_config=config,
            stt="deepgram",
            vad="silero",
            llm="openai",
            tts="elevenlabs",
        )
        
        await session.connect(room)
        agent = Agent(instructions="You are a helpful assistant...")
        await session.start(agent)
        ```
    """
    
    def __init__(
        self,
        *,
        filler_config: FillerDetectionConfig | None = None,
        turn_detection: NotGivenOr[Any] = NOT_GIVEN,
        stt: NotGivenOr[Any] = NOT_GIVEN,
        vad: NotGivenOr[Any] = NOT_GIVEN,
        llm: NotGivenOr[Any] = NOT_GIVEN,
        tts: NotGivenOr[Any] = NOT_GIVEN,
        mcp_servers: NotGivenOr[list] = NOT_GIVEN,
        userdata: NotGivenOr[Userdata_T] = NOT_GIVEN,
        allow_interruptions: bool = True,
        discard_audio_if_uninterruptible: bool = True,
        min_interruption_duration: float = 0.5,
        min_interruption_words: int = 0,
        min_endpointing_delay: float = 0.5,
        max_endpointing_delay: float = 3.0,
        max_tool_steps: int = 3,
        video_sampler: NotGivenOr[Any] = NOT_GIVEN,
        user_away_timeout: float | None = 15.0,
        false_interruption_timeout: float | None = 2.0,
        resume_false_interruption: bool = True,
        min_consecutive_speech_delay: float = 0.0,
        use_tts_aligned_transcript: NotGivenOr[bool] = NOT_GIVEN,
        tts_text_transforms: NotGivenOr[Any] = NOT_GIVEN,
        preemptive_generation: bool = False,
        conn_options: NotGivenOr[Any] = NOT_GIVEN,
        loop: asyncio.AbstractEventLoop | None = None,
        agent_false_interruption_timeout: NotGivenOr[float | None] = NOT_GIVEN,
    ) -> None:
        """Initialize integrated filler-aware session.
        
        Args:
            filler_config: Filler detection configuration.
            All other args: See AgentSession documentation.
        """
        super().__init__(
            turn_detection=turn_detection,
            stt=stt,
            vad=vad,
            llm=llm,
            tts=tts,
            mcp_servers=mcp_servers,
            userdata=userdata,
            allow_interruptions=allow_interruptions,
            discard_audio_if_uninterruptible=discard_audio_if_uninterruptible,
            min_interruption_duration=min_interruption_duration,
            min_interruption_words=min_interruption_words,
            min_endpointing_delay=min_endpointing_delay,
            max_endpointing_delay=max_endpointing_delay,
            max_tool_steps=max_tool_steps,
            video_sampler=video_sampler,
            user_away_timeout=user_away_timeout,
            false_interruption_timeout=false_interruption_timeout,
            resume_false_interruption=resume_false_interruption,
            min_consecutive_speech_delay=min_consecutive_speech_delay,
            use_tts_aligned_transcript=use_tts_aligned_transcript,
            tts_text_transforms=tts_text_transforms,
            preemptive_generation=preemptive_generation,
            conn_options=conn_options,
            loop=loop,
            agent_false_interruption_timeout=agent_false_interruption_timeout,
        )
        
        # Initialize filler detector
        self._filler_detector = FillerDetector(filler_config)
        self._filler_hooks_wrapper: FillerAwareRecognitionHooks | None = None
        
        logger.info(
            f"IntegratedFillerSession initialized with {len(self._filler_detector.config.ignored_words)} ignored words"
        )
    
    async def start(self, agent: Agent | None = None, room: Any = None, **kwargs) -> None:
        """Start the agent session with filler detection integration.
        
        This method wraps the parent start() method and installs the filler
        detection hooks after the agent activity is created.
        
        Args:
            agent: The agent to start. If None, uses a default agent.
            room: The room to connect to (if not already connected).
            **kwargs: Additional arguments passed to parent start().
        """
        # Call parent start first
        if room is not None:
            await super().start(agent=agent, room=room, **kwargs)
        else:
            await super().start(agent=agent, **kwargs)
        
        # Schedule hook injection to happen after event loop processes
        import asyncio
        asyncio.create_task(self._inject_hooks_delayed())
    
    async def _inject_hooks_delayed(self):
        """Inject hooks after a short delay to ensure agent activity is created."""
        import asyncio
        
        # Wait for agent activity to be created
        for attempt in range(20):  # Try for 1 second total
            await asyncio.sleep(0.1)
            
            # Try to access agent activity
            if hasattr(self, '_agent_activity') and self._agent_activity is not None:
                activity = self._agent_activity
                
                # Check if it has an audio recognition component
                if hasattr(activity, '_audio_recognition') and activity._audio_recognition is not None:
                    audio_rec = activity._audio_recognition
                    
                    # Store original hooks
                    original_hooks = audio_rec._hooks
                    
                    # Create wrapped hooks
                    self._filler_hooks_wrapper = FillerAwareRecognitionHooks(
                        wrapped_hooks=original_hooks,
                        filler_detector=self._filler_detector,
                        session=self,
                    )
                    
                    # Replace with our wrapped hooks
                    audio_rec._hooks = self._filler_hooks_wrapper
                    
                    logger.info("✅ Filler detection hooks successfully integrated!")
                    return
        
        logger.warning(
            "Could not integrate filler detection hooks - agent activity not found after 1s"
        )
    
    @property
    def filler_detector(self) -> FillerDetector:
        """Access the filler detector instance."""
        return self._filler_detector
    
    def get_filler_stats(self) -> dict:
        """Get comprehensive filler detection statistics."""
        stats = {
            "detector": self._filler_detector.get_stats(),
        }
        
        if self._filler_hooks_wrapper:
            stats["hooks"] = self._filler_hooks_wrapper.get_stats()
        
        return stats
    
    def update_filler_words(self, words: list[str]) -> None:
        """Update filler words at runtime."""
        self._filler_detector.update_ignored_words(words)
    
    def add_filler_words(self, words: list[str]) -> None:
        """Add filler words at runtime."""
        self._filler_detector.add_ignored_words(words)

