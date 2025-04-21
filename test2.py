import json
import os
import time

from openai import OpenAI
from selenium.common.exceptions import TimeoutException
from history import History
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.support.ui import WebDriverWait
from audio import listen, read
import xml.etree.ElementTree as ET
import re
import itertools
from agent.information_agent import call_agent
import base64
from ML.data import log_click_csv
import asyncio

from load_env import xAI

# ------------------------------
# 1. Set Up Appium Environment
# ------------------------------
capabilities = {
    "platformName": "Android",
    "automationName": "UiAutomator2",
    "deviceName": "Android",  # your device/emulator
    "noReset": True,
    "autoGrantPermissions": True,
    "skipServerInstallation": False,
    "skipDeviceInitialization": False,
    "disableWindowAnimation": True,
    "uiautomator2ServerInstallTimeout": 120000,  # ms
    "uiautomator2ServerLaunchTimeout": 120000,  # ms
    "androidInstallTimeout": 600000,  # ms (if installing APK)
    # Keep the session alive & avoid idle timeouts:
    "newCommandTimeout": 600,  # seconds
    "adbExecTimeout": 60000,  # ms
    "settings[waitForIdleTimeout]": 1000,  # ms
}
Task = True
# Containers for questions and answer options
driver = webdriver.Remote(
    'http://localhost:4723',
    options=UiAutomator2Options().load_capabilities(capabilities)
)

counter = [0]
with open("filter.json", "r") as fp:
    filters = json.load(fp)

dynamic_page_source = None
prev_page_source = None
task_progress = None
current_target = None
opened_app = None


def image_bytes_to_data_url(image_bytes, mime_type="image/png"):
    """
    Convert image bytes to a data URL.
    """
    base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded}"


train_ele = []
temp_list = []
# Get the screen dimensions.
window_size = driver.get_window_size()
screen_width = window_size["width"]
screen_height = window_size["height"]


async def _wait_for_source_change(driver, before_src, timeout):
    loop = asyncio.get_running_loop()

    def condition():
        return driver.page_source != before_src

    try:
        await loop.run_in_executor(
            None,
            lambda: WebDriverWait(driver, timeout).until(lambda d: d.page_source != before_src)
        )
        return True
    except TimeoutException:
        return False


# ------------------------------
# 2. Define Appium Tool Functions
# ------------------------------
class Solver:
    def __init__(self):
        self.driver = driver
        self.history = History()
        self.question = None
        self.answer_option = None
        self.continue_button = None

    def get_display_elements(self, target, progress):
        global current_target, task_progress
        current_target = target
        task_progress = progress
        elements = get_truly_visible_elements()
        temp_list.extend(elements)
        return elements

    def click_element(self, index: int):
        element_data = next((el for el in temp_list if el["index"] == index), None)
        if element_data is None:
            # Return an error message instead of raising an error.
            log_click_csv(app_name=opened_app, element=train_ele[index], outcome="failure", task=current_target,
                          task_progress=task_progress)
            return {"status": "failure", "message": f"click failed with index {index}"}

        # For logging purposes, get the text of the element.
        selected_text = element_data["text"]

        # Parse the "bounds" string (expected format: "[x1,y1][x2,y2]") to calculate center.
        bounds_str = element_data.get("bounds", "")
        matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
        if len(matches) < 2:
            return {"status": "failure",
                    "message": f"Invalid bounds format for element with index {index}: {bounds_str}"}

        # Convert extracted coordinates to integers.
        (x1, y1), (x2, y2) = map(lambda tup: (int(tup[0]), int(tup[1])), matches)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        # Use pointer actions to simulate a tap at the center coordinates.
        touch_input = PointerInput("touch", "touch")
        actions = ActionBuilder(self.driver, mouse=touch_input)

        # Move the pointer to the calculated location.
        actions.pointer_action.move_to_location(center_x, center_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)  # Pause briefly to simulate touch
        actions.pointer_action.pointer_up()

        # Execute the action.
        actions.perform()
        temp_list.clear()
        if dynamic_page_source != prev_page_source:
            log_click_csv(app_name=opened_app, element=train_ele[index], outcome="failure", task=current_target,
                          task_progress=task_progress)
        else:
            log_click_csv(app_name=opened_app, element=train_ele[index], outcome="success", task=current_target,
                          task_progress=task_progress)
        return {"clicked_index": index, "clicked_text": selected_text}

    def edit_any_textbox(self, new_text: str):
        # Find any textbox by looking for elements of class "android.widget.EditText".
        try:
            textboxes = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            if not textboxes:
                raise Exception("No textbox found")
            # Select the first textbox found.
            edit_box = textboxes[0]
            current_text = edit_box.text
            print("Textbox found. Current text:", current_text)
            edit_box.clear()
            edit_box.send_keys(new_text)
            print("New text entered into the textbox:", new_text)
            return {"status": "success", "new_text": new_text}
        except Exception as e:
            print("An error occurred while editing the textbox:", e)
            return {"status": "error", "error": str(e)}


