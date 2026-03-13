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
                print(f"\n[Precision Scan] '{searchPhrase}' on {engine_key}...")
                current_rank = 1
                found = False

                for page in range(1, MAX_PAGES + 1):
                    # Construct URL directly
                    if engine_key == 'google':
                        start = (page - 1) * 10
                        url = f"https://www.google.com/search?q={searchPhrase.replace(' ', '+')}&pws=0&start={start}"
                        # Primary container for Google results
                        container_selector = "div.g, div.tF2Cxc, div.MjjYud"
                    elif engine_key == 'bing':
                        first = (page - 1) * 10 + 1
                        url = f"https://www.bing.com/search?q={searchPhrase.replace(' ', '+')}&first={first}"
                        container_selector = "li.b_algo"
                    else:
                        url = f"https://duckduckgo.com/?q={searchPhrase.replace(' ', '+')}"
                        container_selector = "article[data-testid='result']"
                    
                    driver.get(url)
                    time.sleep(2)

                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, container_selector))
                        )
                        # Find all result containers
                        containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
                        
                        last_domain = None
                        for container in containers:
                            try:
                                # Skip widgets like 'People also ask', 'Videos', or 'Images'
                                # These often don't have the main result title/link structure
                                container_text = container.text.lower()
                                if any(x in container_text for x in ["people also ask", "images for", "videos for", "related searches"]):
                                    continue

                                # Get the main link (usually first a tag with h3/h2 inside or the data-ved)
                                try:
                                    link_element = container.find_element(By.CSS_SELECTOR, "h3 a, a h3, h2 a, a h2")
                                except:
                                    # Fallback: Find the first significant link
                                    links = container.find_elements(By.TAG_NAME, "a")
                                    link_element = None
                                    for l in links:
                                        h = l.get_attribute("href")
                                        if h and not any(x in h for x in ["google.com", "bing.com", "search?", "cache:", "translate.google"]):
                                            link_element = l
                                            break
                                
                                if not link_element: continue
                                
                                href = link_element.get_attribute("href")
                                if not href: continue
                                
                                link_domain = normalize_domain(href)
                                
                                # Deduplicate consecutive identical results (indented links)
                                if link_domain == last_domain:
                                    continue
                                
                                last_domain = link_domain
                                
                                # Finally check if it matches our target
                                if requestedSearchDomain in link_domain:
                                    engine_results.append({"phrase": searchPhrase, "rank": current_rank})
                                    found = True
                                    print(f"  Rank {current_rank}: {link_domain} (MATCH FOUND!)")
                                    break
                                
                                print(f"  Rank {current_rank}: {link_domain}")
                                current_rank += 1
                                if current_rank > 100: break
                            except:
                                continue
                    except Exception:
                        print(f"    No results found on page {page}.")
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
