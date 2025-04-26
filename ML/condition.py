import asyncio
from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import io
import time
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
