import os
import sys
import requests
import re
from scihub import SciHub

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

    def download_by_doi(self, doi: str, title: str) -> dict:
        """
        Download using pypaperretriever (more robust for DOIs).
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
            
            # Try PyPaperRetriever first (Priority: Unpaywall -> SciHub)
            try:
                # Using user's email for Unpaywall API (requires valid email)
                retriever = PaperRetriever(
                    email="superjorgy007@hotmail.com", 
                    doi=clean_doi,
                    download_directory=self.download_dir,
                    allow_scihub=True
                )
                
                result = retriever.download()
                
                # Check result properties
                if result and hasattr(result, 'is_downloaded') and result.is_downloaded:
                    return {
                        "success": True,
                        "filepath": getattr(result, 'saved_file_path', self.download_dir),
                        "source": "Unpaywall/SciHub",
                        "message": "Download successful via DOI"
                    }
                else:
                    raise Exception("PyPaperRetriever returned failure")
                    
            except Exception as e:
                print(f"⚠️ PyPaperRetriever failed ({e}). Falling back to direct SciHub...")
                
                # Fallback to direct SciHub
                sh = SciHub()
                # Check if we should sanitize title for filename
                output_name = re.sub(r'[^\w\s-]', '', title).strip() + ".pdf" if title else f"{clean_doi.replace('/', '_')}.pdf"
                output_path = os.path.join(self.download_dir, output_name)
                
                try:
                    # scihub download returns a dictionary or bytes?
                    # The library usually saves to file if path provided
                    sh_result = sh.download(clean_doi, path=output_path)
                    
                    if os.path.exists(output_path):
                         return {
                            "success": True,
                            "filepath": output_path,
                            "source": "Direct SciHub",
                            "message": "Download successful via Direct SciHub"
                        }
                    else:
                         return {
                            "success": False,
                            "filepath": None,
                            "message": "Direct SciHub failed to save file",
                            "source": "Direct SciHub"
                        }
                except Exception as sh_e:
                     return {
                        "success": False,
                        "filepath": None,
                        "message": f"All DOI methods failed. PyPaperRetriever: {e}, SciHub: {sh_e}",
                        "source": "DOI-Fallback-Failed"
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
