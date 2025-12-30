"""
Android device automation environment using Appium.
Provides comprehensive UI interaction capabilities for the AI agent.
"""

import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver import Keys
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

import xml.etree.ElementTree as ET
import re

from config import AppiumConfig, setup_android_environment

# Ensure Android SDK environment is set up
setup_android_environment()

# Common app name to package mappings
APP_PACKAGES = {
    "chrome": "com.android.chrome",
    "youtube": "com.google.android.youtube",
    "settings": "com.android.settings",
    "calendar": "com.google.android.calendar",
    "contacts": "com.google.android.contacts",
    "photos": "com.google.android.apps.photos",
    "play store": "com.android.vending",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "messages": "com.google.android.apps.messaging",
    "phone": "com.google.android.dialer",
    "camera": "com.android.camera",
    "clock": "com.google.android.deskclock",
    "files": "com.google.android.apps.nbu.files",
}

# Key code mappings
KEY_CODES = {
    "enter": 66,
    "back": 4,
    "home": 3,
    "recent_apps": 187,
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "delete": 67,
    "tab": 61,
}

# Scroll amount percentages
SCROLL_AMOUNTS = {
    "small": 0.25,
    "medium": 0.50,
    "large": 0.75,
    "full_page": 0.90,
}


def parse_bounds(bounds_str):
    """
    Parses a bounds string formatted as "[left,top][right,bottom]".
    Returns a tuple: (left, top, right, bottom), or (0,0,0,0) if parsing fails.
    """
    matches = re.findall(r'\d+', bounds_str)
    if len(matches) >= 4:
        return tuple(map(int, matches[:4]))
    return (0, 0, 0, 0)


