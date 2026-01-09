
import arxiv
import requests
import os

class ArxivService:
    def search_papers(self, query: str, limit: int = 10) -> list:
        """
        Search for papers in ArXiv.
        Returns list of dicts with Title, DOI, Publication_Year, Source, URL.
        """
        print(f"Searching ArXiv for: {query}")
        try:
            # Construct client
            client = arxiv.Client()
            
            # Construct search
            search = arxiv.Search(
                query=query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results = []
            for r in client.results(search):
                # Clean title
                title = r.title.replace('\n', ' ')
                
                # Get DOI if available, else use ArXiv URL
                doi = r.doi if r.doi else f"ArXiv:{r.get_short_id()}"
                
                results.append({
                    "Title": title,
                    "DOI": doi,
                    "Publication_Year": r.published.year,
                    "Authors": ", ".join([a.name for a in r.authors]),
                    "Source": "ArXiv",
                    "URL": r.pdf_url
                })
                
            return results
            
        except Exception as e:
            print(f"ArXiv Search Error: {e}")
            return []

    def download_paper(self, arxiv_url: str, output_path: str) -> dict:
        """
        Download paper using arxiv library.
        """
        try:
            # Extract ID from URL (e.g., http://arxiv.org/abs/2101.00000 -> 2101.00000)
            # or http://arxiv.org/pdf/2101.00000
            import re
            
            # Match 4 digits followed by dot and digits (arxiv id format)
            # Optional version number at the end
            # We look for the last occurrence of this pattern in the URL
            match = re.search(r'(\d{4}\.\d{4,5}(v\d+)?)', arxiv_url)
            
            if not match:
                # Try finding just the ID part if it's old format (e.g. hep-th/0001001), but keeping it simple for now
                # as most are standard. If not found, fall back to last part of url
                paper_id = arxiv_url.split('/')[-1].replace('.pdf', '')
            else:
                paper_id = match.group(0)
            
            print(f"Downloading ArXiv paper {paper_id}...")
            
            client = arxiv.Client()
            search = arxiv.Search(id_list=[paper_id])
            paper = next(client.results(search))
            
            # Filename
            directory = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            
            paper.download_pdf(dirpath=directory, filename=filename)
            
            return {
                "success": True,
                "filepath": output_path,
                "source": "ArXiv Library",
                "message": "Download successful"
            }
            
        except Exception as e:
            print(f"ArXiv Download Error: {e}")
            return {
                "success": False,
                "message": str(e),
                "source": "ArXiv Library"
            }