# Create a Selector instance.
solve = Solver()


def parse_bounds(bounds_str):
    """
    Parses a bounds string formatted as "[left,top][right,bottom]".
    Returns a tuple: (left, top, right, bottom), or (0,0,0,0) if parsing fails.
    """
    matches = re.findall(r'\d+', bounds_str)
    if len(matches) >= 4:
        return map(int, matches[:4])
    return (0, 0, 0, 0)


def search_elements_xml(element, counter, filters, screen_width, screen_height, visible_elems):
    # Get the element text from the attribute, and trim any whitespace.
    element_text = element.attrib.get("text", "").strip()

    # Check if the element should be filtered out.
    if element_text in filters.get("filter", []):
        # Even if filtered out, continue to process its children.
        for child in list(element):
            search_elements_xml(child, counter, filters, screen_width, screen_height, visible_elems)
        return

    # Extract the bounds from the element's "bounds" attribute.
    bounds_attr = element.attrib.get("bounds", "")
    left, top, right, bottom = parse_bounds(bounds_attr)

    # Calculate the element's center point.
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2

    # Check if the element’s center lies within the device screen
    # and that it has non-empty text.
    if 0 <= center_x < screen_width and 0 <= center_y < screen_height:
        bounds_str = f"[{left},{top}][{right},{bottom}]"
        info = {
            "index": counter[0],
            "text": element.attrib.get("text", ""),
            "class": element.attrib.get("class", ""),
            "bounds": bounds_str,
        }
        visible_elems.append(info)
        counter[0] += 1
        global train_ele
        train_ele.append(element)
    # Recurse into the element's children.
    for child in list(element):
        search_elements_xml(child, counter, filters, screen_width, screen_height, visible_elems)


def get_truly_visible_elements():
    # Retrieve and parse the dynamic page source as an XML.
    global dynamic_page_source
    global prev_page_source
    prev_page_source = dynamic_page_source
    dynamic_page_source = driver.page_source
    root = ET.fromstring(dynamic_page_source)

    visible_elems = []
    counter = [0]  # Using a mutable counter to assign an index to each element.

    # Start the recursive search from the root of the XML tree.
    search_elements_xml(root, counter, filters, screen_width, screen_height, visible_elems)
    return visible_elems


def get_apps():
    output = driver.execute_script("mobile: shell", {"command": "pm", "args": ["list", "packages", "-3"]}).splitlines()
    clean_packages = [pkg.replace("package:", "") for pkg in output]
    clean_packages.append("com.android.chrome")
    clean_packages.append("com.google.android.calendar")
    clean_packages.append("com.google.android.contacts")
    clean_packages.append("com.google.android.youtube")
    clean_packages.append("com.google.android.apps.photos")
    clean_packages.append("com.android.vending")
    clean_packages.append("com.google.android.gm")
    clean_packages.append("com.android.settings")
    return clean_packages


def get_display_elements_tool(target, progress):
    return solve.get_display_elements(target=target, progress=progress)


def click_element_tool(index: int):
    return solve.click_element(index)


client2 = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=xAI
    # Replace with your actual API key
)


def screenshot_description(message):
    screenshot_bytes = driver.get_screenshot_as_png()
    # Convert the screenshot bytes to a data URL directly.
    data_url = image_bytes_to_data_url(screenshot_bytes)
    completion = client2.chat.completions.create(
        model="grok-2-vision-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Based on the screenshotL {message}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ]
    )
    return completion.choices[0].message.content


def get_screenshot(text):
    display = screenshot_description(text)
    print("Display data:", display)
    return display


def edit_textbox_tool(text: str):
    return solve.edit_any_textbox(text)


def open_app(app: str):
    global opened_app
    opened_app = app
    driver.activate_app(app)


