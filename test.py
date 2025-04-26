from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

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

driver = webdriver.Remote(
    'http://localhost:4723',
    options=UiAutomator2Options().load_capabilities(capabilities)
)


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


# Containers for questions and answer options


window_size = driver.get_window_size()
width = window_size["width"]
height = window_size["height"]


def scroll_up(percentage=0.8):
    """
    Scroll up by a given percentage of the screen.
    """
    start_x = width // 2
    start_y = height // 2
    end_y = int(height * (1 - (1 - percentage) / 2))
    swipe(start_x, start_y, start_x, end_y)


def scroll_down():
    """
        Scroll down by a given percentage of the screen.
        Default scrolls 80% of screen height.
        """
    start_x = width // 2
    start_y = height // 2
    end_y = int(height * (0.1 / 2))
    swipe(start_x, start_y, start_x, end_y)


scroll_down()
