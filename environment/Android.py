from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

import xml.etree.ElementTree as ET
import re


def parse_bounds(bounds_str):
    """
    Parses a bounds string formatted as "[left,top][right,bottom]".
    Returns a tuple: (left, top, right, bottom), or (0,0,0,0) if parsing fails.
    """
    matches = re.findall(r'\d+', bounds_str)
    if len(matches) >= 4:
        return map(int, matches[:4])
    return (0, 0, 0, 0)


class Android:
    def __init__(self):
        self.capabilities = {
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
        self.driver = webdriver.Remote(
            'http://localhost:4723',
            options=UiAutomator2Options().load_capabilities(self.capabilities)
        )

        self.window_size = self.driver.get_window_size()
        self.screen_width = self.window_size["width"]
        self.screen_height = self.window_size["height"]
        self.temp_ele_list = []
        self.actions = ActionBuilder(self.driver, mouse=PointerInput("touch", "touch"))
        self.current_app = ''

    def search_elements(self, element, counter, filters):
        # Get the element text from the attribute, and trim any whitespace.
        element_text = element.attrib.get("text", "").strip()

        # Check if the element should be filtered out.
        if filters is not None:
            if element_text in filters.get("filter", []):
                # Even if filtered out, continue to process its children.
                for child in list(element):
                    self.search_elements(child, counter, filters)
                return

        # Extract the bounds from the element's "bounds" attribute.
        bounds_attr = element.attrib.get("bounds", "")
        left, top, right, bottom = parse_bounds(bounds_attr)

        # Calculate the element's center point.
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        # Check if the element’s center lies within the device screen
        # and that it has non-empty text.
        if 0 <= center_x < self.screen_width and 0 <= center_y < self.screen_height:
            bounds_str = f"[{left},{top}][{right},{bottom}]"
            info = {
                "index": counter[0],
                "text": element.attrib.get("text", ""),
                "class": element.attrib.get("class", ""),
                "bounds": bounds_str,
            }
            self.temp_ele_list.append(info)
            counter[0] += 1
        # Recurse into the element's children.
        for child in list(element):
            self.search_elements(child, counter, filters)

    def get_display_elements(self, filters=None):
        page_source = self.driver.page_source
        root = ET.fromstring(page_source)
        counter = [0]
        self.search_elements(root, counter, filters)
        return self.temp_ele_list

    def click_element(self, index: int):
        element_data = next((el for el in self.temp_ele_list if el["index"] == index), None)
        if element_data is None:
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

        # Move the pointer to the calculated location.
        self.actions.pointer_action.move_to_location(center_x, center_y)
        self.actions.pointer_action.pointer_down()
        self.actions.pointer_action.pause(0.1)  # Pause briefly to simulate touch
        self.actions.pointer_action.pointer_up()

        # Execute the action.
        self.actions.perform()
        self.temp_ele_list.clear()
        return {"clicked_index": index, "clicked_text": selected_text}

    def edit_any_textbox(self, text: str):
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
            edit_box.send_keys(text)
            print("New text entered into the textbox:", text)
            return {"status": "success", "new_text": text}
        except Exception as e:
            print("An error occurred while editing the textbox:", e)
            return {"status": "error", "error": str(e)}

    def end_driver(self):
        self.driver.quit()

    def go_back(self):
        self.driver.back()

    def swipe(self, start_x, start_y, end_x, end_y, duration=800):
        """
        Perform a swipe gesture from (start_x, start_y) to (end_x, end_y).
        Duration is in milliseconds.
        """
        self.actions.pointer_action.move_to_location(start_x, start_y)
        self.actions.pointer_action.pointer_down()
        self.actions.pointer_action.pause(duration / 1000)
        self.actions.pointer_action.move_to_location(end_x, end_y)
        self.actions.pointer_action.pointer_up()
        self.actions.perform()

    def scroll_down(self):
        start_x = self.screen_width // 2
        start_y = self.screen_height // 2
        end_y = int(self.screen_height * (0.1 / 2))
        self.swipe(start_x, start_y, start_x, end_y)

    def scroll_up(self):
        start_x = self.screen_width // 2
        start_y = self.screen_height // 2
        end_y = int(self.screen_height * (1 - (1 - 0.8) / 2))
        self.swipe(start_x, start_y, start_x, end_y)

    def open_app(self, app: str):
        self.driver.activate_app(app)
        self.current_app = app

    def get_apps(self):
        output = self.driver.execute_script("mobile: shell",
                                            {"command": "pm", "args": ["list", "packages", "-3"]}).splitlines()
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

    def screenshot(self):
        return self.driver.get_screenshot_as_png()
