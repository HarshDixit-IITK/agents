#!/usr/bin/env python3
"""
Generate a LiveKit room token for testing the agent.

This creates a token that lets you join a room to speak with the agent.
"""

import os
import sys
from livekit import api

# Your LiveKit credentials
LIVEKIT_URL="wss://salescode-9jdd6emu.livekit.cloud"
LIVEKIT_API_KEY="APIBFVmpwHACdqN"
LIVEKIT_API_SECRET="iaPyTzkqfoYzwItww2UH5HEnLhq0fBQICqkQU5gPeTuA"

def generate_token(room_name: str = "filler-test-room", participant_name: str = "test-user"):
    """Generate a token for joining a room."""
    
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(participant_name).with_name(participant_name)
    token.with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )
    
    return token.to_jwt()

if __name__ == "__main__":
    room_name = sys.argv[1] if len(sys.argv) > 1 else "filler-test-room"
    participant_name = sys.argv[2] if len(sys.argv) > 2 else "test-user"
    
    token = generate_token(room_name, participant_name)
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║           🎫 LIVEKIT ROOM TOKEN GENERATED                    ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"Room Name: {room_name}")
    print(f"Participant: {participant_name}")
    print()
    print("Your Token:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(token)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("🎯 How to use:")
    print()
    print("Option 1: LiveKit Playground (Easiest)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. Open: https://agents-playground.livekit.io/")
    print("2. Click 'Connect to your server'")
    print("3. Paste this token in the 'Token' field")
    print("4. Click Connect")
    print("5. Allow microphone and start speaking!")
    print()
    print("Option 2: LiveKit Meet")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"1. Open: https://meet.livekit.io/custom?url={LIVEKIT_URL}&token={token}")
    print("2. Click 'Join Room'")
    print("3. Allow microphone and start speaking!")
    print()
    print("The agent will automatically join the same room! 🤖")
    print()

