#!/usr/bin/env python3
"""
Amadeus - AI-Powered Mobile Automation

Usage:
    python main.py                        # Run with default prompt
    python main.py "Your task here"       # Run with custom prompt
    python main.py --audio                # Run with voice input/output
    python main.py --vision               # Run in pure vision mode (no UI tree)
    python main.py --interactive          # Run with user interaction enabled
    
Examples:
    python main.py "Open Chrome and search for weather"
    python main.py --vision "Tap on the Settings icon"
    python main.py --audio --interactive "Help me navigate"
"""

import sys
import json
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runner import Runner
from config import PROJECT_ROOT


def print_help():
    """Print usage help."""
    print(__doc__)
    print("\nModes:")
    print("  Default (ActionAgent): Uses UI element tree + vision for precise interactions")
    print("  --vision (VisionAgent): Pure vision mode, uses only screenshots and coordinates")
    print("\nOptions:")
    print("  --audio        Enable voice input/output")
    print("  --interactive  Enable user interaction during task execution")
    print("  --infinite     Run continuously without auto-ending sessions")
    print("  --help, -h     Show this help message")


def main():
    # Check for help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return
    
    # Load filters
    filter_path = os.path.join(PROJECT_ROOT, "filter.json")
    if os.path.exists(filter_path):
        with open(filter_path, "r") as fp:
            filters = json.load(fp)
    else:
        filters = None

    # Parse command line arguments
    audio_mode = "--audio" in sys.argv
    vision_mode = "--vision" in sys.argv
    interactive_mode = "--interactive" in sys.argv
    infinite_mode = "--infinite" in sys.argv
    
    # Get non-flag arguments for the prompt
    flag_args = {"--audio", "--vision", "--interactive", "--infinite", "--help", "-h"}
    args = [arg for arg in sys.argv[1:] if arg not in flag_args]

    # Get prompt from command line or use default
    if args:
        prompt = " ".join(args)
    else:
        # Default test prompt
        prompt = "Open the settings app"

    print("=" * 50)
    print("AMADEUS - AI Mobile Automation")
    print("=" * 50)
    print(f"Prompt: {prompt}")
    print(f"Mode: {'Vision (pure)' if vision_mode else 'Action (UI tree + vision)'}")
    print(f"Audio: {'enabled' if audio_mode else 'disabled'}")
    print(f"Interactive: {'enabled' if interactive_mode else 'disabled'}")
    print("=" * 50)

    # Create and run the runner
    runner = Runner(
        filters=filters,
        audio=audio_mode,
        vision_mode=vision_mode,
        interactive=interactive_mode,
        infinite=infinite_mode
    )
    runner.run(prompt)


if __name__ == "__main__":
    main()
