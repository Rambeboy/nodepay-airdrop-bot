import asyncio
import cloudscraper
import json
import time
from loguru import logger
import requests
from colorama import Fore, Style, init

init(autoreset=True)

print("\n" + " " * 32 + f"{Fore.CYAN}NODEPAY NETWORK BOT{Style.RESET_ALL}")
print(" " * 32 + f"{Fore.GREEN}AUTHOR : NOFAN RAMBE{Style.RESET_ALL}")
print(" " * 32 + f"{Fore.CYAN}WELCOME & ENJOY SIR!{Style.RESET_ALL}" + "\n")

def truncate_token(token):
    return f"{token[:5]}--{token[-5:]}"

logger.remove()
logger.add(lambda msg: print(msg, end=''), format="{message}", level="INFO")

PING_INTERVAL = 60
RETRIES = 10
MISSION_INTERVAL = 12 * 3600

DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": [
        "https://nw.nodepay.org/api/network/ping"
    ],
    "MISSION": "https://api.nodepay.org/api/mission/complete-mission",
    "SURVEY_1": "https://api.nodepay.org/api/mission/survey/qna-challenge",
    "SURVEY_2": "https://api.nodepay.org/api/mission/survey/qna-challenge-2",
    "SURVEY_3": "https://api.nodepay.org/api/mission/survey/qna-challenge-3",
    "SURVEY_4": "https://api.nodepay.org/api/mission/survey/qna-challenge-4",
    "MEDAL_ALL": "https://api.nodepay.org/api/medal/all",
    "MEDAL_CLAIM": "https://api.nodepay.org/api/medal/claim"
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

class ApiEndpoints:
    BASE_URL = "https://api.nodepay.ai/api"

    @classmethod
    def get_url(cls, endpoint: str) -> str:
        return f"{cls.BASE_URL}/{endpoint}"

class Auth:
    REGISTER = "auth/register"
    LOGIN = "auth/login"
    ACTIVATE = "auth/active-account"

class AccountData:
    def __init__(self, token, proxies, index):
        self.token = token
        self.proxies = proxies
        self.index = index
        self.status_connect = CONNECTION_STATES["NONE_CONNECTION"]
        self.account_info = {}
        self.retries = 0
        self.last_ping_status = 'Waiting...'
        self.activation_failed = False
        self.last_mission_time = 0
        self.browser_ids = [
            {
                'ping_count': 0,
                'successful_pings': 0,
                'score': 0,
                'start_time': time.time(),
                'last_ping_time': None
            }
        ] if not proxies else [
            {
                'ping_count': 0,
                'successful_pings': 0,
                'score': 0,
                'start_time': time.time(),
                'last_ping_time': None
            } for _ in proxies
        ]

    def reset(self):
        self.status_connect = CONNECTION_STATES["NONE_CONNECTION"]
        self.account_info = {}
        self.retries = 3

