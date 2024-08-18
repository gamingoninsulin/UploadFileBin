import csv
import logging
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
import sched

import chromedriver_autoinstaller
from selenium import webdriver
from selenium.common import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Set up logging
logging.basicConfig(filename='console.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("File Upload Manager")

        # Checkboxes
        self.create_zip_var = tk.BooleanVar(value=True)
        self.install_chromedriver_var = tk.BooleanVar(value=True)

        # Console output field (read-only)
        self.console_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20, state='disabled')
        self.console_output.pack()

        # Start the process automatically
        self.start_process()

    def start_process(self):
        self.log_message("Process started...\n")
        # Run the upload script in a separate thread
        threading.Thread(target=self.run_upload_script).start()

    def log_message(self, message):
        self.console_output.config(state='normal')
        self.console_output.insert(tk.END, message + "\n")
        self.console_output.config(state='disabled')
        self.console_output.see(tk.END)
        logging.info(message)

    def run_upload_script(self):
        uploader = FileUploader(self)
        uploader.run_upload_script(self.create_zip_var.get(), self.install_chromedriver_var.get())

class FileUploader:
    def __init__(self, app):
        self.app = app

    def check_and_install_requirements(self):
        if os.path.isfile('requirements.txt'):
            self.app.log_message('requirements.txt found. Installing requirements...')
            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
            self.app.log_message('Requirements installed successfully.')
        else:
            self.app.log_message('requirements.txt not found.')

    def upload_file_selenium(self, driver, file_path):
        self.app.log_message(f"Uploading file: {file_path}")
        driver.get("https://filebin.net")

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.app.log_message("Page loaded")

        if len(driver.find_elements(By.CSS_SELECTOR, "input.upload")) > 0:
            self.app.log_message("File input element is present")
        else:
            self.app.log_message("File input element is NOT present")

        try:
            file_input = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.upload")))
            self.app.log_message("File input element found")
        except Exception as e:
            self.app.log_message(f"Error finding file input element: {e}")
            file_input = driver.find_element(By.CSS_SELECTOR, "input.upload")
            driver.execute_script("arguments[0].style.display = 'block';", file_input)
            self.app.log_message("File input element made interactable with JavaScript")

        file_input.send_keys(file_path)
        self.app.log_message("File input sent")

        # Wait for the page to redirect
        WebDriverWait(driver, 30).until(EC.url_changes(driver.current_url))
        self.app.log_message("Page redirected")

        # Wait for the new page to load
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.app.log_message("New page loaded")

    def wait_for_progress_bar(self, driver):
        self.app.log_message("Waiting for the progress bar to complete")
        timeout = 600
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                progress_bar = driver.find_element(By.CSS_SELECTOR, ".progress-bar")
                progress_value = progress_bar.get_attribute("aria-valuenow")
                self.app.log_message(f"Current progress: {progress_value}%")
                if progress_value == '100':
                    self.app.log_message("Progress bar completed")
                    return
            except Exception as e:
                self.app.log_message(f"An error occurred while checking the progress bar: {e}")
            time.sleep(5)
        self.app.log_message("Timeout waiting for the progress bar to complete")

    def get_shared_link(self, driver):
        self.app.log_message("Waiting for the shared link")
        retries = 3
        for attempt in range(retries):
            try:
                shared_link_element = WebDriverWait(driver, 300).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "p.lead a[rel='nofollow']")))
                shared_link = shared_link_element.get_attribute("href")
                self.app.log_message(f"Shared link: {shared_link}")
                return shared_link
            except StaleElementReferenceException as e:
                self.app.log_message(
                    f"StaleElementReferenceException encountered: {e}. Retrying... ({attempt + 1}/{retries})")
                time.sleep(2)
        raise Exception("Failed to retrieve shared link after multiple attempts")

    def check_for_download_button(self, driver):
        self.app.log_message("Checking for the 'Download files' button")
        timeout = 120
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-bs-target='#modalArchive']")))
                self.app.log_message("'Download files' button found")
                return
            except:
                self.app.log_message("Retrying to find 'Download files' button...")
                time.sleep(5)
        raise TimeoutException("Timed out waiting for 'Download files' button")

    def update_csv(self, csv_file, zip_file, shared_link):
        file_exists = os.path.isfile(csv_file)
        updated = False
        rows = []

        if file_exists:
            with open(csv_file, 'r', newline='') as csvfile:
                csvreader = csv.reader(csvfile)
                for row in csvreader:
                    if row[0] == zip_file:
                        row[1] = shared_link
                        updated = True
                    rows.append(row)

        if not updated:
            rows.append([zip_file, shared_link])

        with open(csv_file, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerows(rows)

    def run_upload_script(self, create_zip, install_chromedriver):
        try:
            self.app.log_message("Starting the upload script...")
            self.check_and_install_requirements()
            main_dir = os.path.dirname(os.path.abspath(__file__))
            self.app.log_message(f"Main directory: {main_dir}")
            zip_dir = os.path.join(main_dir, 'zip')
            self.app.log_message(f"Zip directory: {zip_dir}")

            if create_zip and not os.path.exists(zip_dir):
                os.makedirs(zip_dir)
                self.app.log_message(f"Created zip directory: {zip_dir}")

            zip_files = [f for f in os.listdir(zip_dir) if f.endswith('.zip') and '-DONE' not in f]
            self.app.log_message(f"Zip files found: {zip_files}")
            if not zip_files:
                self.app.log_message(f"No zip files found in {zip_dir}. Program will terminate.")
                return  # Use return instead of exit()

            chromedriver_dir = os.path.join(main_dir, 'chromedriver')
            if not os.path.exists(chromedriver_dir):
                os.makedirs(chromedriver_dir)
            self.app.log_message(f"Chromedriver directory: {chromedriver_dir}")

            if install_chromedriver:
                self.app.log_message("Installing ChromeDriver...")
                chromedriver_autoinstaller.install(path=chromedriver_dir)
                self.app.log_message("ChromeDriver installed.")

            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--disable-search-engine-choice-screen")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-extensions")

            prefs = {"default_search_provider": {"enabled": True, "name": "Google", "keyword": "google.com",
                                                 "search_url": "https://www.google.com/search?q={searchTerms}"}}
            chrome_options.add_experimental_option("prefs", prefs)

            self.app.log_message("Starting ChromeDriver...")
            driver = webdriver.Chrome(options=chrome_options)
            self.app.log_message("ChromeDriver started.")

            self.app.log_message(f"Zip files to process: {zip_files}")

            for zip_file in zip_files:
                file_path = os.path.join(zip_dir, zip_file)
                self.app.log_message(f"Processing file: {file_path}")

                # Navigate to the page and get the shared link
                driver.get("https://filebin.net")
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self.app.log_message("Page loaded")

                shared_link_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//span[contains(text(), 'The files will be available at')]/a"))
                )
                shared_link = shared_link_element.get_attribute("href")
                self.app.log_message(f"Shared link: {shared_link}")

                # Upload the file
                self.upload_file_selenium(driver, file_path)

                # Check for the "Download files" button
                self.check_for_download_button(driver)

                # Save the shared link to the CSV file
                csv_file = os.path.join(main_dir, 'output.csv')
                self.app.log_message(f"Saving shared link URL to: {csv_file}")
                self.update_csv(csv_file, zip_file, shared_link)

                time.sleep(5)

                new_file_path = os.path.join(zip_dir, zip_file.replace('.zip', '-DONE.zip'))
                os.rename(file_path, new_file_path)
                self.app.log_message(f"Renamed file to: {new_file_path}")

                driver.refresh()

        except Exception as e:
            self.app.log_message(f"An error occurred: {e}")
            raise
        finally:
            # Iterate over all files in the zip directory and rename those with the -DONE.zip suffix
            for file in os.listdir(zip_dir):
                if file.endswith('-DONE.zip'):
                    original_file_path = os.path.join(zip_dir, file)
                    new_file_path = os.path.join(zip_dir, file.replace('-DONE.zip', '.zip'))
                    os.rename(original_file_path, new_file_path)
                    self.app.log_message(f"Restored file name to: {new_file_path}")

        driver.quit()
        self.app.log_message("All files were successfully uploaded.")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()