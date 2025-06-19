import os
import time
import pyperclip
import mss
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from google.oauth2.service_account import Credentials

TP_SL_COMBINATIONS = [
    (5, 5),
    (10, 5),
    (15, 10),
    # Add more as needed
]

TIME_INTERVALS = [
    "1 second",
    "30 seconds",
    "1 minute",
]
    # "1 second",
    # "30 seconds",
    # "1 minute",
    # "5 minutes",
    # "30 minutes",
    # "1 hour"



# Setup Google Sheets credentials
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1CIDJI6wXeu0UsWgI6ydcBps3NI8T0utQ0X26zd6jiIo/edit?usp=sharing").sheet1
    if not sheet.get_all_values():  # if sheet is empty
        sheet.append_row(["Strategy Name", "Interval", "TP", "SL", "Pair", "PnL", "ROI", "Profit Factor", "Win Rate"])
    return sheet



OUTPUT_BASE_DIR = os.path.abspath("reports")

# === CONFIGURATION ===
DRIVER_PATH = r"D:\edgedriver_win64\msedgedriver.exe"
EDGE_BINARY = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE_DIR = r"D:\Internship data\New folder\super_mirror\edge_profile"
SCRIPTS_DIR = os.path.abspath("scripts")
TRADINGVIEW_URL = "https://www.tradingview.com/chart"

# === BROWSER SETUP ===
def setup_browser():
    options = Options()
    options.binary_location = EDGE_BINARY
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Edge(service=Service(DRIVER_PATH), options=options)

# === LOAD SCRIPTS ===
def load_scripts(directory):
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Scripts directory '{directory}' does not exist.")
    files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.txt')])
    return [os.path.join(directory, f) for f in files]

# === HANDLE LOGIN ===
def login_if_needed(driver, wait):
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='Pine Editor']")), timeout=10)
        print("Already logged in.")
    except Exception:
        print("Please log in manually.")
        input("After logging in, press Enter to continue...")
        driver.get(TRADINGVIEW_URL)
        wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='Pine Editor']")))    

def modify_code(code, tp, sl):
    code = code.replace("{{TP}}", str(tp))
    code = code.replace("{{SL}}", str(sl))
    return code

def select_time_interval(driver, wait, interval_name):
    """
    Opens the TV interval dropdown and clicks exactly the menu item whose
    visible text (normalized) equals interval_name (e.g. "1 second").
    """
    try:
        # 1) Open the dropdown
        dropdown_xpath = (
            '/html/body/div[2]/div/div[3]/div/div/div[3]/div[1]'
            '/div/div/div/div/div[4]/div/button/div'
        )
        wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath))).click()
        time.sleep(1)  # let the menu render

        # 2) Grab all visible items (this includes both headers & actual intervals)
        items = wait.until(EC.presence_of_all_elements_located((
            By.XPATH, '//div[contains(@class,"tv-menu") or contains(@class,"item")]'
        )))

        # 3) Normalize and match EXACTLY against our target, skipping any header
        target = interval_name.strip().lower()
        for it in items:
            txt = " ".join(it.text.split()).lower()  # collapse whitespace
            if txt == target:
                it.click()
                print(f"✅ Selected interval ‘{interval_name}’")
                time.sleep(2)  # allow chart to redraw
                return True

        # 4) If we get here, it wasn’t found
        print(f"❌ Interval ‘{interval_name}’ not found in dropdown")
        return False

    except Exception as e:
        print(f"❌ Error selecting interval ‘{interval_name}’: {e}")
        return False



        
def prepare_editor(driver, wait):
    print("Opening and preparing Pine Editor...")

    # Step 1: Ensure Pine Editor tab is active
    pine_editor_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Pine Editor']")))
    pine_editor_btn.click()
    time.sleep(3)
    
    # Step 2: Click inside editor to focus
    print("Click inside editor to focus")
    editor_div = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.monaco-editor")))
    editor_div.click()
    time.sleep(0.5)

    # Step 3: Open new script via Ctrl+K then Ctrl+S
    actions = ActionChains(driver)
    actions.key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
    time.sleep(0.5)
    actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
    print("✅ Triggered new script with Ctrl+K then Ctrl+S.")
    time.sleep(1.5)

    # Step 4: Focus the newly opened empty editor
    editor_div = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.monaco-editor")))
    editor_div.click()
    time.sleep(0.3)

    # Step 5: Get the active textarea
    textarea = editor_div.find_element(By.TAG_NAME, "textarea")
    return textarea



