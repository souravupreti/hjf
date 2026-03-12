from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse
import csv
import time
import os

def normalize_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return url.lower()

def run_rank_tracker(search_engines, search_phrases, target_domain):
    print(f"Starting tracking for {target_domain}...")
    chrome_options = Options()
    
    is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
    
    if is_docker:
        print("Running in Docker - Using Headless Mode")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Let Selenium 4 find the system chrome/driver automatically
    else:
        print("Running Locally - Using Headed Mode")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Use Selenium 4's built-in manager (no need for ChromeDriverManager)
    driver = webdriver.Chrome(options=chrome_options)
    
    # Normalize target domain
    characters_to_clear = ["http://", "https://", "www."]
    for character in characters_to_clear:
        target_domain = target_domain.replace(character, "")
    target_domain = target_domain.lower().strip()

    results = {}
    
    try:
        for engine in search_engines:
            engine_key = engine.lower().strip()
            print(f"Engine: {engine_key}")
            engine_results = []
            
            for phrase in search_phrases:
                phrase = phrase.strip()
                print(f"  Searching: {phrase}")
                
                if engine_key == 'google':
                    driver.get("https://www.google.com")
                    selector = "div.yuRUbf a"
                elif engine_key == 'bing':
                    driver.get("https://www.bing.com")
                    selector = "li.b_algo h2 a"
                elif engine_key == 'duckduckgo':
                    driver.get("https://duckduckgo.com")
                    selector = "a[data-testid='result-title-a']"
                else:
                    continue

                try:
                    entry_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "q"))
                    )
                    entry_field.clear()
                    entry_field.send_keys(phrase)
                    entry_field.send_keys(Keys.RETURN)
                    
                    # Wait for results
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    rank = 1
                    found = False
                    for link in links:
                        href = link.get_attribute("href")
                        if not href: continue
                        link_domain = normalize_domain(href)
                        if target_domain in link_domain:
                            engine_results.append({"phrase": phrase, "rank": rank})
                            found = True
                            break
                        rank += 1

                    if not found:
                        engine_results.append({"phrase": phrase, "rank": "not found"})
                        
                except Exception as e:
                    print(f"    Error processing phrase {phrase}: {e}")
                    engine_results.append({"phrase": phrase, "rank": "not found"})
                
                time.sleep(1.5) # Gentle delay
            
            results[engine] = engine_results

        # Save to CSV
        timestamp = int(time.time())
        file_name = f"results_{timestamp}.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_dir = os.path.join(base_dir, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, file_name)
        
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            for engine, engine_results_list in results.items():
                writer.writerow([engine])
                for res in engine_results_list:
                    writer.writerow([res['phrase'], res['rank']])
        
        print(f"Results saved to {file_path}")
        return results, file_name

    finally:
        driver.quit()
