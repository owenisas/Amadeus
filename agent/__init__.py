"""
Amadeus Agent Module

Available Agents:
- ActionAgent: UI tree + vision hybrid agent (recommended for most tasks)
- VisionAgent: Pure vision-based agent (no UI tree, coordinate-only interactions)
"""

from agent.main_agent import ActionAgent
from agent.vision_agent import VisionAgent

__all__ = ['ActionAgent', 'VisionAgent']
