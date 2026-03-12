from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse
import csv
import re
import time

driver = None

while driver is None:
    requestedBrowser = input("Run script in Chrome or Firefox? ")

    match requestedBrowser.lower().strip():
        case "chrome":
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        case _:
            print("Please choose Chrome for now.")

def normalize_domain(url):
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return url.lower()

def search(url, searchPhrase):
    driver.get(url)
    entryField = driver.find_element(By.NAME, "q")
    entryField.clear()
    entryField.send_keys(searchPhrase)
    entryField.send_keys(Keys.RETURN)

requestedSearchEngines = input(
    "Enter desired search engines, separated by commas if multiple (Google, Bing, DuckDuckGo): "
)

requestedSearchPhrases = input(
    "Enter desired search terms or phrases, separated by commas if multiple : "
)

requestedSearchDomain = input("Enter domain to match : ")

charactersToBeCleared = ["http://", "https://", "www."]
for character in charactersToBeCleared:
    requestedSearchDomain = requestedSearchDomain.replace(character, "")
requestedSearchDomain = requestedSearchDomain.lower().strip()

searchEngines = requestedSearchEngines.split(",")
searchPhrases = [s.strip() for s in requestedSearchPhrases.split(",")]

results = {}

for searchEngine in searchEngines:
    match searchEngine.lower().strip():
        case 'google':
            googleResults = []
            for searchPhrase in searchPhrases:
                search("https://www.google.com", searchPhrase)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.yuRUbf a"))
                    )
                    links = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
                except Exception as e:
                    print(f"Timeout or error loading Google results for '{searchPhrase}': {e}")
                    with open("debug_google.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    googleResults.append({searchPhrase: "not found"})
                    continue

                rank = 1
                found = False
                for link in links:
                    href = link.get_attribute("href")
                    link_domain = normalize_domain(href)
                    if requestedSearchDomain in link_domain:
                        googleResults.append({searchPhrase: rank})
                        found = True
                        break
                    rank += 1

                if not found:
                    # For debugging: print all found domains
                    print(f"Google: '{searchPhrase}' not found. Domains on page:")
                    for link in links:
                        print("  ", normalize_domain(link.get_attribute("href")))
                    googleResults.append({searchPhrase: "not found"})
            results["Google"] = googleResults

        case 'bing':
            bingResults = []
            for searchPhrase in searchPhrases:
                search("https://www.bing.com", searchPhrase)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.b_algo h2 a"))
                    )
                    links = driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a")
                except Exception as e:
                    print(f"Timeout or error loading Bing results for '{searchPhrase}': {e}")
                    with open("debug_bing.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    bingResults.append({searchPhrase: "not found"})
                    continue

                rank = 1
                found = False
                for link in links:
                    href = link.get_attribute("href")
                    link_domain = normalize_domain(href)
                    if requestedSearchDomain in link_domain:
                        bingResults.append({searchPhrase: rank})
                        found = True
                        break
                    rank += 1

                if not found:
                    print(f"Bing: '{searchPhrase}' not found. Domains on page:")
                    for link in links:
                        print("  ", normalize_domain(link.get_attribute("href")))
                    bingResults.append({searchPhrase: "not found"})
            results["Bing"] = bingResults

        case 'duckduckgo':
            ddgResults = []
            for searchPhrase in searchPhrases:
                search("https://duckduckgo.com", searchPhrase)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='result-title-a']"))
                    )
                    links = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
                except Exception as e:
                    print(f"Timeout or error loading DuckDuckGo results for '{searchPhrase}': {e}")
                    with open("debug_ddg.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    ddgResults.append({searchPhrase: "not found"})
                    continue

                rank = 1
                found = False
                for link in links:
                    href = link.get_attribute("href")
                    link_domain = normalize_domain(href)
                    if requestedSearchDomain in link_domain:
                        ddgResults.append({searchPhrase: rank})
                        found = True
                        break
                    rank += 1

                if not found:
                    print(f"DuckDuckGo: '{searchPhrase}' not found. Domains on page:")
                    for link in links:
                        print("  ", normalize_domain(link.get_attribute("href")))
                    ddgResults.append({searchPhrase: "not found"})
            results["DuckDuckGo"] = ddgResults

        case _:
            print("Not a valid selection.")

fileName = str(int(time.time())) + ".csv"

with open(fileName, 'w', newline='') as file:
    writer = csv.writer(file)
    for engine in results:
        writer.writerow([engine])
        engineResults = results[engine]
        counter = 0
        for result in engineResults:
            writer.writerow([searchPhrases[counter], result[searchPhrases[counter]]])
            counter += 1

print("Results saved to:", fileName)
driver.quit()