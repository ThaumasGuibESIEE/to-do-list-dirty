# scripts/selenium_task_test_pdf.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION ---
APP_URL = "http://127.0.0.1:8000/"  # Adresse locale de ton application Django
NUM_TASKS = 10
PDF_FILE = "result_test_selenium.pdf"

# --- INITIALISATION DU NAVIGATEUR ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
#options.add_argument("--headless")  # mode sans GUI
driver = webdriver.Chrome(options=options)

# --- RESULTATS ---
results = {}

try:
    driver.get(APP_URL)

    # --- SE CONNECTER (si login nécessaire) ---
    # driver.find_element(By.NAME, "username").send_keys(USERNAME)
    # driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    # driver.find_element(By.XPATH, "//button[@type='submit']").click()
    # time.sleep(1)

    # --- COMPTER LES TÂCHES INITIALES ---
    task_elements = driver.find_elements(By.CLASS_NAME, "item-row")
    initial_count = len(task_elements)
    results["initial_count"] = initial_count

    # --- CRÉER 10 TÂCHES ---
    for i in range(1, NUM_TASKS + 1):
        input_field = driver.find_element(By.NAME, "title")
        input_field.clear()
        input_field.send_keys(f"Tâche Selenium {i}")
        input_field.send_keys(Keys.RETURN)
        time.sleep(0.2)

    # --- NOMBRE APRÈS AJOUT ---
    task_elements = driver.find_elements(By.CLASS_NAME, "item-row")
    count_after_add = len(task_elements)
    results["count_after_add"] = count_after_add
    results["add_status"] = (
        "Success"
        if count_after_add == initial_count + NUM_TASKS
        else "❌Failed"
    )

    # --- SUPPRIMER LES 10 TÂCHES AJOUTÉES ---
    delete_buttons = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'item-row')]/a[contains(text(),'Delete')]",
    )
    for btn in delete_buttons[:NUM_TASKS]:
        task_to_delete = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    (
                        "//div[contains(@class,'item-row')]"
                        "/a[contains(text(),'Delete')]"
                    ),
                )
            )
        )
        task_to_delete.click()
        driver.find_element(By.NAME, "confirm").click()
        time.sleep(0.5)

    # --- NOMBRE APRÈS SUPPRESSION ---
    task_elements = driver.find_elements(By.CLASS_NAME, "item-row")
    final_count = len(task_elements)
    results["final_count"] = final_count
    results["delete_status"] = "Success" if final_count == initial_count else "❌Failed"

except Exception as e:
    results["error"] = str(e)

finally:
    driver.quit()

# --- GÉNÉRATION DU PDF ---
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", 'B', 16)
pdf.cell(0, 10, "Rapport Test Selenium", ln=True, align="C")
pdf.set_font("Arial", '', 12)
pdf.ln(10)

pdf.cell(
    0,
    10,
    f"Date du test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ln=True,
)
pdf.ln(5)

pdf.cell(0, 10, f"Tâches initiales: {results.get('initial_count','-')}", ln=True)
pdf.cell(
    0,
    10,
    (
        f"Tâches après ajout: "
        f"{results.get('count_after_add','-')} - "
        f"{results.get('add_status','-')}"
    ),
    ln=True,
)
pdf.cell(
    0,
    10,
    (
        f"Tâches après suppression: "
        f"{results.get('final_count','-')} - "
        f"{results.get('delete_status','-')}"
    ),
    ln=True,
)

if "error" in results:
    pdf.ln(5)
    pdf.set_text_color(255, 0, 0)
    pdf.multi_cell(0, 10, f"Erreur: {results['error']}")

pdf.output(PDF_FILE)
print(f"[INFO] PDF généré: {PDF_FILE}")
