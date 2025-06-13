import os
import time
import csv
import pyperclip
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
DOWNLOADS_DIR = r"D:\Download"  # Set to your actual browser downloads folder


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

# === OPEN PINE EDITOR ===
def open_pine_editor(driver, wait):
    print("Opening Pine Editor...")
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
        pine_editor_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Pine Editor']")))
        pine_editor_btn.click()
        time.sleep(2)
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
    print("Pasting code")
    pyperclip.copy(code)
    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
    time.sleep(0.5)

# === SAVE AND ADD TO CHART ===
def save_and_add_to_chart(driver, actions, wait):
    try:
        print("Pressing Ctrl + Enter to add script to chart...")
        actions.key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
        time.sleep(2)
        print("✅ Script added to chart using Ctrl + Enter.")
    except Exception as e:
        print("❌ Failed to send Ctrl + Enter:", e)
        
import shutil

def export_strategy_report(driver, wait, script_name, tp, sl):
    try:
        print("🟡 Waiting for strategy name dropdown...")
        strategy_dropdown = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "div[data-name='legend-source-title'] div[class*='button']"
        )))
        strategy_dropdown.click()
        print("📂 Opened strategy dropdown.")

        export_button = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//span[text()='Export data']"
        )))
        export_button.click()
        print("📤 Clicked 'Export strategy report'.")

        time.sleep(5)  # Wait for download to complete

        # Move downloaded file
        download_filename = os.path.join(DOWNLOADS_DIR, "StrategyTester.csv")
        if not os.path.exists(download_filename):
            print("❌ Exported file not found.")
            return False

        # Create destination folder
        combo_dir = os.path.join(OUTPUT_BASE_DIR, f"TP{tp}_SL{sl}")
        os.makedirs(combo_dir, exist_ok=True)

        # Move to structured name
        new_filename = os.path.join(combo_dir, f"{script_name}_TP{tp}_SL{sl}.csv")
        shutil.move(download_filename, new_filename)
        print(f"✅ Exported to: {new_filename}")
        return True

    except Exception as e:
        print("❌ Error during export:", e)
        return False

        
def generate_strategy_report_first(driver, wait):
    # print("Opening Strategy Tester...")
    # wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Strategy Tester']"))).click()
    # time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Generate report']"))).click()
    time.sleep(3)
    
    try:
        report = {}

        # Get the Strategy Tester Panel
        container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class^='reportContainer-']")))

        # Total PnL & ROI
        pnl_block = container.find_element(By.XPATH, ".//div[contains(text(), 'Total P&L')]/following-sibling::div[1]")
        spans = pnl_block.find_elements(By.TAG_NAME, "span")
        report["PnL"] = pnl_block.text.replace(spans[0].text, "").strip()
        report["ROI"] = spans[0].text.strip()

        # Profit Factor
        profit_factor_elem = container.find_element(By.XPATH, ".//div[contains(text(), 'Profit factor')]/following-sibling::div[1]")
        report["Profit Factor"] = profit_factor_elem.text.strip()

        # Win Rate
        win_rate_elem = container.find_element(By.XPATH, ".//div[contains(text(), 'Profitable trades')]/following-sibling::div[1]")
        report["Win Rate"] = win_rate_elem.text.strip()

        print("📊 Extracted:", report)
        return report

    except Exception as e:
        print("❌ Failed to extract strategy metrics:", e)
        return {
            "PnL": "",
            "ROI": "",
            "Profit Factor": "",
            "Win Rate": ""
        }




# === GENERATE STRATEGY REPORT ===
def generate_strategy_report(driver, wait):
    print("Opening Strategy Tester...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Strategy Tester']"))).click()
    time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Generate report']"))).click()
    time.sleep(3)
    
    try:
        report = {}

        # Get the Strategy Tester Panel
        container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class^='reportContainer-']")))

        # Total PnL & ROI
        pnl_block = container.find_element(By.XPATH, ".//div[contains(text(), 'Total P&L')]/following-sibling::div[1]")
        spans = pnl_block.find_elements(By.TAG_NAME, "span")
        report["PnL"] = pnl_block.text.replace(spans[0].text, "").strip()
        report["ROI"] = spans[0].text.strip()

        # Profit Factor
        profit_factor_elem = container.find_element(By.XPATH, ".//div[contains(text(), 'Profit factor')]/following-sibling::div[1]")
        report["Profit Factor"] = profit_factor_elem.text.strip()

        # Win Rate
        win_rate_elem = container.find_element(By.XPATH, ".//div[contains(text(), 'Profitable trades')]/following-sibling::div[1]")
        report["Win Rate"] = win_rate_elem.text.strip()

        print("📊 Extracted:", report)
        return report

    except Exception as e:
        print("❌ Failed to extract strategy metrics:", e)
        return {
            "PnL": "",
            "ROI": "",
            "Profit Factor": "",
            "Win Rate": ""
        }



# === MAIN AUTOMATION ===
def main():
    driver = setup_browser()
    wait = WebDriverWait(driver, 30)
    driver.get(TRADINGVIEW_URL)
    actions = ActionChains(driver)
    print("Loaded")

    try:
        scripts = load_scripts(SCRIPTS_DIR)
        if not scripts:
            print("No .txt files found.")
            return

        for script_path in scripts:
            script_name = os.path.splitext(os.path.basename(script_path))[0]

            with open(script_path, 'r', encoding='utf-8') as f:
                base_code = f.read()
            
            flag = True

            for tp, sl in TP_SL_COMBINATIONS:
                print(f"\n[{script_name}] Processing TP={tp}, SL={sl}")
                code = modify_code(base_code, tp, sl)

                textarea = open_pine_editor(driver, wait)
                paste_code(textarea, code, actions)
        
                if flag:
                    save_and_add_to_chart(driver, actions, wait)
                    flag = False  # No need to click Ctrl+Enter again
                    time.sleep(5)  # Let the strategy load

                # Export the detailed .csv file
                export_success = export_strategy_report(driver, wait, script_name, tp, sl)

                if not export_success:
                    print(f"⚠️ Failed to export report for {script_name} TP={tp} SL={sl}")


                # combo_dir = os.path.join(OUTPUT_BASE_DIR, f"TP{tp}_SL{sl}")
                # os.makedirs(combo_dir, exist_ok=True)

                # csv_filename = os.path.join(combo_dir, f"TP{tp}_SL{sl}.csv")
                # file_exists = os.path.isfile(csv_filename)

                # with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
                #     writer = csv.writer(f)
                #     if not file_exists:
                #         writer.writerow(["Script", "TP", "SL", "PnL", "ROI", "Profit Factor", "Win Rate"])
                #     writer.writerow([
                #         script_name, tp, sl,
                #         report["PnL"], report["ROI"],
                #         report["Profit Factor"], report["Win Rate"]
                #     ])
                # print(f"✅ Appended to CSV: {csv_filename}")


        print("\n✅ All scripts processed successfully.")

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