# === PASTE CODE TO EDITOR ===
def paste_code(textarea, code, actions):
    print("Deleting existing code")    
    textarea.send_keys(Keys.CONTROL, 'a')
    textarea.send_keys(Keys.BACKSPACE)
    time.sleep(0.2)
    
    print("pasting code")
    pyperclip.copy(code)
    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
    time.sleep(0.5)
    

# === SAVE AND ADD TO CHART ===
def save_and_add_to_chart(driver):
    actions = ActionChains(driver)
    # actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
    # time.sleep(1.5)
    actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
    print("Script saved and added to chart.")


# === GENERATE STRATEGY REPORT ===
def generate_strategy_report(driver, wait):
    print("Opening Strategy Tester...")
    # wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Strategy Tester']"))).click()
    # time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Generate report']"))).click()
    time.sleep(3)
    
  
# === TAKE SCREENSHOT ===
def take_screenshot(filename="strategy_report.png"):
    with mss.mss() as sct:
        sct.shot(output=filename)
        print(f"Saved screenshot: {filename}")
        
def extract_and_log_to_sheet(driver, script_name, interval, tp, sl, sheet):
    try:
        pnl_xpath = '/html/body/div[2]/div/div[7]/div[2]/div[4]/div/div/div/div[3]/div[1]/div[1]/div[2]/div[1]'
        roi_xpath = '/html/body/div[2]/div/div[7]/div[2]/div[4]/div/div/div/div[3]/div[1]/div[1]/div[2]/div[3]'
        pf_xpath  = '/html/body/div[2]/div/div[7]/div[2]/div[4]/div/div/div/div[3]/div[1]/div[5]/div[2]/div'
        win_xpath = '/html/body/div[2]/div/div[7]/div[2]/div[4]/div/div/div/div[3]/div[1]/div[4]/div[2]/div[1]'
        pair_xpath = '/html/body/div[2]/div/div[3]/div/div/div[3]/div[1]/div/div/div/div/div[2]/button[1]/div'

        pnl = driver.find_element(By.XPATH, pnl_xpath).text.strip()
        roi = driver.find_element(By.XPATH, roi_xpath).text.strip()
        pf = driver.find_element(By.XPATH, pf_xpath).text.strip()
        win = driver.find_element(By.XPATH, win_xpath).text.strip()
        pair = driver.find_element(By.XPATH, pair_xpath).text.strip()

        row = [script_name, interval, tp, sl, pair, pnl, roi, pf, win]
        sheet.append_row(row)
        time.sleep(1.5)
        print("📄 Data logged to Google Sheet.")
    except Exception as e:
        print(f"❌ Error logging to Google Sheet: {e}")



# === MAIN AUTOMATION ===
def main():
    driver = setup_browser()
    
    wait = WebDriverWait(driver, 30)
    driver.get(TRADINGVIEW_URL)
    actions = ActionChains(driver)
    print("Loaded")
    
    sheet = setup_google_sheets()
    try:
        scripts = load_scripts(SCRIPTS_DIR)
        if not scripts:
            print("No .txt files found.")
            return

        for idx, script_path in enumerate(scripts, 1):
            script_name = os.path.splitext(os.path.basename(script_path))[0]

            with open(script_path, 'r', encoding='utf-8') as f:
                base_code = f.read()

            for interval in TIME_INTERVALS:
                print(f"\n🕒 Changing to interval: {interval}")
                select_time_interval(driver, wait, interval)

                for tp, sl in TP_SL_COMBINATIONS:
                    print(f"\n[{script_name} | {interval}] Processing TP={tp}, SL={sl}")
                    code = modify_code(base_code, tp, sl)

                    textarea = prepare_editor(driver, wait)
                    print("Editor loaded")
                    paste_code(textarea, code, actions)
                    print("Saving and adding to chart...")
                    save_and_add_to_chart(driver)
                    print(generate_strategy_report(driver, wait))
                    time.sleep(100)

                    combo_dir = os.path.join(
                        OUTPUT_BASE_DIR,
                        f"{script_name.replace(' ', '_')}/Interval_{interval.replace(' ', '')}/TP{tp}_SL{sl}"
                    )
                    os.makedirs(combo_dir, exist_ok=True)

                    screenshot_filename = os.path.join(combo_dir, "report.png")
                    take_screenshot(screenshot_filename)                        
                    extract_and_log_to_sheet(driver, script_name, interval, tp, sl, sheet)

                    time.sleep(2)

        print("\n✅ All scripts processed.")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# === RUN SCRIPT ===
if __name__ == "__main__":
    main()



