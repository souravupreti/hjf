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
        print("Running in Docker - Using System Chromium")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/chromium"
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        print("Running Locally - Matches your original script")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        if HAS_WDM:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

    # Normalize domain
    charactersToBeCleared = ["http://", "https://", "www."]
    for character in charactersToBeCleared:
        requestedSearchDomain = requestedSearchDomain.replace(character, "")
    requestedSearchDomain = requestedSearchDomain.lower().strip()

    results = {}
    MAX_PAGES = 5 # Scan up to 5 pages (Top 50-60)
    
    try:
        for searchEngine in search_engines:
            engine_key = searchEngine.lower().strip()
            engine_results = []
            
            for searchPhrase in search_phrases:
                searchPhrase = searchPhrase.strip()
                if not searchPhrase: continue
                
                print(f"Tracking '{searchPhrase}' on {engine_key} (Deep Scan)...")
                current_rank = 1
                found = False

                for page in range(1, MAX_PAGES + 1):
                    print(f"  Scanning Page {page}...")
                    
                    if page == 1:
                        if engine_key == 'google':
                            search_internal(driver, "https://www.google.com", searchPhrase)
                            selector = "div.yuRUbf a, div.kvH9C a, div.g a"
                        elif engine_key == 'bing':
                            search_internal(driver, "https://www.bing.com", searchPhrase)
                            selector = "li.b_algo h2 a"
                        elif engine_key == 'duckduckgo':
                            search_internal(driver, "https://duckduckgo.com", searchPhrase)
                            selector = "a[data-testid='result-title-a']"
                        else:
                            break
                    else:
                        # Logic to go to next page
                        try:
                            if engine_key == 'google':
                                next_btn = driver.find_element(By.ID, "pnnext")
                                next_btn.click()
                            elif engine_key == 'bing':
                                next_btn = driver.find_element(By.CSS_SELECTOR, "a.sb_pagN")
                                next_btn.click()
                            elif engine_key == 'duckduckgo':
                                # DuckDuckGo uses a "More Results" button
                                next_btn = driver.find_element(By.ID, "more-results")
                                next_btn.click()
                            time.sleep(2) # Wait for page load
                        except:
                            print(f"    No more pages found for {engine_key}")
                            break

                    try:
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        links = driver.find_elements(By.CSS_SELECTOR, selector)
                    except Exception:
                        print(f"    Results didn't load on page {page}")
                        break

                    for link in links:
                        try:
                            href = link.get_attribute("href")
                            if not href: continue
                            link_domain = normalize_domain(href)
                            
                            if requestedSearchDomain in link_domain:
                                engine_results.append({"phrase": searchPhrase, "rank": current_rank})
                                found = True
                                print(f"    !!! Found at rank {current_rank} !!!")
                                break
                            current_rank += 1
                        except:
                            continue
                    
                    if found: break # Stop scanning pages if found

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
