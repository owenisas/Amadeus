import re
import xml.etree.ElementTree as ET
import base64
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput


class UIInteraction:
    def __init__(self, driver, filters):
        self.driver = driver
        self.filters = filters
        self.temp_elements = []

    def parse_bounds(self, bounds_str: str):
        matches = re.findall(r'\d+', bounds_str)
        if len(matches) >= 4:
            return tuple(map(int, matches[:4]))
        return (0, 0, 0, 0)

    def _search_elements_xml(self, element, counter, visible_elems):
        element_text = element.attrib.get("text", "").strip()
        # Skip elements whose text is in filters.
        if element_text in self.filters:
            for child in list(element):
                self._search_elements_xml(child, counter, visible_elems)
            return

        bounds_attr = element.attrib.get("bounds", "")
        left, top, right, bottom = self.parse_bounds(bounds_attr)
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        window_size = self.driver.get_window_size()
        screen_width = window_size["width"]
        screen_height = window_size["height"]

        if 0 <= center_x < screen_width and 0 <= center_y < screen_height:
            bounds_str = f"[{left},{top}][{right},{bottom}]"
            visible_elems.append({
                "index": counter[0],
                "text": element.attrib.get("text", ""),
                "class": element.attrib.get("class", ""),
                "bounds": bounds_str
            })
            counter[0] += 1

        for child in list(element):
            self._search_elements_xml(child, counter, visible_elems)

    def get_truly_visible_elements(self):
        source = self.driver.page_source
        root = ET.fromstring(source)
        visible_elems = []
        counter = [0]
        self._search_elements_xml(root, counter, visible_elems)
        self.temp_elements = visible_elems
        return visible_elems

    def click_element(self, index: int):
        element_data = next((el for el in self.temp_elements if el["index"] == index), None)
        if not element_data:
            return {"status": "failure", "message": f"Element with index {index} not found."}

        bounds_str = element_data.get("bounds", "")
        matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
        if len(matches) < 2:
            return {"status": "failure", "message": f"Invalid bounds format for element index {index}."}

        (x1, y1), (x2, y2) = map(lambda tup: (int(tup[0]), int(tup[1])), matches)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        touch_input = PointerInput("touch", "touch")
        actions = ActionBuilder(self.driver, mouse=touch_input)
        actions.pointer_action.move_to_location(center_x, center_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()
        self.temp_elements = []  # Clear after click.
        return {"clicked_index": index, "clicked_text": element_data.get("text", "")}

    def screenshot_to_data_url(self, mime_type: str = "image/png"):
        screenshot_bytes = self.driver.get_screenshot_as_png()
        base64_encoded = base64.b64encode(screenshot_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{base64_encoded}"
