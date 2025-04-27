import re
import xml.etree.ElementTree as ET        # :contentReference[oaicite:10]{index=10}
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
interactive_classes = [
    "android.widget.Button",         # A push-button widget users can tap or click to perform an action :contentReference[oaicite:1]{index=1}
    "android.widget.EditText",       # A text entry field that allows users to input and modify text :contentReference[oaicite:2]{index=2}
    "android.widget.CheckBox",       # A specific two-state button for selecting one or more options :contentReference[oaicite:3]{index=3}
    "android.widget.RadioButton",    # A two-state button for mutually exclusive selections in a RadioGroup :contentReference[oaicite:4]{index=4}
    "android.widget.Spinner",        # A dropdown menu widget for selecting a single item from a set :contentReference[oaicite:5]{index=5}
    "android.widget.SeekBar",        # A draggable slider widget for selecting a value within a range :contentReference[oaicite:6]{index=6}
    "android.widget.RatingBar",      # A star-based rating widget, extension of SeekBar/ProgressBar :contentReference[oaicite:7]{index=7}
    "android.widget.Switch",         # A two-state toggle widget for on/off settings :contentReference[oaicite:8]{index=8}
    "android.widget.ToggleButton",   # A button that displays checked/unchecked states with an indicator light :contentReference[oaicite:9]{index=9}
    "android.webkit.WebView",
    "android.widget.TextView",
    "android.view.View",
    "android.widget.ImageButton",
    "android.widget.EditText",
    "android.widget.ImageView"
]
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
def annotate_from_files(driver, out_path: str):
    # 1. Load XML
    root = ET.fromstring(driver.page_source)

    # 2. Extract bounds
    boxes = []
    for elem in root.iter():
        element_class = elem.attrib.get("class", "")
        if element_class in interactive_classes:
            bounds = elem.attrib.get('bounds')
            if bounds:
                nums = list(map(int, re.findall(r'\d+', bounds)))  # :contentReference[oaicite:12]{index=12}
                x1, y1, x2, y2 = nums
                boxes.append((x1, y1, x2, y2))

    # 3. Open screenshot
    font = ImageFont.truetype("arial.ttf", size=20)  # load a 20-pt Arial font :contentReference[oaicite:3]{index=3}
    img = Image.open(BytesIO(driver.get_screenshot_as_png()))
    draw = ImageDraw.Draw(img)

    for idx, (x1, y1, x2, y2) in enumerate(boxes, start=1):
        # Draw the box
        draw.rectangle((x1, y1, x2, y2), outline='orange', width=4)  # :contentReference[oaicite:4]{index=4}
        # Draw the index number just above the box
        text_pos = (x1, max(0, y1 - 20))  # 20px above y1, not below 0 :contentReference[oaicite:5]{index=5}
        draw.text(text_pos, str(idx), font=font, fill='orange')
        # 5. Save result
    img.save(out_path)

# Usage
annotate_from_files(
    driver=driver,
    out_path='annotated_screenshot.png'
)
