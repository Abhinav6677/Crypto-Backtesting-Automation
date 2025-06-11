import os
import time
import pyperclip
import mss
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

TP_SL_COMBINATIONS = [
    (5, 5),
    (10, 5),
    (15, 10),
    # Add more as needed
]

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

# === OPEN PINE EDITOR ===
def open_pine_editor(driver, wait):
    print("Opening Pine Editor...")

    # Check if the Monaco editor is already present
    editor_elements = driver.find_elements(By.CSS_SELECTOR, "div.monaco-editor")
    visible_editors = [e for e in editor_elements if e.is_displayed()]
    if visible_editors:
        print("Pine Editor already visible.")
        editor_div = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.monaco-editor")))
        editor_div.click()
        textarea = editor_div.find_element(By.TAG_NAME, "textarea")
        return textarea
    else:
        print("Pine Editor not visible, clicking the tab.")
        # Click the Pine Editor button
        pine_editor_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Pine Editor']")))
        pine_editor_btn.click()
        time.sleep(2)  # Let it load

        # Wait and grab the editor
        editor_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.monaco-editor")))
        editor_div.click()
        textarea = editor_div.find_element(By.TAG_NAME, "textarea")
        return textarea    

def modify_code(code, tp, sl):
    code = code.replace("{{TP}}", str(tp))
    code = code.replace("{{SL}}", str(sl))
    return code

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
    actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
    time.sleep(1.5)
    actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
    print("Script saved and added to chart.")

# === GENERATE STRATEGY REPORT ===
def generate_strategy_report(driver, wait):
    print("Opening Strategy Tester...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Strategy Tester']"))).click()
    time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Generate report']"))).click()
    time.sleep(1)

# === TAKE SCREENSHOT ===
def take_screenshot(filename="strategy_report.png"):
    with mss.mss() as sct:
        sct.shot(output=filename)
        print(f"Saved screenshot: {filename}")

# === MAIN AUTOMATION ===
def main():
    driver = setup_browser()
    wait = WebDriverWait(driver, 30)
    driver.get(TRADINGVIEW_URL)
    actions = ActionChains(driver)
    print("Loaded")
    try:
        # login_if_needed(driver, wait)
        scripts = load_scripts(SCRIPTS_DIR)
        if not scripts:
            print("No .txt files found.")
            return

        for idx, script_path in enumerate(scripts, 1):
            script_name = os.path.splitext(os.path.basename(script_path))[0]
            
            with open(script_path, 'r', encoding='utf-8') as f:
                base_code = f.read()

            for tp, sl in TP_SL_COMBINATIONS:
                print(f"\n[{script_name}] Processing TP={tp}, SL={sl}")
                code = modify_code(base_code, tp, sl)

                textarea = open_pine_editor(driver, wait)
                print("Editor loaded")
                paste_code(textarea, code, actions)
                print("saving and adding to chart")
                save_and_add_to_chart(driver)
                generate_strategy_report(driver, wait)
                time.sleep(10)

                # Create output dir
                combo_dir = os.path.join(OUTPUT_BASE_DIR, f"TP{tp}_SL{sl}")
                os.makedirs(combo_dir, exist_ok=True)

                screenshot_filename = os.path.join(combo_dir, f"{script_name}_report.png")
                take_screenshot(screenshot_filename)
                time.sleep(2)

        print("\nAll scripts processed.")

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
