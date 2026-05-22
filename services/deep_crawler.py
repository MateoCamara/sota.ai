
import time
from bs4 import BeautifulSoup
import re
import urllib.parse
import os
try:
    import winsound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

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

    
    # Domain-specific rules for finding PDF links.
    # Each rule: {'selector': css, 'type': 'selector', optional 'attribute', 'transform'}.
    # Transforms: 'wiley_pdfdirect' rewrites /doi/pdf/ → /doi/pdfdirect/?download=true
    # so the response is the file rather than the in-page viewer.
    DOMAIN_RULES = {
        'arxiv.org': [
            {'selector': 'a.download-pdf', 'type': 'selector'},
            {'selector': 'a[href^="/pdf/"]', 'type': 'selector'},
        ],
        'jmir.org': [
            {'selector': 'a[href$="/PDF"]', 'type': 'selector'},
            {'selector': 'a[aria-label="Download PDF"]', 'type': 'selector'},
        ],
        'springer.com': [
            {'selector': 'a.c-pdf-download__link', 'type': 'selector'},
            {'selector': 'a[data-track-action="download pdf"]', 'type': 'selector'},
        ],
        'biomedcentral.com': [
            {'selector': 'a.c-pdf-download__link', 'type': 'selector'},
        ],
        'sciencedirect.com': [
            {'selector': 'a[aria-label*="View PDF"]', 'type': 'selector'},
            {'selector': 'a.pdf-download-btn-link', 'type': 'selector'},
            {'selector': 'a.PdfEmbed-button', 'type': 'selector'},
            {'selector': 'a.download-pdf-link', 'type': 'selector'},
            {'selector': 'a[href*="pdfft?md5"]', 'type': 'selector'},
        ],
        'ieee.org': [
            {'selector': 'a.xpl-btn-pdf', 'type': 'selector'},
            {'selector': 'a[href*="stampPDF"]', 'type': 'selector'},
            {'selector': 'iframe', 'attribute': 'src', 'contains': 'pdf',
             'type': 'iframe_heuristic'},
        ],
        'nature.com': [
            {'selector': 'a.c-pdf-download__link', 'type': 'selector'},
            {'selector': 'a[data-test="download-pdf"]', 'type': 'selector'},
        ],
        'researchgate.net': [
            {'selector': 'a.js-download-full-text', 'type': 'selector'},
            {'selector': 'a[href*="publication"]', 'text_contains': 'Download',
             'type': 'heuristic'},
        ],
        # AIP / JASA — strict article-pdf pattern to avoid CMS banners.
        'pubs.aip.org': [
            {'selector': 'a[href*="/article-pdf/"]', 'type': 'selector'},
        ],
        # Wiley serves a viewer on /doi/pdf/<doi>; rewrite to the direct URL.
        'onlinelibrary.wiley.com': [
            {'selector': 'a[href*="/doi/pdfdirect/"]', 'type': 'selector'},
            {'selector': 'a[href*="/doi/pdf/"]', 'type': 'selector',
             'transform': 'wiley_pdfdirect'},
            {'selector': 'a[href*="/doi/epdf/"]', 'type': 'selector',
             'transform': 'wiley_pdfdirect'},
        ],
        'mdpi.com': [
            {'selector': 'a[href*="/pdf"]', 'type': 'selector'},
        ],
        'isca-archive.org': [
            {'selector': 'a[href$=".pdf"]', 'type': 'selector'},
        ],
        'isca-speech.org': [
            {'selector': 'a[href$=".pdf"]', 'type': 'selector'},
        ],
        'frontiersin.org': [
            {'selector': 'a.download-files-pdf', 'type': 'selector'},
            {'selector': 'a[href*="pdf"]', 'type': 'selector'},
        ],
        'academic.oup.com': [
            {'selector': 'a[href*=".pdf"]', 'type': 'selector'},
        ],
        'asmedigitalcollection.asme.org': [
            {'selector': 'a[data-pdf-link]', 'type': 'selector'},
            {'selector': 'a[href$="/pdf"]', 'type': 'selector'},
        ],
        'jstage.jst.go.jp': [
            {'selector': 'a[href$="_pdf"]', 'type': 'selector'},
            {'selector': 'a[href*="_pdf/"]', 'type': 'selector'},
        ],
        'hal.science': [
            {'selector': 'a.file-download-pdf', 'type': 'selector'},
            {'selector': 'a[href$=".pdf"]', 'type': 'selector'},
        ],
        'tandfonline.com': [
            {'selector': 'a[href*="full/pdf"]', 'type': 'selector'},
        ],
        'biorxiv.org': [
            {'selector': 'a[href$=".full.pdf"]', 'type': 'selector'},
        ],
    }

    @staticmethod
    def _apply_transform(name, full_url):
        if name == 'wiley_pdfdirect':
            full = re.sub(r'/doi/e?pdf/', '/doi/pdfdirect/', full_url)
            if 'download=true' not in full:
                full += ('&' if '?' in full else '?') + 'download=true'
            return full
        return full_url

    # ------------------------------------------------------------------
    # NEW: end-to-end PDF download with cookies + Cloudflare clearance.
    # Reuses the institutional session set by IP-authenticated subscribers
    # (e.g. via a university IP) without round-tripping cookies through
    # urllib, which lets us bypass Cloudflare bot walls and JS-rendered
    # download buttons that plain `requests` cannot handle.
    # ------------------------------------------------------------------

    @staticmethod
    def _chrome_options(download_dir: str):
        opts = uc.ChromeOptions()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,1024")
        opts.add_experimental_option("prefs", {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
        })
        return opts

    @staticmethod
    def _detect_chrome_major():
        try:
            import subprocess
            for cmd in ("google-chrome", "chromium", "chromium-browser"):
                try:
                    out = subprocess.run([cmd, "--version"], capture_output=True,
                                         text=True, timeout=5).stdout
                    m = re.search(r"\b(\d+)\.", out)
                    if m:
                        return int(m.group(1))
                except FileNotFoundError:
                    continue
        except Exception:
            pass
        return None

    def _new_driver(self, download_dir: str):
        return uc.Chrome(
            options=self._chrome_options(download_dir),
            version_main=self._detect_chrome_major(),
        )

    @staticmethod
    def _looks_blocked(driver):
        title = (driver.title or "").lower()
        for ind in ("challenge", "security check", "captcha", "cloudflare",
                    "just a moment", "please wait", "ddos protection",
                    "verify you are human"):
            if ind in title:
                return True
        return False

    def _wait_unblock(self, driver, max_wait=60):
        waited = 0
        while waited < max_wait and self._looks_blocked(driver):
            time.sleep(3)
            waited += 3

    # URLs that look like PDFs but are actually publisher banners, ads,
    # user-guide downloads, or terms-of-service pages.
    _BANNER_PATTERNS = (
        'wp-content/uploads', '/assets/', '/static/', '/marketing/',
        'userguide', 'user-guide', 'user_guide',
        '/cookie', '/privacy', '/terms', 'instructions-for-authors',
    )

    @classmethod
    def _is_banner_url(cls, url):
        u = url.lower()
        return any(p in u for p in cls._BANNER_PATTERNS)

    def _extract_pdf_url(self, driver):
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        current_url = driver.current_url
        domain = urllib.parse.urlparse(current_url).netloc.lower()
        for key, rules in self.DOMAIN_RULES.items():
            if key not in domain:
                continue
            for rule in rules:
                el = soup.select_one(rule['selector'])
                if not el:
                    continue
                attr = rule.get('attribute', 'href')
                val = el.get(attr) or ''
                if not val:
                    continue
                full = urllib.parse.urljoin(current_url, val)
                transform = rule.get('transform')
                if transform:
                    full = self._apply_transform(transform, full)
                return full
        meta = soup.find('meta', attrs={'name': 'citation_pdf_url'})
        if meta and meta.get('content'):
            return urllib.parse.urljoin(current_url, meta['content'])
        candidates = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('mailto:', 'javascript:')):
                continue
            full = urllib.parse.urljoin(current_url, href)
            if self._is_banner_url(full):
                continue
            score = 10 if full.lower().endswith('.pdf') else 0
            text = (a.get_text() or '').lower()
            if 'pdf' in text:
                score += 5
            if 'download' in text:
                score += 2
            if score >= 5:
                candidates.append((score, full))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None

    @staticmethod
    def _cdp_fetch(driver, pdf_url):
        """Fetch a PDF URL via the browser's fetch() so cookies + CF clearance attach."""
        import base64
        cur_host = urllib.parse.urlparse(driver.current_url).netloc
        pdf_host = urllib.parse.urlparse(pdf_url).netloc
        if pdf_host and cur_host != pdf_host:
            driver.get(f"{urllib.parse.urlparse(pdf_url).scheme}://{pdf_host}/")
            time.sleep(2)
        js = """
            const url = arguments[0];
            const cb = arguments[arguments.length - 1];
            fetch(url, {credentials: 'include',
                        headers: {'Accept': 'application/pdf,*/*'}})
                .then(r => r.arrayBuffer())
                .then(b => {
                    const bytes = new Uint8Array(b);
                    let s = '';
                    const CHUNK = 0x8000;
                    for (let i = 0; i < bytes.length; i += CHUNK) {
                        s += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
                    }
                    cb({status:'ok', size: bytes.length, b64: btoa(s)});
                })
                .catch(e => cb({status:'err', error: String(e)}));
        """
        try:
            driver.set_script_timeout(60)
            result = driver.execute_async_script(js, pdf_url)
        except Exception as e:
            return None, f"CDP error: {e}"
        if result.get('status') != 'ok':
            return None, f"fetch failed: {result.get('error','?')}"
        data = base64.b64decode(result['b64'])
        if not data.startswith(b"%PDF"):
            return None, f"not a PDF ({len(data)} bytes)"
        return data, "ok"

    @staticmethod
    def _watch_for_native_download(download_dir, before, timeout=30):
        deadline = time.time() + timeout
        download_dir = os.path.abspath(download_dir)
        while time.time() < deadline:
            time.sleep(1.0)
            partials = [f for f in os.listdir(download_dir)
                        if f.endswith('.crdownload')]
            candidates = [f for f in os.listdir(download_dir)
                          if f.lower().endswith('.pdf') and f not in before]
            if candidates and not partials:
                candidates.sort(
                    key=lambda f: os.path.getmtime(os.path.join(download_dir, f)),
                    reverse=True,
                )
                return os.path.join(download_dir, candidates[0])
        return None

    def download_pdf(self, landing_url: str, download_dir: str,
                     output_filename: str | None = None,
                     interactive: bool = False, sound_alert: bool = False,
                     driver=None, max_wait_block: int = 60) -> dict:
        """End-to-end PDF download given a landing URL.

        Visits the page in undetected Chrome (so institutional cookies
        and Cloudflare clearance kick in), tries:
          1. Auto-save detection (publishers that embed a PDF object)
          2. CDP fetch via browser's `fetch()` so cookies+CF auth attach
          3. Native Chrome download to `download_dir`

        Returns the same shape as DownloaderService methods:
            {success: bool, filepath: str | None,
             source: 'DeepCrawl-{stage}', message: str}

        If `driver` is given, the caller manages its lifecycle (useful for
        batch usage to amortize the browser start-up cost). For long
        batches we recommend recycling the driver every ~25 papers since
        Chrome accumulates state (cookies, memory, anti-bot fingerprint
        drift) that can silently break later visits to Cloudflare-protected
        publishers such as JASA/AIP.
        """
        if not SELENIUM_AVAILABLE:
            return {"success": False, "filepath": None,
                    "source": "DeepCrawl", "message": "Selenium not available"}

        os.makedirs(download_dir, exist_ok=True)
        own_driver = driver is None
        if own_driver:
            driver = self._new_driver(download_dir)

        try:
            # Reset state so a previous page can never leak into ours.
            try:
                driver.get("about:blank")
                time.sleep(0.5)
            except Exception:
                pass

            before = {f for f in os.listdir(download_dir)
                      if f.lower().endswith('.pdf')}
            try:
                driver.get(landing_url)
            except Exception as e:
                return {"success": False, "filepath": None,
                        "source": "DeepCrawl-Nav", "message": str(e)}
            time.sleep(4)

            # Did Chrome auto-save the PDF while loading? Some publishers
            # render the PDF after the JS layer completes, so the save can
            # fire several seconds after the page is "complete".
            auto = self._watch_for_native_download(download_dir, before, timeout=12)
            if auto and output_filename:
                target = os.path.join(download_dir, output_filename)
                try:
                    os.replace(auto, target)
                    auto = target
                except Exception:
                    pass
            if auto:
                return {"success": True, "filepath": auto,
                        "source": "DeepCrawl-AutoSave",
                        "message": f"{os.path.getsize(auto)} bytes"}

            if self._looks_blocked(driver):
                self._wait_unblock(driver, max_wait_block)

            # Retry extraction with progressively longer waits so we catch
            # JS-rendered links (e.g. JASA's "Open the PDF" button).
            pdf_url = None
            for extra_wait in (0, 3, 5, 7):
                if extra_wait:
                    time.sleep(extra_wait)
                pdf_url = self._extract_pdf_url(driver)
                if pdf_url:
                    break
            if not pdf_url:
                return {"success": False, "filepath": None,
                        "source": "DeepCrawl-NoLink",
                        "message": "no PDF link found on landing page"}

            # CDP fetch (works through institutional auth + Cloudflare cookies).
            data, info = self._cdp_fetch(driver, pdf_url)
            if data:
                target = os.path.join(
                    download_dir,
                    output_filename or os.path.basename(urllib.parse.urlparse(pdf_url).path) or "paper.pdf",
                )
                if not target.lower().endswith('.pdf'):
                    target += '.pdf'
                with open(target, 'wb') as fh:
                    fh.write(data)
                return {"success": True, "filepath": target,
                        "source": "DeepCrawl-CDP",
                        "message": f"{len(data)} bytes"}

            # Native fallback: navigate Chrome to the PDF URL and wait for the file.
            before2 = {f for f in os.listdir(download_dir)
                       if f.lower().endswith('.pdf')}
            try:
                driver.get(pdf_url)
            except Exception as e:
                return {"success": False, "filepath": None,
                        "source": "DeepCrawl-NativeNav",
                        "message": f"{e} | cdp:{info}"}
            saved = self._watch_for_native_download(download_dir, before2, timeout=30)
            if saved and output_filename:
                target = os.path.join(download_dir, output_filename)
                try:
                    os.replace(saved, target)
                    saved = target
                except Exception:
                    pass
            if saved:
                return {"success": True, "filepath": saved,
                        "source": "DeepCrawl-Native",
                        "message": f"{os.path.getsize(saved)} bytes"}
            return {"success": False, "filepath": None,
                    "source": "DeepCrawl-Failed",
                    "message": f"native timed out | cdp:{info}"}
        finally:
            if own_driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def find_pdf_link(self, url: str, interactive: bool = False, sound_alert: bool = False) -> str:
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
                                if sound_alert and SOUND_AVAILABLE:
                                    # Play a system sound (Frequency 1000Hz, Duration 500ms)
                                    try:
                                        winsound.Beep(1000, 500)
                                    except:
                                        pass
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
