# scripts/selenium_task_test_pdf.py
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import sys
import time
from typing import Optional
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
import json

# --- CONFIGURATION ---
APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:8000/")  # Adresse locale
NUM_TASKS = 10
PDF_FILE = "result_test_selenium.pdf"
JSON_FILE = Path(__file__).resolve().parent.parent / "result_test_selenium.json"

ROOT = Path(__file__).resolve().parent.parent


def clear_tasks():
    """Supprime toutes les tâches via Django before/after the Selenium run."""
    cmd = [
        sys.executable,
        "manage.py",
        "shell",
        "-c",
        "from tasks.models import Task; Task.objects.all().delete()",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


def start_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    if os.environ.get("HEADLESS", "1") != "0":
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


# Instancier le driver global utilisé par les helpers ci-dessous
driver = start_driver()

def wait_for_home(driver):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "title"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form button[type='submit']"))
    )


# --- RESULTATS ---
results = {}

def task_count():
    """Compte uniquement les tâches réelles (liens Delete visibles)."""
    return len(driver.find_elements(By.CSS_SELECTOR, ".item-row a.btn-danger"))


def add_task(title: str) -> None:
    wait_for_home(driver)
    input_field = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.NAME, "title"))
    )
    input_field.clear()
    input_field.send_keys(title)
    submit_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "form button[type='submit']"))
    )
    submit_btn.click()
    locator = (
        By.XPATH,
        f"//li[contains(@class,'item-row')][contains(., \"{title}\")]",
    )
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(locator)
    )
    time.sleep(0.1)


def find_task_row(title: str) -> Optional[object]:
    for el in driver.find_elements(By.CSS_SELECTOR, "li.item-row"):
        if title in el.text:
            return el
    return None


def delete_task_by_title(title: str) -> None:
    delete_locator = (
        By.XPATH,
        (
            "//li[contains(@class,'item-row')][contains(., \"{title}\")]"
            "//a[contains(@class,'btn-danger')]"
        ).format(title=title),
    )
    btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable(delete_locator)
    )
    btn.click()
    confirm_button = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "form button.btn-danger"))
    )
    confirm_button.click()
    WebDriverWait(driver, 5).until(
        lambda d: len(d.find_elements(*delete_locator)) == 0
    )
    time.sleep(0.2)


try:
    clear_tasks()
    driver.get(APP_URL)
    wait_for_home(driver)

    # --- SE CONNECTER (si login nécessaire) ---
    # driver.find_element(By.NAME, "username").send_keys(USERNAME)
    # driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    # driver.find_element(By.XPATH, "//button[@type='submit']").click()
    # time.sleep(1)

    # --- COMPTER LES TÂCHES INITIALES ---
    initial_count = task_count()
    results["initial_count"] = initial_count

    # --- CRÉER 10 TÂCHES ---
    # --- SCÉNARIO BULK (10 tâches) ---
    bulk_titles = [
        f"Tâche Selenium {i} - {int(time.time())}"
        for i in range(1, NUM_TASKS + 1)
    ]
    for title in bulk_titles:
        add_task(title)
    after_bulk_add = task_count()
    results["bulk_after_add_count"] = after_bulk_add
    results["bulk_add_status"] = (
        "Success" if after_bulk_add == initial_count + NUM_TASKS else "Failed"
    )

    for title in reversed(bulk_titles):
        delete_task_by_title(title)
    after_bulk_delete = task_count()
    results["bulk_after_delete_count"] = after_bulk_delete
    results["bulk_delete_status"] = (
        "Success" if after_bulk_delete == initial_count else "Failed"
    )

    # --- SCÉNARIO E2E (persist first task) ---
    first_title = f"Tâche Selenium A - {int(time.time())}"
    second_title = f"Tâche Selenium B - {int(time.time())}"
    add_task(first_title)
    add_task(second_title)
    results["after_add_count"] = task_count()

    delete_task_by_title(second_title)

    first_still_there = find_task_row(first_title) is not None
    results["first_task_present"] = first_still_there
    results["final_count"] = task_count()
    results["delete_status"] = "Success" if first_still_there else "Failed"

except Exception as e:
    results["error"] = str(e)

finally:
    try:
        clear_tasks()
    except Exception:
        results["cleanup_error"] = "Impossible de vider les tâches en sortie."
    driver.quit()

# --- EXPORT JSON ---
tests_payload = []

bulk_ok = (
    results.get("bulk_add_status") == "Success"
    and results.get("bulk_delete_status") == "Success"
    and "error" not in results
)
tests_payload.append(
    {
        "id": "TA11",
        "name": "Parcours Selenium (ajout/suppression en lot)",
        "status": "passed" if bulk_ok else "failed",
        "details": results,
    }
)

e2e_ok = (
    results.get("delete_status") == "Success"
    and results.get("first_task_present")
    and "error" not in results
)
tests_payload.append(
    {
        "id": "TA12",
        "name": "Parcours E2E Selenium (vérifier tâche restante)",
        "status": "passed" if e2e_ok else "failed",
        "details": results,
    }
)

json_payload = {"tests": tests_payload}
JSON_FILE.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

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

pdf.cell(
    0,
    10,
    f"Tâches initiales: {results.get('initial_count','-')}",
    ln=True,
)
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
elif "cleanup_error" in results:
    pdf.ln(5)
    pdf.set_text_color(255, 165, 0)
    pdf.multi_cell(0, 10, results["cleanup_error"])

pdf.output(PDF_FILE)
print(f"[INFO] PDF généré: {PDF_FILE}")
