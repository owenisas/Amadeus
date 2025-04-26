from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import time
from ML.data import log_click_csv
import xml.etree.ElementTree as ET
import re
Captcha = "Captcha"

# Set desired capabilities
capabilities = {
    'platformName': 'Android',
    'automationName': 'uiautomator2',
    'deviceName': 'Android',
}
driver = webdriver.Remote('http://localhost:4723', options=UiAutomator2Options().load_capabilities(capabilities))

window_size = driver.get_window_size()
screen_width = window_size["width"]
screen_height = window_size["height"]
def parse_bounds(bounds_str):
    """
    Parses a bounds string formatted as "[left,top][right,bottom]".
    Returns a tuple: (left, top, right, bottom), or (0,0,0,0) if parsing fails.
    """
    matches = re.findall(r'\d+', bounds_str)
    if len(matches) >= 4:
        return map(int, matches[:4])
    return (0, 0, 0, 0)


def get_truly_visible_elements():
    # Retrieve and parse the dynamic page source as an XML.
    dynamic_page_source = driver.page_source
    root = ET.fromstring(dynamic_page_source)

    visible_elems = []
    counter = [0]  # Using a mutable counter to assign an index to each element.

    # Start the recursive search from the root of the XML tree.
    search_elements_xml(root, counter, screen_width, screen_height, visible_elems)
    return visible_elems
def search_elements_xml(element, counter, screen_width, screen_height, visible_elems):
    # Get the element text from the attribute, and trim any whitespace.
    element_text = element.attrib.get("text", "").strip()

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

    # Recurse into the element's children.
    for child in list(element):
        search_elements_xml(child, counter, screen_width, screen_height, visible_elems)

# Connect to Appium server
time.sleep(2)  # wait for the app to load

while True:
    time.sleep(2)
    elements = get_truly_visible_elements()
    # Display each element's text with its index
    print("Elements found in the current view:")
    for idx, el in enumerate(elements):
        print(f"{idx}: {el['text']}")

    # Prompt the user to select an element by index
    selected_index = int(input("Enter the index of the element to tap: "))
    selected_element = elements[selected_index]
    print("You selected:", selected_element.text)

    # Click the selected element
    try:
        selected_element.click()
    except Exception:
        log_click_csv(app_name="com.android.chrome", task="Check Stock Price", element=selected_element, outcome=
        "failure")
    print("Element clicked!")
    # Clean up by quitting the driver session
    time.sleep(1)
    log_click_csv(app_name="com.android.chrome", task="Check Stock Price", element=selected_element, outcome="success")
