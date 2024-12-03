## NODEPAY NETWORK BOT

## Description
This script automates network or node operations for Nodepay Network.

## Features

- **Automated Get Token**
- **Automated node interaction**
- **Automated Scrape Token**
- **Multi-account session**
- **Proxy and non-proxy support**

## Prerequisites
- [Python](https://www.python.org/) (version 3.7 or higher)

## Installation

1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com/Rambeboy/nodepay-airdrop-bot.git
   ```
2. Navigate to the project directory:
   ```bash
   cd nodepay-airdrop-bot
   ```
4. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### RUN AUTO SCRAPE TOKEN

1. Enter your email and password in the `accounts.txt` folder.

   ```bash
   nano accounts.txt
   ```
3. Run bot auto scrape token:
   ```bash
   python main-autoscrape-token.py
   ```
   or
   ```bash
   python get-token.py
   ```
   
5. Your token will automatically be saved in the `token.txt` folder.

## Usage

1. Register nodepay account first, if you dont have you can register [here](https://app.nodepay.ai/register), I recomended to `download extension`, `activate your account`, complete the `Proof of Humanhood` and `connect your wallet` first before running the script because this important for `Nodepay TGE`.
2. Set and Modify `user.txt` before running the script. Below how to setup this file, put your np_token in the text file, example below:
   ```
   eyJhbGcixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   eyJ23wixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
To get your token, follow this step:
- Login to your grass account in https://app.nodepay.ai/dashboard, make sure you is in this link before go to next step
- Go to inspect element, press F12 or right-click then pick inspect element in your browser
- Go to application tab - look for Local Storage in storage list -> click `https://app.nodepay.ai` and you will see your np_token.
- or you can go Console tab and paste This.
  ```bash
  localStorage.getItem('np_token')
  ```
3. If you want to use proxy, edit the `proxy.txt` with your proxy.

   ```
   ip:port
   username:password@ip:port
   http://ip:port
   http://username:password@ip:port
   socks5://ip:port
   socks5://username:password@ip:port
   ```

5. Run the script:
	```bash
	python main.py
	```
6. When running the script, answer if you want to use proxy and how much proxy you want to use, it will look like this:
   ```
   Do you want to use proxies? (y/n):
   ```

   ```
   How many proxies per account do you want to use?:
   ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Note
This script only for testing purpose, using this script might violates ToS and may get your account permanently banned.
