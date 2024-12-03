import asyncio
import requests
from datetime import datetime
from typing import Optional, Dict
from colorama import Fore, Style, init
from capmonster_python import TurnstileTask
from twocaptcha import TwoCaptcha
from anticaptchaofficial.turnstileproxyless import turnstileProxyless

init(autoreset=True)

# Utility logging function
def log_step(message: str, type: str = "info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "info": Fore.LIGHTCYAN_EX,
        "success": Fore.LIGHTGREEN_EX,
        "error": Fore.LIGHTRED_EX,
        "warning": Fore.LIGHTYELLOW_EX
    }
    color = colors.get(type, Fore.WHITE)
    prefix = {
        "info": "ℹ",
        "success": "✓",
        "error": "✗",
        "warning": "⚠"
    }
    print(f"{Fore.WHITE}[{timestamp}] {color}{prefix.get(type, '•')} {message}{Style.RESET_ALL}")

class CaptchaConfig:
    WEBSITE_KEY = '0x4AAAAAAAx1CyDNL8zOEPe7'
    WEBSITE_URL = 'https://app.nodepay.ai/login'

class ServiceCapmonster:
    def __init__(self, api_key):
        self.capmonster = TurnstileTask(api_key)

    async def get_captcha_token_async(self):
        task_id = self.capmonster.create_task(
            website_key=CaptchaConfig.WEBSITE_KEY,
            website_url=CaptchaConfig.WEBSITE_URL
        )
        return self.capmonster.join_task_result(task_id).get("token")

class ServiceAnticaptcha:
    def __init__(self, api_key):
        self.api_key = api_key
        self.solver = turnstileProxyless()
        self.solver.set_key(self.api_key)
        self.solver.set_website_url(CaptchaConfig.WEBSITE_URL)
        self.solver.set_website_key(CaptchaConfig.WEBSITE_KEY)
        self.solver.set_action("login")

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.solver.solve_and_return_solution)

class Service2Captcha:
    def __init__(self, api_key):
        self.solver = TwoCaptcha(api_key)

    async def get_captcha_token_async(self):
        result = await asyncio.to_thread(
            lambda: self.solver.turnstile(
                sitekey=CaptchaConfig.WEBSITE_KEY,
                url=CaptchaConfig.WEBSITE_URL
            )
        )
        return result['code']

class CaptchaServiceFactory:
    @staticmethod
    def create_service(service_name: str, api_key: str):
        if service_name.lower() == "capmonster":
            return ServiceCapmonster(api_key)
        elif service_name.lower() == "anticaptcha":
            return ServiceAnticaptcha(api_key)
        elif service_name.lower() == "2captcha":
            return Service2Captcha(api_key)
        raise ValueError(f"Unknown service: {service_name}")
    
class ProxyManager:
    def __init__(self, proxy_list: list):
        self.proxies = proxy_list
        self.current_index = -1
        self.total_proxies = len(proxy_list) if proxy_list else 0
        self.current_session_proxy = None
        
        if self.total_proxies == 1:
            log_step("Single proxy detected - will use the same proxy for all requests", "warning")
        elif self.total_proxies > 1:
            log_step(f"Multiple proxies detected ({self.total_proxies}) - will rotate proxies", "info")
        else:
            log_step("No proxies provided - will run without proxy", "warning")
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None
        
        if self.total_proxies == 1:
            proxy = self.proxies[0]
            self.current_session_proxy = {"http": proxy, "https": proxy}
            log_step(f"Using single proxy: {proxy}", "warning")
        else:
            self.current_index = (self.current_index + 1) % self.total_proxies
            proxy = self.proxies[self.current_index]
            self.current_session_proxy = {"http": proxy, "https": proxy}
            log_step(f"Using proxy: {proxy}", "warning")
            
        return self.current_session_proxy
    
    def start_new_session(self) -> Optional[Dict[str, str]]:
        return self.get_next_proxy()
    
    def get_session_proxy(self) -> Optional[Dict[str, str]]:
        return self.current_session_proxy

    def get_current_ip(self) -> str:
        try:
            response = requests.get(
                'https://api64.ipify.org?format=json',
                proxies=self.current_session_proxy,
                timeout=30
            )
            return response.json()['ip']
        except Exception as e:
            log_step(f"Failed to get IP address: {str(e)}", "error")
            return "Unknown"

