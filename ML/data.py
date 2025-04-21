import uuid
import csv
import asyncio
import aiofiles
from aiocsv import AsyncWriter
import re

# Generate one run_id for this entire session
RUN_ID = str(uuid.uuid4())


def parse_bounds(bounds_str: str):
    """
    Convert a bounds string "[x1,y1][x2,y2]" into (x, y, width, height).
    """
    # Find all integer substrings in the bounds string :contentReference[oaicite:2]{index=2}
    nums = list(map(int, re.findall(r'\d+', bounds_str)))
    x1, y1, x2, y2 = nums
    return x1, y1, x2 - x1, y2 - y1
CSV_PATH = r"C:\Users\thoma\PycharmProjects\Salieri\ML\ml_click_logs.csv"

fieldnames = [
    "run_id", "app_name", "target",
    "text", "checkable", "checked", "clickable", "enabled", "focusable", "focused", "selected", "displayed",
    "class", "x", "y", "width", "height",
    "outcome", "task_progress"
]


async def ensure_header(path):
    """Write header if file is empty or missing."""
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
            first = await f.readline()
    except FileNotFoundError:
        first = ""
    if not first.strip().split(",") == fieldnames:
        async with aiofiles.open(path, mode='w', encoding='utf-8', newline='') as f:
            writer = AsyncWriter(f)
            await writer.writerow(fieldnames)

async def log_click_csv_async(app_name, task, element, outcome, task_progress):
    """
    Appends a single row to CSV asynchronously.
    `row` should be a list matching the HEADER order.
    """
    # Ensure header once per run
    await ensure_header(CSV_PATH)

    bounds_str = element.attrib.get('bounds', '[0,0][0,0]')
    x, y, width, height = parse_bounds(bounds_str)
    row = {
        "run_id": RUN_ID,
        "app_name": app_name,
        "target": task,
        "text": element.text,
        "checkable": element.get_attribute("checkable"),
        "checked": element.get_attribute("checked"),
        "clickable": element.get_attribute("clickable"),
        "enabled": element.get_attribute("enabled"),
        "focusable": element.get_attribute("focusable"),
        "focused": element.get_attribute("focused"),
        "selected": element.get_attribute("selected"),
        "displayed": element.get_attribute("displayed"),
        "class": element.get_attribute("className"),
        "x": x, "y": y,
        "width": width, "height": height,
        "outcome": outcome,
        "task_progress": task_progress
    }
    # Append the row
    async with aiofiles.open(CSV_PATH, mode='a', encoding='utf-8', newline='') as f:
        writer = AsyncWriter(f)
        await writer.writerow(row)

def log_click_csv(app_name, task, element, outcome, task_progress):
    """
    Append a single CSV row (including run_id).
    """
    bounds_str = element.attrib.get('bounds', '[0,0][0,0]')
    x, y, width, height = parse_bounds(bounds_str)
    row = {
        "run_id": RUN_ID,
        "app_name": app_name,
        "target": task,
        "text": element.text,
        "checkable": element.attrib.get("checkable"),
        "checked": element.attrib.get("checked"),
        "clickable": element.attrib.get("clickable"),
        "enabled": element.attrib.get("enabled"),
        "focusable": element.attrib.get("focusable"),
        "focused": element.attrib.get("focused"),
        "selected": element.attrib.get("selected"),
        "displayed": element.attrib.get("displayed"),
        "class": element.attrib.get("className"),
        "x": x, "y": y,
        "width": width, "height": height,
        "outcome": outcome,
        "task_progress": task_progress
    }
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(row)
