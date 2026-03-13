from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import csv
import time
import os

# Re-adding webdriver_manager for your local compatibility
try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

def normalize_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return url.lower()

def search_internal(driver, url, searchPhrase):
    # Added &pws=0 to disable personalized search results for better accuracy
    if "google.com" in url:
        url += f"/search?q={searchPhrase.replace(' ', '+')}&pws=0"
        driver.get(url)
    else:
        driver.get(url)
        try:
            entryField = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            entryField.clear()
            entryField.send_keys(searchPhrase)
            entryField.send_keys(Keys.RETURN)
        except Exception as e:
            print(f"Error finding search field on {url}: {e}")
            raise

def run_rank_tracker(search_engines, search_phrases, requestedSearchDomain):
    chrome_options = Options()
    is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
    
    if is_docker:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/chromium"
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        if HAS_WDM:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

    # Normalize target domain
    charactersToBeCleared = ["http://", "https://", "www."]
    for character in charactersToBeCleared:
        requestedSearchDomain = requestedSearchDomain.replace(character, "")
    requestedSearchDomain = requestedSearchDomain.lower().strip()

    results = {}
    MAX_PAGES = 5
    
    try:
        for searchEngine in search_engines:
            engine_key = searchEngine.lower().strip()
            engine_results = []
            
            for searchPhrase in search_phrases:
                print(f"\n[Accuracy Scan] '{searchPhrase}' on {engine_key}...")
                current_rank = 1
                found = False

                for page in range(1, MAX_PAGES + 1):
                    if page == 1:
                        if engine_key == 'google':
                            search_internal(driver, "https://www.google.com", searchPhrase)
                            container_selector = "div.g" # Focus on main result containers
                        elif engine_key == 'bing':
                            search_internal(driver, "https://www.bing.com", searchPhrase)
                            container_selector = "li.b_algo"
                        elif engine_key == 'duckduckgo':
                            search_internal(driver, "https://duckduckgo.com", searchPhrase)
                            container_selector = "article[data-testid='result']"
                        else: break
                    else:
                        try:
                            if engine_key == 'google':
                                driver.find_element(By.ID, "pnnext").click()
                            elif engine_key == 'bing':
                                driver.find_element(By.CSS_SELECTOR, "a.sb_pagN").click()
                            elif engine_key == 'duckduckgo':
                                driver.find_element(By.ID, "more-results").click()
                            time.sleep(2)
                        except: break

                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, container_selector))
                        )
                        containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
                        
                        for container in containers:
                            try:
                                # Find the first main link inside the container
                                link_element = container.find_element(By.TAG_NAME, "a")
                                href = link_element.get_attribute("href")
                                if not href or "google.com" in href or "bing.com" in href: continue
                                
                                link_domain = normalize_domain(href)
                                # Log for transparency
                                print(f"  Rank {current_rank}: {link_domain}")

                                if requestedSearchDomain in link_domain:
                                    engine_results.append({"phrase": searchPhrase, "rank": current_rank})
                                    found = True
                                    print(f"  >> TARGET FOUND AT RANK {current_rank} <<")
                                    break
                                current_rank += 1
                            except: continue
                    except: break
                    
                    if found: break

                if not found:
                    engine_results.append({"phrase": searchPhrase, "rank": "not found"})
            
            display_name = engine_key.capitalize()
            if engine_key == 'duckduckgo': display_name = "DuckDuckGo"
            results[display_name] = engine_results

        # CSV Saving logic
        timestamp = int(time.time())
        file_name = f"results_{timestamp}.csv"
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, file_name)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for engine, engine_data in results.items():
                writer.writerow([f"Search Engine: {engine}"])
                writer.writerow(["Keyword", "Rank"])
                for res in engine_data:
                    writer.writerow([res['phrase'], res['rank']])
                writer.writerow([]) 
        
        return results, file_name

    finally:
        driver.quit()
