
from Bio import Entrez
import time

class PubMedService:
    def __init__(self, email: str = "your.email@example.com"):
        # Always tell NCBI who you are
        Entrez.email = email

    def search_papers(self, query: str, limit: int = 10) -> list:
        """
        Search for papers in PubMed.
        Returns list of dicts with Title, DOI, Publication_Year, Source.
        """
        print(f"Searching PubMed for: {query}")
        try:
            # 1. Search for IDs
            handle = Entrez.esearch(db="pubmed", term=query, retmax=limit)
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record["IdList"]
            if not id_list:
                return []
                
            # 2. Fetch details
            handle = Entrez.efetch(db="pubmed", id=id_list, rettype="medline", retmode="text")
            # We parse simplified xml or medline format
            # Let's use ESummary for easier JSON-like parsing usually, but EFetch gives more data.
            # Using ESummary for simplicity:
            handle = Entrez.esummary(db="pubmed", id=",".join(id_list), retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            results = []
            for r in records:
                try:
                    title = r.get("Title", "N/A")
                    pub_date = r.get("PubDate", "")
                    # Extract year roughly
                    year = pub_date.split()[0] if pub_date else "N/A"
                    
                    # DOI is often in ArticleIds
                    doi = "N/A"
                    if "ArticleIds" in r:
                        # ArticleIds is a dictionary-like object/list in BioPython
                        # It usually looks like {'pubmed': ['123'], 'doi': '10.xxx', ...}
                        # or a list of strings
                        
                        # In Entrez esummary XML, ArticleIds is a dictionary where keys are types
                        if 'doi' in r['ArticleIds']:
                            doi = r['ArticleIds']['doi']
                    
                    source = r.get("Source", "PubMed")
                    
                    results.append({
                        "Title": title,
                        "DOI": doi,
                        "Publication_Year": year,
                        "Source": f"PubMed ({source})",
                        "Authors": ", ".join(r.get("AuthorList", [])) if "AuthorList" in r else "N/A"
                    })
                except Exception as e:
                    print(f"Error parsing PubMed record: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"PubMed Search Error: {e}")
            print("Make sure 'biopython' is installed: pip install biopython")
            return []
