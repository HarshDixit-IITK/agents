"""
Example Filler-Aware Agent

This example demonstrates how to use the filler detection extension with
LiveKit Agents. It creates a voice agent that intelligently handles filler
words to prevent false interruptions.

Run this example:
    python example_agent.py --url <livekit-url> --token <token>

Or use environment variables:
    export LIVEKIT_URL=wss://your-instance.livekit.cloud
    export LIVEKIT_API_KEY=your-api-key
    export LIVEKIT_API_SECRET=your-api-secret
    python example_agent.py
"""

import asyncio
import logging
import os
from typing import Optional

from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent

# Import from local modules
from filler_detector import FillerDetectionConfig
from integration import IntegratedFillerSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("filler_example")


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the agent.
    
    This function is called when a participant joins a room.
    """
    logger.info(f"📞 JOB ACCEPTED - Connecting to room: {ctx.room.name}")
    
    # Configure filler detection with a comprehensive list
    filler_config = FillerDetectionConfig(
        ignored_words=[
            # English fillers
            "uh", "um", "umm", "hmm", "hm", "ah", "eh", "er", "err",
            "uh-huh", "mm-hmm", "mhm", "yeah", "yep", "yup",
            # Hindi/Urdu fillers
            "haan", "han", "achha", "acha", "theek", "thik",
            # Spanish fillers
            "eh", "este", "pues", "bueno",
            # French fillers
            "euh", "hein", "ben", "quoi",
            # German fillers
            "äh", "ähm", "also",
            # Japanese fillers
            "うん", "ええと", "えーと", "あの", "その",
            # Chinese fillers
            "嗯", "啊", "呃", "那个",
        ],
        confidence_threshold=0.5,
        min_real_words=1,
        case_sensitive=False,
        whole_word_match=True,
        enabled=True,
        log_all_detections=True,
    )
    
    # Create the filler-aware session
    # Using LiveKit's inference service - models resolved through LiveKit Cloud
    session = IntegratedFillerSession(
        filler_config=filler_config,
        # Use string-based model identifiers - LiveKit resolves these
        stt="assemblyai/universal-streaming:en",  # LiveKit-managed AssemblyAI
        llm="openai/gpt-4.1-mini",  # LiveKit-managed OpenAI
        tts="cartesia/sonic-2",  # LiveKit-managed Cartesia (most compatible)
        allow_interruptions=True,
        min_interruption_duration=0.5,  # 500ms minimum speech to interrupt
        min_interruption_words=0,  # Handled by filler detection instead
        false_interruption_timeout=2.0,  # Resume after 2s if false interruption
        resume_false_interruption=True,
    )
    
    # Set up event handlers BEFORE starting
    @session.on("user_input_transcribed")
    def on_user_transcript(event):
        """Log user transcriptions for debugging."""
        logger.info(
            f"User transcript ({'final' if event.is_final else 'interim'}): '{event.transcript}'"
        )
    
    @session.on("agent_state_changed")
    def on_agent_state(event):
        """Log agent state changes."""
        logger.info(f"Agent state: {event.old_state} -> {event.new_state}")
    
    @session.on("agent_false_interruption")
    def on_false_interruption(event):
        """Log false interruptions."""
        logger.warning(
            f"False interruption detected (resumed={event.resumed})"
        )
    
    # Create the agent with instructions
    agent = Agent(
        instructions="""
        You are a helpful and friendly voice assistant. 
        
        Speak naturally and conversationally. If users make filler sounds like
        "uh", "um", or "hmm" while you're speaking, continue your response
        without interruption - these are natural listening sounds, not real
        interruptions.
        
        However, if users say actual words or phrases like "wait", "stop",
        "hold on", or "no", immediately stop and listen to their input.
        
        Keep your responses concise and natural.
        """,
    )
    
    # Start the agent (this connects to room and starts everything)
    logger.info("Starting agent...")
    await session.start(agent=agent, room=ctx.room)
    
    # Wait for the session to end
    await asyncio.sleep(1)  # Give hooks time to integrate
    
    # Log initial statistics
    logger.info("Agent started successfully!")
    logger.info(f"Monitoring for filler words: {filler_config.ignored_words[:10]}...")
    
    # The session will run until the room is closed or participant leaves
    # We can periodically log statistics
    try:
        while session.agent_state != "initializing":
            await asyncio.sleep(30)  # Log stats every 30 seconds
            
            stats = session.get_filler_stats()
            logger.info(
                "Filler detection statistics:",
                extra=stats,
            )
            
            # Example: dynamically add filler words based on conversation
            # session.add_filler_words(["okay", "got it"])
            
    except asyncio.CancelledError:
        logger.info("Session cancelled, shutting down...")
        stats = session.get_filler_stats()
        logger.info(
            "Final filler detection statistics:",
            extra=stats,
        )
        raise


if __name__ == "__main__":
    # Run the agent worker
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

