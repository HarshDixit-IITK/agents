"""
Filler Detection Extension for LiveKit Agents

This package provides intelligent filler word detection to prevent false
interruptions during agent speech.

Quick Start:
    ```python
    from livekit.agents.voice import Agent
    from filler_detection import IntegratedFillerSession, FillerDetectionConfig
    
    # Configure filler detection
    config = FillerDetectionConfig(
        ignored_words=["uh", "um", "hmm", "haan"],
        confidence_threshold=0.5,
    )
    
    # Create session with filler detection
    session = IntegratedFillerSession(
        filler_config=config,
        stt="deepgram",
        vad="silero",
        llm="openai",
        tts="elevenlabs",
    )
    
    # Use normally
    await session.connect(room)
    agent = Agent(instructions="You are a helpful assistant...")
    await session.start(agent)
    ```

Main Components:
- FillerDetector: Core filler detection logic
- FillerDetectionConfig: Configuration for filler detection
- IntegratedFillerSession: Session with filler detection integrated
- FillerAwareRecognitionHooks: Custom hooks that filter interruptions
"""

from .filler_detector import (
    FillerDetectionConfig,
    FillerDetectionResult,
    FillerDetector,
)
from .integration import IntegratedFillerSession

__all__ = [
    "FillerDetectionConfig",
    "FillerDetectionResult",
    "FillerDetector",
    "IntegratedFillerSession",
]

__version__ = "1.0.0"

