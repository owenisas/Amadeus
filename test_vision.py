#!/usr/bin/env python3
"""
Vision Model Comparison Test
Compares NVIDIA Nemotron vs OpenAI GPT-4o for visual perception accuracy.
Helps determine which model to use for vision-based automation.
"""

import os
import sys
import json
import base64
import time
import requests
from io import BytesIO
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment - we need API keys
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# Import the grid overlay system
from agent.vision_agent import GridOverlay, NVIDIA_VISION_URL, NVIDIA_VISION_MODEL


# ============================================================================
# CONFIGURATION
# ============================================================================
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')


@dataclass
class TestElement:
    """A test element with known position."""
    x: int
    y: int
    width: int
    height: int
    elem_type: str
    label: str
    expected_cell: str  # Expected grid cell(s)


def encode_image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def create_test_screenshot(width=1080, height=2400) -> Tuple[Image.Image, List[TestElement]]:
    """Create a synthetic test screenshot with known elements at specific positions."""
    img = Image.new('RGB', (width, height), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
            small_font = font
    
    elements = []
    
    # ===== TOP NAVIGATION BAR =====
    # Back button - top left
    elements.append(TestElement(20, 60, 100, 50, "button", "Back", "A2"))
    draw.rounded_rectangle([20, 60, 120, 110], radius=10, fill='#4a69bd', outline='#6a89cc')
    draw.text((70, 85), "Back", fill='white', font=small_font, anchor='mm')
    
    # Title - center
    elements.append(TestElement(width//2 - 75, 60, 150, 50, "text", "Settings", "J2-K2"))
    draw.text((width//2, 85), "Settings", fill='white', font=font, anchor='mm')
    
    # Save button - top right
    elements.append(TestElement(width - 120, 60, 100, 50, "button", "Save", "S2-T2"))
    draw.rounded_rectangle([width - 120, 60, width - 20, 110], radius=10, fill='#27ae60', outline='#2ecc71')
    draw.text((width - 70, 85), "Save", fill='white', font=small_font, anchor='mm')
    
    # ===== TOGGLE SWITCHES =====
    elements.append(TestElement(width - 100, 200, 80, 40, "toggle", "Toggle ON", "S4"))
    draw.rounded_rectangle([width - 100, 200, width - 20, 240], radius=20, fill='#27ae60')
    draw.ellipse([width - 40, 205, width - 10, 235], fill='white')
    draw.text((40, 220), "Dark Mode", fill='white', font=small_font, anchor='lm')
    
    elements.append(TestElement(width - 100, 280, 80, 40, "toggle", "Toggle OFF", "S5"))
    draw.rounded_rectangle([width - 100, 280, width - 20, 320], radius=20, fill='#7f8c8d')
    draw.ellipse([width - 100 + 5, 285, width - 100 + 35, 315], fill='white')
    draw.text((40, 300), "Notifications", fill='white', font=small_font, anchor='lm')
    
    # ===== MENU ITEMS =====
    menu_items = [
        ("Account Settings", 400, "A7-T7"),
        ("Privacy", 480, "A8-T8"),
        ("Security", 560, "A10-T10"),
        ("Display", 640, "A11-T11"),
        ("Language", 720, "A12-T12"),
    ]
    
    for label, y, expected_cell in menu_items:
        elements.append(TestElement(40, y, width - 80, 60, "menu_item", label, expected_cell))
        draw.rounded_rectangle([40, y, width - 40, y + 60], radius=8, fill='#2d3436')
        draw.text((60, y + 30), label, fill='white', font=small_font, anchor='lm')
        draw.text((width - 60, y + 30), ">", fill='#636e72', font=font, anchor='mm')
    
    # ===== SMALL ICONS ROW (precision test) =====
    icons_y = 850
    icon_data = [
        ("🔔", 50, "A15"),
        ("⚙️", 150, "C15"),
        ("👤", 250, "E15"),
        ("📱", 350, "G15"),
        ("🔒", 450, "I15"),
    ]
    
    for icon, x, expected_cell in icon_data:
        elements.append(TestElement(x, icons_y, 48, 48, "icon", icon, expected_cell))
        draw.ellipse([x, icons_y, x + 48, icons_y + 48], fill='#34495e', outline='#5d6d7e')
        draw.text((x + 24, icons_y + 24), icon, fill='white', font=small_font, anchor='mm')
    
    # ===== BOTTOM NAVIGATION =====
    nav_y = height - 120
    nav_items = [
        ("Home", 54, "A38"),
        ("Search", width//4, "F38"),
        ("Add", width//2 - 30, "J38"),
        ("Chat", 3*width//4 - 30, "N38"),
        ("Profile", width - 114, "S38"),
    ]
    
    for label, x, expected_cell in nav_items:
        elements.append(TestElement(x, nav_y, 60, 60, "nav", label, expected_cell))
        draw.ellipse([x, nav_y, x + 60, nav_y + 60], fill='#2c3e50')
        draw.text((x + 30, nav_y + 80), label, fill='#bdc3c7', font=small_font, anchor='mm')
    
    # ===== STATUS BAR =====
    draw.rectangle([0, 0, width, 40], fill='#0f0f1a')
    draw.text((width - 60, 20), "100%", fill='white', font=small_font, anchor='mm')
    draw.text((60, 20), "12:00", fill='white', font=small_font, anchor='mm')
    
    return img, elements


def call_nvidia_nemotron(img_base64: str, prompt: str, think: bool = True) -> Tuple[str, float]:
    """Call NVIDIA Nemotron vision model."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
    ]
    
    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {"role": "system", "content": "/think" if think else "/no_think"},
            {"role": "user", "content": content}
        ],
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": False
    }
    
    start = time.time()
    try:
        response = requests.post(NVIDIA_VISION_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        elapsed = time.time() - start
        return result['choices'][0]['message']['content'], elapsed
    except Exception as e:
        return f"Error: {str(e)}", time.time() - start


def call_openai_gpt4o(img_base64: str, prompt: str) -> Tuple[str, float]:
    """Call OpenAI GPT-4o vision model."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    start = time.time()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}", "detail": "high"}}
                ]
            }],
            max_tokens=2000
        )
        elapsed = time.time() - start
        return response.choices[0].message.content, elapsed
    except Exception as e:
        return f"Error: {str(e)}", time.time() - start


def run_perception_test(model_name: str, call_func, img_base64: str, grid_description: str, elements: List[TestElement]):
    """Run a perception test with a specific model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print('='*60)
    
    prompt = f"""Analyze this Android screenshot with grid overlay.

{grid_description}

Answer these questions precisely:

1. **Top Navigation**: What 3 elements are in the top bar? Give their grid cells.

2. **Toggles**: How many toggle switches? Which is ON and which is OFF? Grid cells?

3. **Menu Items**: List ALL menu item labels with their grid cells.

4. **Small Icons**: How many small circular icons in a row? Which grid cells?

5. **Bottom Nav**: What are the 5 bottom navigation labels? Give each one's grid cell.

6. **PRECISION TEST**: What is the EXACT grid cell for "Privacy" menu item?

Use ONLY grid cell references like A1, B2, K15, T40."""

    response, elapsed = call_func(img_base64, prompt)
    
    print(f"\n⏱️  Response time: {elapsed:.2f}s")
    print(f"\n📝 Response:\n{'-'*40}")
    print(response)
    print('-'*40)
    
    return response, elapsed


def evaluate_accuracy(response: str, elements: List[TestElement]) -> dict:
    """Evaluate how accurately the model identified elements."""
    import re
    
    # Extract all cell references from response
    cells_found = set(re.findall(r'\b([A-T])(\d{1,2})\b', response.upper()))
    cells_found = {f"{c}{r}" for c, r in cells_found}
    
    # Check which expected cells were found
    correct = 0
    missed = []
    
    for elem in elements:
        expected = elem.expected_cell.split('-')[0]  # Take first cell if range
        if expected in cells_found:
            correct += 1
        else:
            missed.append(f"{elem.label}: expected {elem.expected_cell}")
    
    return {
        "total_elements": len(elements),
        "correct": correct,
        "accuracy": correct / len(elements) * 100,
        "missed": missed[:5],  # Show first 5 missed
        "cells_mentioned": len(cells_found)
    }


def compare_models():
    """Compare NVIDIA Nemotron vs OpenAI GPT-4o."""
    print("\n" + "="*70)
    print("  VISION MODEL COMPARISON: NVIDIA Nemotron vs OpenAI GPT-4o")
    print("="*70)
    
    # Check API keys
    if not NVIDIA_API_KEY:
        print("⚠️  NVIDIA_API_KEY not set - skipping Nemotron test")
    if not OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY not set - skipping GPT-4o test")
    
    # Create test screenshot
    print("\n📸 Creating test screenshot with known elements...")
    screenshot, elements = create_test_screenshot()
    
    # Apply grid overlay
    print("📐 Applying 20x40 grid overlay...")
    grid = GridOverlay(screenshot.width, screenshot.height)
    screenshot_with_grid = grid.draw_grid(screenshot)
    grid_description = grid.get_grid_description()
    
    # Save for inspection
    test_path = "/Users/user/Documents/Amadeus/test_screenshot_grid.png"
    screenshot_with_grid.save(test_path)
    print(f"💾 Screenshot saved: {test_path}")
    
    # Encode
    img_base64 = encode_image_to_base64(screenshot_with_grid)
    
    results = {}
    
    # Test NVIDIA Nemotron
    if NVIDIA_API_KEY:
        response, elapsed = run_perception_test(
            "NVIDIA Nemotron (nemotron-nano-12b-v2-vl)",
            lambda img, p: call_nvidia_nemotron(img, p, think=True),
            img_base64,
            grid_description,
            elements
        )
        eval_result = evaluate_accuracy(response, elements)
        results['nvidia'] = {
            'response': response,
            'time': elapsed,
            **eval_result
        }
    
    # Test OpenAI GPT-4o
    if OPENAI_API_KEY:
        response, elapsed = run_perception_test(
            "OpenAI GPT-4o",
            call_openai_gpt4o,
            img_base64,
            grid_description,
            elements
        )
        eval_result = evaluate_accuracy(response, elements)
        results['openai'] = {
            'response': response,
            'time': elapsed,
            **eval_result
        }
    
    # Summary
    print("\n" + "="*70)
    print("  COMPARISON SUMMARY")
    print("="*70)
    
    print(f"\n📊 Ground Truth ({len(elements)} elements):")
    print("-"*40)
    for elem in elements:
        print(f"  {elem.label:20} → {elem.expected_cell}")
    
    print("\n📈 Results:")
    print("-"*40)
    for model, data in results.items():
        print(f"\n  {model.upper()}:")
        print(f"    ⏱️  Time: {data['time']:.2f}s")
        print(f"    ✅ Accuracy: {data['accuracy']:.1f}% ({data['correct']}/{data['total_elements']})")
        print(f"    📍 Cells mentioned: {data['cells_mentioned']}")
        if data['missed']:
            print(f"    ❌ Missed: {data['missed'][:3]}")
    
    print("\n" + "="*70)
    print("  RECOMMENDATION")
    print("="*70)
    
    if 'nvidia' in results and 'openai' in results:
        nvidia_acc = results['nvidia']['accuracy']
        openai_acc = results['openai']['accuracy']
        nvidia_time = results['nvidia']['time']
        openai_time = results['openai']['time']
        
        if nvidia_acc >= openai_acc - 5:  # Within 5% accuracy
            if nvidia_time < openai_time:
                print("✅ NVIDIA Nemotron: Similar accuracy, faster response")
            else:
                print("🤔 Both models comparable - NVIDIA may be cheaper")
        elif nvidia_acc < openai_acc - 10:
            print("✅ OpenAI GPT-4o: Better accuracy for precise grid detection")
        else:
            print("🤔 Both models viable - consider cost/speed tradeoffs")
    
    return results


def test_single_model(model: str = "nvidia"):
    """Test a single model."""
    print(f"\n📸 Creating test screenshot...")
    screenshot, elements = create_test_screenshot()
    grid = GridOverlay(screenshot.width, screenshot.height)
    screenshot_with_grid = grid.draw_grid(screenshot)
    grid_description = grid.get_grid_description()
    
    test_path = "/Users/user/Documents/Amadeus/test_screenshot_grid.png"
    screenshot_with_grid.save(test_path)
    print(f"💾 Screenshot saved: {test_path}")
    
    img_base64 = encode_image_to_base64(screenshot_with_grid)
    
    if model == "nvidia":
        response, elapsed = run_perception_test(
            "NVIDIA Nemotron",
            lambda img, p: call_nvidia_nemotron(img, p),
            img_base64,
            grid_description,
            elements
        )
    else:
        response, elapsed = run_perception_test(
            "OpenAI GPT-4o",
            call_openai_gpt4o,
            img_base64,
            grid_description,
            elements
        )
    
    eval_result = evaluate_accuracy(response, elements)
    print(f"\n✅ Accuracy: {eval_result['accuracy']:.1f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test vision model perception")
    parser.add_argument("--compare", action="store_true", help="Compare NVIDIA vs OpenAI")
    parser.add_argument("--nvidia", action="store_true", help="Test NVIDIA Nemotron only")
    parser.add_argument("--openai", action="store_true", help="Test OpenAI GPT-4o only")
    args = parser.parse_args()
    
    if args.compare:
        compare_models()
    elif args.nvidia:
        test_single_model("nvidia")
    elif args.openai:
        test_single_model("openai")
    else:
        # Default: compare both
        compare_models()
