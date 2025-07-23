import sys
import requests
import random
import time
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# ANSI Colors 
class Colors:
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    WARNING = "\033[93m"

# OSINT categories
CATEGORIES = {
    "1": {
        "name": "Social Sites",
        "sites": {
            "Instagram": {
                "url": "https://www.instagram.com/{}/",
                "method": "playwright",
                "success_indicators": ['profilePage_', '"username":"{}"', 'content="@{}'],
                "failure_indicators": ["Sorry, this page isn't available", "User not found"]
            },
            "Facebook": {
                "url": "https://www.facebook.com/{}/",
                "method": "requests",
                "success_indicators": [],
                "failure_indicators": ["This content isn't available", "Page not found"]
            },
            "Twitter": {
                "url": "https://x.com/{}/",
                "method": "playwright", 
                "success_indicators": ['data-testid="UserName"', 'data-testid="UserDescription"'],
                "failure_indicators": ["This account doesn't exist", "Account suspended"]
            },
            "Snapchat": {
                "url": "https://www.snapchat.com/add/{}/",
                "method": "playwright",
                "success_indicators": ['data-testid="add-friend-button"', 'snapcode'],
                "failure_indicators": ["Hmm, couldn't find", "User not found"]
            }
        }
    },
    "2": {
        "name": "Tech Side",
        "sites": {
            "LinkedIn": {
                "url": "https://www.linkedin.com/in/{}/",
                "method": "requests",
                "success_indicators": [],
                "failure_indicators": ["This LinkedIn profile doesn't exist"]
            },
            "GitHub": {
                "url": "https://api.github.com/users/{}",
                "method": "requests",
                "success_indicators": [],
                "failure_indicators": []
            }
        }
    },
    "3": {
        "name": "All Sites",
        "sites": {}
    }
}

# Combine all sites for option 3
CATEGORIES["3"]["sites"] = {**CATEGORIES["1"]["sites"], **CATEGORIES["2"]["sites"]}

OSINT_TIPS = [
    "With great power comes great responsibility.",
    "Always cross-check usernames across multiple platforms.",
    "Even if a username is taken, try variations with numbers or underscores.",
    "Combine OSINT tools with manual research for best results.",
    "Be aware of privacy and legal considerations while doing OSINT."
]

def setup_browser_context(browser):
    """Setup browser context with realistic settings"""
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    return context

