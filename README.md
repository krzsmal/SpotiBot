# SpotiBot: Spotify stats booster

## Overview

SpotiBot is designed to boost Spotify statistics, such as the total number of minutes listened, favorite artists, and favorite songs, which are featured in the annual Spotify Wrapped summary. 
The program plays music during a user-defined time period each day to maintain a natural listening pattern.
It also detects when music is being played on other devices, such as a phone, and pauses its own playback to avoid interference.
SpotiBot resumes playback only when the user has finished listening on the other device, ensuring a seamless experience.
The bot also includes robust error handling, logging any issues encountered during operation, and sending an email notification if a critical error causes the program to stop. 
This ensures that any interruptions in playback are promptly communicated for quick resolution.

I personally use SpotiBot to boost my Spotify Wrapped stats, running it continuously and autonomously on a Raspberry Pi 5.
## Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/krzsmal/spotibot.git
   cd spotibot
   ```

2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root directory with the following content:
   ```env
   PLAYLIST_LINK=<Spotify Playlist Link>
   LOGIN_USERNAME=<Spotify Username>
   LOGIN_PASSWORD=<Spotify Password>
   START_HOUR=<Playback Start Hour (0-23)>
   END_HOUR=<Playback End Hour (0-23)>
   SHUFFLE=<true/false>
   HEADLESS=<true/false>
   SENDER_EMAIL=<Your Email for Notifications>
   RECEIVER_EMAIL=<Email to Receive Notifications>
   APP_PASSWORD=<App Password for Sender Email>
   ```
   You can get your app password here: https://myaccount.google.com/apppasswords, but you need to have two-step verification enabled.
## Usage

To run the script, simply execute:

```sh
python spotibot.py
```

The bot will run continuously and control playback according to the specified schedule. To stop the program, press `Ctrl+Z`.

## License

This project is open-source under the MIT License.

## Acknowledgment

- [Selenium WebDriver](https://www.selenium.dev/) - For web automation and controlling browser interactions.
- [ChromeDriver Manager](https://github.com/SergeyPirogov/webdriver_manager) - For automatically managing the ChromeDriver installation.
- [dotenv](https://github.com/theskumar/python-dotenv) - For managing environment variables easily.
- [Python](https://www.python.org/) - The programming language used to develop this bot.

## Disclaimer

This project is intended for educational purposes. Automating interactions with Spotify may violate their terms of service. Use this project responsibly and at your own risk.
