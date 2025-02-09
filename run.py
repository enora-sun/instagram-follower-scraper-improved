import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager as CM
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

def save_credentials(username, password):
    with open('credentials.txt', 'w') as file:
        file.write(f"{username}\n{password}")

def load_credentials():
    if not os.path.exists('credentials.txt'):
        return None

    with open('credentials.txt', 'r') as file:
        lines = file.readlines()
        if len(lines) >= 2:
            return lines[0].strip(), lines[1].strip()

    return None

def prompt_credentials():
    username = input("Enter your Instagram username: ")
    password = input("Enter your Instagram password: ")
    save_credentials(username, password)
    return username, password

def login(bot, username, password):
    bot.get('https://www.instagram.com/accounts/login/')
    time.sleep(5)

    '''
    # Check if cookies need to be accepted
    try:
        element = bot.find_element(By.XPATH, "/html/body/div[4]/div/div/div[3]/div[2]/button")
        element.click()
    except NoSuchElementException:
        print("[Info] - Instagram did not require to accept cookies this time.")

    print("[Info] - Logging in...")
    username_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))
    password_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='password']")))

    username_input.clear()
    username_input.send_keys(username)
    password_input.clear()
    password_input.send_keys(password)

    login_button = WebDriverWait(bot, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()
    time.sleep(10)
    '''

    try:
        # Accept cookies if prompted
        accept_cookies = WebDriverWait(bot, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Only allow essential cookies']")))
        accept_cookies.click()
    except:
        print("[Info] - No cookies prompt or already accepted.")

    print("[Info] - Logging in...")

    try:
        # Wait until username and password fields are visible
        username_input = WebDriverWait(bot, 15).until(EC.presence_of_element_located((By.NAME, 'username')))
        password_input = WebDriverWait(bot, 15).until(EC.presence_of_element_located((By.NAME, 'password')))

        username_input.clear()
        username_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)

        login_button = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
    except Exception as e:
        print(f"[Error] - Login failed: {e}")

    time.sleep(10)

def close_popups(bot):
    popups = [
        "//button[contains(text(), 'Not Now')]",
        "//button[contains(text(), 'Cancel')]",
        "//button[contains(text(), 'Save Info')]"
    ]

    for popup_xpath in popups:
        try:
            popup_button = WebDriverWait(bot, 5).until(EC.element_to_be_clickable((By.XPATH, popup_xpath)))
            popup_button.click()
            print(f"[Info] - Closed popup with text: {popup_button.text}")
            time.sleep(2)
        except TimeoutException:
            pass  # No popup appeared, continue

def scrape_followers(bot, username, user_input):
    retries = 3
    for attempt in range(retries):
        try:
            print(f"[Info] - Attempting to load {username}'s profile (Attempt {attempt + 1})...")
            bot.get(f'https://www.instagram.com/{username}/')
            WebDriverWait(bot, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(5)
            break
        except TimeoutException:
            print(f"[Warning] - Timeout loading {username}'s profile. Retrying...")
            if attempt == retries - 1:
                print(f"[Error] - Failed to load {username}'s profile after {retries} attempts.")
                return

    try:
        followers_link = WebDriverWait(bot, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers') or contains(text(), 'followers')]"))
        )
        bot.execute_script("arguments[0].scrollIntoView(true);", followers_link)
        time.sleep(2)
        followers_link.click()
        print("[Info] - Clicked followers link.")
        close_popups(bot)

    except Exception as e:
        print(f"[Error] - Could not find or click followers link for {username}: {e}")
        return

    time.sleep(5)
    print(f"[Info] - Scraping followers for {username}...")

    users = set()
    scroll_attempts = 0
    max_scroll_attempts = 50

    try:
        scroll_box = WebDriverWait(bot, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@style, 'overflow')]"))
        )
        print("[Info] - Scrollable followers dialog found.")
    except TimeoutException:
        print(f"[Error] - Could not find scrollable followers dialog for {username}.")
        return

    last_height = bot.execute_script("return arguments[0].scrollHeight", scroll_box)
    scroll_increment = 300  # Small scrolls to trigger lazy loading

    while len(users) < user_input and scroll_attempts < max_scroll_attempts:
        try:
            followers = bot.find_elements(By.XPATH, "//div[@role='dialog']//a[starts-with(@href, '/')]")
            prev_count = len(users)

            for follower in followers:
                try:
                    href = follower.get_attribute('href')
                    if href:
                        username_from_href = href.split("/")[3]
                        if username_from_href and not username_from_href.startswith(('explore', 'p', 'reels')) and username_from_href not in users:
                            users.add(username_from_href)
                except StaleElementReferenceException:
                    print("[Warning] - Encountered stale element, skipping.")
                    continue

            print(f"[Debug] - Found {len(users)} followers so far.")

            # Scroll incrementally
            bot.execute_script("arguments[0].scrollTop += arguments[1];", scroll_box, scroll_increment)
            time.sleep(4)  # Allow enough time for content to load

            new_height = bot.execute_script("return arguments[0].scrollHeight", scroll_box)

            if new_height == last_height:
                scroll_attempts += 1
                print(f"[Debug] - No new followers loaded, scroll attempt {scroll_attempts}/{max_scroll_attempts}.")
            else:
                scroll_attempts = 0  # Reset if new followers load

            last_height = new_height

        except StaleElementReferenceException:
            print("[Error] - Scroll box became stale, re-locating.")
            scroll_box = WebDriverWait(bot, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@style, 'overflow')]"))
            )
        except Exception as e:
            print(f"[Error] - Exception during scrolling: {e}")
            break

    print(f"[Info] - Scraped {len(users)} followers. Saving to file...")
    with open(f'{username}_followers.txt', 'w') as file:
        file.write('\n'.join(users) + "\n")

def scrape():
    credentials = load_credentials()

    if credentials is None:
        username, password = prompt_credentials()
    else:
        username, password = credentials

    user_input = int(input('[Required] - How many followers do you want to scrape (100-2000 recommended): '))

    usernames = input("Enter the Instagram usernames you want to scrape (separated by commas): ").split(",")

    service = Service()
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument("--log-level=3")
    options.add_argument('--disable-dev-shm-usage')  # Prevents issues with shared memory in Docker/VM
    options.add_argument('--disable-gpu')  # Disable GPU rendering
    options.add_argument('--disable-features=VizDisplayCompositor')  # Fix for some rendering issues
    options.add_argument('--start-maximized')  # Open browser in maximized mode
    #mobile_emulation = {
    #    "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/90.0.1025.166 Mobile Safari/535.19"}
    #options.add_experimental_option("mobileEmulation", mobile_emulation)


    bot = webdriver.Chrome(service=service, options=options)
    from selenium.common.exceptions import TimeoutException

    try:
        bot.set_script_timeout(60)
        bot.set_page_load_timeout(30)  # Increase timeout to 30 seconds
    except TimeoutException:
        print(f"[Warning] - Timeout while loading {username}'s profile, trying to continue...")

    login(bot, username, password)

    for user in usernames:
        user = user.strip()
        scrape_followers(bot, user, user_input)

    bot.quit()


if __name__ == '__main__':
    TIMEOUT = 30
    scrape()
