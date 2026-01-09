
import time
import urllib.parse
from bs4 import BeautifulSoup
import re

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class ScholarService:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar"

    def search_papers(self, query: str, limit: int = 10) -> list:
        """
        Search Google Scholar using Selenium.
        Ensure consistent keys in return dictionaries.
        """
        if not SELENIUM_AVAILABLE:
            print("❌ undetected-chromedriver not installed.")
            return []

        print(f"Searching Google Scholar for: {query}")
        results = []
        
        try:
            options = uc.ChromeOptions()
            # options.add_argument('--headless') # Keep visible for captcha
            
            print("🚀 Launching browser...")
            driver = uc.Chrome(options=options)
            
            try:
                params = {"q": query, "hl": "en"}
                url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
                driver.get(url)
                
                # Manual Captcha Wait
                while "sorry" in driver.current_url or "ipv4.google.com" in driver.current_url:
                    print("⚠️  CAPTCHA detected! Please solve it.")
                    time.sleep(5)
                
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "gs_res_ccl")))
                
                while len(results) < limit:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    entries = soup.find_all('div', class_='gs_r gs_or gs_scl')
                    
                    for entry in entries:
                        if len(results) >= limit:
                            break
                        
                        try:
                            # Initialize with defaults to avoid KeyErrors
                            res = {
                                'Title': 'N/A',
                                'DOI': 'N/A', 
                                'Publication_Year': 'N/A',
                                'Authors': 'N/A',
                                'Source': 'Google Scholar',
                                'URL': 'N/A',
                                'PDF_Link': None
                            }
                            
                            # Title & Link Cleaning
                            title_tag = entry.find('h3', class_='gs_rt')
                            if title_tag:
                                # Remove standard [PDF], [HTML], [BOOK], [CITATION] tags and unbracketed HTML/PDF prefixes
                                raw_title = title_tag.text
                                # 1. Remove bracketed content like [HTML] or [PDF]
                                clean_title = re.sub(r'\[.*?\]', '', raw_title)
                                # 2. Remove leading "HTML" or "PDF" words that might remain (case insensitive)
                                clean_title = re.sub(r'^\s*(html|pdf|book|citation)\s+', '', clean_title, flags=re.IGNORECASE)
                                # 3. Double cleanup of spaces
                                clean_title = clean_title.strip()
                                res['Title'] = clean_title
                                
                                link_tag = title_tag.find('a')
                                if link_tag:
                                    res['URL'] = link_tag['href']
                                    
                                    # Attempt to extract DOI from URL
                                    # Common DOI pattern: 10.xxxx/yyyy
                                    doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', res['URL'])
                                    if doi_match:
                                        res['DOI'] = doi_match.group(1)

                            # Metadata (Authors, Year, Source)
                            info_tag = entry.find('div', class_='gs_a')
                            if info_tag:
                                info_text = info_tag.text
                                parts = info_text.split(' - ')
                                if len(parts) > 0:
                                    res['Authors'] = parts[0]
                                    
                                # Extract year
                                year_match = re.search(r'\d{4}', info_text)
                                if year_match:
                                    res['Publication_Year'] = year_match.group(0)

                            # Direct PDF Link (Right side)
                            pdf_div = entry.find('div', class_='gs_or_ggsm')
                            if pdf_div:
                                pdf_a = pdf_div.find('a')
                                if pdf_a:
                                    res['PDF_Link'] = pdf_a['href']
                                    res['Source'] = "Google Scholar (Direct PDF)"

                            # If DOI is still missing, try to resolve via CrossRef using Title
                            if res['DOI'] == 'N/A' and res['Title'] != 'N/A':
                                try:
                                    # Simple CrossRef Query (Public API)
                                    import requests
                                    # Polite pool: good practice to include email, but works without for low volume
                                    cr_url = f"https://api.crossref.org/works?query.title={urllib.parse.quote(res['Title'])}&rows=1"
                                    cr_resp = requests.get(cr_url, timeout=5)
                                    if cr_resp.status_code == 200:
                                        data = cr_resp.json()
                                        if data['message']['items']:
                                            # Check if title match is close enough could be good, but for now take top 1
                                            found_doi = data['message']['items'][0].get('DOI')
                                            if found_doi:
                                                 res['DOI'] = found_doi
                                except Exception:
                                    pass # Fail silently on DOI resolution
                                    
                            results.append(res)
                            
                        except Exception as e:
                            print(f"Entry parsing error: {e}")

                    # Pagination
                    if len(results) < limit:
                        try:
                            next_btn = driver.find_element(By.XPATH, "//b[contains(text(),'Next')]/..")
                            next_btn.click()
                            time.sleep(2)
                            while "sorry" in driver.current_url:
                                time.sleep(2)
                        except:
                            break
            finally:
                driver.quit()
                
            return results
        except Exception as e:
            print(f"Scholar Error: {e}")
            return []
