
import time
from bs4 import BeautifulSoup
import re
import urllib.parse
import os

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class DeepPDFCrawler:
    """
    Crawls a given URL to find a PDF download link.
    Simulates behavior similar to Zotero translators.
    """
    
    def __init__(self):
        pass

    
    # Domain-specific rules for finding PDF links
    # Key: partial domain string
    # Value: Dict with 'selector' (css), 'attribute' (default href), 'base_url_needed' (bool)
    DOMAIN_RULES = {
        'arxiv.org': [
            {'selector': 'a.download-pdf', 'type': 'selector'},
            {'selector': 'a[href^="/pdf/"]', 'type': 'selector'} # Fallback
        ],
        'jmir.org': [
            {'selector': 'a[href$="/PDF"]', 'type': 'selector'},
            {'selector': 'a[aria-label="Download PDF"]', 'type': 'selector'}
        ],
        'springer.com': [
            {'selector': 'a.c-pdf-download__link', 'type': 'selector'},
            {'selector': 'a[data-track-action="download pdf"]', 'type': 'selector'}
        ],
        'biomedcentral.com': [ # Similar to Springer usually
             {'selector': 'a.c-pdf-download__link', 'type': 'selector'}
        ],
        'sciencedirect.com': [
            {'selector': 'a[aria-label*="View PDF"]', 'type': 'selector'}, # "View PDF. Opens in a new window."
            {'selector': 'a.link-button-primary', 'content_text': 'PDF', 'type': 'heuristic'} # Complex SVG inside
        ],
        'ieee.org': [
            {'selector': 'a.xpl-btn-pdf', 'type': 'selector'},
            {'selector': 'iframe', 'attribute': 'src', 'contains': 'pdf', 'type': 'iframe_heuristic'} # Sometimes IEEE embeds
        ],
        'nature.com': [
            {'selector': 'a.c-pdf-download__link', 'type': 'selector'},
            {'selector': 'a[data-test="download-pdf"]', 'type': 'selector'}
        ],
        'researchgate.net': [
             # ResearchGate pages often redirect or have a "Download full-text PDF" button
             {'selector': 'a.js-download-full-text', 'type': 'selector'},
             {'selector': 'a[href*="publication"]', 'text_contains': 'Download', 'type': 'heuristic'}
        ]
    }

    def find_pdf_link(self, url: str, interactive: bool = False) -> str:
        """
        Visits the URL and attempts to return a direct PDF link.
        """
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium/Undetected-Chromedriver not available")
            return None

        print(f"🕵️ Deep Crawl: Visiting {url}...")
        
        try:
            options = uc.ChromeOptions()
            # options.add_argument('--headless') # Keep visible
            
            driver = uc.Chrome(options=options)
            found_pdf_url = None
            
            try:
                driver.get(url)
                
                # Handling Interactive Mode (Cloudflare / CAPTCHAs)
                if interactive:
                    max_wait = 300 # 5 minutes max wait
                    waited = 0
                    while waited < max_wait:
                        # Check for common challenge indicators
                        page_src = driver.page_source.lower()
                        title = driver.title.lower()
                        blocked = False
                        
                        indicators = [
                            "challenge", "security check", "verify you are human", "captcha", 
                            "cloudflare", "human verification", "please wait", "ddos protection",
                            "just a moment"
                        ]
                        
                        # Strong indicators in title or specific elements
                        if any(ind in title for ind in indicators):
                            blocked = True
                        
                        # Cloudflare specific
                        try:
                            if driver.find_element(By.ID, "challenge-running"): blocked = True
                        except: pass
                        
                        if blocked:
                            if waited % 5 == 0:
                                print(f"⚠️  Detectado Bloqueo/Captcha. Esperando al usuario... ({waited}s)")
                            time.sleep(2)
                            waited += 2
                        else:
                            if waited > 0:
                                print("✅ Bloqueo superado. Continuando...")
                                time.sleep(2) # Extra buffer
                            break
                else:
                    time.sleep(5) # Standard wait
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                current_domain = urllib.parse.urlparse(url).netloc
                
                # 1. Check Domain Rules First
                for domain_key, rules in self.DOMAIN_RULES.items():
                    if domain_key in current_domain:
                        print(f"   Matched domain rule: {domain_key}")
                        for rule in rules:
                            try:
                                if rule['type'] == 'selector':
                                    element = soup.select_one(rule['selector'])
                                    if element and element.has_attr('href'):
                                        found_pdf_url = urllib.parse.urljoin(url, element['href'])
                                        print(f"   ✅ Found via rule {rule['selector']}: {found_pdf_url}")
                                        break
                            except Exception as e:
                                print(f"   Rule error: {e}")
                                
                    if found_pdf_url: break

                # 2. Heuristics / Meta tags (Fallback)
                if not found_pdf_url:
                    meta_pdf = soup.find('meta', attrs={'name': 'citation_pdf_url'})
                    if meta_pdf:
                        found_pdf_url = meta_pdf.get('content')
                        print(f"   ✅ Found meta citation_pdf_url: {found_pdf_url}")

                # 3. Generic Scan (Last Resort)
                if not found_pdf_url:
                    candidates = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        # Ignore common non-pdf links
                        if 'mailto:' in href or 'javascript:' in href: continue
                        
                        full_url = urllib.parse.urljoin(url, href)
                        score = 0
                        
                        # Strong signals
                        if full_url.lower().endswith('.pdf'): score += 10
                        if 'pdf' in a.text.lower(): score += 5
                        if 'download' in a.text.lower(): score += 2
                        
                        if score >= 5: # Threshold
                            candidates.append((score, full_url))
                    
                    if candidates:
                        candidates.sort(key=lambda x: x[0], reverse=True)
                        found_pdf_url = candidates[0][1]
                        print(f"   ✅ Found heuristic candidate: {found_pdf_url}")

            finally:
                driver.quit()
                
            return found_pdf_url
            
        except Exception as e:
            print(f"Deep Crawl Error: {e}")
            return None
