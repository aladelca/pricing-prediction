from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory


def fetch_search_page_html(url: str, timeout: float) -> str:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("Selenium is not installed.") from exc

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,2400")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(int(timeout * 2))

    try:
        driver.get(url)
        _dismiss_cookie_banner(driver, timeout=timeout)
        WebDriverWait(driver, timeout).until(
            lambda current_driver: "__NEXT_DATA__" in current_driver.page_source
        )
        return driver.page_source
    except Exception as exc:  # pragma: no cover - browser fallback is runtime only
        with TemporaryDirectory(prefix="falabella-fallback-") as tmp_dir:
            _save_debug_bundle(driver, Path(tmp_dir))
        raise RuntimeError(f"Browser fallback failed for {url}") from exc
    finally:
        driver.quit()


def _dismiss_cookie_banner(driver: object, timeout: float) -> None:
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    locators = (
        (By.XPATH, "//button[normalize-space()='Aceptar']"),
        (By.XPATH, "//button[contains(., 'Aceptar')]"),
    )
    for locator in locators:
        try:
            button = WebDriverWait(driver, timeout).until(ec.element_to_be_clickable(locator))
        except TimeoutException:
            continue
        button.click()
        return


def _save_debug_bundle(driver: object, debug_dir: Path) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = debug_dir / "fallback.png"
    html_path = debug_dir / "fallback.html"
    driver.save_screenshot(str(screenshot_path))
    html_path.write_text(driver.page_source)