def swipe(start_x, start_y, end_x, end_y, duration=800):
    """
    Perform a swipe gesture from (start_x, start_y) to (end_x, end_y).
    Duration is in milliseconds.
    """
    touch_input = PointerInput("touch", "touch")
    actions = ActionBuilder(driver, mouse=touch_input)
    actions.pointer_action.move_to_location(start_x, start_y)
    actions.pointer_action.pointer_down()
    actions.pointer_action.pause(duration / 1000)
    actions.pointer_action.move_to_location(end_x, end_y)
    actions.pointer_action.pointer_up()
    actions.perform()


def scroll_up(percentage=0.8):
    """
    Scroll up by a given percentage of the screen.
    """
    start_x = screen_width // 2
    start_y = screen_height // 2
    end_y = int(screen_height * (1 - (1 - percentage) / 2))
    swipe(start_x, start_y, start_x, end_y)


def scroll_down():
    """
        Scroll down by a given percentage of the screen.
        Default scrolls 80% of screen height.
        """
    start_x = screen_width // 2
    start_y = screen_height // 2
    end_y = int(screen_height * (0.1 / 2))
    swipe(start_x, start_y, start_x, end_y)


def go_back():
    driver.back()


def end_session():
    global Task, latest_message
    read(latest_message)
    Task = False


# ------------------------------
# 3. Define Function Calling Schema and Mapping
# ------------------------------
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_display_elements",
            "description": "Retrieve all text elements on the screen along with their indexes",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Describe the target of the element you are looking for(button, checkbox, etc.)"
                    },
                    "progress": {
                        "type": "boolean",
                        "description": "Whether or not the task is having progress compared to the last display elements."
                    }
                },
                "required": ["progress"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screenshot",
            "description": "Retrieve a description of the screenshot of the device",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Describe what description you need, be specific."
                    }
                },
                "required": ['text']
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click on the element at the specified index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Index of the element to click."
                    }
                },
                "required": ["index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_apps",
            "description": "Retrieve all apps on the device, paired with open_app.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_textbox",
            "description": "Find any textbox on the screen, clear it, and enter new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "New text to enter in the textbox."
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_agent",
            "description": "calls an agent that can answer informational questions, you should ask whenever you need an answer to a question",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "questions that needs to be answered"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Opens an app with the app name, has to run get_app before running this function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {
                        "type": "string",
                        "description": "app that needs to be opened"
                    }
                },
                "required": ["app"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_up",
            "description": "Scroll up the screen.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_down",
            "description": "Scroll down the screen.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "go_back",
            "description": "Navigate back to the previous screen.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "end the session when the task is complete.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]

# Map tool names to the corresponding functions.
tools_map = {
    "get_display_elements": get_display_elements_tool,
    "get_screenshot": get_screenshot,
    "click": click_element_tool,
    "edit_textbox": edit_textbox_tool,
    "call_agent": call_agent,
    "get_apps": get_apps,
    "open_app": open_app,
    "scroll_up": scroll_up,
    "scroll_down": scroll_down,
    "go_back": go_back,
    "end_session": end_session
}


def set_latest(msg):
    """Update the latest_message before tool execution."""
    global latest_message
    latest_message = msg


# ------------------------------
# 4. Set Up xAI (Grok) API Client
# ------------------------------
# Ensure your xAI API key is set in your environment variable "XAI_API_KEY"

# ------------------------------
# 5. Function Calling Workflow
# ------------------------------
Test_Prompt = "open facebook and make a post on mental health"
Stock_Prompt = "Check the stock price of Tesla"
Prompt = ("You are on facebook marketplace, "
          "ask for 30% off of the listing price for every item if the item is what I am looking for."
          "you should move on to the next listing after messaging one."
          "you should also check if you have messaged the same item before."
          "list of items I am looking for:Apple Products(IPad, IPhone, Macbook), PCs, herman miller chairs")
i = 1
os.environ["API_KEY"] = xAI
from agent.main_agent import ActionAgent

# user_request = listen()
# print(user_request)
action_agent = ActionAgent(
    tools_map=tools_map, tools_definition=tools_definition, message=Stock_Prompt, on_new_message=set_latest)
# note: save previous experience of clicking buttons
while Task:
    time.sleep(0.5)
    print(f"Response{i}:")
    action_agent.chat()
    i += 1
driver.quit()
