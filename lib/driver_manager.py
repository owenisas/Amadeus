import json
from appium import webdriver
from appium.options.android import UiAutomator2Options


def create_driver(config: dict):
    capabilities = config.get("appium", {})
    options = UiAutomator2Options().load_capabilities(capabilities)
    driver = webdriver.Remote('http://localhost:4723', options=options)
    return driver
