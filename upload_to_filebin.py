import os
import csv
import time
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller

# Function to upload file using Selenium
def upload_file_selenium(driver, file_path):
    print(f"Uploading file: {file_path}")
    driver.get("https://filebin.net")

    # Wait for the page to load completely
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    print("Page loaded")

    # Check if the file input element is present
    if len(driver.find_elements(By.CSS_SELECTOR, "input.upload")) > 0:
        print("File input element is present")
    else:
        print("File input element is NOT present")

    # Wait for the file input element to be clickable
    try:
        file_input = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input.upload"))
        )
        print("File input element found")
    except Exception as e:
        print(f"Error finding file input element: {e}")
        # Use JavaScript to make the element interactable
        file_input = driver.find_element(By.CSS_SELECTOR, "input.upload")
        driver.execute_script("arguments[0].style.display = 'block';", file_input)
        print("File input element made interactable with JavaScript")

    file_input.send_keys(file_path)
    print("File input sent")

# Function to check if the progress bar is complete
def wait_for_progress_bar(driver):
    print("Waiting for the progress bar to complete")
    WebDriverWait(driver, 300).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".progress-bar[aria-valuenow='100']"))
    )
    print("Progress bar completed")

# Function to get the shared link URL
def get_shared_link(driver):
    print("Waiting for the shared link")
    shared_link_element = WebDriverWait(driver, 300).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "p.lead a[rel='nofollow']"))
    )
    shared_link = shared_link_element.get_attribute("href")
    print(f"Shared link: {shared_link}")
    return shared_link

# Function to check for the "Download files" button with retry logic
def check_for_download_button(driver):
    print("Checking for the 'Download files' button")
    timeout = 120  # 2 minute timeout
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-bs-target='#modalArchive']"))
            )
            print("'Download files' button found")
            return
        except:
            print("Retrying to find 'Download files' button...")
            time.sleep(5)
    raise TimeoutException("Timed out waiting for 'Download files' button")

# Function to update or append to the CSV file
def update_csv(csv_file, zip_file, shared_link):
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

if __name__ == "__main__":
    main_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Main directory: {main_dir}")
    zip_dir = os.path.join(main_dir, 'zip')
    print(f"Zip directory: {zip_dir}")

    # Ensure the zip directory exists
    if not os.path.exists(zip_dir):
        os.makedirs(zip_dir)
        print(f"Created zip directory: {zip_dir}")

    # Check if there are any zip files in the directory
    zip_files = [f for f in os.listdir(zip_dir) if f.endswith('.zip') and '-DONE' not in f]
    if not zip_files:
        print(f"No zip files found in {zip_dir}. Program will terminate.")
        exit()

    try:
        # Ensure the chromedriver directory exists
        chromedriver_dir = os.path.join(main_dir, 'chromedriver')
        if not os.path.exists(chromedriver_dir):
            os.makedirs(chromedriver_dir)
        print(f"Chromedriver directory: {chromedriver_dir}")

        # Automatically download and install the latest ChromeDriver
        chromedriver_autoinstaller.install(path=chromedriver_dir)

        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-search-engine-choice-screen")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-extensions")

        # Set default search engine
        prefs = {
            "default_search_provider": {
                "enabled": True,
                "name": "Google",
                "keyword": "google.com",
                "search_url": "https://www.google.com/search?q={searchTerms}"
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Set up the WebDriver
        driver = webdriver.Chrome(options=chrome_options)

        # Loop through all zip files and upload them
        print(f"Zip files to process: {zip_files}")

        for zip_file in zip_files:
            file_path = os.path.join(zip_dir, zip_file)
            print(f"Processing file: {file_path}")

            # Upload the file using Selenium
            upload_file_selenium(driver, file_path)

            # Wait for the progress bar to complete
            wait_for_progress_bar(driver)

            # Get the shared link URL
            shared_link = get_shared_link(driver)

            # Check for the "Download files" button
            check_for_download_button(driver)

            # Save the shared link URL to a CSV file
            csv_file = os.path.join(main_dir, 'output.csv')
            print(f"Saving shared link URL to: {csv_file}")
            update_csv(csv_file, zip_file, shared_link)

            # Add a small delay to ensure the file is no longer in use
            time.sleep(5)

            # Rename the uploaded file to mark it as done
            new_file_path = os.path.join(zip_dir, zip_file.replace('.zip', '-DONE.zip'))
            os.rename(file_path, new_file_path)
            print(f"Renamed file to: {new_file_path}")

            # Refresh the page to ensure the session remains valid
            driver.refresh()

        # Remove the -DONE suffix from the zip files before terminating
        for zip_file in os.listdir(zip_dir):
            if zip_file.endswith('-DONE.zip'):
                original_file_path = os.path.join(zip_dir, zip_file)
                new_file_path = os.path.join(zip_dir, zip_file.replace('-DONE.zip', '.zip'))
                os.rename(original_file_path, new_file_path)
                print(f"Restored file name to: {new_file_path}")

        # Close the browser
        driver.quit()

        print("All files were successfully uploaded.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

    print("Script completed successfully.")
