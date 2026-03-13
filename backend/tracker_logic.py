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
        # Wait for either "q" (standard) or "p" (sometimes used)
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
        # Avoid detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        if HAS_WDM:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

    # Normalize domain exactly like your script
    charactersToBeCleared = ["http://", "https://", "www."]
    for character in charactersToBeCleared:
        requestedSearchDomain = requestedSearchDomain.replace(character, "")
    requestedSearchDomain = requestedSearchDomain.lower().strip()

    results = {}
    
    try:
        for searchEngine in search_engines:
            engine_key = searchEngine.lower().strip()
            engine_results = []
            
            for searchPhrase in search_phrases:
                searchPhrase = searchPhrase.strip()
                if not searchPhrase: continue
                
                print(f"Tracking '{searchPhrase}' on {engine_key}...")
                
                if engine_key == 'google':
                    search_internal(driver, "https://www.google.com", searchPhrase)
                    selector = "div.yuRUbf a, div.kvH9C a, div.g a" # Multi-selector for better catch
                elif engine_key == 'bing':
                    search_internal(driver, "https://www.bing.com", searchPhrase)
                    selector = "li.b_algo h2 a"
                elif engine_key == 'duckduckgo':
                    search_internal(driver, "https://duckduckgo.com", searchPhrase)
                    selector = "a[data-testid='result-title-a']"
                else:
                    continue

                try:
                    # Wait for results to load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                except Exception as e:
                    print(f"Timeout waiting for results for '{searchPhrase}' on {engine_key}")
                    engine_results.append({"phrase": searchPhrase, "rank": "not found"})
                    continue

                rank = 1
                found = False
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if not href: continue
                        
                        link_domain = normalize_domain(href)
                        if requestedSearchDomain in link_domain:
                            engine_results.append({"phrase": searchPhrase, "rank": rank})
                            found = True
                            print(f"  Found at rank {rank}!")
                            break
                        rank += 1
                        if rank > 50: break # Depth limit
                    except:
                        continue

                if not found:
                    engine_results.append({"phrase": searchPhrase, "rank": "not found"})
            
            # Map engine names back to their original display names
            display_name = engine_key.capitalize()
            if engine_key == 'duckduckgo': display_name = "DuckDuckGo"
            results[display_name] = engine_results

        # CSV Saving logic
        timestamp = int(time.time())
        file_name = f"results_{timestamp}.csv"
        # Use a path that works in both Local and Docker
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
                writer.writerow([]) # Spacer
        
        return results, file_name

    finally:
        driver.quit()
