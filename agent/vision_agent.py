"""
Vision Agent for Amadeus - Pure vision-based UI automation without UI tree parsing.
Relies entirely on visual understanding and coordinate-based interactions.

Uses a grid overlay system for accurate coordinate detection:
- Screenshots are annotated with a labeled grid
- Vision model references grid cells (e.g., "B3", "D5")
- Grid cells are converted to precise pixel coordinates
"""

import os
import sys
import base64
import json
import time
import re
import requests
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import Client
from environment.Android import Android
from config import APIConfig, ModelConfig, DataConfig
from openai import OpenAI

# ============================================================================
# DUAL MODEL CONFIGURATION
# ============================================================================
# Vision Model: NVIDIA Nemotron for image understanding
NVIDIA_VISION_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_VISION_MODEL = "nvidia/nemotron-nano-12b-v2-vl"

# Planning Model: DeepSeek for reasoning and tool calling
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_PLANNING_MODEL = "deepseek-ai/deepseek-v3.2"
# ============================================================================

# Try to import PIL for grid overlay
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Grid overlay disabled. Install with: pip install Pillow")


def image_bytes_to_data_url(image_bytes, mime_type="image/png"):
    """Convert image bytes to a data URL for vision models."""
    base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded}"


def load_vision_tools() -> list:
    """Load vision-specific tools definition."""
    tools_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 'vision_agent_tools.json')
    with open(tools_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Grid configuration - high density for small buttons
GRID_COLS = 20   # A-T columns (was 10)
GRID_ROWS = 40   # 1-40 rows (was 20)
GRID_COLOR = (255, 0, 0, 180)  # Semi-transparent red
LABEL_COLOR = (255, 255, 0)  # Yellow labels
LABEL_FREQUENCY = 2  # Only label every Nth cell to reduce clutter


class GridOverlay:
    """
    Handles grid overlay on screenshots for precise coordinate detection.
    
    Uses a high-density grid (20x40 = 800 cells) for accurate targeting of small elements.
    On a typical 1080x2400 screen, each cell is ~54x60 pixels.
    
    Cell labels use spreadsheet notation: A1, B2, ... T40
    For columns beyond J: K, L, M, N, O, P, Q, R, S, T
    """
    
    def __init__(self, screen_width: int, screen_height: int, cols: int = GRID_COLS, rows: int = GRID_ROWS):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.cols = cols
        self.rows = rows
        self.cell_width = screen_width / cols
        self.cell_height = screen_height / rows
    
    def add_grid_to_image(self, image_bytes: bytes) -> bytes:
        """Add grid overlay to screenshot image."""
        if not PIL_AVAILABLE:
            return image_bytes
        
        # Open image
        img = Image.open(BytesIO(image_bytes))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Try to load a small font for dense grid
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()
        
        # Draw grid lines (thinner for dense grid)
        for col in range(self.cols + 1):
            x = int(col * self.cell_width)
            # Major lines every 5 cells
            width = 2 if col % 5 == 0 else 1
            alpha = 200 if col % 5 == 0 else 100
            draw.line([(x, 0), (x, self.screen_height)], fill=(255, 0, 0, alpha)[:3], width=width)
        
        for row in range(self.rows + 1):
            y = int(row * self.cell_height)
            width = 2 if row % 5 == 0 else 1
            alpha = 200 if row % 5 == 0 else 100
            draw.line([(0, y), (self.screen_width, y)], fill=(255, 0, 0, alpha)[:3], width=width)
        
        # Add cell labels - only at intersections of major grid lines to reduce clutter
        for col in range(0, self.cols, LABEL_FREQUENCY):
            for row in range(0, self.rows, LABEL_FREQUENCY):
                label = self._cell_label(col, row)
                x = int(col * self.cell_width + 2)
                y = int(row * self.cell_height + 2)
                
                # Draw label background for visibility
                bbox = draw.textbbox((x, y), label, font=font)
                draw.rectangle(bbox, fill=(0, 0, 0, 180))
                draw.text((x, y), label, fill=LABEL_COLOR, font=font)
        
        # Convert back to bytes
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    
    def draw_grid(self, img: 'Image.Image') -> 'Image.Image':
        """
        Add grid overlay to a PIL Image object.
        Returns the modified image (for testing with synthetic screenshots).
        """
        if not PIL_AVAILABLE:
            return img
        
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Try to load a small font for dense grid
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()
        
        # Draw grid lines
        for col in range(self.cols + 1):
            x = int(col * self.cell_width)
            width = 2 if col % 5 == 0 else 1
            draw.line([(x, 0), (x, self.screen_height)], fill=(255, 0, 0), width=width)
        
        for row in range(self.rows + 1):
            y = int(row * self.cell_height)
            width = 2 if row % 5 == 0 else 1
            draw.line([(0, y), (self.screen_width, y)], fill=(255, 0, 0), width=width)
        
        # Add cell labels
        for col in range(0, self.cols, LABEL_FREQUENCY):
            for row in range(0, self.rows, LABEL_FREQUENCY):
                label = self._cell_label(col, row)
                x = int(col * self.cell_width + 2)
                y = int(row * self.cell_height + 2)
                bbox = draw.textbbox((x, y), label, font=font)
                draw.rectangle(bbox, fill=(0, 0, 0))
                draw.text((x, y), label, fill=LABEL_COLOR, font=font)
        
        return img
    
    def _cell_label(self, col: int, row: int) -> str:
        """Generate cell label like A1, B2, K15, T40, etc."""
        col_letter = chr(ord('A') + col)
        return f"{col_letter}{row + 1}"
    
    def cell_to_coordinates(self, cell: str) -> tuple:
        """
        Convert cell reference (e.g., 'B3', 'K15') to pixel coordinates (center of cell).
        
        Returns (x, y) tuple or None if invalid.
        """
        cell = cell.strip().upper()
        
        # Parse cell reference - handle single letter columns A-T
        match = re.match(r'^([A-T])(\d+)$', cell)
        if not match:
            return None
        
        col_letter, row_str = match.groups()
        col = ord(col_letter) - ord('A')
        row = int(row_str) - 1
        
        # Validate bounds
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return None
        
        # Calculate center of cell
        x = int((col + 0.5) * self.cell_width)
        y = int((row + 0.5) * self.cell_height)
        
        return (x, y)
    
    def coordinates_to_cell(self, x: int, y: int) -> str:
        """Convert pixel coordinates to cell reference."""
        col = int(x / self.cell_width)
        row = int(y / self.cell_height)
        col = max(0, min(col, self.cols - 1))
        row = max(0, min(row, self.rows - 1))
        return self._cell_label(col, row)
    
    def get_grid_description(self) -> str:
        """Get description of the grid system for the prompt."""
        return f"""## Grid System (HIGH PRECISION)
The screen has a **{self.cols}x{self.rows}** grid overlay for precise targeting:
- Columns: A-T (left to right, 20 columns)  
- Rows: 1-{self.rows} (top to bottom, 40 rows)
- Cell size: ~{int(self.cell_width)}x{int(self.cell_height)} pixels (small enough for icons/buttons)

**Major gridlines** are drawn every 5 cells for easy reference.
Labels shown at major intersections: A1, A3, A5... C1, C3, C5... etc.

Examples:
- A1 = top-left corner
- T40 = bottom-right corner  
- J20 = center of screen
- Small icon in upper-right: might be in S3 or T4"""


# Vision-only system prompt with grid system
VISION_SYSTEM_PROMPT = """You are Amadeus Vision, an AI agent that controls an Android device using ONLY visual understanding. You cannot access the UI element tree - you must rely entirely on what you SEE in screenshots.

## CRITICAL: High-Precision Grid System
Screenshots have a **20x40 grid overlay** for precise targeting of even small buttons:
- Columns: A through T (left to right, 20 columns)
- Rows: 1 through 40 (top to bottom, 40 rows)
- Cell size: ~54x60 pixels - small enough for icons!
- Reference: "A1" = top-left, "T40" = bottom-right, "J20" = center

**ALWAYS use grid cell references (e.g., "C5", "M28", "T3") for element locations!**

## How You Perceive the Screen
- Use `observe_screen` to get a screenshot WITH grid overlay
- Elements are identified by their grid cell position
- Example: "The Settings button is in cell D3"

## How You Interact
- `tap_cell(cell)` - tap the center of a grid cell (e.g., "D3")
- `tap_element(description)` - find and tap element by description
- `type_text(text)` - type into focused field
- `scroll(direction, amount)` - scroll the screen
- `press_key(key)` - press system keys (back, home, enter)

## Workflow

### 1. ALWAYS Observe First
Call `observe_screen` before any action. The grid helps you identify exact positions.

### 2. Reference Grid Cells
When locating elements, note their grid cell:
- "The search icon is in cell B2"
- "The 'Login' button spans cells E15-F15"

### 3. Tap Using Cells
Use `tap_cell("B2")` to tap precisely at that grid position.

### 4. Verify After Acting
Call `observe_screen` again after taps to confirm success.

## Tips
- If an element spans multiple cells, use the CENTER cell
- Small icons: use the exact cell they're in
- Buttons with text: reference the cell containing the text
- If unsure, describe the element and let tap_element find it

Remember: The grid overlay ensures PRECISE coordinate mapping between what you see and where you tap!"""


class VisionAgent:
    """
    Pure vision-based agent for Android automation.
    Does not use UI element trees - relies entirely on visual understanding.
    
    Uses a grid overlay system for accurate coordinate mapping:
    1. Screenshots are annotated with a labeled grid (A1, B2, C3, etc.)
    2. Vision model references grid cells in its responses
    3. Grid cells are converted to precise pixel coordinates
    """
    
    def __init__(
        self,
        message: str,
        on_new_message: callable = None,
        infinite: bool = False,
        interactive: bool = False,
        audio: bool = False
    ):
        self.env = Android()
        self.screen_width = self.env.screen_width
        self.screen_height = self.env.screen_height
        
        # Initialize grid overlay system
        self.grid = GridOverlay(self.screen_width, self.screen_height)
        
        # Build system prompt with grid info
        system_prompt = VISION_SYSTEM_PROMPT + "\n\n" + self.grid.get_grid_description()
        
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "I'm ready to help you control your Android device using vision. I'll use the grid overlay to precisely locate and interact with elements. What would you like me to do?"},
            {"role": "user", "content": message}
        ]
        
        # Vision-only tools map
        self.tools_map = {
            # Observation
            "observe_screen": self._observe_screen,
            "find_element": self._find_element,
            "find_text": self._find_text,
            "get_screen_size": self._get_screen_size,
            
            # Grid-based tap (PRIMARY method)
            "tap_cell": self._tap_cell,
            
            # Coordinate tap (backup)
            "tap_at": self.env.tap_coordinates,
            
            # Smart tap methods
            "tap_element": self._tap_element,
            "tap_text": self._tap_text,
            
            # Other taps
            "double_tap_at": lambda x, y: self.env.double_tap(x=x, y=y),
            "long_press_at": lambda x, y, duration_ms=1000: self.env.long_press(x=x, y=y, duration_ms=duration_ms),
            
            # Text input
            "type_text": self._type_text,
            
            # Scroll/Swipe
            "scroll": self.env.scroll,
            "swipe": self.env.swipe,
            
            # Navigation
            "press_key": self.env.press_key,
            "open_app": self.env.open_app,
            
            # Utility
            "wait": self.env.wait,
        }
        
        self.tool_definition = load_vision_tools()
        
        # Add tap_cell to tool definitions
        self.tool_definition.insert(0, {
            "type": "function",
            "function": {
                "name": "tap_cell",
                "description": "Tap at the center of a grid cell. This is the most reliable way to tap - precise enough for small icons. Use grid references like 'A1', 'M25', 'T40'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cell": {
                            "type": "string",
                            "description": "Grid cell reference (e.g., 'B3', 'M28', 'T5'). Column A-T (20 cols), Row 1-40."
                        }
                    },
                    "required": ["cell"]
                }
            }
        })
        
        # Initialize client with DeepSeek for planning/reasoning
        # Vision is handled separately by NVIDIA Nemotron
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY', APIConfig.get_api_key())
        
        self.client = Client(
            model=DEEPSEEK_PLANNING_MODEL,
            base=DEEPSEEK_BASE_URL,
            tools_map=self.tools_map,
            tools_definition=self.tool_definition,
            messages=self.messages,
            on_new_message=on_new_message,
            api_key=deepseek_api_key
        )
        
        print(f"[VisionAgent] Planning model: {DEEPSEEK_PLANNING_MODEL}")
        print(f"[VisionAgent] Vision model: {NVIDIA_VISION_MODEL}")
        
        self.task = True
        self.audio = audio
        
        # Setup optional tools
        self._setup_optional_tools(infinite, interactive)
    
    def _setup_optional_tools(self, infinite: bool, interactive: bool):
        """Setup optional tools."""
        if not infinite:
            self.tools_map["end_session"] = self.done
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "end_session",
                    "description": "End the session when task is complete.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            })
        
        if interactive:
            self.tools_map["ask_user"] = self._user_interaction
            self.tool_definition.append({
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask user for input or clarification.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Question to ask"}
                        },
                        "required": ["question"]
                    }
                }
            })
    
    def _call_vision_model(self, prompt: str, screenshot_bytes: bytes = None, add_grid: bool = True, think: bool = True) -> str:
        """
        Call NVIDIA Nemotron vision model for image understanding.
        
        Args:
            prompt: Question or instruction about the image
            screenshot_bytes: Raw screenshot bytes (will capture if None)
            add_grid: Whether to add grid overlay
            think: Whether to enable /think mode for deeper reasoning
        """
        if screenshot_bytes is None:
            screenshot_bytes = self.env.screenshot()
        
        # Add grid overlay if requested
        if add_grid and PIL_AVAILABLE:
            screenshot_bytes = self.grid.add_grid_to_image(screenshot_bytes)
        
        # Encode image to base64
        base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Build content with image
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            }
        ]
        
        # NVIDIA API request
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY', '')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        payload = {
            "model": NVIDIA_VISION_MODEL,
            "messages": [
                {"role": "system", "content": "/think" if think else "/no_think"},
                {"role": "user", "content": content}
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            response = requests.post(NVIDIA_VISION_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            return f"NVIDIA Vision API error: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Vision response parsing error: {str(e)}"
    
    def _tap_cell(self, cell: str) -> dict:
        """
        Tap at the center of a grid cell.
        
        Args:
            cell: Grid cell reference (e.g., 'B3', 'F12')
        """
        coords = self.grid.cell_to_coordinates(cell)
        
        if coords is None:
            return {
                "status": "error",
                "message": f"Invalid cell reference: {cell}. Use format like 'A1', 'M25', 'T40'. Columns A-T (20), Rows 1-40."
            }
        
        x, y = coords
        result = self.env.tap_coordinates(x, y)
        
        return {
            "status": "success",
            "action": "tap_cell",
            "cell": cell.upper(),
            "coordinates": {"x": x, "y": y},
            "tap_result": result
        }
    
    def _observe_screen(self, focus: str = None) -> dict:
        """
        Take a screenshot with grid overlay and provide detailed visual analysis.
        The grid helps identify precise element locations.
        """
        focus_instruction = ""
        if focus:
            focus_instruction = f"\n\nFocus especially on: {focus}"
        
        grid_info = self.grid.get_grid_description()
        
        prompt = f"""Analyze this Android screenshot WITH GRID OVERLAY.

{grid_info}

Describe what you see:

1. **Current App/Screen**: What app or screen is visible?

2. **Interactive Elements by Grid Position**:
   List visible buttons, icons, text fields, links with their GRID CELL:
   - Example: "Search icon in cell B2"
   - Example: "Login button spanning cells E15-F15"
   - Example: "Text field in cells C8-H8"

3. **Text Content**: Important text and which cells contain it

4. **Navigation Elements**: Back button, menus, tabs with grid positions
{focus_instruction}

IMPORTANT: Always reference grid cells (A1, B2, etc.) for element positions!"""

        analysis = self._call_vision_model(prompt, add_grid=True)
        
        return {
            "status": "success",
            "screen_size": {"width": self.screen_width, "height": self.screen_height},
            "grid": {"columns": self.grid.cols, "rows": self.grid.rows},
            "analysis": analysis
        }
    
    def _find_element(self, description: str, return_multiple: bool = False) -> dict:
        """
        Find a UI element by visual description and return its GRID CELL.
        """
        prompt = f"""Find the UI element: "{description}"

The screen has a {self.grid.cols}x{self.grid.rows} grid overlay.
Columns: A-{chr(ord('A') + self.grid.cols - 1)} (left to right)
Rows: 1-{self.grid.rows} (top to bottom)

{"Find ALL matching elements." if return_multiple else "Find the BEST matching element."}

Respond in this EXACT format:
FOUND: yes/no
ELEMENT:
- description: [what you found]
- cell: [grid cell like B3, F12]
- confidence: [high/medium/low]

If the element spans multiple cells, give the CENTER cell.
If not found, explain what you see instead."""

        result = self._call_vision_model(prompt, add_grid=True)
        
        # Parse the response to extract cell reference
        cells = self._parse_cells(result)
        
        if cells:
            cell = cells[0]
            coords = self.grid.cell_to_coordinates(cell)
            return {
                "status": "success",
                "description": description,
                "cell": cell,
                "coordinates": {"x": coords[0], "y": coords[1]} if coords else None,
                "raw_analysis": result
            }
        else:
            return {
                "status": "not_found",
                "description": description,
                "analysis": result
            }
    
    def _find_text(self, text: str, partial_match: bool = False) -> dict:
        """
        Find specific text on screen and return its GRID CELL.
        """
        match_type = "containing" if partial_match else "exactly matching"
        
        prompt = f"""Find text {match_type}: "{text}"

The screen has a grid overlay with columns A-{chr(ord('A') + self.grid.cols - 1)} and rows 1-{self.grid.rows}.

Respond in this EXACT format:
FOUND: yes/no
TEXT:
- text: [exact text found]
- cell: [grid cell like C5]
- confidence: [high/medium/low]

If not found, describe what text IS visible."""

        result = self._call_vision_model(prompt, add_grid=True)
        cells = self._parse_cells(result)
        
        if cells:
            cell = cells[0]
            coords = self.grid.cell_to_coordinates(cell)
            return {
                "status": "success",
                "search_text": text,
                "cell": cell,
                "coordinates": {"x": coords[0], "y": coords[1]} if coords else None,
                "raw_analysis": result
            }
        else:
            return {
                "status": "not_found",
                "search_text": text,
                "analysis": result
            }
    
    def _parse_cells(self, response: str) -> list:
        """Parse grid cell references from vision model response."""
        cells = []
        
        # Look for cell patterns like A1, B12, J20
        pattern = r'\b([A-Ja-j])(\d{1,2})\b'
        matches = re.findall(pattern, response)
        
        for col, row in matches:
            col = col.upper()
            row_num = int(row)
            # Validate it's within our grid
            if ord(col) - ord('A') < self.grid.cols and 1 <= row_num <= self.grid.rows:
                cell = f"{col}{row_num}"
                if cell not in cells:
                    cells.append(cell)
        
        return cells
    
    def _parse_coordinates(self, response: str) -> list:
        """Legacy: Parse coordinates from vision model response."""
        coords = []
        lines = response.split('\n')
        current_x, current_y = None, None
        
        for line in lines:
            line_lower = line.lower().strip()
            x_match = re.search(r'x[:\s]+(\d+)', line_lower)
            if x_match:
                current_x = int(x_match.group(1))
            y_match = re.search(r'y[:\s]+(\d+)', line_lower)
            if y_match:
                current_y = int(y_match.group(1))
            if current_x is not None and current_y is not None:
                if 0 <= current_x <= self.screen_width and 0 <= current_y <= self.screen_height:
                    coords.append({"x": current_x, "y": current_y})
                current_x, current_y = None, None
        
        return coords
    
    def _tap_element(self, description: str) -> dict:
        """Find and tap on an element by description using grid system."""
        # First find the element
        find_result = self._find_element(description)
        
        if find_result["status"] != "success":
            return {
                "status": "error",
                "message": f"Could not find element: {description}",
                "search_result": find_result
            }
        
        # Tap using the cell reference
        cell = find_result.get("cell")
        if cell:
            return self._tap_cell(cell)
        
        # Fallback to coordinates if available
        coords = find_result.get("coordinates")
        if coords:
            tap_result = self.env.tap_coordinates(coords["x"], coords["y"])
            return {
                "status": "success",
                "action": "tap_element",
                "description": description,
                "coordinates": coords,
                "tap_result": tap_result
            }
        
        return {"status": "error", "message": "Could not determine tap location"}
    
    def _tap_text(self, text: str) -> dict:
        """Find and tap on specific text using grid system."""
        find_result = self._find_text(text)
        
        if find_result["status"] != "success":
            return {
                "status": "error",
                "message": f"Could not find text: {text}",
                "search_result": find_result
            }
        
        # Tap using the cell reference
        cell = find_result.get("cell")
        if cell:
            result = self._tap_cell(cell)
            result["text"] = text
            return result
        
        # Fallback to coordinates
        coords = find_result.get("coordinates")
        if coords:
            tap_result = self.env.tap_coordinates(coords["x"], coords["y"])
            return {
                "status": "success",
                "action": "tap_text",
                "text": text,
                "coordinates": coords,
                "tap_result": tap_result
            }
        
        return {"status": "error", "message": "Could not determine tap location"}
    
    def _type_text(self, text: str, clear_first: bool = True, submit: bool = False) -> dict:
        """Type text into the focused field."""
        return self.env.type_text(text, clear_first=clear_first, submit=submit)
    
    def _get_screen_size(self) -> dict:
        """Get screen dimensions."""
        return {
            "status": "success",
            "width": self.screen_width,
            "height": self.screen_height
        }
    
    def _user_interaction(self, question: str = "") -> dict:
        """Handle user interaction."""
        if self.audio:
            from audio import record_to_wav, transcribe_with_groq, start_stream, read
            read(question)
            pa, stream = start_stream()
            wav_path = record_to_wav(duration_s=5.0, stream=stream, pa=pa)
            transcribe = transcribe_with_groq(wav_path)
            os.remove(wav_path)
            return {"status": "success", "user_response": transcribe}
        else:
            user_input = input(f"{question}\n> ")
            return {"status": "success", "user_response": user_input}
    
    def chat(self):
        """Execute one round of conversation/action."""
        return self.client.chat()
    
    def done(self):
        """Mark task as complete."""
        self.task = False
        return {"status": "success", "message": "Session ended"}


if __name__ == "__main__":
    print("Vision Agent Tools:")
    for tool in load_vision_tools():
        print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")