class ApiEndpoints:
    BASE_URL = "https://api.nodepay.ai/api"
    
    @classmethod
    def get_url(cls, endpoint: str) -> str:
        return f"{cls.BASE_URL}/{endpoint}"
    
    class Auth:
        LOGIN = "auth/login"

class ReferralClient:
    def __init__(self, proxy_manager: Optional[ProxyManager] = None):
        self.email = None
        self.proxy_manager = proxy_manager
        self.password = None
        self.max_retries = 5

    async def _get_captcha_with_retry(self, captcha_service) -> Optional[str]:
        # Ambil token captcha
        captcha_token = await captcha_service.get_captcha_token_async()
        if not captcha_token:
            log_step("Failed to get captcha token", "error")

        return captcha_token

    async def _make_request(self, method: str, endpoint: str, json_data: dict, auth_token: Optional[str] = None) -> dict:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
            'Authorization': f'Bearer {auth_token}' if auth_token else '',
        }
        url = ApiEndpoints.get_url(endpoint)

        try:
            response = await asyncio.to_thread(
                lambda: requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    timeout=30
                )
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            log_step(f"Request failed: {str(e)}", "error")
            return {"success": False, "msg": str(e)}

    async def login(self, email: str, password: str, captcha_service) -> Optional[str]:
        for attempt in range(1, self.max_retries + 1):
            try:
                log_step(f"Login attempt {attempt} of {self.max_retries}...", "info")
                
                captcha_token = await self._get_captcha_with_retry(captcha_service)
                if not captcha_token:
                    continue
                
                json_data = {
                    'user': email,
                    'password': password,
                    'remember_me': True,
                    'recaptcha_token': captcha_token
                }
                
                response = await self._make_request(
                    method='POST',
                    endpoint=ApiEndpoints.Auth.LOGIN,
                    json_data=json_data
                )
                
                
                if response.get("success"):
                    access_token = response['data']['token']
                    log_step("Login successful", "success")
                    return access_token

                msg = response.get("msg", "Unknown login error")
                log_step(f"Login failed on attempt {attempt}: {msg}", "error")
                
                if attempt == self.max_retries:
                    return None
                
            except Exception as e:
                log_step(f"Login error on attempt {attempt}: {str(e)}", "error")
                if attempt == self.max_retries:
                    return None
        return None

    async def process_login(self, email: str, password: str, captcha_service):
        token = await self.login(email, password, captcha_service)
        if token:
            log_step(f"Token for {email}: {token}", "success")
            with open('token_list.txt', 'a') as f:
                f.write(f"{token}\n")
        else:
            log_step(f"Failed to get token for {email}", "error")

async def main():
    print(f"{Fore.GREEN}Auto GET Token Nodepay{Style.RESET_ALL}")
    
    # Choose captcha service
    print(f"\n{Fore.YELLOW}Available captcha services:{Style.RESET_ALL}")
    print(f"1. Capmonster")
    print(f"2. Anticaptcha")
    print(f"3. 2Captcha{Style.RESET_ALL}")
    service_choice = input(f"{Fore.GREEN}Choose captcha service (1-3): {Style.RESET_ALL}")
    api_key = input(f"{Fore.GREEN}Enter API key for captcha service: {Style.RESET_ALL}")

    use_proxies = input(f"{Fore.GREEN}Use proxies? (yes/no): {Style.RESET_ALL}").lower() == 'yes'
    proxy_manager = None
    
    if use_proxies:
        try:
            with open('proxy.txt', 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            proxy_manager = ProxyManager(proxy_list)
            log_step(f"Loaded {len(proxy_list)} proxies", "success")
        except FileNotFoundError:
            log_step("proxies.txt not found. Running without proxies.", "warning")

    service_map = {
        "1": "capmonster",
        "2": "anticaptcha",
        "3": "2captcha"
    }

    try:
        captcha_service = CaptchaServiceFactory.create_service(service_map[service_choice], api_key)
        log_step("Captcha service initialized", "success")
    except Exception as e:
        log_step(f"Failed to initialize captcha service: {str(e)}", "error")
        return

    with open('accounts.txt', 'r') as f:
        accounts = f.readlines()

    client = ReferralClient()

    for account in accounts:
        email, password = account.strip().split(":")
        
        log_step(f"Processing login for {email}", "info")
        await client.process_login(email, password, captcha_service)
    
    log_step("All logins processed.", "info")

if __name__ == "__main__":
    asyncio.run(main())
