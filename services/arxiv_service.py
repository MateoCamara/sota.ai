
import arxiv
import requests

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
