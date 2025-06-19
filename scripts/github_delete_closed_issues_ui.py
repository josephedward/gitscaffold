#!/usr/bin/env python3
"""
Automate deletion of all closed issues in a GitHub repo.

Prerequisites:
  pip install selenium webdriver-manager python-dotenv
  Create a .env file with:
    GH_USER=your_username
    GH_PASS=your_password
    REPO_URL=https://github.com/<owner>/<repo>
"""
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

load_dotenv()
GH_USER = os.getenv("GH_USER")
GH_PASS = os.getenv("GH_PASS")
REPO_URL = os.getenv("REPO_URL")  # e.g. https://github.com/owner/repo

CLOSED_URL = f"{REPO_URL}/issues?q=is%3Aissue+state%3Aclosed"

def log(msg):
    print(f"[+] {msg}")

def login(driver):
    driver.get("https://github.com/login")
    driver.find_element(By.ID, "login_field").send_keys(GH_USER)
    driver.find_element(By.ID, "password").send_keys(GH_PASS)
    driver.find_element(By.NAME, "commit").click()
    time.sleep(2)
    log("Logged in")

def delete_closed_issues(driver):
    while True:
        driver.get(CLOSED_URL)
        time.sleep(2)
        try:
            first_issue = driver.find_element(
                By.CSS_SELECTOR,
                'div[aria-label="Issues"] a.Link--primary'
            )
        except NoSuchElementException:
            log("No more closed issues found.")
            break

        title = first_issue.text
        link = first_issue.get_attribute("href")
        log(f"Deleting: {title} ({link})")
        first_issue.click()
        time.sleep(2)

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(1)

        try:
            delete_btn = driver.find_element(By.XPATH, "//button[.='Delete issue']")
        except NoSuchElementException:
            delete_btn = driver.find_element(By.XPATH, "//a[.='Delete issue']")

        delete_btn.click()
        time.sleep(1)

        confirm = driver.find_element(By.XPATH, "//button[normalize-space()='Delete']")
        confirm.click()
        time.sleep(2)

if __name__ == "__main__":
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # uncomment to run headless

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    try:
        login(driver)
        delete_closed_issues(driver)
    finally:
        driver.quit()
        log("Done.")