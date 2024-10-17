import os
import sys
import time
import shutil
import pickle
from datetime import datetime

# dotenv for environment variable management
from dotenv import load_dotenv

# Selenium WebDriver imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
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
PATH_TO_CHROMEDRIVER: str = '/usr/bin/chromedriver'  # If webdriver-manager doesn't work on your system install chromedriver manually and change this path


class SpotiBot:
    def __init__(self):
        self.driver: WebDriver | None = None
        self.playlist_play_pause_btn: WebElement | None = None
        self.play_pause_btn: WebElement | None = None
        self.skip_btn: WebElement | None = None
        self.use_local_chromedriver: bool = False

        # Load environment variables
        load_dotenv()
        self.PLAYLIST_LINK = os.getenv("PLAYLIST_LINK")
        self.LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
        self.LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")
        self.START_HOUR = int(os.getenv("START_HOUR"))
        self.END_HOUR = int(os.getenv("END_HOUR"))
        self.SHUFFLE = self.string_to_bool(os.getenv("SHUFFLE"))
        self.HEADLESS = self.string_to_bool(os.getenv("HEADLESS"))
        self.SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        self.RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
        self.APP_PASSWORD = os.getenv("APP_PASSWORD")

        # Setup logging
        self.logger = logging.getLogger("SpotiBot_Logger")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

        # Validate  environment variables
        if None in [self.PLAYLIST_LINK, self.LOGIN_USERNAME, self.LOGIN_PASSWORD, self.START_HOUR, self.END_HOUR,
                    self.SHUFFLE, self.HEADLESS, self.SENDER_EMAIL, self.RECEIVER_EMAIL, self.APP_PASSWORD]:
            self.logger.error(f"Environment variables are missing or improperly configured in the .env file. Shutting down SpotiBot.")
            sys.exit(1)

        self.logger.info("SpotiBot initialization completed successfully.")

    # Converts string to boolean value
    @staticmethod
    def string_to_bool(s: str) -> bool:
        return s.lower() in {"yes", "true", "t", "1"}

    # Sets up local Chrome WebDriver with custom options and preferences
    def initialize_local_webdriver(self, options: ChromeOptions) -> None:
        try:
            service = ChromeService(PATH_TO_CHROMEDRIVER)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("Using the local ChromeDriver.")
        except:
            self.logger.error("Failed to initialize the local WebDriver. Change the PATH_TO_CHROMEDRIVER variable or install chromedriver manually if it is not already installed.")
            sys.exit(1)

    # Sets up the Chrome WebDriver with custom options and preferences
    def initialize_webdriver(self) -> None:
        options = webdriver.ChromeOptions()
        # options.add_experimental_option("detach", True)  # keep browser open
        preferences = {"credentials_enable_service": False,
                       "profile.password_manager_enabled": False}
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("prefs", preferences)
        flags = [
            "--disable-search-engine-choice-screen",
            "--mute-audio",
            "--autoplay-policy=no-user-gesture-required",
            "--no-sandbox",
            "--blink-settings=imagesEnabled=false",
            "--disable-extensions",
            "--disable-webgl",
            "--disable-dev-shm-usage",
            "--disable-client-side-phishing-detection",
            "--disable-crash-reporter",
            "--disable-gpu",
            "--silent",
            "--disable-infobars",
        ]
        for flag in flags:
            options.add_argument(flag)

        if self.HEADLESS:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=800,600")
            options.add_argument("--window-position=-2400,-2400")

        if self.use_local_chromedriver:
            self.initialize_local_webdriver(options)
        else:
            try:
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except:
                self.use_local_chromedriver = True
                self.logger.error(f"Failed to initialize the WebDriver using webdriver-manager.")

                wdm_directory = None
                if sys.platform.startswith('linux'):
                    wdm_directory = os.path.expanduser('~/.wdm')
                elif sys.platform.startswith('win'):
                    wdm_directory = os.path.join(os.getenv('USERPROFILE'), '.wdm')
                else:
                    self.logger.error("Unsupported OS, unable to remove .wdm directory.")

                # Remove the entire .wdm directory if it exists
                if wdm_directory and os.path.exists(wdm_directory):
                    shutil.rmtree(wdm_directory)
                    self.logger.info(f"Removed the entire .wdm (webdriver-manager) directory: {wdm_directory}")

                self.initialize_local_webdriver(options)

        self.logger.info(f"WebDriver setup completed successfully with headless mode: {'--headless' in options.arguments}")

    # Executes a click event using JavaScript on a given WebElement
    def click_element_with_js(self, btn: WebElement) -> None:
        try:
            self.driver.execute_script("arguments[0].click();", btn)
        except Exception as e:
            self.logger.error(f"JavaScript click failed: {e.__class__.__name__} {e}", exc_info=True)
            sys.exit(1)

    # Waits for an element to be clickable within a given timeout period
    def wait_for_element(self, by: str, element_identifier: str, timeout: int, error_txt: str = "") -> WebElement:
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, element_identifier)))
            return element
        except TimeoutException:
            self.logger.error(f"TimeoutException - Couldn't find element with {by}: {element_identifier} {error_txt}", exc_info=True)
            sys.exit(1)

    # Accepts cookies by clicking the corresponding button on the webpage
    def accept_cookies(self) -> None:
        accept_cookies_btn = self.wait_for_element(By.ID, 'onetrust-accept-btn-handler', TIMEOUT)
        self.click_element_with_js(accept_cookies_btn)
        self.logger.info("Cookies have been successfully accepted.")

    # Automates the login process on the Spotify website
    def login(self) -> None:
        login_btn1 = self.wait_for_element(By.XPATH, '//*[@data-testid="login-button"]', TIMEOUT, "(login 1/4)")
        self.click_element_with_js(login_btn1)

        username_input = self.wait_for_element(By.XPATH, '//*[@data-testid="login-username"]', TIMEOUT, "(login 2/4)")
        username_input.send_keys(self.LOGIN_USERNAME)

        password_input = self.wait_for_element(By.XPATH, '//*[@data-testid="login-password"]', TIMEOUT, "(login 3/4)")
        password_input.send_keys(self.LOGIN_PASSWORD)

        login_btn2 = self.wait_for_element(By.XPATH, '//*[@data-testid="login-button"]', TIMEOUT, "(login 4/4)")
        self.click_element_with_js(login_btn2)
        self.logger.info("Successfully logged into the Spotify account.")

    # Changes the website language to English
    def set_language_to_english(self) -> None:
        select_language = self.wait_for_element(By.ID, 'desktop.settings.selectLanguage', TIMEOUT)
        select = Select(select_language)
        select.select_by_value("en-GB")
        self.logger.info("Language preference has been set to English.")
        self.driver.refresh()

    # Toggles the shuffle button
    def toggle_shuffle(self) -> None:
        shuffle_btn = self.wait_for_element(By.XPATH, '//*[@data-testid="control-button-shuffle"]', TIMEOUT)
        current_state = shuffle_btn.get_attribute('aria-checked')
        if self.SHUFFLE != self.string_to_bool(current_state):
            self.click_element_with_js(shuffle_btn)
            try:
                WebDriverWait(self.driver, 10).until(lambda driver: self.SHUFFLE == self.string_to_bool(shuffle_btn.get_attribute('aria-checked')))
            except TimeoutException:
                pass

    # Checks if music is playing
    def is_music_playing(self) -> bool:
        return self.play_pause_btn.get_attribute('aria-label') == "Pause"

    # Toggles the play/pause state of the Spotify playlist
    def toggle_play_pause(self, play: bool) -> None:
        while self.is_music_playing() != play:
            self.click_element_with_js(self.playlist_play_pause_btn)
            if self.is_music_playing() != play:
                time.sleep(3)

    # Skips a song
    def skip_track(self) -> None:
        self.click_element_with_js(self.skip_btn)

    # Checks if Spotify is being played on another device
    def is_playing_on_another_device(self) -> bool:
        try:
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//div/button/span[contains(., "Playing on")]')))
            return True
        except TimeoutException:
            return False

    # Saves cookies to a file
    def save_cookies(self) -> None:
        cookies = self.driver.get_cookies()
        with open('cookies.pkl', 'wb') as file:
            pickle.dump(cookies, file)
        self.logger.info(f"Cookies have been saved to 'cookies.pkl'.")

    # Sets up the Spotify player
    def setup_spotify_player(self) -> None:
        self.driver.get("https://open.spotify.com/preferences")
        new_cookies = False
        if os.path.exists('cookies.pkl'):
            with open('cookies.pkl', 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            self.driver.refresh()

        time.sleep(10)
        if len(self.driver.find_elements(By.ID, 'onetrust-accept-btn-handler')) != 0:
            self.accept_cookies()
            new_cookies = True
        if self.driver.find_elements(By.ID, 'desktop.settings.selectLanguage')[0].get_attribute("value") != 'en-GB':
            self.set_language_to_english()
            new_cookies = True
        if len(self.driver.find_elements(By.XPATH, '//*[@data-testid="login-button"]')) != 0:
            self.login()
            new_cookies = True
        if new_cookies:
            time.sleep(10)
            self.save_cookies()
        else:
            self.logger.info(f"Cookies were successfully loaded from 'cookies.pkl'.")

        time.sleep(10)
        self.driver.get(self.PLAYLIST_LINK)
        time.sleep(10)
        self.playlist_play_pause_btn = self.wait_for_element(By.XPATH, '//div[@data-testid="action-bar-row"]//button[@data-testid="play-button"]', TIMEOUT)
        self.play_pause_btn = self.wait_for_element(By.XPATH, '//*[@data-testid="control-button-playpause"]', TIMEOUT)
        self.skip_btn = self.wait_for_element(By.XPATH, '//*[@data-testid="control-button-skip-forward"]', TIMEOUT)

    # Checks if WebDriver is active
    def is_driver_active(self):
        return self.driver and self.driver.service.is_connectable()

    # Main function
    def run(self):
        while True:
            within_active_hours = self.START_HOUR <= datetime.now().hour <= self.END_HOUR
            if within_active_hours:
                if not self.is_driver_active():
                    self.initialize_webdriver()
                    self.setup_spotify_player()

                if not self.is_playing_on_another_device() and not self.is_music_playing():
                    self.toggle_play_pause(True)
                    self.toggle_shuffle()
                    if self.SHUFFLE:
                        self.skip_track()
                    self.logger.info("Playback has started for the specified playlist.")

            elif self.is_driver_active():
                self.driver.quit()
                self.logger.info("Playback has stopped and the WebDriver instance has been closed.")

            time.sleep(60 if self.is_driver_active() else 300)


if __name__ == '__main__':
    bot = None
    try:
        bot = SpotiBot()
        bot.run()
    except KeyboardInterrupt:
        bot.logger.warning("KeyboardInterrupt: Shutting down SpotiBot.")
    except Exception as e:
        bot.logger.error(f"{e.__class__.__name__}: {e}", exc_info=True)
        if None not in [bot.SENDER_EMAIL, bot.RECEIVER_EMAIL, bot.APP_PASSWORD]:
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(bot.SENDER_EMAIL, bot.APP_PASSWORD)
            smtp_server.sendmail(bot.SENDER_EMAIL, bot.RECEIVER_EMAIL, f"Subject: SpotiBot went down!\n\n{e.__class__.__name__}: {e}")
    finally:
        if bot.is_driver_active():
            bot.driver.quit()