def check_with_playwright(username, site_config):
    """Enhanced Playwright checking with better detection"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = setup_browser_context(browser)
            page = context.new_page()
            
            # Navigate to the URL
            url = site_config["url"].format(username)
            print(f"{Colors.WARNING}[DEBUG] Checking: {url}{Colors.ENDC}")
            
            response = page.goto(url, timeout=15000, wait_until='networkidle')
            
            # Wait a bit more for JS to render
            page.wait_for_timeout(2000)
            
            # Get page content and current URL (in case of redirects)
            content = page.content().lower()
            current_url = page.url
            
            browser.close()
            
            # Check for success indicators
            success_indicators = site_config.get("success_indicators", [])
            failure_indicators = site_config.get("failure_indicators", [])
            
            # Check failure indicators first
            for indicator in failure_indicators:
                if indicator.lower() in content:
                    print(f"{Colors.WARNING}[DEBUG] Found failure indicator: {indicator}{Colors.ENDC}")
                    return False, "Not Found"
            
            # Check success indicators
            for indicator in success_indicators:
                formatted_indicator = indicator.format(username).lower()
                if formatted_indicator in content:
                    print(f"{Colors.WARNING}[DEBUG] Found success indicator: {indicator}{Colors.ENDC}")
                    return True, url
            
            # For GitHub API and simple cases, check status code
            if response and response.status == 200:
                # Additional checks for specific platforms
                if "snapchat.com" in url:
                    # For Snapchat, if we didn't get redirected to explore page, it's likely valid
                    if "/explore/" not in current_url and username.lower() in current_url.lower():
                        return True, url
                elif "instagram.com" in url:
                    # Instagram specific: check if we're still on the profile page
                    if f"/{username}/" in current_url and "login" not in current_url:
                        return True, url
                elif "x.com" in url or "twitter.com" in url:
                    # Twitter/X: check if we're still on the profile URL
                    if f"/{username}" in current_url and "home" not in current_url:
                        return True, url
            
            return False, "Not Found"
            
    except Exception as e:
        print(f"{Colors.WARNING}[DEBUG] Playwright error: {str(e)}{Colors.ENDC}")
        return False, "Error checking"

def check_with_requests(username, site_config):
    """Enhanced requests checking"""
    try:
        url = site_config["url"].format(username)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # GitHub API returns 404 for non-existent users
        if "api.github.com" in url:
            return response.status_code == 200, url if response.status_code == 200 else "Not Found"
        
        # For other sites, check content
        if response.status_code == 200:
            content = response.text.lower()
            
            # Check failure indicators
            failure_indicators = site_config.get("failure_indicators", [])
            for indicator in failure_indicators:
                if indicator.lower() in content:
                    return False, "Not Found"
            
            return True, url
        else:
            return False, "Not Found"
            
    except requests.RequestException as e:
        print(f"{Colors.WARNING}[DEBUG] Requests error: {str(e)}{Colors.ENDC}")
        return False, "Error checking"

def check_username(username, sites):
    """Main function to check username across sites"""
    results = {}
    
    for site_name, site_config in sites.items():
        print(f"{Colors.OKBLUE}[*] Checking {site_name}...{Colors.ENDC}")
        
        method = site_config.get("method", "requests")
        
        if method == "playwright":
            found, message = check_with_playwright(username, site_config)
        else:
            found, message = check_with_requests(username, site_config)
        
        results[site_name] = (found, message)
        
        # small delay to avoid rate limiting
        time.sleep(1)
    
    return results

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print(f"{Colors.FAIL}Usage: python osint_checker.py <username1> [username2] [username3]{Colors.ENDC}")
        sys.exit()

    usernames = sys.argv[1:]

    print(f"\n{Colors.OKBLUE}{Colors.BOLD}🔍 OSINT Recon CLI Tool{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}Choose category to check:{Colors.ENDC}")
    print("1 - Social Sites (Instagram, Facebook, Twitter, Snapchat)")
    print("2 - Tech Side (LinkedIn, GitHub)")
    print("3 - All Sites")
    choice = input("Enter your choice (1/2/3): ")

    if choice not in CATEGORIES:
        print(f"{Colors.FAIL}Invalid choice. Exiting...{Colors.ENDC}")
        sys.exit()

    selected_sites = CATEGORIES[choice]["sites"]

    for username in usernames:
        print(f"\n{Colors.OKBLUE}{'='*50}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}[*] Checking username: {Colors.BOLD}{username}{Colors.ENDC}{Colors.OKBLUE} across {CATEGORIES[choice]['name']}...{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'='*50}{Colors.ENDC}")
        
        results = check_username(username, selected_sites)

        found_count = sum(1 for status, _ in results.values() if status)
        total_sites = len(results)
        possibility_score = round((found_count / total_sites) * 100, 2) if total_sites > 0 else 0

        print(f"\n{Colors.BOLD}📊 Results for {username}:{Colors.ENDC}")
        print("-" * 40)
        
        for site, (status, message) in results.items():
            if status:
                print(f"{Colors.OKGREEN}✅ [Found] {site}: {message}{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ [Not Found] {site}{Colors.ENDC}")

        print(f"\n{Colors.OKBLUE}📈 Possibility Score: {Colors.BOLD}{possibility_score}%{Colors.ENDC}")
        print(f"{Colors.OKBLUE}💡 OSINT Tip: {random.choice(OSINT_TIPS)}{Colors.ENDC}")

if __name__ == "__main__":
    main()