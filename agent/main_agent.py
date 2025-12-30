"""
Main Action Agent for Amadeus - handles UI automation tasks on Android devices.
"""

import os
import sys
import base64
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import Client
from environment.Android import Android
from config import APIConfig, ModelConfig, DataConfig
from openai import OpenAI


def image_bytes_to_data_url(image_bytes, mime_type="image/png"):
    """Convert image bytes to a data URL for vision models."""
    base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded}"


def tools_definition() -> list:
    """Load tools definition from JSON file."""
    import json
    tools_path = DataConfig.get_tools_definition_path()
    with open(tools_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Improved system prompt with structured reasoning
SYSTEM_PROMPT = """You are Amadeus, an intelligent Android device automation assistant. You interact with a real Android device through a set of tools that allow you to see, tap, type, scroll, and navigate.

## Your Capabilities
- **See**: Get UI elements via `get_screen_elements` or visual analysis via `analyze_screen`
- **Tap**: Click elements by index (`tap`) or coordinates (`tap_coordinates`)
- **Type**: Enter text into fields with `type_text`
- **Scroll**: Navigate content with directional `scroll` or precise `swipe`
- **Navigate**: Use `press_key` for back/home/enter, `open_app` to launch apps

## Workflow for Every Task

### Step 1: Observe
Before any action, ALWAYS call `get_screen_elements` to understand what's on screen. This gives you:
- Element indexes for tapping
- Text content to identify buttons/labels
- Class types to understand element purposes

Use `analyze_screen` when you need to understand:
- Visual layouts not captured in UI tree
- Images, icons, or colors
- Overall screen context

### Step 2: Plan
Think through the logical steps needed:
- What app/screen do I need to be on?
- What elements do I need to interact with?
- What's the sequence of actions?

### Step 3: Act
Execute ONE action at a time:
- After each action, the screen may change
- Always re-check elements after significant actions
- Don't assume the screen state - verify it

### Step 4: Verify
After completing actions:
- Confirm the expected result occurred
- If something failed, try alternative approaches
- Report clear results to the user

## Important Guidelines

1. **Element Freshness**: The element list becomes stale after ANY tap, scroll, or navigation. Always call `get_screen_elements` again after such actions.

2. **Scroll Strategy**: 
   - Use `scroll(direction="down")` to reveal content below
   - Use `scroll(direction="up")` to reveal content above
   - Use `amount` parameter: "small", "medium", "large", or "full_page"

3. **Text Input**:
   - First tap the text field (get its index, then tap)
   - Then use `type_text` with the text
   - Use `submit=true` if you need to press Enter after

4. **Error Recovery**:
   - If an element isn't found, try scrolling to find it
   - If an action fails, try an alternative approach
   - Never repeat the exact same failed action

5. **App Navigation**:
   - Use `open_app` with common names ("Chrome", "YouTube") or package names
   - Use `press_key("back")` to go back one screen
   - Use `press_key("home")` to return to home screen

## Response Format
- Explain your reasoning briefly before each action
- Report what you observed and what you're doing
- Provide clear, direct answers when the task is complete
- If you cannot complete a task, explain why clearly

Remember: You control a REAL device. Be precise, be careful, and always verify your actions succeeded."""


class ActionAgent:
    """
    AI-powered agent for automating Android device interactions.
    Uses vision and UI element analysis to understand screens and execute tasks.
    """
    
    def __init__(
        self, 
        message: str, 
        on_new_message: callable = None, 
        multi_agent: bool = False, 
        infinite: bool = False,
        filters=None, 
        interactive: bool = False, 
        audio: bool = False
    ):
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "I'm ready to help you with your Android device. What would you like me to do?"},
            {"role": "user", "content": message}
        ]
        
        self.env = Android()
        self.filters = filters
        
        # Build tools map with new function names
        self.tools_map = {
            # Screen analysis
            "get_screen_elements": self._get_screen_elements,
            "analyze_screen": self._analyze_screen,
            "get_device_info": self.env.get_device_info,
            
            # Tap actions
            "tap": self.env.tap,
            "tap_coordinates": self.env.tap_coordinates,
            "double_tap": self.env.double_tap,
            "long_press": self.env.long_press,
            
            # Text input
            "type_text": self.env.type_text,
            
            # Scroll/Swipe
            "scroll": self.env.scroll,
            "swipe": self.env.swipe,
            
            # Navigation
            "press_key": self.env.press_key,
            "open_app": self.env.open_app,
            "get_installed_apps": self.env.get_installed_apps,
            
            # Utility
            "wait": self.env.wait,
        }
        
        self.tool_definition = tools_definition()

        # Initialize the client
        self.client = Client(
            model=ModelConfig.get_chat_model(),
            base=APIConfig.get_base_url(),
            tools_map=self.tools_map,
            tools_definition=self.tool_definition,
            messages=self.messages,
            on_new_message=on_new_message,
            api_key=APIConfig.get_api_key()
        )
        
        self.task = True
        self.audio = audio
        
        # Add optional capabilities
        self._setup_optional_tools(multi_agent, infinite, interactive)
    
    def _setup_optional_tools(self, multi_agent: bool, infinite: bool, interactive: bool):
        """Setup optional tools based on configuration."""
        if multi_agent:
            from agent.information_agent import call_agent
            self.tools_map["call_agent"] = call_agent
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "call_agent",
                    "description": "Call an information agent to answer questions or gather knowledge. Use this when you need factual information to complete a task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The question or information request"
                            }
                        },
                        "required": ["message"]
                    }
                }
            })
        
        if not infinite:
            self.tools_map["end_session"] = self.done
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "end_session",
                    "description": "End the current session when the task is fully complete and you have provided the final answer/result to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            })
        
        if interactive:
            self.tools_map["ask_user"] = self._user_interaction
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask the user for input when you need clarification, a choice, or additional information to proceed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question to ask the user"
                            }
                        },
                        "required": ["question"]
                    }
                }
            })

    def _get_screen_elements(self, include_all: bool = False):
        """Get screen elements with optional filtering."""
        return self.env.get_screen_elements(filters=self.filters, include_all=include_all)
    
    def _analyze_screen(self, question: str, focus_area: str = "full_screen"):
        """
        Analyze the current screen using vision AI.
        
        Args:
            question: Specific question about the screen
            focus_area: Area to focus on (full_screen, top, bottom, center, left, right)
        """
        try:
            screenshot_bytes = self.env.screenshot()
            
            # Build the analysis prompt
            area_context = ""
            if focus_area != "full_screen":
                area_context = f" Focus particularly on the {focus_area} area of the screen."
            
            analysis_prompt = f"""Analyze this Android device screenshot and answer the following question:

Question: {question}{area_context}

Provide a clear, concise answer based on what you can see in the screenshot. Include:
- Direct answer to the question
- Relevant details you observe
- Any UI elements that might help with the task

Be specific about positions (top, bottom, center) and element types (button, text field, icon) when relevant."""

            completion = OpenAI(
                base_url=APIConfig.get_base_url(),
                api_key=APIConfig.get_api_key()
            ).chat.completions.create(
                model=ModelConfig.get_vision_model(),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": analysis_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_bytes_to_data_url(screenshot_bytes)}
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            analysis = completion.choices[0].message.content
            return {
                "status": "success",
                "question": question,
                "focus_area": focus_area,
                "analysis": analysis
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _user_interaction(self, question: str = ""):
        """Handle user interaction via text or audio."""
        if self.audio:
            from audio import record_to_wav, transcribe_with_groq, start_stream, read
            read(question if question else self.messages[-1].get("content", ""))
            pa, stream = start_stream()
            wav_path = record_to_wav(duration_s=5.0, stream=stream, pa=pa)
            print("Transcribing...")
            transcribe = transcribe_with_groq(wav_path)
            os.remove(wav_path)
            return {"status": "success", "user_response": transcribe}
        else:
            prompt = question if question else "Enter your response: "
            user_input = input(f"{prompt}\n> ")
            return {"status": "success", "user_response": user_input}

    def chat(self):
        """Execute one round of agent conversation/action."""
        return self.client.chat()

    def done(self):
        """Mark the task as complete."""
        self.task = False
        return {"status": "success", "message": "Session ended"}
    
    # Legacy compatibility
    def apply_filters(self):
        """Legacy method for backward compatibility."""
        return self.env.get_display_elements(filters=self.filters)
    
    def get_screenshot(self, text):
        """Legacy method - use analyze_screen instead."""
        result = self._analyze_screen(question=text)
        return result.get("analysis", result.get("message", ""))


if __name__ == "__main__":
    # Test tool definitions
    print("Available tools:")
    for tool in tools_definition():
        print(f"  - {tool['function']['name']}: {tool['function']['description'][:60]}...")
