import os
import sys
import requests
import re
from scihub import SciHub
from services.scihub_service import SciHubService

# Add parent directory to path to import brother packages

# Add parent directory to path to import sibling packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

class DownloaderService:
    def __init__(self, download_dir: str = "downloaded_papers"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)


    
    def download_from_url(self, url: str, filename: str) -> dict:
        """
        Download a PDF directly from a URL.
        """
        print(f"Direct download from: {url}")
        try:
            # Headers to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                # Ensure extension
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                    
                # Sanitize filename
                filename = re.sub(r'[^\w\s-]', '', filename).strip() + ".pdf"
                filepath = os.path.join(self.download_dir, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                return {
                    "success": True,
                    "filepath": filepath,
                    "source": "Direct URL",
                    "message": "Download successful"
                }
            else:
                 return {
                    "success": False,
                    "filepath": None,
                    "message": f"HTTP Error {response.status_code}",
                    "source": "Direct URL"
                }
                
        except Exception as e:
            return {
                "success": False,
                "filepath": None,
                "message": str(e),
                "source": "Direct URL"
            }

    def download_by_doi(self, doi: str, title: str,
                        allow_scihub: bool = False) -> dict:
        """
        Download using pypaperretriever (Unpaywall) and, only if
        `allow_scihub=True`, fall back to the multi-mirror Sci-Hub
        service. See services/scihub_service.py for the legal note.
        """
        print(f"Downloading via DOI (pypaperretriever): {doi}")
        try:
            from pypaperretriever import PaperRetriever
        except ImportError:
            return {
                "success": False,
                "filepath": None,
                "message": "pypaperretriever not installed. Run: pip install git+https://github.com/JosephIsaacTurner/pypaperretriever.git",
                "source": "DOI-Retriever"
            }

        try:
            # Clean DOI
            clean_doi = str(doi).strip()
            
            # Try PyPaperRetriever first (mainly for the Unpaywall path).
            try:
                retriever = PaperRetriever(
                    email=os.getenv("UNPAYWALL_EMAIL", "anonymous@example.com"),
                    doi=clean_doi,
                    download_directory=self.download_dir,
                    allow_scihub=allow_scihub,
                )

                result = retriever.download()

                if result and hasattr(result, 'is_downloaded') and result.is_downloaded:
                    return {
                        "success": True,
                        "filepath": getattr(result, 'saved_file_path', self.download_dir),
                        "source": "Unpaywall" + ("/SciHub-pypaper" if allow_scihub else ""),
                        "message": "Download successful via DOI"
                    }
                else:
                    raise Exception("PyPaperRetriever returned failure")

            except Exception as e:
                if not allow_scihub:
                    return {
                        "success": False,
                        "filepath": None,
                        "message": f"Unpaywall returned no OA copy; SciHub not enabled. ({e})",
                        "source": "DOI-Unpaywall-Failed",
                    }
                print(f"⚠️ PyPaperRetriever failed ({e}). Falling back to multi-mirror SciHub…")

                # Multi-mirror SciHub fallback.
                # NB: pypaperretriever hardcodes sci-hub.se which is DNS-blocked
                # in several countries (Spain, Italy, …). Our service tries
                # sci-hub.ren / .ru / .st / .cat / sci.bban.top in turn.
                output_name = (
                    re.sub(r'[^\w\s-]', '', title).strip() + ".pdf"
                    if title else f"{clean_doi.replace('/', '_')}.pdf"
                )
                sh = SciHubService(download_dir=self.download_dir)
                r = sh.download(clean_doi, output_filename=output_name,
                                allow_scihub=True)
                if r.get("success"):
                    return {
                        "success": True,
                        "filepath": r["filepath"],
                        "source": r["source"],
                        "message": r["message"],
                    }
                return {
                    "success": False,
                    "filepath": None,
                    "message": f"All DOI methods failed. PyPaperRetriever: {e}; SciHub: {r['message']}",
                    "source": "DOI-Fallback-Failed",
                }
        except Exception as e:
            return {
                "success": False,
                "filepath": None,
                "message": f"Unexpected error: {str(e)}",
                "source": "Process-Error"
            }
            

        """
        [DEPRECATED] Download by title using PyPaperBot was unreliable.
        Now mostly a placeholder or legacy method.
        """
        print(f"Skipping download_paper (PyPaperBot) for: {title} - Method Disabled by configuration.")
        return {
            "success": False,
            "filepath": None,
            "message": "PyPaperBot downloaded disabled.",
            "source": "Disabled"
        }