class Android:
    """
    Android device automation class providing comprehensive UI interaction.
    Uses Appium with UiAutomator2 for reliable element detection and actions.
    """
    
    def __init__(self):
        # Use centralized config for capabilities
        self.capabilities = AppiumConfig.get_capabilities()
        self.driver = webdriver.Remote(
            AppiumConfig.SERVER_URL,
            options=UiAutomator2Options().load_capabilities(self.capabilities)
        )

        self.window_size = self.driver.get_window_size()
        self.screen_width = self.window_size["width"]
        self.screen_height = self.window_size["height"]
        self.elements_cache = []  # Renamed for clarity
        self.current_app = ''
        
    def _create_action_builder(self):
        """Create a fresh ActionBuilder for each action to avoid state issues."""
        return ActionBuilder(self.driver, mouse=PointerInput("touch", "touch"))
    
    def _get_element_center(self, bounds_str: str) -> tuple:
        """Parse bounds string and return center coordinates."""
        matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
        if len(matches) < 2:
            return None, None
        (x1, y1), (x2, y2) = map(lambda tup: (int(tup[0]), int(tup[1])), matches)
        return (x1 + x2) // 2, (y1 + y2) // 2

    def search_elements(self, element, counter, filters, include_all=False):
        """Recursively search and collect UI elements from the XML tree."""
        element_text = element.attrib.get("text", "").strip()
        element_class = element.attrib.get("class", "")
        content_desc = element.attrib.get("content-desc", "").strip()
        clickable = element.attrib.get("clickable", "false") == "true"
        focusable = element.attrib.get("focusable", "false") == "true"
        enabled = element.attrib.get("enabled", "true") == "true"
        resource_id = element.attrib.get("resource-id", "")

        # Apply filters
        filters = filters or {"filter": [], "class_filter": []}
        if element_text in filters.get("filter", []):
            for child in list(element):
                self.search_elements(child, counter, filters, include_all)
            return

        if element_class in filters.get("class_filter", []):
            for child in list(element):
                self.search_elements(child, counter, filters, include_all)
            return

        bounds_attr = element.attrib.get("bounds", "")
        left, top, right, bottom = parse_bounds(bounds_attr)
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        # Check if element is within screen bounds
        if 0 <= center_x < self.screen_width and 0 <= center_y < self.screen_height:
            # Determine if element should be included
            is_interactive = clickable or focusable or element_class.endswith("EditText")
            has_content = element_text or content_desc
            
            if include_all or (is_interactive and enabled) or has_content:
                bounds_str = f"[{left},{top}][{right},{bottom}]"
                info = {
                    "index": counter[0],
                    "text": element_text,
                    "class": element_class.split('.')[-1] if element_class else "",  # Short class name
                    "bounds": bounds_str,
                    "content_desc": content_desc,
                    "clickable": clickable,
                    "resource_id": resource_id.split('/')[-1] if resource_id else "",  # Short resource ID
                }
                # Remove empty values except index
                clean_info = {k: v for k, v in info.items() if v or k == "index"}
                self.elements_cache.append(clean_info)
                counter[0] += 1
                
        # Recurse into children
        for child in list(element):
            self.search_elements(child, counter, filters, include_all)

    # ==================== SCREEN ELEMENT FUNCTIONS ====================
    
    def get_screen_elements(self, filters=None, include_all=False):
        """
        Get all UI elements on the current screen.
        
        Args:
            filters: Optional filter configuration
            include_all: If True, include non-interactive elements
            
        Returns:
            List of element dictionaries with index, text, bounds, etc.
        """
        self.elements_cache = []
        try:
            page_source = self.driver.page_source
            root = ET.fromstring(page_source)
            counter = [0]
            self.search_elements(root, counter, filters, include_all)
            return {
                "status": "success",
                "element_count": len(self.elements_cache),
                "elements": self.elements_cache
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "elements": []}
    
    def get_device_info(self):
        """Get device and screen information."""
        try:
            current_package = self.driver.current_package
            current_activity = self.driver.current_activity
            return {
                "status": "success",
                "screen_width": self.screen_width,
                "screen_height": self.screen_height,
                "current_package": current_package,
                "current_activity": current_activity,
                "orientation": self.driver.orientation
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== TAP FUNCTIONS ====================
    
    def tap(self, index: int):
        """
        Tap on an element by its index from the elements cache.
        
        Args:
            index: Element index from get_screen_elements
        """
        element_data = next((el for el in self.elements_cache if el["index"] == index), None)
        if element_data is None:
            return {"status": "error", "message": f"Element with index {index} not found. Call get_screen_elements first."}

        bounds_str = element_data.get("bounds", "")
        center_x, center_y = self._get_element_center(bounds_str)
        
        if center_x is None:
            return {"status": "error", "message": f"Invalid bounds for element {index}"}

        return self.tap_coordinates(center_x, center_y, element_info=element_data)
    
    def tap_coordinates(self, x: int, y: int, element_info=None):
        """
        Tap at specific screen coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            element_info: Optional element info for logging
        """
        try:
            actions = self._create_action_builder()
            actions.pointer_action.move_to_location(x, y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.1)
            actions.pointer_action.pointer_up()
            actions.perform()
            
            result = {
                "status": "success",
                "action": "tap",
                "coordinates": {"x": x, "y": y}
            }
            if element_info:
                result["element_text"] = element_info.get("text", "")
                result["element_index"] = element_info.get("index")
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def double_tap(self, index: int = None, x: int = None, y: int = None):
        """
        Double tap on an element or coordinates.
        
        Args:
            index: Element index (optional)
            x, y: Coordinates (used if index not provided)
        """
        if index is not None:
            element_data = next((el for el in self.elements_cache if el["index"] == index), None)
            if element_data is None:
                return {"status": "error", "message": f"Element with index {index} not found"}
            bounds_str = element_data.get("bounds", "")
            x, y = self._get_element_center(bounds_str)
            
        if x is None or y is None:
            return {"status": "error", "message": "Either index or x/y coordinates required"}
        
        try:
            actions = self._create_action_builder()
            # First tap
            actions.pointer_action.move_to_location(x, y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pointer_up()
            actions.pointer_action.pause(0.05)
            # Second tap
            actions.pointer_action.pointer_down()
            actions.pointer_action.pointer_up()
            actions.perform()
            
            return {"status": "success", "action": "double_tap", "coordinates": {"x": x, "y": y}}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def long_press(self, index: int = None, x: int = None, y: int = None, duration_ms: int = 1000):
        """
        Long press on an element or coordinates.
        
        Args:
            index: Element index (optional)
            x, y: Coordinates (used if index not provided)
            duration_ms: Press duration in milliseconds
        """
        if index is not None:
            element_data = next((el for el in self.elements_cache if el["index"] == index), None)
            if element_data is None:
                return {"status": "error", "message": f"Element with index {index} not found"}
            bounds_str = element_data.get("bounds", "")
            x, y = self._get_element_center(bounds_str)
            
        if x is None or y is None:
            return {"status": "error", "message": "Either index or x/y coordinates required"}
        
        try:
            actions = self._create_action_builder()
            actions.pointer_action.move_to_location(x, y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(duration_ms / 1000)
            actions.pointer_action.pointer_up()
            actions.perform()
            
            return {"status": "success", "action": "long_press", "coordinates": {"x": x, "y": y}, "duration_ms": duration_ms}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== TEXT INPUT FUNCTIONS ====================
    
    def type_text(self, text: str, target_index: int = None, clear_first: bool = True, submit: bool = False):
        """
        Type text into a text field.
        
        Args:
            text: Text to type
            target_index: Index of specific text field (optional)
            clear_first: Whether to clear existing text first
            submit: Whether to press Enter after typing
        """
        try:
            edit_box = None
            
            # If target_index provided, tap on that element first
            if target_index is not None:
                element_data = next((el for el in self.elements_cache if el["index"] == target_index), None)
                if element_data:
                    bounds_str = element_data.get("bounds", "")
                    x, y = self._get_element_center(bounds_str)
                    if x and y:
                        self.tap_coordinates(x, y)
                        time.sleep(0.3)  # Wait for focus
            
            # Find text fields
            textboxes = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            if not textboxes:
                return {"status": "error", "message": "No text field found on screen"}
            
            # If we tapped a specific element, try to find the focused one
            if target_index is not None:
                for tb in textboxes:
                    if tb.get_attribute("focused") == "true":
                        edit_box = tb
                        break
            
            # Default to first textbox if no focused one found
            if edit_box is None:
                edit_box = textboxes[0]
            
            current_text = edit_box.text
            
            if clear_first:
                edit_box.clear()
                
            edit_box.click()
            edit_box.send_keys(text)
            
            result = {
                "status": "success",
                "action": "type_text",
                "previous_text": current_text,
                "new_text": text
            }
            
            if submit:
                self.press_key("enter")
                result["submitted"] = True
                
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== SCROLL & SWIPE FUNCTIONS ====================
    
    def scroll(self, direction: str, amount: str = "medium", start_x: int = None, start_y: int = None):
        """
        Scroll the screen in a direction with configurable amount.
        
        Args:
            direction: 'up', 'down', 'left', 'right'
            amount: 'small', 'medium', 'large', 'full_page'
            start_x, start_y: Optional starting point for the scroll
        """
        scroll_percent = SCROLL_AMOUNTS.get(amount, 0.5)
        
        # Default to center of screen
        if start_x is None:
            start_x = self.screen_width // 2
        if start_y is None:
            start_y = self.screen_height // 2
        
        # Calculate scroll distance
        scroll_distance_y = int(self.screen_height * scroll_percent)
        scroll_distance_x = int(self.screen_width * scroll_percent)
        
        # Calculate end coordinates based on direction
        end_x, end_y = start_x, start_y
        
        if direction == "down":
            # Swipe up to scroll down (reveal content below)
            start_y = int(self.screen_height * 0.7)
            end_y = start_y - scroll_distance_y
        elif direction == "up":
            # Swipe down to scroll up (reveal content above)
            start_y = int(self.screen_height * 0.3)
            end_y = start_y + scroll_distance_y
        elif direction == "left":
            # Swipe right to scroll left
            start_x = int(self.screen_width * 0.7)
            end_x = start_x - scroll_distance_x
        elif direction == "right":
            # Swipe left to scroll right
            start_x = int(self.screen_width * 0.3)
            end_x = start_x + scroll_distance_x
        else:
            return {"status": "error", "message": f"Invalid direction: {direction}"}
        
        return self.swipe(start_x, start_y, end_x, end_y)
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 500):
        """
        Perform a swipe gesture from one point to another.
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            duration_ms: Duration of swipe in milliseconds
        """
        try:
            actions = self._create_action_builder()
            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(duration_ms / 1000)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pointer_up()
            actions.perform()
            
            return {
                "status": "success",
                "action": "swipe",
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "duration_ms": duration_ms
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== KEY & NAVIGATION FUNCTIONS ====================
    
    def press_key(self, key: str):
        """
        Press a system key.
        
        Args:
            key: Key name ('enter', 'back', 'home', etc.)
        """
        key_code = KEY_CODES.get(key.lower())
        if key_code is None:
            return {"status": "error", "message": f"Unknown key: {key}. Valid keys: {list(KEY_CODES.keys())}"}
        
        try:
            self.driver.press_keycode(key_code)
            return {"status": "success", "action": "press_key", "key": key}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== APP FUNCTIONS ====================
    
    def open_app(self, app: str):
        """
        Open an application by package name or common name.
        
        Args:
            app: Package name or common app name
        """
        # Check if it's a common name
        package = APP_PACKAGES.get(app.lower(), app)
        
        try:
            self.driver.activate_app(package)
            self.current_app = package
            time.sleep(1)  # Wait for app to open
            return {"status": "success", "action": "open_app", "package": package}
        except Exception as e:
            return {"status": "error", "message": f"Failed to open {app}: {str(e)}"}
    
    def get_installed_apps(self, include_system: bool = False):
        """
        Get list of installed applications.
        
        Args:
            include_system: Include system apps if True
        """
        try:
            if include_system:
                output = self.driver.execute_script("mobile: shell",
                    {"command": "pm", "args": ["list", "packages"]}).splitlines()
            else:
                output = self.driver.execute_script("mobile: shell",
                    {"command": "pm", "args": ["list", "packages", "-3"]}).splitlines()
                    
            packages = [pkg.replace("package:", "") for pkg in output]
            
            # Add common system apps that users often want
            if not include_system:
                system_apps = list(APP_PACKAGES.values())
                packages.extend([app for app in system_apps if app not in packages])
            
            return {
                "status": "success",
                "app_count": len(packages),
                "apps": sorted(packages)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== UTILITY FUNCTIONS ====================
    
    def wait(self, seconds: float = 1.0, reason: str = None):
        """
        Wait for a specified duration.
        
        Args:
            seconds: Duration to wait
            reason: Optional reason for logging
        """
        time.sleep(seconds)
        result = {"status": "success", "action": "wait", "seconds": seconds}
        if reason:
            result["reason"] = reason
        return result
    
    def screenshot(self):
        """Take a screenshot and return as PNG bytes."""
        return self.driver.get_screenshot_as_png()

    def end_driver(self):
        """Clean up and quit the driver."""
        self.driver.quit()

    # ==================== LEGACY COMPATIBILITY ====================
    # These methods maintain backward compatibility with old code
    
    def get_display_elements(self, filters=None):
        """Legacy method - use get_screen_elements instead."""
        result = self.get_screen_elements(filters=filters)
        return result.get("elements", [])
    
    def click_element(self, index: int):
        """Legacy method - use tap instead."""
        return self.tap(index)
    
    def edit_any_textbox(self, text: str):
        """Legacy method - use type_text instead."""
        return self.type_text(text, clear_first=True)
    
    def scroll_down(self):
        """Legacy method - use scroll(direction='down') instead."""
        return self.scroll("down", "medium")
    
    def scroll_up(self):
        """Legacy method - use scroll(direction='up') instead."""
        return self.scroll("up", "medium")
    
    def go_back(self):
        """Legacy method - use press_key('back') instead."""
        return self.press_key("back")
    
    def press_enter(self):
        """Legacy method - use press_key('enter') instead."""
        return self.press_key("enter")
    
    def get_apps(self):
        """Legacy method - use get_installed_apps instead."""
        result = self.get_installed_apps(include_system=False)
        return result.get("apps", [])


if __name__ == "__main__":
    # Test the Android environment
    test = Android()
    print("Device info:", test.get_device_info())
    print("Screen elements:", test.get_screen_elements())
    test.end_driver()
