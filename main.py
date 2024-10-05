import os
import sys
import time
import shutil
from datetime import datetime

# dotenv for environment variable management
from dotenv import load_dotenv

# Selenium WebDriver imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Selenium support imports
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

# Logging
import logging

# Mailing
import smtplib

# Timeout duration for Selenium wait operations (in seconds)
TIMEOUT: int = 15

# Path to locally installed chromedriver
PATH_TO_CHROMEDRIVER: str = '/usr/bin/chromedriver' # If webdriver-manager doesn't work on your system install chromedriver manually and change this path


# Sets up the Chrome WebDriver with custom options and preferences
def setup_webdriver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    # options.add_experimental_option("detach", True)  # keep browser open
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-search-engine-choice-screen")
    preferences = {"credentials_enable_service": False,
                   "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", preferences)
    options.add_argument("--mute-audio")

    if HEADLESS:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--window-position=-2400,-2400")  # temporarily

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        logger.error(f"Failed to setup WebDriver: {e}")

        wdm_directory = None
        if sys.platform.startswith('linux'):
            wdm_directory = os.path.expanduser('~/.wdm')
        elif sys.platform.startswith('win'):
            wdm_directory = os.path.join(os.getenv('USERPROFILE'), '.wdm')
        else:
            logger.error("Unsupported OS, unable to remove .wdm directory.")

        # Remove the entire .wdm directory if it exists
        if wdm_directory and os.path.exists(wdm_directory):
            shutil.rmtree(wdm_directory)
            logger.info(f"Removed the entire .wdm (webdriver-manager) directory: {wdm_directory}")

        service = ChromeService(PATH_TO_CHROMEDRIVER)
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Using the local ChromeDriver.")

    logger.info(f"WebDriver setup completed successfully with headless mode: {'--headless' in options.arguments}")
    return driver


# Executes a click event using JavaScript on a given WebElement
def click_js(driver: webdriver.Chrome, btn: WebElement) -> None:
    try:
        driver.execute_script("arguments[0].click();", btn)
    except Exception as e:
        logger.error(f"JavaScript click failed: {e.__class__.__name__} {e}", exc_info=True)
        sys.exit(1)


# Waits for an element to be clickable within a given timeout period
def wait_for_element(driver: webdriver.Chrome, by: str, element_identifier: str, timeout: int, error_txt: str = "") -> WebElement:
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, element_identifier)))
        return element
    except TimeoutException:
        logger.error(f"TimeoutException - Couldn't find element with {by}: {element_identifier} {error_txt}", exc_info=True)
        sys.exit(1)


# Converts a string representation of a boolean value to an actual boolean
def str2bool(s: str) -> bool:
    return s.lower() in ("yes", "true", "t", "1")


# Accepts cookies by clicking the corresponding button on the webpage
def accept_cookies(driver: webdriver.Chrome) -> None:
    accept_cookies_btn = wait_for_element(driver, By.ID, 'onetrust-accept-btn-handler', TIMEOUT)
    click_js(driver, accept_cookies_btn)
    logger.info("Cookies accepted successfully")


# Automates the login process on the Spotify website
def login(driver: webdriver.Chrome) -> None:
    login_btn1 = wait_for_element(driver, By.XPATH, '//*[@data-testid="login-button"]', TIMEOUT, "(login 1/4)")
    click_js(driver, login_btn1)

    username_input = wait_for_element(driver, By.XPATH, '//*[@data-testid="login-username"]', TIMEOUT, "(login 2/4)")
    username_input.send_keys(LOGIN_USERNAME)

    password_input = wait_for_element(driver, By.XPATH, '//*[@data-testid="login-password"]', TIMEOUT, "(login 3/4)")
    password_input.send_keys(LOGIN_PASSWORD)

    login_btn2 = wait_for_element(driver, By.XPATH, '//*[@data-testid="login-button"]', TIMEOUT, "(login 4/4)")
    click_js(driver, login_btn2)
    logger.info("Logged to Spotify successfully")


# Changes the website language to English
def change_language(driver: webdriver.Chrome) -> None:
    select_language = wait_for_element(driver, By.ID, 'desktop.settings.selectLanguage', TIMEOUT)
    select = Select(select_language)
    select.select_by_value("en-GB")
    logger.info("Changed language to english successfully")
    driver.refresh()