async def retrieve_tokens():
    try:
        with open('user.txt', 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        raise SystemExit("Exiting due to failure in loading tokens")

async def retrieve_proxies():
    try:
        with open('proxy.txt', 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        raise SystemExit("Exiting due to failure in loading proxies")

async def execute_request(url, data, account, proxy=None, method='POST'):
    headers = {
        "Authorization": f"Bearer {account.token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://app.nodepay.ai/",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
        "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cors-site"
    }

    proxy_config = {"http": proxy, "https": proxy} if proxy else None

    try:
        if method == 'POST':
            response = scraper.post(url, json=data, headers=headers, proxies=proxy_config, timeout=60)
        else:
            response = scraper.get(url, headers=headers, proxies=proxy_config, timeout=60)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"{Fore.RED}Error during API call for token {truncate_token(account.token)} with proxy {proxy}: {e}{Style.RESET_ALL}")
        raise ValueError(f"Failed API call to {url}")

    return response.json()

async def activate_account(account, proxy=None):
    """
    Activate the account using the activation endpoint.
    """
    if account.activation_failed:
        logger.info(f"{Fore.YELLOW}Skipping activation for token {truncate_token(account.token)} as it previously failed.{Style.RESET_ALL}")
        return

    url = ApiEndpoints.get_url(Auth.ACTIVATE)
    data = {}

    try:
        response = await execute_request(url, data, account, proxy)
        if response.get("code") == 0:
            logger.info(f"{Fore.GREEN}Account activated successfully for token {truncate_token(account.token)}{Style.RESET_ALL}")
        else:
            logger.warning(f"{Fore.RED}Account activation failed for token {truncate_token(account.token)}: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
            account.activation_failed = True
    except Exception as e:
        logger.error(f"{Fore.RED}Failed to activate account for token {truncate_token(account.token)}: {e}{Style.RESET_ALL}")
        account.activation_failed = True

async def complete_mission(account, proxy=None):
    """
    Complete the daily login and quest mission.
    """
    current_time = time.time()
    if current_time - account.last_mission_time < MISSION_INTERVAL:
        logger.info(f"{Fore.YELLOW}Skipping mission for token {truncate_token(account.token)} as it was completed recently.{Style.RESET_ALL}")
        return

    url = DOMAIN_API["MISSION"]
    data = {"mission_id": "1"}

    try:
        response = await execute_request(url, data, account, proxy)
        if response.get("code") == 0:
            logger.info(f"{Fore.GREEN}Mission completed successfully for token {truncate_token(account.token)}{Style.RESET_ALL}")
            account.last_mission_time = current_time
        else:
            logger.warning(f"{Fore.RED}Mission completion failed for token {truncate_token(account.token)}: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Failed to complete mission for token {truncate_token(account.token)}: {e}{Style.RESET_ALL}")

async def start_ping(account, proxies, browser_ids):
    try:
        proxy_count = len(proxies) if proxies else 1
        proxy_index = 0

        proxy = proxies[proxy_index] if proxies else None
        browser_id = browser_ids[proxy_index] if proxies else browser_ids[0]

        logger.info(f"{Fore.CYAN}[{time.strftime('%H:%M:%S')}][{account.index}]{Style.RESET_ALL} Starting initial ping for token {Fore.CYAN}{truncate_token(account.token)}{Style.RESET_ALL} with proxy {proxy}")

        try:
            await perform_ping(account, proxy, browser_id)
        except Exception as e:
            logger.error(f"{Fore.RED}Initial ping failed for token {truncate_token(account.token)} using proxy {proxy}: {e}{Style.RESET_ALL}")

        while True:
            await asyncio.sleep(PING_INTERVAL)

            proxy = proxies[proxy_index] if proxies else None
            browser_id = browser_ids[proxy_index] if proxies else browser_ids[0]

            logger.info(f"{Fore.CYAN}[{time.strftime('%H:%M:%S')}][{account.index}]{Style.RESET_ALL} Starting ping for token {Fore.CYAN}{truncate_token(account.token)}{Style.RESET_ALL} with proxy {proxy}")

            try:
                await perform_ping(account, proxy, browser_id)
            except Exception as e:
                logger.error(f"{Fore.RED}Ping failed for token {truncate_token(account.token)} using proxy {proxy}: {e}{Style.RESET_ALL}")

            proxy_index = (proxy_index + 1) % proxy_count

    except asyncio.CancelledError:
        logger.info(f"Ping task for token {truncate_token(account.token)} was cancelled")
    except Exception as e:
        logger.error(f"Error in start_ping for token {truncate_token(account.token)}: {e}")

async def perform_ping(account, proxy, browser_id):
    current_time = time.time()
    logger.info(f"{Fore.CYAN}[{time.strftime('%H:%M:%S')}][{account.index}]{Style.RESET_ALL} Attempting to send ping from {Fore.CYAN}{truncate_token(account.token)}{Style.RESET_ALL} with {Fore.YELLOW}{proxy if proxy else 'no proxy'}{Style.RESET_ALL}")

    if browser_id['last_ping_time'] and (current_time - browser_id['last_ping_time']) < PING_INTERVAL:
        logger.info(f"Woah there! Not enough time has elapsed for proxy {proxy}")
        return

    browser_id['last_ping_time'] = current_time

    for url in DOMAIN_API["PING"]:
        try:
            data = {
                "id": account.account_info.get("uid"),
                "browser_id": browser_id,
                "timestamp": int(time.time())
            }
            response = await execute_request(url, data, account, proxy)
            ping_result, network_quality = "success" if response["code"] == 0 else "failed", response.get("data", {}).get("ip_score", "N/A")

            if ping_result == "success":
                logger.info(f"{Fore.CYAN}[{time.strftime('%H:%M:%S')}][{account.index}]{Style.RESET_ALL} Ping {Fore.GREEN}{ping_result}{Style.RESET_ALL} from {Fore.CYAN}{truncate_token(account.token)}{Style.RESET_ALL} with {Fore.YELLOW}{proxy if proxy else 'no proxy'}{Style.RESET_ALL}, Network Quality: {Fore.GREEN}{network_quality}{Style.RESET_ALL}")
                browser_id['successful_pings'] += 1
                return
            else:
                logger.warning(f"{Fore.RED}Ping {ping_result}{Style.RESET_ALL} for token {truncate_token(account.token)} using proxy {proxy}")

        except Exception as e:
            logger.error(f"{Fore.RED}Ping failed for token {truncate_token(account.token)} using URL {url} and proxy {proxy}: {e}{Style.RESET_ALL}")

async def collect_profile_info(account):
    try:
        if not account.proxies:
            await start_ping(account, None, account.browser_ids)
        else:
            proxy_count = len(account.proxies)
            proxy_index = 0
            success = False

            while not success and proxy_index < proxy_count:
                proxy = account.proxies[proxy_index]
                browser_id = account.browser_ids[proxy_index]

                try:
                    response = await execute_request(DOMAIN_API["SESSION"], {}, account, proxy)
                    if response.get("code") == 0:
                        account.account_info = response["data"]
                        if account.account_info.get("uid"):
                            await start_ping(account, account.proxies, account.browser_ids)
                            success = True
                    else:
                        logger.warning(f"Session failed for token {truncate_token(account.token)} using proxy {proxy}")
                except Exception as e:
                    logger.error(f"Failed to collect profile info for token {truncate_token(account.token)} using proxy {proxy}: {e}")

                proxy_index = (proxy_index + 1) % proxy_count

            if not success:
                logger.error(f"All proxies failed for token {truncate_token(account.token)}")
    except Exception as e:
        logger.error(f"Error in collect_profile_info for token {truncate_token(account.token)}: {e}")

async def complete_survey(account, proxy=None):
    """
    Complete the surveys and claim rewards.
    """
    surveys = [
        {
            "url": DOMAIN_API["SURVEY_1"],
            "payload": {"is_new_in_web3": False, "location": "Indonesia", "gender": "male", "occupation": "Marketing Manager", "industry": "Retail", "age_range": "BETWEEN_18_24"},
            "mission_id": "8"
        },
        {
            "url": DOMAIN_API["SURVEY_2"],
            "payload": {"web3_experience": "MORE_THAN_1_YEAR", "exchange": "BOTH", "trading_frequency": "YES"},
            "mission_id": "20"
        },
        {
            "url": DOMAIN_API["SURVEY_3"],
            "payload": {
                "search_tool": ["X", "DISCORD", "TELEGRAM"],
                "verification_frequency": "A_FEW_TIMES_PER_WEEK",
                "research_type": "NEWS_AND_UPDATES",
                "search_frustration": "HARD_TO_VERIFY_CURRENCY",
                "real_time_importance": "EXTREMELY_IMPORTANT",
                "switch_feature": ["TOKEN_UNLOCK_ALERTS", "SMART_CONTRACT_VERIFICATION", "SCAM_CHECK"],
                "verification_step": "check the smart contract and project info",
                "time_sensitive_info": ["TEAM_UPDATES", "PRICE_MOVEMENTS", "COMMUNITY_SENTIMENT"],
                "result_format": "DETAILED_ANALYSIS",
                "ideal_search_tool": "More detailed about team info and project"
            },
            "mission_id": "21"
        },
        {
            "url": DOMAIN_API["SURVEY_4"],
            "payload": {
                "cex_accounts": ["BINANCE", "BYBIT", "OKX", "COINBASE", "KUCOIN"],
                "most_used_cexs": ["BINANCE", "BYBIT", "OKX"],
                "most_used_dex": "JUPITER",
                "trade_frequency": "TEN_OR_MORE_TIMES_A_MONTH",
                "country": "ID",
                "crypto_wallets": ["PHANTOM"]
            },
            "mission_id": "22"
        }
    ]

    for survey in surveys:
        try:
            response = await execute_request(survey["url"], survey["payload"], account, proxy)
            if response.get("code") == 0:
                logger.info(f"{Fore.GREEN}Survey completed successfully for token {truncate_token(account.token)}{Style.RESET_ALL}")
                reward_response = await execute_request(DOMAIN_API["MISSION"], {"mission_id": survey["mission_id"]}, account, proxy)
                if reward_response.get("code") == 0:
                    logger.info(f"{Fore.GREEN}Reward claimed successfully for survey {survey['mission_id']} for token {truncate_token(account.token)}{Style.RESET_ALL}")
                else:
                    logger.warning(f"{Fore.RED}Reward claim failed for survey {survey['mission_id']} for token {truncate_token(account.token)}: {reward_response.get('message', 'Unknown error')}{Style.RESET_ALL}")
            else:
                logger.warning(f"{Fore.RED}Survey failed for token {truncate_token(account.token)}: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"{Fore.RED}Failed to complete survey for token {truncate_token(account.token)}: {e}{Style.RESET_ALL}")

async def claim_medals(account, proxy=None):
    """
    Retrieve all medals and attempt to claim those that are ready.
    """
    try:
        response = await execute_request(DOMAIN_API["MEDAL_ALL"], {}, account, proxy, method='GET')
        if response.get("code") == 0 and response.get("data"):
            medals = response["data"]
            for medal in medals:
                if medal["status"] == "NOT_READY_TO_CLAIM":
                    logger.info(f"{Fore.YELLOW}Medal {medal['name']} is not ready to claim for token {truncate_token(account.token)}{Style.RESET_ALL}")
                    continue
                if medal["status"] == "CLAIMED":
                    logger.info(f"{Fore.YELLOW}Medal {medal['name']} already claimed for token {truncate_token(account.token)}{Style.RESET_ALL}")
                    continue

                claim_response = await execute_request(DOMAIN_API["MEDAL_CLAIM"], {"medal_id": medal["id"]}, account, proxy)
                if claim_response.get("code") == 0:
                    logger.info(f"{Fore.GREEN}Medal {medal['name']} claimed successfully for token {truncate_token(account.token)}{Style.RESET_ALL}")
                else:
                    logger.warning(f"{Fore.RED}Failed to claim medal {medal['name']} for token {truncate_token(account.token)}: {claim_response.get('message', 'Unknown error')}{Style.RESET_ALL}")
        else:
            logger.warning(f"{Fore.RED}Failed to retrieve medals for token {truncate_token(account.token)}: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Error retrieving medals for token {truncate_token(account.token)}: {e}{Style.RESET_ALL}")

async def retrieve_missions(account, proxy=None):
    """
    Retrieve all missions and attempt to claim those that are available.
    """
    try:
        response = await execute_request("https://api.nodepay.org/api/mission", {}, account, proxy, method='GET')
        if response.get("code") == 0 and response.get("data"):
            missions = response["data"]
            for mission in missions:
                if mission["status"] == "AVAILABLE":
                    claim_response = await execute_request(DOMAIN_API["MISSION"], {"mission_id": mission["id"]}, account, proxy)
                    if claim_response.get("code") == 0:
                        logger.info(f"{Fore.GREEN}Mission {mission['title']} claimed successfully for token {truncate_token(account.token)}{Style.RESET_ALL}")
                    else:
                        logger.warning(f"{Fore.RED}Failed to claim mission {mission['title']} for token {truncate_token(account.token)}: {claim_response.get('message', 'Unknown error')}{Style.RESET_ALL}")
                else:
                    logger.info(f"{Fore.YELLOW}Mission {mission['title']} is not available for claiming for token {truncate_token(account.token)}{Style.RESET_ALL}")
        else:
            logger.warning(f"{Fore.RED}Failed to retrieve missions for token {truncate_token(account.token)}: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Error retrieving missions for token {truncate_token(account.token)}: {e}{Style.RESET_ALL}")

async def register_and_activate_account(token, proxies, index, operations):
    """
    Register and activate a single account.
    """
    account = AccountData(token, proxies, index)

    if 'activation' in operations:
        await activate_account(account, proxies[0] if proxies else None)

    if 'mission' in operations:
        await complete_mission(account, proxies[0] if proxies else None)

    if 'nodeping' in operations:
        await collect_profile_info(account)

    if 'survey' in operations:
        await complete_survey(account, proxies[0] if proxies else None)
        logger.info(f"{Fore.CYAN}Survey tasks completed. Exiting script as surveys are one-time tasks.{Style.RESET_ALL}")
        return

    if 'medal' in operations:
        await claim_medals(account, proxies[0] if proxies else None)

    if 'mission_claim' in operations:
        await retrieve_missions(account, proxies[0] if proxies else None)

async def main():
    tokens = await retrieve_tokens()
    proxies = await retrieve_proxies()

    use_proxies = input(f"{Fore.YELLOW}Do you want to use proxies? (y/n): {Style.RESET_ALL}").strip().lower() == 'y'
    proxies_per_account = 0

    if use_proxies:
        try:
            proxies_per_account = int(input(f"{Fore.YELLOW}How many proxies per account do you want to use?: {Style.RESET_ALL}").strip())
        except ValueError:
            logger.error("Invalid input. Please enter a number.")
            return

    print(f"{Fore.YELLOW}Select operations to perform:{Style.RESET_ALL}")
    print("1. Nodeping and Daily")
    print("2. Nodeping only")
    print("3. Activation only")
    print("4. Daily only")
    print("5. Survey task")
    print("6. Claim Medals")
    print("7. Mission Claim")
    choice = input("Enter your choice (1-7): ").strip()

    operations = []
    if choice == '1':
        operations = ['nodeping', 'mission']
    elif choice == '2':
        operations = ['nodeping']
    elif choice == '3':
        operations = ['activation']
    elif choice == '4':
        operations = ['mission']
    elif choice == '5':
        operations = ['survey']
    elif choice == '6':
        operations = ['medal']
    elif choice == '7':
        operations = ['mission_claim']
    else:
        logger.error("Invalid choice. Exiting.")
        return

    tasks = []
    for index, token in enumerate(tokens, start=1):
        start_index = (index - 1) * proxies_per_account
        assigned_proxies = proxies[start_index:start_index + proxies_per_account] if use_proxies else []

        tasks.append(register_and_activate_account(token, assigned_proxies, index, operations))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("All tasks have been cancelled.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
        tasks = asyncio.all_tasks()
        for task in tasks:
            task.cancel()
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        asyncio.get_event_loop().close()
