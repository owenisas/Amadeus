import time
import os
import json

from agent.main_agent import ActionAgent
from lib.driver_manager import create_driver
from lib.ui_interaction import UIInteraction
from lib.history import History


# Load configuration.
with open("config/config.json", "r") as config_file:
    config = json.load(config_file)

# Create the Appium driver.
driver = create_driver(config)

# Load filters from configuration.
filters = config.get("filters", [])

# Create UI interaction helper.
ui = UIInteraction(driver, filters)

# Optional: Create history if needed.
history = History()

# Define available tool functions.
def get_display_elements():
    return ui.get_truly_visible_elements()

def click(index: int):
    return ui.click_element(index)

def get_screenshot(text: str):
    data_url = ui.screenshot_to_data_url()
    # Here you could integrate more advanced image analysis or call an agent for description.
    return call_agent(f"Describe the screenshot with context: {text}")

def edit_textbox(text: str):
    try:
        textbox = driver.find_element("class name", "android.widget.EditText")
        textbox.clear()
        textbox.send_keys(text)
        return {"status": "success", "new_text": text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_apps():
    output = driver.execute_script("mobile: shell", {"command": "pm", "args": ["list", "packages", "-3"]}).splitlines()
    return [pkg.replace("package:", "") for pkg in output]

def open_app(app: str):
    driver.activate_app(app)
    return {"status": "success", "app": app}

# Map tool functions.
tools_map = {
    "get_display_elements": get_display_elements,
    "get_screenshot": get_screenshot,
    "click": click,
    "edit_textbox": edit_textbox,
    "get_apps": get_apps,
    "open_app": open_app,
    "call_agent": call_agent
}

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_display_elements",
            "description": "Retrieve all visible UI elements on the screen.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screenshot",
            "description": "Get and describe a screenshot of the current screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Context for screenshot description."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click the UI element with the given index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Index of the UI element."}
                },
                "required": ["index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_textbox",
            "description": "Edit a textbox on the screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to input."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_apps",
            "description": "Retrieve a list of installed apps.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an app given its package name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Package name of the app."}
                },
                "required": ["app"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_agent",
            "description": "Call the agent for additional information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Query or information to process."}
                },
                "required": ["message"]
            }
        }
    }
]

# Create an ActionAgent instance with a sample action.
action_message = "Check Tesla stock price"
action_agent = ActionAgent(
    tools_map=tools_map,
    tools_definition=tools_definition,
    message=action_message
)

# Main loop: continuously process actions.
if __name__ == "__main__":
    iteration = 1
    while True:
        time.sleep(0.5)
        print(f"Iteration {iteration}:")
        action_agent.chat()
        iteration += 1