# Sets the shuffle state of the playlist based on the new_state parameter
def set_shuffle(driver: webdriver.Chrome, new_state: bool) -> None:
    shuffle_btn = wait_for_element(driver, By.XPATH, '//*[@data-testid="control-button-shuffle"]', TIMEOUT)
    current_state = shuffle_btn.get_attribute('aria-checked')
    if new_state != str2bool(current_state):
        click_js(driver, shuffle_btn)


# Retrieves the current playing state (playing or paused)
def get_playing_state(driver: webdriver.Chrome) -> bool:
    play_pause_btn = wait_for_element(driver, By.XPATH, '//*[@data-testid="control-button-playpause"]', TIMEOUT)
    return play_pause_btn.get_attribute('aria-label') == "Pause"


# Toggles the play/pause state of the Spotify playlist.
def play_pause(driver: webdriver.Chrome) -> None:
    play_pause_btn = wait_for_element(driver, By.XPATH, '//div[@data-testid="action-bar-row"]//button[@data-testid="play-button"]', TIMEOUT)
    click_js(driver, play_pause_btn)


# Checks if Spotify is being played on another device
def other_device(driver: webdriver.Chrome) -> bool:
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//div/button/span[contains(., "Playing on")]')))
        return True
    except TimeoutException:
        return False


if __name__ == '__main__':
    web_driver = None
    logger = None
    SENDER_EMAIL: str | None = None
    RECEIVER_EMAIL: str | None = None
    APP_PASSWORD: str | None = None
    try:

        # Setup logging
        logger = logging.getLogger("SpitifyBot_Logger")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        # Load environment variables
        load_dotenv()
        PLAYLIST_LINK: str = os.getenv("PLAYLIST_LINK")
        LOGIN_USERNAME: str = os.getenv("LOGIN_USERNAME")
        LOGIN_PASSWORD: str = os.getenv("LOGIN_PASSWORD")
        START_HOUR: int = int(os.getenv("START_HOUR"))
        END_HOUR: int = int(os.getenv("END_HOUR"))
        SHUFFLE: bool = str2bool(os.getenv("SHUFFLE"))
        HEADLESS: bool = str2bool(os.getenv("HEADLESS"))
        SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
        APP_PASSWORD = os.getenv("APP_PASSWORD")

        # Set up WebDriver
        web_driver = setup_webdriver()

        # Validate  environment variables
        if None in [PLAYLIST_LINK, LOGIN_USERNAME, LOGIN_PASSWORD, START_HOUR, END_HOUR, SHUFFLE, HEADLESS, SENDER_EMAIL, RECEIVER_EMAIL, APP_PASSWORD]:
            logger.error(f"Environment variables are not correctly defined in file .env, closing SpotiBot")
            sys.exit(1)

        # Automate Spotify
        web_driver.get("https://open.spotify.com/preferences")
        accept_cookies(web_driver)
        change_language(web_driver)
        login(web_driver)
        time.sleep(10)
        web_driver.get(PLAYLIST_LINK)
        time.sleep(10)

        while True:
            current_playing_state = get_playing_state(web_driver)
            if START_HOUR <= datetime.now().hour <= END_HOUR:
                if not other_device(web_driver) and not current_playing_state:
                    play_pause(web_driver)
                    set_shuffle(web_driver, SHUFFLE)
                    logger.info("Started to play the playlist")
                time.sleep(60)  # 300
            else:
                if not other_device(web_driver) and current_playing_state:
                    play_pause(web_driver)
                    logger.info("Stopped playing")
                time.sleep(900)

    except KeyboardInterrupt:
        if logger is not None:
            logger.warning(f"KeyboardInterrupt: Closing SpotiBot")
    except Exception as e:
        if logger is not None:
            logger.error(f"{e.__class__.__name__}: {e}", exc_info=True)

        # Send an email notification if the bot crashes
        if None not in [SENDER_EMAIL, RECEIVER_EMAIL, APP_PASSWORD]:
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(SENDER_EMAIL, APP_PASSWORD)
            smtp_server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, f"Subject: SpotiBot went down!\n\n{e.__class__.__name__}: {e}")
    finally:
        if web_driver is not None:
            web_driver.quit()
