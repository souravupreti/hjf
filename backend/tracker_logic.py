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
                    # Construct URL directly to avoid search field timing issues
                    if engine_key == 'google':
                        start = (page - 1) * 10
                        url = f"https://www.google.com/search?q={searchPhrase.replace(' ', '+')}&pws=0&start={start}"
                        header_selector = "h3"
                    elif engine_key == 'bing':
                        first = (page - 1) * 10 + 1
                        url = f"https://www.bing.com/search?q={searchPhrase.replace(' ', '+')}&first={first}"
                        header_selector = "h2"
                    else: # DuckDuckGo
                        url = f"https://duckduckgo.com/?q={searchPhrase.replace(' ', '+')}"
                        header_selector = "h2"
                    
                    driver.get(url)
                    time.sleep(2) # Allow results to load

                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, header_selector))
                        )
                        # Find all headers - these represent unique organic results
                        headers = driver.find_elements(By.TAG_NAME, header_selector)
                        
                        for header in headers:
                            try:
                                # Get the nearest link to this header
                                # We look for 'a' either in the header or in its parent/ancestor
                                link_element = None
                                try:
                                    link_element = header.find_element(By.XPATH, "./ancestor::a")
                                except:
                                    try:
                                        link_element = header.find_element(By.XPATH, ".//a")
                                    except:
                                        # Fallback to parent's first link
                                        try:
                                            link_element = header.find_element(By.XPATH, "..//a")
                                        except:
                                            continue
                                
                                if not link_element: continue
                                
                                href = link_element.get_attribute("href")
                                if not href or any(x in href for x in ["google.com", "bing.com", "search?", "cache:", "translate.google"]):
                                    continue
                                
                                link_domain = normalize_domain(href)
                                print(f"  Rank {current_rank}: {link_domain}")

                                if requestedSearchDomain in link_domain:
                                    engine_results.append({"phrase": searchPhrase, "rank": current_rank})
                                    found = True
                                    print(f"  >> TARGET FOUND AT RANK {current_rank} <<")
                                    break
                                
                                current_rank += 1
                                if current_rank > 100: break
                            except:
                                continue
                    except:
                        print(f"    Page {page} timeout or no results.")
                        break
                    
                    if found: break

                if not found:
                    engine_results.append({"phrase": searchPhrase, "rank": "not found"})
            
            display_name = engine_key.capitalize()
            if engine_key == 'duckduckgo': display_name = "DuckDuckGo"
            results[display_name] = engine_results

        # CSV Saving
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
