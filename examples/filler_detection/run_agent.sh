#!/bin/bash

# ⚠️  IMPORTANT: Replace these placeholder values with your actual API keys!
# Never commit this file with real API keys to a public repository.

# LiveKit credentials - ONLY credentials needed!
# Using LiveKit's built-in STT, TTS, and LLM
export LIVEKIT_URL=wss://salescode-9jdd6emu.livekit.cloud
export LIVEKIT_API_KEY=APIBFVmpwHACdqN
export LIVEKIT_API_SECRET=iaPyTzkqfoYzwItww2UH5HEnLhq0fBQICqkQU5gPeTuA

# No external API keys needed - LiveKit provides everything!

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        🎙️  FILLER-AWARE VOICE AGENT STARTING...             ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ LiveKit URL: $LIVEKIT_URL"
echo "✅ All API keys configured"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting agent worker..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the agent in dev mode (automatically connects to rooms)
python3 example_agent.py dev

